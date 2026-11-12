# -*- coding: utf-8 -*-
"""yfinance statement labels mapped to the canonical column names the data layer uses."""
import numpy as np
import pandas as pd

# Map stockyard's column names to candidate yfinance row labels. Label availability varies by
# company, so each column lists fallbacks tried in order; missing labels become NaN columns so
# downstream access never raises KeyError.
INCOME_FIELD_MAP = {
    "revenue": ["Total Revenue"],
    "net_income": ["Net Income", "Net Income Common Stockholders"],
}

BALANCE_FIELD_MAP = {
    "cash": ["Cash And Cash Equivalents"],
    "short_term_investments": ["Other Short Term Investments", "Short Term Investments"],
    "long_term_debt": ["Long Term Debt"],
    "shares_outstanding": ["Ordinary Shares Number", "Share Issued"],
    "receivables": ["Receivables", "Accounts Receivable", "Net Receivables"],
    "inventory": ["Inventory"],
    "other_current_assets": ["Other Current Assets"],
    "current_assets": ["Current Assets", "Total Current Assets"],
    "payables": ["Accounts Payable", "Payables"],
    "short_term_debt": ["Current Debt", "Current Debt And Capital Lease Obligation"],
    "other_current_liabilities": ["Other Current Liabilities"],
    "current_liabilities": ["Current Liabilities", "Total Current Liabilities"],
}

CASHFLOW_FIELD_MAP = {
    "dividends_paid": ["Cash Dividends Paid", "Common Stock Dividend Paid"],
    "net_income": ["Net Income", "Net Income From Continuing Operations"],
}


def _normalize_index(df: pd.DataFrame):
    """Coerce a statement DataFrame index to a timezone-naive DatetimeIndex.

    The report code compares the index against timezone-naive datetimes, so any tz must be
    stripped to avoid tz-naive/tz-aware comparison errors.

    :param df: (pandas.DataFrame) statement frame with date-like index
    :return: same frame with a tz-naive DatetimeIndex, sorted ascending
    """
    df.index = pd.to_datetime(df.index)
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    df.sort_index(ascending=True, inplace=True)
    return df


def _remap_columns(df: pd.DataFrame, field_map: dict):
    """Translate yfinance row labels into stockyard's column names.

    :param df: (pandas.DataFrame) transposed yfinance statement (dates as index, items as columns)
    :param field_map: (dict) {column_name: [candidate yfinance labels]}
    :return: DataFrame with stockyard-named, numeric columns; missing source labels become NaN
    """
    if df is None or df.empty:
        return pd.DataFrame()

    remapped = pd.DataFrame(index=df.index)
    for column, yf_candidates in field_map.items():
        remapped[column] = np.nan
        for label in yf_candidates:
            if label in df.columns:
                remapped[column] = pd.to_numeric(df[label], errors="coerce")
                break
    return _normalize_index(remapped)
