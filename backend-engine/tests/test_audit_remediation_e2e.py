"""
E2E Opaque-Box Remediation Test Suite for Trade Systems Studio
=============================================================
This test suite verifies compliance with:
- ORIGINAL_REQUEST.md (Critical C1-C5, High H1-H10, Medium M1-M13, Low L1-L8)
- PROJECT.md (Interface Contracts 1-4)
- TEST_INFRA.md (4-Tier Testing Model & Scenarios S1-S6)
- Statutory International Trade Law:
    * 19 U.S.C. § 1401a & 19 CFR § 152.103 (US Customs Valuation & CIF deductions)
    * 19 U.S.C. § 1592 (Statutory Penalties for Negligence & Gross Negligence)
    * 19 U.S.C. § 1313 (Statutory 99% Duty Drawback Matching)
    * 19 CFR § 24.23 (FY2025 MPF Statutory Caps: $32.71 min, $634.62 max, 0.3464% rate)
    * 19 CFR § 24.24 (Harbor Maintenance Fee: 0.125% ocean, $0 air/truck)
    * 31 CFR Part 501 / OFAC 50% Rule (Aggregated Blocked Ownership)
    * 15 CFR Part 744 (EAR / BIS Entity List Export Controls)
    * FMC 46 CFR § 545.5 / OSRA 2022 (Demurrage & Port Free Time Rules)
    * 19 CFR § 162.74 (Statutory Prior Disclosure Mitigation & Interest Calculation)
"""

import json
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.models.hts_models import (
    ClassificationRequest,
)
from app.models.schemas import (
    BoundingBox,
    Discrepancy,
    KillShotMetrics,
)
from app.services.customs_audit import (
    audit_customs_invoice,
    calculate_1592_penalties,
)
from app.services.drawback_audit import audit_duty_drawback
from app.services.freight_audit import audit_freight_bill
from app.services.hts_classifier import (
    HTSClassifierEngine,
    calculate_landed_cost,
)
from app.services.layout_extractor import DocumentLayoutExtractor
from app.services.sanctions_screener import (
    SanctionsScreener,
    sanctions_screener,
)
from app.services.utils import quantize_currency, safe_decimal
from app.services.valuation_ledger import CustomsValuationService
from main import app

# Shared TestClient for API endpoints
client = TestClient(app)



def full_drawback(duties_paid: str, **overrides):
    """A complete (j)(1) unused-merchandise claim: dates, quantities and direct identification."""
    payload = {
        "import_entry": "CBP-7501-84920184",
        "export_bl": "BGFU-0941824",
        "entry_date": "2024-01-15",
        "export_date": "2024-03-10",
        "claim_date": "2026-11-20",
        "duties_paid": duties_paid,
        "imported_quantity": "1000",
        "exported_quantity": "1000",
        "direct_identification": True,
        "drawback_percentage": "0.99",
    }
    payload.update(overrides)
    return payload


def eu_corridor_xml() -> str:
    """UniversalShipment XML for a Durban -> Rotterdam (non-US) corridor."""
    from app.services.cargowise_xml import cargowise_exporter

    return cargowise_exporter.generate_universal_interchange_xml(port_origin_code="ZADUR", port_dest_code="NLRTM")


# Path to ground truth PDF fixtures
FIXTURES_DIR = Path(__file__).parent.parent / "app" / "data" / "nightmares"


# ==============================================================================
# TIER 1: FEATURE EQUIVALENCE CLASS COVERAGE (F1 through F10)
# ==============================================================================

