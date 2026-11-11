# -*- coding: utf-8 -*-
# pylint: disable=C0116, W0511
"""Unit testing module for the utilities module."""
import asyncio
import os
import shutil
import tempfile
import unittest
from unittest import mock

from stockyard import utilities as util


class SendMessageInChunksTestCase(unittest.TestCase):
    """Unittest send_message_in_chunks."""

    def test_single_string_split_into_chunks(self):
        # Given - content longer than one Discord message
        channel = mock.AsyncMock()
        content = "a" * (util.MAX_MESSAGE_LENGTH + 10)

        # When
        asyncio.run(util.send_message_in_chunks(channel, content))

        # Then - two chunks sent
        self.assertEqual(channel.send.await_count, 2)
        first_chunk = channel.send.await_args_list[0].args[0]
        self.assertEqual(len(first_chunk), util.MAX_MESSAGE_LENGTH)

    def test_list_of_messages_each_sent(self):
        # Given - a list of short messages
        channel = mock.AsyncMock()
        content = ["one", "two", "three"]

        # When
        asyncio.run(util.send_message_in_chunks(channel, content))

        # Then - one send per list item
        self.assertEqual(channel.send.await_count, 3)


class DataPathTestCase(unittest.TestCase):
    """Test the data_path writable-output-dir resolver."""

    def test_default_uses_cwd(self):
        """With STOCKYARD_DATA_DIR unset, paths resolve under the current directory."""
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("STOCKYARD_DATA_DIR", None)
            result = util.data_path("eps_fig.jpg")
        self.assertEqual(result, os.path.join(".", "eps_fig.jpg"))

    def test_uses_env_var(self):
        """STOCKYARD_DATA_DIR relocates output under the configured directory."""
        tmp = tempfile.mkdtemp()
        try:
            with mock.patch.dict(os.environ, {"STOCKYARD_DATA_DIR": tmp}):
                result = util.data_path("stocks.pkl")
            self.assertEqual(result, os.path.join(tmp, "stocks.pkl"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_creates_parent_directory_for_subpath(self):
        """A nested part (e.g. charts/) has its parent directory created."""
        tmp = tempfile.mkdtemp()
        try:
            with mock.patch.dict(os.environ, {"STOCKYARD_DATA_DIR": tmp}):
                result = util.data_path("charts", "AAPL_chart.png")
            self.assertEqual(result, os.path.join(tmp, "charts", "AAPL_chart.png"))
            self.assertTrue(os.path.isdir(os.path.join(tmp, "charts")))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class LoadDiscordTokenTestCase(unittest.TestCase):
    """Test the Discord token resolver."""

    def test_from_env_var(self):
        """DISCORD_TOKEN environment variable takes precedence."""
        with mock.patch.dict(os.environ, {"DISCORD_TOKEN": "env-token"}, clear=False):
            self.assertEqual(util.load_discord_token(), "env-token")

    def test_from_token_file(self):
        """DISCORD_TOKEN_FILE (Docker secret) is read and stripped when no env var is set."""
        tmp = tempfile.mkdtemp()
        try:
            token_path = os.path.join(tmp, "discord_token")
            with open(token_path, "w", encoding="utf-8") as f:
                f.write("file-token\n")
            with mock.patch.dict(os.environ, {"DISCORD_TOKEN_FILE": token_path}, clear=False):
                os.environ.pop("DISCORD_TOKEN", None)
                self.assertEqual(util.load_discord_token(), "file-token")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_from_ini_fallback(self):
        """The legacy bot_config.ini in the working dir is used when no env config exists."""
        tmp = tempfile.mkdtemp()
        cwd = os.getcwd()
        try:
            with open(os.path.join(tmp, "bot_config.ini"), "w", encoding="utf-8") as f:
                f.write("[discord]\ntoken = ini-token\n")
            os.chdir(tmp)
            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop("DISCORD_TOKEN", None)
                os.environ.pop("DISCORD_TOKEN_FILE", None)
                self.assertEqual(util.load_discord_token(), "ini-token")
        finally:
            os.chdir(cwd)
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
