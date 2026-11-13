# -*- coding: utf-8 -*-
"""Record of Stock section (design §5.4, §5.7): fiscal-year price history, P/E and dividends."""
import datetime

import pytest

from stockyard.data.fundamentals import aligned_annual_fundamentals
from stockyard.research.sections import record_of_stock
from tests.builders import daily_bars, quarterly_eps, stock_data
from tests.fixture_replay import load_stock_data

AS_OF = datetime.date(2026, 11, 11)


def _quarters(year):
    return [f"{year}-03-31", f"{year}-06-30", f"{year}-09-30", f"{year}-12-31"]


def _company(eps_2024=1.0):
    """FY2024: high 40 low 20, EPS 4 x eps_2024; FY2025: high 60 low 30, EPS 4.00; present close 50."""
    bars = daily_bars(
        {
            "2023-12-29": {},
            "2024-03-01": {"high": 40.0},
            "2024-06-03": {"low": 20.0, "dividend": 1.0},
            "2025-03-03": {"high": 60.0},
            "2025-06-02": {"low": 30.0, "dividend": 1.0},
            "2026-11-11": {"close": 50.0},
        },
        base_low=35.0,
        base_high=36.0,
    )
    eps = quarterly_eps(_quarters(2024), eps_2024) + quarterly_eps(_quarters(2025), 1.0)
    eps += [("2026-04-25", 1.0), ("2026-07-25", 1.0), ("2026-10-25", 1.0)]  # TTM = 4.00
    return stock_data(annual={"2024-12-31": (100, 10), "2025-12-31": (110, 11)}, eps=eps, daily=bars)


def _section(data):
    return record_of_stock(data, aligned_annual_fundamentals(data, AS_OF), AS_OF)


def test_rows_averages_and_current_figures():
    result = _section(_company())

    assert [(r.fiscal_year, r.high, r.low, r.eps) for r in result.rows] == [
        ("FY2024", 40.0, 20.0, 4.0),
        ("FY2025", 60.0, 30.0, 4.0),
    ]
    assert result.average_high == pytest.approx(50.0)
    assert result.average_low == pytest.approx(25.0)
    assert result.average_pe_high == pytest.approx(12.5)  # (10 + 15) / 2
    assert result.average_pe_low == pytest.approx(6.25)  # (5 + 7.5) / 2
    assert result.average_pe == pytest.approx((10 + 15 + 5 + 7.5) / 4)
    assert result.average_payout == pytest.approx(0.25)
    assert (result.present_price, result.ttm_eps, result.current_pe) == (50.0, pytest.approx(4.0), pytest.approx(12.5))
    assert result.oldest_fiscal_year == "FY2024"
    assert result.change_from_oldest_high == pytest.approx(50 / 40 - 1)
    assert result.warnings == ()


def test_loss_years_are_listed_but_left_out_of_pe_averages():
    result = _section(_company(eps_2024=-0.5))

    assert result.rows[0].pe_high is None
    assert result.average_pe_high == pytest.approx(15.0)
    assert ("non_positive_eps", "FY2024") in {(w.code, w.message.split(":")[0]) for w in result.warnings}


def test_rddt_recorded_ipo_year_is_listed_without_prices():
    data, as_of = load_stock_data("RDDT")
    result = record_of_stock(data, aligned_annual_fundamentals(data, as_of), as_of)

    fy2024, fy2025 = result.rows
    assert fy2024.fiscal_year == "FY2024" and fy2024.high is None
    assert fy2025.high is not None
    assert result.oldest_fiscal_year == "FY2025"
    assert ("figure_unavailable", "FY2024") in {(w.code, w.message.split(":")[0]) for w in result.warnings}
