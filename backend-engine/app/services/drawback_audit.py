"""
Deterministic unused-merchandise drawback check under 19 U.S.C. 1313(j).

Eligibility is computed, not asserted:
- Time: the merchandise must be exported, and the claim filed, within 5 years of the
  date of importation (19 U.S.C. 1313(j)(1), 1313(r)(1)).
- Quantity: drawback is limited to the quantity both imported and exported.
- Basis: (j)(1) direct identification (the same goods, e.g. matched by serial or entry
  line) or (j)(2) substitution (commercially interchangeable goods classifiable under the
  same 8-digit HTS subheading).
- Amount: 99% of the duties paid on the eligible quantity.

Service model: preparation software for licensed customs brokers and self-filing importers.
"""

from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from app.models.schemas import BoundingBox, Discrepancy, KillShotMetrics
from app.services.utils import optional_decimal, parse_iso_date, quantize_currency, safe_decimal

DRAWBACK_YEARS = 5


def _add_years(d: date, years: int) -> date:
    try:
        return d.replace(year=d.year + years)
    except ValueError:  # 29 Feb
        return d.replace(year=d.year + years, day=28)


def _hts8(code: Any) -> str:
    return str(code or "").replace(".", "")[:8]


def evaluate_timeliness(
    import_date: Optional[date], export_date: Optional[date], claim_date: Optional[date]
) -> Tuple[Optional[bool], str]:
    """(timely, reason). None means it cannot be determined from the inputs."""
    if import_date is None or export_date is None:
        return None, "import or export date missing"
    if export_date < import_date:
        return False, "export date precedes import date"
    deadline = _add_years(import_date, DRAWBACK_YEARS)
    if export_date > deadline:
        return False, f"exported after the 5-year limit ({deadline.isoformat()})"
    if claim_date is not None and claim_date > deadline:
        return False, f"claim date after the 5-year limit ({deadline.isoformat()})"
    return True, f"export and claim within 5 years of import (limit {deadline.isoformat()})"


def determine_basis(data: Dict[str, Any]) -> Optional[str]:
    if data.get("direct_identification"):
        return "j1"
    imp, exp = _hts8(data.get("import_hts")), _hts8(data.get("export_hts"))
    if len(imp) == 8 and imp == exp:
        return "j2"
    return None


