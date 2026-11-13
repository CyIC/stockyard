# -*- coding: utf-8 -*-
"""Errors the data layer raises; front ends map them to exit codes and messages (design §5.5)."""


class DataUnavailable(Exception):
    """The source has no statements and no prices for the ticker (unknown or delisted symbol)."""


class UpstreamError(Exception):
    """The data source raised while fetching (network failure, rate limiting, API change).

    yfinance often logs failures and returns empty frames instead of raising; those surface as
    DataUnavailable, so this error is only guaranteed for failures yfinance raises.
    """
