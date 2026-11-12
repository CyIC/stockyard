# -*- coding: utf-8 -*-
"""Warren's !stock_report pipeline: the new core, rendered for Discord (bot adapter moves in phase 7)."""
import tempfile
from pathlib import Path

import discord

from stockyard.clock import new_york_today
from stockyard.data.fundamentals import aligned_annual_fundamentals
from stockyard.data.snapshot import fetch_stock_data
from stockyard.render import charts, text
from stockyard.render import discord as discord_messages
from stockyard.research import sections


async def _post(channel, rendered):
    for message in discord_messages.messages(rendered):
        await channel.send(message)


async def _post_charts(channel, paths):
    for path in paths:
        with open(path, "rb") as handle:
            await channel.send(file=discord.File(handle, filename=path.name))


async def run(message, ticker):
    """Build and post the Stock Selection Guide report for ``ticker`` from the new core.

    :param message: <discord.message> Discord message object to make replies to
    :param ticker: Company stock ticker
    """
    data = fetch_stock_data(ticker)
    as_of = new_york_today()
    fundamentals = aligned_annual_fundamentals(data, as_of)
    channel = message.channel
    with tempfile.TemporaryDirectory() as chart_dir:  # per request: concurrent reports never share files
        await _post(channel, text.past_sales(sections.past_sales(data, fundamentals, as_of)))
        await _post(channel, text.past_eps(sections.past_eps(data, fundamentals, as_of)))
        await _post(channel, text.record_of_stock(sections.record_of_stock(data, fundamentals, as_of)))
        trend_result = sections.trend(data, fundamentals, as_of)
        await _post(channel, text.trend(trend_result))
        await _post_charts(channel, charts.trend(trend_result, Path(chart_dir)))
        await _post(channel, text.cash_position(sections.cash_position(data, fundamentals, as_of)))
        await _post(channel, text.revenue_growth(sections.revenue_growth(data, fundamentals, as_of)))
        await _post(channel, text.earnings_growth(sections.earnings_growth(data, fundamentals, as_of)))
        risk = sections.risk_reward(data, fundamentals, as_of)
        await _post(channel, text.risk_reward(risk))
        await _post_charts(channel, charts.risk_reward(risk, Path(chart_dir)))