class TestTier1FeatureCoverage:
    """
    Tier 1: Feature Coverage (≥5 tests per feature, total ≥50 tests).
    Verifies functional correctness and interface contracts across all 10 feature areas.
    """

    # --------------------------------------------------------------------------
    # F1: Grounded Document Extraction & Layout Verification
    # --------------------------------------------------------------------------

    def test_f1_01_nightmare_pdf_fixture_exists_and_non_empty(self):
        """F1.1: Verify real PDF test fixture exists on disk and is non-empty."""
        pdf_path = FIXTURES_DIR / "nightmare_01_customs_ci.pdf"
        assert pdf_path.exists(), f"Fixture missing: {pdf_path}"
        assert pdf_path.stat().st_size > 0, "Fixture file is empty"

    def test_f1_02_layout_extractor_normalizes_to_1000_grid(self):
        """F1.2: Verify extracted layout bounding boxes are normalized to [0, 1000) space."""
        pdf_path = FIXTURES_DIR / "nightmare_01_customs_ci.pdf"
        extractor = DocumentLayoutExtractor()
        boxes = extractor.extract_bounding_boxes(str(pdf_path))
        assert len(boxes) > 0, "Layout extractor returned no bounding boxes"
        for item in boxes:
            bbox: BoundingBox = item["bounding_box"]
            assert 0.0 <= bbox.x <= 1000.0, f"bbox.x out of range: {bbox.x}"
            assert 0.0 <= bbox.y <= 1000.0, f"bbox.y out of range: {bbox.y}"
            assert bbox.x + bbox.width <= 1000.0, f"bbox extends past width 1000: {bbox.x + bbox.width}"
            assert bbox.y + bbox.height <= 1000.0, f"bbox extends past height 1000: {bbox.y + bbox.height}"

    def test_f1_03_layout_extractor_extracts_actual_tokens(self):
        """F1.3: Verify layout extractor yields real extracted text tokens from document."""
        pdf_path = FIXTURES_DIR / "nightmare_01_customs_ci.pdf"
        extractor = DocumentLayoutExtractor()
        boxes = extractor.extract_bounding_boxes(str(pdf_path))
        all_text = " ".join(item.get("text", "") for item in boxes)
        assert len(all_text.strip()) > 0, "Extracted layout contains zero text"
        assert "INVOICE" in all_text.upper() or "COMMERCIAL" in all_text.upper() or "DSP" in all_text

    def test_f1_04_bounding_box_validates_strict_1000_extent(self):
        """F1.4: Verify BoundingBox model enforces the [0, 1000) coordinate system."""
        # Valid boundary box
        valid_box = BoundingBox(x=900.0, y=900.0, width=100.0, height=100.0, page_number=1, confidence=0.95)
        assert valid_box.x + valid_box.width == 1000.0

        # Invalid box exceeding width
        with pytest.raises(Exception):
            BoundingBox(x=950.0, y=100.0, width=60.0, height=50.0, page_number=1, confidence=0.95)

        # Invalid box exceeding height
        with pytest.raises(Exception):
            BoundingBox(x=100.0, y=950.0, width=50.0, height=60.0, page_number=1, confidence=0.95)

    def test_f1_05_layout_extractor_handles_missing_file_without_fabrication(self):
        """F1.5: Verify layout extractor returns empty list for nonexistent file path."""
        extractor = DocumentLayoutExtractor()
        boxes = extractor.extract_bounding_boxes("app/data/nightmares/does_not_exist.pdf")
        assert boxes == [], "Extractor fabricated layout boxes for nonexistent file"

    # --------------------------------------------------------------------------
    # F2: Empty Input & Missing Field Validation
    # --------------------------------------------------------------------------

    def test_f2_01_customs_audit_empty_payload_returns_zero_exposure(self):
        """F2.1: Calling audit_customs_invoice with empty dict returns $0.00 exposure and 0 findings."""
        metrics, discrepancies = audit_customs_invoice({})
        assert metrics.penalty_exposure_avoided == Decimal("0.00"), "Empty input fabricated penalty exposure"
        assert len(discrepancies) == 0, f"Empty input fabricated {len(discrepancies)} findings"

    def test_f2_02_freight_audit_empty_payload_returns_zero_exposure(self):
        """F2.2: Calling audit_freight_bill with empty dict returns $0.00 overbilling and 0 findings."""
        metrics, discrepancies = audit_freight_bill({})
        assert metrics.carrier_overbilling_caught == Decimal("0.00"), "Empty input fabricated carrier overbilling"
        assert len(discrepancies) == 0, f"Empty input fabricated {len(discrepancies)} findings"

    def test_f2_03_drawback_audit_empty_payload_returns_zero_drawback(self):
        """F2.3: Calling audit_duty_drawback with empty dict returns $0.00 drawback and 0 findings."""
        metrics, discrepancies = audit_duty_drawback({})
        assert metrics.drawback_unclaimed_unlocked == Decimal("0.00"), "Empty input fabricated duty drawback unlock"
        assert len(discrepancies) == 0, f"Empty input fabricated {len(discrepancies)} findings"

    def test_f2_04_all_engines_empty_input_sum_to_zero_dollars(self):
        """F2.4: Sum of fabricated findings across all three engines on empty input must equal exactly $0.00."""
        m_cust, _ = audit_customs_invoice({})
        m_frt, _ = audit_freight_bill({})
        m_drw, _ = audit_duty_drawback({})
        total_fabricated = (
            m_cust.penalty_exposure_avoided
            + m_frt.carrier_overbilling_caught
            + m_drw.drawback_unclaimed_unlocked
        )
        assert total_fabricated == Decimal("0.00"), f"Total fabricated exposure on empty input was ${total_fabricated}"

    def test_f2_05_customs_audit_parties_only_no_items_yields_zero_penalty(self):
        """F2.5: Invoice with trading parties but no items, value, or invoice number yields 0 exposure."""
        payload = {"shipper": "Clean Shipper Ltd", "consignee": "Clean Consignee Corp"}
        metrics, discrepancies = audit_customs_invoice(payload)
        assert metrics.penalty_exposure_avoided == Decimal("0.00")
        assert len(discrepancies) == 0

    # --------------------------------------------------------------------------
    # F3: Autonomous HTS Classification & Word Boundaries
    # --------------------------------------------------------------------------

    def test_f3_01_unrelated_goods_bananas_not_defaulted_to_drone_motor(self):
        """F3.1: Bananas must NOT default to drone motor (8501.31.8000) at 94% confidence."""
        req = ClassificationRequest(
            product_title="Fresh Cavendish Bananas",
            product_description="Grade A edible fresh yellow bananas from Ecuador",
            entered_value=Decimal("5000.00"),
        )
        res = HTSClassifierEngine().classify(req)
        is_drone_default = (res.classified_hts_code == "8501.31.8000" and res.confidence >= 0.85 and not res.requires_human_review)
        assert not is_drone_default, "Unrelated fruit was classified as drone motor with high confidence"

    def test_f3_02_unrelated_goods_tshirt_requires_human_review(self):
        """F3.2: Unrelated clothing item must require human review (confidence < 0.85 or explicit review flag)."""
        req = ClassificationRequest(
            product_title="100% Organic Cotton Crewneck T-Shirt",
            product_description="Men's casual knitted cotton apparel",
            entered_value=Decimal("12000.00"),
        )
        res = HTSClassifierEngine().classify(req)
        assert res.requires_human_review is True, "Unrelated apparel should flag requires_human_review=True"

    def test_f3_03_word_boundary_esc_in_telescope_does_not_match_drone_esc(self):
        """F3.3: 'telescope' contains 'esc' as a substring but must NOT match drone electronic speed controller."""
        req = ClassificationRequest(
            product_title="Astronomical Refractor Telescope",
            product_description="High-power optical telescope with tripod for celestial observation",
            entered_value=Decimal("3500.00"),
        )
        res = HTSClassifierEngine().classify(req)
        assert res.classified_hts_code != "8501.31.8000", "Substring 'esc' in 'telescope' incorrectly triggered drone motor"

    def test_f3_04_word_boundary_esc_in_description_does_not_match_drone_esc(self):
        """F3.4: 'description' contains 'esc' as a substring but must NOT match drone electronic speed controller."""
        req = ClassificationRequest(
            product_title="Industrial Storage Steel Rack",
            product_description="Heavy duty warehouse storage shelving with technical description document",
            entered_value=Decimal("4500.00"),
        )
        res = HTSClassifierEngine().classify(req)
        assert res.classified_hts_code != "8501.31.8000", "Substring 'esc' in 'description' incorrectly triggered drone motor"

    def test_f3_05_landed_cost_statutory_mpf_fy2025_statutory_caps(self):
        """F3.5: Landed cost calculator must use active FY2027 MPF caps ($34.58 min, $670.86 max) with FY2025 support."""
        # Active FY2027 default
        landed_low = calculate_landed_cost(
            entered_value=Decimal("5000.00"),
            duty_rate_ad_valorem=Decimal("0.00"),
            is_ocean_freight=False,
        )
        assert landed_low.mpf_min_cap == Decimal("34.58"), f"Stale MPF minimum cap: expected $34.58, got {landed_low.mpf_min_cap}"
        assert landed_low.mpf_max_cap == Decimal("670.86"), f"Stale MPF maximum cap: expected $670.86, got {landed_low.mpf_max_cap}"
        assert landed_low.mpf_fee == Decimal("34.58"), f"MPF fee below minimum cap: got {landed_low.mpf_fee}"

        # FY2025 compatibility
        landed_fy25 = calculate_landed_cost(
            entered_value=Decimal("5000.00"),
            duty_rate_ad_valorem=Decimal("0.00"),
            is_ocean_freight=False,
            fiscal_year="FY2025",
        )
        assert landed_fy25.mpf_fee == Decimal("32.71")

        # High value test: $1,000,000 * 0.003464 = $3,464.00, above ceiling -> clamped to max cap
        landed_high = calculate_landed_cost(
            entered_value=Decimal("1000000.00"),
            duty_rate_ad_valorem=Decimal("0.00"),
            is_ocean_freight=False,
        )
        assert landed_high.mpf_fee == Decimal("670.86"), f"MPF fee above maximum cap: got {landed_high.mpf_fee}"

    def test_f3_06_adversarial_non_motor_goods_require_broker_review(self):
        """F3.6: Verify unrelated goods with isolated keywords do not classify as drone motors (C3 Challenger Fix)."""
        engine = HTSClassifierEngine()
        unrelated_cases = [
            ("Brushless Art Painting", "Modern abstract oil painting created without brushes"),
            ("Brushless Shaving Cream", "Sensitive skin shaving foam"),
            ("Synthetic Motor Oil 5W-30", "Automotive engine lubrication oil"),
            ("ESC Mechanical Keyboard Keycap", "Polycarbonate escape key replacement"),
            ("Toy UAV Glider", "Unpowered lightweight balsa wood toy glider"),
            ("White Lithium Grease", "Industrial mechanical lubricant"),
            ("Vintage GPU Silicon Graphic T-Shirt", "Cotton novelty apparel"),
        ]
        for title, desc in unrelated_cases:
            req = ClassificationRequest(product_title=title, product_description=desc, entered_value=Decimal("500.00"))
            res = engine.classify(req)
            assert res.requires_human_review is True, f"Bypassed human review: {title}"
            assert res.classified_hts_code == "REQUIRES_BROKER_REVIEW", f"Miscalibrated HTS code: {title} -> {res.classified_hts_code}"
            assert res.confidence == 0.0

    # --------------------------------------------------------------------------
    # F4: Fail-Closed Sanctions Screening & Cycle-Safe Graph
    # --------------------------------------------------------------------------

    def test_f4_01_unknown_entity_fails_closed_to_unscreened_or_hold(self):
        """F4.1: Unknown entity query must fail closed to UNSCREENED or COMPLIANCE_HOLD, never CLEAN_COMMERCIAL."""
        graph = sanctions_screener.get_ownership_graph("completely_unknown_entity_99999")
        target_node = graph.nodes[0]
        assert target_node.risk_level in ("UNSCREENED", "COMPLIANCE_HOLD"), (
            f"Unknown entity failed open with risk_level: {target_node.risk_level}"
        )

    def test_f4_02_unknown_entity_requires_manual_review_action(self):
        """F4.2: Unknown entity compliance action must be REQUIRES_MANUAL_REVIEW, never CLEAR_TRANSACTION."""
        graph = sanctions_screener.get_ownership_graph("completely_unknown_entity_99999")
        action = graph.evaluation.compliance_action
        assert action == "REQUIRES_MANUAL_REVIEW", (
            f"Unknown entity failed open with compliance action: {action}"
        )

    def test_f4_03_known_sdn_entity_returns_blocked_status(self):
        """F4.3: Direct OFAC SDN entity (Apex Ocean Logistics) returns SDN_BLOCKED and BLOCK_AND_REPORT."""
        graph = sanctions_screener.get_ownership_graph("ofac-sdn-ir-0382")
        eval_res = graph.evaluation
        assert eval_res.is_blocked_by_50_percent_rule is True or eval_res.direct_sdn_status is True
        assert eval_res.compliance_action == "BLOCK_AND_REPORT"

    def test_f4_04_bis_entity_list_distinguished_from_ofac_sdn(self):
        """F4.4: BIS Entity List entities (Global Micro Electronics) are distinguished from OFAC SDN blocking."""
        match = sanctions_screener.match_entity("Global Micro Electronics Ltd")
        assert match.matched is True
        assert any("BIS Entity List" in p or "EAR" in p for p in match.programs), "BIS programs missing"
        # Must not falsely cite OFAC SDN program for a purely BIS listed entity
        assert not any("OFAC SDN" in p for p in match.programs), "BIS entity misidentified as OFAC SDN"

    def test_f4_05_ofac_50_percent_rule_aggregation_blocks_majority_owned(self):
        """F4.5: Entity owned 25% + 30% = 55% by SDNs is blocked under the OFAC 50% Rule (31 CFR Part 501)."""
        graph = sanctions_screener.get_ownership_graph("bis-el-cn-0941")
        assert graph.evaluation.total_blocked_ownership_pct == 55.0
        assert graph.evaluation.is_blocked_by_50_percent_rule is True
        assert graph.evaluation.compliance_action == "BLOCK_AND_REPORT"

    def test_f4_06_dynamic_concept_4_sanctions_audit_clean_vs_blocked(self):
        """F4.6: Verify extractor.run_audit dynamically screens concept_4_sanctions entities (Auditor Finding 1)."""
        from app.services.extractor import TradeDocumentExtractor
        extractor = TradeDocumentExtractor()

        # Blocked target (bis-el-cn-0941)
        res_blocked = extractor.run_audit("concept_4_sanctions")
        assert res_blocked.metrics.penalty_exposure_avoided == Decimal("377700.00")
        assert len(res_blocked.discrepancies) == 1
        assert "55%" in res_blocked.discrepancies[0].title
        assert "Victor Petrov" in res_blocked.discrepancies[0].description

        # Clean target (pacific-apex-01)
        res_clean = extractor.run_audit("concept_4_sanctions", custom_payload={"entity_id": "pacific-apex-01", "name": "Pacific Apex Corp"})
        assert res_clean.metrics.penalty_exposure_avoided == Decimal("0.00")
        assert len(res_clean.discrepancies) == 0

        # Unknown entity: a caller-supplied "CLEAR_TRANSACTION" must not clear it (fail closed)
        res_probe = extractor.run_audit("concept_4_sanctions", custom_payload={
            "entity_id": "completely-clean-entity",
            "name": "Completely Clean Co",
            "aggregate_blocked_pct": "0.0",
            "action": "CLEAR_TRANSACTION"
        })
        assert res_probe.metrics.penalty_exposure_avoided == Decimal("0.00")
        assert [d.id for d in res_probe.discrepancies] == ["disc-c4-unscreened-hold"]
        assert res_probe.quarantine_status == "QUARANTINED"

    # --------------------------------------------------------------------------
    # F5: US Valuation & CIF Marine Insurance Deductions (H1, 19 USC 1401a / 19 CFR 152.103)
    # --------------------------------------------------------------------------

    def test_f5_01_cif_marine_insurance_deducted_under_19usc1401a(self):
        """F5.1: Under 19 U.S.C. § 1401a(b)(4)(A), international freight and insurance are excluded from dutiable value."""
        payload = {
            "incoterms": "CIF LOS ANGELES",
            "insurance_charge": "0.00",
            "freight_charge": "1200.00",
            "items": [{"line_number": 1, "quantity": "100", "unit_price": "10.00", "stated_total": "1000.00"}]
        }
        _, discrepancies = audit_customs_invoice(payload)
        cif_disc = next((d for d in discrepancies if "CIF" in d.title or "152.103" in d.statutory_code), None)
        assert cif_disc is not None, "Missing CIF marine insurance audit finding"
        # Under US law, omitted deduction causes duty overpayment, not an underpayment penalty
        desc = (cif_disc.description + " " + (cif_disc.financial_blast_radius or "")).lower()
        assert "overstatement" in desc or "overpayment" in desc or "deduction" in desc

    def test_f5_02_customs_valuation_service_calculates_cif_overvaluation(self):
        """F5.2: CustomsValuationService identifies freight and insurance as non-dutiable CIF deductions."""
        service = CustomsValuationService()
        audit = service.audit_entry_valuation(
            invoice_incoterm="CIF Los Angeles",
            international_freight_in_invoice=Decimal("24500.00"),
            marine_insurance_in_invoice=Decimal("3200.00"),
        )
        assert audit.improper_cif_overvaluation == Decimal("27700.00"), (
            f"CIF freight + insurance deduction mismatch: expected 27700.00, got {audit.improper_cif_overvaluation}"
        )

    def test_f5_03_fob_terms_have_zero_cif_insurance_deduction(self):
        """F5.3: Invoices on FOB terms have $0.00 CIF deduction overvaluation."""
        service = CustomsValuationService()
        audit = service.audit_entry_valuation(
            invoice_incoterm="FOB Yantian",
            international_freight_in_invoice=Decimal("0.00"),
            marine_insurance_in_invoice=Decimal("0.00"),
        )
        assert audit.improper_cif_overvaluation == Decimal("0.00")

    def test_f5_04_valuation_adds_undeclared_assists_under_19cfr152(self):
        """F5.4: Statutory assists (tooling, overseas engineering) are correctly added to dutiable value."""
        service = CustomsValuationService()
        audit = service.audit_entry_valuation()
        assert audit.assists_omitted_cost > Decimal("0.00"), "Assists omitted cost should be non-zero"
        # Adjusted lawful value = declared - CIF deductions + assists
        expected_adjusted = audit.declared_transaction_value - audit.improper_cif_overvaluation + audit.assists_omitted_cost
        assert audit.adjusted_lawful_dutiable_value == expected_adjusted

    def test_f5_05_cif_overvaluation_does_not_trigger_1592_penalty(self):
        """F5.5: CIF insurance omission (value overstatement) does not create 19 U.S.C. § 1592 underpayment penalty."""
        payload = {
            "incoterms": "CIF LOS ANGELES",
            "insurance_charge": "0.00",
            "misclassified_value": "0.00",
            "declared_duty_rate": "0.00",
            "lawful_duty_rate": "0.00",
            "items": [{"line_number": 1, "quantity": "10", "unit_price": "100.00", "stated_total": "1000.00"}]
        }
        metrics, _ = audit_customs_invoice(payload)
        assert metrics.penalty_exposure_avoided == Decimal("0.00"), (
            "CIF insurance overstatement incorrectly added to 1592 underpayment penalty exposure"
        )

    def test_f5_06_dynamic_cif_freight_exposure_calculation(self):
        """F5.6: Verify CIF missing insurance exposure derives dynamically from freight charge (Auditor Finding 2)."""
        # Probe 1: $99,999.00 freight
        payload_large = {
            "incoterms": "CIF LOS ANGELES",
            "insurance_charge": "0.00",
            "freight_charge": "99999.00",
            "items": [{"line_number": 1, "quantity": "10", "unit_price": "100.00", "stated_total": "1000.00"}]
        }
        _, disc_large = audit_customs_invoice(payload_large)
        cif_large = next(d for d in disc_large if "CIF" in d.title)
        assert cif_large.metadata["non_dutiable_charges"] == "99999.00"
        assert "$99,999.00" in cif_large.description
        assert cif_large.exposure_amount == Decimal("0.00")  # line duty rate unknown: no guessed rate

        # Probe 2: $450.50 freight
        payload_small = {
            "incoterms": "CIF LOS ANGELES",
            "insurance_charge": "0.00",
            "freight_charge": "450.50",
            "items": [{"line_number": 1, "quantity": "10", "unit_price": "100.00", "stated_total": "1000.00"}]
        }
        _, disc_small = audit_customs_invoice(payload_small)
        cif_small = next(d for d in disc_small if "CIF" in d.title)
        assert cif_small.metadata["non_dutiable_charges"] == "450.50"
        assert "$450.50" in cif_small.description

    # --------------------------------------------------------------------------
    # F6: Corridor Jurisdiction & Statutory Penalties (H2, 19 USC 1592)
    # --------------------------------------------------------------------------

    def test_f6_01_zadur_to_nlrtm_corridor_rejects_19usc1592_penalties(self):
        """F6.1: Shipment from Durban (ZADUR) to Rotterdam (NLRTM) is governed by EU law, rejecting US 1592 penalties."""
        xml = eu_corridor_xml()
        assert "19_USC_1592" not in xml, "Corridor ZADUR -> NLRTM incorrectly tagged with US 19 U.S.C. 1592"

    def test_f6_02_scenarios_endpoint_marks_durban_rotterdam_as_eu_ucc(self):
        """F6.2: Scenario ZADUR -> NLRTM must cite EU Union Customs Code (UCC) or EU customs jurisdiction."""
        assert "EU_UCC_COMPLIANT" in eu_corridor_xml()

    def test_f6_03_us_inbound_corridor_applies_1592_penalties(self):
        """F6.3: US-bound sample (Yantian -> Los Angeles) cites 19 U.S.C. § 1592; amounts come from the engine."""
        res = client.get("/api/v1/scenarios")
        assert all(s["default_exposure_usd"] != "0.00" for s in res.json())
        lax = next(s for s in res.json() if s.get("id") == "scenario_long_beach_battery")
        assert "19 U.S.C. § 1592" in lax.get("statute", ""), "US inbound corridor must cite 19 U.S.C. § 1592"

    def test_f6_04_1592_negligence_statutory_multiplier_range(self):
        """F6.4: 19 U.S.C. 1592(c)(3): negligence maximum is 2x the loss of duty."""
        loss = Decimal("10000.00")
        penalties = calculate_1592_penalties(loss)
        assert penalties["negligence"] == Decimal("20000.00")

    def test_f6_05_1592_gross_negligence_statutory_multiplier_range(self):
        """F6.5: 19 U.S.C. 1592(c)(2): gross negligence maximum is 4x the loss of duty."""
        loss = Decimal("10000.00")
        penalties = calculate_1592_penalties(loss)
        assert penalties["gross_negligence"] == Decimal("40000.00")

    # --------------------------------------------------------------------------
    # F7: Legal Representation & Statutory Disclaimers
    # --------------------------------------------------------------------------

    def test_f7_01_prior_disclosure_contains_draft_review_watermark(self):
        """F7.1: Prior Disclosure letter contains mandatory DRAFT review watermark."""
        service = CustomsValuationService()
        audit = service.audit_entry_valuation()
        pd = service.generate_prior_disclosure(audit)
        letter = pd.letter_text
        assert "DRAFT" in letter, "Prior disclosure missing DRAFT watermark"
        assert "LICENSED CUSTOMS BROKER OR LEGAL COUNSEL" in letter, (
            "Prior disclosure missing required licensed customs broker / legal counsel review disclaimer"
        )

    def test_f7_02_prior_disclosure_omits_counsel_of_record_claims(self):
        """F7.2: Generated Prior Disclosure does NOT claim platform acts as Counsel of Record or Special Counsel."""
        service = CustomsValuationService()
        audit = service.audit_entry_valuation()
        pd = service.generate_prior_disclosure(audit)
        letter = pd.letter_text
        assert "Counsel of Record" not in letter, "Letter falsely claims Counsel of Record status"
        assert "Special Customs Counsel" not in letter, "Letter falsely claims Special Customs Counsel title"

    def test_f7_03_prior_disclosure_identifies_as_software_compliance_engine(self):
        """F7.3: Prior Disclosure identifies source as software automation engine prepared on behalf of importer."""
        service = CustomsValuationService()
        audit = service.audit_entry_valuation()
        pd = service.generate_prior_disclosure(audit)
        letter = pd.letter_text
        assert "TradeTech Systems Studio" in letter
        assert "Compliance Automation Engine" in letter or "Software" in letter

    def test_f7_04_drawback_metadata_omits_contingency_fee_claim(self):
        """F7.4: Duty Drawback audit does not frame findings around a 20% contingency fee."""
        payload = full_drawback("10000.00")
        _, discrepancies = audit_duty_drawback(payload)
        drawback_disc = next(d for d in discrepancies if "Drawback" in d.title)
        assert "contingency_fee_20pct" not in drawback_disc.metadata, (
            "Drawback discrepancy retains prohibited contingency fee metadata"
        )
        assert "20% contingency fee" not in drawback_disc.description.lower(), (
            "Drawback description text contains unauthorized contingency fee framing"
        )

    def test_f7_05_prior_disclosure_applies_19cfr162_74_penalty_mitigation(self):
        """F7.5: Prior Disclosure calculates statutory interest under 19 U.S.C. § 1505 to mitigate penalties."""
        service = CustomsValuationService()
        audit = service.audit_entry_valuation(months_elapsed=9)
        assert audit.statutory_interest_19usc1505 > Decimal("0.00")
        assert audit.prior_disclosure_tender_amount == audit.duty_underpayment + audit.statutory_interest_19usc1505

    # --------------------------------------------------------------------------
    # F8: Demurrage & Accessorial Free-Time Logic
    # --------------------------------------------------------------------------

    def test_f8_01_zero_free_days_retained_as_zero_not_four(self):
        """F8.1: port_free_days_allowed=0 must be treated as 0 free days, not 4."""
        payload = {
            "base_freight": "1000.00",
            "port_free_days_allowed": 0,
            "actual_days_held": 4,
            "detention_billed": "880.00",
        }
        _, discrepancies = audit_freight_bill(payload)
        # When free days is 0, day 4 is AFTER free time expired; detention billed was NOT incurred inside free time
        det_disc = next((d for d in discrepancies if "Inside Port Free Time" in d.title), None)
        assert det_disc is None, (
            "Falsy-zero bug: port_free_days_allowed=0 evaluated to 4, falsely flagging day 4 as inside free time"
        )

    def test_f8_02_zero_days_held_retained_as_zero_not_four(self):
        """F8.2: actual_days_held=0 with 0 free days correctly evaluates container returned on Day 0 (0 <= 0)."""
        payload = {
            "base_freight": "1000.00",
            "port_free_days_allowed": 0,
            "actual_days_held": 0,
            "detention_billed": "200.00",
        }
        _, discrepancies = audit_freight_bill(payload)
        det_disc = next((d for d in discrepancies if "Inside Port Free Time" in d.title), None)
        assert det_disc is not None, "Container picked up on Day 0 of 0 free days should flag billed detention as unlawful"

    def test_f8_03_zero_free_days_held_positive_days_not_inside_free_time(self):
        """F8.3: Hazardous cargo with 0 free days held for 2 days incurs legitimate detention after Day 0."""
        payload = {
            "base_freight": "2000.00",
            "port_free_days_allowed": 0,
            "actual_days_held": 2,
            "detention_billed": "500.00",
        }
        _, discrepancies = audit_freight_bill(payload)
        det_inside = [d for d in discrepancies if "Inside Port Free Time" in d.title]
        assert len(det_inside) == 0, "Detention on Day 2 of 0 free days should not be flagged as inside free time"

    def test_f8_04_detention_billed_inside_free_time_flagged_as_unlawful(self):
        """F8.4: Gate-out on Day 3 of 5 allowed free days flags billed detention as unlawful under FMC 46 CFR § 545.5."""
        payload = {
            "base_freight": "3000.00",
            "port_free_days_allowed": 5,
            "actual_days_held": 3,
            "detention_billed": "660.00",
        }
        metrics, discrepancies = audit_freight_bill(payload)
        det_disc = next((d for d in discrepancies if "Inside Port Free Time" in d.title), None)
        assert det_disc is not None
        assert det_disc.exposure_amount == Decimal("660.00")
        assert metrics.carrier_overbilling_caught >= Decimal("660.00")

    def test_f8_05_unauthorized_chassis_split_intercepted_without_work_order(self):
        """F8.5: Chassis split surcharge without signed work order is intercepted as an unauthorized accessorial."""
        payload = {
            "base_freight": "2500.00",
            "chassis_split_fee": "285.00",
            "has_chassis_work_order": False,
        }
        metrics, discrepancies = audit_freight_bill(payload)
        split_disc = next((d for d in discrepancies if "Chassis Split" in d.title), None)
        assert split_disc is not None
        assert split_disc.exposure_amount == Decimal("285.00")
        assert metrics.carrier_overbilling_caught == Decimal("285.00")

    # --------------------------------------------------------------------------
    # F9: Duty Drawback 99% Statutory Matching (H10, 19 USC 1313)
    # --------------------------------------------------------------------------

    def test_f9_01_exact_99_percent_calculation_via_decimal(self):
        """F9.1: 19 U.S.C. § 1313 drawback calculation is exact 99.0% using Python Decimal without float drift."""
        payload = full_drawback("10000.00")
        metrics, _ = audit_duty_drawback(payload)
        assert metrics.drawback_unclaimed_unlocked == Decimal("9900.00")

    def test_f9_02_untimely_filing_beyond_5_years_yields_zero_recovery(self):
        """F9.2: Merchandise re-exported outside the statutory 5-year window yields $0.00 recovery."""
        payload = {"duties_paid": "50000.00", "is_timely_5yr_window": False}
        metrics, discrepancies = audit_duty_drawback(payload)
        assert metrics.drawback_unclaimed_unlocked == Decimal("0.00")
        for d in discrepancies:
            assert d.exposure_amount == Decimal("0.00")

    def test_f9_03_zero_duties_paid_yields_zero_drawback(self):
        """F9.3: Zero customs duties paid yields exactly $0.00 drawback."""
        payload = full_drawback("0.00")
        metrics, discrepancies = audit_duty_drawback(payload)
        assert metrics.drawback_unclaimed_unlocked == Decimal("0.00")
        assert len(discrepancies) == 0

    def test_f9_04_unlocked_drawback_preserves_full_99_pct_without_contingency_cut(self):
        """F9.4: Unlocked drawback amount is the full 99% ($27,324.00 on $27,600 duties) without contingency deduction."""
        payload = full_drawback("27600.00")
        metrics, discrepancies = audit_duty_drawback(payload)
        assert metrics.drawback_unclaimed_unlocked == Decimal("27324.00")
        # Metadata must not report net client recovery diminished by 20% fee
        disc = discrepancies[0]
        assert disc.metadata.get("client_net_recovery") is None or Decimal(disc.metadata["client_net_recovery"]) == Decimal("27324.00")

    def test_f9_05_drawback_quantizes_to_cents_with_round_half_up(self):
        """F9.5: Drawback quantizes to 2 decimal places using ROUND_HALF_UP ($123.45 * 0.99 = $122.2155 -> $122.22)."""
        payload = full_drawback("123.45")
        metrics, _ = audit_duty_drawback(payload)
        assert metrics.drawback_unclaimed_unlocked == Decimal("122.22")

    # --------------------------------------------------------------------------
    # F10: API Security, Schemas & Decimal Serialization
    # --------------------------------------------------------------------------

    def test_f10_01_discrepancy_schema_exposure_serializes_as_decimal_string(self):
        """F10.1: Discrepancy.exposure_amount must serialize as a Decimal string (e.g. '125000.00'), NOT float."""
        disc = Discrepancy(
            id="disc-test-01",
            concept_id="concept_1_customs",
            title="Test Discrepancy",
            description="Test Description",
            statutory_code="19 U.S.C. § 1592",
            severity="critical",
            exposure_amount=Decimal("125000.00"),
            bounding_box=BoundingBox(x=0.0, y=0.0, width=10.0, height=10.0, page_number=1, confidence=0.95),
        )
        data = json.loads(disc.model_dump_json())
        assert isinstance(data["exposure_amount"], str), (
            f"exposure_amount serialized as {type(data['exposure_amount'])}, expected Decimal string"
        )
        assert data["exposure_amount"] == "125000.00"

    def test_f10_02_metrics_schema_financial_fields_serialize_as_decimal_string(self):
        """F10.2: KillShotMetrics money fields must serialize as Decimal strings, NOT float."""
        metrics = KillShotMetrics(
            penalty_exposure_avoided=Decimal("125000.00"),
            carrier_overbilling_caught=Decimal("1547.50"),
            drawback_unclaimed_unlocked=Decimal("27324.00"),
        )
        data = json.loads(metrics.model_dump_json())
        for field in ("penalty_exposure_avoided", "carrier_overbilling_caught", "drawback_unclaimed_unlocked"):
            val = data[field]
            assert isinstance(val, str), f"Field {field} serialized as {type(val)} instead of Decimal string"

    def test_f10_03_cors_configuration_rejects_wildcard_with_credentials(self):
        """F10.3: CORS middleware must NOT allow wildcard origin ('*') with allow_credentials=True."""
        from starlette.middleware.cors import CORSMiddleware
        for middleware in app.user_middleware:
            if middleware.cls == CORSMiddleware:
                allow_origins = middleware.kwargs.get("allow_origins", [])
                allow_credentials = middleware.kwargs.get("allow_credentials", False)
                if "*" in allow_origins:
                    assert not allow_credentials, (
                        "Security violation: allow_origins=['*'] combined with allow_credentials=True"
                    )

    def test_f10_04_leads_endpoint_validates_required_fields(self):
        """F10.4: POST /api/v1/leads validates payload schema and rejects invalid/empty objects."""
        res = client.post("/api/v1/leads", json={"arbitrary_unvalidated_field": "spam"})
        # Should return 422 Unprocessable Entity if schema validation is enforced
        assert res.status_code in (400, 422), (
            f"POST /api/v1/leads accepted unvalidated payload with status {res.status_code}"
        )

    def test_f10_05_telemetry_endpoint_validates_event_schema(self):
        """F10.5: POST /api/v1/telemetry validates event structure and rejects unbounded data."""
        res = client.post("/api/v1/telemetry", json={"bogus": "event", "malicious_injection": "x" * 10000})
        assert res.status_code in (400, 422), (
            f"POST /api/v1/telemetry accepted invalid payload with status {res.status_code}"
        )


