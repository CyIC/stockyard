# -*- coding: utf-8 -*-
"""Container healthchecks must run against the real package (design §16 defect 6)."""
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SNIPPET = re.compile(r'"-c",\s*"([^"]+)"')


def _healthchecks():
    for name in ("Dockerfile", "docker-compose.yml", "docker-compose.secure.yml"):
        lines = (ROOT / name).read_text(encoding="utf-8").splitlines()
        for number, line in enumerate(lines):
            if "HEALTHCHECK" in line or "healthcheck:" in line:
                window = " ".join(lines[number : number + 3])  # noqa: E203
                yield pytest.param(SNIPPET.search(window).group(1), id=name)


@pytest.mark.parametrize("code", _healthchecks())
def test_healthcheck_snippet_succeeds(code):
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
