# -*- coding: utf-8 -*-
"""Revenue Growth section, including Lynch's dividend-adjusted ratio (design §5.4, §5.7, D15)."""
import datetime

import pytest

from stockyard.data.fundamentals import aligned_annual_fundamentals
from stockyard.research.sections import revenue_growth
from tests.builders import daily_bars, quarterly_eps, stock_data
from tests.fixture_replay import load_stock_data

AS_OF = datetime.date(2026, 11, 11)


def _company(dividend_per_quarter=0.5, quarter_eps=(1.0, 1.0, 1.0, 1.0, 1.25, 1.25, 1.25, 1.25)):
    """Two complete years (EPS 4.00 -> 5.00), price 100, dividends 0.50 a quarter for the last year."""
    quarters = [
        "2024-03-31",
        "2024-06-30",
        "2024-09-30",
        "2024-12-31",
        "2025-03-31",
        "2025-06-30",
        "2025-09-30",
        "2025-12-31",
    ]
    eps = [(announced, value) for (announced, _), value in zip(quarterly_eps(quarters), quarter_eps)]
    eps += [("2026-04-25", 1.25), ("2026-07-25", 1.25), ("2026-10-25", 1.25)]  # TTM = 1.25 * 4 = 5.00
    bars = {"2025-11-03": {}, "2026-11-11": {"close": 100.0}}
    for day in ("2025-12-15", "2026-03-16", "2026-06-15", "2026-09-15"):
        bars[day] = {"dividend": dividend_per_quarter}
    return stock_data(
        annual={"2023-12-31": (80.0, 8), "2024-12-31": (100.0, 10), "2025-12-31": (125.0, 12)},
        eps=eps,
        daily=daily_bars(bars),
    )


def _section(data):
    return revenue_growth(data, aligned_annual_fundamentals(data, AS_OF), AS_OF)


def test_revenue_change_by_year_and_average_growth():
    result = _section(_company())

    assert result.years == (
        ("FY2023", 80.0, None, None),
        ("FY2024", 100.0, 20.0, pytest.approx(0.25)),
        ("FY2025", 125.0, 25.0, pytest.approx(0.25)),
    )
    assert result.average_growth == pytest.approx(0.25)


def test_dividends_yield_pe_and_lynch_ratio():
    result = _section(_company())

    assert result.ttm_dividends_per_share == pytest.approx(2.0)
    assert result.dividend_yield == pytest.approx(0.02)
    assert result.present_price == 100.0 and result.ttm_eps == pytest.approx(5.0)
    assert result.current_pe == pytest.approx(20.0)
    assert result.eps_cagr == pytest.approx(0.25)  # 4.00 -> 5.00 over one period
    assert result.lynch_ratio == pytest.approx((25 + 2) / 20)  # (EPS growth % + yield %) / P/E
    assert result.warnings == ()


def test_lynch_ratio_is_null_with_a_reason_when_eps_growth_is_unavailable():
    result = _section(_company(quarter_eps=(-1.0, -1.0, -1.0, -1.0, 1.25, 1.25, 1.25, 1.25)))

    assert result.eps_cagr is None and result.lynch_ratio is None
    codes = {(w.code, w.figure) for w in result.warnings}
    assert ("non_positive_eps", "eps_cagr") in codes
    assert ("figure_unavailable", "lynch_ratio") in codes


def test_a_non_payer_has_zero_yield_and_still_gets_a_lynch_ratio():
    result = _section(_company(dividend_per_quarter=0.0))
    assert result.dividend_yield == 0.0
    assert result.lynch_ratio == pytest.approx(25 / 20)


def test_msft_recorded_lynch_ratio_from_its_own_figures():
    data, as_of = load_stock_data("MSFT")
    result = revenue_growth(data, aligned_annual_fundamentals(data, as_of), as_of)

    assert result.lynch_ratio == pytest.approx(
        (result.eps_cagr * 100 + result.dividend_yield * 100) / result.current_pe
    )
    assert result.current_pe == pytest.approx(result.present_price / result.ttm_eps)
