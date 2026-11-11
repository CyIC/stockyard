# ======================================================================================
# DEVELOPMENT CONTAINER FOR WARREN BOT
#
# This is intentionally NOT derived from the project's production Dockerfile. That image is
# Chainguard distroless with no shell, which a devcontainer cannot use. Production hardening
# lives in ../Dockerfile and is left untouched; this image optimises for developer ergonomics
# on the same Python minor version (3.13, per pyproject's `python = "^3.13"`).
# ======================================================================================
ARG BASE_IMAGE=mcr.microsoft.com/devcontainers/python:1-3.13-bookworm
FROM ${BASE_IMAGE}

# Pinned to the version that generated poetry.lock. An older Poetry rewrites the lock on
# contact: a 2.1.2 run against this 2.4.1 lock stripped 1680 lines. Note ../Dockerfile still
# pins 2.1.0 -- it only ever calls `poetry build` so it cannot corrupt the lock, but the two
# pins disagreeing is worth resolving.
ARG POETRY_VERSION=2.4.1

# The venv lives outside the workspace on purpose: the workspace is a bind mount from a
# Windows host, where a venv is slow over thousands of small files and would collide with the
# host's own venv/ directory. MPLBACKEND keeps chart rendering headless -- there is no display
# here, and test_stock_analysis.py does not set a backend itself.
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV POETRY_NO_INTERACTION=1
ENV VENV_PATH=/home/vscode/.venv
ENV MPLBACKEND=Agg
ENV MPLCONFIGDIR=/home/vscode/.cache/matplotlib

# pinentry-curses lets gpg prompt for a passphrase on the terminal. Without a TTY pinentry gpg
# tries to open a GUI dialog, which in a container has nothing to draw on, and fails with
# "signing failed: Timeout" -- the exact failure this repo hits when commit.gpgsign is true
# and no graphical agent is reachable.
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        gnupg2 \
        pinentry-curses \
        less \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Poetry gets its own pipx prefix rather than the project venv: it manages virtualenvs, and
# installing it into the venv it operates on invites dependency conflicts. Every other tool
# (tox, pytest, flake8, pylint, mypy, black, bandit, pip-audit) comes from the PEP 735 "dev"
# group in postCreate.sh, keeping pyproject.toml the single source of tool versions.
RUN pipx install "poetry==${POETRY_VERSION}"

# Point gpg at the terminal pinentry installed above.
RUN mkdir -p /home/vscode/.gnupg \
    && printf 'pinentry-program /usr/bin/pinentry-curses\n' > /home/vscode/.gnupg/gpg-agent.conf \
    && printf 'use-agent\n' > /home/vscode/.gnupg/gpg.conf \
    && chmod 700 /home/vscode/.gnupg \
    && chown -R vscode:vscode /home/vscode/.gnupg

# Pre-create the venv and matplotlib cache with the right ownership. Packages are installed in
# postCreate.sh, where the mounted pyproject.toml is available.
RUN install -d -o vscode -g vscode /home/vscode/.cache/matplotlib \
    && su vscode -c "python -m venv ${VENV_PATH}"

# Put the venv first on PATH so python, pip and pytest resolve to it in every shell.
ENV VIRTUAL_ENV=${VENV_PATH}
ENV PATH=${VENV_PATH}/bin:${PATH}
