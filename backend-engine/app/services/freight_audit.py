"""
Deterministic pre-payment audit of an ocean carrier freight invoice.

Checks:
1. Fuel surcharge billed above the contracted index rate.
2. Accessorial (chassis split) billed without a referenced work order.
3. Detention billed while the container was still inside free time (46 CFR 545.5 guidance).
4. Demurrage/detention billing requirements under 46 CFR Part 541 (OSRA 2022 rule,
   in effect since May 2024):
   - 541.7: the invoice must be issued within 30 days of the date the charge was last
     incurred, otherwise the billed party is not required to pay it.
   - 541.5/541.6: an invoice missing the required minimum information eliminates the
     billed party's obligation to pay.
   - 541.8: the billed party has at least 30 days from issuance to request mitigation,
     refund or waiver.
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Literal, Optional, Tuple

from app.models.schemas import BoundingBox, Discrepancy, KillShotMetrics
from app.services.utils import optional_decimal, parse_iso_date, quantize_currency

FreeTimeBasis = Literal["calendar", "business"]
DND_INVOICE_DEADLINE_DAYS = 30


def count_days_held(start: date, end: date, basis: FreeTimeBasis = "calendar") -> int:
    """Days held counting the start day as day 1 (inclusive of both ends)."""
    if end < start:
        return 0
    if basis == "calendar":
        return (end - start).days + 1
    days = 0
    d = start
    while d <= end:
        if d.weekday() < 5:
            days += 1
        d += timedelta(days=1)
    return days


def audit_freight_bill(data: Dict[str, Any]) -> Tuple[KillShotMetrics, List[Discrepancy]]:
    if not data or not any(
        k in data
        for k in ("base_freight", "billed_fsc_rate", "chassis_split_fee", "detention_billed", "freight_charges", "invoice_number")
    ):
        return KillShotMetrics(), []

    discrepancies: List[Discrepancy] = []
    total_overbilling = Decimal("0.00")

    # 1. Fuel surcharge markup (needs base freight and both rates)
    base_freight = optional_decimal(data.get("base_freight"))
    billed_fsc_rate = optional_decimal(data.get("billed_fsc_rate"))
    authorized_fsc_rate = optional_decimal(data.get("authorized_fsc_rate"))
    if base_freight is not None and billed_fsc_rate is not None and authorized_fsc_rate is not None:
        billed_fsc_amount = quantize_currency(base_freight * billed_fsc_rate)
        lawful_fsc_amount = quantize_currency(base_freight * authorized_fsc_rate)
        fsc_overcharge = billed_fsc_amount - lawful_fsc_amount
        if fsc_overcharge > 0:
            total_overbilling += fsc_overcharge
            discrepancies.append(
                Discrepancy(
                    id="disc-c2-01",
                    concept_id="concept_2_freight",
                    title="Fuel Surcharge Billed Above Contracted Index Rate",
                    description=(
                        f"Fuel surcharge billed at {billed_fsc_rate * 100:.2f}% of base freight (${billed_fsc_amount:,.2f}) "
                        f"against a contracted index rate of {authorized_fsc_rate * 100:.2f}% (${lawful_fsc_amount:,.2f}). "
                        f"Overcharge: ${fsc_overcharge:,.2f}."
                    ),
                    statutory_code="Service contract fuel clause",
                    severity="critical",
                    exposure_amount=fsc_overcharge,
                    confidence=0.98,
                    executive_summary=f"FSC billed at {billed_fsc_rate * 100:.1f}% vs {authorized_fsc_rate * 100:.1f}% contracted: ${fsc_overcharge:,.2f} over.",
                    financial_blast_radius=f"${fsc_overcharge:,.2f} on this invoice.",
                    statutory_defense="Short-pay the variance and dispute it with the carrier, citing the service contract fuel clause.",
                    bounding_box=BoundingBox(x=58.0, y=385.0, width=880.0, height=45.0, page_number=1, confidence=0.98),
                    metadata={
                        "billed_rate": f"{billed_fsc_rate * 100:.1f}%",
                        "contract_rate": f"{authorized_fsc_rate * 100:.1f}%",
                        "billed_fsc": str(billed_fsc_amount),
                        "lawful_fsc": str(lawful_fsc_amount),
                        "variance": str(fsc_overcharge),
                    },
                )
            )

    # 2. Accessorial billed without a work order
    chassis_split = optional_decimal(data.get("chassis_split_fee"))
    has_signed_work_order = bool(data.get("has_chassis_work_order", False))
    if chassis_split is not None and chassis_split > 0 and not has_signed_work_order:
        total_overbilling += chassis_split
        discrepancies.append(
            Discrepancy(
                id="disc-c2-02",
                concept_id="concept_2_freight",
                title="Chassis Split Billed Without a Work Order",
                description=(
                    f"The carrier billed ${chassis_split:,.2f} for a chassis split, and no shipper work order or "
                    f"accessorial authorisation is referenced on the invoice. Accessorials are payable only "
                    f"where the service contract or published tariff provides for them."
                ),
                statutory_code="Service contract / tariff accessorial rule",
                severity="warning",
                exposure_amount=chassis_split,
                confidence=0.9,
                executive_summary=f"${chassis_split:,.2f} accessorial with no authorisation referenced.",
                financial_blast_radius=f"${chassis_split:,.2f} accessorial charge.",
                statutory_defense="Request the work order or tariff rule; dispute the line if none is produced.",
                bounding_box=BoundingBox(x=58.0, y=435.0, width=880.0, height=45.0, page_number=1, confidence=0.9),
                metadata={"charge_code": "CHS", "billed_amount": str(chassis_split), "authorization_present": False},
            )
        )

    # 3. Detention inside free time
    basis: FreeTimeBasis = "business" if str(data.get("free_time_basis", "calendar")).lower() == "business" else "calendar"
    detention_billed = optional_decimal(data.get("detention_billed")) or Decimal("0.00")
    discharge = parse_iso_date(data.get("discharge_date"))
    outgate = parse_iso_date(data.get("outgate_date"))
    free_days_val = data.get("port_free_days_allowed")
    actual_days_val = data.get("actual_days_held")
    if discharge and outgate:
        actual_days_val = count_days_held(discharge, outgate, basis)
    detention_disallowed = False

    if free_days_val is not None and actual_days_val is not None and detention_billed > 0:
        free_days = int(free_days_val)
        actual_days = int(actual_days_val)
        if actual_days <= free_days:
            detention_disallowed = True
            total_overbilling += detention_billed
            discrepancies.append(
                Discrepancy(
                    id="disc-c2-03",
                    concept_id="concept_2_freight",
                    title="Detention Billed Inside Port Free Time",
                    description=(
                        f"Detention of ${detention_billed:,.2f} was billed, but the container was returned on day "
                        f"{actual_days} of {free_days} {basis} days of free time."
                        + (f" Discharge {discharge.isoformat()}, out-gate {outgate.isoformat()}." if discharge and outgate else "")
                    ),
                    statutory_code="46 CFR 545.5 / 46 CFR Part 541",
                    severity="critical",
                    exposure_amount=detention_billed,
                    confidence=0.97,
                    executive_summary=f"Detention charged on day {actual_days} of {free_days} free days.",
                    financial_blast_radius=f"${detention_billed:,.2f} not owed.",
                    statutory_defense=(
                        "Dispute within the period stated on the invoice (at least 30 days from issuance, "
                        "46 CFR 541.8); the billing party must respond within 30 days of the dispute."
                    ),
                    bounding_box=BoundingBox(x=58.0, y=485.0, width=880.0, height=45.0, page_number=1, confidence=0.97),
                    metadata={
                        "free_days_allowed": free_days,
                        "days_held": actual_days,
                        "free_time_basis": basis,
                        "illegal_detention": str(detention_billed),
                    },
                )
            )

    # 4a. 46 CFR 541.7 invoice timeliness
    invoice_date = parse_iso_date(data.get("invoice_date"))
    last_incurred = parse_iso_date(data.get("charges_last_incurred")) or outgate
    if detention_billed > 0 and invoice_date and last_incurred:
        lag = (invoice_date - last_incurred).days
        if lag > DND_INVOICE_DEADLINE_DAYS and not detention_disallowed:
            detention_disallowed = True
            total_overbilling += detention_billed
            discrepancies.append(
                Discrepancy(
                    id="disc-c2-04-late-invoice",
                    concept_id="concept_2_freight",
                    title="Detention Invoice Issued More Than 30 Days After Charges Stopped",
                    description=(
                        f"Charges were last incurred on {last_incurred.isoformat()} and the invoice is dated "
                        f"{invoice_date.isoformat()} ({lag} days later). Under 46 CFR 541.7 the billed party is not "
                        f"required to pay a demurrage or detention charge invoiced more than 30 days after it was last incurred."
                    ),
                    statutory_code="46 CFR 541.7",
                    severity="critical",
                    exposure_amount=detention_billed,
                    confidence=0.95,
                    executive_summary=f"Detention invoiced {lag} days after last accrual (limit 30).",
                    financial_blast_radius=f"${detention_billed:,.2f} not payable.",
                    statutory_defense="Decline payment citing 46 CFR 541.7.",
                    bounding_box=BoundingBox(x=58.0, y=485.0, width=880.0, height=45.0, page_number=1, confidence=0.95),
                    metadata={"invoice_date": invoice_date.isoformat(), "charges_last_incurred": last_incurred.isoformat(), "lag_days": lag},
                )
            )

    # 4b. 46 CFR 541.5 / 541.6 required minimum information
    missing_info: Optional[List[str]] = data.get("dnd_missing_fields")
    if detention_billed > 0 and missing_info:
        amount = Decimal("0.00") if detention_disallowed else detention_billed
        if not detention_disallowed:
            total_overbilling += detention_billed
        discrepancies.append(
            Discrepancy(
                id="disc-c2-05-missing-info",
                concept_id="concept_2_freight",
                title="Detention Invoice Missing Required Information",
                description=(
                    "The invoice does not show: " + ", ".join(missing_info) + ". Under 46 CFR 541.5 an invoice that "
                    "omits required minimum information eliminates the billed party's obligation to pay the charge."
                ),
                statutory_code="46 CFR 541.5 / 541.6",
                severity="warning",
                exposure_amount=amount,
                confidence=0.85,
                bounding_box=BoundingBox(x=58.0, y=485.0, width=880.0, height=45.0, page_number=1, confidence=0.85),
                metadata={"missing_fields": missing_info, "checked_subset": True},
            )
        )

    metrics = KillShotMetrics(
        penalty_exposure_avoided=Decimal("0.00"),
        carrier_overbilling_caught=quantize_currency(total_overbilling),
        drawback_unclaimed_unlocked=Decimal("0.00"),
    )
    return metrics, discrepancies
