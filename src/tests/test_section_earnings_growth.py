# -*- coding: utf-8 -*-
"""Earnings Growth section: net income per fiscal year from the aligned income statement (design §5.4)."""
import datetime

import pytest

from stockyard.data.fundamentals import aligned_annual_fundamentals
from stockyard.research.sections import earnings_growth
from tests.builders import stock_data
from tests.fixture_replay import load_stock_data

AS_OF = datetime.date(2026, 11, 11)


def _section(net_income_by_year):
    annual = {f"{year}-12-31": (100, value) for year, value in net_income_by_year.items()}
    data = stock_data(annual=annual)
    return earnings_growth(data, aligned_annual_fundamentals(data, AS_OF), AS_OF)


def test_year_over_year_change_and_percent_change():
    result = _section({2023: 100.0, 2024: 120.0, 2025: 90.0})

    assert result.years == (
        ("FY2023", 100.0, None, None),
        ("FY2024", 120.0, 20.0, pytest.approx(0.2)),
        ("FY2025", 90.0, -30.0, pytest.approx(-0.25)),
    )
    assert result.warnings == ()


def test_a_loss_turning_into_a_profit_is_growth():
    """Percent change divides by the absolute prior value, as in 0.1."""
    result = _section({2024: -50.0, 2025: 200.0})
    assert result.years[-1][3] == pytest.approx(5.0)


def test_a_zero_prior_year_has_no_percent_change():
    result = _section({2024: 0.0, 2025: 10.0})
    assert result.years[-1][2:] == (10.0, None)


def test_one_year_has_no_change_and_says_so():
    result = _section({2025: 10.0})
    (warning,) = result.warnings
    assert (warning.code, warning.section, warning.figure, warning.needed, warning.available) == (
        "figure_unavailable",
        "earnings_growth",
        "change",
        2,
        1,
    )


def test_msft_recorded():
    data, as_of = load_stock_data("MSFT")
    result = earnings_growth(data, aligned_annual_fundamentals(data, as_of), as_of)
    assert [row[0] for row in result.years] == ["FY2023", "FY2024", "FY2025", "FY2026"]
    assert result.years[-1][2] == pytest.approx(133_749e6 - 101_832e6)
