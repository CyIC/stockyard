# -*- coding: utf-8 -*-
"""Warren: the Discord front end (design §8.3).

Parses commands, builds reports off the event loop with the shared core, and posts them as Discord messages
and chart files. Nothing here computes analysis; importing it needs no Discord token.
"""
import asyncio
import contextlib
import logging
import re
import tempfile
from pathlib import Path

import discord

from stockyard import logging_config
from stockyard.clock import new_york_today
from stockyard.config import Settings
from stockyard.data.cache import Cache
from stockyard.data.errors import DataUnavailable, RateLimited, UpstreamError
from stockyard.data.snapshot import fetch_stock_data
from stockyard.data.tickers import InvalidTicker, validate_ticker
from stockyard.render import charts, text
from stockyard.render import discord as discord_messages
from stockyard.research.report import build_report
from stockyard.utilities import load_discord_token

LOGGER = logging.getLogger(__name__)
RATE_LIMITED = "Yahoo Finance is rate-limiting requests right now. Please try again in a few minutes."
UNREACHABLE = "I couldn't reach the market data source. Please try again later."

HELP = (
    "Hi! I'm Warren, the Cypress Investment Club's research assistant. I don't know or save your name.\n"
    "```\n"
    "!stock_report <ticker>  Stock Selection Guide report for a ticker (also !sr)\n"
    "!help                   This message\n"
    "```"
)
DISCORD_SECTIONS = (  # report order; fundamentals is for the CLI and JSON only
    ("past_sales", text.past_sales, None),
    ("past_eps", text.past_eps, None),
    ("record_of_stock", text.record_of_stock, None),
    ("trend", text.trend, charts.trend),
    ("cash_position", text.cash_position, None),
    ("revenue_growth", text.revenue_growth, None),
    ("earnings_growth", text.earnings_growth, None),
    ("risk_reward", text.risk_reward, charts.risk_reward),
)


def parse_command(content: str, application_id) -> tuple[str, str]:
    """Return (lower-cased command, argument), ignoring a leading @-mention of the bot."""
    content = content.strip()
    mention = f"<@{application_id}>"
    if content.startswith(mention):
        content = content[len(mention) :].strip()  # noqa: E203
    parts = re.split(r"\s+", content, maxsplit=1)
    return parts[0].lower(), (parts[1].strip() if len(parts) > 1 else "")


def _prepare(ticker: str, chart_dir: Path) -> list[tuple[str, object]]:
    """Fetch, analyse and render in a worker thread; return ("text", message) and ("file", path) items."""
    as_of = new_york_today()
    data = fetch_stock_data(ticker, cache=Cache(Settings.from_env().data_dir, today=as_of))
    report = build_report(data, as_of, sections=[name for name, _, _ in DISCORD_SECTIONS])
    items = []
    for name, render_text, render_charts in DISCORD_SECTIONS:
        result = report.sections[name]
        if result is None:
            items.append(("text", f"__**{name}**__ failed; see the warnings."))
            continue
        items += [("text", message) for message in discord_messages.messages(render_text(result))]
        if render_charts:
            items += [("file", path) for path in render_charts(result, chart_dir)]
    return items


async def stock_report(message, argument: str) -> None:
    """!stock_report / !sr: build the report off the event loop and post it."""
    if not argument:
        await message.reply("!stock_report requires a ticker symbol, e.g. `!sr MSFT`.")
        return
    try:
        ticker = validate_ticker(argument)
    except InvalidTicker:
        await message.reply(f"`{argument[:20]}` doesn't look like a ticker symbol.")
        return
    await message.add_reaction("⏳")
    try:
        with tempfile.TemporaryDirectory() as chart_dir:  # per request: concurrent reports never share files
            items = await asyncio.to_thread(_prepare, ticker, Path(chart_dir))
            for kind, payload in items:
                if kind == "text":
                    await message.channel.send(payload)
                else:
                    with open(payload, "rb") as handle:
                        await message.channel.send(file=discord.File(handle, filename=payload.name))
        await message.channel.send("✅ __**Stock Report Finished!**__")
    except DataUnavailable:
        await _failed(message, f"No data available for {ticker}.")
    except UpstreamError as exc:
        LOGGER.warning("stock report for %s: %s", ticker, exc)
        await _failed(message, RATE_LIMITED if isinstance(exc, RateLimited) else UNREACHABLE)
    except Exception:  # pylint: disable=broad-exception-caught  # report it in the channel, log the details
        LOGGER.exception("stock report for %s failed", ticker)
        await _failed(message, "❌ __**Stock Report Failed!**__")
    finally:
        with contextlib.suppress(discord.errors.Forbidden, discord.errors.NotFound):
            await message.clear_reaction("⏳")


async def _failed(message, reply: str) -> None:
    with contextlib.suppress(discord.errors.Forbidden):
        await message.add_reaction("🛑")
    await message.reply(reply)


async def handle_message(message, client_user, application_id) -> None:
    """Route one Discord message to its command."""
    if message.author == client_user or message.author.bot:
        return
    command, argument = parse_command(message.content, application_id)
    if not command:
        return
    match command:
        case "!help":
            await message.reply(HELP)
        case "!stock_report" | "!sr":
            await stock_report(message, argument)
        case _:
            await message.reply("Command not recognized. Try `!help`.")


def create_client() -> discord.Client:
    """A discord.Client wired to handle_message."""
    intents = discord.Intents.default()
    intents.guild_messages = True
    intents.messages = True
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        await client.change_presence(activity=discord.Activity(name="the markets.", type=discord.ActivityType.watching))
        LOGGER.info("logged in as %s (%s)", client.user, client.application_id)

    @client.event
    async def on_message(message):
        await handle_message(message, client.user, client.application_id)

    return client


def main() -> None:
    """Console script ``warren``: configure logging, read the token, run the bot."""
    logging_config.configure_logging()
    try:
        token = load_discord_token()
    except (KeyError, OSError) as exc:
        raise SystemExit(
            "No Discord token: set DISCORD_TOKEN, or DISCORD_TOKEN_FILE to a file holding it "
            f"(or a [discord] token in bot_config.ini). ({exc!r})"
        ) from exc
    create_client().run(token, log_handler=None)
