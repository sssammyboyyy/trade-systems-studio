"""
Deterministic customs compliance audit of a commercial invoice payload.

Contract: the engine only computes a dollar figure from inputs that are present. A
missing input (``None`` or absent key) produces either no finding or an informational
finding with a zero amount; it is never replaced by a guessed rate or value.
"""

from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from app.core.penalties import (
    Culpability,
    calculate_1592_penalties,
    max_1592_penalty,
    normalize_culpability,
    prior_disclosure_penalty,
)
from app.core.statutory_rates import calculate_1505_interest, calculate_1505_interest_by_months
from app.models.schemas import BoundingBox, Discrepancy, KillShotMetrics
from app.services.utils import optional_decimal, parse_iso_date, quantize_currency, safe_decimal

__all__ = ["audit_customs_invoice", "calculate_1592_penalties", "effective_duty_rate"]

_CULPABILITY_LABEL = {
    "negligence": "Negligence, 19 U.S.C. 1592(c)(3)",
    "gross_negligence": "Gross negligence, 19 U.S.C. 1592(c)(2)",
    "fraud": "Fraud, 19 U.S.C. 1592(c)(1)",
}


def _line_value(item: Dict[str, Any]) -> Decimal:
    stated = optional_decimal(item.get("stated_total") or item.get("total_price"))
    if stated is not None:
        return stated
    return safe_decimal(item.get("quantity"), "0") * safe_decimal(item.get("unit_price"), "0")


def effective_duty_rate(items: List[Dict[str, Any]], rate_key: str = "duty_rate") -> Optional[Decimal]:
    """Value-weighted duty rate across lines, or None if any line's rate is unknown."""
    total_value = Decimal("0")
    total_duty = Decimal("0")
    for it in items:
        if not isinstance(it, dict):
            continue
        rate = optional_decimal(it.get(rate_key))
        if rate is None:
            return None
        value = _line_value(it)
        total_value += value
        total_duty += value * rate
    if total_value <= 0:
        return None
    return total_duty / total_value


def _resolve_culpability(data: Dict[str, Any]) -> Culpability:
    if data.get("fraud") or str(data.get("violation_level", "")).lower() == "fraud":
        return "fraud"
    return normalize_culpability(data.get("culpability"))


def _interest(loss: Decimal, data: Dict[str, Any]) -> Tuple[Decimal, str]:
    """Interest on a loss of duty, from real dates when available, else a labelled estimate."""
    entry = parse_iso_date(data.get("entry_date") or data.get("invoice_date"))
    as_of = parse_iso_date(data.get("as_of_date")) or date.today()
    if entry is not None and as_of > entry:
        return calculate_1505_interest(loss, entry, as_of), f"19 U.S.C. 1505, {entry.isoformat()} to {as_of.isoformat()}"
    return calculate_1505_interest_by_months(loss, months_elapsed=9), "estimate: 9 months at 7.0% (no entry date)"


