#!/usr/bin/env bash
# Creates the repo-root .env from .env.example on first run, with a fresh random value for every
# `change-me` secret, and refuses to continue while any `change-me` value is left.
# Usage: env-init.sh <repo root>. Works in Git Bash and on Linux.
set -euo pipefail

root=${1:?usage: env-init.sh <repo root>}
env_file="$root/.env"
example="$root/.env.example"

random_hex() { od -An -tx1 -N24 /dev/urandom | tr -d ' \n'; }

if [ ! -f "$env_file" ]; then
  umask 077
  while IFS= read -r line || [ -n "$line" ]; do
    if [[ $line =~ ^([A-Z0-9_]+)=change-me$ ]]; then
      printf '%s=%s\n' "${BASH_REMATCH[1]}" "$(random_hex)"
    else
      printf '%s\n' "$line"
    fi
  done <"$example" >"$env_file"
  echo "env-init: created .env with generated secrets (never commit it)"
fi

if grep -Eq '^[A-Z0-9_]+=.*change-me' "$env_file"; then
  echo "env-init: .env still has change-me values; set them or delete .env to regenerate" >&2
  exit 1
fi
