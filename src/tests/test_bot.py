# -*- coding: utf-8 -*-
"""Warren, the Discord front end (design §8.3, plan phase 7). No Discord connection is made."""
import asyncio
import os
import subprocess
import sys
import threading
import tomllib
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from stockyard import bot
from stockyard.data.errors import DataUnavailable, RateLimited, UpstreamError
from tests.builders import quarterly_eps, stock_data

SECTION_TITLES = [
    "Past Sales Records",
    "Past EPS",
    "Record of Stock",
    "Trends",
    "Cash Position",
    "Revenue Growth",
    "Earnings Growth",
    "Evaluating Risk & Reward",
]


def _message(content, author_is_bot=False):
    message = MagicMock()
    message.content = content
    message.author.bot = author_is_bot
    message.reply = AsyncMock()
    message.add_reaction = AsyncMock()
    message.clear_reaction = AsyncMock()
    message.channel.send = AsyncMock()
    return message


def _handle(message, **kwargs):
    asyncio.run(bot.handle_message(message, client_user=object(), application_id=123, **kwargs))
    return message


def _replies(message):
    return [str(call.args[0]) for call in message.reply.await_args_list]


def _sent(message):
    return [str(call.args[0]) for call in message.channel.send.await_args_list if call.args]


@pytest.fixture(name="company")
def _company(monkeypatch):
    quarters = [f"{y}-{md}" for y in range(2022, 2026) for md in ("03-31", "06-30", "09-30", "12-31")]
    data = stock_data(
        annual={f"{y}-12-31": (100.0 + y, 10.0) for y in range(2022, 2026)},
        eps=quarterly_eps(quarters),
        prices=("2021-12-01", "2026-11-10"),
    )
    calls = []

    def fetch(ticker, **kwargs):
        calls.append((ticker, threading.get_ident()))
        return data

    monkeypatch.setattr(bot, "fetch_stock_data", fetch)
    monkeypatch.setattr(bot, "new_york_today", lambda: __import__("datetime").date(2026, 11, 11))
    return calls


def test_importing_the_bot_needs_no_discord_token():
    env = {k: v for k, v in os.environ.items() if not k.startswith("DISCORD")}
    result = subprocess.run([sys.executable, "-c", "import stockyard.bot"], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ("!sr msft", ("!sr", "msft")),
        ("!SR  ibm ", ("!sr", "ibm")),
        ("<@123> !stock_report ibm", ("!stock_report", "ibm")),
        ("!help", ("!help", "")),
        ("", ("", "")),
    ],
)
def test_parse_command(content, expected):
    assert bot.parse_command(content, application_id=123) == expected


def test_messages_from_bots_are_ignored():
    message = _handle(_message("!help", author_is_bot=True))
    message.reply.assert_not_awaited()


def test_help_lists_only_real_commands():
    (reply,) = _replies(_handle(_message("!help")))
    assert "!stock_report" in reply and "!sr" in reply and "!help" in reply
    assert "!bug" not in reply


def test_bug_is_no_longer_a_command():
    assert _replies(_handle(_message("!bug"))) == ["Command not recognized. Try `!help`."]


def test_stock_report_needs_a_ticker():
    assert "requires a ticker" in _replies(_handle(_message("!sr")))[0]


def test_an_invalid_ticker_is_rejected_before_fetching(company):
    replies = _replies(_handle(_message("!sr ../etc")))
    assert "doesn't look like a ticker" in replies[0]
    assert company == []


def test_no_data_and_upstream_failures_get_friendly_replies(monkeypatch):
    def unavailable(ticker, **kwargs):
        raise DataUnavailable("none")

    monkeypatch.setattr(bot, "fetch_stock_data", unavailable)
    assert "No data available for ZZZZ" in _replies(_handle(_message("!sr zzzz")))[-1]

    def down(ticker, **kwargs):
        raise UpstreamError("down")

    monkeypatch.setattr(bot, "fetch_stock_data", down)
    assert "couldn't reach the market data source" in _replies(_handle(_message("!sr ibm")))[-1]


def test_an_unexpected_failure_is_reported_not_raised(monkeypatch):
    def broken(ticker, **kwargs):
        raise RuntimeError("bug")

    monkeypatch.setattr(bot, "fetch_stock_data", broken)
    message = _handle(_message("!sr ibm"))
    assert "Stock Report Failed" in _replies(message)[-1]


def test_a_report_posts_every_section_in_order_with_charts_and_a_finish_line(company):
    message = _handle(_message("!sr ibm"))
    sent = _sent(message)

    titles = [title for text in sent for title in SECTION_TITLES if f"__**{title}**__" in text]
    assert titles == SECTION_TITLES
    files = [c.kwargs["file"].filename for c in message.channel.send.await_args_list if "file" in c.kwargs]
    assert {"trend_high_low.png", "risk_eps_forecast.png"} <= set(files)
    assert "Stock Report Finished" in sent[-1]
    assert all(len(text) <= 2000 for text in sent)


def test_the_report_is_built_off_the_event_loop(company):
    _handle(_message("!sr ibm"))
    ((ticker, thread),) = company
    assert ticker == "IBM" and thread != threading.get_ident()


def test_main_reads_the_token_only_when_called_and_runs_the_client(monkeypatch):
    client = MagicMock()
    monkeypatch.setattr(bot, "load_discord_token", lambda: "secret")
    monkeypatch.setattr(bot, "create_client", lambda: client)
    monkeypatch.setattr(bot.logging_config, "configure_logging", lambda: None)

    bot.main()

    assert client.run.call_args.args == ("secret",)


def test_warren_console_script_and_docker_run_the_bot():
    root = Path(__file__).resolve().parents[2]
    scripts = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["tool"]["poetry"]["scripts"]
    assert scripts["warren"] == "stockyard.bot:main"
    assert 'CMD ["-m", "stockyard.bot"]' in (root / "Dockerfile").read_text(encoding="utf-8")


def test_a_missing_token_exits_with_a_clear_message(monkeypatch):
    def missing():
        raise KeyError("discord")

    monkeypatch.setattr(bot, "load_discord_token", missing)
    monkeypatch.setattr(bot.logging_config, "configure_logging", lambda: None)
    with pytest.raises(SystemExit, match="DISCORD_TOKEN"):
        bot.main()


def test_a_rate_limit_says_so_and_upstream_failures_are_logged(monkeypatch, caplog):
    def throttled(ticker, **kwargs):
        raise RateLimited("fetching IBM: Yahoo Finance rate limited the request")

    monkeypatch.setattr(bot, "fetch_stock_data", throttled)
    with caplog.at_level("WARNING", logger="stockyard.bot"):
        reply = _replies(_handle(_message("!sr ibm")))[-1]
    assert "rate-limiting" in reply and "few minutes" in reply
    assert any("rate limited" in record.getMessage() for record in caplog.records)
