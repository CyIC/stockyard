# -*- coding: utf-8 -*-
"""Centralized logging configuration file.

See LICENSE.md for license info.
"""
import logging.config
import os

from pythonjsonlogger import jsonlogger  # noqa: F401 pylint: disable=unused-import


def set_logging_level(level):
    """Return proper logging level for logging library.

    :param level: str of the logging level
    :return: proper logging class
    """
    level = str.upper(level)
    if level == "DEBUG":
        rtn_level = logging.DEBUG
    elif level == "INFO":
        rtn_level = logging.INFO
    elif level in ("WARN", "WARNING"):
        rtn_level = logging.WARNING
    elif level == "ERROR":
        rtn_level = logging.ERROR
    elif level == "CRITICAL":
        rtn_level = logging.CRITICAL
    else:
        rtn_level = logging.INFO
    return rtn_level


def configure_logging():
    """Configure root logging for a front end (bot or CLI).

    Never called on import: a library must not install handlers on behalf of whoever imports it.
    Records go to stderr so stdout stays a clean data channel (ADR-0003). The level comes from the
    LOGGING_LEVEL environment variable (default INFO).
    """
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {
                    "format": (
                        "%(asctime)s::%(levelname)s::%(name)s::%(filename)s::%(lineno)s::%(funcName)s::%(message)s"
                    ),
                    "class": "pythonjsonlogger.jsonlogger.JsonFormatter",
                }
            },
            "handlers": {
                "stderr": {
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stderr",
                    "formatter": "json",
                }
            },
            "root": {
                "handlers": ["stderr"],
                "level": set_logging_level(os.environ.get("LOGGING_LEVEL", "INFO")),
            },
        }
    )
