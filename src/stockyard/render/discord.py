# -*- coding: utf-8 -*-
"""Discord messages from rendered sections (design §6).

Discord caps a message at 2000 characters. Sections are split on line boundaries, each message is its own
closed code block (so markdown never breaks across messages), and only the first carries the title.
"""
from stockyard.render.text import RenderedSection

MAX_MESSAGE_LENGTH = 2000
OPEN, CLOSE = "```\n", "\n```"


def _pieces(body: str, room: int) -> list[str]:
    """Body lines, with any line longer than ``room`` cut into ``room``-sized pieces."""
    pieces = []
    for line in body.split("\n"):
        pieces += [line[i : i + room] for i in range(0, len(line), room)] or [""]  # noqa: E203
    return pieces


def messages(rendered: RenderedSection) -> list[str]:
    """One or more messages, each within Discord's limit, carrying the whole section."""
    title = f"__**{rendered.title}**__\n"
    room = MAX_MESSAGE_LENGTH - len(title) - len(OPEN) - len(CLOSE)
    chunks, current = [], []
    for piece in _pieces(rendered.body, room):
        if current and len("\n".join(current + [piece])) > room:
            chunks.append("\n".join(current))
            current = []
        current.append(piece)
    chunks.append("\n".join(current))
    return [(title if index == 0 else "") + OPEN + chunk + CLOSE for index, chunk in enumerate(chunks)]
