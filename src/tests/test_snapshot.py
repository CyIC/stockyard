# -*- coding: utf-8 -*-
"""Tests for StockData and fetch_stock_data (design §5.1)."""
import dataclasses

import pandas as pd
import pytest

from stockyard.data.errors import DataUnavailable, UpstreamError
from stockyard.data.snapshot import StockData, fetch_stock_data
from stockyard.data.tickers import InvalidTicker
from tests.fakes import FakeTicker, statement

ANNUAL = ["2025-12-31", "2024-12-31", "2023-12-31", "2022-12-31", "2021-12-31"]
TZ = "America/New_York"


def _earnings_dates():
    index = pd.DatetimeIndex(
        [pd.Timestamp("2027-01-20", tz=TZ), pd.Timestamp("2026-10-20", tz=TZ), pd.Timestamp("2026-07-22", tz=TZ)],
        name="Earnings Date",
    )
    return pd.DataFrame(
        {"EPS Estimate": [2.1, 2.0, 1.9], "Reported EPS": [None, 2.05, 1.95], "Surprise(%)": [None, 2.5, 2.6]},
        index=index,
    )


def _history():
    index = pd.DatetimeIndex([pd.Timestamp("2026-11-10", tz=TZ), pd.Timestamp("2026-11-09", tz=TZ)], name="Date")
    return pd.DataFrame(
        {
            "Open": [10.0, 9.0],
            "High": [11.0, 10.0],
            "Low": [9.5, 8.5],
            "Close": [10.5, 9.5],
            "Adj Close": [10.4, 9.4],
            "Volume": [100, 200],
            "Dividends": [0.0, 0.25],
            "Stock Splits": [0.0, 0.0],
        },
        index=index,
    )


def _fake(**overrides):
    kwargs = {
        "income": statement({"Total Revenue": [5, 4, 3, 2, 1], "Net Income": [50, 40, 30, 20, 10]}, ANNUAL),
        "balance": statement({"Cash And Cash Equivalents": [9, 8, 7, 6, 5]}, ANNUAL),
        "cashflow": statement({"Cash Dividends Paid": [-1, -1, -1, -1, -1]}, ANNUAL),
        "earnings_dates": _earnings_dates(),
        "history": _history(),
    }
    kwargs.update(overrides)
    return FakeTicker("IBM", **kwargs)


def _fetch(fake=None):
    fake = fake or _fake()
    return fetch_stock_data("ibm", ticker_factory=lambda symbol: fake), fake


def test_ticker_is_validated_before_anything_is_fetched():
    def factory(symbol):
        raise AssertionError("must not fetch")

    with pytest.raises(InvalidTicker):
        fetch_stock_data("../etc", ticker_factory=factory)


def test_ticker_is_normalised():
    data, _ = _fetch()
    assert data.ticker == "IBM"


def test_statements_are_indexed_by_period_end_oldest_first_with_canonical_columns():
    data, _ = _fetch()
    assert list(data.income_annual.index) == [pd.Timestamp(d) for d in reversed(ANNUAL)]
    assert data.income_annual["revenue"].tolist() == [1, 2, 3, 4, 5]
    assert data.income_annual["net_income"].tolist() == [10, 20, 30, 40, 50]
    assert data.balance_annual["cash"].tolist() == [5, 6, 7, 8, 9]


def test_no_synthetic_annual_rows_are_built_from_quarters():
    """Design §5.2.7: annual frames hold only real annual period-ends."""
    quarters = statement(
        {"Total Revenue": [1.5, 1.4, 1.3, 1.2]}, ["2026-09-30", "2026-06-30", "2026-03-31", "2025-12-31"]
    )
    data, _ = _fetch(_fake(quarterly_income=quarters))
    assert data.income_annual.index.max() == pd.Timestamp("2025-12-31")
    assert len(data.income_quarterly) == 4


def test_earnings_depth_covers_the_oldest_fiscal_year():
    _, fake = _fetch()
    assert ("get_earnings_dates", {"limit": 4 * 5 + 12, "offset": 0}) in fake.calls


