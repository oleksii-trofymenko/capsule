# Capsule API image (E0-07). Build context: apps/api. Run by infra/compose/compose.base.yml.
# Pins: tag for humans, digest for the build; both at least 7 days old (ADR-018, ADR-019).
# UV_IMAGE must match UV_VERSION in .github/workflows/ci.yml (checked by infra/compose/check-pins.sh).
ARG PYTHON_IMAGE=python:3.13.15-slim-trixie@sha256:7c61056e61ac89e852de05f3dc6fa51a6dd2181797bceed46aa725dd7cb2cd3b
ARG UV_IMAGE=ghcr.io/astral-sh/uv:0.13.1@sha256:4a1f3666816dafadd20ceb71eac9a7d56d7ef30279f7d64048519ab901ada336

FROM ${UV_IMAGE} AS uv

FROM ${PYTHON_IMAGE} AS build
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PYTHON=/usr/local/bin/python3.13 \
    UV_PROJECT_ENVIRONMENT=/app/.venv
WORKDIR /app
# Runtime dependencies only, exactly as locked; the dev group (tests, mypy) never ships (ADR-020).
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project
COPY . .
RUN python -m compileall -q main.py core

FROM ${PYTHON_IMAGE} AS runtime
ENV PATH=/app/.venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
RUN groupadd --system --gid 10001 capsule \
    && useradd --system --uid 10001 --gid capsule --no-create-home --shell /usr/sbin/nologin capsule
WORKDIR /app
# Root owns the code; the app user can read it but not change it.
COPY --from=build /app /app
USER 10001:10001
EXPOSE 8000
# Liveness only (/v1/health). /v1/ready may report a dependency as failing for up to ~10 s after
# it recovers from a hang (E0-06), so it never drives restarts.
HEALTHCHECK --interval=10s --timeout=3s --start-period=30s --start-interval=1s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/v1/health', timeout=2)"]
# ADR-021. RequestContextMiddleware writes the access line; uvicorn's would add client IPs.
CMD ["uvicorn", "main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
