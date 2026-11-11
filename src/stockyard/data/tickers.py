# -*- coding: utf-8 -*-
"""Ticker validation: the trust boundary for symbols typed by users or agents.

A validated ticker is safe to send to the data provider and to use as a cache path component.
"""
import re

_TICKER = re.compile(r"[A-Z0-9^][A-Z0-9.\-^=]{0,14}")


class InvalidTicker(ValueError):
    """Raised when input is not a plausible ticker symbol."""


def validate_ticker(raw: str) -> str:
    """Return the normalised (stripped, upper-case) ticker, or raise InvalidTicker.

    Accepts letters, digits and . - ^ = (e.g. BRK.B, ^GSPC, EURUSD=X), at most 15 characters, not
    starting with . - or =. Anything else, including path separators and whitespace inside the
    symbol, is rejected before it reaches the network or the filesystem.
    """
    ticker = raw.strip().upper()
    if not _TICKER.fullmatch(ticker):
        raise InvalidTicker(f"{raw!r} is not a valid ticker symbol")
    return ticker
