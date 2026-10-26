#!/usr/bin/env bash
# Fails when an image pin shared between CI and the Compose stack drifts (ADR-016, ADR-019):
# - postgres and redis service images (tag and digest) in ci.yml and compose.base.yml;
# - the uv version in ci.yml (UV_VERSION) and the uv image in apps/api/Dockerfile.
# Run from the repo root (CI lint job, or by hand). Bump all files in the same PR.
set -euo pipefail

ci=.github/workflows/ci.yml
compose=infra/compose/compose.base.yml
dockerfile=apps/api/Dockerfile
status=0

images() { # file, image name -> every pinned reference to that image, sorted and unique
  grep -Eo "image: *$2:[^[:space:]]+" "$1" | sed -E 's/^image: *//' | sort -u
}

for name in pgvector/pgvector redis; do
  in_ci=$(images "$ci" "$name")
  in_compose=$(images "$compose" "$name")
  if [ -z "$in_ci" ] || [ "$in_ci" != "$in_compose" ] || [ "$(wc -l <<<"$in_ci")" -ne 1 ]; then
    printf 'check-pins: %s differs\n  %s: %s\n  %s: %s\n' \
      "$name" "$ci" "${in_ci:-<missing>}" "$compose" "${in_compose:-<missing>}" >&2
    status=1
  elif [[ $in_ci != *@sha256:* ]]; then
    echo "check-pins: $name is not pinned by digest: $in_ci" >&2
    status=1
  else
    echo "check-pins: $name ok ($in_ci)"
  fi
done

uv_ci=$(sed -nE 's/^ *UV_VERSION: *"?([^"[:space:]]+)"?.*/\1/p' "$ci")
uv_docker=$(sed -nE 's#^ARG UV_IMAGE=ghcr.io/astral-sh/uv:([^@]+)@sha256:.*#\1#p' "$dockerfile")
if [ -z "$uv_ci" ] || [ "$uv_ci" != "$uv_docker" ]; then
  echo "check-pins: uv differs: $ci=${uv_ci:-<missing>} $dockerfile=${uv_docker:-<missing>}" >&2
  status=1
else
  echo "check-pins: uv ok ($uv_ci)"
fi

exit "$status"
