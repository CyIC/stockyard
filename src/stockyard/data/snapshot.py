# -*- coding: utf-8 -*-
"""StockData: everything one report needs, fetched once (design §5.1)."""
from collections.abc import Callable
from dataclasses import dataclass
from functools import partial

import pandas as pd
import yfinance as yf
from yfinance.exceptions import YFRateLimitError

from stockyard.data.cache import Cache, RecordingTicker, ReplayTicker
from stockyard.data.errors import DataUnavailable, RateLimited, UpstreamError
from stockyard.data.tickers import validate_ticker
from stockyard.data.yfinance_source import (
    BALANCE_FIELD_MAP,
    CASHFLOW_FIELD_MAP,
    INCOME_FIELD_MAP,
    RateLimitWatch,
    _remap_columns,
    rate_limit_watch,
)

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


def fetch_stock_data(
    raw_ticker: str,
    *,
    ticker_factory: Callable | None = None,
    cache: Cache | None = None,
    rate_limits: RateLimitWatch | None = None,
) -> StockData:
    """Validate the ticker and fetch everything a report needs in one pass.

    :param raw_ticker: symbol as typed by a user or agent
    :param ticker_factory: builds the yfinance Ticker (injectable for tests); default: live yfinance,
        fetching through the process-wide rate-limit watch
    :param cache: same-day cache; None disables caching (``--no-cache``)
    :param rate_limits: notices 429s yfinance swallows (injectable for tests)
    :raises InvalidTicker: before any network access, if the symbol is not plausible
    :raises RateLimited: if Yahoo rate limited any request, raised or swallowed; nothing is cached
    :raises UpstreamError: if the data source raises while fetching
    :raises DataUnavailable: if there are neither statements nor prices for the ticker
    """
    ticker = validate_ticker(raw_ticker)
    if ticker_factory is None:
        rate_limits = rate_limits or rate_limit_watch()
        ticker_factory = partial(yf.Ticker, session=rate_limits)
    cached = cache.load(ticker) if cache is not None else None
    if cached is not None:
        stock = ReplayTicker(cached)
    else:
        stock = ticker_factory(ticker)
        if cache is not None:
            stock = RecordingTicker(stock)
    data = _fetch_watching_upstream(ticker, stock, rate_limits)
    statements = (
        data.income_annual,
        data.income_quarterly,
        data.balance_annual,
        data.balance_quarterly,
        data.cashflow_annual,
        data.cashflow_quarterly,
    )
    if data.daily_prices.empty and all(frame.empty for frame in statements):
        raise DataUnavailable(f"no statements or prices for {ticker}")
    if cache is not None and cached is None:
        cache.save(ticker, stock.to_dict())
    return data


def _fetch_watching_upstream(ticker: str, stock, rate_limits: RateLimitWatch | None) -> StockData:
    """Fetch; any yfinance failure becomes UpstreamError, any rate limit (raised or swallowed) RateLimited."""
    rate_limited = f"fetching {ticker}: Yahoo Finance rate limited the request; try again later"
    if rate_limits is not None:
        rate_limits.begin()
    try:
        data = _fetch(ticker, stock)
    except YFRateLimitError as exc:
        raise RateLimited(rate_limited) from exc
    except Exception as exc:  # pylint: disable=broad-exception-caught  # any yfinance failure is upstream
        raise UpstreamError(f"fetching {ticker} failed: {exc}") from exc
    if rate_limits is not None and rate_limits.hit:  # yfinance swallowed it: some data is missing
        raise RateLimited(rate_limited)
    return data


def _fetch(ticker: str, stock) -> StockData:
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
