#!/usr/bin/env bash
# Throwaway Postgres (pgvector) and Redis for `make test`, until Compose lands (E0-07).
# The images MUST match the service containers in .github/workflows/ci.yml (tag and digest).
# Usage: test-services.sh up|down. Ports bind to 127.0.0.1 only; credentials are test-only.
set -euo pipefail

PG_IMAGE="pgvector/pgvector:0.8.7-pg16@sha256:7b822b0aac60967beb1ea5e576b8602c94c300a157d187f385ae3e0da199b90a"
REDIS_IMAGE="redis:8.10.2-alpine@sha256:9f8d2d789b9a1d1e3f283f979aa9cbf393373806472e1ccd460e2f9c869b833b"
PG_NAME="capsule-test-postgres"
REDIS_NAME="capsule-test-redis"
PG_PORT="${CAPSULE_TEST_PG_PORT:-55432}"
REDIS_PORT="${CAPSULE_TEST_REDIS_PORT:-56379}"

down() {
  docker rm --force "$PG_NAME" "$REDIS_NAME" >/dev/null 2>&1 || true
}

wait_for() { # name, command...
  local name=$1
  shift
  for _ in $(seq 1 60); do
    if "$@" >/dev/null 2>&1; then return 0; fi
    sleep 1
  done
  echo "test-services: $name did not become ready in 60 s" >&2
  docker logs --tail 20 "$name" >&2 || true
  return 1
}

up() {
  down
  docker run --detach --rm --name "$PG_NAME" \
    --env POSTGRES_USER=capsule --env POSTGRES_PASSWORD=capsule --env POSTGRES_DB=capsule_test \
    --publish "127.0.0.1:$PG_PORT:5432" "$PG_IMAGE" >/dev/null
  docker run --detach --rm --name "$REDIS_NAME" \
    --publish "127.0.0.1:$REDIS_PORT:6379" "$REDIS_IMAGE" >/dev/null
  # -h 127.0.0.1: wait for the real server, not the init-time one on the Unix socket.
  wait_for "$PG_NAME" docker exec "$PG_NAME" pg_isready -h 127.0.0.1 -U capsule -d capsule_test
  wait_for "$REDIS_NAME" docker exec "$REDIS_NAME" redis-cli ping
  echo "test-services: postgres on 127.0.0.1:$PG_PORT, redis on 127.0.0.1:$REDIS_PORT"
}

case "${1:-}" in
  up) up ;;
  down) down ;;
  *) echo "usage: $0 up|down" >&2; exit 2 ;;
esac
