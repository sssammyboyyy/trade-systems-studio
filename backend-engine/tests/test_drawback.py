from decimal import Decimal

from app.services.drawback_audit import audit_duty_drawback

BASE = {
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


def test_duty_drawback_audit_full_match():
    metrics, discrepancies = audit_duty_drawback(BASE)
    assert metrics.drawback_unclaimed_unlocked == Decimal("27324.00")  # 99% of $27,600
    recovery = next(d for d in discrepancies if d.id == "disc-c3-01")
    assert recovery.statutory_code == "19 U.S.C. 1313(j)(1)"
    assert recovery.metadata["basis"] == "j1"
    match = next(d for d in discrepancies if d.id == "disc-c3-02")
    assert match.metadata["quantity_match"] == "100%"


def test_partial_export_limits_refund_to_exported_quantity():
    metrics, _ = audit_duty_drawback({**BASE, "exported_quantity": "400"})
    # 400 of 1,000 units: 400 x $27.60 x 99% = $10,929.60
    assert metrics.drawback_unclaimed_unlocked == Decimal("10929.60")


def test_substitution_requires_same_8_digit_hts():
    data = {**BASE, "direct_identification": False, "import_hts": "8542.31.0001", "export_hts": "8542.31.0045"}
    metrics, discrepancies = audit_duty_drawback(data)
    assert metrics.drawback_unclaimed_unlocked == Decimal("27324.00")
    assert discrepancies[0].metadata["basis"] == "j2"

    m2, d2 = audit_duty_drawback({**data, "export_hts": "8542.32.0010"})
    assert m2.drawback_unclaimed_unlocked == Decimal("0.00")
    assert d2[0].id == "disc-c3-insufficient"


def test_five_year_limit_computed_from_dates():
    metrics, discrepancies = audit_duty_drawback({**BASE, "export_date": "2029-01-16"})
    assert metrics.drawback_unclaimed_unlocked == Decimal("0.00")
    assert discrepancies[0].id == "disc-c3-expired"

    m2, d2 = audit_duty_drawback({**BASE, "claim_date": "2029-01-16"})
    assert m2.drawback_unclaimed_unlocked == Decimal("0.00")
    assert d2[0].id == "disc-c3-expired"


def test_no_refund_without_quantities():
    data = {k: v for k, v in BASE.items() if k not in ("imported_quantity", "exported_quantity")}
    metrics, discrepancies = audit_duty_drawback(data)
    assert metrics.drawback_unclaimed_unlocked == Decimal("0.00")
    assert discrepancies[0].severity == "info"
