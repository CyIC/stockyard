# -*- coding: utf-8 -*-
"""Shared fixtures."""
import datetime

import pytest

from tests.builders import quarterly_eps, stock_data

CORE_STUB_ANNUAL = {"2022-12-31": (100.0, 10.0), "2023-12-31": (120.0, 12.0), "2024-12-31": (150.0, 15.0), "2025-12-31": (180.0, 18.0)}


@pytest.fixture
def core_stub(monkeypatch):
    """Legacy run() tests: serve the new core from a small hand-built company instead of the network."""
    from stockyard import stock_analysis  # pylint: disable=import-outside-toplevel

    quarters = [f"{year}-{md}" for year in range(2022, 2026) for md in ("03-31", "06-30", "09-30", "12-31")]
    data = stock_data(annual=CORE_STUB_ANNUAL, eps=quarterly_eps(quarters), prices=("2021-12-01", "2026-11-10"))
    monkeypatch.setattr(stock_analysis, "fetch_stock_data", lambda ticker: data)
    monkeypatch.setattr(stock_analysis, "new_york_today", lambda: datetime.date(2026, 11, 11))
    return data
