from decimal import Decimal

from app.services.customs_audit import audit_customs_invoice, calculate_1592_penalties


def test_1592_statutory_maximums_without_domestic_value():
    loss = Decimal("31250.00")
    penalties = calculate_1592_penalties(loss)
    # 19 U.S.C. 1592(c)(3) and (c)(2): 2x and 4x the loss of duty
    assert penalties["negligence"] == Decimal("62500.00")
    assert penalties["gross_negligence"] == Decimal("125000.00")
    # (c)(1): fraud is capped by domestic value, unknown here
    assert penalties["fraud"] is None


def test_1592_domestic_value_caps_every_tier():
    # Loss $31,250 and domestic value $20,000: every maximum is $20,000
    penalties = calculate_1592_penalties(Decimal("31250.00"), domestic_value=Decimal("20000.00"))
    assert penalties == {
        "negligence": Decimal("20000.00"),
        "gross_negligence": Decimal("20000.00"),
        "fraud": Decimal("20000.00"),
    }


def test_1592_non_revenue_loss_tiers_use_dutiable_value():
    # No loss of duty: 20% (negligence) and 40% (gross negligence) of dutiable value
    penalties = calculate_1592_penalties(Decimal("0.00"), dutiable_value=Decimal("100000.00"))
    assert penalties["negligence"] == Decimal("20000.00")
    assert penalties["gross_negligence"] == Decimal("40000.00")


def test_customs_invoice_audit_errors():
    test_data = {
        "incoterms": "CIF LOS ANGELES",
        "insurance_charge": "0.00",
        "misclassified_value": "125000.00",
        "declared_duty_rate": "0.00",
        "lawful_duty_rate": "0.25",
        "entry_date": "2024-04-12",
        "as_of_date": "2026-11-20",
        "items": [{"line_number": 1, "quantity": "500", "unit_price": "45.00", "stated_total": "25500.00"}],
    }

    metrics, discrepancies = audit_customs_invoice(test_data)

    # Default culpability is negligence: 2 x $31,250 loss of duty
    assert metrics.penalty_exposure_avoided == Decimal("62500.00")
    assert len(discrepancies) == 3

    cif_disc = next(d for d in discrepancies if "CIF" in d.title)
    assert cif_disc.severity == "info"
    assert cif_disc.exposure_amount == Decimal("0.00")  # no invented 1% insurance estimate

    math_disc = next(d for d in discrepancies if "Arithmetic" in d.title)
    assert math_disc.exposure_amount == Decimal("3000.00")
    assert math_disc.severity == "critical"

    hts_disc = next(d for d in discrepancies if "HTS Misclassification" in d.title)
    assert hts_disc.exposure_amount == Decimal("62500.00")
    assert hts_disc.metadata["culpability_assumed"] == "negligence"
    assert hts_disc.metadata["statutory_max_by_culpability"]["gross_negligence"] == "125000.00"
    assert hts_disc.statutory_code == "19 U.S.C. 1592(c)"
    # Prior disclosure for negligence limits the penalty to interest, computed from real dates
    assert hts_disc.metadata["interest_basis"].startswith("19 U.S.C. 1505, 2024-04-12")


def test_zero_lawful_rate_is_not_replaced_by_25_percent():
    """Decimal('0.00') is falsy; an explicit 0% rate must stay 0%, not fall back to 25%."""
    payload = {
        "incoterms": "CIF LOS ANGELES",
        "freight_charge": "1000.00",
        "items": [{"line_number": 1, "quantity": "1", "unit_price": "10000.00", "stated_total": "10000.00", "duty_rate": "0.00"}],
    }
    _, discrepancies = audit_customs_invoice(payload)
    cif = next(d for d in discrepancies if d.id == "disc-c1-01")
    assert cif.exposure_amount == Decimal("0.00")
    assert cif.metadata["estimated_excess_duty"] == "0.00"


def test_customs_dynamic_hts_and_cif_excess_duty():
    custom_payload = {
        "incoterms": "CIF LONG BEACH",
        "freight_charge": "5000.00",
        "insurance_charge": "0.00",
        "misclassified_value": "80000.00",
        "declared_duty_rate": "0.024",
        "lawful_duty_rate": "0.274",
        "declared_hts": "8501.31.8000",
        "lawful_hts": "8501.31.2000",
        "product_description": "Industrial Brushless DC Drone Motors",
        "items": [
            {
                "line_number": 1,
                "description": "Industrial Brushless DC Drone Motors",
                "declared_hts": "8501.31.8000",
                "lawful_hts": "8501.31.2000",
                "quantity": "200",
                "unit_price": "400.00",
                "stated_total": "80000.00",
                "duty_rate": "0.024",
            }
        ],
    }

    _, discrepancies = audit_customs_invoice(custom_payload)

    # Freight is deducted at the rate actually declared on the lines: $5,000 x 2.4% = $120.00
    cif_disc = next(d for d in discrepancies if d.id == "disc-c1-01")
    assert cif_disc.metadata["non_dutiable_charges"] == "5000.00"
    assert cif_disc.metadata["estimated_excess_duty"] == "120.00"
    assert cif_disc.exposure_amount == Decimal("120.00")

    hts_disc = next(d for d in discrepancies if "HTS Misclassification" in d.title)
    assert "Industrial Brushless DC Drone Motors" in hts_disc.description
    assert "8501.31.8000" in hts_disc.description
    assert "8501.31.2000" in hts_disc.description
    assert hts_disc.metadata["declared_hts"] == "8501.31.8000"
    assert hts_disc.metadata["lawful_hts"] == "8501.31.2000"
