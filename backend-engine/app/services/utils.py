"""Shared utility functions for currency, decimal math, and common operations."""

from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Optional


def quantize_currency(amount: Decimal) -> Decimal:
    """Quantize financial amounts to 2 decimal places using ROUND_HALF_UP."""
    if not isinstance(amount, Decimal):
        amount = Decimal(str(amount))
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def safe_decimal(val: Any, default: str = "0.00") -> Decimal:
    """Safely convert value to Decimal, falling back to default on None, empty string, or error."""
    if val is None or val == "":
        return Decimal(default)
    try:
        return Decimal(str(val))
    except Exception:
        return Decimal(default)


def optional_decimal(val: Any) -> Optional[Decimal]:
    """Decimal for a present value, None for a missing or unparseable one (never a guessed default)."""
    if val is None or val == "":
        return None
    try:
        d = Decimal(str(val))
    except Exception:
        return None
    return d if d.is_finite() else None


def parse_iso_date(val: Any) -> Optional[date]:
    """Parse an ISO date (YYYY-MM-DD) or pass a date through; None when absent or invalid."""
    if val is None or val == "":
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    try:
        return date.fromisoformat(str(val)[:10])
    except ValueError:
        return None
