# -*- coding: utf-8 -*-
# pylint: disable=C0116, W0212, R0801
"""Numeric correctness tests for the calculations in stock_analysis.

The sibling test_stock_analysis module asserts return *types* only. These tests assert the
actual arithmetic, using hand-built fixtures with round numbers so every expected value is
computable by hand rather than restated from whatever the code happens to emit.
"""
import asyncio
import datetime
import re
from unittest.mock import AsyncMock, MagicMock, patch

import matplotlib
import numpy as np
import pandas as pd
import pytest
from dateutil.relativedelta import relativedelta

# under test
from stockyard import stock_analysis

matplotlib.use("Agg")  # headless: risk_reward writes chart files


# --------------------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------------------
def _clean(line):
    """Strip the surrounding discord markdown fence off a rendered table line."""
    return line.strip().strip("`").strip()


def _row(msg, label):
    """Return the stripped cells of a bordered PrettyTable row whose first cell equals label."""
    for line in msg.splitlines():
        cells = [cell.strip() for cell in _clean(line).strip("|").split("|")]
        if cells and cells[0] == label:
            return cells
    raise AssertionError(f"no row labelled {label!r} in:\n{msg}")


def _field(msg, label):
    """Return the trailing value of a borderless PrettyTable row beginning with label."""
    for line in msg.splitlines():
        stripped = _clean(line)
        if stripped.startswith(label):
            return stripped[len(label) :].strip()  # noqa: E203
    raise AssertionError(f"no row beginning {label!r} in:\n{msg}")


def _pct(text):
    """Parse a percent-formatted cell such as '8.000%' into a fraction."""
    return float(text.replace("%", "").replace(",", "").strip("` ")) / 100


def _money(text):
    """Parse a currency-formatted cell such as '$  1,234' into a float."""
    return float(text.replace("$", "").replace(",", "").strip("` "))


def _labelled(msg, label):
    """Return the numeric text following 'label:' in a rendered report message.

    The report concatenates its labelled figures onto the tail of a DataFrame repr with no
    separating newline, so these have to be matched by pattern rather than by line.
    """
    match = re.search(re.escape(label) + r":\s*(-?[\d.,]+%?)", msg)
    if match is None:
        raise AssertionError(f"no {label!r} value in:\n{msg}")
    return match.group(1)


def _annual_index(count):
    """Build `count` ascending annual timestamps that all survive a 5-year lookback filter.

    Anchored to now so the `datetime.datetime.now() - relativedelta(years=5)` filters inside
    stock_analysis keep exactly these rows regardless of the date the suite runs.
    """
    now = datetime.datetime.now()
    return pd.to_datetime([now - relativedelta(years=count - 1 - offset, months=6) for offset in range(count)])


# --------------------------------------------------------------------------------------
# populate_vars
# --------------------------------------------------------------------------------------
@pytest.mark.parametrize(
    "old, new, expected_diff, expected_percent",
    [
        (100.0, 120.0, 20.0, 0.2),
        (100.0, 80.0, -20.0, -0.2),
        # abs() in the denominator keeps the sign of the swing, not of the base
        (-50.0, 50.0, 100.0, 2.0),
        (-50.0, -75.0, -25.0, -0.5),
    ],
)
def test_populate_vars_computes_difference_and_percent(old, new, expected_diff, expected_percent):
    diff, percent = stock_analysis.populate_vars(old, new)

    assert diff == pytest.approx(expected_diff)
    assert percent == pytest.approx(expected_percent)


def test_populate_vars_returns_zero_percent_for_numpy_zero_base():
    """A zero base pulled from a DataFrame must yield 0, not inf.

    Every real caller in cash_position passes numpy scalars sliced out of a DataFrame, and
    numpy division by zero returns inf instead of raising, so the ZeroDivisionError guard
    never fires on the production data path.
    """
    frame = pd.DataFrame({"value": [0.0, 5.0]}, index=_annual_index(2))
    old = frame["value"].iloc[0]
    new = frame["value"].iloc[1]
    assert isinstance(old, np.floating), "fixture must reproduce the numpy scalar callers pass"

    diff, percent = stock_analysis.populate_vars(old, new)

    assert diff == pytest.approx(5.0)
    assert percent == 0


