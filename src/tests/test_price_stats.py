# -*- coding: utf-8 -*-
"""Shared per-fiscal-year price statistics and TTM dividends (design §5.4, §5.7)."""
import datetime

import pytest

from stockyard.data.fundamentals import aligned_annual_fundamentals
from stockyard.research.price_stats import (
    fiscal_year_price_stats,
    present_price,
    trailing_eps,
    ttm_dividends_per_share,
)
from tests.builders import daily_bars, quarterly_eps, stock_data

AS_OF = datetime.date(2026, 11, 11)
Q2024 = ["2024-03-31", "2024-06-30", "2024-09-30", "2024-12-31"]
Q2025 = ["2025-03-31", "2025-06-30", "2025-09-30", "2025-12-31"]


def _stats(data):
    return fiscal_year_price_stats(data, aligned_annual_fundamentals(data, AS_OF), AS_OF)


def test_each_complete_year_takes_high_low_and_dividends_from_its_own_window():
    """FY2025's window is (2024-12-31, 2025-12-31]: the bar on 2024-12-31 belongs to FY2024."""
    bars = daily_bars(
        {
            "2023-12-29": {},
            "2024-12-31": {"high": 99.0, "low": 1.0},  # FY2024's last day, not FY2025's
            "2025-02-03": {"low": 8.0},
            "2025-03-14": {"dividend": 0.5},
            "2025-09-15": {"dividend": 0.5},
            "2025-12-31": {"high": 12.0},  # FY2025's last day is inside its window
            "2026-11-10": {},
        }
    )
    data = stock_data(
        annual={"2024-12-31": (100, 10), "2025-12-31": (110, 11)},
        eps=quarterly_eps(Q2024, value=0.5) + quarterly_eps(Q2025, value=0.5),
        daily=bars,
    )

    fy2025 = _stats(data)[-1]

    assert fy2025.fiscal_year == "FY2025"
    assert (fy2025.high, fy2025.low, fy2025.eps) == (12.0, 8.0, pytest.approx(2.0))
    assert fy2025.dividends_per_share == pytest.approx(1.0)
    assert fy2025.pe_high == pytest.approx(6.0)
    assert fy2025.pe_low == pytest.approx(4.0)
    assert fy2025.payout == pytest.approx(0.5)
    assert fy2025.high_yield == pytest.approx(0.125)


def test_only_complete_fiscal_years_have_rows():
    data = stock_data(
        annual={"2024-12-31": (100, 10), "2025-12-31": (110, 11)},
        eps=quarterly_eps(Q2025),
        prices=("2023-12-29", "2026-11-10"),
    )

    assert [row.fiscal_year for row in _stats(data)] == ["FY2025"]


def test_non_positive_eps_years_have_no_pe_or_payout():
    data = stock_data(
        annual={"2025-12-31": (110, -5)}, eps=quarterly_eps(Q2025, value=-0.5), prices=("2024-12-02", "2026-11-10")
    )

    (row,) = _stats(data)
    assert row.eps == pytest.approx(-2.0)
    assert (row.pe_high, row.pe_low, row.payout) == (None, None, None)
    assert row.high is not None


def test_a_year_not_fully_traded_has_no_price_figures():
    """IPO in June 2025: FY2025's window is not covered (design §5.2.8)."""
    data = stock_data(annual={"2025-12-31": (110, 11)}, eps=quarterly_eps(Q2025), prices=("2025-06-13", "2026-11-10"))

    (row,) = _stats(data)
    assert row.eps == pytest.approx(4.0)
    assert (row.high, row.low, row.dividends_per_share, row.pe_high, row.high_yield) == (None,) * 5


def test_ttm_dividends_sum_the_365_days_up_to_as_of():
    bars = daily_bars(
        {
            "2025-01-02": {},
            "2025-11-10": {"dividend": 9.0},
            "2025-11-12": {"dividend": 0.5},
            "2026-05-12": {"dividend": 0.5},
            "2026-11-11": {},
        }
    )
    assert ttm_dividends_per_share(stock_data(daily=bars), AS_OF) == pytest.approx(1.0)


def test_ttm_dividends_are_zero_for_a_non_payer_and_none_without_a_year_of_prices():
    assert ttm_dividends_per_share(stock_data(prices=("2025-01-02", "2026-11-11")), AS_OF) == 0.0
    assert ttm_dividends_per_share(stock_data(prices=("2026-03-02", "2026-11-11")), AS_OF) is None


def test_present_price_is_the_last_close_on_or_before_as_of():
    bars = daily_bars({"2026-11-09": {"close": 50.0}, "2026-11-11": {"close": 60.0}, "2026-11-12": {"close": 70.0}})
    assert present_price(stock_data(daily=bars), AS_OF) == 60.0
    assert present_price(stock_data(), AS_OF) is None


def test_trailing_eps_sums_the_last_four_reports_on_or_before_as_of():
    eps = [
        ("2025-10-20", 1.0),
        ("2026-01-20", 1.1),
        ("2026-04-20", 1.2),
        ("2026-07-20", 1.3),
        ("2026-10-20", 1.4),
        ("2026-11-20", 9.0),
    ]
    assert trailing_eps(stock_data(eps=eps), AS_OF) == pytest.approx(5.0)
    assert trailing_eps(stock_data(eps=eps[:3]), AS_OF) is None
