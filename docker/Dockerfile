# syntax=docker/dockerfile:1.7
# =============================================================================
# NIGHTWATCH - Production Container Image
# =============================================================================
# Task: DEP-001
# Pairs with: docker/docker-compose.prod.yml (service: nightwatch)
#
# Build (from repo root):
#   docker compose -f docker/docker-compose.prod.yml build nightwatch
# Smoke test:
#   docker run --rm <image> nightwatch --version
#
# Notes:
#   * Multi-stage: `builder` compiles wheels into a venv; `runtime` copies the
#     venv into a slim base. Compiler toolchain stays out of the final image.
#   * Voice deps (faster-whisper, piper-tts, sounddevice) are intentionally
#     EXCLUDED — voice runs in the `wyoming-satellite` sibling container.
#   * Runtime stage runs as a non-root `nightwatch` user (UID/GID 10001).
#     The compose file still sets `privileged: true` for /dev/* hardware
#     access; that is a runtime concern, not a build concern.
# =============================================================================

ARG PYTHON_VERSION=3.11.10
ARG DEBIAN_RELEASE=bookworm

# -----------------------------------------------------------------------------
# Stage 1: builder
# -----------------------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim-${DEBIAN_RELEASE} AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

# Build-time system deps: compilers for any C extensions in services/* deps
# (skyfield/pyserial are pure-Python wheels, but aiohttp ships sdist on some
# arches and pyindi-client needs libindi headers; keep build-essential here).
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        libffi-dev \
        libssl-dev \
        git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create the venv that we'll copy into the runtime stage.
RUN python -m venv "${VIRTUAL_ENV}" \
    && pip install --upgrade pip setuptools wheel

WORKDIR /build

# Pre-install runtime dependencies (core + services extras only — NO voice).
# Pinning these in the Dockerfile rather than pulling pyproject extras keeps
# this layer cache-stable across source edits; pyproject is the source of truth
# (see [project].dependencies and [project.optional-dependencies].services).
RUN pip install \
        "pydantic>=2.0" \
        "PyYAML>=6.0" \
        "skyfield>=1.48" \
        "aiohttp>=3.9" \
        "pyserial>=3.5"

# Copy project metadata + source for the final wheel install.
COPY pyproject.toml README.md ./
COPY nightwatch/ ./nightwatch/
COPY services/ ./services/
COPY voice/ ./voice/

# Install the project (no extras — runtime deps already present above).
# `--no-deps` keeps the wheel layer small and prevents accidental re-resolution.
RUN pip install --no-deps .

# -----------------------------------------------------------------------------
# Stage 2: runtime
# -----------------------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim-${DEBIAN_RELEASE} AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    NIGHTWATCH_CONFIG=/config/nightwatch.yaml \
    NIGHTWATCH_LOG_LEVEL=INFO

# Runtime system deps:
#   * curl     — HEALTHCHECK probe + general ops debugging
#   * tini     — PID 1 reaper so SIGTERM propagates cleanly to nightwatch
#   * tzdata   — TZ env var resolution (compose passes TIMEZONE)
#   * ca-certificates — outbound HTTPS (weather APIs, ephemeris downloads)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        tini \
        tzdata \
        ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Non-root user. Fixed UID/GID so bind-mount permissions are reproducible.
ARG NIGHTWATCH_UID=10001
ARG NIGHTWATCH_GID=10001
RUN groupadd --system --gid "${NIGHTWATCH_GID}" nightwatch \
    && useradd --system --uid "${NIGHTWATCH_UID}" --gid nightwatch \
        --home-dir /home/nightwatch --create-home --shell /usr/sbin/nologin \
        nightwatch

# Pull the prebuilt venv from the builder stage.
COPY --from=builder --chown=nightwatch:nightwatch /opt/venv /opt/venv

# Create the bind-mount target dirs so they exist even when the host-side
# directories are empty (and so they're owned by the runtime user).
RUN mkdir -p /config /data /logs \
    && chown -R nightwatch:nightwatch /config /data /logs

WORKDIR /home/nightwatch
USER nightwatch

EXPOSE 8080 9999

# Slow first-boot grace: orchestrator initializes services serially before
# the health endpoint comes online. 60s start_period keeps the first probe
# from flapping the container into unhealthy during normal cold-start.
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl --fail --silent --show-error http://localhost:8080/health || exit 1

# tini reaps zombies and forwards signals so `docker stop` is graceful.
# ENTRYPOINT intentionally does NOT include `nightwatch` so that smoke checks
# like `docker run --rm <image> nightwatch --version` (which replace CMD) work
# as written in the DEP-001 acceptance criteria. Compose runs default CMD.
ENTRYPOINT ["/usr/bin/tini", "--"]

# Default command boots the orchestrator with the configured /config volume.
# Override at `docker run` to invoke other CLI surfaces (e.g. `nightwatch --version`).
CMD ["nightwatch", "--config", "/config/nightwatch.yaml"]