# --------------------------------------------------------------------------------------
# predict_low
# --------------------------------------------------------------------------------------
@pytest.mark.parametrize(
    "current_price, expected",
    [
        (40.0, "BUY"),
        (59.99, "BUY"),
        (60.0, "Maybe"),  # exact lower boundary falls in the middle third
        (70.0, "Maybe"),
        (80.0, "Maybe"),  # exact upper boundary falls in the middle third
        (80.01, "SELL"),
        (100.0, "SELL"),
    ],
)
def test_predict_low_zones_price_into_thirds(current_price, expected):
    msg = stock_analysis.predict_low(100.0, 40.0, current_price)

    assert f"**{expected}** range" in msg


def test_predict_low_splits_range_into_equal_thirds():
    msg = stock_analysis.predict_low(100.0, 40.0, 70.0)

    assert "Lower 1/3 = 40.00 to 60.00" in msg
    assert "Middle 1/3 = 60.00 to 80.00" in msg
    assert "Upper 1/3 = 80.00 to 100.00" in msg


def test_predict_low_rejects_inverted_range():
    with pytest.raises(AssertionError):
        stock_analysis.predict_low(40.0, 100.0, 70.0)


# --------------------------------------------------------------------------------------
# _zone_analysis
# --------------------------------------------------------------------------------------
def test_zone_analysis_returns_upside_downside_ratio():
    fragment, ratio = stock_analysis._zone_analysis(100.0, 40.0, 60.0)

    assert fragment.startswith("```Lower")
    assert ratio == pytest.approx((100.0 - 60.0) / (60.0 - 40.0))


def test_zone_analysis_survives_price_equal_to_projected_low():
    """A projected low equal to the present price must not kill the whole report.

    The ratio denominator goes to zero; without a guard the ZeroDivisionError escapes
    risk_reward and no report is sent at all.
    """
    fragment, ratio = stock_analysis._zone_analysis(100.0, 60.0, 60.0)

    assert fragment == "```NaN```"
    assert ratio == 0


# --------------------------------------------------------------------------------------
# earnings_growth
# --------------------------------------------------------------------------------------
def _cash_flow_fixture(net_income):
    """Build the {'annualReports': DataFrame} contract earnings_growth consumes."""
    return {"annualReports": pd.DataFrame({"netIncome": net_income}, index=_annual_index(len(net_income)))}


def test_earnings_growth_computes_year_over_year_change():
    cash_flow = _cash_flow_fixture([100.0, 150.0, -50.0, 200.0])
    years = [stamp.year for stamp in cash_flow["annualReports"].index]

    msg = stock_analysis.earnings_growth(cash_flow)

    first = _row(msg, str(years[0]))
    assert _money(first[1]) == pytest.approx(100.0)

    second = _row(msg, str(years[1]))
    assert _money(second[2]) == pytest.approx(50.0)
    assert _pct(second[3]) == pytest.approx(0.5)

    third = _row(msg, str(years[2]))
    assert _money(third[2]) == pytest.approx(-200.0)
    assert _pct(third[3]) == pytest.approx(-200.0 / 150.0, rel=1e-3)


def test_earnings_growth_reports_positive_swing_out_of_a_loss():
    """abs() in the denominator is deliberate: a loss turning into a profit is growth."""
    cash_flow = _cash_flow_fixture([100.0, -50.0, 200.0])
    years = [stamp.year for stamp in cash_flow["annualReports"].index]

    msg = stock_analysis.earnings_growth(cash_flow)

    recovery = _row(msg, str(years[2]))
    assert _money(recovery[2]) == pytest.approx(250.0)
    assert _pct(recovery[3]) == pytest.approx(5.0)


