# -*- coding: utf-8 -*-
"""The bot's !sr pipeline posts every section from the new core (plan phase 4 complete)."""
import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from stockyard import stock_analysis
from tests.builders import stock_data

SECTION_ORDER = [
    "Past Sales Records",
    "Past EPS",
    "Record of Stock",
    "Trends",
    "Cash Position",
    "Revenue Growth",
    "Earnings Growth",
    "Evaluating Risk & Reward",
]


def _run(monkeypatch=None, data=None):
    message = MagicMock()
    message.channel.send = AsyncMock()
    if data is not None:
        monkeypatch.setattr(stock_analysis, "fetch_stock_data", lambda ticker: data)
    asyncio.run(stock_analysis.run(message, "TEST"))
    texts = [str(c.args[0]) for c in message.channel.send.await_args_list if c.args]
    files = [c.kwargs["file"].filename for c in message.channel.send.await_args_list if "file" in c.kwargs]
    return texts, files


@pytest.mark.usefixtures("core_stub")
def test_every_section_is_posted_in_report_order():
    texts, _ = _run()
    titles = [title for text in texts for title in SECTION_ORDER if f"__**{title}**__" in text]
    assert titles == SECTION_ORDER


@pytest.mark.usefixtures("core_stub")
def test_trend_and_risk_charts_are_attached():
    _, files = _run()
    assert {"trend_high_low.png", "risk_eps_forecast.png", "risk_low_forecast.png"} <= set(files)


@pytest.mark.usefixtures("core_stub")
def test_a_company_without_earnings_still_gets_a_report_with_warnings(monkeypatch):
    """Issue #2: as much of the report as the data allows, never a crash."""
    texts, _ = _run(monkeypatch, stock_data(annual={"2025-12-31": (100.0, 10.0)}, prices=("2024-01-02", "2026-11-10")))

    assert len([t for t in texts if t.startswith("__**")]) == len(SECTION_ORDER)
    assert any("⚠" in t for t in texts)


def test_the_legacy_yfinance_integration_is_no_longer_used():
    assert not hasattr(stock_analysis, "yf_api")
