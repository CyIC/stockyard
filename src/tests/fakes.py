# -*- coding: utf-8 -*-
"""Test doubles for yfinance."""
import pandas as pd


def statement(rows: dict, period_ends: list) -> pd.DataFrame:
    """Build a yfinance-shaped statement: rows are line items, columns are period-end Timestamps (newest first)."""
    columns = [pd.Timestamp(d) for d in period_ends]
    return pd.DataFrame(rows, index=columns).T


class FakeTicker:  # pylint: disable=too-many-instance-attributes
    """Stands in for yfinance.Ticker; records the calls made to it."""

    def __init__(
        self,
        symbol,
        *,
        income=None,
        quarterly_income=None,
        balance=None,
        quarterly_balance=None,
        cashflow=None,
        quarterly_cashflow=None,
        earnings_dates=None,
        history=None,
    ):
        """Each statement is a yfinance-shaped frame; omitted ones are empty."""
        self.ticker = symbol
        self.financials = income if income is not None else pd.DataFrame()
        self.quarterly_financials = quarterly_income if quarterly_income is not None else pd.DataFrame()
        self.balance_sheet = balance if balance is not None else pd.DataFrame()
        self.quarterly_balance_sheet = quarterly_balance if quarterly_balance is not None else pd.DataFrame()
        self.cashflow = cashflow if cashflow is not None else pd.DataFrame()
        self.quarterly_cashflow = quarterly_cashflow if quarterly_cashflow is not None else pd.DataFrame()
        self._earnings_dates = earnings_dates if earnings_dates is not None else pd.DataFrame()
        self._history = history if history is not None else pd.DataFrame()
        self.calls = []

    def get_earnings_dates(self, limit=12, offset=0):
        self.calls.append(("get_earnings_dates", {"limit": limit, "offset": offset}))
        return self._earnings_dates

    def history(self, **kwargs):
        self.calls.append(("history", kwargs))
        return self._history