# --------------------------------------------------------------------------------------
# past_sales_records
# --------------------------------------------------------------------------------------
def test_past_sales_records_compounds_growth_over_elapsed_periods():
    """Five annual observations span four growth periods, so the exponent is 1/4.

    Using 1/YRS_LOOKBACK understates the rate: doubling revenue across those five rows is
    18.92% a year, not the 14.87% a fifth-root produces.
    """
    revenue = pd.DataFrame({"totalRevenue": [100.0, 120.0, 150.0, 180.0, 200.0]}, index=_annual_index(5))

    msg = stock_analysis.past_sales_records(revenue)

    assert _pct(_field(msg, "Compound Annual Sales Growth Rate")) == pytest.approx(2 ** (1 / 4) - 1, abs=1e-4)


def test_past_sales_records_averages_the_outer_year_pairs():
    revenue = pd.DataFrame({"totalRevenue": [100.0, 120.0, 150.0, 180.0, 200.0]}, index=_annual_index(5))

    msg = stock_analysis.past_sales_records(revenue)

    # (200 + 180)/2 against (100 + 120)/2
    assert _pct(_field(msg, "% increase in sales")) == pytest.approx((190.0 - 110.0) / 110.0, abs=1e-4)
    assert _money(_field(msg, "Sales for most recent year")) == pytest.approx(200.0)


# --------------------------------------------------------------------------------------
# past_eps
# --------------------------------------------------------------------------------------
def test_past_eps_compounds_growth_over_elapsed_periods():
    """Same off-by-one as past_sales_records: 1.00 -> 3.00 over four periods is 31.61%/yr."""
    earnings = pd.DataFrame({"reportedEPS": [1.00, 1.50, 2.00, 2.50, 3.00]}, index=_annual_index(5))

    msg = stock_analysis.past_eps(earnings)

    assert _pct(_field(msg, "Compound Annual rate of EPS")) == pytest.approx(3 ** (1 / 4) - 1, abs=1e-4)


def test_past_eps_averages_the_outer_year_pairs():
    earnings = pd.DataFrame({"reportedEPS": [1.00, 1.50, 2.00, 2.50, 3.00]}, index=_annual_index(5))

    msg = stock_analysis.past_eps(earnings)

    # (3.00 + 2.50)/2 against (1.50 + 1.00)/2
    assert _pct(_field(msg, "% increase in earnings")) == pytest.approx((2.75 - 1.25) / 1.25, abs=1e-4)


# --------------------------------------------------------------------------------------
# _ttm_eps
# --------------------------------------------------------------------------------------
def _quarterly_eps_fixture(values):
    """Build the quarterly earnings frame contract, newest row last."""
    now = datetime.datetime.now()
    newest_first = [now - relativedelta(months=3 * (len(values) - 1 - offset)) for offset in range(len(values))]
    return pd.DataFrame({"reportedEPS": values}, index=pd.to_datetime(newest_first))


def test_ttm_eps_sums_the_last_four_quarters():
    """A P/E built off an annual price needs an annual earnings denominator."""
    quarterly = _quarterly_eps_fixture([0.10, 0.50, 0.60, 0.70, 0.80, 0.90])

    assert stock_analysis._ttm_eps(quarterly) == pytest.approx(0.60 + 0.70 + 0.80 + 0.90)


# --------------------------------------------------------------------------------------
# revenue_growth
# --------------------------------------------------------------------------------------
def _revenue_growth_args(revenue, close, dividend_payout, shares, current_eps):
    """Build the five positional arguments revenue_growth consumes."""
    index = _annual_index(len(revenue))
    return {
        "daily_prices": pd.DataFrame({"close": close}, index=_annual_index(len(close))),
        "cash_flow": {"annualReports": pd.DataFrame({"dividendPayout": dividend_payout}, index=index)},
        "income_statement": {"annualReports": pd.DataFrame({"totalRevenue": revenue}, index=index)},
        "current_eps": current_eps,
        "current_shares_outstanding": shares,
    }