# ==============================================================================
# TIER 2: BOUNDARY AND CORNER CASES
# ==============================================================================

class TestTier2BoundaryAndCornerCases:
    """
    Tier 2: Boundary Value Analysis (BVA) & Corner Cases (≥25 tests).
    Tests extreme values, zero inputs, statutory caps, recursion loops, and precision.
    """

    def test_t2_01_boundary_zero_free_days_with_zero_held_flags_detention(self):
        """T2.01: Exactly 0 free days and 0 days held flags billed detention as within free time (0 <= 0)."""
        payload = {"base_freight": "1000.00", "port_free_days_allowed": 0, "actual_days_held": 0, "detention_billed": "150.00"}
        _, disc = audit_freight_bill(payload)
        assert any("Inside Port Free Time" in d.title for d in disc)

    def test_t2_02_boundary_free_days_equal_actual_days_held(self):
        """T2.02: Actual days held exactly equals allowed free days (e.g. 5 == 5) -> detention is unlawful."""
        payload = {"base_freight": "2000.00", "port_free_days_allowed": 5, "actual_days_held": 5, "detention_billed": "400.00"}
        _, disc = audit_freight_bill(payload)
        assert any("Inside Port Free Time" in d.title for d in disc)

    def test_t2_03_boundary_actual_days_one_above_free_days(self):
        """T2.03: Actual days held is 1 day above allowed free days (5 held vs 4 allowed) -> not inside free time."""
        payload = {"base_freight": "2000.00", "port_free_days_allowed": 4, "actual_days_held": 5, "detention_billed": "200.00"}
        _, disc = audit_freight_bill(payload)
        assert not any("Inside Port Free Time" in d.title for d in disc)

    def test_t2_04_boundary_extreme_high_financial_value_customs(self):
        """T2.04: Extremely large dutiable base ($100,000,000.00) calculates without overflow or precision loss."""
        loss = Decimal("100000000.00") * Decimal("0.25")
        penalties = calculate_1592_penalties(loss)
        assert penalties["gross_negligence"] == Decimal("100000000.00")

    def test_t2_05_boundary_minimum_penny_financial_value(self):
        """T2.05: Minimum 1-cent dutiable base ($0.01) calculates cleanly with ROUND_HALF_UP."""
        loss = Decimal("0.01")
        penalties = calculate_1592_penalties(loss)
        assert penalties["negligence"] == Decimal("0.02")  # 0.01 * 2 = 0.02

    def test_t2_06_boundary_zero_duty_rate_produces_zero_duty_loss(self):
        """T2.06: Dutiable value declared and lawful rate both 0.00 produces $0.00 lawful duty loss."""
        payload = {
            "misclassified_value": "500000.00",
            "declared_duty_rate": "0.00",
            "lawful_duty_rate": "0.00",
            "items": [{"line_number": 1, "quantity": 100, "unit_price": 5000.00, "stated_total": 500000.00}]
        }
        metrics, disc = audit_customs_invoice(payload)
        assert metrics.penalty_exposure_avoided == Decimal("0.00")
        assert not any("HTS Misclassification" in d.title for d in disc)

    def test_t2_07_boundary_100_percent_duty_loss(self):
        """T2.07: 100% lawful duty rate (e.g. punitive anti-dumping) equals entire dutiable value."""
        loss = quantize_currency(Decimal("10000.00") * Decimal("1.00"))
        assert loss == Decimal("10000.00")
        penalties = calculate_1592_penalties(loss)
        assert penalties["gross_negligence"] == Decimal("40000.00")

    def test_t2_08_boundary_1592_fraud_tier_100_percent_domestic_value(self):
        """T2.08: Under 19 U.S.C. § 1592(c)(1), maximum penalty for fraud is 100% of the domestic value of merchandise."""
        loss = Decimal("31250.00")
        domestic_value = Decimal("250000.00")

        # 1. Direct Domain Service Verification
        penalties = calculate_1592_penalties(loss, domestic_value=domestic_value)
        # 19 U.S.C. 1592(c)(1): maximum penalty is the domestic value
        assert penalties["fraud"] == Decimal("250000.00")
        # Negligence and gross negligence: lesser of domestic value or 2x / 4x the loss
        assert penalties["negligence"] == Decimal("62500.00")
        assert penalties["gross_negligence"] == Decimal("125000.00")

        # 2. Authentic Customs Invoice Audit Pipeline Verification
        payload = {
            "invoice_number": "INV-2026-FRAUD-001",
            "misclassified_value": "125000.00",
            "declared_duty_rate": "0.00",
            "lawful_duty_rate": "0.25",
            "domestic_value": "250000.00",
            "violation_level": "fraud",
        }
        metrics, discrepancies = audit_customs_invoice(payload)
        assert metrics.penalty_exposure_avoided == Decimal("250000.00")

        fraud_disc = next((d for d in discrepancies if d.id == "disc-c1-03"), None)
        assert fraud_disc is not None
        assert fraud_disc.exposure_amount == Decimal("250000.00")
        assert fraud_disc.statutory_code == "19 U.S.C. 1592(c)"
        assert fraud_disc.metadata["culpability_assumed"] == "fraud"
        assert fraud_disc.metadata.get("domestic_value") == "250000.00"
        assert fraud_disc.metadata["statutory_max_by_culpability"]["fraud"] == "250000.00"
        # Prior disclosure for fraud: 100% of the loss of duty (1592(c)(4)(A))
        assert fraud_disc.metadata["prior_disclosure_max_penalty"] == "31250.00"

    def test_t2_09_boundary_cyclic_ownership_graph_self_loop(self):
        """T2.09: Entity with a self-referencing ownership loop terminates cleanly without recursion error."""
        screener = SanctionsScreener()
        # Create self-loop: Entity A owns 100% of Entity A
        screener.networks["cycle-self"] = {
            "target": {"id": "cycle-self", "name": "Self Loop Corp", "is_blocked": False},
            "nodes": [{"id": "cycle-self", "label": "Self Loop Corp", "country": "US", "is_blocked": False, "risk_level": "CLEAN_COMMERCIAL", "programs": []}],
            "edges": [{"source_id": "cycle-self", "target_id": "cycle-self", "ownership_pct": 100.0, "relationship_type": "SELF_OWNED"}]
        }
        ownership = screener.calculate_effective_blocked_ownership("cycle-self")
        assert ownership == 0.0

    def test_t2_10_boundary_cyclic_ownership_graph_3_tier_loop(self):
        """T2.10: 3-tier circular ownership (A -> B -> C -> A) terminates cleanly without stack overflow."""
        screener = SanctionsScreener()
        # Existing cyprus cross holding test
        ownership = screener.calculate_effective_blocked_ownership("cyprus-holding-alpha")
        assert isinstance(ownership, float)
        assert 0.0 <= ownership <= 100.0

    def test_t2_11_boundary_ofac_exactly_50_percent_blocked(self):
        """T2.11: Beneficial ownership of exactly 50.0% is blocked by operation of law under 31 CFR Part 501."""
        screener = SanctionsScreener()
        # Entity with two blocked shareholders holding 25.0% each, totaling exactly 50.0%
        screener.networks["target-boundary-50"] = {
            "target": {
                "id": "target-boundary-50",
                "label": "Fifty Percent Boundary Holding LLC",
                "country": "CY",
                "is_blocked": False,
                "risk_level": "CLEAN_COMMERCIAL",
                "programs": [],
            },
            "nodes": [
                {
                    "id": "target-boundary-50",
                    "label": "Fifty Percent Boundary Holding LLC",
                    "country": "CY",
                    "is_blocked": False,
                    "risk_level": "CLEAN_COMMERCIAL",
                    "programs": [],
                },
                {
                    "id": "sdn-owner-a",
                    "label": "Sanctioned Entity Alpha",
                    "country": "RU",
                    "is_blocked": True,
                    "risk_level": "SDN_BLOCKED",
                    "programs": ["OFAC SDN (E.O. 14024)"],
                },
                {
                    "id": "sdn-owner-b",
                    "label": "Sanctioned Entity Beta",
                    "country": "RU",
                    "is_blocked": True,
                    "risk_level": "SDN_BLOCKED",
                    "programs": ["OFAC SDN (E.O. 14024)"],
                },
                {
                    "id": "clean-owner-c",
                    "label": "Commercial Investor Gamma",
                    "country": "CY",
                    "is_blocked": False,
                    "risk_level": "CLEAN_COMMERCIAL",
                    "programs": [],
                },
            ],
            "edges": [
                {
                    "source_id": "sdn-owner-a",
                    "target_id": "target-boundary-50",
                    "ownership_pct": 25.0,
                    "relationship_type": "BENEFICIAL_OWNER",
                },
                {
                    "source_id": "sdn-owner-b",
                    "target_id": "target-boundary-50",
                    "ownership_pct": 25.0,
                    "relationship_type": "BENEFICIAL_OWNER",
                },
                {
                    "source_id": "clean-owner-c",
                    "target_id": "target-boundary-50",
                    "ownership_pct": 50.0,
                    "relationship_type": "COMMERCIAL_SHAREHOLDER",
                },
            ],
        }

        # 1. Direct engine ownership calculation
        ownership_pct = screener.calculate_effective_blocked_ownership("target-boundary-50")
        assert ownership_pct == 50.0

        # 2. Graph response evaluation under 31 CFR Part 501
        graph_resp = screener.get_ownership_graph("target-boundary-50")
        eval_res = graph_resp.evaluation

        assert eval_res.target_entity_id == "target-boundary-50"
        assert eval_res.total_blocked_ownership_pct == 50.0
        assert eval_res.is_blocked_by_50_percent_rule is True
        assert eval_res.direct_sdn_status is False
        assert eval_res.compliance_action == "BLOCK_AND_REPORT"
        assert len(eval_res.blocking_entities) == 2

    def test_t2_12_boundary_ofac_49_point_99_percent_not_blocked(self):
        """T2.12: Beneficial ownership of 49.99% does NOT meet the 50% Rule blocking threshold."""
        screener = SanctionsScreener()
        # Entity with 49.99% blocked ownership (sdn-owner-x) vs 50.01% clean commercial ownership
        screener.networks["target-boundary-49-99"] = {
            "target": {
                "id": "target-boundary-49-99",
                "label": "Forty-Nine Point Ninety-Nine Holding LLC",
                "country": "CY",
                "is_blocked": False,
                "risk_level": "CLEAN_COMMERCIAL",
                "programs": [],
            },
            "nodes": [
                {
                    "id": "target-boundary-49-99",
                    "label": "Forty-Nine Point Ninety-Nine Holding LLC",
                    "country": "CY",
                    "is_blocked": False,
                    "risk_level": "CLEAN_COMMERCIAL",
                    "programs": [],
                },
                {
                    "id": "sdn-owner-x",
                    "label": "Sanctioned Entity X",
                    "country": "RU",
                    "is_blocked": True,
                    "risk_level": "SDN_BLOCKED",
                    "programs": ["OFAC SDN (E.O. 14024)"],
                },
                {
                    "id": "clean-owner-y",
                    "label": "Commercial Investor Y",
                    "country": "CY",
                    "is_blocked": False,
                    "risk_level": "CLEAN_COMMERCIAL",
                    "programs": [],
                },
            ],
            "edges": [
                {
                    "source_id": "sdn-owner-x",
                    "target_id": "target-boundary-49-99",
                    "ownership_pct": 49.99,
                    "relationship_type": "BENEFICIAL_OWNER",
                },
                {
                    "source_id": "clean-owner-y",
                    "target_id": "target-boundary-49-99",
                    "ownership_pct": 50.01,
                    "relationship_type": "COMMERCIAL_SHAREHOLDER",
                },
            ],
        }

        # 1. Direct engine ownership calculation
        ownership_pct = screener.calculate_effective_blocked_ownership("target-boundary-49-99")
        assert ownership_pct == 49.99

        # 2. Graph response evaluation: falls below 50.0% threshold
        graph_resp = screener.get_ownership_graph("target-boundary-49-99")
        eval_res = graph_resp.evaluation

        assert eval_res.target_entity_id == "target-boundary-49-99"
        assert eval_res.total_blocked_ownership_pct == 49.99
        assert eval_res.is_blocked_by_50_percent_rule is False
        assert eval_res.direct_sdn_status is False
        assert eval_res.compliance_action == "ENHANCED_DUE_DILIGENCE"
        assert len(eval_res.blocking_entities) == 1
        assert eval_res.blocking_entities[0]["ownership_pct"] == 49.99

    def test_t2_13_boundary_statutory_mpf_minimum_floor(self):
        """T2.13: Entered value yielding raw MPF < $34.58 is clamped to the statutory floor."""
        landed = calculate_landed_cost(entered_value=Decimal("5000.00"), duty_rate_ad_valorem=Decimal("0.00"))
        # Formal entry: 5,000 * 0.003464 = 17.32 -> clamped to the FY2027 minimum
        assert landed.mpf_fee == Decimal("34.58")
        # Informal entry ($500): flat automated surcharge, not the formal minimum
        informal = calculate_landed_cost(entered_value=Decimal("500.00"), duty_rate_ad_valorem=Decimal("0.00"))
        assert informal.mpf_fee == Decimal("2.77")

    def test_t2_14_boundary_statutory_mpf_maximum_ceiling(self):
        """T2.14: Entered value yielding raw MPF > $670.86 is clamped to the statutory ceiling."""
        landed = calculate_landed_cost(entered_value=Decimal("500000.00"), duty_rate_ad_valorem=Decimal("0.00"))
        # 500,000 * 0.003464 = 1,732.00 -> Clamped to max cap
        assert landed.mpf_fee == Decimal("670.86")

    def test_t2_15_boundary_statutory_mpf_exact_cutoff(self):
        """T2.15: Entered value where raw MPF falls between minimum and maximum caps calculates un-clamped."""
        # Entered value = $100,000 -> MPF = $346.40 (between $32.71 and $634.62)
        landed = calculate_landed_cost(entered_value=Decimal("100000.00"), duty_rate_ad_valorem=Decimal("0.00"))
        assert landed.mpf_fee == Decimal("346.40")

    def test_t2_16_boundary_hmf_air_or_truck_shipment_is_zero(self):
        """T2.16: Harbor Maintenance Fee (HMF) is $0.00 for air and truck transport (19 CFR § 24.24)."""
        landed = calculate_landed_cost(
            entered_value=Decimal("100000.00"),
            duty_rate_ad_valorem=Decimal("0.05"),
            is_ocean_freight=False,
        )
        assert landed.hmf_fee == Decimal("0.00")
        assert landed.hmf_rate == Decimal("0.00")

    def test_t2_17_boundary_bounding_box_at_exact_origin(self):
        """T2.17: Bounding box located at exact (0.0, 0.0) coordinate origin is valid."""
        box = BoundingBox(x=0.0, y=0.0, width=50.0, height=50.0, page_number=1, confidence=0.99)
        assert box.x == 0.0 and box.y == 0.0

    def test_t2_18_boundary_bounding_box_at_exact_max_extent(self):
        """T2.18: Bounding box reaching exactly x + width = 1000.0 and y + height = 1000.0 is valid."""
        box = BoundingBox(x=800.0, y=800.0, width=200.0, height=200.0, page_number=1, confidence=0.99)
        assert box.x + box.width == 1000.0
        assert box.y + box.height == 1000.0

    def test_t2_19_boundary_bounding_box_exceeding_1000_raises_validation_error(self):
        """T2.19: Bounding box with x + width = 1000.1 raises Pydantic ValidationError."""
        with pytest.raises(Exception):
            BoundingBox(x=900.0, y=0.0, width=100.1, height=10.0, page_number=1, confidence=0.9)

    def test_t2_20_boundary_negative_currency_values_in_safe_decimal(self):
        """T2.20: Negative numbers are preserved cleanly in safe_decimal."""
        assert safe_decimal("-150.25") == Decimal("-150.25")
        assert safe_decimal(Decimal("-50.00")) == Decimal("-50.00")

    def test_t2_21_boundary_null_and_empty_in_safe_decimal(self):
        """T2.21: None, empty string, and whitespace in safe_decimal return default $0.00."""
        assert safe_decimal(None) == Decimal("0.00")
        assert safe_decimal("") == Decimal("0.00")

    def test_t2_22_boundary_corrupt_string_in_safe_decimal(self):
        """T2.22: Non-numeric strings in safe_decimal gracefully fall back to default $0.00."""
        assert safe_decimal("N/A") == Decimal("0.00")
        assert safe_decimal("UNDEFINED_PRICE") == Decimal("0.00")

    def test_t2_23_boundary_empty_items_list_in_customs_invoice(self):
        """T2.23: Customs invoice with empty items list [] produces zero math discrepancies."""
        payload = {"items": [], "misclassified_value": "0.00"}
        metrics, discrepancies = audit_customs_invoice(payload)
        math_disc = [d for d in discrepancies if "Arithmetic" in d.title]
        assert len(math_disc) == 0

    def test_t2_24_boundary_item_with_zero_quantity_and_price(self):
        """T2.24: Line item with quantity=0 and unit_price=0.00 produces zero extension variance."""
        payload = {
            "items": [{"line_number": 1, "quantity": "0", "unit_price": "0.00", "stated_total": "0.00"}],
            "misclassified_value": "0.00"
        }
        _, discrepancies = audit_customs_invoice(payload)
        math_disc = [d for d in discrepancies if "Arithmetic" in d.title]
        assert len(math_disc) == 0

    def test_t2_25_boundary_drawback_five_year_statutory_cutoff(self):
        """T2.25: The 5-year limit (19 U.S.C. 1313(r)(1)) is computed from the import date."""
        # Exactly inside window
        m_timely, _ = audit_duty_drawback(full_drawback("1000.00"))
        assert m_timely.drawback_unclaimed_unlocked == Decimal("990.00")
        # 1 day outside window
        m_untimely, _ = audit_duty_drawback(full_drawback("1000.00", export_date="2029-01-16"))
        assert m_untimely.drawback_unclaimed_unlocked == Decimal("0.00")

    def test_t2_26_boundary_fsc_billed_rate_equals_authorized_rate(self):
        """T2.26: Billed FSC rate equals authorized contractual cap -> $0.00 fuel overbilling."""
        payload = {
            "base_freight": "5000.00",
            "billed_fsc_rate": "0.240",
            "authorized_fsc_rate": "0.240",
        }
        metrics, disc = audit_freight_bill(payload)
        fsc_disc = [d for d in disc if "Fuel Surcharge" in d.title]
        assert len(fsc_disc) == 0
        assert metrics.carrier_overbilling_caught == Decimal("0.00")


