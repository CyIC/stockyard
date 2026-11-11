# -*- coding: utf-8 -*-
"""Recording raw yfinance responses and replaying them must be lossless (design §11)."""
import datetime
import importlib
import json
from pathlib import Path

import pandas as pd
import pandas.testing as pdt

from stockyard.data.snapshot import fetch_stock_data
from tests import test_snapshot
from stockyard.data.cache import RecordingTicker, ReplayTicker
from tests.fixture_replay import load_stock_data, save_recording


def _record(fake):
    recorder = RecordingTicker(fake)
    original = fetch_stock_data("IBM", ticker_factory=lambda symbol: recorder)
    payload = json.loads(json.dumps(recorder.to_dict()))  # through real JSON text
    return original, payload


def _assert_same(left, right):
    for field in (
        "income_annual",
        "income_quarterly",
        "balance_annual",
        "balance_quarterly",
        "cashflow_annual",
        "cashflow_quarterly",
        "earnings",
        "daily_prices",
    ):
        pdt.assert_frame_equal(getattr(left, field), getattr(right, field), check_freq=False)


def test_replay_reproduces_the_recorded_stock_data():
    original, payload = _record(test_snapshot._fake())

    replayed = fetch_stock_data("IBM", ticker_factory=lambda symbol: ReplayTicker(payload))

    _assert_same(original, replayed)


def test_timezones_survive_so_evening_announcements_keep_their_local_date():
    """20:30 New York is 01:30 UTC the next day; the replayed announcement must stay on its NY date."""
    late = pd.DataFrame(
        {"EPS Estimate": [1.0], "Reported EPS": [1.1], "Surprise(%)": [10.0]},
        index=pd.DatetimeIndex([pd.Timestamp("2026-07-22 20:30", tz="America/New_York")], name="Earnings Date"),
    )
    _, payload = _record(test_snapshot._fake(earnings_dates=late))

    replayed = fetch_stock_data("IBM", ticker_factory=lambda symbol: ReplayTicker(payload))

    assert replayed.earnings.index[0].date() == pd.Timestamp("2026-07-22").date()


def test_recording_has_the_ticker_and_every_call():
    _, payload = _record(test_snapshot._fake())

    assert payload["ticker"] == "IBM"
    assert set(payload["calls"]) == {"get_earnings_dates", "history"}
    assert {"financials", "balance_sheet", "cashflow"} <= set(payload["attributes"])


def test_saved_recordings_load_as_stock_data_with_their_capture_date(tmp_path):
    recorder = RecordingTicker(test_snapshot._fake())
    original = fetch_stock_data("IBM", ticker_factory=lambda symbol: recorder)
    save_recording(recorder, tmp_path, captured_at=datetime.date(2026, 11, 11))

    loaded, as_of = load_stock_data("IBM", directory=tmp_path)

    assert (tmp_path / "IBM.raw.json").exists()
    assert as_of == datetime.date(2026, 11, 11)
    _assert_same(original, loaded)


def test_record_script_writes_one_replayable_file_per_ticker(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "scripts"))
    record_raw_fixtures = importlib.import_module("record_raw_fixtures")
    fakes = {"IBM": test_snapshot._fake(), "MSFT": test_snapshot._fake()}
    fakes["MSFT"].ticker = "MSFT"

    record_raw_fixtures.main(
        ["ibm", "msft"], ticker_factory=fakes.__getitem__, directory=tmp_path, today=datetime.date(2026, 11, 11)
    )

    assert sorted(p.name for p in tmp_path.iterdir()) == ["IBM.raw.json", "MSFT.raw.json"]
    loaded, as_of = load_stock_data("MSFT", directory=tmp_path)
    assert loaded.ticker == "MSFT" and as_of == datetime.date(2026, 11, 11)
