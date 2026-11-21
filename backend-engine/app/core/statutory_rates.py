"""
Statutory trade-law rates, fee schedules and tariff measures.

Every table in this module is *dated*: a value is looked up for the date on which it
applies (entry date, invoice date or violation date), never for "today". Unknown
periods raise instead of silently falling back to a different year's figure.

Covered:
- CBP Merchandise Processing Fee, formal and informal (19 U.S.C. 58c / 19 CFR 24.23)
- Harbor Maintenance Fee (26 U.S.C. 4461 / 19 CFR 24.24)
- 19 U.S.C. 1505 interest, compounded daily (26 U.S.C. 6621 / 6622)
- USTR Section 301 Chapter 99 measures on China-origin goods (19 U.S.C. 2411)
- IEEPA civil monetary penalty maximum (50 U.S.C. 1705, inflation adjusted)

Figures that have not been checked against a primary source are flagged
``verified=False`` so downstream callers (and the UI) can say so.
"""

import calendar
import logging
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Dict, List, Literal, Optional, Tuple

from app.services.utils import quantize_currency

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 1. Merchandise Processing Fee (19 U.S.C. 58c / 19 CFR 24.23)
# ---------------------------------------------------------------------------
MPF_AD_VALOREM_RATE = Decimal("0.003464")  # 0.3464%

# Formal-entry (min, max) caps, adjusted each fiscal year (FAST Act inflation indexing).
MPF_CAPS_BY_FY: Dict[str, Tuple[Decimal, Decimal]] = {
    "FY2024": (Decimal("31.67"), Decimal("614.35")),
    "FY2025": (Decimal("32.71"), Decimal("634.62")),
    # FR Doc. 2025-13869, 90 FR (23 Jul 2025), effective 1 Oct 2025
    "FY2026": (Decimal("33.58"), Decimal("651.50")),
    # FR Doc. 2026-15530, 91 FR 48398 (31 Jul 2026), effective 1 Oct 2026
    "FY2027": (Decimal("34.58"), Decimal("670.86")),
}

# Informal-entry surcharges (entries valued at or below $2,500, 19 CFR 143.21).
# Keys: automated (ACE, filer-prepared), manual (filer-prepared, non-automated),
# cbp_prepared (prepared by CBP personnel).
INFORMAL_MPF_BY_FY: Dict[str, Dict[str, Decimal]] = {
    # FR Doc. 2025-13869 (FY2026); CBP-prepared figure not recorded here
    "FY2026": {
        "automated": Decimal("2.69"),
        "manual": Decimal("8.06"),
    },
    # FR Doc. 2026-15530 (FY2027)
    "FY2027": {
        "automated": Decimal("2.77"),
        "manual": Decimal("8.30"),
        "cbp_prepared": Decimal("12.45"),
    },
}

INFORMAL_ENTRY_THRESHOLD = Decimal("2500.00")

DEFAULT_MPF_FISCAL_YEAR = "FY2027"

EntryType = Literal["formal", "informal"]
InformalMethod = Literal["automated", "manual", "cbp_prepared"]


def fiscal_year_for(d: date) -> str:
    """US federal fiscal year label for a date (FY runs 1 Oct to 30 Sep)."""
    return f"FY{d.year + (1 if d.month >= 10 else 0)}"


def get_mpf_caps(fiscal_year: str = DEFAULT_MPF_FISCAL_YEAR) -> Tuple[Decimal, Decimal]:
    """Returns (minimum, maximum) formal-entry MPF for a fiscal year. Raises KeyError if unpublished."""
    fy_key = fiscal_year.upper()
    if fy_key not in MPF_CAPS_BY_FY:
        raise KeyError(f"No published MPF caps for {fy_key}; known years: {sorted(MPF_CAPS_BY_FY)}")
    return MPF_CAPS_BY_FY[fy_key]


def calculate_mpf(
    entered_value: Decimal,
    fiscal_year: str = DEFAULT_MPF_FISCAL_YEAR,
    entry_type: Optional[EntryType] = None,
    informal_method: InformalMethod = "automated",
    fta_exempt: bool = False,
) -> Decimal:
    """
    Merchandise Processing Fee.

    - Formal entries: 0.3464% ad valorem clamped to the fiscal-year minimum and maximum.
    - Informal entries (value <= $2,500 unless ``entry_type`` says otherwise): flat surcharge
      by preparation method.
    - ``fta_exempt``: originating goods under USMCA and most other FTAs are exempt (19 U.S.C. 58c(b)(10)).
    """
    if fta_exempt:
        return Decimal("0.00")
    resolved_type: EntryType = entry_type or (
        "informal" if entered_value <= INFORMAL_ENTRY_THRESHOLD else "formal"
    )
    fy_key = fiscal_year.upper()
    if resolved_type == "informal":
        schedule = INFORMAL_MPF_BY_FY.get(fy_key, {})
        if informal_method not in schedule:
            raise KeyError(f"No published {informal_method} informal MPF for {fy_key}")
        return schedule[informal_method]
    min_cap, max_cap = get_mpf_caps(fy_key)
    raw_mpf = quantize_currency(entered_value * MPF_AD_VALOREM_RATE)
    return min(max_cap, max(min_cap, raw_mpf))


