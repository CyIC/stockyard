# -*- coding: utf-8 -*-
"""Errors the data layer raises; front ends map them to exit codes and messages (design §5.5)."""


class DataUnavailable(Exception):
    """The source has no statements and no prices for the ticker (unknown or delisted symbol)."""


class UpstreamError(Exception):
    """The data source failed while fetching (network failure, rate limiting, API change)."""


class RateLimited(UpstreamError):
    """Yahoo Finance answered 429 Too Many Requests, whether yfinance raised it or swallowed it."""
