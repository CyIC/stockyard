# -*- coding: utf-8 -*-
"""Risk & Reward section (design §5.6, §5.7; D14 zones 25/50/25 and average of fiscal-year lows)."""
import datetime

import pandas as pd
import pytest

from stockyard.data.fundamentals import aligned_annual_fundamentals
from stockyard.research.sections import risk_reward
from tests.builders import daily_bars, quarterly_eps, stock_data
from tests.fixture_replay import load_stock_data

AS_OF = datetime.date(2026, 11, 11)
QUARTERS = [f"{y}-{md}" for y in (2022, 2023, 2024, 2025) for md in ("03-31", "06-30", "09-30", "12-31")]


def _company(present_close=35.0, quarter_eps=None):
    """Four complete fiscal years (D19), EPS 4.00 each, $1 dividend a year.

    Prices start late 2023, so only FY2024 (high 40 / low 20) and FY2025 (high 60 / low 30) have price figures.
    """
    bars = daily_bars(
        {
            "2023-12-29": {},
            "2024-03-01": {"high": 40.0},
            "2024-06-03": {"low": 20.0, "dividend": 1.0},
            "2025-03-03": {"high": 60.0},
            "2025-06-02": {"low": 30.0, "dividend": 1.0},
            "2026-06-15": {"dividend": 1.0},
            "2026-11-11": {"close": present_close},
        },
        base_low=35.0,
        base_high=36.0,
    )
    eps = quarterly_eps(QUARTERS) + [("2026-04-25", 1.0), ("2026-07-25", 1.0), ("2026-10-25", 1.0)]
    if quarter_eps is not None:
        eps = [(day, value) for (day, _), value in zip(eps, quarter_eps)]
    annual = {"2022-12-31": (90, 9), "2023-12-31": (95, 9), "2024-12-31": (100, 10), "2025-12-31": (110, 11)}
    return stock_data(annual=annual, eps=eps, daily=bars)


def _section(data):
    return risk_reward(data, aligned_annual_fundamentals(data, AS_OF), AS_OF)


def _low(result, name):
    (estimate,) = [low for low in result.lows if low.name == name]
    return estimate


def test_forecast_high_is_average_pe_high_times_projected_eps():
    result = _section(_company())

    assert result.average_pe_high == pytest.approx(12.5)
    assert result.projected_eps == pytest.approx(4.0)
    assert result.forecast_high == pytest.approx(50.0)
    assert result.price_target_appreciation == pytest.approx(50 / 35 - 1)


def test_average_low_is_the_mean_of_fiscal_year_lows_not_daily_lows():
    """D14 / design §16.8: 0.1 averaged every daily low."""
    assert _low(_section(_company()), "average_low").value == pytest.approx(25.0)


def test_severe_and_dividend_support_lows():
    result = _section(_company())
    assert _low(result, "severe_low").value == pytest.approx(20.0)
    assert _low(result, "dividend_support").value == pytest.approx(1.0 / 0.05)


def test_zones_position_and_up_down_ratio_per_low():
    average = _low(_section(_company()), "average_low")

    assert average.zones.buy == pytest.approx((25.0, 31.25))
    assert average.zones.sell == pytest.approx((43.75, 50.0))
    assert average.position == "maybe"
    assert average.up_down_ratio == pytest.approx(1.5)


def test_linear_regression_low_projects_the_trend_of_daily_lows_five_years_ahead():
    start = pd.Timestamp("2021-11-15")
    days = pd.bdate_range(start, "2026-11-11")
    lows = {day.strftime("%Y-%m-%d"): {"low": 10 + 0.01 * (day - start).days} for day in days}
    data = stock_data(daily=daily_bars(lows, base_low=0.0, base_high=100.0))

    result = _section(data)

    horizon = pd.Timestamp("2031-11-11")
    assert _low(result, "linear_regression").value == pytest.approx(10 + 0.01 * (horizon - start).days, rel=1e-4)


def test_a_falling_earnings_trend_quotes_no_forecast_and_no_zones():
    falling = [3.6 - 0.2 * i for i in range(19)]  # positive fiscal years, TTM trend heading below zero
    result = _section(_company(quarter_eps=falling))

    assert result.forecast_high is None and result.price_target_appreciation is None
    assert all(low.zones is None and low.up_down_ratio is None for low in result.lows)
    assert ("figure_unavailable", "forecast_high") in {(w.code, w.figure) for w in result.warnings}


def test_a_price_above_the_forecast_high_is_above_range_without_a_ratio():
    average = _low(_section(_company(present_close=55.0)), "average_low")
    result = _section(_company(present_close=55.0))

    assert average.position == "above_range" and average.up_down_ratio is None
    assert "price_above_range" in {w.code for w in result.warnings}


def test_too_few_quarters_for_a_trend_says_how_many():
    data = stock_data(
        annual={"2025-12-31": (110, 11)}, eps=quarterly_eps(QUARTERS[-4:]), prices=("2024-12-02", "2026-11-11")
    )
    result = _section(data)

    (warning,) = [w for w in result.warnings if w.figure == "projected_eps"]
    assert (warning.needed, warning.available) == (5, 4)


def test_msft_recorded_forecast_is_consistent():
    data, as_of = load_stock_data("MSFT")
    result = risk_reward(data, aligned_annual_fundamentals(data, as_of), as_of)

    assert result.forecast_high == pytest.approx(result.average_pe_high * result.projected_eps)
    average = _low(result, "average_low")
    assert average.zones.buy[1] == pytest.approx(average.value + (result.forecast_high - average.value) / 4)


def test_no_forecast_without_four_complete_fiscal_years_but_lows_still_shown():
    """D19: an IPO's short, distorted EPS trend must not produce a price target."""
    data, as_of = load_stock_data("RDDT")
    result = risk_reward(data, aligned_annual_fundamentals(data, as_of), as_of)

    assert result.forecast_high is None and result.price_target_appreciation is None
    assert all(low.zones is None for low in result.lows)
    assert _low(result, "average_low").value is not None
    (warning,) = [w for w in result.warnings if w.figure == "forecast_high"]
    assert (warning.needed, warning.available) == (4, 2)
