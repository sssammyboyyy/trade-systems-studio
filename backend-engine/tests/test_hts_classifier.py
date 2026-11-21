"""Test suite for Autonomous HTS Classification Copilot & Landed Cost Engine."""

from decimal import Decimal

from fastapi.testclient import TestClient

from app.models.hts_models import ClassificationRequest
from app.services.hts_classifier import HTSClassifierEngine, calculate_landed_cost
from main import app

client = TestClient(app)


def test_landed_cost_mathematical_precision():
    """Verify landed cost calculation using strict Python Decimal and statutory rules."""
    entered_val = Decimal("100000.00")
    duty_rate = Decimal("0.025")  # 2.5%
    freight = Decimal("2000.00")

    breakdown = calculate_landed_cost(
        entered_value=entered_val,
        duty_rate_ad_valorem=duty_rate,
        is_ocean_freight=True,
        freight_and_insurance=freight,
    )

    assert breakdown.customs_duty == Decimal("2500.00")
    # MPF: 100,000 * 0.003464 = 346.40 (within 31.67 and 614.35)
    assert breakdown.mpf_fee == Decimal("346.40")
    # HMF: 100,000 * 0.00125 = 125.00
    assert breakdown.hmf_fee == Decimal("125.00")
    assert breakdown.total_customs_cost == Decimal("2971.40")
    assert breakdown.total_landed_cost == Decimal("104971.40")


def test_mpf_statutory_minimum_cap():
    """Formal entry ($5,000): MPF is floored at the statutory minimum ($34.58 for FY2027 active default, $32.71 for FY2025, $31.67 for FY2024)."""
    # FY2027 active default (91 FR 48398)
    breakdown_fy27 = calculate_landed_cost(
        entered_value=Decimal("5000.00"),
        duty_rate_ad_valorem=Decimal("0.05"),
        is_ocean_freight=False,
    )
    assert breakdown_fy27.mpf_fee == Decimal("34.58")
    assert breakdown_fy27.hmf_fee == Decimal("0.00")  # Air freight has no HMF

    # FY2025 backward compatibility
    breakdown_fy25 = calculate_landed_cost(
        entered_value=Decimal("5000.00"),
        duty_rate_ad_valorem=Decimal("0.05"),
        is_ocean_freight=False,
        fiscal_year="FY2025",
    )
    assert breakdown_fy25.mpf_fee == Decimal("32.71")

    # FY2024 backward compatibility
    breakdown_fy24 = calculate_landed_cost(
        entered_value=Decimal("5000.00"),
        duty_rate_ad_valorem=Decimal("0.05"),
        is_ocean_freight=False,
        fiscal_year="FY2024",
    )
    assert breakdown_fy24.mpf_fee == Decimal("31.67")


def test_mpf_informal_entry_and_fiscal_year():
    from datetime import date

    from app.core.statutory_rates import calculate_mpf, fiscal_year_for

    assert calculate_mpf(Decimal("800.00"), "FY2027") == Decimal("2.77")
    assert calculate_mpf(Decimal("800.00"), "FY2027", informal_method="cbp_prepared") == Decimal("12.45")
    assert calculate_mpf(Decimal("100000.00"), "FY2026") == Decimal("346.40")
    assert calculate_mpf(Decimal("5000.00"), "FY2026") == Decimal("33.58")  # FR Doc. 2025-13869
    assert calculate_mpf(Decimal("900000.00"), "FY2026") == Decimal("651.50")
    assert calculate_mpf(Decimal("50000.00"), "FY2027", fta_exempt=True) == Decimal("0.00")
    assert fiscal_year_for(date(2026, 9, 30)) == "FY2026"
    assert fiscal_year_for(date(2026, 10, 1)) == "FY2027"


def test_mpf_statutory_maximum_cap():
    """Verify MPF is capped at statutory maximum ($670.86 for FY2027 active default, $634.62 for FY2025, $614.35 for FY2024)."""
    # FY2027 active default
    breakdown_fy27 = calculate_landed_cost(
        entered_value=Decimal("500000.00"),
        duty_rate_ad_valorem=Decimal("0.05"),
        is_ocean_freight=True,
    )
    assert breakdown_fy27.mpf_fee == Decimal("670.86")

    # FY2025 backward compatibility
    breakdown_fy25 = calculate_landed_cost(
        entered_value=Decimal("500000.00"),
        duty_rate_ad_valorem=Decimal("0.05"),
        is_ocean_freight=True,
        fiscal_year="FY2025",
    )
    assert breakdown_fy25.mpf_fee == Decimal("634.62")

    # FY2024 backward compatibility
    breakdown_fy24 = calculate_landed_cost(
        entered_value=Decimal("500000.00"),
        duty_rate_ad_valorem=Decimal("0.05"),
        is_ocean_freight=True,
        fiscal_year="FY2024",
    )
    assert breakdown_fy24.mpf_fee == Decimal("614.35")


