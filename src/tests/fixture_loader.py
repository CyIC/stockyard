# -*- coding: utf-8 -*-
"""Load the yfinance snapshot fixture used by the stock report tests.

The snapshot in ``IBM.yfinance.json`` is a faithful capture of what the ``get_yfinance_*``
helpers return, so tests exercise the same contract the report functions see in production.
Regenerate it with ``python scripts/refresh_test_fixtures.py``.

Every report function in stock_analysis filters its inputs to
``datetime.datetime.now() - relativedelta(years=5)``. A fixture with fixed dates therefore
decays: once it ages past that window the filters start silently trimming rows, and the
report is computed from a handful of survivors. To keep the tests drift-proof, every index is
shifted forward by the number of whole years elapsed since the snapshot's anchor date. The
shift is a whole number of years so fiscal year ends stay on their original month and day,
and it is applied uniformly across every dataset so prices and earnings stay aligned with
each other (record_of_stock looks up price rows by the fiscal year of an earnings row).
"""
import datetime
import functools
import json
import os

import pandas as pd
from dateutil.relativedelta import relativedelta

FIXTURE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "IBM.yfinance.json")


def _shift_years(snapshot_anchor: str) -> int:
    """Return the whole years elapsed since the snapshot was captured."""
    anchor = datetime.datetime.fromisoformat(snapshot_anchor)
    now = datetime.datetime.now()
    if now <= anchor:
        return 0
    return relativedelta(now, anchor).years


def _payload_to_frame(payload: dict, shift: int) -> pd.DataFrame:
    """Rebuild a DataFrame from a serialized payload, shifting its index forward."""
    index = [datetime.datetime.fromisoformat(stamp) for stamp in payload["index"]]
    if shift:
        index = [stamp + relativedelta(years=shift) for stamp in index]
    frame = pd.DataFrame(payload["data"], columns=payload["columns"], index=pd.to_datetime(index))
    frame.index.name = payload["index_name"]
    for column, dtype in payload.get("dtypes", {}).items():
        if column in frame.columns and dtype.startswith(("float", "int")):
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame


@functools.lru_cache(maxsize=1)
def _snapshot() -> dict:
    """Read and parse the fixture file once per session."""
    with open(FIXTURE_PATH, encoding="utf-8") as handle:
        return json.load(handle)


def load(dataset: str):
    """Return one dataset from the snapshot, rebased to the current date.

    :param dataset: one of income_statement, balance_sheet, cash_flow, earnings,
        monthly_prices, daily_prices
    :return: a DataFrame for the price datasets, or a dict of DataFrames for the statements,
        matching what the corresponding get_yfinance_* helper returns
    """
    snapshot = _snapshot()
    try:
        payload = snapshot["datasets"][dataset]
    except KeyError as exc:
        raise KeyError(f"{dataset!r} not in fixture; have {sorted(snapshot['datasets'])}") from exc

    shift = _shift_years(snapshot["anchor"])
    if "data" in payload:
        return _payload_to_frame(payload, shift)
    return {key: _payload_to_frame(sub, shift) for key, sub in payload.items()}


def anchor() -> datetime.datetime:
    """Return the snapshot's as-of date, after rebasing."""
    snapshot = _snapshot()
    captured = datetime.datetime.fromisoformat(snapshot["anchor"])
    return captured + relativedelta(years=_shift_years(snapshot["anchor"]))
