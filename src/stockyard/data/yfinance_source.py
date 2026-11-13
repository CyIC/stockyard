# -*- coding: utf-8 -*-
"""yfinance specifics: statement labels mapped to stockyard's column names, and rate-limit detection."""
import functools
import threading

import numpy as np
import pandas as pd
from curl_cffi import requests as curl_requests

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


class RateLimitWatch(curl_requests.Session):
    """The curl_cffi session yfinance fetches through, noting Yahoo's 429 Too Many Requests responses.

    yfinance raises on some rate limits but swallows others (its statement scrapers catch every error and
    return empty tables), so the HTTP responses are the only reliable signal. yfinance shares one session
    across threads; ``begin()`` and ``hit`` are per thread, so concurrent reports never see each other's.
    """

    def __init__(self):
        """A Chrome-impersonating session, the same kind yfinance creates for itself."""
        super().__init__(impersonate="chrome")
        self._fetch = threading.local()

    def begin(self) -> None:
        """Start watching a new fetch on this thread."""
        self._fetch.hit = False

    @property
    def hit(self) -> bool:
        """Whether Yahoo rate limited a request on this thread since ``begin()``."""
        return getattr(self._fetch, "hit", False)

    def request(self, method, url, *args, **kwargs):  # pylint: disable=signature-differs
        """Send the request as curl_cffi would, noting a rate-limit response."""
        response = super().request(method, url, *args, **kwargs)
        if response.status_code == 429 or response.text.startswith("Too Many Requests"):
            self._fetch.hit = True
        return response


@functools.cache
def rate_limit_watch() -> RateLimitWatch:
    """The process-wide watch, created on first use (yfinance keeps one session for all tickers)."""
    return RateLimitWatch()
