"""Unit tests for months.py."""

from datetime import date

import pytest

from app.errors import InvalidInputError
from app.months import month_bounds, parse_month


def test_parse_month_gives_the_first_day():
    assert parse_month("2026-11") == date(2026, 11, 1)


@pytest.mark.parametrize("bad", ["2026-13", "2026-00", "2026-1", "26-11", "2026/11", "november", ""])
def test_parse_month_rejects_anything_else(bad):
    with pytest.raises(InvalidInputError):
        parse_month(bad)


def test_month_bounds_end_at_the_next_month():
    assert month_bounds(date(2026, 2, 1)) == (date(2026, 2, 1), date(2026, 3, 1))


def test_december_rolls_over_to_january():
    assert month_bounds(date(2026, 12, 1)) == (date(2026, 12, 1), date(2027, 1, 1))
