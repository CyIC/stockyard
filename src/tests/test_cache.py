# -*- coding: utf-8 -*-
"""Tests for the same-day cache (design §7)."""
import datetime
import json

import pandas.testing as pdt
import pytest

from stockyard.data.cache import Cache
from stockyard.data.errors import DataUnavailable, UpstreamError
from stockyard.data.snapshot import fetch_stock_data
from stockyard.data.tickers import InvalidTicker
from tests import test_snapshot
from tests.fakes import FakeTicker

DAY = datetime.date(2026, 11, 11)


def _never(symbol):
    raise AssertionError(f"network used for {symbol}")


def _fetch_into(directory, today=DAY, fake=None):
    fake = fake or test_snapshot._fake()
    return fetch_stock_data("ibm", ticker_factory=lambda symbol: fake, cache=Cache(directory, today=today))


def test_a_miss_fetches_and_writes_one_json_entry(tmp_path):
    _fetch_into(tmp_path)
    entry = tmp_path / "cache" / "IBM.json"
    assert json.loads(entry.read_text(encoding="utf-8"))["date"] == "2026-11-11"


def test_a_hit_on_the_same_day_does_not_touch_the_network(tmp_path):
    first = _fetch_into(tmp_path)

    second = fetch_stock_data("IBM", ticker_factory=_never, cache=Cache(tmp_path, today=DAY))

    pdt.assert_frame_equal(first.earnings, second.earnings)
    pdt.assert_frame_equal(first.daily_prices, second.daily_prices, check_freq=False)
    pdt.assert_frame_equal(first.income_annual, second.income_annual)


def test_an_entry_from_another_day_is_refetched(tmp_path):
    _fetch_into(tmp_path, today=DAY)
    calls = []

    def factory(symbol):
        calls.append(symbol)
        return test_snapshot._fake()

    fetch_stock_data("IBM", ticker_factory=factory, cache=Cache(tmp_path, today=DAY + datetime.timedelta(days=1)))

    assert calls == ["IBM"]
    assert json.loads((tmp_path / "cache" / "IBM.json").read_text(encoding="utf-8"))["date"] == "2026-11-12"


def test_without_a_cache_nothing_is_written(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    fetch_stock_data("IBM", ticker_factory=lambda symbol: test_snapshot._fake())
    assert list(tmp_path.iterdir()) == []


def test_unavailable_data_is_not_cached(tmp_path):
    with pytest.raises(DataUnavailable):
        _fetch_into(tmp_path, fake=FakeTicker("IBM"))
    assert not (tmp_path / "cache" / "IBM.json").exists()


def test_upstream_failures_are_not_cached(tmp_path):
    class Broken(FakeTicker):
        def history(self, **kwargs):
            raise ConnectionError("down")

    with pytest.raises(UpstreamError):
        _fetch_into(tmp_path, fake=Broken("IBM", earnings_dates=test_snapshot._earnings_dates()))
    assert not (tmp_path / "cache" / "IBM.json").exists()


def test_an_invalid_ticker_never_reaches_the_cache_directory(tmp_path):
    with pytest.raises(InvalidTicker):
        fetch_stock_data("../../escape", ticker_factory=_never, cache=Cache(tmp_path, today=DAY))
    assert list(tmp_path.iterdir()) == []


def test_writes_leave_no_temporary_files(tmp_path):
    _fetch_into(tmp_path)
    assert sorted(p.name for p in (tmp_path / "cache").iterdir()) == ["IBM.json"]
