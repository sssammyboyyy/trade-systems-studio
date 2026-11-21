from decimal import Decimal

from app.services.freight_audit import audit_freight_bill


def test_freight_bill_audit():
    test_data = {
        "base_freight": "4500.00",
        "billed_fsc_rate": "0.325",
        "authorized_fsc_rate": "0.240",
        "chassis_split_fee": "285.00",
        "has_chassis_work_order": False,
        "port_free_days_allowed": 4,
        "actual_days_held": 4,
        "detention_billed": "880.00"
    }

    metrics, discrepancies = audit_freight_bill(test_data)
    
    # Total overcharges = 382.50 (FSC) + 285.00 (Chassis) + 880.00 (Detention) = 1547.50
    assert metrics.carrier_overbilling_caught == Decimal("1547.50")
    assert len(discrepancies) == 3
    
    # Find FSC overcharge
    fsc_disc = next(d for d in discrepancies if "Fuel Surcharge" in d.title)
    assert fsc_disc.exposure_amount == Decimal("382.50")
    
    # Find Chassis split overcharge
    chassis_disc = next(d for d in discrepancies if "Chassis Split" in d.title)
    assert chassis_disc.exposure_amount == Decimal("285.00")
    
    # Find Free time detention
    det_disc = next(d for d in discrepancies if "Detention" in d.title)
    assert det_disc.exposure_amount == Decimal("880.00")
    assert "46 CFR 545.5" in det_disc.statutory_code