def test_revenue_growth_measures_growth_against_the_prior_year():
    """Year-over-year growth divides the change by the *previous* year, not the current one.

    Revenue rising 100 -> 120 is 20% growth. Dividing by the current year reports 16.7%,
    understating every year in the table and the average beneath it.
    """
    args = _revenue_growth_args(
        revenue=[100.0, 120.0, 150.0, 180.0, 200.0],
        close=[10.0, 20.0, 30.0, 40.0, 50.0],
        dividend_payout=[0.0, 0.0, 0.0, 0.0, 100.0],
        shares=200,
        current_eps=2.0,
    )

    msg = stock_analysis.revenue_growth(**args)

    expected = np.mean([20.0 / 100.0, 30.0 / 120.0, 30.0 / 150.0, 20.0 / 180.0])
    assert _pct(_labelled(msg, "Average Growth")) == pytest.approx(expected, abs=1e-4)


def test_revenue_growth_divides_price_by_the_supplied_eps():
    args = _revenue_growth_args(
        revenue=[100.0, 120.0, 150.0, 180.0, 200.0],
        close=[10.0, 20.0, 30.0, 40.0, 50.0],
        dividend_payout=[0.0, 0.0, 0.0, 0.0, 100.0],
        shares=200,
        current_eps=2.0,
    )

    msg = stock_analysis.revenue_growth(**args)

    assert float(_labelled(msg, "Current P/E")) == pytest.approx(50.0 / 2.0)


# --------------------------------------------------------------------------------------
# run() wiring
# --------------------------------------------------------------------------------------
def _run_with_mocked_sections(earnings, **section_mocks):
    """Drive run() with every collaborator mocked, returning the section mocks used.

    Mirrors the scaffolding in test_stock_analysis.test_run_calls_risk_reward_with_matching_signature.
    """
    message = MagicMock()
    message.channel.send = AsyncMock()

    yf_mock = MagicMock()
    for getter in (
        "get_yfinance_income_statement",
        "get_yfinance_balance_sheet",
        "get_yfinance_cash_flow",
        "get_monthly_yfinance_company_prices",
        "get_daily_yfinance_company_prices",
    ):
        setattr(yf_mock, getter, MagicMock(return_value=MagicMock()))
    yf_mock.get_yfinance_earnings = MagicMock(return_value=earnings)

    utils_mock = MagicMock()
    utils_mock.send_message_in_chunks = AsyncMock()

    defaults = {
        "past_sales_records": MagicMock(),
        "past_eps": MagicMock(),
        "record_of_stock": MagicMock(return_value=(["msg"], 5.0)),
        "trend": MagicMock(return_value=("trend", [])),
        "cash_position": MagicMock(),
        "revenue_growth": MagicMock(),
        "earnings_growth": MagicMock(),
        "risk_reward": MagicMock(return_value=("risk_reward", [])),
    }
    defaults.update(section_mocks)

    with patch.object(stock_analysis, "yf_api", yf_mock), patch.object(
        stock_analysis, "utils", utils_mock
    ), patch.multiple(stock_analysis, **defaults):
        asyncio.run(stock_analysis.run(message, "IBM"))
    return defaults


def test_run_passes_trailing_twelve_month_eps_to_revenue_growth():
    """run() must hand revenue_growth an annual EPS, not a single quarter's.

    revenue_growth divides an annual share price by whatever EPS it is given, so passing one
    quarter overstates the reported P/E roughly fourfold.
    """
    quarterly = _quarterly_eps_fixture([0.50, 0.60, 0.70, 0.80, 0.90])
    earnings = {
        "annualEarnings": pd.DataFrame({"reportedEPS": [2.0, 3.0]}, index=_annual_index(2)),
        "quarterlyEarnings": quarterly,
    }
    revenue_growth_mock = MagicMock()

    _run_with_mocked_sections(earnings, revenue_growth=revenue_growth_mock)

    revenue_growth_mock.assert_called_once()
    passed_eps = revenue_growth_mock.call_args.args[3]
    assert passed_eps == pytest.approx(0.60 + 0.70 + 0.80 + 0.90)


