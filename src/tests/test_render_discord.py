# -*- coding: utf-8 -*-
"""Discord rendering: titled, code-blocked, split on line boundaries within 2000 characters (design §6)."""
from stockyard.render import discord as render_discord
from stockyard.render.text import RenderedSection

LIMIT = 2000


def test_a_short_section_is_one_titled_code_block():
    assert render_discord.messages(RenderedSection("Past EPS", "FY2025  $11.57")) == [
        "__**Past EPS**__\n```\nFY2025  $11.57\n```"
    ]


def test_a_long_section_splits_on_line_boundaries_with_every_code_block_closed():
    lines = [f"row {i:04d} " + "x" * 60 for i in range(120)]
    messages = render_discord.messages(RenderedSection("Cash Position", "\n".join(lines)))

    assert len(messages) > 1
    assert all(len(message) <= LIMIT for message in messages)
    assert messages[0].startswith("__**Cash Position**__\n```\n")
    assert not any(message.startswith("__**") for message in messages[1:])
    assert all(message.count("```") == 2 and message.endswith("\n```") for message in messages)
    recovered = [line for message in messages for line in message.split("```")[1].strip("\n").split("\n")]
    assert recovered == lines


def test_a_single_overlong_line_is_cut_to_fit():
    messages = render_discord.messages(RenderedSection("T", "y" * 5000))
    assert all(len(message) <= LIMIT for message in messages)
    assert "".join(message.split("```")[1].strip("\n") for message in messages) == "y" * 5000