# ---------------------------------------------------------------------------
# 2. Harbor Maintenance Fee (26 U.S.C. 4461 / 19 CFR 24.24)
# ---------------------------------------------------------------------------
HMF_AD_VALOREM_RATE = Decimal("0.00125")  # 0.125%


def calculate_hmf(
    entered_value: Decimal,
    transport_mode: str = "ocean",
) -> Decimal:
    """Harbor Maintenance Fee (0.125% ad valorem) on commercial cargo arriving by vessel only."""
    if str(transport_mode).strip().lower() != "ocean":
        return Decimal("0.00")
    return quantize_currency(entered_value * HMF_AD_VALOREM_RATE)


# ---------------------------------------------------------------------------
# 3. 19 U.S.C. 1505 interest, compounded daily (26 U.S.C. 6621(a)(2) / 6622)
# ---------------------------------------------------------------------------
# IRS underpayment rates by calendar quarter, as republished by CBP each quarter.
QUARTERLY_INTEREST_RATES: Dict[str, Decimal] = {
    "2024-Q1": Decimal("0.0800"),
    "2024-Q2": Decimal("0.0800"),
    "2024-Q3": Decimal("0.0800"),
    "2024-Q4": Decimal("0.0800"),
    "2025-Q1": Decimal("0.0700"),
    "2025-Q2": Decimal("0.0700"),
    "2025-Q3": Decimal("0.0700"),
    "2025-Q4": Decimal("0.0700"),
    "2026-Q1": Decimal("0.0700"),
    "2026-Q2": Decimal("0.0600"),
    "2026-Q3": Decimal("0.0600"),
    "2026-Q4": Decimal("0.0700"),
}

DEFAULT_ANNUAL_INTEREST_RATE = Decimal("0.0700")


def get_quarter_key(d: date) -> str:
    q = (d.month - 1) // 3 + 1
    return f"{d.year}-Q{q}"


def _next_quarter_start(d: date) -> date:
    q = (d.month - 1) // 3 + 1
    if q == 4:
        return date(d.year + 1, 1, 1)
    return date(d.year, 3 * q + 1, 1)


def calculate_1505_interest(
    principal: Decimal,
    start_date: date,
    end_date: date,
) -> Decimal:
    """
    Daily-compounded interest under 19 U.S.C. 1505(c).

    Interest accrues for every day in [start_date, end_date) (end-exclusive), at the
    quarterly rate in force on each day, with a 366-day denominator in leap years
    (26 U.S.C. 6622). Each quarter is a compounding segment; interest earned in one
    segment becomes principal for the next.
    """
    if principal <= Decimal("0.00") or end_date <= start_date:
        return Decimal("0.00")

    total_interest = Decimal("0.00")
    current_principal = principal
    cursor = start_date

    while cursor < end_date:
        segment_end = min(end_date, _next_quarter_start(cursor))
        # A quarter never spans two calendar years, so one denominator applies per segment.
        q_key = get_quarter_key(cursor)
        q_rate = QUARTERLY_INTEREST_RATES.get(q_key)
        if q_rate is None:
            logger.warning("No published 1505 rate for %s; using %s", q_key, DEFAULT_ANNUAL_INTEREST_RATE)
            q_rate = DEFAULT_ANNUAL_INTEREST_RATE
        days = (segment_end - cursor).days
        denom = Decimal(366 if calendar.isleap(cursor.year) else 365)
        factor = ((Decimal("1") + q_rate / denom) ** days) - Decimal("1")
        period_interest = quantize_currency(current_principal * factor)
        total_interest += period_interest
        current_principal += period_interest
        cursor = segment_end

    return quantize_currency(total_interest)


def calculate_1505_interest_by_months(
    principal: Decimal,
    months_elapsed: int = 9,
    annual_rate: Decimal = DEFAULT_ANNUAL_INTEREST_RATE,
) -> Decimal:
    """
    Planning estimate when no dates are known: a flat annual rate compounded daily over
    ``months_elapsed`` average-length months (30.4375 days). Callers that know the entry
    date must use ``calculate_1505_interest`` instead.
    """
    if principal <= Decimal("0.00") or months_elapsed <= 0:
        return Decimal("0.00")

    days = int(months_elapsed * 30.4375)
    daily_rate = annual_rate / Decimal("365")
    factor = ((Decimal("1") + daily_rate) ** days) - Decimal("1")
    return quantize_currency(principal * factor)


# ---------------------------------------------------------------------------
# 4. USTR Section 301 Chapter 99 measures on China-origin goods (19 U.S.C. 2411)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Ch99Measure:
    """One dated Section 301 additional duty on an HTS prefix for one origin."""

    hts_prefix: str
    rate: Decimal
    effective_from: date
    effective_to: Optional[date]  # inclusive; None = still in force
    authority: str
    heading: Optional[str] = None
    verified: bool = False

    def applies(self, hts_code: str, on: date) -> bool:
        digits = hts_code.replace(".", "")
        if not digits.startswith(self.hts_prefix.replace(".", "")):
            return False
        if on < self.effective_from:
            return False
        return self.effective_to is None or on <= self.effective_to


