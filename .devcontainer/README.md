# Dev container

Reopen the repo in the container (VS Code: **Dev Containers: Reopen in Container**). First
creation installs the toolchain and takes a few minutes; later starts are immediate.

```bash
pytest src/tests/ -q     # suite
tox                      # full gate: clean, flake8, pylint, py313, coverage-report
tox -e flake8 -e pylint  # lint only
pip-audit                # dependency vulnerabilities
```

## Things that are not obvious

**Installed versions can differ from `poetry.lock`.** `postCreate.sh` installs with pip, not
`poetry install`, to match the production image, which also resolves with pip. pip picks the
newest versions `pyproject.toml` allows, so they can run ahead of the lock. The lock itself is
current as of v1.0 and installs cleanly with `poetry install` on Python 3.13.

**`.tox/` is a named volume, not the host directory.** The host is Windows and its `.tox/`
contains Windows launchers Linux cannot execute. The volume shadows it, so the host copy is
untouched and container I/O is native speed. Coverage output still lands at the usual
`.tox/htmlcov-py313/`, but that path is inside the volume — open reports from the container,
not from Windows Explorer. `docker volume rm cyicbot-tox` forces a clean rebuild.

**The venv lives at `/home/vscode/.venv`, outside the workspace.** Keeps it off the Windows
bind mount (slow over many small files) and prevents collisions with the host's own `venv/`.
It is already first on `PATH`.

**`gpg` uses `pinentry-curses`.** Commit signing prompts in the terminal. Without a TTY
pinentry, `gpg` tries to open a GUI dialog it cannot draw and fails with
`signing failed: Timeout` — the failure this repo hits when `commit.gpgsign` is true and no
graphical agent is reachable. Git pushes still need your SSH key: Dev Containers forwards the
host's SSH agent, so start one on the host (`ssh-agent` + `ssh-add`) before opening the
container, or push from the host.

**Warren needs `DISCORD_TOKEN` in the environment.** Stockyard does not read `.env` itself (only Docker
Compose does), so `export DISCORD_TOKEN=...` in the terminal before `warren` or `python -m stockyard.bot`. The
CLI (`stockyard report MSFT`) and the tests need no token. `STOCKYARD_DATA_DIR` is preset to `./data` (the
same-day cache), and `MPLBACKEND=Agg` keeps chart rendering headless.

**Docker is the host daemon.** `docker` and `docker compose` target the host, so images you
build are visible on the host and `scripts/build-secure.sh` works. This is host-daemon
access, which is effectively root on the host.
