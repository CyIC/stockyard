# -*- coding: utf-8 -*-
"""Container healthchecks must run against the real package (design §16 defect 6)."""
import re
import subprocess
import sys
import tomllib
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


def test_deploy_button_spec_runs_warren_as_a_worker_from_the_dockerfile():
    spec = (ROOT / ".do" / "deploy.yaml").read_text(encoding="utf-8")

    assert "workers:" in spec and "services:" not in spec  # a Discord bot has no HTTP port
    assert "dockerfile_path: Dockerfile" in spec and (ROOT / "Dockerfile").exists()
    assert re.search(r"key: DISCORD_TOKEN\n\s+scope: RUN_TIME\n\s+type: SECRET", spec)
    assert re.search(r"key: STOCKYARD_DATA_DIR\n\s+scope: RUN_TIME\n\s+value: /tmp/", spec)  # no volumes there


def test_secret_files_are_ignored_by_git_and_docker():
    if not (ROOT / ".git").exists():
        pytest.skip("not a git checkout")
    ignored = subprocess.run(
        ["git", "check-ignore", "-q", "secrets/discord_token.txt"], cwd=ROOT, capture_output=True, check=False
    )
    tracked = subprocess.run(
        ["git", "check-ignore", "-q", "secrets/README.md"], cwd=ROOT, capture_output=True, check=False
    )
    assert ignored.returncode == 0 and tracked.returncode == 1
    assert "secrets/" in (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()


def test_dev_container_uses_the_v1_names():
    devcontainer = ROOT / ".devcontainer"
    text = "\n".join(path.read_text(encoding="utf-8") for path in sorted(devcontainer.iterdir()))

    assert '"STOCKYARD_DATA_DIR"' in (devcontainer / "devcontainer.json").read_text(encoding="utf-8")
    assert "WARREN_DATA_DIR" not in text and "warren_bot" not in text


def _installs_on_python_313(filename):
    if not filename.endswith(".whl"):
        return False
    python_tag, abi_tag = filename[:-4].split("-")[-3:-1]
    if python_tag in ("py3", "py2.py3") or "cp313" in python_tag.split("."):
        return True
    return abi_tag == "abi3" and int(python_tag.removeprefix("cp3")) <= 13


def test_every_locked_package_has_a_python_313_wheel():
    lock = tomllib.loads((ROOT / "poetry.lock").read_text(encoding="utf-8"))
    sdist_only = [
        f"{package['name']} {package['version']}"
        for package in lock["package"]
        if not any(_installs_on_python_313(file["file"]) for file in package.get("files", []))
    ]
    assert not sdist_only  # `poetry install` would compile these, and old numpy/pandas fail on 3.13


def test_lxml_is_a_direct_dependency():
    # yfinance's get_earnings_dates() parses Yahoo's page with pandas.read_html, which needs lxml, but yfinance does
    # not declare it. v0.1 only had it through xhtml2pdf -> svglib; recorded fixtures never call read_html.
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    lock = tomllib.loads((ROOT / "poetry.lock").read_text(encoding="utf-8"))
    assert "lxml" in project["tool"]["poetry"]["dependencies"]
    assert "lxml" in {package["name"] for package in lock["package"]}


def test_app_platform_runs_the_released_image_as_a_worker():
    spec = (ROOT / ".do" / "app.yml").read_text(encoding="utf-8")

    assert "workers:" in spec and "services:" not in spec  # a Discord bot has no HTTP port
    assert "dockerfile_path" not in spec and "github:" not in spec  # App Platform never builds; it runs CI's image
    assert re.search(r"image:\n\s+registry_type: GHCR\n\s+registry: cyic\n\s+repository: stockyard\n", spec)
    assert "digest: ${WARREN_DIGEST}" in spec and "deploy_on_push" not in spec  # exact image, deployed only by CI
    assert "instance_size_slug: apps-s-1vcpu-0.5gb" in spec
    assert re.search(r"key: DISCORD_TOKEN\n\s+scope: RUN_TIME\n\s+type: SECRET\n\s+value: \$\{DISCORD_TOKEN\}", spec)
    assert re.search(r"key: STOCKYARD_DATA_DIR\n\s+scope: RUN_TIME\n\s+value: /tmp/", spec)  # no volumes there


def test_release_workflow_tests_then_builds_then_deploys():
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")

    assert re.search(r"on:\n\s+release:\n\s+types: \[published\]", workflow)
    assert re.search(r"build:\n(.*\n)*?\s+needs: test\n", workflow)
    assert re.search(r"deploy:\n(.*\n)*?\s+needs: build\n", workflow)
    assert "tox -e flake8,pylint,py313" in workflow
    assert "ghcr.io/cyic/stockyard:${{ github.event.release.tag_name }}" in workflow  # GHCR names must be lower case
    assert "digitalocean/app_action/deploy@v2" in workflow and "app_spec_location: .do/app.yml" in workflow
    assert "WARREN_DIGEST: ${{ needs.build.outputs.digest }}" in workflow
    assert "environment: production" in workflow and "packages: write" in workflow
