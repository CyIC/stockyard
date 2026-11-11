# -*- coding: utf-8 -*-
"""Record raw yfinance responses and replay them in tests without the network.

``RecordingTicker`` wraps a real ``yf.Ticker`` while ``fetch_stock_data`` runs, so a recording holds
exactly what the data layer asks for. ``ReplayTicker`` serves a recording back. Timezones are kept so an
evening announcement in New York keeps its local date.
"""
import datetime
import json
from pathlib import Path

import pandas as pd

from stockyard.data.snapshot import StockData, fetch_stock_data

FIXTURES_DIR = Path(__file__).parent / "fixtures"

ATTRIBUTES = (
    "financials",
    "quarterly_financials",
    "balance_sheet",
    "quarterly_balance_sheet",
    "cashflow",
    "quarterly_cashflow",
)


def _axis_to_dict(axis: pd.Index) -> dict:
    if isinstance(axis, pd.DatetimeIndex):
        return {
            "kind": "datetime",
            "tz": None if axis.tz is None else str(axis.tz),
            "name": axis.name,
            "values": [stamp.isoformat() for stamp in axis],
        }
    return {"kind": "plain", "name": axis.name, "values": list(axis)}


def _axis_from_dict(spec: dict) -> pd.Index:
    if spec["kind"] == "datetime":
        if spec["tz"]:
            axis = pd.to_datetime(spec["values"], utc=True).tz_convert(spec["tz"])
        else:
            axis = pd.to_datetime(spec["values"])
        return pd.DatetimeIndex(axis, name=spec["name"])
    return pd.Index(spec["values"], name=spec["name"])


def frame_to_dict(frame: pd.DataFrame | None) -> dict | None:
    """Serialise a DataFrame to JSON-safe primitives, preserving datetime axes and timezones."""
    if frame is None:
        return None
    return {
        "index": _axis_to_dict(frame.index),
        "columns": _axis_to_dict(frame.columns),
        "data": frame.astype(object).where(frame.notna(), None).to_numpy().tolist(),
    }


def frame_from_dict(spec: dict | None) -> pd.DataFrame | None:
    """Inverse of frame_to_dict."""
    if spec is None:
        return None
    frame = pd.DataFrame(spec["data"], index=_axis_from_dict(spec["index"]), columns=_axis_from_dict(spec["columns"]))
    return frame.infer_objects()


class RecordingTicker:
    """Pass-through wrapper around a yfinance Ticker that records every response."""

    def __init__(self, stock):
        """Wrap ``stock``; nothing is fetched until the data layer asks."""
        self._stock = stock
        self._attributes = {}
        self._calls = {}

    def __getattr__(self, name):
        """Fetch and record a statement attribute (financials, balance_sheet, ...)."""
        if name not in ATTRIBUTES:
            raise AttributeError(name)
        value = getattr(self._stock, name)
        self._attributes[name] = frame_to_dict(value)
        return value

    def get_earnings_dates(self, **kwargs):
        """Fetch and record earnings dates."""
        return self._record("get_earnings_dates", kwargs, self._stock.get_earnings_dates(**kwargs))

    def history(self, **kwargs):
        """Fetch and record price history."""
        return self._record("history", kwargs, self._stock.history(**kwargs))

    def _record(self, name, kwargs, value):
        self._calls[name] = {"kwargs": kwargs, "result": frame_to_dict(value)}
        return value

    def to_dict(self) -> dict:
        """Return the recording as JSON-safe primitives."""
        return {"ticker": self._stock.ticker, "attributes": self._attributes, "calls": self._calls}


class ReplayTicker:
    """Serves a recording made by RecordingTicker in place of yfinance.Ticker."""

    def __init__(self, recording: dict):
        """Rebuild every recorded frame up front."""
        self.ticker = recording["ticker"]
        for name, spec in recording["attributes"].items():
            setattr(self, name, frame_from_dict(spec))
        self._results = {name: frame_from_dict(call["result"]) for name, call in recording["calls"].items()}

    def get_earnings_dates(self, **_kwargs):
        """Return the recorded earnings dates."""
        return self._results["get_earnings_dates"]

    def history(self, **_kwargs):
        """Return the recorded price history."""
        return self._results["history"]


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