# --------------------------------------------------------------------------------------
# record_of_stock
# --------------------------------------------------------------------------------------
def _record_of_stock_args():
    """Build a five-year fixture with flat annual EPS so the P/E columns are hand-checkable.

    Yearly highs run 100..140 and lows 50..90, annual EPS is a flat 4.00 made up of four
    1.00 quarters, and the present price is 150.
    """
    annual = _annual_index(5)
    years = [stamp.year for stamp in annual]

    dates = []
    rows = []
    for position, year in enumerate(years):
        for month in range(1, 13):
            dates.append(datetime.datetime(year, month, 1))
            rows.append({"high": 100.0 + 10 * position, "low": 50.0 + 10 * position, "dividend_amt": 0.25})
    monthly_prices = pd.DataFrame(rows, index=pd.to_datetime(dates))

    return {
        "eps": {
            "annualEarnings": pd.DataFrame({"reportedEPS": [4.0] * 5}, index=annual),
            "quarterlyEarnings": _quarterly_eps_fixture([1.0] * 8),
        },
        "income_statement": {
            "annualReports": pd.DataFrame({"totalRevenue": [100.0, 120.0, 150.0, 180.0, 200.0]}, index=annual)
        },
        "daily_prices": pd.DataFrame({"close": [140.0, 145.0, 150.0]}, index=_quarterly_eps_fixture([0, 0, 0]).index),
        "monthly_prices": monthly_prices,
    }


def test_record_of_stock_compares_present_price_to_the_oldest_year_high():
    """The 'x years ago' comparison must use the oldest year's high, not the newest.

    Reading high_prices[-1] compares the present price against this year's own high, which
    is near zero by construction and says nothing about five-year appreciation.
    """
    msg, _ = stock_analysis.record_of_stock(**_record_of_stock_args())

    cells = _row("\n".join(msg), f"Present Price % difference then high price {stock_analysis.YRS_LOOKBACK} years ago")
    # present price 150 against the oldest yearly high of 100
    assert _pct(cells[1]) == pytest.approx((150.0 - 100.0) / 100.0, abs=1e-4)


def test_record_of_stock_current_pe_uses_annual_earnings():
    """Current P/E must sit on the same annual basis as the Average P/E printed beside it.

    Dividing the price by a single 1.00 quarter gives 150; the four quarters that make up
    the 4.00 annual EPS give 37.5, comparable to the 23.75 average.
    """
    msg, _ = stock_analysis.record_of_stock(**_record_of_stock_args())
    joined = "\n".join(msg)

    average = float(re.search(r"\*Average PE Ratio\*:\s*([\d.,]+)", joined).group(1))
    current = float(re.search(r"\*Current PE Ratio\*\s*([\d.,]+)", joined).group(1))

    assert average == pytest.approx(23.75)
    assert current == pytest.approx(150.0 / 4.0)


def test_record_of_stock_returns_high_yield_in_percent_units():
    """risk_reward divides this by 100, so the contract is percent, not a fraction."""
    _, high_yield = stock_analysis.record_of_stock(**_record_of_stock_args())

    # 12 monthly dividends of 0.25 = 3.00 against the oldest year's low of 50
    assert high_yield == pytest.approx(3.0 / 50.0 * 100)


# --------------------------------------------------------------------------------------
# cash_position
# --------------------------------------------------------------------------------------
def _balance_sheet_fixture():
    """Build a three-year balance sheet so the oldest row differs from the prior year."""
    index = _annual_index(3)
    columns = {
        "cashAndCashEquivalentsAtCarryingValue": [100.0, 200.0, 300.0],
        "shortTermInvestments": [10.0, 20.0, 30.0],
        "longTermDebt": [50.0, 60.0, 70.0],
        "commonStockSharesOutstanding": [1000.0, 1000.0, 1000.0],
        "currentNetReceivables": [40.0, 50.0, 60.0],
        "inventory": [5.0, 6.0, 7.0],
        "otherCurrentAssets": [1.0, 2.0, 3.0],
        "totalCurrentAssets": [146.0, 258.0, 370.0],
        "currentAccountsPayable": [500.0, 700.0, 900.0],
        "shortTermDebt": [11.0, 12.0, 13.0],
        "otherCurrentLiabilities": [2.0, 3.0, 4.0],
        "totalCurrentLiabilities": [513.0, 715.0, 917.0],
    }
    return {"annualReports": pd.DataFrame(columns, index=index)}


