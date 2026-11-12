# -*- coding: utf-8 -*-
"""yfinance statement labels mapped to the canonical column names the data layer uses."""
import numpy as np
import pandas as pd

# Map alphavantage field names (which the report code consumes) to the candidate yfinance
# row labels. yfinance label availability varies by company, so each target lists fallbacks
# tried in order; missing labels become NaN columns so downstream access never KeyErrors.
INCOME_FIELD_MAP = {
    "totalRevenue": ["Total Revenue"],
    "netIncome": ["Net Income", "Net Income Common Stockholders"],
}

BALANCE_FIELD_MAP = {
    "cashAndCashEquivalentsAtCarryingValue": ["Cash And Cash Equivalents"],
    "shortTermInvestments": ["Other Short Term Investments", "Short Term Investments"],
    "longTermDebt": ["Long Term Debt"],
    "commonStockSharesOutstanding": ["Ordinary Shares Number", "Share Issued"],
    "currentNetReceivables": ["Receivables", "Accounts Receivable", "Net Receivables"],
    "inventory": ["Inventory"],
    "otherCurrentAssets": ["Other Current Assets"],
    "totalCurrentAssets": ["Current Assets", "Total Current Assets"],
    "currentAccountsPayable": ["Accounts Payable", "Payables"],
    "shortTermDebt": ["Current Debt", "Current Debt And Capital Lease Obligation"],
    "otherCurrentLiabilities": ["Other Current Liabilities"],
    "totalCurrentLiabilities": ["Current Liabilities", "Total Current Liabilities"],
}

CASHFLOW_FIELD_MAP = {
    "dividendPayout": ["Cash Dividends Paid", "Common Stock Dividend Paid"],
    "netIncome": ["Net Income", "Net Income From Continuing Operations"],
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
    """Translate yfinance row labels into the alphavantage column names the report expects.

    :param df: (pandas.DataFrame) transposed yfinance statement (dates as index, items as columns)
    :param field_map: (dict) {alphavantage_name: [candidate yfinance labels]}
    :return: DataFrame with alphavantage-named, numeric columns; missing source labels become NaN
    """
    if df is None or df.empty:
        return pd.DataFrame()

    remapped = pd.DataFrame(index=df.index)
    for av_name, yf_candidates in field_map.items():
        remapped[av_name] = np.nan
        for label in yf_candidates:
            if label in df.columns:
                remapped[av_name] = pd.to_numeric(df[label], errors="coerce")
                break
    return _normalize_index(remapped)
