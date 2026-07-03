# ======================================================================================
# SECURE MULTI-STAGE DOCKERFILE FOR WARREN BOT
#
# Base: Chainguard distroless Python (minimal CVEs, non-root by default, no shell in
# the runtime layer). All shell/pip work happens in the `-dev` build stages; the final
# runtime stage only COPYs the built virtualenv and runs as the nonroot user (65532),
# matching docker-compose.secure.yml.
# ======================================================================================

# ------------------------------------------------------------------------------------------
# BUILD STAGE — compile the project into a wheel
# ------------------------------------------------------------------------------------------
FROM chainguard/python:latest-dev AS builder

ARG WARREN_VERSION="0.1.0"

# Reproducible, quiet, no-bytecode builds
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VENV_IN_PROJECT=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Poetry pinned for reproducibility (root only for build tooling; stage is discarded)
USER root
RUN pip install --no-cache-dir poetry==2.1.0

WORKDIR /build

# Preserve the src/ layout so poetry-core discovers the warren_bot package correctly
COPY pyproject.toml poetry.lock README.md ./
COPY src/ ./src/

RUN poetry build --format wheel

# ------------------------------------------------------------------------------------------
# INSTALLER STAGE — install the wheel into a self-contained virtualenv
# ------------------------------------------------------------------------------------------
FROM chainguard/python:latest-dev AS installer

ARG WARREN_VERSION="0.1.0"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/app/.venv/bin:$PATH"

USER root
WORKDIR /app

# Build the venv and install only the wheel (no dev/build deps leak into runtime)
RUN python -m venv --copies .venv
COPY --from=builder /build/dist/warren_bot-${WARREN_VERSION}-py3-none-any.whl ./
RUN pip install --no-cache-dir ./warren_bot-${WARREN_VERSION}-py3-none-any.whl \
    && rm ./warren_bot-${WARREN_VERSION}-py3-none-any.whl \
    && python -c "import warren_bot; print('Warren Bot installed successfully')" \
    && chown -R nonroot:nonroot /app/.venv

# ------------------------------------------------------------------------------------------
# RUNTIME STAGE — distroless, non-root, no shell. Only COPY + metadata here.
# ------------------------------------------------------------------------------------------
FROM chainguard/python:latest AS runtime

ARG WARREN_VERSION="0.1.0"
ARG BUILD_DATE
ARG VCS_REF

LABEL maintainer="J.A. Simmons V <simmonsj@jasimmonsv.com>" \
      org.opencontainers.image.title="Warren Bot" \
      org.opencontainers.image.description="Secure Discord Investment Club Chatbot" \
      org.opencontainers.image.version="${WARREN_VERSION}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.vendor="Cypress Investment Club" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.url="https://github.com/CyIC/warren_bot" \
      org.opencontainers.image.documentation="https://github.com/CyIC/warren_bot/blob/main/README.md" \
      org.opencontainers.image.source="https://github.com/CyIC/warren_bot" \
      security.scan.policy="required" \
      security.non-root="true"

WORKDIR /app

# Copy the ready-to-run virtualenv, owned by the nonroot runtime user
COPY --from=installer --chown=nonroot:nonroot /app/.venv /app/.venv

# Minimal runtime environment. No PYTHONPATH: the venv on PATH resolves its own
# site-packages, so this stays correct even if the base Python minor version changes.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    HOME="/app"

# Run as the Chainguard nonroot user (uid 65532; matches docker-compose.secure.yml)
USER nonroot

# Exec form so it works without a shell in the distroless image
CMD ["python", "-m", "warren_bot"]

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD ["python", "-c", "import warren_bot, sys; sys.exit(0)"]

STOPSIGNAL SIGTERM
