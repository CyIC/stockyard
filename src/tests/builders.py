# -*- coding: utf-8 -*-
"""Build small, exact StockData values for unit tests."""
import pandas as pd

from stockyard.data.snapshot import StockData


def _frame(rows: dict, columns: list[str]) -> pd.DataFrame:
    frame = pd.DataFrame.from_dict(rows, orient="index", columns=columns)
    frame.index = pd.to_datetime(frame.index)
    return frame.sort_index()


def _sheet(rows) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    frame = pd.DataFrame.from_dict(rows, orient="index", dtype=float)
    frame.index = pd.to_datetime(frame.index)
    return frame.sort_index()


def stock_data(  # pylint: disable=too-many-arguments
    annual=None,
    eps=None,
    prices=None,
    ticker="TEST",
    daily=None,
    balance=None,
    balance_quarterly=None,
    quarterly=None,
) -> StockData:
    """Build StockData.

    :param annual: {period_end: (revenue, net_income)}
    :param eps: [(announced, reported_eps)]
    :param prices: (first_date, last_date) for a flat daily price series, or None
    :param daily: an explicit daily price frame (overrides ``prices``)
    :param balance: {period_end: {canonical_column: value}} annual balance sheets
    :param balance_quarterly: the same for quarterly balance sheets
    :param quarterly: {quarter_end: (revenue, net_income)} quarterly income statements
    """
    income = _frame(annual or {}, ["totalRevenue", "netIncome"]) if annual else pd.DataFrame()
    earnings = (
        _frame({announced: (value,) for announced, value in eps}, ["reported_eps"])
        if eps
        else pd.DataFrame(columns=["reported_eps"])
    )
    if daily is None and prices:
        daily = pd.DataFrame(
            {"open": 10.0, "high": 11.0, "low": 9.0, "close": 10.0, "volume": 100, "dividend": 0.0},
            index=pd.bdate_range(prices[0], prices[1]),
        )
    elif daily is None:
        daily = pd.DataFrame(columns=["open", "high", "low", "close", "volume", "dividend"])
    empty = pd.DataFrame()
    return StockData(
        ticker=ticker,
        income_annual=income,
        income_quarterly=_frame(quarterly, ["totalRevenue", "netIncome"]) if quarterly else empty,
        balance_annual=_sheet(balance),
        balance_quarterly=_sheet(balance_quarterly),
        cashflow_annual=empty,
        cashflow_quarterly=empty,
        earnings=earnings,
        daily_prices=daily,
    )


def quarterly_eps(quarter_ends: list[str], value: float = 1.0, lag_days: int = 25) -> list:
    """One announcement ``lag_days`` after each quarter-end."""
    return [((pd.Timestamp(end) + pd.DateOffset(days=lag_days)).strftime("%Y-%m-%d"), value) for end in quarter_ends]


def daily_bars(bars: dict, base_low: float = 9.0, base_high: float = 11.0) -> pd.DataFrame:
    """Flat business-day bars between the first and last given dates, overridden by ``bars``.

    :param bars: {date: {"high": .., "low": .., "dividend": ..}} for the days that matter
    """
    dates = sorted(pd.Timestamp(day) for day in bars)
    frame = pd.DataFrame(
        {"open": 10.0, "high": base_high, "low": base_low, "close": 10.0, "volume": 100, "dividend": 0.0},
        index=pd.bdate_range(dates[0], dates[-1]),
    )
    for day, values in bars.items():
        for column, value in values.items():
            frame.loc[pd.Timestamp(day), column] = value
    return frame.sort_index()
