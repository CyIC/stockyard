# -*- coding: utf-8 -*-
# pylint: disable=C0116, W0511
"""Collection of useful utilities for stockyard.

Includes getting data from alphavantage and processing data structures.
"""
import configparser
import logging
import os


def data_path(*parts) -> str:
    """Resolve a writable output path under the configured data directory.

    Reads the WARREN_DATA_DIR environment variable (default: current working directory) so
    file output works on a read-only container root where only a mounted data volume is
    writable. Ensures the returned path's parent directory exists.

    :param parts: path components joined under the data dir (e.g. "charts", "AAPL_chart.png")
    :return: path string with its parent directory created
    """
    base = os.environ.get("WARREN_DATA_DIR", ".")
    path = os.path.join(base, *parts)
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    return path


def load_discord_token() -> str:
    """Resolve the Discord bot token from the environment, a secret file, or the legacy INI.

    Resolution order (first match wins):
      1. DISCORD_TOKEN environment variable (e.g. --env-file .env)
      2. the file named by DISCORD_TOKEN_FILE (Docker/Swarm secret at /run/secrets/...)
      3. the [discord] token in bot_config.ini in the working directory (local dev fallback)

    :return: the Discord bot token
    :raises KeyError: if no token is found in any source
    """
    token = os.environ.get("DISCORD_TOKEN")
    if token:
        return token
    token_file = os.environ.get("DISCORD_TOKEN_FILE")
    if token_file:
        with open(token_file, encoding="utf-8") as handle:
            return handle.read().strip()
    parser = configparser.ConfigParser()
    parser.read("bot_config.ini")
    return parser["discord"]["token"]


MAX_MESSAGE_LENGTH = 2000  # Maximum message length allowed by Discord
logger = logging.getLogger("discord")
logger.setLevel(logging.DEBUG)


async def send_message_in_chunks(channel, content):
    """Split a long message into Discord allowed chunks.

    :param channel: Discord message channel
    :param content: Message to break into chunks
    :return:
    """
    # split the message into chunks
    if isinstance(content, list):
        for msg in content:
            chunks = [msg[i : i + MAX_MESSAGE_LENGTH] for i in range(0, len(msg), MAX_MESSAGE_LENGTH)]  # noqa: E203

            for chunk in chunks:
                await channel.send(chunk)  # send each chunk to the channel
    else:
        chunks = [content[i : i + MAX_MESSAGE_LENGTH] for i in range(0, len(content), MAX_MESSAGE_LENGTH)]  # noqa: E203

        for chunk in chunks:
            await channel.send(chunk)  # send each chunk to the channel


