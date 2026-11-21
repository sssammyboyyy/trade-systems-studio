"""
Audit orchestration: document -> parsed payload -> deterministic rule engines -> AuditResult.

Every audit is computed from a real document (a bundled fixture PDF or an upload) or from
an explicit caller payload. There is no silent fallback to canned data.

Provenance (ADR-001):
    run_digest = SHA-256(calc_version | canonical(engagement_policy) | ruleset_hash | document_sha256)
where ``ruleset_hash`` is the SHA-256 of the source of every rule module, so any change
to a rule produces a new run id for the same document.
"""

import hashlib
import json
import logging
import os
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

from app.core.config import settings
from app.core.statutory_rates import ieepa_max_penalty
from app.models.schemas import AuditResult, BoundingBox, Discrepancy, KillShotMetrics, default_engagement_policy
from app.services.ai_classifier import ai_classifier
from app.services.customs_audit import audit_customs_invoice
from app.services.drawback_audit import audit_duty_drawback
from app.services.freight_audit import audit_freight_bill
from app.services.pdf_field_parser import ParsedDocument, parse_document
from app.services.utils import optional_decimal, parse_iso_date

logger = logging.getLogger(__name__)

CALC_VERSION = "2026.2.0"

# The bundled fixtures are evaluated as of a fixed date so the demo is reproducible
# (interest accrual and the drawback claim date depend on it). Uploads use today's date.
FIXTURE_AS_OF = date(2026, 11, 20)

_RULE_MODULES = (
    "core/statutory_rates.py",
    "core/penalties.py",
    "services/customs_audit.py",
    "services/freight_audit.py",
    "services/drawback_audit.py",
    "services/sanctions_screener.py",
    "services/pdf_field_parser.py",
)


def _compute_ruleset_hash() -> str:
    root = Path(__file__).resolve().parent.parent
    h = hashlib.sha256()
    for rel in _RULE_MODULES:
        h.update(rel.encode())
        h.update((root / rel).read_bytes())
    return h.hexdigest()


RULESET_HASH = _compute_ruleset_hash()


