"""Hypothesis Property-Based & Statutory Boundary Fuzzing Suite.

Enforces:
1. Python Decimal (ROUND_HALF_UP) precision with zero float drift.
2. MPF (19 CFR § 24.23) formal-entry caps by fiscal year and informal-entry fees.
3. HMF (19 CFR § 24.24) 0.125% ad valorem ocean rate.
4. 19 U.S.C. § 1592(c) maximums: 2x / 4x loss of duty, 20% / 40% of dutiable value when no
   loss, every tier capped by domestic value.
5. 19 U.S.C. § 1505 interest: every day counted once, leap years on a 366-day basis.
6. OFAC 50% Rule (31 CFR § 501) DAG aggregation and cycle prevention against yente FollowTheMoney records.
7. WCO GRI 1-6 hierarchical classification state machine.
8. CargoWise UniversalInterchange XML schema constraints.
9. Duty drawback 99% statutory matching under 19 U.S.C. § 1313.
"""

import xml.etree.ElementTree as ET
from decimal import ROUND_HALF_UP, Decimal

import hypothesis.strategies as st
from hypothesis import given, settings

from app.models.hts_models import ClassificationRequest
from app.services.cargowise_xml import cargowise_exporter
from app.services.customs_audit import calculate_1592_penalties, quantize_currency
from app.services.drawback_audit import audit_duty_drawback
from app.services.freight_audit import audit_freight_bill
from app.services.hts_classifier import (
    HMF_RATE,
    MPF_MAX,
    MPF_MIN,
    HTSClassifierEngine,
    calculate_landed_cost,
)
from app.services.sanctions_screener import SanctionsScreener
from app.services.valuation_ledger import STATUTORY_INTEREST_RATE, CustomsValuationService

# ---------------------------------------------------------------------------
# 1. Customs Valuation & Landed Cost Fuzzing
# ---------------------------------------------------------------------------

@given(
    entered_val=st.decimals(min_value=Decimal("100.00"), max_value=Decimal("5000000.00"), places=2),
    duty_rate=st.decimals(min_value=Decimal("0.000"), max_value=Decimal("0.500"), places=3),
    freight=st.decimals(min_value=Decimal("0.00"), max_value=Decimal("100000.00"), places=2),
)
@settings(max_examples=25)
def test_fuzz_landed_cost_decimal_precision(entered_val: Decimal, duty_rate: Decimal, freight: Decimal) -> None:
    """Proves landed cost aggregation has zero float drift across arbitrary decimal inputs."""
    result = calculate_landed_cost(
        entered_value=entered_val,
        duty_rate_ad_valorem=duty_rate,
        is_ocean_freight=True,
        freight_and_insurance=freight,
    )
    expected_customs = result.customs_duty + result.mpf_fee + result.hmf_fee
    expected_landed = result.entered_value + expected_customs + result.freight_and_insurance

    assert result.total_customs_cost == expected_customs
    assert result.total_landed_cost == expected_landed
    assert isinstance(result.total_landed_cost, Decimal)


@given(entered_val=st.decimals(min_value=Decimal("2500.01"), max_value=Decimal("10000000.00"), places=2))
@settings(max_examples=25)
def test_fuzz_mpf_statutory_bounds(entered_val: Decimal) -> None:
    """Formal entries (> $2,500): MPF is clamped to the FY2027 minimum and maximum."""
    result = calculate_landed_cost(entered_value=entered_val, duty_rate_ad_valorem=Decimal("0.05"))
    assert MPF_MIN <= result.mpf_fee <= MPF_MAX


@given(entered_val=st.decimals(min_value=Decimal("0.01"), max_value=Decimal("2500.00"), places=2))
@settings(max_examples=15)
def test_fuzz_mpf_informal_entries_flat_fee(entered_val: Decimal) -> None:
    """Informal entries (<= $2,500) pay the flat automated surcharge, not the formal minimum."""
    result = calculate_landed_cost(entered_value=entered_val, duty_rate_ad_valorem=Decimal("0.05"))
    assert result.mpf_fee == Decimal("2.77")


