# -*- coding: utf-8 -*-
"""Load the yfinance snapshot fixture used by the stock report tests.

The snapshot in ``IBM.yfinance.json`` is a faithful capture of what the ``get_yfinance_*``
helpers return, so tests exercise the same contract the report functions see in production.
Regenerate it with ``python scripts/refresh_test_fixtures.py``.

Dates are used exactly as captured. Code under test takes an explicit ``as_of`` (design §5.3);
tests pin it to ``anchor()``, the snapshot's capture date, so results never drift with the clock.
"""
import datetime
import functools
import json
import os

import pandas as pd

FIXTURE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "IBM.yfinance.json")


def _payload_to_frame(payload: dict) -> pd.DataFrame:
    """Rebuild a DataFrame from a serialized payload."""
    index = [datetime.datetime.fromisoformat(stamp) for stamp in payload["index"]]
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
    """Return one dataset from the snapshot.

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

    if "data" in payload:
        return _payload_to_frame(payload)
    return {key: _payload_to_frame(sub) for key, sub in payload.items()}


def anchor() -> datetime.datetime:
    """Return the snapshot's capture date: the as_of to pin in tests."""
    return datetime.datetime.fromisoformat(_snapshot()["anchor"])