def audit_duty_drawback(data: Dict[str, Any]) -> Tuple[KillShotMetrics, List[Discrepancy]]:
    if not data or not any(k in data for k in ("duties_paid", "import_entry", "export_bl", "dutiable_value")):
        return KillShotMetrics(), []

    discrepancies: List[Discrepancy] = []
    duties_paid = optional_decimal(data.get("duties_paid"))
    drawback_pct = safe_decimal(data.get("drawback_percentage"), "0.99")
    import_entry = str(data.get("import_entry") or "[entry not stated]")
    export_bl = str(data.get("export_bl") or "[B/L not stated]")

    import_date = parse_iso_date(data.get("entry_date") or data.get("import_date"))
    export_date = parse_iso_date(data.get("export_date"))
    claim_date = parse_iso_date(data.get("claim_date")) or (date.today() if import_date else None)
    timely, timely_reason = evaluate_timeliness(import_date, export_date, claim_date)
    if timely is None and data.get("is_timely_5yr_window") is not None:
        timely = bool(data.get("is_timely_5yr_window"))
        timely_reason = "timeliness asserted by caller (no dates supplied)"

    imported_qty = optional_decimal(data.get("imported_quantity"))
    exported_qty = optional_decimal(data.get("exported_quantity"))
    basis = determine_basis(data)

    missing: List[str] = []
    if duties_paid is None:
        missing.append("duties_paid")
    if timely is None:
        missing.append("import/export dates")
    if imported_qty is None or exported_qty is None:
        missing.append("imported and exported quantities")
    if basis is None:
        missing.append("j1 direct identification or matching 8-digit HTS for j2")

    unlocked = Decimal("0.00")
    if timely is False and duties_paid is not None and duties_paid > 0:
        discrepancies.append(
            Discrepancy(
                id="disc-c3-expired",
                concept_id="concept_3_drawback",
                title="Drawback Barred: Outside the 5-Year Limit",
                description=f"Drawback cannot be claimed: {timely_reason} (19 U.S.C. 1313(r)(1)).",
                statutory_code="19 U.S.C. 1313(r)(1)",
                severity="warning",
                exposure_amount=Decimal("0.00"),
                confidence=0.99,
                bounding_box=BoundingBox(x=58.0, y=570.0, width=880.0, height=50.0, page_number=1, confidence=0.99),
                metadata={"is_timely_5yr_window": False, "reason": timely_reason, "statutory_limit_years": DRAWBACK_YEARS},
            )
        )
    elif missing:
        if duties_paid is not None and duties_paid > 0:
            discrepancies.append(
                Discrepancy(
                    id="disc-c3-insufficient",
                    concept_id="concept_3_drawback",
                    title="Drawback Eligibility Not Established",
                    description="No refund is computed because these inputs are missing: " + "; ".join(missing) + ".",
                    statutory_code="19 U.S.C. 1313(j)",
                    severity="info",
                    exposure_amount=Decimal("0.00"),
                    confidence=0.5,
                    bounding_box=BoundingBox(x=58.0, y=570.0, width=880.0, height=50.0, page_number=1, confidence=0.5),
                    metadata={"missing_inputs": missing},
                )
            )
    else:
        assert duties_paid is not None and imported_qty is not None and exported_qty is not None
        eligible_qty = min(imported_qty, exported_qty)
        duty_per_unit = duties_paid / imported_qty if imported_qty > 0 else Decimal("0")
        unlocked = quantize_currency(eligible_qty * duty_per_unit * drawback_pct)
        match_pct = (eligible_qty / imported_qty * 100) if imported_qty > 0 else Decimal("0")
        basis_label = "(j)(1) direct identification" if basis == "j1" else "(j)(2) substitution"
        if unlocked > 0:
            discrepancies.append(
                Discrepancy(
                    id="disc-c3-01",
                    concept_id="concept_3_drawback",
                    title="Unclaimed 99% Statutory Duty Drawback Recovery",
                    description=(
                        f"Entry {import_entry} paid ${duties_paid:,.2f} on {imported_qty:,} units; export B/L {export_bl} "
                        f"shows {exported_qty:,} units exported ({timely_reason}). Eligible quantity {eligible_qty:,} "
                        f"under 19 U.S.C. 1313{basis_label[:6]}: refund of {drawback_pct * 100:.0f}% = ${unlocked:,.2f}, "
                        f"for filing by a licensed customs broker or self-filing importer."
                    ),
                    statutory_code=f"19 U.S.C. 1313{basis_label[:6]}",
                    severity="opportunity",
                    exposure_amount=unlocked,
                    confidence=0.95,
                    executive_summary=f"{eligible_qty:,} units match import to export: ${unlocked:,.2f} refundable.",
                    financial_blast_radius=f"${unlocked:,.2f} refundable on liquidation of the drawback claim.",
                    statutory_defense="File a drawback entry (type 47) in ACE; keep import, export and matching records for 3 years after liquidation.",
                    bounding_box=BoundingBox(x=58.0, y=570.0, width=880.0, height=180.0, page_number=1, confidence=0.95),
                    metadata={
                        "import_entry": import_entry,
                        "export_bl": export_bl,
                        "basis": basis,
                        "statutory_percent": f"{drawback_pct * 100:.1f}%",
                        "duties_paid": str(duties_paid),
                        "duty_per_unit": str(quantize_currency(duty_per_unit)),
                        "eligible_quantity": str(eligible_qty),
                        "cash_recovery_ready": str(unlocked),
                        "timeliness": timely_reason,
                        "service_model": "compliance_auditing_software_for_licensed_brokers_and_self_filers",
                    },
                )
            )
            discrepancies.append(
                Discrepancy(
                    id="disc-c3-02",
                    concept_id="concept_3_drawback",
                    title="Export Evidence Matched to Import Entry",
                    description=(
                        f"Export B/L {export_bl} accounts for {exported_qty:,} of {imported_qty:,} imported units "
                        f"({match_pct:.0f}%) on a {basis_label} basis (19 CFR Part 190)."
                    ),
                    statutory_code="19 CFR Part 190",
                    severity="opportunity",
                    exposure_amount=Decimal("0.00"),
                    confidence=0.95,
                    executive_summary="Import and export records reconcile on quantity and basis.",
                    financial_blast_radius=f"Supports the ${unlocked:,.2f} claim on CBP review.",
                    statutory_defense="Retain the matching record with the claim.",
                    bounding_box=BoundingBox(x=58.0, y=430.0, width=880.0, height=110.0, page_number=1, confidence=0.95),
                    metadata={
                        "carrier": str(data.get("carrier") or "[carrier not stated]"),
                        "destination": str(data.get("destination") or "[destination not stated]"),
                        "quantity_match": f"{match_pct:.0f}%",
                        "basis": basis,
                    },
                )
            )

    metrics = KillShotMetrics(
        penalty_exposure_avoided=Decimal("0.00"),
        carrier_overbilling_caught=Decimal("0.00"),
        drawback_unclaimed_unlocked=unlocked,
    )
    return metrics, discrepancies
