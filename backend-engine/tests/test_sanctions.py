from decimal import Decimal

from app.services.customs_audit import audit_customs_invoice
from app.services.drawback_audit import audit_duty_drawback
from app.services.sanctions_screener import (
    SanctionsScreener,
    sanctions_screener,
)


def test_sanctions_screener_rapidfuzz_matching():
    screener = SanctionsScreener()

    # High similarity match above threshold 85.0
    match = screener.match_entity("Global Micro Electronics Ltd, Shenzhen", threshold=85.0)
    assert match.matched is True
    assert match.entity_id == "bis-el-cn-0941"
    assert match.match_score >= 85.0
    assert "BIS Entity List (15 CFR Part 744, Supp. No. 4)" in match.programs
    assert match.schema_type == "Company"

    # Match via alias
    match_alias = screener.match_entity("Shenzhen Global Microelectronics Defense Dynamics", threshold=85.0)
    assert match_alias.matched is True
    assert match_alias.entity_id == "bis-el-cn-0941"

    # Unsanctioned clean entity below threshold
    clean_match = screener.match_entity("Clean Pacific Components Corp California", threshold=85.0)
    assert clean_match.matched is False
    assert clean_match.entity_id is None

def test_sanctions_screen_parties_report():
    report = sanctions_screener.screen_parties(
        shipper="Global Micro Electronics Ltd, Shenzhen",
        buyer="Pacific Apex Distribution LLC",
        consignee=None,
        threshold=85.0
    )
    assert report.has_violations is True
    assert report.total_matches == 1
    assert report.shipper is not None
    assert report.shipper.matched is True
    assert report.buyer is not None
    assert report.buyer.matched is False

def test_customs_invoice_with_unreported_assists():
    data = {
        "incoterms": "FOB SHENZHEN",
        "insurance_charge": "0.00",
        "misclassified_value": "0.00",
        "declared_duty_rate": "0.00",
        "lawful_duty_rate": "0.25",
        "unreported_assists": "40000.00",
        "items": []
    }
    metrics, discrepancies = audit_customs_invoice(data)
    assist_disc = next((d for d in discrepancies if "Assist" in d.title), None)
    assert assist_disc is not None
    assert assist_disc.statutory_code == "19 U.S.C. 1401a(h)(1)(A) / 19 CFR 152.103(d)"
    assert assist_disc.severity == "critical"
    # Assist of $40,000 @ 25% = $10,000 loss of duty -> negligence maximum 2x = $20,000.00
    assert assist_disc.exposure_amount == Decimal("20000.00")

def test_drawback_audit_contingency_fee():
    data = {
        "import_entry": "CBP-7501-84920184",
        "export_bl": "BGFU-0941824",
        "entry_date": "2024-01-15",
        "export_date": "2024-03-10",
        "claim_date": "2026-11-20",
        "duties_paid": "27600.00",
        "imported_quantity": "1000",
        "exported_quantity": "1000",
        "direct_identification": True,
        "drawback_percentage": "0.99",
    }
    metrics, discrepancies = audit_duty_drawback(data)
    disc = next(d for d in discrepancies if "99% Statutory" in d.title)
    assert disc is not None
    assert metrics.drawback_unclaimed_unlocked == Decimal("27324.00")
    # Verify no contingency fee deduction and broker software service model
    assert "contingency_fee_20pct" not in disc.metadata
    assert disc.metadata["cash_recovery_ready"] == "27324.00"
    assert disc.metadata["service_model"] == "compliance_auditing_software_for_licensed_brokers_and_self_filers"

