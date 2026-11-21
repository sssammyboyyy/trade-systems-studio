"""
19 U.S.C. 1592 civil penalty maximums and prior-disclosure limits.

Statute (19 U.S.C. 1592(c)):
- (1) Fraud: not to exceed the domestic value of the merchandise.
- (2) Gross negligence: not to exceed the lesser of the domestic value, or
      4x the lawful duties, taxes and fees of which the U.S. is or may be deprived;
      if there is no loss of duty, 40% of the dutiable value.
- (3) Negligence: not to exceed the lesser of the domestic value, or 2x the loss of
      duty; if there is no loss of duty, 20% of the dutiable value.
- (4) Prior disclosure: fraud, not to exceed 100% of the loss of duty (10% of dutiable
      value if there is no loss); negligence or gross negligence, interest on the loss of
      duty (computed from liquidation), or no penalty if there is no loss. Tender of the
      actual loss of duty is required in every case.

These are statutory *maximums*. CBP's mitigation guidelines (19 CFR Part 171 App. B)
produce lower assessed amounts case by case; this module never invents a "floor".
"""

from decimal import Decimal
from typing import Dict, Literal, Optional

from app.services.utils import quantize_currency

Culpability = Literal["negligence", "gross_negligence", "fraud"]
CULPABILITY_LEVELS: tuple[Culpability, ...] = ("negligence", "gross_negligence", "fraud")
DEFAULT_CULPABILITY: Culpability = "negligence"

_TIERS: Dict[str, tuple[Decimal, Decimal]] = {
    # culpability: (multiple of loss of duty, share of dutiable value when no loss)
    "negligence": (Decimal("2"), Decimal("0.20")),
    "gross_negligence": (Decimal("4"), Decimal("0.40")),
}


def normalize_culpability(value: object) -> Culpability:
    v = str(value or "").strip().lower().replace(" ", "_").replace("-", "_")
    if v in CULPABILITY_LEVELS:
        return v  # type: ignore[return-value]
    return DEFAULT_CULPABILITY


def max_1592_penalty(
    culpability: Culpability,
    loss_of_duty: Decimal,
    dutiable_value: Optional[Decimal] = None,
    domestic_value: Optional[Decimal] = None,
) -> Optional[Decimal]:
    """
    Statutory maximum for one culpability level. Returns None when the maximum cannot be
    computed from the inputs (fraud without a domestic value, or a non-revenue violation
    without a dutiable value).
    """
    loss = quantize_currency(max(loss_of_duty, Decimal("0")))
    dom = quantize_currency(domestic_value) if domestic_value is not None else None

    if culpability == "fraud":
        return dom

    mult, pct = _TIERS[culpability]
    if loss > 0:
        statutory = quantize_currency(loss * mult)
    elif dutiable_value is not None:
        statutory = quantize_currency(dutiable_value * pct)
    else:
        return None
    return min(dom, statutory) if dom is not None else statutory


def calculate_1592_penalties(
    lawful_duty_loss: Decimal,
    domestic_value: Optional[Decimal] = None,
    dutiable_value: Optional[Decimal] = None,
) -> Dict[str, Optional[Decimal]]:
    """Statutory maximum for every culpability level (None where it cannot be computed)."""
    return {
        level: max_1592_penalty(level, lawful_duty_loss, dutiable_value, domestic_value)
        for level in CULPABILITY_LEVELS
    }


def prior_disclosure_penalty(
    culpability: Culpability,
    loss_of_duty: Decimal,
    interest_on_loss: Decimal,
    dutiable_value: Optional[Decimal] = None,
) -> Optional[Decimal]:
    """
    Maximum penalty after a valid prior disclosure under 1592(c)(4). The actual loss of
    duty must be tendered in addition. Returns None when it cannot be computed.
    """
    loss = quantize_currency(max(loss_of_duty, Decimal("0")))
    if culpability == "fraud":
        if loss > 0:
            return loss
        return quantize_currency(dutiable_value * Decimal("0.10")) if dutiable_value is not None else None
    if loss == 0:
        return Decimal("0.00")
    return quantize_currency(interest_on_loss)