# ==============================================================================
# TIER 3: CROSS-FEATURE COMBINATIONS
# ==============================================================================

class TestTier3CrossFeatureInteractions:
    """
    Tier 3: Pairwise & Multi-Domain Interactions (≥10 tests).
    Tests compound workflows where multiple compliance domains interact.
    """

    def test_t3_01_cross_hts_misclassification_and_cif_valuation_in_single_entry(self):
        """T3.01: Customs invoice with both HTS misclassification and CIF marine insurance deduction."""
        payload = {
            "incoterms": "CIF LOS ANGELES",
            "insurance_charge": "0.00",
            "freight_charge": "1500.00",
            "misclassified_value": "100000.00",
            "declared_duty_rate": "0.00",
            "lawful_duty_rate": "0.25",
            "items": [{"line_number": 1, "quantity": "1000", "unit_price": "100.00", "stated_total": "100000.00"}],
        }
        metrics, discrepancies = audit_customs_invoice(payload)
        # Negligence (default culpability) maximum = $100k * 25% * 2 = $50,000.00
        assert metrics.penalty_exposure_avoided == Decimal("50000.00")
        titles = [d.title for d in discrepancies]
        assert any("HTS Misclassification" in t for t in titles)
        assert any("CIF" in t for t in titles)

    def test_t3_02_cross_customs_valuation_and_sanctions_hit(self):
        """T3.02: Invoice with undeclared engineering assists and high-risk sanctioned shipper."""
        payload = {
            "unreported_assists": "50000.00",
            "lawful_duty_rate": "0.25",
            "shipper": "Rosoboronexport",
            "items": [{"line_number": 1, "quantity": "10", "unit_price": "5000.00", "stated_total": "50000.00"}]
        }
        metrics, discrepancies = audit_customs_invoice(payload)
        # Undeclared assist: $50,000 * 25% = $12,500 loss of duty -> negligence maximum $25,000
        assist_disc = next(d for d in discrepancies if "Assist" in d.title)
        assert assist_disc.exposure_amount == Decimal("25000.00")
        titles = [d.title for d in discrepancies]
        assert any("Assist" in t for t in titles)
        assert any("Sanctioned" in t for t in titles)

    def test_t3_03_cross_foreign_corridor_with_sanctioned_entity(self):
        """T3.03: Transshipment on foreign corridor (ZADUR -> NLRTM) with sanctioned entity."""
        # Sanctions check applies under international lists, but US 1592 penalties are rejected
        assert "19_USC_1592" not in eu_corridor_xml()
        # Screen parties on this corridor
        report = sanctions_screener.screen_parties(shipper="Rosoboronexport JSC", buyer="European Buyer BV")
        assert report.has_violations is True
        assert report.shipper.matched is True

    def test_t3_04_cross_empty_input_firewall_across_all_endpoints(self):
        """T3.04: Empty inputs submitted across all 3 audit services simultaneously report zero findings."""
        m1, d1 = audit_customs_invoice({})
        m2, d2 = audit_freight_bill({})
        m3, d3 = audit_duty_drawback({})
        assert len(d1) == len(d2) == len(d3) == 0
        assert m1.penalty_exposure_avoided == m2.carrier_overbilling_caught == m3.drawback_unclaimed_unlocked == Decimal("0.00")

    def test_t3_05_cross_freight_demurrage_with_chassis_split_and_fsc_markup(self):
        """T3.05: Single freight bill exhibiting FSC overcharge + unauthorized chassis split + illegal detention."""
        payload = {
            "base_freight": "4000.00",
            "billed_fsc_rate": "0.300",       # 30% billed vs 20% authorized -> $400 overcharge
            "authorized_fsc_rate": "0.200",
            "chassis_split_fee": "285.00",     # No work order -> $285 overcharge
            "has_chassis_work_order": False,
            "port_free_days_allowed": 4,       # Picked up Day 3 of 4 -> $500 illegal detention
            "actual_days_held": 3,
            "detention_billed": "500.00",
        }
        metrics, discrepancies = audit_freight_bill(payload)
        expected_total = Decimal("400.00") + Decimal("285.00") + Decimal("500.00")  # $1,185.00
        assert metrics.carrier_overbilling_caught == expected_total
        assert len(discrepancies) == 3

    def test_t3_06_cross_prior_disclosure_generation_with_assists_and_cif_deductions(self):
        """T3.06: Prior disclosure filing reconciles CIF overvaluation and undeclared assists into net tender check."""
        service = CustomsValuationService()
        audit = service.audit_entry_valuation(
            declared_transaction_value=Decimal("500000.00"),
            invoice_incoterm="CIF Los Angeles",
            international_freight_in_invoice=Decimal("30000.00"),
            marine_insurance_in_invoice=Decimal("5000.00"),
            months_elapsed=6,
        )
        pd = service.generate_prior_disclosure(audit)
        assert pd.letter_text is not None
        assert f"${audit.prior_disclosure_tender_amount:,.2f}" in pd.letter_text
        assert "DRAFT" in pd.letter_text

    def test_t3_07_cross_hts_classification_landed_cost_with_ocean_freight_and_insurance(self):
        """T3.07: HTS classification result carries full landed cost calculation with customs duty, MPF, HMF."""
        req = ClassificationRequest(
            product_title="Brushless DC Motor for Multirotor",
            product_description="High-efficiency 2207 brushless drone motor for commercial quadcopter",
            entered_value=Decimal("25000.00"),
            is_ocean_freight=True,
            freight_and_insurance=Decimal("1500.00"),
        )
        res = HTSClassifierEngine().classify(req)
        landed = res.landed_cost
        assert landed.entered_value == Decimal("25000.00")
        assert landed.total_landed_cost > landed.entered_value
        assert landed.hmf_fee > Decimal("0.00")
        assert landed.mpf_fee > Decimal("0.00")

    def test_t3_08_cross_drawback_paired_with_hts_reclassification(self):
        """T3.08: Drawback audit matching entry with Section 301 duties accurately computes 99% recovery on all duties."""
        # Entry paid $25,000 standard duty + $25,000 Section 301 tariff = $50,000 total duties paid
        payload = full_drawback("50000.00")
        metrics, disc = audit_duty_drawback(payload)
        assert metrics.drawback_unclaimed_unlocked == Decimal("49500.00")
        assert len(disc) >= 1

    def test_t3_09_cross_api_cargowise_xml_export_with_cif_terms(self):
        """T3.09: CargoWise One eAdaptor XML export for CIF shipment accurately formats financial elements."""
        from app.services.cargowise_xml import cargowise_exporter
        xml_str = cargowise_exporter.generate_universal_interchange_xml(
            shipment_id="SHP-99001",
            declaration_id="DEC-88120",
            port_origin_code="CNSZX",
            port_origin_name="Shenzhen",
            port_dest_code="USLAX",
            port_dest_name="Los Angeles",
            invoice_number="INV-2026-99",
            incoterm="CIF",
            invoice_amount=Decimal("125000.00"),
            insurance_amount=Decimal("1200.00"),
        )
        assert "<UniversalShipment" in xml_str
        assert "125000.00" in xml_str
        assert "1200.00" in xml_str
        assert "CIF" in xml_str

    def test_t3_10_cross_sanctions_graph_traversal_with_multi_hop_indirect_ownership(self):
        """T3.10: 2-hop indirect ownership evaluation aggregates correctly under the OFAC 50% Rule."""
        screener = SanctionsScreener()
        screener.networks["target-multi-hop"] = {
            "target": {"id": "target-multi-hop", "name": "Target Subsidiary LLC", "is_blocked": False},
            "nodes": [
                {"id": "target-multi-hop", "label": "Target Subsidiary LLC", "country": "CY", "is_blocked": False, "risk_level": "CLEAN_COMMERCIAL", "programs": []},
                {"id": "parent-holding", "label": "Intermediate Holding", "country": "CY", "is_blocked": False, "risk_level": "CLEAN_COMMERCIAL", "programs": []},
                {"id": "sdn-ultimate-owner", "label": "Blocked Oligarch", "country": "RU", "is_blocked": True, "risk_level": "SDN_BLOCKED", "programs": ["OFAC SDN"]},
            ],
            "edges": [
                {"source_id": "sdn-ultimate-owner", "target_id": "parent-holding", "ownership_pct": 100.0, "relationship_type": "BENEFICIAL_OWNER"},
                {"source_id": "parent-holding", "target_id": "target-multi-hop", "ownership_pct": 60.0, "relationship_type": "PARENT_COMPANY"},
            ]
        }
        ownership = screener.calculate_effective_blocked_ownership("target-multi-hop")
        assert ownership == 60.0, f"Multi-hop ownership aggregation failed: expected 60.0%, got {ownership}%"


