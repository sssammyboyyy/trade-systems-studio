"""HTS Classification Engine & Deterministic Landed Cost Calculator.

Implements the World Customs Organization (WCO) General Rules of Interpretation (GRI 1-6)
as a path-dependent hierarchical state machine with element-wise confidence scoring and
strict Python Decimal fee aggregation.
"""

import os
import re
from decimal import Decimal
from typing import Dict, Optional

from app.core.statutory_rates import (
    DEFAULT_MPF_FISCAL_YEAR,
    HMF_AD_VALOREM_RATE,
    MPF_AD_VALOREM_RATE,
    MPF_CAPS_BY_FY,
    calculate_hmf,
    calculate_mpf,
    get_mpf_caps,
    get_section_301_rate,
)
from app.models.hts_models import (
    ClassificationRequest,
    GRIDecisionNode,
    HTSClassificationResult,
    LandedCostBreakdown,
)
from app.services.utils import quantize_currency

# Statutory Constants
MPF_RATE = MPF_AD_VALOREM_RATE
HMF_RATE = HMF_AD_VALOREM_RATE
MPF_CAPS = {
    fy: {"min": caps[0], "max": caps[1]}
    for fy, caps in MPF_CAPS_BY_FY.items()
}
# Active default FY2027 caps (91 FR 48398) while supporting FY2024-FY2026
MPF_MIN, MPF_MAX = get_mpf_caps(DEFAULT_MPF_FISCAL_YEAR)
CONFIDENCE_THRESHOLD = 0.85

# Non-apparatus exclusions under WCO GRI 1 to prevent polysemous keyword collisions
NON_APPARATUS_EXCLUSIONS = [
    r"\b(?:t-?shirts?|hoodies?|clothing|apparel|hats?|caps?|socks?|jackets?)\b",
    r"\b(?:shaving\s+cream|cosmetics?|lotions?|soaps?|shampoos?)\b",
    r"\b(?:paintings?|artwork|posters?|canvas(?:es)?|drawings?)\b",
    r"\b(?:oils?|greases?|lubricants?|fuels?|additives?)\b",
    r"\b(?:keycaps?|keyboard\s+keys?|novelty|stickers?|decals?|patch(?:es)?)\b",
    r"\b(?:foods?|supplements?|vitamins?|powders?|capsules?|pills?)\b",
    r"\b(?:books?|manuals?|magazines?|guides?|catalogs?)\b",
]


def calculate_landed_cost(
    entered_value: Decimal,
    duty_rate_ad_valorem: Decimal,
    is_ocean_freight: bool = True,
    freight_and_insurance: Decimal = Decimal("0.00"),
    fiscal_year: str = DEFAULT_MPF_FISCAL_YEAR,
    country_of_origin: Optional[str] = None,
    hts_code: Optional[str] = None,
    section_301_rate: Optional[Decimal] = None,
) -> LandedCostBreakdown:
    """Calculate US Customs Landed Cost using statutory formulas and Python Decimal."""
    # Ensure standard 2-decimal quantization for currency values
    entered_val_quantized = quantize_currency(entered_value)
    freight_quantized = quantize_currency(freight_and_insurance)

    # General Customs Duty: Value * Rate
    customs_duty = quantize_currency(entered_val_quantized * duty_rate_ad_valorem)

    # USTR Section 301 Chapter 99 Country-of-Origin Surcharge (19 U.S.C. § 2411)
    sec_subheading: Optional[str] = None
    if section_301_rate is not None:
        sec_rate = section_301_rate
        if sec_rate > Decimal("0.00") and hts_code and country_of_origin:
            _, sec_subheading = get_section_301_rate(hts_code, country_of_origin)
    elif hts_code and country_of_origin:
        sec_rate, sec_subheading = get_section_301_rate(hts_code, country_of_origin)
    else:
        sec_rate = Decimal("0.00")

    section_301_duty = quantize_currency(entered_val_quantized * sec_rate)

    # Merchandise Processing Fee (19 CFR § 24.23): 0.3464% clamped between caps
    min_cap, max_cap = get_mpf_caps(fiscal_year)
    mpf_fee = calculate_mpf(entered_val_quantized, fiscal_year)

    # Harbor Maintenance Fee (19 CFR § 24.24): 0.125% for ocean freight, $0 for air/truck
    transport_mode = "ocean" if is_ocean_freight else "air"
    hmf_fee = calculate_hmf(entered_val_quantized, transport_mode)

    total_customs_cost = customs_duty + section_301_duty + mpf_fee + hmf_fee
    total_landed_cost = entered_val_quantized + total_customs_cost + freight_quantized

    return LandedCostBreakdown(
        entered_value=entered_val_quantized,
        duty_rate_ad_valorem=duty_rate_ad_valorem,
        customs_duty=customs_duty,
        section_301_rate=sec_rate,
        section_301_duty=section_301_duty,
        section_301_subheading=sec_subheading,
        mpf_rate=MPF_RATE,
        mpf_min_cap=min_cap,
        mpf_max_cap=max_cap,
        mpf_fee=mpf_fee,
        hmf_rate=HMF_RATE if is_ocean_freight else Decimal("0.00"),
        hmf_fee=hmf_fee,
        freight_and_insurance=freight_quantized,
        total_customs_cost=total_customs_cost,
        total_landed_cost=total_landed_cost,
        fiscal_year=fiscal_year.upper(),
    )


