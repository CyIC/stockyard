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


@pytest.mark.parametrize("name", ["app.yml", "deploy.yaml"])
def test_digitalocean_runs_warren_as_a_worker_from_the_dockerfile(name):
    spec = (ROOT / ".do" / name).read_text(encoding="utf-8")

    assert "workers:" in spec and "services:" not in spec  # a Discord bot has no HTTP port
    assert "dockerfile_path: Dockerfile" in spec and (ROOT / "Dockerfile").exists()
    assert re.search(r"key: DISCORD_TOKEN\n\s+scope: RUN_TIME\n\s+type: SECRET", spec)
    assert re.search(r"key: STOCKYARD_DATA_DIR\n\s+scope: RUN_TIME\n\s+value: /tmp/", spec)  # no volumes there
