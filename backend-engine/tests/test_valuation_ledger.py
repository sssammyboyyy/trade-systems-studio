"""Test suite for CBP Assist & Valuation Register (19 CFR § 152.103 & 19 U.S.C. § 1401a)."""

from decimal import Decimal

from fastapi.testclient import TestClient

from app.services.valuation_ledger import CustomsValuationService
from main import app

client = TestClient(app)


def test_assist_valuation_audit_math():
    """Verify statutory assist apportionment, CIF deduction, and penalty mitigation using Decimal."""
    service = CustomsValuationService()

    audit = service.audit_entry_valuation(
        entry_number="CBP-7501-84920184",
        importer_of_record="Test Importer Corp",
        declared_transaction_value=Decimal("450000.00"),
        duty_rate_ad_valorem=Decimal("0.054"),  # 5.4%
        current_entry_units=15000,
        invoice_incoterm="CIF Los Angeles",
        international_freight_in_invoice=Decimal("24500.00"),
        marine_insurance_in_invoice=Decimal("3200.00"),
        months_elapsed=12,
    )

    # CIF overvaluation check: 24,500 + 3,200 = 27,700
    assert audit.improper_cif_overvaluation == Decimal("27700.00")

    # Undeclared assists omitted:
    # AST-001 (185,000 / 100,000 = 1.85 * 15,000 = 27,750.00)
    # AST-002 (120,000 / 60,000 = 2.00 * 15,000 = 30,000.00)
    # AST-003 is already declared, so not omitted
    # Total omitted = 27,750 + 30,000 = 57,750.00
    assert audit.assists_omitted_cost == Decimal("57750.00")

    # Adjusted Lawful Value = 450,000 - 27,700 + 57,750 = 480,050.00
    assert audit.adjusted_lawful_dutiable_value == Decimal("480050.00")

    # Declared duty paid: 450,000 * 0.054 = 24,300.00
    assert audit.declared_duty_paid == Decimal("24300.00")

    # Lawful duty due: 480,050 * 0.054 = 25,922.70
    assert audit.lawful_duty_due == Decimal("25922.70")

    # Underpayment: 25,922.70 - 24,300.00 = 1,622.70
    assert audit.duty_underpayment == Decimal("1622.70")

    # Gross negligence penalty (4.0x): 1,622.70 * 4 = 6,490.80
    assert audit.gross_negligence_penalty_exposure == Decimal("6490.80")

    # Statutory interest under 19 U.S.C. § 1505(c) / 26 U.S.C. §§ 6621/6622 (7% compounded daily for 365 days):
    # 1,622.70 * (((1 + 0.07/365)**365) - 1) = 117.65
    assert audit.statutory_interest_19usc1505 == Decimal("117.65")

    # Prior disclosure tender = 1,622.70 + 117.65 = 1,740.35
    assert audit.prior_disclosure_tender_amount == Decimal("1740.35")

    # Negligence maximum (2x, 19 U.S.C. 1592(c)(3)): 3,245.40
    assert audit.negligence_penalty_exposure == Decimal("3245.40")

    # After a prior disclosure the negligence penalty is limited to interest (1592(c)(4)(B)):
    # 3,245.40 - 117.65 = 3,127.75 avoided
    assert audit.total_liability_avoided == Decimal("3127.75")


def test_prior_disclosure_letter_generation():
    """Verify statutory formal disclosure letter contents under 19 CFR § 162.74."""
    service = CustomsValuationService()
    audit = service.audit_entry_valuation()
    pkg = service.generate_prior_disclosure(audit, port_of_entry="Los Angeles / Long Beach (2704)")

    assert "FORMAL PRIOR DISCLOSURE UNDER 19 CFR § 162.74" in pkg.letter_text
    assert "19 U.S.C. § 1592(c)(4)" in pkg.letter_text
    assert "TOTAL TENDER CHECK ENCLOSED" in pkg.letter_text
    assert pkg.actual_duty_loss == audit.duty_underpayment
    assert pkg.total_tender_check == audit.prior_disclosure_tender_amount
    assert "Counsel of Record" not in pkg.letter_text
    assert "Special Customs Counsel" not in pkg.letter_text
    assert "DRAFT" in pkg.letter_text


def test_valuation_api_endpoints():
    """Verify HTTP API endpoints for valuation ledger and audit."""
    # Test ledger GET
    res_ledger = client.get("/api/v1/valuation/ledger")
    assert res_ledger.status_code == 200
    ledger_data = res_ledger.json()
    assert len(ledger_data) >= 3

    # Test audit POST
    payload = {
        "entry_number": "CBP-7501-TEST1234",
        "importer_of_record": "Pacific Tech Imports LLC",
        "declared_transaction_value": "450000.00",
        "duty_rate_ad_valorem": "0.054",
        "current_entry_units": 15000,
        "invoice_incoterm": "CIF Los Angeles",
        "international_freight_in_invoice": "24500.00",
        "marine_insurance_in_invoice": "3200.00",
        "months_elapsed": 9,
    }
    res_audit = client.post("/api/v1/valuation/audit-entry", json=payload)
    assert res_audit.status_code == 200
    audit_data = res_audit.json()
    assert "adjusted_lawful_dutiable_value" in audit_data
    assert "prior_disclosure_tender_amount" in audit_data

    # Test prior disclosure POST
    res_pd = client.post("/api/v1/valuation/prior-disclosure", json=payload)
    assert res_pd.status_code == 200
    pd_data = res_pd.json()
    assert "FORMAL PRIOR DISCLOSURE" in pd_data["letter_text"]
