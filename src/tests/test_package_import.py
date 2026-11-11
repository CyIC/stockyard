# -*- coding: utf-8 -*-
"""Importing stockyard must have no visible side effects.

The CLI's stdout is a data channel for AI agents (ADR-0003), so nothing may be written to it merely by
importing the package.
"""
import subprocess
import sys


def _run(code: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)


def test_import_writes_nothing_to_stdout_or_stderr():
    result = _run("import stockyard")
    assert result.stdout == ""
    assert result.stderr == ""


def test_import_does_not_configure_root_logging():
    result = _run("import logging, stockyard; print(len(logging.getLogger().handlers))")
    assert result.stdout.strip() == "0"
