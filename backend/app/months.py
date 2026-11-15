"""Months as used across the app: "2026-11" in the API, date(2026, 11, 1) inside."""

import re
from datetime import date

from app.errors import InvalidInputError

_MONTH = re.compile(r"^(\d{4})-(0[1-9]|1[0-2])$")


def parse_month(value: str) -> date:
    """"2026-11" -> date(2026, 11, 1). Raises InvalidInputError otherwise."""
    match = _MONTH.match(value)
    if not match:
        raise InvalidInputError(f"month must look like 2026-11, got {value!r}")
    return date(int(match[1]), int(match[2]), 1)


def month_bounds(first_day: date) -> tuple[date, date]:
    """(first day, first day of the NEXT month): use as start <= day < end."""
    if first_day.month == 12:
        return first_day, date(first_day.year + 1, 1, 1)
    return first_day, date(first_day.year, first_day.month + 1, 1)
