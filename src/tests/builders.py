# -*- coding: utf-8 -*-
"""Build small, exact StockData values for unit tests."""
import pandas as pd

from stockyard.data.snapshot import StockData


def _frame(rows: dict, columns: list[str]) -> pd.DataFrame:
    frame = pd.DataFrame.from_dict(rows, orient="index", columns=columns)
    frame.index = pd.to_datetime(frame.index)
    return frame.sort_index()


def stock_data(annual=None, eps=None, prices=None, ticker="TEST") -> StockData:
    """Build StockData.

    :param annual: {period_end: (revenue, net_income)}
    :param eps: [(announced, reported_eps)]
    :param prices: (first_date, last_date) for a flat daily price series, or None
    """
    income = _frame(annual or {}, ["totalRevenue", "netIncome"]) if annual else pd.DataFrame()
    earnings = (
        _frame({announced: (value,) for announced, value in eps}, ["reported_eps"])
        if eps
        else pd.DataFrame(columns=["reported_eps"])
    )
    if prices:
        index = pd.bdate_range(prices[0], prices[1])
        daily = pd.DataFrame(
            {"open": 10.0, "high": 11.0, "low": 9.0, "close": 10.0, "volume": 100, "dividend": 0.0}, index=index
        )
    else:
        daily = pd.DataFrame(columns=["open", "high", "low", "close", "volume", "dividend"])
    empty = pd.DataFrame()
    return StockData(
        ticker=ticker,
        income_annual=income,
        income_quarterly=empty,
        balance_annual=empty,
        balance_quarterly=empty,
        cashflow_annual=empty,
        cashflow_quarterly=empty,
        earnings=earnings,
        daily_prices=daily,
    )


def quarterly_eps(quarter_ends: list[str], value: float = 1.0, lag_days: int = 25) -> list:
    """One announcement ``lag_days`` after each quarter-end."""
    return [((pd.Timestamp(end) + pd.DateOffset(days=lag_days)).strftime("%Y-%m-%d"), value) for end in quarter_ends]