def audit_customs_invoice(data: Dict[str, Any]) -> Tuple[KillShotMetrics, List[Discrepancy]]:
    """
    Customs invoice checks:
    1. CIF valuation: international freight and insurance are excluded from transaction value
       (19 U.S.C. 1401a(b)(4)(A)); including them overstates entered value.
    2. Line-item arithmetic.
    3. Classification: duty loss and 19 U.S.C. 1592 statutory maximums by culpability.
    4. Undeclared assists (19 U.S.C. 1401a(h)).
    5. Denied-party screening of named parties.
    """
    if not data or not any(
        k in data for k in ("items", "misclassified_value", "dutiable_value", "invoice_number", "unreported_assists")
    ):
        return KillShotMetrics(), []

    discrepancies: List[Discrepancy] = []
    items: List[Dict[str, Any]] = [it for it in (data.get("items") or []) if isinstance(it, dict)]
    eff_declared_rate = effective_duty_rate(items, "duty_rate")
    culpability = _resolve_culpability(data)
    penalty_total = Decimal("0.00")

    # 1. CIF valuation (overstatement of entered value, i.e. potential duty overpayment)
    incoterms = str(data.get("incoterms") or "").upper()
    freight_charge = optional_decimal(data.get("freight_charge"))
    insurance_charge = optional_decimal(data.get("insurance_charge"))
    if incoterms.startswith("CIF") or " CIF" in f" {incoterms}":
        non_dutiable = (freight_charge or Decimal("0")) + (insurance_charge or Decimal("0"))
        if non_dutiable > 0:
            excess_duty = quantize_currency(non_dutiable * eff_declared_rate) if eff_declared_rate is not None else None
            duty_text = (
                f"estimated excess duty of ${excess_duty:,.2f} at the invoice's value-weighted rate"
                if excess_duty is not None
                else "excess duty not computed because at least one line's duty rate is unknown"
            )
            discrepancies.append(
                Discrepancy(
                    id="disc-c1-01",
                    concept_id="concept_1_customs",
                    title="CIF Freight and Insurance Must Be Deducted From Transaction Value",
                    description=(
                        f"The invoice is CIF and itemises ${non_dutiable:,.2f} of international freight/insurance. "
                        f"These are excluded from transaction value under 19 U.S.C. 1401a(b)(4)(A). If the entry was "
                        f"filed at the CIF total, entered value is overstated by ${non_dutiable:,.2f}: {duty_text}."
                    ),
                    statutory_code="19 U.S.C. 1401a(b)(4)(A) / 19 CFR 152.103(a)(5)",
                    severity="warning",
                    exposure_amount=excess_duty or Decimal("0.00"),
                    confidence=0.82,
                    executive_summary=f"${non_dutiable:,.2f} of non-dutiable CIF charges may be inflating entered value.",
                    financial_blast_radius=(
                        f"Recoverable overpayment of ${excess_duty:,.2f} via Post-Summary Correction or protest."
                        if excess_duty is not None
                        else "Overpayment depends on line-level duty rates (not all known)."
                    ),
                    statutory_defense="Deduct itemised freight/insurance on the entry summary; file a PSC (or a 19 U.S.C. 1514 protest after liquidation).",
                    bounding_box=BoundingBox(x=58.0, y=125.0, width=880.0, height=55.0, page_number=1, confidence=0.82),
                    metadata={
                        "rule": "19_USC_1401a_b_4_A",
                        "incoterm": incoterms,
                        "freight_charge": None if freight_charge is None else str(freight_charge),
                        "declared_insurance": None if insurance_charge is None else str(insurance_charge),
                        "non_dutiable_charges": str(non_dutiable),
                        "effective_duty_rate": None if eff_declared_rate is None else str(eff_declared_rate.quantize(Decimal("0.0001"))),
                        "estimated_excess_duty": None if excess_duty is None else str(excess_duty),
                        "valuation_effect": "overstatement_duty_overpayment",
                    },
                )
            )
        elif insurance_charge is not None and insurance_charge == 0:
            discrepancies.append(
                Discrepancy(
                    id="disc-c1-01-insurance",
                    concept_id="concept_1_customs",
                    title="CIF Invoice Shows $0.00 Insurance",
                    description=(
                        "The invoice is CIF but states no insurance amount. If insurance is bundled into the unit "
                        "prices it is still non-dutiable and must be itemised to be deducted. No amount is estimated."
                    ),
                    statutory_code="19 U.S.C. 1401a(b)(4)(A)",
                    severity="info",
                    exposure_amount=Decimal("0.00"),
                    confidence=0.6,
                    bounding_box=BoundingBox(x=58.0, y=125.0, width=880.0, height=55.0, page_number=1, confidence=0.6),
                    metadata={"rule": "19_USC_1401a_b_4_A", "incoterm": incoterms, "declared_insurance": "0.00"},
                )
            )

    # 2. Line-item arithmetic
    for item in items:
        qty = safe_decimal(item.get("quantity"), "0")
        unit_price = safe_decimal(item.get("unit_price"), "0.00")
        stated_total = safe_decimal(item.get("stated_total") or item.get("total_price"), "0.00")
        calculated_total = quantize_currency(qty * unit_price)
        diff = stated_total - calculated_total
        if diff != Decimal("0.00"):
            line_no = item.get("line_number", 1)
            direction = "overstates" if diff > 0 else "understates"
            discrepancies.append(
                Discrepancy(
                    id=f"disc-c1-02-line-{line_no}",
                    concept_id="concept_1_customs",
                    title="Invoice Line Item Arithmetic Extension Error",
                    description=(
                        f"Line {line_no}: {qty} units @ ${unit_price} = ${calculated_total}, but the line is invoiced at "
                        f"${stated_total}. The ${abs(diff):,.2f} difference {direction} the value on this line."
                    ),
                    statutory_code="19 CFR 141.86 / 19 CFR 152.103(a)",
                    severity="critical",
                    exposure_amount=abs(diff),
                    confidence=0.99,
                    executive_summary=f"Line {line_no} extension is off by ${abs(diff):,.2f}.",
                    financial_blast_radius=f"Entered value on line {line_no} {direction} by ${abs(diff):,.2f}.",
                    statutory_defense="Obtain a corrected invoice or debit/credit memo before filing; PSC within 300 days of entry if already filed.",
                    bounding_box=BoundingBox(x=58.0, y=360.0, width=880.0, height=50.0, page_number=1, confidence=0.99),
                    metadata={
                        "line_number": line_no,
                        "stated_total": str(stated_total),
                        "calculated_total": str(calculated_total),
                        "variance": str(diff),
                    },
                )
            )

    # 3. Classification and 19 U.S.C. 1592
    dutiable_value = optional_decimal(data.get("misclassified_value"))
    declared_rate = optional_decimal(data.get("declared_duty_rate"))
    lawful_rate = optional_decimal(data.get("lawful_duty_rate"))
    domestic_value = optional_decimal(data.get("domestic_value"))
    declared_hts = str(data.get("declared_hts") or data.get("declared_hts_code") or "")
    lawful_hts = str(data.get("lawful_hts") or data.get("lawful_hts_code") or "")
    product_desc = str(data.get("product_description") or data.get("product_title") or "")
    if not (declared_hts and product_desc):
        for it in items:
            if not declared_hts and (it.get("declared_hts") or it.get("hts_code")):
                declared_hts = str(it.get("declared_hts") or it.get("hts_code"))
            if not lawful_hts and it.get("lawful_hts"):
                lawful_hts = str(it.get("lawful_hts"))
            if not product_desc and it.get("description"):
                product_desc = str(it.get("description"))
    declared_hts = declared_hts or "[declared HTS not stated]"
    lawful_hts = lawful_hts or "[lawful HTS not stated]"
    product_desc = product_desc or "the merchandise"

    hts_inputs_known = dutiable_value is not None and declared_rate is not None and lawful_rate is not None
    lawful_duty_loss = (
        quantize_currency(dutiable_value * (lawful_rate - declared_rate))  # type: ignore[operator]
        if hts_inputs_known
        else Decimal("0.00")
    )

    if hts_inputs_known and (lawful_duty_loss > 0 or culpability == "fraud"):
        penalties = calculate_1592_penalties(lawful_duty_loss, domestic_value=domestic_value, dutiable_value=dutiable_value)
        exposure = penalties[culpability]
        estimated_interest, interest_basis = _interest(lawful_duty_loss, data)
        pd_penalty = prior_disclosure_penalty(culpability, lawful_duty_loss, estimated_interest, dutiable_value)
        protected = (
            max(Decimal("0.00"), exposure - pd_penalty) if exposure is not None and pd_penalty is not None else None
        )
        exposure_amount = exposure if exposure is not None else Decimal("0.00")
        penalty_total += exposure_amount

        cap_note = "" if domestic_value is not None else " Domestic value not stated, so the domestic-value cap is not applied."
        if exposure is None:
            max_text = "cannot be computed (the fraud maximum is the domestic value, which is not stated)"
        else:
            max_text = f"${exposure:,.2f}"
        pd_text = (
            f"interest on the loss of duty (about ${estimated_interest:,.2f}; {interest_basis})"
            if culpability != "fraud"
            else (f"${pd_penalty:,.2f} (100% of the loss of duty)" if pd_penalty is not None else "not computable")
        )
        discrepancies.append(
            Discrepancy(
                id="disc-c1-03",
                concept_id="concept_1_customs",
                title="HTS Misclassification & 19 U.S.C. § 1592 Penalty Exposure",
                description=(
                    f"{product_desc} declared under HTS {declared_hts} (rate {declared_rate * 100:.1f}%) "  # type: ignore[operator]
                    f"appears classifiable under {lawful_hts} (rate {lawful_rate * 100:.1f}%). "  # type: ignore[operator]
                    f"Loss of duty: ${lawful_duty_loss:,.2f}. Statutory maximum at the assumed culpability "
                    f"({_CULPABILITY_LABEL[culpability]}): {max_text}.{cap_note}"
                ),
                statutory_code="19 U.S.C. 1592(c)",
                severity="critical",
                exposure_amount=exposure_amount,
                confidence=0.96,
                executive_summary=(
                    f"Declared {declared_hts} vs {lawful_hts}: ${lawful_duty_loss:,.2f} loss of duty; "
                    f"statutory maximum {max_text} ({culpability.replace('_', ' ')})."
                ),
                financial_blast_radius=f"${lawful_duty_loss:,.2f} unpaid duty plus up to {max_text} civil penalty.",
                statutory_defense=(
                    f"Consider a prior disclosure under 19 CFR 162.74 before CBP opens an inquiry: tender the "
                    f"${lawful_duty_loss:,.2f} loss of duty; the penalty is then limited to {pd_text}. "
                    f"Culpability is a legal determination for counsel."
                ),
                bounding_box=BoundingBox(x=58.0, y=415.0, width=880.0, height=50.0, page_number=1, confidence=0.96),
                metadata={
                    "declared_hts": declared_hts,
                    "lawful_hts": lawful_hts,
                    "product_description": product_desc,
                    "dutiable_base": str(dutiable_value),
                    "duty_loss": str(lawful_duty_loss),
                    "culpability_assumed": culpability,
                    "statutory_max_by_culpability": {k: (None if v is None else str(v)) for k, v in penalties.items()},
                    "domestic_value": None if domestic_value is None else str(domestic_value),
                    "domestic_value_cap_applied": domestic_value is not None,
                    "statutory_interest": str(estimated_interest),
                    "interest_basis": interest_basis,
                    "prior_disclosure_max_penalty": None if pd_penalty is None else str(pd_penalty),
                    "capital_protected": None if protected is None else str(protected),
                    "penalty_basis": "19_USC_1592",
                    "rate_sources": data.get("rate_sources"),
                },
            )
        )

    # 4. Undeclared assists (19 U.S.C. 1401a(h)(1)(A))
    unreported_assists = optional_decimal(data.get("unreported_assists"))
    if unreported_assists is not None and unreported_assists > 0:
        assist_rate = optional_decimal(data.get("assist_duty_rate"))
        if assist_rate is None:
            assist_rate = lawful_rate if lawful_rate is not None else eff_declared_rate
        assist_loss = quantize_currency(unreported_assists * assist_rate) if assist_rate is not None else None
        assist_max = (
            max_1592_penalty(culpability, assist_loss, unreported_assists, domestic_value) if assist_loss is not None else None
        )
        if assist_max is not None:
            penalty_total += assist_max
        discrepancies.append(
            Discrepancy(
                id="disc-c1-04-assists",
                concept_id="concept_1_customs",
                title="Undeclared Assist Omitted From Transaction Value",
                description=(
                    f"Buyer-supplied assists of ${unreported_assists:,.2f} are not included in declared value "
                    f"(19 U.S.C. 1401a(b)(1)(C), (h)(1)(A)). "
                    + (
                        f"Loss of duty ${assist_loss:,.2f}; statutory maximum ${assist_max:,.2f} ({culpability.replace('_', ' ')})."
                        if assist_loss is not None and assist_max is not None
                        else "Duty rate unknown, so no loss of duty is computed."
                    )
                ),
                statutory_code="19 U.S.C. 1401a(h)(1)(A) / 19 CFR 152.103(d)",
                severity="critical" if assist_loss is not None else "warning",
                exposure_amount=assist_max or Decimal("0.00"),
                confidence=0.97,
                executive_summary=f"${unreported_assists:,.2f} in assists missing from entered value.",
                financial_blast_radius=(
                    f"${assist_loss:,.2f} unpaid duty plus up to ${assist_max:,.2f} penalty."
                    if assist_loss is not None and assist_max is not None
                    else "Exposure depends on the applicable duty rate."
                ),
                statutory_defense="Tender the additional duty and consider a prior disclosure for the assist undervaluation.",
                bounding_box=BoundingBox(x=58.0, y=475.0, width=880.0, height=45.0, page_number=1, confidence=0.97),
                metadata={
                    "rule": "19_USC_1401a_h",
                    "assist_value": str(unreported_assists),
                    "duty_rate": None if assist_rate is None else str(assist_rate),
                    "unpaid_duty": None if assist_loss is None else str(assist_loss),
                    "penalty_basis": "19_USC_1592",
                },
            )
        )

    # 5. Denied-party screening
    shipper = data.get("shipper")
    buyer = data.get("buyer")
    consignee = data.get("consignee")
    if shipper or buyer or consignee:
        from app.services.sanctions_screener import sanctions_screener

        report = sanctions_screener.screen_parties(shipper=shipper, buyer=buyer, consignee=consignee)
        if report.has_violations:
            invoice_total = sum((_line_value(it) for it in items), Decimal("0.00"))
            for role, match in [("Shipper", report.shipper), ("Buyer", report.buyer), ("Consignee", report.consignee)]:
                if match and match.matched:
                    if dutiable_value is not None and dutiable_value > 0:
                        sanctions_exposure = dutiable_value
                    elif invoice_total > 0:
                        sanctions_exposure = invoice_total
                    else:
                        sanctions_exposure = safe_decimal(data.get("transaction_value"), "0.00")
                    discrepancies.append(
                        Discrepancy(
                            id=f"disc-c1-sanctions-{role.lower()}",
                            concept_id="concept_1_customs",
                            title=f"High-Risk Sanctioned / Denied Party Match ({role})",
                            description=(
                                f"{role} '{match.query_name}' matches restricted entity '{match.matched_name}' "
                                f"({match.entity_id}) at {match.match_score}% similarity. Programs: {', '.join(match.programs)}. "
                                f"The amount shown is the transaction value at risk, not a penalty."
                            ),
                            statutory_code="15 CFR Part 744 (EAR) / 31 CFR Chapter V (OFAC)",
                            severity="critical",
                            exposure_amount=sanctions_exposure,
                            confidence=round(match.match_score / 100.0, 2),
                            bounding_box=BoundingBox(
                                x=58.0, y=70.0, width=400.0, height=50.0, page_number=1,
                                confidence=round(match.match_score / 100.0, 2),
                            ),
                            metadata={
                                "role": role,
                                "matched_entity_id": match.entity_id,
                                "match_score": match.match_score,
                                "programs": match.programs,
                                "country": match.country,
                                "screening_engine": match.screening_engine,
                                "amount_meaning": "transaction_value_at_risk",
                            },
                        )
                    )

    metrics = KillShotMetrics(
        penalty_exposure_avoided=quantize_currency(penalty_total),
        carrier_overbilling_caught=Decimal("0.00"),
        drawback_unclaimed_unlocked=Decimal("0.00"),
    )
    return metrics, discrepancies
