# -*- coding: utf-8 -*-
"""Recorded yfinance responses as test fixtures, replayed without the network.

Recordings use the same RecordingTicker / ReplayTicker as the cache (stockyard.data.cache): a recording
holds exactly the calls fetch_stock_data makes.
"""
import datetime
import json
from pathlib import Path


from stockyard.data.cache import RecordingTicker, ReplayTicker
from stockyard.data.snapshot import StockData, fetch_stock_data

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def save_recording(recorder: RecordingTicker, directory: Path, *, captured_at: datetime.date) -> Path:
    """Write a recording to ``<directory>/<TICKER>.raw.json`` with the date it was captured."""
    path = Path(directory) / f"{recorder.to_dict()['ticker']}.raw.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"captured_at": captured_at.isoformat(), "recording": recorder.to_dict()}
    path.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    return path


def load_stock_data(ticker: str, *, directory: Path = FIXTURES_DIR) -> tuple[StockData, datetime.date]:
    """Replay ``<TICKER>.raw.json`` through fetch_stock_data; return the data and the as_of to pin."""
    payload = json.loads((Path(directory) / f"{ticker}.raw.json").read_text(encoding="utf-8"))
    replay = ReplayTicker(payload["recording"])
    return fetch_stock_data(ticker, ticker_factory=lambda symbol: replay), datetime.date.fromisoformat(
        payload["captured_at"]
    )
