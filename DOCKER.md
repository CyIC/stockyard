# Docker Deployment Guide for Stockyard

This guide covers building the Stockyard image and running Warren, the Discord bot, in a container, either
self-hosted with Docker Compose or on DigitalOcean App Platform. The same image also runs the `stockyard` CLI.

The image is Chainguard distroless Python: non-root (uid 65532), no shell, and its entry point is the
virtualenv's Python, so the command is the arguments to `python` (the default is `-m stockyard.bot`).

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+ (optional, for easier deployment)
- A Discord bot token (for Warren; the CLI needs none)

## Quick Start with Docker Compose (Recommended)

1. **Clone the repository**
   ```bash
   git clone https://github.com/CyIC/stockyard.git
   cd stockyard
   ```

2. **Set up environment variables**
   ```bash
   cp .env.template .env
   # Edit .env and set DISCORD_TOKEN
   ```

3. **Run with Docker Compose**
   ```bash
   docker compose up -d
   ```
   For the hardened configuration (read-only root filesystem, dropped capabilities, the token as a Docker
   secret in `secrets/discord_token.txt`, see `secrets/README.md`) use `docker compose -f docker-compose.secure.yml up -d`.

4. **Check logs**
   ```bash
   docker compose logs -f warren
   ```

## Manual Docker Build and Run

```bash
docker build -t stockyard:latest .

docker run -d \
  --name warren \
  --restart unless-stopped \
  -e DISCORD_TOKEN="your_discord_bot_token_here" \
  -v $(pwd)/data:/app/data \
  stockyard:latest
```

### Running the CLI in the container

```bash
docker run --rm stockyard:latest -m stockyard report MSFT
docker run --rm stockyard:latest -m stockyard risk-reward MSFT --json
docker run --rm -v $(pwd)/charts:/charts stockyard:latest -m stockyard trend MSFT --charts /charts
```

## Configuration

### Environment Variables

| Variable             | Required          | Default (image) | Description                                                      |
|----------------------|-------------------|-----------------|------------------------------------------------------------------|
| `DISCORD_TOKEN`      | Yes, or the file  | -               | Discord bot token                                                |
| `DISCORD_TOKEN_FILE` | Yes, or the token | -               | Path to a file holding the token, e.g. `/run/secrets/discord_token` |
| `STOCKYARD_DATA_DIR` | No                | `/app/data`     | Writable directory for the same-day market-data cache            |
| `LOGGING_LEVEL`      | No                | `INFO`          | `DEBUG`, `INFO`, `WARNING`, `ERROR` or `CRITICAL`                |

The README's [Configuration](README.md#configuration) section lists every variable, including those kept in
`.env.template` for deployment tooling but not read by Stockyard.

### Volume Mounts

| Host Path | Container Path | Purpose                                                                 |
|-----------|----------------|-------------------------------------------------------------------------|
| `./data`  | `/app/data`    | Same-day cache of Yahoo Finance responses (`cache/<TICKER>.json`); safe to delete |

Logs go to stderr as JSON, so read them with `docker logs`. The compose files also mount or `tmpfs` an
`/app/logs` directory, which v1 does not write to.

### Health Check

The Dockerfile and both compose files check that the `stockyard` package imports in the container's
virtualenv. A test (`src/tests/test_deployment.py`) runs each check so they cannot drift.

## DigitalOcean App Platform

Warren runs on App Platform as a **worker** (it has no HTTP port), deployed by GitHub Actions whenever a
GitHub release is published (`.github/workflows/release.yml`):

1. **test**: `tox -e flake8,pylint,py313`, the same gate as CI.
2. **build**: builds the Dockerfile once (linux/amd64) and pushes `ghcr.io/cyic/stockyard:<release tag>` and
   `:latest`.
3. **deploy**: `digitalocean/app_action` applies `.do/app.yml` with that image's **digest**, so App Platform
   runs exactly the image that was tested and never builds anything itself. The app is created on the first
   deploy.

### One-time setup

1. **DigitalOcean API token**: in DigitalOcean, create a personal access token that can create and update apps.
2. **GitHub environment**: in CyIC/stockyard, open **Settings → Environments → New environment**, name it
   `production`, and add two secrets:
   - `DIGITALOCEAN_ACCESS_TOKEN`: the token from step 1
   - `DISCORD_TOKEN`: Warren's bot token (passed to App Platform, which stores it encrypted)

   Optionally add yourself as a required reviewer so every deploy waits for your approval.
3. **First release**: publish a release (e.g. `v1.0.1`). After the image is pushed for the first time, check
   that the package at `github.com/orgs/CyIC/packages` is **public**. App Platform pulls it without
   credentials, so a private package makes the deploy fail.

### On App Platform

- Size `apps-s-1vcpu-0.5gb` (1 shared vCPU, 512 MiB), one instance.
- `STOCKYARD_DATA_DIR` is `/tmp/stockyard`: App Platform has no volumes, so the same-day cache starts empty
  after each deploy or restart, which only costs a fresh fetch.
- Logs are under the app's **Runtime Logs** in the DigitalOcean dashboard.
- **Rollback**: re-run the deploy job of an earlier release in GitHub Actions; it redeploys that release's
  image by digest.

`.do/deploy.yaml` is a separate spec that builds the Dockerfile from source; it is not used by the pipeline.

## Management Commands

```bash
# Logs
docker compose logs -f warren          # or: docker logs -f warren

# Stop
docker compose down                    # or: docker stop warren && docker rm warren

# Update
git pull
docker compose build && docker compose up -d
```

The runtime image has no shell, so `docker exec ... /bin/bash` does not work. To debug, raise
`LOGGING_LEVEL=DEBUG` and restart, or run a one-off command such as
`docker run --rm stockyard:latest -m stockyard past-eps MSFT -v`.

## Security Considerations

1. **Secrets**: `.env` and everything in `secrets/` except its README are gitignored and kept out of the
   build context; prefer `DISCORD_TOKEN_FILE` with a Docker secret.
2. **Non-root**: The image runs as uid 65532 with no shell.
3. **Network**: Warren makes outbound connections to Discord and Yahoo Finance only; it exposes no ports.
4. **Updates**: Rebuild regularly to pick up base-image and dependency fixes; pin base images by digest
   (see the Dockerfile's `PYTHON_DEV_IMAGE` / `PYTHON_RUNTIME_IMAGE` build arguments) for reproducible builds.

## Troubleshooting

1. **Warren exits at start-up saying no token was found**: set `DISCORD_TOKEN`, or `DISCORD_TOKEN_FILE`
   pointing at a readable file.
2. **Permission errors writing the cache**: the data directory must be writable by the container's user
   (uid 1000 in `docker-compose.yml`, 65532 in the image and `docker-compose.secure.yml`), e.g.
   `sudo chown 65532:65532 data`, or point `STOCKYARD_DATA_DIR` at a writable path.
3. **Lookups fail with an upstream error**: Yahoo Finance is unreachable or rate-limiting; try again later.
4. **Memory issues**: adjust the resource limits in the compose file; monitor with `docker stats warren`.

## Multi-Architecture Support

```bash
docker buildx build --platform linux/amd64,linux/arm64 -t stockyard:latest .
```
