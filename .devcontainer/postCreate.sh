#!/usr/bin/env bash
# Runs once when the container is created. Installs the toolchain against the mounted
# workspace, which is not available during the image build.
set -euo pipefail

WORKSPACE="${1:-$PWD}"
cd "$WORKSPACE"

echo "==> Claiming mounted volumes"
# .tox and the pip cache are named volumes (see devcontainer.json). Docker creates them
# root-owned on first use, so hand them to the user that will write to them.
sudo chown -R vscode:vscode .tox "$HOME/.cache/pip" 2>/dev/null || true

# UID mismatches between a Windows host and the container make git treat the bind mount as
# untrusted, which breaks every git command in the workspace.
git config --global --add safe.directory "$WORKSPACE" || true

echo "==> Upgrading pip"
# PEP 735 dependency groups (`pip install --group`) need pip 25.1 or newer, and the dev
# toolchain below is declared only as a group in pyproject.toml.
python -m pip install --quiet --upgrade pip

echo "==> Installing stockyard and its runtime dependencies"
# pip, not `poetry install`, to match the production installer stage in ../Dockerfile, which
# also resolves with pip. Versions here are freshly resolved, so they can be newer than
# poetry.lock. (The lock was stale until v1.0 and pinned packages with no cp313 wheels; it now
# installs cleanly with `poetry install`, and src/tests/test_deployment.py keeps it that way.)
python -m pip install --editable .

echo "==> Installing the dev toolchain (PEP 735 'dev' group)"
python -m pip install --group dev

echo "==> Creating runtime output directories"
# STOCKYARD_DATA_DIR points at ./data (gitignored); logs go to stderr.
mkdir -p data

echo
echo "================================================================"
python --version
echo "pip      $(python -m pip --version | awk '{print $2}')"
echo "poetry   $(poetry --version 2>/dev/null | awk '{print $3}' | tr -d '()')"
echo "tox      $(tox --version 2>/dev/null | awk '{print $1}')"
echo "pytest   $(python -m pytest --version 2>/dev/null | awk '{print $2}')"
echo "venv     ${VIRTUAL_ENV:-none}"
echo "================================================================"
echo
echo "Run the suite with:   pytest src/tests/ -q"
echo "Full gate with:       tox"
echo
if [ -z "${DISCORD_TOKEN:-}${DISCORD_TOKEN_FILE:-}" ]; then
    echo "NOTE: DISCORD_TOKEN is not set. Warren ('warren' or 'python -m stockyard.bot') needs it;"
    echo "      the CLI ('stockyard report MSFT') and the tests do not."
fi
