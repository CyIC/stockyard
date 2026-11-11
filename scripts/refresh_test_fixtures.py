# -*- coding: utf-8 -*-
"""Regenerate the test fixture snapshot from live yfinance data.

Captures exactly what the ``get_yfinance_*`` helpers return, so the fixture is a faithful
snapshot of the contract the report functions consume rather than an approximation of it.

The snapshot records an ``anchor`` (its newest observation). ``src/tests/fixture_loader.py``
shifts every index forward by whole elapsed years at load time, so the five-year lookback
windows inside stock_analysis always see the complete dataset no matter when the suite runs.

Usage (from the repository root)::

    python scripts/refresh_test_fixtures.py
    python scripts/refresh_test_fixtures.py --ticker MSFT --out src/tests/MSFT.yfinance.json
"""
import argparse
import datetime
import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from warren_bot import yfinance_integration as yf_api  # noqa: E402  pylint: disable=C0413


def _clean(value):
    """Coerce a numpy/pandas scalar into something json can represent."""
    if pd.isna(value):
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, (int,)) or hasattr(value, "is_integer") is False:
        return int(value)
    number = float(value)
    return round(number, 6)


def _frame_to_payload(frame: pd.DataFrame) -> dict:
    """Serialize a date-indexed DataFrame into a json-safe split-style payload."""
    return {
        "index_name": frame.index.name,
        "index": [stamp.isoformat() for stamp in frame.index],
        "columns": list(frame.columns),
        "dtypes": {str(column): str(dtype) for column, dtype in frame.dtypes.items()},
        "data": [[_clean(value) for value in row] for row in frame.itertuples(index=False, name=None)],
    }


def _newest(frame: pd.DataFrame):
    """Return the newest index value in a frame, or None when it is empty."""
    return None if frame.empty else frame.index.max()


def build_snapshot(ticker: str) -> dict:
    """Pull every dataset the stock report needs and package it with an anchor date."""
    reports = {
        "income_statement": yf_api.get_yfinance_income_statement(ticker),
        "balance_sheet": yf_api.get_yfinance_balance_sheet(ticker),
        "cash_flow": yf_api.get_yfinance_cash_flow(ticker),
        "earnings": yf_api.get_yfinance_earnings(ticker),
    }
    prices = {
        "monthly_prices": yf_api.get_monthly_yfinance_company_prices(ticker),
        "daily_prices": yf_api.get_daily_yfinance_company_prices(ticker),
    }

    # The newest daily price is the snapshot's "as of" date. Statement frames are not used
    # here: yfinance labels some periods with a fiscal end that is still in the future.
    anchor = _newest(prices["daily_prices"])
    if anchor is None:
        raise SystemExit(f"no daily prices returned for {ticker}; cannot anchor the snapshot")

    datasets = {name: {key: _frame_to_payload(frame) for key, frame in group.items()} for name, group in reports.items()}
    datasets.update({name: _frame_to_payload(frame) for name, frame in prices.items()})

    return {
        "ticker": ticker,
        "generated": datetime.datetime.now().isoformat(timespec="seconds"),
        "anchor": anchor.isoformat(),
        "datasets": datasets,
    }


def main() -> int:
    """Write a fresh snapshot to disk."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ticker", default="IBM")
    parser.add_argument("--out", default=os.path.join("src", "tests", "IBM.yfinance.json"))
    args = parser.parse_args()

    snapshot = build_snapshot(args.ticker)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(snapshot, handle, indent=1, allow_nan=False)
        handle.write("\n")

    size_kb = os.path.getsize(args.out) / 1024
    print(f"wrote {args.out} ({size_kb:,.0f} KB), anchor={snapshot['anchor']}")
    for name, payload in snapshot["datasets"].items():
        if "data" in payload:
            print(f"  {name}: {len(payload['data'])} rows")
        else:
            for key, sub in payload.items():
                print(f"  {name}.{key}: {len(sub['data'])} rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