def test_cash_position_compares_payables_against_the_prior_year():
    """Payables must compare the two most recent years, like every other row in the table.

    Indexing [0] instead of [-2] reaches back to the oldest report, so the Payables row is
    the only one in the table measured over a different span than its own column headers.
    """
    msg = stock_analysis.cash_position(_balance_sheet_fixture())

    cells = _row("\n".join(msg), "Payables")
    assert _money(cells[2]) == pytest.approx(700.0)  # prior year, not the oldest (500)
    assert _pct(cells[4]) == pytest.approx((900.0 - 700.0) / 700.0, abs=1e-4)


def test_cash_position_compares_short_term_debt_against_the_prior_year():
    """Sibling row that already used [-2]; pins the convention the Payables fix restores."""
    msg = stock_analysis.cash_position(_balance_sheet_fixture())

    cells = _row("\n".join(msg), "Short Term Debt")
    assert _money(cells[2]) == pytest.approx(12.0)
    assert _pct(cells[4]) == pytest.approx((13.0 - 12.0) / 12.0, abs=1e-4)


# --------------------------------------------------------------------------------------
# risk_reward
# --------------------------------------------------------------------------------------
def _risk_reward_args(quarterly_values=None, annual_eps=4.0):
    """Build a risk_reward fixture with hand-computable P/E inputs.

    Yearly highs run 100..140 against a flat annual EPS, so pe_high is evenly spaced and its
    mean is exact. Defaults give a flat 1.00/quarter EPS and a pe_high mean of 30.0.
    """
    if quarterly_values is None:
        quarterly_values = [1.0] * 8
    annual = _annual_index(5)
    years = [stamp.year for stamp in annual]

    dates = []
    rows = []
    for position, year in enumerate(years):
        for month in range(1, 13):
            dates.append(datetime.datetime(year, month, 1))
            rows.append({"high": 100.0 + 10 * position, "low": 50.0 + 10 * position, "dividend_amt": 0.25})
    monthly_prices = pd.DataFrame(rows, index=pd.to_datetime(dates))

    daily_index = pd.to_datetime(
        [datetime.datetime.now() - relativedelta(months=offset) for offset in range(23, -1, -1)]
    )
    daily_prices = pd.DataFrame(
        {
            "close": [90.0] * 24,
            "high": [100.0] * 24,
            "low": [60.0] * 24,
        },
        index=daily_index,
    )

    quarterly = _quarterly_eps_fixture(quarterly_values)
    return {
        "daily_prices": daily_prices,
        "eps": {
            "annualEarnings": pd.DataFrame({"reportedEPS": [annual_eps] * 5}, index=annual),
            "quarterlyEarnings": quarterly,
        },
        "monthly_company_prices": monthly_prices,
        "income_statement": {
            "quarterlyReports": pd.DataFrame({"totalRevenue": [100.0] * len(quarterly)}, index=quarterly.index)
        },
        "high_yield": 6.0,
    }


def test_risk_reward_forecasts_high_on_an_annual_earnings_basis(tmp_path, monkeypatch):
    """The 5-year price target must multiply an annual P/E by an annual EPS projection.

    pe_high is built from annual EPS, but est_high_eps is fitted on quarterly EPS. Multiplying
    the two mixes bases and understates the headline target roughly fourfold: 30.0 x 1.00
    instead of 30.0 x 4.00.
    """
    monkeypatch.setenv("STOCKYARD_DATA_DIR", str(tmp_path))

    msg, files = stock_analysis.risk_reward(**_risk_reward_args())

    forecast = float(re.search(r"Linear Regression of Highs:\s*([\d.]+)", msg).group(1))
    assert forecast == pytest.approx(30.0 * 4.0, rel=1e-6)
    assert len(files) == 4


