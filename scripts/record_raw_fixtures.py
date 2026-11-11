# -*- coding: utf-8 -*-
"""Record raw yfinance responses as replayable test fixtures (design §11).

Run from the repository root, on a machine that can reach Yahoo Finance:

    poetry run python scripts/record_raw_fixtures.py IBM MSFT RDDT

Writes src/tests/fixtures/<TICKER>.raw.json for each ticker. Tests replay them with
tests.fixture_replay.load_stock_data and pin as_of to the capture date.
"""
import datetime
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import yfinance as yf  # noqa: E402  pylint: disable=C0413

from stockyard.data.snapshot import fetch_stock_data  # noqa: E402  pylint: disable=C0413
from stockyard.data.cache import RecordingTicker  # noqa: E402  pylint: disable=C0413
from tests.fixture_replay import FIXTURES_DIR, save_recording  # noqa: E402  pylint: disable=C0413


def _record_one(raw, ticker_factory):
    """Run fetch_stock_data with a recording wrapper and return the recorder."""
    recorders = []

    def factory(symbol):
        recorders.append(RecordingTicker(ticker_factory(symbol)))
        return recorders[-1]

    fetch_stock_data(raw, ticker_factory=factory)
    return recorders[-1]


def main(tickers, *, ticker_factory=yf.Ticker, directory=FIXTURES_DIR, today=None):
    """Record each ticker through the real data-layer path and save it."""
    today = today or datetime.date.today()
    for raw in tickers:
        path = save_recording(_record_one(raw, ticker_factory), directory, captured_at=today)
        print(f"recorded {path}")


if __name__ == "__main__":
    main(sys.argv[1:])
