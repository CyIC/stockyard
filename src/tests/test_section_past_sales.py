# -*- coding: utf-8 -*-
"""Past Sales Records section (design §5.4, §5.6, §5.7)."""
import datetime

import pytest

from stockyard.data.fundamentals import aligned_annual_fundamentals
from stockyard.research.sections import past_sales
from tests.builders import stock_data
from tests.fixture_replay import load_stock_data

AS_OF = datetime.date(2026, 11, 11)


def _section(annual):
    data = stock_data(annual=annual)
    return past_sales(data, aligned_annual_fundamentals(data, AS_OF), AS_OF)


def test_lists_revenue_per_fiscal_year_and_computes_growth():
    result = _section(
        {"2022-12-31": (100, 1), "2023-12-31": (120, 1), "2024-12-31": (150, 1), "2025-12-31": (133.1, 1)}
    )

    assert result.years == (("FY2022", 100.0), ("FY2023", 120.0), ("FY2024", 150.0), ("FY2025", pytest.approx(133.1)))
    assert result.recent_pair_average == pytest.approx((150 + 133.1) / 2)
    assert result.oldest_pair_average == pytest.approx(110)
    assert result.pair_increase == pytest.approx(((150 + 133.1) / 2 - 110) / 110)
    assert result.cagr == pytest.approx(0.10)  # 100 -> 133.1 over three periods
    assert result.warnings == ()


def test_years_without_revenue_are_left_out():
    """The oldest recorded IBM statement is empty."""
    result = _section({"2024-12-31": (None, None), "2025-12-31": (110, 1)})
    assert result.years == (("FY2025", 110.0),)


def test_short_history_nulls_each_figure_with_a_warning():
    result = _section({"2024-12-31": (100, 1), "2025-12-31": (110, 1)})

    assert result.cagr == pytest.approx(0.10)
    assert (result.recent_pair_average, result.oldest_pair_average, result.pair_increase) == (None, None, None)
    (warning,) = result.warnings
    assert (warning.code, warning.section, warning.figure) == ("figure_unavailable", "past_sales", "pair_increase")
    assert (warning.needed, warning.available) == (4, 2)


def test_one_year_has_no_growth_figures():
    result = _section({"2025-12-31": (110, 1)})

    assert result.cagr is None
    assert {w.figure for w in result.warnings} == {"cagr", "pair_increase"}


def test_ibm_recorded():
    data, as_of = load_stock_data("IBM")
    result = past_sales(data, aligned_annual_fundamentals(data, as_of), as_of)

    assert [fy for fy, _ in result.years] == ["FY2022", "FY2023", "FY2024", "FY2025"]
    assert result.cagr == pytest.approx((67_536 / 60_530) ** (1 / 3) - 1)