def test_earnings_depth_has_a_floor_of_28():
    _, fake = _fetch(_fake(income=statement({"Total Revenue": [5, 4]}, ANNUAL[:2])))
    assert ("get_earnings_dates", {"limit": 28, "offset": 0}) in fake.calls


def test_earnings_keep_only_reported_rows_indexed_by_naive_announcement_date():
    data, _ = _fetch()
    assert list(data.earnings.index) == [pd.Timestamp("2026-07-22"), pd.Timestamp("2026-10-20")]
    assert data.earnings["reported_eps"].tolist() == [1.95, 2.05]


def test_prices_start_with_the_oldest_fiscal_year_and_are_split_adjusted_only():
    """auto_adjust=False: SSG price history must not be lowered by later dividends."""
    _, fake = _fetch()
    calls = [kwargs for name, kwargs in fake.calls if name == "history"]
    assert calls == [{"start": "2021-01-01", "interval": "1d", "auto_adjust": False}]


def test_prices_have_naive_dates_oldest_first_and_per_share_dividends():
    data, _ = _fetch()
    prices = data.daily_prices
    assert list(prices.index) == [pd.Timestamp("2026-11-09"), pd.Timestamp("2026-11-10")]
    assert list(prices.columns) == ["open", "high", "low", "close", "volume", "dividend"]
    assert prices["close"].tolist() == [9.5, 10.5]
    assert prices["dividend"].tolist() == [0.25, 0.0]


def test_each_remote_call_is_made_once():
    _, fake = _fetch()
    assert [name for name, _ in fake.calls] == ["get_earnings_dates", "history"]


def test_stock_data_is_immutable():
    data, _ = _fetch()
    with pytest.raises(dataclasses.FrozenInstanceError):
        data.ticker = "MSFT"


def test_there_is_no_net_income_as_eps_fallback():
    """Design §5.1: yfinance 'Earnings' (net income) must never become reported EPS."""
    data, _ = _fetch(_fake(earnings_dates=pd.DataFrame()))
    assert data.earnings.empty
    assert isinstance(data, StockData)


def test_without_annual_statements_the_full_listing_history_is_requested():
    """A very new listing has no annual statement yet; its whole (short) price history is wanted."""
    _, fake = _fetch(_fake(income=pd.DataFrame()))
    calls = [kwargs for name, kwargs in fake.calls if name == "history"]
    assert calls == [{"period": "max", "interval": "1d", "auto_adjust": False}]


def test_no_statements_and_no_prices_is_data_unavailable():
    empty = FakeTicker("ZZZZ")
    with pytest.raises(DataUnavailable, match="ZZZZ"):
        fetch_stock_data("zzzz", ticker_factory=lambda symbol: empty)


def test_prices_without_statements_is_not_unavailable():
    """A listing too new for any annual statement still has a price history worth reporting."""
    data, _ = _fetch(_fake(income=pd.DataFrame(), balance=pd.DataFrame(), cashflow=pd.DataFrame()))
    assert not data.daily_prices.empty


class _BrokenHistory(FakeTicker):
    def history(self, **kwargs):
        raise ConnectionError("network down")


class _BrokenStatements(FakeTicker):
    @property
    def financials(self):
        raise RuntimeError("yahoo said no")

    @financials.setter
    def financials(self, value):
        pass


@pytest.mark.parametrize("broken", [_BrokenHistory, _BrokenStatements])
def test_errors_raised_by_yfinance_become_upstream_errors(broken):
    fake = broken("IBM", earnings_dates=_earnings_dates(), history=_history())
    with pytest.raises(UpstreamError, match="IBM") as caught:
        fetch_stock_data("IBM", ticker_factory=lambda symbol: fake)
    assert caught.value.__cause__ is not None


def test_error_types_are_distinguishable_from_each_other():
    assert not issubclass(DataUnavailable, UpstreamError)
    assert not issubclass(UpstreamError, DataUnavailable)
