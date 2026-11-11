# -*- coding: utf-8 -*-
"""StockData: everything one report needs, fetched once (design §5.1)."""
from collections.abc import Callable
from dataclasses import dataclass

import pandas as pd
import yfinance as yf

from stockyard.data.tickers import validate_ticker
from stockyard.data.yfinance_source import BALANCE_FIELD_MAP, CASHFLOW_FIELD_MAP, INCOME_FIELD_MAP, _remap_columns

MIN_EARNINGS_ROWS = 28
PRICE_COLUMNS = {
    "Open": "open",
    "High": "high",
    "Low": "low",
    "Close": "close",
    "Volume": "volume",
    "Dividends": "dividend",
}


@dataclass(frozen=True)
class StockData:  # pylint: disable=too-many-instance-attributes
    """Raw, normalised market data for one ticker. Every frame is indexed by tz-naive date, oldest first.

    Statements are keyed by their real period-end dates (no synthetic annual rows). ``earnings`` holds
    reported EPS by announcement date. ``daily_prices`` are split-adjusted, not dividend-adjusted, and
    carry per-share dividends.
    """

    ticker: str
    income_annual: pd.DataFrame
    income_quarterly: pd.DataFrame
    balance_annual: pd.DataFrame
    balance_quarterly: pd.DataFrame
    cashflow_annual: pd.DataFrame
    cashflow_quarterly: pd.DataFrame
    earnings: pd.DataFrame
    daily_prices: pd.DataFrame


def _statement(frame, field_map) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame()
    return _remap_columns(frame.T, field_map)


def _earnings(stock, limit: int) -> pd.DataFrame:
    raw = stock.get_earnings_dates(limit=limit)
    if raw is None or raw.empty:
        return pd.DataFrame(columns=["reported_eps"])
    reported = raw[raw["Reported EPS"].notna()]
    index = reported.index.tz_localize(None) if reported.index.tz is not None else reported.index
    earnings = pd.DataFrame({"reported_eps": reported["Reported EPS"].astype(float).to_numpy()}, index=index)
    earnings.index.name = "announced"
    return earnings.sort_index()


def _prices(stock, income_annual: pd.DataFrame) -> pd.DataFrame:
    if income_annual.empty:
        window = {"period": "max"}
    else:
        oldest_start = income_annual.index.min() - pd.DateOffset(years=1) + pd.DateOffset(days=1)
        window = {"start": oldest_start.strftime("%Y-%m-%d")}
    raw = stock.history(**window, interval="1d", auto_adjust=False)
    if raw is None or raw.empty:
        return pd.DataFrame(columns=list(PRICE_COLUMNS.values()))
    prices = raw.rename(columns=PRICE_COLUMNS)[list(PRICE_COLUMNS.values())]
    if prices.index.tz is not None:
        prices.index = prices.index.tz_localize(None)
    prices.index.name = "date"
    return prices.sort_index()


def fetch_stock_data(raw_ticker: str, *, ticker_factory: Callable = yf.Ticker) -> StockData:
    """Validate the ticker and fetch everything a report needs in one pass.

    :param raw_ticker: symbol as typed by a user or agent
    :param ticker_factory: builds the yfinance Ticker (injectable for tests)
    :raises InvalidTicker: before any network access, if the symbol is not plausible
    """
    ticker = validate_ticker(raw_ticker)
    stock = ticker_factory(ticker)
    income_annual = _statement(stock.financials, INCOME_FIELD_MAP)
    return StockData(
        ticker=ticker,
        income_annual=income_annual,
        income_quarterly=_statement(stock.quarterly_financials, INCOME_FIELD_MAP),
        balance_annual=_statement(stock.balance_sheet, BALANCE_FIELD_MAP),
        balance_quarterly=_statement(stock.quarterly_balance_sheet, BALANCE_FIELD_MAP),
        cashflow_annual=_statement(stock.cashflow, CASHFLOW_FIELD_MAP),
        cashflow_quarterly=_statement(stock.quarterly_cashflow, CASHFLOW_FIELD_MAP),
        earnings=_earnings(stock, max(MIN_EARNINGS_ROWS, 4 * len(income_annual) + 12)),
        daily_prices=_prices(stock, income_annual),
    )