# ==============================================================================
# TIER 4: REAL-WORLD APPLICATION SCENARIOS (S1 through S6)
# ==============================================================================

class TestTier4RealWorldApplicationScenarios:
    """
    Tier 4: End-to-End Application Scenarios (S1 through S6 per TEST_INFRA.md).
    Simulates production regulatory audits from document intake through API verification.
    """

    def test_t4_s1_transpacific_drone_motor_ocean_import(self):
        """
        S1: Trans-Pacific Drone Motor Ocean Import (CNTAO -> USLAX).
        Exercises F1, F3, F5, F6, F10:
        - HTS classification of drone motor under GRI 1-6.
        - CIF insurance exclusion under 19 U.S.C. § 1401a.
        - Negligence penalty calculation under 19 U.S.C. § 1592.
        - Strict Decimal serialization in API response.
        """
        # 1. Classify product
        req = ClassificationRequest(
            product_title="Brushless Drone Motor 2207",
            product_description="High-precision brushless DC motor for commercial quadcopters",
            entered_value=Decimal("125000.00"),
            is_ocean_freight=True,
            freight_and_insurance=Decimal("3500.00"),
        )
        hts_res = HTSClassifierEngine().classify(req)
        assert hts_res.classified_hts_code == "8501.31.8000"
        assert hts_res.confidence >= 0.85

        # 2. Run customs valuation and 1592 audit
        payload = {
            "incoterms": "CIF LOS ANGELES",
            "insurance_charge": "0.00",
            "freight_charge": "3500.00",
            "misclassified_value": "125000.00",
            "declared_duty_rate": "0.00",
            "lawful_duty_rate": "0.25",
            "items": [{"line_number": 1, "quantity": 1000, "unit_price": 125.00, "stated_total": 125000.00}]
        }
        metrics, discrepancies = audit_customs_invoice(payload)
        assert metrics.penalty_exposure_avoided == Decimal("62500.00")
        assert any("HTS Misclassification" in d.title for d in discrepancies)
        assert any("CIF" in d.title for d in discrepancies)

        # 3. Check API serialization
        res = client.get("/api/v1/audit/concept_1_customs")
        assert res.status_code == 200
        data = res.json()
        assert data["concept_id"] == "concept_1_customs"
        # Verify monetary fields are serialized as Decimal strings per H8
        assert isinstance(data["metrics"]["penalty_exposure_avoided"], str), "API serialized money as float"

    def test_t4_s2_foreign_to_foreign_transshipment_corridor(self):
        """
        S2: Foreign-to-Foreign Transshipment Corridor (ZADUR -> NLRTM).
        Exercises F5, F6, F7, F10:
        - Verifies rejection of US CBP 19 U.S.C. § 1592 penalty exposure on South Africa to Netherlands shipment.
        - Directs to EU Union Customs Code (UCC).
        - Verifies Prior Disclosure letters omit Counsel of Record claims.
        """
        xml = eu_corridor_xml()
        assert "19_USC_1592" not in xml, "US statute applied to EU corridor"
        assert "EU_UCC_COMPLIANT" in xml

        # Prior disclosure letter test
        service = CustomsValuationService()
        audit = service.audit_entry_valuation()
        pd = service.generate_prior_disclosure(audit)
        assert "Counsel of Record" not in pd.letter_text
        assert "DRAFT" in pd.letter_text

    def test_t4_s3_multitier_corporate_ownership_sanctions_with_cyclic_entity(self):
        """
        S3: Multi-Tier Corporate Ownership Sanctions Screening with Cyclic Entity.
        Exercises F4, F10:
        - Traversal of 3-tier ownership network with circular parent-subsidiary references.
        - Verifies cycle prevention and OFAC 50% Rule aggregation.
        - Fail-closed behavior on unknown entities.
        """
        # 1. Known entity with OFAC 50% Rule blocking
        graph_50 = sanctions_screener.get_ownership_graph("bis-el-cn-0941")
        assert graph_50.evaluation.total_blocked_ownership_pct == 55.0
        assert graph_50.evaluation.is_blocked_by_50_percent_rule is True

        # 2. Cyclic ownership network
        cyclic_pct = sanctions_screener.calculate_effective_blocked_ownership("cyprus-holding-alpha")
        assert isinstance(cyclic_pct, float)

        # 3. Unknown entity fail-closed
        unknown_graph = sanctions_screener.get_ownership_graph("unknown-shell-co-888")
        assert unknown_graph.nodes[0].risk_level in ("UNSCREENED", "COMPLIANCE_HOLD")
        assert unknown_graph.evaluation.compliance_action == "REQUIRES_MANUAL_REVIEW"

    def test_t4_s4_hazardous_cargo_demurrage_at_port_of_houston(self):
        """
        S4: Hazardous Cargo Demurrage & Chassis Split Audit at Port of Houston.
        Exercises F8, F10:
        - Dangerous goods container with 0 contractual free days.
        - Verifies elimination of falsy-zero bug (int(0 or 4) == 4).
        - Validates unauthorized accessorial fees under OSRA 2022.
        """
        payload = {
            "base_freight": "3500.00",
            "billed_fsc_rate": "0.280",
            "authorized_fsc_rate": "0.220",
            "chassis_split_fee": "285.00",
            "has_chassis_work_order": False,
            "port_free_days_allowed": 0,       # 0 contractual free days
            "actual_days_held": 3,             # Held 3 days
            "detention_billed": "900.00",
        }
        metrics, discrepancies = audit_freight_bill(payload)
        # Billed FSC overcharge: $3500 * (0.28 - 0.22) = $210.00
        # Chassis split: $285.00
        # Detention: Held 3 days on 0 free days -> detention is NOT inside free time
        assert not any("Inside Port Free Time" in d.title for d in discrepancies)
        assert metrics.carrier_overbilling_caught == Decimal("495.00")  # $210 FSC + $285 Split

    def test_t4_s5_paired_import_export_99_duty_drawback_audit(self):
        """
        S5: Paired Import/Export 99% Duty Drawback Audit.
        Exercises F9, F7, F10:
        - CBP Form 7501 paired with outbound export Bill of Lading.
        - Validates exact 99% refund matching under 19 U.S.C. § 1313.
        - Verifies total absence of 20% broker contingency fee framing.
        """
        payload = full_drawback("27600.00", import_entry="441-9872134-2", export_bl="EXP-2024-88412")
        metrics, discrepancies = audit_duty_drawback(payload)
        assert metrics.drawback_unclaimed_unlocked == Decimal("27324.00")
        assert len(discrepancies) >= 1
        # Absence of contingency fee
        disc = discrepancies[0]
        assert "contingency_fee_20pct" not in disc.metadata
        assert "20% contingency fee" not in disc.description.lower()

    def test_t4_s6_adversarial_empty_and_corrupt_input_ingestion_firewall(self):
        """
        S6: Adversarial Empty & Corrupt Input Ingestion Firewall.
        Exercises F1, F2, F10:
        - Submitting empty, null, and stripped payloads to all 3 audit engines.
        - Confirms $0.00 exposure and zero fabricated violations across all endpoints.
        """
        # Empty dicts
        m_c, d_c = audit_customs_invoice({})
        m_f, d_f = audit_freight_bill({})
        m_d, d_d = audit_duty_drawback({})
        assert m_c.penalty_exposure_avoided == Decimal("0.00") and len(d_c) == 0
        assert m_f.carrier_overbilling_caught == Decimal("0.00") and len(d_f) == 0
        assert m_d.drawback_unclaimed_unlocked == Decimal("0.00") and len(d_d) == 0

        # Corrupt and null fields
        corrupt_payload = {"items": None, "declared_duty_rate": "INVALID", "misclassified_value": None}
        m_corrupt, d_corrupt = audit_customs_invoice(corrupt_payload)
        assert m_corrupt.penalty_exposure_avoided == Decimal("0.00")
        assert len(d_corrupt) == 0
