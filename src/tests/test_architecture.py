# -*- coding: utf-8 -*-
"""Enforce the layering rule from ADR-0002.

The core (stockyard.data, stockyard.research) must never depend on a front end or a renderer, so it can
serve the bot, the CLI and the MCP server alike. Every submodule is imported, in a fresh interpreter so modules imported by other tests cannot mask a
violation.
"""
import json
import subprocess
import sys

import pytest

FORBIDDEN = ("discord", "matplotlib", "prettytable")
CORE_PACKAGES = ("stockyard.data", "stockyard.research")


@pytest.mark.parametrize("package", CORE_PACKAGES)
def test_core_package_does_not_import_front_end_or_rendering_libraries(package):
    code = (
        "import importlib, json, pkgutil, sys; "
        f"pkg = importlib.import_module({package!r}); "
        "[importlib.import_module(m.name) for m in pkgutil.walk_packages(pkg.__path__, pkg.__name__ + '.')]; "
        "print(json.dumps(sorted(m for m in sys.modules if m.split('.')[0] in "
        f"{FORBIDDEN!r})))"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert json.loads(result.stdout) == []