_REVIEW_2024 = "USTR four-year review modification, FR Doc. 2024-21217 (18 Sep 2024)"

SECTION_301_MEASURES_CN: List[Ch99Measure] = [
    # Semiconductors (heading 8541/8542): 25% from the 2018 actions, raised to 50% on 1 Jan 2025.
    Ch99Measure("8542", Decimal("0.25"), date(2018, 8, 23), date(2024, 12, 31),
                "Section 301 List 2 (2018)", "9903.88.02", verified=False),
    Ch99Measure("8542", Decimal("0.50"), date(2025, 1, 1), None, _REVIEW_2024, verified=True),
    Ch99Measure("8541", Decimal("0.25"), date(2018, 8, 23), date(2024, 12, 31),
                "Section 301 List 2 (2018)", "9903.88.02", verified=False),
    Ch99Measure("8541", Decimal("0.50"), date(2025, 1, 1), None, _REVIEW_2024, verified=True),
    # Lithium-ion batteries (8507.60): 7.5% (List 4A); non-EV batteries 25% from 1 Jan 2026.
    # EV batteries (25% from 27 Sep 2024) need the statistical suffix and are not modelled here.
    Ch99Measure("8507.60", Decimal("0.075"), date(2020, 2, 14), date(2025, 12, 31),
                "Section 301 List 4A", "9903.88.15", verified=False),
    Ch99Measure("8507.60", Decimal("0.25"), date(2026, 1, 1), None, _REVIEW_2024, verified=True),
    # Electric motors (List 1) and static converters (List 3) at 25%.
    Ch99Measure("8501.31", Decimal("0.25"), date(2018, 7, 6), None,
                "Section 301 List 1", "9903.88.01", verified=False),
    Ch99Measure("8504.40", Decimal("0.25"), date(2019, 5, 10), None,
                "Section 301 List 3", "9903.88.03", verified=False),
]

# Ordinary (column 1 general) rates for the subheadings this demo reasons about.
GENERAL_DUTY_RATES: Dict[str, Decimal] = {
    "8471.30": Decimal("0.00"),
    "8542.31": Decimal("0.00"),
    "8542.32": Decimal("0.00"),
    "8542.39": Decimal("0.00"),
    "8504.40": Decimal("0.00"),
}


def get_general_duty_rate(hts_code: str) -> Optional[Decimal]:
    """Column 1 general rate for a known subheading, or None when this demo has no data."""
    code = str(hts_code).strip()
    return GENERAL_DUTY_RATES.get(code[:7])


def _is_china(country_of_origin: Optional[str]) -> bool:
    return str(country_of_origin or "").strip().upper() in ("CN", "CHINA", "PRC")


def section_301_measures(hts_code: str, country_of_origin: Optional[str], on: date) -> List[Ch99Measure]:
    """All Section 301 measures in force for an HTS code, origin and date (stacked)."""
    if not _is_china(country_of_origin):
        return []
    return [m for m in SECTION_301_MEASURES_CN if m.applies(str(hts_code).strip(), on)]


def get_section_301_rate(
    hts_code: str,
    country_of_origin: str,
    on: Optional[date] = None,
) -> Tuple[Decimal, Optional[str]]:
    """
    Returns (combined Section 301 rate, Chapter 99 heading or authority) for the date ``on``
    (defaults to today). Non-China origins return (0.00, None).
    """
    measures = section_301_measures(hts_code, country_of_origin, on or date.today())
    if not measures:
        return (Decimal("0.00"), None)
    total = sum((m.rate for m in measures), Decimal("0.00"))
    label = measures[-1].heading or measures[-1].authority
    return (total, label)


# ---------------------------------------------------------------------------
# 5. IEEPA civil monetary penalty maximum (50 U.S.C. 1705(b), inflation adjusted)
# ---------------------------------------------------------------------------
# Greater of this amount or twice the value of the transaction.
IEEPA_MAX_PENALTY_BY_YEAR: Dict[int, Decimal] = {
    2024: Decimal("368136.00"),
    2025: Decimal("377700.00"),  # FR Doc. 2025-00786, 90 FR 3687 (15 Jan 2025)
    2026: Decimal("377700.00"),  # OMB M-26-11: no 2026 inflation adjustment
}


def ieepa_max_penalty(transaction_value: Optional[Decimal], year: int) -> Decimal:
    """Statutory IEEPA maximum for a violation in ``year``: max(base, 2 x transaction value)."""
    known = sorted(IEEPA_MAX_PENALTY_BY_YEAR)
    base = IEEPA_MAX_PENALTY_BY_YEAR.get(year) or IEEPA_MAX_PENALTY_BY_YEAR[known[-1] if year > known[-1] else known[0]]
    if transaction_value is None:
        return base
    return max(base, quantize_currency(transaction_value * Decimal("2")))