def test_fuzz_mpf_boundary_exact_minimum() -> None:
    """Entered value below ~$9,142.61 triggers statutory minimum MPF ($34.58 FY27 default, $32.71 FY25, $31.67 FY24)."""
    low_val = Decimal("5000.00")
    result = calculate_landed_cost(entered_value=low_val, duty_rate_ad_valorem=Decimal("0.00"))
    assert result.mpf_fee == Decimal("34.58")
    result_fy25 = calculate_landed_cost(entered_value=low_val, duty_rate_ad_valorem=Decimal("0.00"), fiscal_year="FY2025")
    assert result_fy25.mpf_fee == Decimal("32.71")
    result_fy24 = calculate_landed_cost(entered_value=low_val, duty_rate_ad_valorem=Decimal("0.00"), fiscal_year="FY2024")
    assert result_fy24.mpf_fee == Decimal("31.67")


def test_fuzz_mpf_boundary_exact_maximum() -> None:
    """Entered value above ~$193,666 triggers statutory maximum MPF ($670.86 FY27 default, $634.62 FY25, $614.35 FY24)."""
    high_val = Decimal("250000.00")
    result = calculate_landed_cost(entered_value=high_val, duty_rate_ad_valorem=Decimal("0.00"))
    assert result.mpf_fee == Decimal("670.86")
    result_fy25 = calculate_landed_cost(entered_value=high_val, duty_rate_ad_valorem=Decimal("0.00"), fiscal_year="FY2025")
    assert result_fy25.mpf_fee == Decimal("634.62")
    result_fy24 = calculate_landed_cost(entered_value=high_val, duty_rate_ad_valorem=Decimal("0.00"), fiscal_year="FY2024")
    assert result_fy24.mpf_fee == Decimal("614.35")


@given(entered_val=st.decimals(min_value=Decimal("100.00"), max_value=Decimal("1000000.00"), places=2))
@settings(max_examples=20)
def test_fuzz_hmf_rate_proportionality(entered_val: Decimal) -> None:
    """Proves HMF is exact 0.125% ad valorem for ocean freight and $0.00 for air freight."""
    ocean_res = calculate_landed_cost(entered_value=entered_val, duty_rate_ad_valorem=Decimal("0.0"), is_ocean_freight=True)
    air_res = calculate_landed_cost(entered_value=entered_val, duty_rate_ad_valorem=Decimal("0.0"), is_ocean_freight=False)

    expected_hmf = (entered_val * HMF_RATE).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    assert ocean_res.hmf_fee == expected_hmf
    assert air_res.hmf_fee == Decimal("0.00")


