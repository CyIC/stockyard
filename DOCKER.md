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

`.do/app.yml` (and the deploy-button spec `.do/deploy.yaml`) builds the Dockerfile and runs Warren as a
**worker** (it has no HTTP port). On App Platform:

- Set `DISCORD_TOKEN` as an encrypted (SECRET) environment variable on the app; the build fails to start
  without it.
- `STOCKYARD_DATA_DIR` is `/tmp/stockyard`, because App Platform has no volumes and the non-root user cannot
  create `/app/data`. The cache is lost on each restart, which only costs a fresh fetch.
- `app.yml` deploys on every push to `main`.
- The spec in the repository does not change a running app by itself; apply it with
  `doctl apps update <app-id> --spec .do/app.yml` or in the DigitalOcean dashboard.

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
