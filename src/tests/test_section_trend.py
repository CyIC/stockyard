# -*- coding: utf-8 -*-
"""Trend section: chart data only, within five years of as_of (design §5.4)."""
import datetime

import pytest

from stockyard.data.fundamentals import aligned_annual_fundamentals
from stockyard.research.sections import trend
from tests.builders import daily_bars, stock_data

AS_OF = datetime.date(2026, 11, 11)


def _section(data):
    return trend(data, aligned_annual_fundamentals(data, AS_OF), AS_OF)


def test_quarterly_revenue_and_eps_within_five_years_and_on_or_before_as_of():
    data = stock_data(
        quarterly={"2021-06-30": (1, 0), "2026-06-30": (5, 0), "2026-09-30": (6, 0), "2026-12-31": (7, 0)},
        eps=[("2021-07-20", 0.1), ("2026-07-20", 1.0), ("2026-10-20", 1.1), ("2026-11-20", 9.9)],
    )
    result = _section(data)

    assert result.quarterly_revenue == (("2026-06-30", 5.0), ("2026-09-30", 6.0))
    assert result.quarterly_eps == (("2026-07-20", 1.0), ("2026-10-20", 1.1))


def test_monthly_highs_and_lows_with_four_month_averages():
    bars = daily_bars(
        {
            "2026-07-01": {"high": 10.0, "low": 5.0},
            "2026-08-03": {"high": 14.0, "low": 6.0},
            "2026-09-01": {"high": 12.0, "low": 4.0},
            "2026-10-01": {"high": 16.0, "low": 8.0},
            "2026-11-11": {},
        },
        base_low=9.0,
        base_high=9.5,
    )
    result = _section(stock_data(daily=bars))

    months = {row[0]: row for row in result.monthly_prices}
    assert months["2026-08"][1:3] == (14.0, 6.0)
    assert months["2026-07"][3] is None  # fewer than four months yet
    assert months["2026-10"][3] == pytest.approx((10 + 14 + 12 + 16) / 4)
    assert months["2026-10"][4] == pytest.approx((5 + 6 + 4 + 8) / 4)


def test_no_data_warns_instead_of_failing():
    result = _section(stock_data())
    assert (result.quarterly_revenue, result.quarterly_eps, result.monthly_prices) == ((), (), ())
    assert {w.figure for w in result.warnings} == {"quarterly_revenue", "quarterly_eps", "monthly_prices"}