def canonical_json(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def compute_run_digest(policy: Dict[str, Any], document_sha256: str) -> str:
    return hashlib.sha256(
        b"|".join([CALC_VERSION.encode(), canonical_json(policy), RULESET_HASH.encode(), document_sha256.encode()])
    ).hexdigest()


# Scenario catalogue for the bundled fixture documents.
SCENARIOS: Dict[str, Dict[str, str]] = {
    "concept_1_customs": {
        "title": "Concept 1: Customs Compliance Firewall",
        "subtitle": "19 U.S.C. § 1592 Penalty Exposure & 19 U.S.C. § 1401a Valuation",
        "filename": "nightmare_01_customs_ci.pdf",
    },
    "concept_2_freight": {
        "title": "Concept 2: Pre-Payment Freight Audit",
        "subtitle": "Detention Free Time & 46 CFR Part 541 Billing Requirements",
        "filename": "nightmare_02_freight_audit.pdf",
    },
    "concept_3_drawback": {
        "title": "Concept 3: Duty Drawback Harvester",
        "subtitle": "19 U.S.C. § 1313(j) Unused Merchandise Drawback Matching",
        "filename": "nightmare_03_duty_drawback.pdf",
    },
    "concept_clean_fob": {
        "title": "Clean Production Invoice: Verified FOB Terms",
        "subtitle": "Baseline Clean Fixture (Demo) • No Valuation or Classification Findings",
        "filename": "clean_01_customs_fob.pdf",
    },
    "concept_4_sanctions": {
        "title": "Concept 4: OFAC 50% Rule & Entity Resolution",
        "subtitle": "31 CFR Chapter V Blocked-Ownership Aggregation & BIS Entity List",
        "filename": "nightmare_04_ofac_registry.pdf",
    },
}
# Backwards-compatible name used by the API layer.
NIGHTMARE_GROUND_TRUTH = SCENARIOS

# Which parsed field anchors each finding on the page.
_BBOX_KEYS: List[Tuple[str, Tuple[str, ...]]] = [
    ("disc-c1-01-insurance", ("insurance_charge", "incoterms")),
    ("disc-c1-01", ("freight_charge", "insurance_charge", "incoterms")),
    ("disc-c1-03", ("hts_misclassification",)),
    ("disc-c1-04-assists", ("unreported_assists",)),
    ("disc-c2-01", ("fuel_surcharge",)),
    ("disc-c2-02", ("chassis_split",)),
    ("disc-c2-0", ("detention",)),
    ("disc-c3-01", ("duties_paid", "import_entry")),
    ("disc-c3-02", ("export_bl",)),
    ("disc-c3-", ("import_entry",)),
    ("disc-c4-", ("entity_id", "entity_name")),
]


def _anchor_box(d: Discrepancy, bboxes: Dict[str, BoundingBox]) -> Optional[Tuple[str, BoundingBox]]:
    if d.id.startswith("disc-c1-02-line-"):
        line_no = str(d.metadata.get("line_number", ""))
        key = f"line_{int(line_no):03d}" if line_no.isdigit() else ""
        return (key, bboxes[key]) if key in bboxes else None
    for prefix, keys in _BBOX_KEYS:
        if d.id.startswith(prefix):
            for k in keys:
                if k in bboxes:
                    return k, bboxes[k]
            return None
    return None


_ROW_ANCHORS = ("line_", "hts_misclassification", "base_freight", "fuel_surcharge", "chassis_split", "detention")


def _padded(bb: BoundingBox, confidence: float, key: str = "") -> BoundingBox:
    if key.startswith(_ROW_ANCHORS):
        # Table rows: highlight the full row at the anchor's own vertical position.
        y = max(0.0, bb.y - 4.0)
        h = min(1000.0 - y, bb.height + 8.0)
        return BoundingBox(x=60.0, y=y, width=880.0, height=h, page_number=bb.page_number, confidence=confidence)
    x = max(0.0, bb.x - 6.0)
    y = max(0.0, bb.y - 4.0)
    w = min(1000.0 - x, bb.width + 12.0)
    h = min(1000.0 - y, bb.height + 8.0)
    return BoundingBox(x=x, y=y, width=w, height=h, page_number=bb.page_number, confidence=confidence)


def audit_sanctions_payload(payload: Dict[str, Any], as_of: date) -> Tuple[KillShotMetrics, List[Discrepancy]]:
    """OFAC 50% Rule evaluation for a target entity, with the dated IEEPA penalty maximum."""
    from app.services.sanctions_screener import sanctions_screener

    target_id = payload.get("entity_id")
    target_name = payload.get("name")
    if not target_id and target_name:
        match = sanctions_screener.match_entity(target_name)
        target_id = match.entity_id if match.matched and match.entity_id else target_name
    if not target_id:
        for party_key in ("shipper", "consignee", "buyer", "target_id"):
            if payload.get(party_key):
                target_id = payload.get(party_key)
                break
    target_id = target_id or "UNKNOWN_ENTITY"

    graph_resp = sanctions_screener.get_ownership_graph(target_id)
    eval_res = graph_resp.evaluation

    tx_value = optional_decimal(
        payload.get("transaction_value") or payload.get("dutiable_value") or payload.get("amount")
    )
    statutory_penalty = ieepa_max_penalty(tx_value, as_of.year)
    penalty_note = (
        f"IEEPA maximum for {as_of.year}: the greater of ${ieepa_max_penalty(None, as_of.year):,.2f} or twice the "
        + (f"${tx_value:,.2f} transaction value." if tx_value is not None else "transaction value (not stated, so the base amount is shown).")
    )
    region = BoundingBox(x=42.0, y=620.0, width=535.0, height=100.0, page_number=1, confidence=0.99)

    discrepancies: List[Discrepancy] = []
    if eval_res.is_blocked_by_50_percent_rule:
        if eval_res.blocking_entities:
            owners_summary = " and ".join(
                f"{b.get('ownership_pct', 0):g}% by {b.get('owner_name', b.get('owner_id'))}"
                for b in eval_res.blocking_entities
            )
            desc = f"Target entity {eval_res.target_entity_name} ({target_id}) is owned {owners_summary}. "
        else:
            desc = f"Target entity {eval_res.target_entity_name} ({target_id}) has "
        desc += (
            f"Aggregate blocked ownership is {eval_res.total_blocked_ownership_pct:g}%, so the entity is blocked "
            f"by operation of law under the OFAC 50 Percent Rule. {penalty_note}"
        )
        discrepancies.append(
            Discrepancy(
                id="disc-c4-01",
                concept_id="concept_4_sanctions",
                title=f"OFAC 50 Percent Rule: Aggregate Blocked Ownership ({eval_res.total_blocked_ownership_pct:g}%)",
                description=desc,
                severity="critical",
                confidence=0.99,
                bounding_box=region,
                statutory_code="31 CFR 501 / OFAC 50 Percent Rule guidance",
                exposure_amount=statutory_penalty,
                statutory_defense="Block the property, do not proceed, and report to OFAC within 10 business days (31 CFR 501.603).",
                metadata={
                    "target_id": target_id,
                    "blocked_ownership_pct": f"{eval_res.total_blocked_ownership_pct:g}%",
                    "compliance_action": eval_res.compliance_action,
                    "blocking_entities": eval_res.blocking_entities,
                    "penalty_basis": "50_USC_1705",
                    "penalty_year": as_of.year,
                },
            )
        )
    elif eval_res.direct_sdn_status:
        discrepancies.append(
            Discrepancy(
                id="disc-c4-sdn-direct",
                concept_id="concept_4_sanctions",
                title=f"OFAC SDN Direct Match: {eval_res.target_entity_name}",
                description=(
                    f"Target entity {eval_res.target_entity_name} ({target_id}) is on the SDN List; its property and "
                    f"interests in property are blocked. {penalty_note}"
                ),
                severity="critical",
                confidence=0.99,
                bounding_box=region,
                statutory_code="31 CFR Chapter V",
                exposure_amount=statutory_penalty,
                statutory_defense="Block and report (31 CFR 501.603).",
                metadata={"target_id": target_id, "direct_sdn": True, "compliance_action": eval_res.compliance_action,
                          "penalty_basis": "50_USC_1705", "penalty_year": as_of.year},
            )
        )
    elif eval_res.compliance_action in ("REQUIRES_MANUAL_REVIEW", "ENHANCED_DUE_DILIGENCE", "HOLD_INVESTIGATION", "COMPLIANCE_HOLD"):
        discrepancies.append(
            Discrepancy(
                id="disc-c4-unscreened-hold",
                concept_id="concept_4_sanctions",
                title=f"Compliance Hold: Ownership Not Verified ({eval_res.target_entity_name})",
                description=(
                    f"{eval_res.target_entity_name} ({target_id}) has no ownership record in the screening dataset. "
                    f"Hold for manual ownership verification before proceeding."
                ),
                severity="warning",
                confidence=0.50,
                exposure_amount=Decimal("0.00"),
                statutory_code="31 CFR Chapter V / compliance hold",
                statutory_defense="Obtain beneficial-ownership documentation and re-screen.",
                bounding_box=BoundingBox(x=42.0, y=620.0, width=535.0, height=100.0, page_number=1, confidence=0.50),
                metadata={"target_id": target_id, "compliance_action": eval_res.compliance_action, "review_required": True},
            )
        )

    penalty = sum((d.exposure_amount for d in discrepancies if d.severity == "critical"), Decimal("0.00"))
    return KillShotMetrics(penalty_exposure_avoided=penalty), discrepancies


class TradeDocumentExtractor:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY.strip() if settings.GEMINI_API_KEY else ""
        self.is_offline = not bool(self.api_key)

    def validate_document_firewall(self, payload: Dict[str, Any], concept_id: str) -> None:
        """Reject payloads that do not carry the structures a concept's rules need."""
        if not payload or not isinstance(payload, dict):
            raise ValueError("Pre-ingest document firewall rejected: empty or non-dict payload.")
        required = {
            "concept_1_customs": ("items", "misclassified_value", "dutiable_value", "unreported_assists"),
            "concept_clean_fob": ("items", "misclassified_value", "dutiable_value", "unreported_assists"),
            "concept_2_freight": ("base_freight", "chassis_split_fee", "detention_billed", "freight_charges"),
            "concept_3_drawback": ("duties_paid", "dutiable_value", "import_entry"),
            "concept_4_sanctions": ("entity_id", "name", "shipper", "consignee", "buyer", "target_id"),
        }.get(concept_id)
        if required and not any(k in payload for k in required):
            labels = {
                "concept_1_customs": "Customs firewall rejected: payload missing required invoice structures.",
                "concept_clean_fob": "Customs firewall rejected: payload missing required invoice structures.",
                "concept_2_freight": "Freight firewall rejected: payload missing required freight billing fields.",
                "concept_3_drawback": "Drawback firewall rejected: payload missing required duty drawback data.",
                "concept_4_sanctions": "Sanctions firewall rejected: payload missing target entity identifiers.",
            }
            raise ValueError(labels[concept_id])

    def _enrich_gri(self, payload: Dict[str, Any], discrepancies: List[Discrepancy]) -> None:
        if not ai_classifier.is_online:
            return
        try:
            items = payload.get("items") or []
            target_item = next((it for it in items if "8471" in str(it.get("hts_code", ""))), items[0] if items else {})
            gri = ai_classifier.analyze_gri_classification(
                item_description=target_item.get("description", "Electronic Processing Unit"),
                declared_hts=target_item.get("hts_code", "8471.30.0100"),
            )
            if gri:
                for d in discrepancies:
                    if "HTS" in d.title:
                        d.metadata["ai_gri_reasoning"] = gri.classification_rationale
                        d.metadata["gri_rules_applied"] = gri.gri_rules_applied
                        d.metadata["ai_model"] = settings.GEMINI_CLASSIFIER_MODEL
        except Exception as e:
            logger.warning("AI GRI reasoning enrichment failed: %s", e)

    def run_audit(
        self,
        concept_id: str,
        custom_payload: Optional[Dict[str, Any]] = None,
        *,
        parsed_document: Optional[ParsedDocument] = None,
        document_sha256: Optional[str] = None,
        document_filename: Optional[str] = None,
        as_of: Optional[date] = None,
    ) -> AuditResult:
        """
        Run the deterministic audit for one concept.

        - ``parsed_document``: an uploaded document already parsed (its own text, boxes and hash).
        - ``custom_payload``: an explicit payload (API callers and tests); no document is attached.
        - neither: parse the bundled fixture PDF for the concept.
        """
        if concept_id not in SCENARIOS:
            raise KeyError(f"Concept scenario '{concept_id}' not found in registered scenario catalogue.")
        scenario = SCENARIOS[concept_id]

        layout_boxes: List[Dict[str, Any]] = []
        bboxes: Dict[str, BoundingBox] = {}
        missing: List[str] = []
        source: Literal["fixture", "upload", "custom_payload"]

        if parsed_document is not None:
            source = "upload"
            payload = parsed_document.payload
            bboxes = parsed_document.bounding_boxes
            layout_boxes = parsed_document.metadata.get("layout_boxes", [])
            missing = parsed_document.missing_fields
            filename = document_filename or "uploaded.pdf"
            document_url = ""
            as_of = as_of or date.today()
        elif custom_payload is not None:
            source = "custom_payload"
            payload = custom_payload
            filename = document_filename or "payload.json"
            document_url = ""
            document_sha256 = document_sha256 or hashlib.sha256(canonical_json(payload)).hexdigest()
            as_of = as_of or parse_iso_date(payload.get("as_of_date")) or date.today()
        else:
            source = "fixture"
            pdf_path = os.path.join(settings.NIGHTMARES_DIR, scenario["filename"])
            parsed = parse_document(pdf_path, concept_id=concept_id)
            payload = parsed.payload
            bboxes = parsed.bounding_boxes
            layout_boxes = parsed.metadata.get("layout_boxes", [])
            missing = parsed.missing_fields
            filename = scenario["filename"]
            document_url = f"/api/v1/documents/{scenario['filename']}"
            document_sha256 = sha256_file(pdf_path)
            as_of = as_of or FIXTURE_AS_OF

        payload = dict(payload)
        payload.setdefault("as_of_date", as_of.isoformat())
        if concept_id == "concept_3_drawback":
            payload.setdefault("claim_date", as_of.isoformat())

        self.validate_document_firewall(payload, concept_id)

        if concept_id in ("concept_1_customs", "concept_clean_fob"):
            metrics, discrepancies = audit_customs_invoice(payload)
            self._enrich_gri(payload, discrepancies)
        elif concept_id == "concept_2_freight":
            metrics, discrepancies = audit_freight_bill(payload)
        elif concept_id == "concept_4_sanctions":
            metrics, discrepancies = audit_sanctions_payload(payload, as_of)
        else:
            metrics, discrepancies = audit_duty_drawback(payload)

        # Anchor each finding to text found in *this* document.
        for d in discrepancies:
            anchored = _anchor_box(d, bboxes)
            if anchored:
                key, bb = anchored
                d.bounding_box = _padded(bb, d.confidence, key)
                d.metadata["layout_verified"] = True
                d.metadata["layout_anchor"] = key
                d.metadata["bbox_source"] = "document_text"
            else:
                d.metadata["layout_verified"] = False
                d.metadata["bbox_source"] = "template_region" if layout_boxes else "none"
            d.metadata["extraction_source"] = source

        # Release gate: a document is released only when extraction is complete,
        # the currency is USD and no finding needs review.
        reasons: List[str] = []
        if missing:
            reasons.append("MISSING_REQUIRED_FIELDS")
        currency = payload.get("currency")
        if source != "custom_payload" and currency not in (None, "USD"):
            reasons.append("NON_USD_CURRENCY")
        if any(d.confidence < 0.85 or d.severity == "critical" for d in discrepancies):
            reasons.append("FINDINGS_REQUIRE_REVIEW")
        quarantine_status = "QUARANTINED" if reasons else "RELEASED"

        policy = default_engagement_policy()
        assert document_sha256 is not None
        run_digest = compute_run_digest(policy, document_sha256)

        return AuditResult(
            concept_id=concept_id,
            title=scenario["title"],
            subtitle=scenario["subtitle"],
            document_filename=filename,
            document_url=document_url,
            metrics=metrics,
            discrepancies=discrepancies,
            extracted_data=payload,
            offline_fallback_active=not ai_classifier.is_online,
            audit_run_id=f"RUN-{run_digest[:20].upper()}",
            run_digest=run_digest,
            document_sha256=document_sha256,
            ruleset_hash=RULESET_HASH,
            calc_version=CALC_VERSION,
            executed_at=datetime.now(timezone.utc).isoformat(),
            as_of_date=as_of.isoformat(),
            source=source,
            missing_fields=missing,
            quarantine_reasons=reasons,
            quarantine_status=quarantine_status,
            engagement_policy=policy,
        )


extractor_service = TradeDocumentExtractor()