def test_risk_reward_price_target_matches_the_forecast_high(tmp_path, monkeypatch):
    """The PRICE TARGET line and its appreciation figure derive from the same forecast."""
    monkeypatch.setenv("STOCKYARD_DATA_DIR", str(tmp_path))

    msg, _ = stock_analysis.risk_reward(**_risk_reward_args())

    target = float(re.search(r"\$([\d,.]+) 5yr predicted stock price", msg).group(1).replace(",", ""))
    appreciation = float(re.search(r"drives ([\d,.-]+)% appreciation", msg).group(1).replace(",", ""))

    assert target == pytest.approx(120.0, abs=0.01)
    # present price is a flat 90.0 across the daily fixture
    assert appreciation == pytest.approx((120.0 / 90.0) * 100 - 100, abs=0.01)


# Four quarters of a strongly seasonal but perfectly stable business: every rolling
# four-quarter window sums to exactly 10.00, so real annual earnings never change.
SEASONAL_QUARTERS = [4.0, 1.5, 2.0, 2.5, 4.0, 1.5, 2.0]


def test_risk_reward_forecast_ignores_quarterly_seasonality(tmp_path, monkeypatch):
    """Seasonal swings must not masquerade as an earnings trend.

    SEASONAL_QUARTERS has flat trailing-twelve-month earnings of exactly 10.00, but the
    window ends on a weak quarter. Fitting the raw quarterly series reads that as decline
    and drives the projection negative; fitting trailing twelve months sees the truth.
    """
    monkeypatch.setenv("STOCKYARD_DATA_DIR", str(tmp_path))
    args = _risk_reward_args(quarterly_values=SEASONAL_QUARTERS, annual_eps=10.0)

    msg, _ = stock_analysis.risk_reward(**args)

    # highs 100..140 over a flat 10.00 annual EPS give pe_high 10..14, mean 12.0
    forecast = float(re.search(r"Linear Regression of Highs:\s*(-?[\d.]+)", msg).group(1))
    assert forecast == pytest.approx(12.0 * 10.0, rel=1e-6)


def test_risk_reward_declines_to_report_a_target_when_earnings_trend_negative(tmp_path, monkeypatch):
    """A collapsing earnings trend must not print a negative dollar price target.

    Extrapolating any declining series five years out eventually crosses zero. A negative
    forecast is not a price, so the report should say so rather than quote one.
    """
    monkeypatch.setenv("STOCKYARD_DATA_DIR", str(tmp_path))
    collapsing = [4.0, 3.0, 2.0, 1.0, 0.5, 0.25, 0.1]
    args = _risk_reward_args(quarterly_values=collapsing, annual_eps=10.0)

    msg, files = stock_analysis.risk_reward(**args)

    assert "does not support" in msg
    assert "PRICE TARGET" not in msg
    assert re.search(r"-[\d,.]+ 5yr predicted stock price", msg) is None
    # the low-price analysis and its charts remain useful and are still produced
    assert "LOW PRICE - NEXT 5 YEARS" in msg
    assert len(files) == 4


def test_risk_reward_handles_too_little_history_for_a_trailing_year(tmp_path, monkeypatch):
    """Fewer than five quarters yields under two TTM points, which cannot define a trend.

    Fitting trailing twelve months needs four quarters per point, so a young listing that the
    old raw-quarterly fit would have accepted must degrade gracefully rather than crash.
    """
    monkeypatch.setenv("STOCKYARD_DATA_DIR", str(tmp_path))
    args = _risk_reward_args(quarterly_values=[2.5] * 4, annual_eps=10.0)

    msg, files = stock_analysis.risk_reward(**args)

    assert "does not support" in msg
    assert "PRICE TARGET" not in msg
    # no EPS chart without a fit, but the three price charts are still produced
    assert len(files) == 3
