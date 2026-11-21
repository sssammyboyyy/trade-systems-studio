from decimal import Decimal

from fastapi.testclient import TestClient

from app.services.customs_audit import audit_customs_invoice
from app.services.drawback_audit import audit_duty_drawback
from app.services.freight_audit import audit_freight_bill
from main import app

client = TestClient(app)

def test_invalid_concept_id_404():
    response = client.get("/api/v1/audit/non_existent_concept")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

def test_concept_clean_fob_audit_endpoint():
    response = client.get("/api/v1/audit/concept_clean_fob")
    assert response.status_code == 200
    data = response.json()
    assert data["concept_id"] == "concept_clean_fob"
    assert data["metrics"]["penalty_exposure_avoided"] == "0.00"
    assert len(data["discrepancies"]) == 0

def test_customs_invoice_clean_no_errors():
    clean_data = {
        "incoterms": "FOB SHENZHEN", # FOB does not require seller marine insurance
        "insurance_charge": "0.00",
        "misclassified_value": "0.00",
        "declared_duty_rate": "0.00",
        "lawful_duty_rate": "0.00",
        "items": [
            {
                "line_number": 1,
                "quantity": "100",
                "unit_price": "10.00",
                "stated_total": "1000.00", # Exact math 100 * 10 = 1000
            }
        ]
    }
    metrics, discrepancies = audit_customs_invoice(clean_data)
    assert metrics.penalty_exposure_avoided == Decimal("0.00")
    # Only the clean item, no statutory errors
    math_discs = [d for d in discrepancies if "Arithmetic" in d.title]
    assert len(math_discs) == 0

def test_freight_audit_clean_no_overbilling():
    clean_freight = {
        "base_freight": "5000.00",
        "billed_fsc_rate": "0.240",
        "authorized_fsc_rate": "0.240", # Exact match to EIA index
        "chassis_split_fee": "0.00",
        "has_chassis_work_order": True,
        "port_free_days_allowed": 5,
        "actual_days_held": 3, # Gate out inside free time
        "detention_billed": "0.00"
    }
    metrics, discrepancies = audit_freight_bill(clean_freight)
    assert metrics.carrier_overbilling_caught == Decimal("0.00")
    assert len(discrepancies) == 0

def test_null_and_malformed_payload_handling():
    # Verify no decimal.InvalidOperation is thrown on null / None values
    null_customs = {
        "incoterms": None,
        "insurance_charge": None,
        "misclassified_value": None,
        "declared_duty_rate": None,
        "lawful_duty_rate": None,
        "items": [
            {
                "line_number": None,
                "quantity": None,
                "unit_price": None,
                "stated_total": None
            }
        ]
    }
    m1, d1 = audit_customs_invoice(null_customs)
    assert m1.penalty_exposure_avoided == Decimal("0.00")
    assert len(d1) == 0

    null_freight = {
        "base_freight": None,
        "billed_fsc_rate": None,
        "authorized_fsc_rate": None,
        "chassis_split_fee": None,
        "port_free_days_allowed": None,
        "actual_days_held": None,
        "detention_billed": None
    }
    m2, d2 = audit_freight_bill(null_freight)
    assert m2.carrier_overbilling_caught == Decimal("0.00")
    assert len(d2) == 0

    null_drawback = {
        "dutiable_value": None,
        "duties_paid": None,
        "drawback_percentage": None,
        "is_timely_5yr_window": None
    }
    m3, d3 = audit_duty_drawback(null_drawback)
    assert m3.drawback_unclaimed_unlocked == Decimal("0.00")
    assert len(d3) == 0

def test_empty_dict_input_returns_zero_discrepancies():
    """C2 requirement: passing {} must return KillShotMetrics() and 0 discrepancies."""
    m1, d1 = audit_customs_invoice({})
    assert m1.penalty_exposure_avoided == Decimal("0.00")
    assert len(d1) == 0

    m2, d2 = audit_freight_bill({})
    assert m2.carrier_overbilling_caught == Decimal("0.00")
    assert len(d2) == 0

    m3, d3 = audit_duty_drawback({})
    assert m3.drawback_unclaimed_unlocked == Decimal("0.00")
    assert len(d3) == 0

def test_duty_drawback_untimely_5yr_window():
    expired_drawback = {
        "import_entry": "441-9872134-2",
        "export_bl": "EXP-2024-88412",
        "dutiable_value": "200000.00",
        "duties_paid": "20000.00",
        "drawback_percentage": "0.99",
        "is_timely_5yr_window": False, # Outside statutory 5-year window
    }
    metrics, discrepancies = audit_duty_drawback(expired_drawback)
    assert metrics.drawback_unclaimed_unlocked == Decimal("0.00")
    assert len(discrepancies) == 1
    assert "5-Year Limit" in discrepancies[0].title
    assert discrepancies[0].statutory_code == "19 U.S.C. 1313(r)(1)"


def test_freight_missing_free_days_no_fabrication():
    """C2: Missing port free days or actual days held must not fabricate a violation."""
    partial_freight = {
        "invoice_number": "FB-TEST-001",
        "detention_billed": "100.00"
    }
    metrics, discrepancies = audit_freight_bill(partial_freight)
    assert metrics.carrier_overbilling_caught == Decimal("0.00")
    detention_discs = [d for d in discrepancies if "Detention" in d.title]
    assert len(detention_discs) == 0


def test_drawback_missing_entry_no_fabrication():
    """C2: Duties paid without paired import entry must return 0 unlocked drawback."""
    partial_drawback = {"duties_paid": "1000.00"}
    metrics, discrepancies = audit_duty_drawback(partial_drawback)
    assert metrics.drawback_unclaimed_unlocked == Decimal("0.00")
    assert all(d.exposure_amount == Decimal("0.00") for d in discrepancies)
    assert [d.id for d in discrepancies] == ["disc-c3-insufficient"]


def test_drawback_missing_export_bl_no_fabrication():
    """C2: Import entry without export B/L must return 0 unlocked drawback."""
    partial_drawback = {
        "duties_paid": "1000.00",
        "import_entry": "441-1234567-8"
    }
    metrics, discrepancies = audit_duty_drawback(partial_drawback)
    assert metrics.drawback_unclaimed_unlocked == Decimal("0.00")
    assert all(d.exposure_amount == Decimal("0.00") for d in discrepancies)


def test_freight_explicit_values_still_work():
    """Verify that complete freight bills still catch all overbillings accurately."""
    full_freight = {
        "invoice_number": "FB-2024-FULL",
        "base_freight": "4500.00",
        "billed_fsc_rate": "0.325",
        "authorized_fsc_rate": "0.240",
        "chassis_split_fee": "285.00",
        "has_chassis_work_order": False,
        "port_free_days_allowed": 4,
        "actual_days_held": 4,
        "detention_billed": "880.00"
    }
    metrics, discrepancies = audit_freight_bill(full_freight)
    assert metrics.carrier_overbilling_caught == Decimal("1547.50")
    assert len(discrepancies) == 3