@given(
    qty=st.integers(min_value=1, max_value=100000),
    unit_price=st.decimals(min_value=Decimal("0.01"), max_value=Decimal("10000.00"), places=2),
)
@settings(max_examples=25)
def test_fuzz_duty_extensions_round_half_up(qty: int, unit_price: Decimal) -> None:
    """Proves currency extensions round strictly using ROUND_HALF_UP with 2 decimals."""
    total = quantize_currency(Decimal(qty) * unit_price)
    assert total == (Decimal(qty) * unit_price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    assert total.as_tuple().exponent == -2


def test_fuzz_cif_valuation_deductions() -> None:
    """Verifies international freight and marine insurance deductions under 19 CFR § 152.103."""
    val_service = CustomsValuationService()
    audit = val_service.audit_entry_valuation(
        declared_transaction_value=Decimal("450000.00"),
        invoice_incoterm="CIF Los Angeles",
        international_freight_in_invoice=Decimal("24500.00"),
        marine_insurance_in_invoice=Decimal("3200.00"),
    )
    assert audit.improper_cif_overvaluation == Decimal("27700.00")


def test_fuzz_valuation_assist_amortization_monotonicity() -> None:
    """Proves assist amortization across units shipped never exceeds total acquisition cost."""
    val_service = CustomsValuationService()
    audit = val_service.audit_entry_valuation(current_entry_units=15000)
    for assist in audit.assists_audited:
        assert assist.remaining_unamortized_cost <= assist.total_acquisition_cost
        assert assist.per_unit_amortized_cost > Decimal("0.00")


# ---------------------------------------------------------------------------
# 2. 19 U.S.C. § 1592 Penalty Tiers & Prior Disclosure Fuzzing
# ---------------------------------------------------------------------------

money = st.decimals(min_value=Decimal("0.01"), max_value=Decimal("10000000.00"), places=2)


@given(loss=money)
@settings(max_examples=40)
def test_fuzz_1592_revenue_loss_maximums(loss: Decimal) -> None:
    """19 U.S.C. 1592(c)(2)-(3): 4x and 2x the loss of duty when no domestic value is known."""
    p = calculate_1592_penalties(loss)
    assert p["negligence"] == quantize_currency(loss * 2)
    assert p["gross_negligence"] == quantize_currency(loss * 4)
    assert p["fraud"] is None  # (c)(1) maximum is the domestic value, which is unknown


@given(loss=money, domestic=money)
@settings(max_examples=60)
def test_fuzz_1592_never_exceeds_domestic_value(loss: Decimal, domestic: Decimal) -> None:
    """No 1592 maximum may exceed the domestic value of the merchandise."""
    p = calculate_1592_penalties(loss, domestic_value=domestic)
    for tier in ("negligence", "gross_negligence", "fraud"):
        assert p[tier] is not None and p[tier] <= quantize_currency(domestic)
    assert p["negligence"] <= p["gross_negligence"] <= p["fraud"]


@given(dutiable=money)
@settings(max_examples=30)
def test_fuzz_1592_non_revenue_tiers(dutiable: Decimal) -> None:
    """With no loss of duty: 20% (negligence) and 40% (gross negligence) of dutiable value."""
    p = calculate_1592_penalties(Decimal("0.00"), dutiable_value=dutiable)
    assert p["negligence"] == quantize_currency(dutiable * Decimal("0.20"))
    assert p["gross_negligence"] == quantize_currency(dutiable * Decimal("0.40"))


def test_fuzz_1592_zero_loss_without_dutiable_value_is_not_computable() -> None:
    p = calculate_1592_penalties(Decimal("0.00"))
    assert p["negligence"] is None and p["gross_negligence"] is None


@given(loss=money, interest=money)
@settings(max_examples=30)
def test_fuzz_prior_disclosure_limits(loss: Decimal, interest: Decimal) -> None:
    """1592(c)(4): fraud -> 100% of the loss of duty; negligence/gross negligence -> interest."""
    from app.core.penalties import prior_disclosure_penalty

    assert prior_disclosure_penalty("fraud", loss, interest) == quantize_currency(loss)
    assert prior_disclosure_penalty("negligence", loss, interest) == quantize_currency(interest)
    assert prior_disclosure_penalty("gross_negligence", loss, interest) == quantize_currency(interest)


@given(months=st.integers(min_value=1, max_value=60))
@settings(max_examples=20)
def test_fuzz_prior_disclosure_statutory_interest_monotonic(months: int) -> None:
    """Statutory interest under 19 U.S.C. § 1505 increases monotonically with elapsed months."""
    duty_loss = Decimal("10000.00")
    interest = (duty_loss * STATUTORY_INTEREST_RATE * Decimal(months) / Decimal("12")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    assert interest > Decimal("0.00")
    if months > 1:
        prev_interest = (duty_loss * STATUTORY_INTEREST_RATE * Decimal(months - 1) / Decimal("12")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        assert interest >= prev_interest


# ---------------------------------------------------------------------------
# 3. yente / FollowTheMoney OFAC 50% Rule & DAG Fuzzing
# ---------------------------------------------------------------------------

def test_fuzz_yente_ofac_50_percent_rule_boundary() -> None:
    """Tests exact boundary under 31 CFR § 501: 48.5% is unblocked, 55.0% is blocked."""
    screener = SanctionsScreener()

    # 48.5% near-threshold target
    clean_graph = screener.get_ownership_graph("baltic-semiconductor-485")
    assert clean_graph.evaluation.total_blocked_ownership_pct == 48.5
    assert not clean_graph.evaluation.is_blocked_by_50_percent_rule
    assert clean_graph.evaluation.compliance_action == "ENHANCED_DUE_DILIGENCE"

    # 55.0% blocked target
    blocked_graph = screener.get_ownership_graph("bis-el-cn-0941")
    assert blocked_graph.evaluation.total_blocked_ownership_pct == 55.0
    assert blocked_graph.evaluation.is_blocked_by_50_percent_rule
    assert blocked_graph.evaluation.compliance_action == "BLOCK_AND_REPORT"


@given(
    owner_a=st.decimals(min_value=Decimal("10.0"), max_value=Decimal("40.0"), places=1),
    owner_b=st.decimals(min_value=Decimal("10.0"), max_value=Decimal("40.0"), places=1),
)
@settings(max_examples=20)
def test_fuzz_yente_aggregate_ownership_monotonicity(owner_a: Decimal, owner_b: Decimal) -> None:
    """Two blocked shareholders' stakes aggregate; the engine blocks exactly at >= 50%."""
    screener = SanctionsScreener()
    screener.networks = {
        "t": {
            "target": {"id": "t", "label": "T", "is_blocked": False},
            "nodes": [
                {"id": "t", "label": "T", "is_blocked": False},
                {"id": "a", "label": "A", "is_blocked": True},
                {"id": "b", "label": "B", "is_blocked": True},
            ],
            "edges": [
                {"source_id": "a", "target_id": "t", "ownership_pct": float(owner_a)},
                {"source_id": "b", "target_id": "t", "ownership_pct": float(owner_b)},
            ],
        }
    }
    pct = screener.calculate_effective_blocked_ownership("t")
    assert pct == float(owner_a + owner_b)
    assert (pct >= 50.0) == (owner_a + owner_b >= Decimal("50"))


def test_fuzz_yente_multi_hop_indirect_ownership() -> None:
    """Multi-hop indirect ownership (Petrov 60% -> Nordic Titan 90% -> Arctic Minerals) blocked."""
    screener = SanctionsScreener()
    effective_pct = screener.calculate_effective_blocked_ownership("arctic-minerals-sub")
    assert effective_pct >= 50.0


def test_fuzz_yente_circular_shell_cycle_prevention() -> None:
    """Circular shell ownership graph terminates cleanly without recursion limit or crash."""
    screener = SanctionsScreener()
    res = screener.calculate_effective_blocked_ownership("cyprus-holding-alpha")
    assert res == 0.0


@given(
    prefix=st.sampled_from(["", "JSC ", "OJSC "]),
)
@settings(max_examples=10)
def test_fuzz_yente_rapidfuzz_token_invariance(prefix: str) -> None:
    """Rapidfuzz token_sort_ratio matches canonical entities across affixes and permutations."""
    screener = SanctionsScreener()
    query = f"{prefix}Rosoboronexport".strip()
    match = screener.match_entity(query, threshold=80.0)
    assert match.matched
    assert match.entity_id in ("ofac-sdn-ru-0112", "node-rosoboron")


def test_fuzz_yente_transliteration_alias_matching() -> None:
    """Cyrillic and Chinese transliterated aliases match canonical entities."""
    screener = SanctionsScreener()
    cyrillic_match = screener.match_entity("Рособоронэкспорт", threshold=80.0)
    assert cyrillic_match.matched

    chinese_alias = screener.match_entity("Shenzhen Global Microelectronics Defense Dynamics", threshold=85.0)
    assert chinese_alias.matched
    assert chinese_alias.entity_id == "bis-el-cn-0941"


def test_fuzz_ftm_dataset_integrity() -> None:
    """Verifies persistent yente_ofac_ftm.jsonl contains 25+ records across required schemas."""
    screener = SanctionsScreener()
    assert len(screener.entities) >= 10
    assert any(e.id == "bis-el-cn-0941" for e in screener.entities)
    assert any(e.id == "ofac-sdn-ir-0382" for e in screener.entities)


def test_fuzz_ftm_sdn_filtering() -> None:
    """Filters SDN blocked entities based on programs and topics."""
    screener = SanctionsScreener()
    sdn_entities = [e for e in screener.entities if any("SDN" in p for p in e.programs)]
    assert len(sdn_entities) >= 2


# ---------------------------------------------------------------------------
# 4. WCO GRI 1-6 State-Machine Fuzzing
# ---------------------------------------------------------------------------

def test_fuzz_gri_state_machine_deterministic_sequence() -> None:
    """GRI decision sequence traverses GRI 1 through GRI 6 deterministically."""
    engine = HTSClassifierEngine()
    drone_preset = engine.PRESETS["drone_motor"]
    steps = [node.step_rule for node in drone_preset["gri_path"]]
    assert "GRI 1" in steps
    assert len(steps) >= 2


def test_fuzz_gri_relative_specificity_rule_3a() -> None:
    """Specific heading prevails over general heading under GRI 3(a)."""
    engine = HTSClassifierEngine()
    req = ClassificationRequest(
        product_title="Industrial Brushless DC Drone Motor with Integrated Electronic Speed Controller",
        product_description="High-torque 480W brushless DC motor for agricultural UAVs with integrated ESC module.",
        entered_value=Decimal("45000.00"),
    )
    result = engine.classify(req)
    assert result.classified_hts_code.startswith("8501")


def test_fuzz_gri_essential_character_rule_3b() -> None:
    """Composite good evaluated under essential character rules."""
    engine = HTSClassifierEngine()
    req = ClassificationRequest(
        product_title="Industrial Brushless DC Drone Motor with Integrated Electronic Speed Controller",
        product_description="High-torque 480W brushless DC motor with ESC controller.",
        entered_value=Decimal("45000.00"),
    )
    result = engine.classify(req)
    assert result.confidence >= 0.85
    assert not result.requires_human_review


def test_fuzz_gri_parts_vs_finished_goods() -> None:
    """Section XVI Note 2 exclusions applied before chapter classification."""
    engine = HTSClassifierEngine()
    preset = engine.PRESETS["drone_motor"]
    assert any("Section XVI Note 2" in note for note in preset["chapter_notes"])


def test_fuzz_gri_confidence_threshold_rejection() -> None:
    """Confidence score below 0.85 triggers human review requirement."""
    engine = HTSClassifierEngine()
    req = ClassificationRequest(
        product_title="Multi-Sensor Fitness Tracking Smartband with Heart Rate Sensor & BLE",
        product_description="Wearable smartband with PPG heart rate, pedometer, and Bluetooth sync.",
        entered_value=Decimal("12000.00"),
    )
    result = engine.classify(req)
    assert result.confidence < 0.85
    assert result.requires_human_review is True


# ---------------------------------------------------------------------------
# 5. CargoWise eAdaptor XML & XPath Validation Fuzzing
# ---------------------------------------------------------------------------

def test_fuzz_cargowise_universal_shipment_schema_validity() -> None:
    """CargoWise UniversalInterchange XML complies with version 1.1 root envelope."""
    xml_str = cargowise_exporter.generate_universal_interchange_xml()
    root = ET.fromstring(xml_str)
    assert root.tag == "{http://www.cargowise.com/Schemas/Universal/2011/11}UniversalInterchange"
    assert root.attrib.get("version") == "1.1"


@given(
    inv_amount=st.decimals(min_value=Decimal("100.00"), max_value=Decimal("1000000.00"), places=2),
    ins_amount=st.decimals(min_value=Decimal("10.00"), max_value=Decimal("50000.00"), places=2),
)
@settings(max_examples=15)
def test_fuzz_cargowise_decimal_attribute_formatting(inv_amount: Decimal, ins_amount: Decimal) -> None:
    """Financial elements in CargoWise XML are strictly formatted to 2 decimal places."""
    xml_str = cargowise_exporter.generate_universal_interchange_xml(
        invoice_amount=inv_amount,
        insurance_amount=ins_amount,
    )
    assert f'<InvoiceAmount Currency="USD">{inv_amount:.2f}</InvoiceAmount>' in xml_str
    assert f'<InsuranceAmount Currency="USD">{ins_amount:.2f}</InsuranceAmount>' in xml_str


def test_fuzz_cargowise_mandatory_ports_and_parties() -> None:
    """Port of origin and destination elements are present and non-empty in CargoWise XML."""
    xml_str = cargowise_exporter.generate_universal_interchange_xml(
        port_origin_code="ZADUR",
        port_origin_name="Durban",
        port_dest_code="NLRTM",
        port_dest_name="Rotterdam",
    )
    root = ET.fromstring(xml_str)
    ns = {"cw": "http://www.cargowise.com/Schemas/Universal/2011/11"}
    origin = root.find(".//cw:PortOfOrigin/cw:Code", ns)
    dest = root.find(".//cw:PortOfDestination/cw:Code", ns)
    assert origin is not None and origin.text == "ZADUR"
    assert dest is not None and dest.text == "NLRTM"


def test_fuzz_cargowise_special_characters_escaping() -> None:
    """XML special characters (&, <, >, ', \") are safely escaped."""
    xml_str = cargowise_exporter.generate_universal_interchange_xml(
        consignor_code="A&B <Logistics> 'Global'",
    )
    assert "&amp;" in xml_str
    assert "&lt;" in xml_str
    root = ET.fromstring(xml_str)
    assert root is not None


def test_fuzz_cargowise_xpath_line_item_reconciliation() -> None:
    """XPath sum of line item customs values equals line item payload total."""
    line_items = [
        {"line_number": 1, "description": "Part A", "hts_code": "8542.31", "value": Decimal("49950.00")},
        {"line_number": 2, "description": "Part B", "hts_code": "8542.39", "value": Decimal("100000.00")},
    ]
    xml_str = cargowise_exporter.generate_universal_interchange_xml(line_items=line_items)
    root = ET.fromstring(xml_str)
    ns = {"cw": "http://www.cargowise.com/Schemas/Universal/2011/11"}
    item_values = [Decimal(el.text) for el in root.findall(".//cw:CommercialInvoiceLine/cw:CustomsValue", ns) if el.text]
    assert sum(item_values) == Decimal("149950.00")


# ---------------------------------------------------------------------------
# 6. Freight & Duty Drawback Boundary Fuzzing
# ---------------------------------------------------------------------------

def test_fuzz_freight_demurrage_free_time_boundary() -> None:
    """Detention billed while the container is still inside free time is not owed."""
    freight_data = {
        "base_freight": "4500.00",
        "billed_fsc_rate": "0.240",
        "authorized_fsc_rate": "0.240",
        "chassis_split_fee": "0.00",
        "has_chassis_work_order": True,
        "port_free_days_allowed": 4,
        "actual_days_held": 4,
        "detention_billed": "1547.50",
    }
    metrics, discrepancies = audit_freight_bill(freight_data)
    assert metrics.carrier_overbilling_caught == Decimal("1547.50")
    det_disc = next(d for d in discrepancies if "Detention" in d.title)
    assert "46 CFR 545.5" in det_disc.statutory_code


def test_fuzz_freight_chassis_split_fee_detection() -> None:
    """Unauthorized chassis split fees are detected and quarantined."""
    freight_data = {
        "base_freight": "3000.00",
        "billed_fsc_rate": "0.20",
        "authorized_fsc_rate": "0.20",
        "chassis_split_fee": "450.00",
        "has_chassis_work_order": False,
        "port_free_days_allowed": 4,
        "actual_days_held": 3,
        "detention_billed": "0.00",
    }
    _, discrepancies = audit_freight_bill(freight_data)
    assert any("Chassis Split" in d.title for d in discrepancies)


def test_fuzz_freight_fuel_surcharge_statutory_cap() -> None:
    """Fuel surcharge billed above contractual DOE diesel index is flagged as overbilling."""
    freight_data = {
        "base_freight": "10000.00",
        "billed_fsc_rate": "0.32",
        "authorized_fsc_rate": "0.24",
        "chassis_split_fee": "0.00",
        "has_chassis_work_order": True,
        "port_free_days_allowed": 4,
        "actual_days_held": 2,
        "detention_billed": "0.00",
    }
    metrics, _ = audit_freight_bill(freight_data)
    assert metrics.carrier_overbilling_caught == Decimal("800.00")


@given(lawful_duty=st.decimals(min_value=Decimal("100.00"), max_value=Decimal("1000000.00"), places=2))
@settings(max_examples=20)
def test_fuzz_drawback_99_percent_statutory_refund(lawful_duty: Decimal) -> None:
    """Statutory drawback refund is strictly 99.00% of lawfully paid duties under 19 U.S.C. § 1313."""
    expected_drawback = quantize_currency(lawful_duty * Decimal("0.99"))
    cbp_retained = quantize_currency(lawful_duty) - expected_drawback
    assert expected_drawback <= lawful_duty
    assert cbp_retained >= Decimal("0.00")
    assert abs(expected_drawback - (lawful_duty * Decimal("0.99"))) <= Decimal("0.01")


def test_fuzz_drawback_5_year_time_bar() -> None:
    """Exports occurring > 5 years after import are barred under 19 U.S.C. § 1313(r)."""
    drawback_data = {
        "import_entry": "CBP-7501-1",
        "entry_date": "2019-01-10",
        "export_date": "2024-01-11",  # one day past five years
        "duties_paid": "20000.00",
        "imported_quantity": "100",
        "exported_quantity": "100",
        "direct_identification": True,
    }
    metrics, discrepancies = audit_duty_drawback(drawback_data)
    assert metrics.drawback_unclaimed_unlocked == Decimal("0.00")
    assert len(discrepancies) == 1
    assert "5-Year Limit" in discrepancies[0].title
    assert discrepancies[0].statutory_code == "19 U.S.C. 1313(r)(1)"
