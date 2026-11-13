# -*- coding: utf-8 -*-
# pylint: disable=C0116, W0511
"""Unit testing module for logging_config."""
import io
import logging
import os
import sys
import unittest
from unittest import mock

from stockyard import logging_config


class SetLoggingLevelTestCase(unittest.TestCase):
    """Cover every branch of set_logging_level."""

    def test_debug(self):
        self.assertEqual(logging_config.set_logging_level("debug"), logging.DEBUG)

    def test_info(self):
        self.assertEqual(logging_config.set_logging_level("info"), logging.INFO)

    def test_warn_alias(self):
        self.assertEqual(logging_config.set_logging_level("warn"), logging.WARNING)

    def test_warning(self):
        self.assertEqual(logging_config.set_logging_level("WARNING"), logging.WARNING)

    def test_error(self):
        self.assertEqual(logging_config.set_logging_level("error"), logging.ERROR)

    def test_critical(self):
        self.assertEqual(logging_config.set_logging_level("critical"), logging.CRITICAL)

    def test_unknown_defaults_to_info(self):
        self.assertEqual(logging_config.set_logging_level("bogus"), logging.INFO)


class ConfigureLoggingTestCase(unittest.TestCase):
    """configure_logging() is the only place logging is set up, and it never writes to stdout."""

    def tearDown(self):
        logging.getLogger().handlers.clear()

    def test_records_go_to_stderr_not_stdout(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch.object(sys, "stdout", stdout), mock.patch.object(sys, "stderr", stderr):
            logging_config.configure_logging()
            logging.getLogger("stockyard.test").warning("hello")
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("hello", stderr.getvalue())

    def test_level_comes_from_logging_level_env_var(self):
        with mock.patch.dict(os.environ, {"LOGGING_LEVEL": "error"}):
            logging_config.configure_logging()
        self.assertEqual(logging.getLogger().level, logging.ERROR)

    def test_level_defaults_to_info(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            logging_config.configure_logging()
        self.assertEqual(logging.getLogger().level, logging.INFO)


if __name__ == "__main__":
    unittest.main()