def test_section_301_origin_aware_tariff_calculation():
    """Verify Section 301 +25.0% surcharge applies strictly to CN origin for covered HTS lines."""
    # Origin CN: Triggers 25% Section 301
    breakdown_cn = calculate_landed_cost(
        entered_value=Decimal("100000.00"),
        duty_rate_ad_valorem=Decimal("0.024"),
        hts_code="8501.31.8000",
        country_of_origin="CN",
    )
    assert breakdown_cn.customs_duty == Decimal("2400.00")
    assert breakdown_cn.section_301_rate == Decimal("0.250")
    assert breakdown_cn.section_301_duty == Decimal("25000.00")
    assert breakdown_cn.section_301_subheading == "9903.88.01"

    # Origin TW: Free of Section 301
    breakdown_tw = calculate_landed_cost(
        entered_value=Decimal("100000.00"),
        duty_rate_ad_valorem=Decimal("0.024"),
        hts_code="8501.31.8000",
        country_of_origin="TW",
    )
    assert breakdown_tw.customs_duty == Decimal("2400.00")
    assert breakdown_tw.section_301_rate == Decimal("0.00")
    assert breakdown_tw.section_301_duty == Decimal("0.00")
    assert breakdown_tw.section_301_subheading is None


def test_wco_gri_drone_motor_classification():
    """Verify GRI 1-6 hierarchical decision tree traversal for drone motor with ESC."""
    engine = HTSClassifierEngine()
    req = ClassificationRequest(
        product_title="Industrial Brushless DC Drone Motor with Integrated Electronic Speed Controller",
        product_description="High-torque 480W brushless DC motor for agricultural UAVs with integrated ESC module.",
        entered_value=Decimal("45000.00"),
        is_ocean_freight=True,
    )
    result = engine.classify(req)

    assert result.classified_hts_code == "8501.31.8000"
    assert result.confidence >= 0.85
    assert not result.requires_human_review
    assert len(result.gri_path) >= 3
    assert result.gri_path[0].step_rule == "GRI 1"
    assert "8501" in result.gri_path[1].heading_or_subheading
    assert any("Section XVI" in note for note in result.chapter_notes_cited)


def test_low_confidence_triggers_human_review():
    """Verify confidence < 0.85 triggers dashed amber review requirement."""
    engine = HTSClassifierEngine()
    req = ClassificationRequest(
        product_title="Multi-Sensor Fitness Tracking Smartband with Heart Rate Sensor & BLE",
        product_description="Wearable smartband with PPG heart rate, pedometer, and Bluetooth sync.",
        entered_value=Decimal("12000.00"),
    )
    result = engine.classify(req)

    assert result.classified_hts_code == "8517.62.0050"
    assert result.confidence < 0.85
    assert result.requires_human_review is True


def test_hts_api_endpoints():
    """Verify HTTP API endpoints for HTS classification and presets."""
    response = client.get("/api/v1/hts/preset/server_accelerator?entered_value=50000")
    assert response.status_code == 200
    data = response.json()
    assert data["classified_hts_code"] == "8542.31.0001"
    assert data["landed_cost"]["entered_value"] == "50000.00"
    assert data["landed_cost"]["customs_duty"] == "0.00"  # ITA free duty


def test_unclassified_product_requires_human_review():
    """Verify unclassified merchandise does not default to drone motor and requires broker review."""
    engine = HTSClassifierEngine()
    req = ClassificationRequest(
        product_title="Fresh Organic Honeycrisp Apples",
        product_description="Grade A edible fresh apples packaged in crates.",
        entered_value=Decimal("8000.00"),
    )
    result = engine.classify(req)
    assert result.classified_hts_code == "REQUIRES_BROKER_REVIEW"
    assert result.confidence == 0.0
    assert result.requires_human_review is True
    assert result.item_id == "hts-unclassified"


def test_word_boundary_esc_does_not_match_telescope():
    """Verify word boundary regex prevents substring false matches like 'esc' in 'telescope'."""
    engine = HTSClassifierEngine()
    req = ClassificationRequest(
        product_title="High Precision Astronomical Telescope",
        product_description="Optical astronomical observation telescope tube and mount.",
        entered_value=Decimal("15000.00"),
    )
    result = engine.classify(req)
    # Must not match 'drone_motor' via substring 'esc' in 'telescope'
    assert result.classified_hts_code == "REQUIRES_BROKER_REVIEW"
    assert result.requires_human_review is True
    assert result.item_id != "hts-drone_motor"