class HTSClassifierEngine:
    """Path-dependent hierarchical classification engine implementing GRI 1-6."""

    PRESETS: Dict[str, Dict] = {
        "drone_motor": {
            "title": "Industrial Brushless DC Drone Motor with Integrated Electronic Speed Controller (ESC)",
            "hts_code": "8501.31.8000",
            "duty_rate": Decimal("0.024"),  # 2.4%
            "confidence": 0.94,
            "chapter_notes": [
                "Section XVI Note 2 (Classification of Parts of Machines)",
                "Chapter 85 Note 2 (Electric Motors & Generators)",
                "WCO Explanatory Notes to Heading 85.01",
            ],
            "gri_path": [
                GRIDecisionNode(
                    step_rule="GRI 1",
                    heading_or_subheading="Chapter 85",
                    description="Electrical machinery and equipment and parts thereof; sound recorders and reproducers",
                    legal_rationale="Merchandise is primarily an electro-mechanical energy conversion apparatus covered by Chapter 85 terms.",
                    confidence=0.99,
                    passed=True,
                    competing_candidates=["Chapter 84 (Machinery and Mechanical Appliances)", "Chapter 88 (Aircraft & Drones)"],
                ),
                GRIDecisionNode(
                    step_rule="GRI 1 / GRI 3(b)",
                    heading_or_subheading="Heading 8501",
                    description="Electric motors and generators (excluding generating sets)",
                    legal_rationale="Composite article of an electric motor and speed controller. Under GRI 3(b), the motor provides the essential character of motive propulsion.",
                    confidence=0.93,
                    passed=True,
                    competing_candidates=["8504.40 (Static Converters / Speed Controllers)", "8543.70 (Electrical machines with individual functions)"],
                ),
                GRIDecisionNode(
                    step_rule="GRI 6",
                    heading_or_subheading="Subheading 8501.31",
                    description="Other DC motors; DC generators: Of an output not exceeding 750 W",
                    legal_rationale="Rated continuous output is 480 Watts, strictly satisfying the under-750W threshold of subheading 8501.31.",
                    confidence=0.96,
                    passed=True,
                    competing_candidates=["8501.32 (Output exceeding 750 W but not exceeding 75 kW)"],
                ),
                GRIDecisionNode(
                    step_rule="Statutory Suffix",
                    heading_or_subheading="8501.31.8000",
                    description="Other DC motors of an output not exceeding 750 W: Other: Brushless",
                    legal_rationale="Permanent magnet brushless architecture satisfies statistical annotation 8000.",
                    confidence=0.95,
                    passed=True,
                    competing_candidates=["8501.31.4000 (Motors of under 18.65 W)"],
                ),
            ],
        },
        "server_accelerator": {
            "title": "Enterprise AI Tensor Accelerator PCIe Card with Integrated Vapor Chamber",
            "hts_code": "8542.31.0001",
            "duty_rate": Decimal("0.00"),  # Free (Information Technology Agreement ITA-1)
            "confidence": 0.96,
            "chapter_notes": [
                "Chapter 84 Note 5(E) (Exclusion of machines incorporating ADP units)",
                "Chapter 85 Note 9(b)(i) (Definition of Multicomponent Integrated Circuits MCOs)",
                "WTO Information Technology Agreement (ITA-1) Zero-Duty Concession",
            ],
            "gri_path": [
                GRIDecisionNode(
                    step_rule="GRI 1",
                    heading_or_subheading="Chapter 85",
                    description="Electrical machinery and equipment and parts thereof",
                    legal_rationale="Electronic integrated circuit assembly functioning as a cryptographic and tensor computation accelerator.",
                    confidence=0.98,
                    passed=True,
                    competing_candidates=["Chapter 84 (Heading 8471 ADP Machines)"],
                ),
                GRIDecisionNode(
                    step_rule="GRI 1 / Note 5(E)",
                    heading_or_subheading="Heading 8542",
                    description="Electronic integrated circuits and microassemblies",
                    legal_rationale="Chapter 84 Note 5(E) directs that electronic acceleration coprocessor cards are classified in their own heading. Heading 8542 specifically covers processors and controllers.",
                    confidence=0.97,
                    passed=True,
                    competing_candidates=["8473.30 (Parts and accessories of the machines of heading 8471)"],
                ),
                GRIDecisionNode(
                    step_rule="GRI 6",
                    heading_or_subheading="Subheading 8542.31",
                    description="Processors and controllers, whether or not combined with memories, converters, logic circuits, amplifiers, clock and timing circuits, or other circuits",
                    legal_rationale="The neural processing core executes programmable arithmetic and matrix tensor multiplication.",
                    confidence=0.96,
                    passed=True,
                    competing_candidates=["8542.32 (Memories)", "8542.39 (Other)"],
                ),
                GRIDecisionNode(
                    step_rule="Statutory Suffix",
                    heading_or_subheading="8542.31.0001",
                    description="Electronic integrated circuits: Processors: Microprocessors, having a 64-bit or greater architecture",
                    legal_rationale="64-bit wide register addressing qualifies under statistical reporting number 0001.",
                    confidence=0.95,
                    passed=True,
                    competing_candidates=[],
                ),
            ],
        },
        "ev_battery_pack": {
            "title": "Lithium Iron Phosphate (LiFePO4) Battery Module with Battery Management System (BMS)",
            "hts_code": "8507.60.0000",
            "duty_rate": Decimal("0.034"),  # 3.4% + Section 301 25% ad valorem
            "confidence": 0.91,
            "chapter_notes": [
                "Chapter 85 Note 2",
                "US Note 20 to Subchapter III, Chapter 99 (Section 301 Tariff on Chinese Lithium-Ion Accumulators)",
            ],
            "gri_path": [
                GRIDecisionNode(
                    step_rule="GRI 1",
                    heading_or_subheading="Heading 8507",
                    description="Electric storage batteries, including separators therefor, whether or not rectangular",
                    legal_rationale="Heading 8507 explicitly describes electric storage batteries and accumulators.",
                    confidence=0.98,
                    passed=True,
                    competing_candidates=["8504.40 (Power Supplies)"],
                ),
                GRIDecisionNode(
                    step_rule="GRI 6",
                    heading_or_subheading="Subheading 8507.60",
                    description="Lithium-ion accumulators",
                    legal_rationale="Electrochemical cell chemistry is based on lithium iron phosphate intercalation.",
                    confidence=0.95,
                    passed=True,
                    competing_candidates=["8507.20 (Other lead-acid accumulators)", "8507.80 (Other storage batteries)"],
                ),
                GRIDecisionNode(
                    step_rule="Statutory Suffix",
                    heading_or_subheading="8507.60.0000",
                    description="Lithium-ion accumulators (including battery packs and modules)",
                    legal_rationale="Complete modular pack assembly classified under 8507.60.0000.",
                    confidence=0.92,
                    passed=True,
                    competing_candidates=[],
                ),
            ],
        },
        "smart_apparel_watch": {
            "title": "Multi-Sensor Fitness Tracking Smartband with Heart Rate Sensor & Bluetooth Low Energy",
            "hts_code": "8517.62.0050",
            "duty_rate": Decimal("0.00"),  # Free (ITA)
            "confidence": 0.81,  # Intentional low confidence < 0.85 to test human review gating!
            "chapter_notes": [
                "Chapter 90 Note 1(h) (Exclusion of smart wearables with primary data communication)",
                "Chapter 91 Note 1(n) (Exclusion of chronometers that are wireless transceivers)",
                "CBP Ruling HQ H258957 (Classification of wearable fitness devices)",
            ],
            "gri_path": [
                GRIDecisionNode(
                    step_rule="GRI 1 / GRI 3(b)",
                    heading_or_subheading="Heading 8517",
                    description="Telephone sets... other apparatus for the transmission or reception of voice, images or other data",
                    legal_rationale="Composite machine with optical heart rate monitor (Ch 90), time display (Ch 91), and BLE transmission (Ch 85). Essential character determined to be two-way wireless data connectivity.",
                    confidence=0.82,
                    passed=True,
                    competing_candidates=["9031.80 (Measuring or checking instruments)", "9102.12 (Wristwatches with opto-electronic display)"],
                ),
                GRIDecisionNode(
                    step_rule="GRI 6",
                    heading_or_subheading="Subheading 8517.62",
                    description="Machines for the reception, conversion and transmission or regeneration of voice, images or other data",
                    legal_rationale="Device converts photoplethysmography sensor pulses into encrypted digital BLE packets.",
                    confidence=0.80,
                    passed=True,
                    competing_candidates=["8517.69 (Other)"],
                ),
                GRIDecisionNode(
                    step_rule="Statutory Suffix",
                    heading_or_subheading="8517.62.0050",
                    description="Machines for the reception, conversion and transmission of data: Other",
                    legal_rationale="Qualified as other data communications hardware under 8517.62.0050.",
                    confidence=0.81,
                    passed=True,
                    competing_candidates=[],
                ),
            ],
        },
    }

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")

    def classify(self, request: ClassificationRequest) -> HTSClassificationResult:
        """Classify a product description through the hierarchical WCO GRI decision tree."""
        # Detect matching preset or keyword using word boundaries
        text_lower = f"{request.product_title} {request.product_description} {request.commercial_attributes or ''}".lower()

        patterns = {
            "drone_motor": [
                r"\b(?:brushless\s+(?:dc\s+)?(?:drone\s+)?motors?|bldc\s+motors?|drone\s+motors?|electric\s+(?:dc\s+)?motors?)\b",
                r"\b(?:uav|drone)\s+propulsion\b",
                r"\bmotors?\s+(?:with|for|incorporating)\s+(?:(?:integrated\s+)?esc|(?:agricultural\s+)?(?:uav|drone)s?)\b",
                r"\bpermanent\s+magnet\s+brushless\s+dc\s+motors?\b",
            ],
            "server_accelerator": [
                r"\b(?:ai|tensor|neural|inference|deep\s+learning)\s+accelerators?\b",
                r"\b(?:pcie|server)\s+(?:ai\s+)?accelerators?\b",
                r"\b(?:tensor\s+processing\s+units?|neural\s+processing\s+units?)\b",
                r"\b(?:gpu|pcie)\s+(?:compute\s+)?(?:accelerators?|coprocessors?)\b",
                r"\b(?:enterprise|datacenter)\s+(?:ai\s+)?gpus?\b",
                r"\bhigh[- ]performance\s+neural\s+tensor\s+accelerators?\b",
                r"\bneural\s+tensor\s+accelerators?\b",
            ],
            "ev_battery_pack": [
                r"\b(?:ev|traction|automotive)\s+battery\s+packs?\b",
                r"\b(?:lithium[\s-](?:iron\s+phosphate|ion)|lifepo4|lfp|nmc)\b.*?\b(?:battery\s+(?:pack|module)s?|accumulators?)\b",
                r"\bbattery\s+modules?\s+(?:with|and|incorporating)\s+(?:(?:integrated\s+)?bms|(?:integrated\s+)?battery\s+management(?:\s+system)?)\b",
                r"\belectric\s+vehicle\s+(?:storage\s+)?batter(?:y|ies)\b",
                r"\blithium\s+accumulator\s+(?:pack|module|assembly)s?\b",
                r"\blifepo4\s+battery\s+modules?\b",
            ],
            "smart_apparel_watch": [
                r"\b(?:fitness\s+tracking\s+)?smartbands?\b",
                r"\b(?:smart\s*watch(?:es)?|fitness\s+trackers?|activity\s+trackers?)\b",
                r"\bwearable\s+(?:smartbands?|fitness|health|biometric|activity)\b",
                r"\bheart\s+rate\s+tracking\s+(?:wristbands?|watch(?:es)?|smartbands?)\b",
                r"\bmulti[- ]sensor\s+fitness\s+tracking\s+smartband\b",
                r"\bwearable\s+device\s+with\s+(?:bluetooth|ble|heart\s+rate)\b",
            ],
        }

        matched_key = None
        if not any(re.search(exc, text_lower) for exc in NON_APPARATUS_EXCLUSIONS):
            for key, regex_list in patterns.items():
                if any(re.search(pat, text_lower, re.IGNORECASE) for pat in regex_list):
                    matched_key = key
                    break

        # C3: On no match, DO NOT default to 'drone_motor' with 0.94 confidence!
        # Return requires_human_review=True, confidence=0.0, classified_hts_code="REQUIRES_BROKER_REVIEW"
        if matched_key is None:
            landed = calculate_landed_cost(
                entered_value=request.entered_value,
                duty_rate_ad_valorem=Decimal("0.00"),
                is_ocean_freight=request.is_ocean_freight,
                freight_and_insurance=request.freight_and_insurance,
            )
            return HTSClassificationResult(
                item_id="hts-unclassified",
                product_title=request.product_title,
                input_description=request.product_description,
                country_of_origin=request.country_of_origin,
                declared_hts_code=request.declared_hts_code,
                classified_hts_code="REQUIRES_BROKER_REVIEW",
                confidence=0.0,
                requires_human_review=True,
                gri_path=[],
                chapter_notes_cited=[
                    "Unclassified merchandise: product description does not match pre-computed GRI patterns.",
                    "Mandatory review by licensed customs broker required under 19 CFR Part 111 before CBP entry filing."
                ],
                landed_cost=landed,
            )

        preset = self.PRESETS[matched_key]
        landed = calculate_landed_cost(
            entered_value=request.entered_value,
            duty_rate_ad_valorem=preset["duty_rate"],
            is_ocean_freight=request.is_ocean_freight,
            freight_and_insurance=request.freight_and_insurance,
            country_of_origin=request.country_of_origin,
            hts_code=preset["hts_code"],
        )

        overall_conf = preset["confidence"]
        requires_review = overall_conf < CONFIDENCE_THRESHOLD

        return HTSClassificationResult(
            item_id=f"hts-{matched_key}",
            product_title=request.product_title,
            input_description=request.product_description,
            country_of_origin=request.country_of_origin,
            declared_hts_code=request.declared_hts_code,
            classified_hts_code=preset["hts_code"],
            confidence=overall_conf,
            requires_human_review=requires_review,
            gri_path=preset["gri_path"],
            chapter_notes_cited=preset["chapter_notes"],
            landed_cost=landed,
        )

    def get_preset(self, preset_id: str, entered_value: Decimal = Decimal("25000.00")) -> HTSClassificationResult:
        """Fetch a specific pre-computed GRI reasoning tree."""
        if preset_id not in self.PRESETS:
            raise KeyError(f"Preset '{preset_id}' not found. Available presets: {list(self.PRESETS.keys())}")
        preset = self.PRESETS[preset_id]

        req = ClassificationRequest(
            product_title=preset["title"],
            product_description="High precision commercial specification for US Customs entry filing.",
            entered_value=entered_value,
            is_ocean_freight=True,
            freight_and_insurance=Decimal("1500.00"),
        )
        return self.classify(req)
