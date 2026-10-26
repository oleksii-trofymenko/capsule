#!/usr/bin/env bash
# Keeps the repo-root .env in step with .env.example:
# - first run: creates .env from .env.example with a fresh random value for every `change-me`;
# - later runs: appends any `change-me` variable that .env lacks (new secrets added by an
#   upgrade), with a fresh random value; existing values are never changed;
# - refuses to continue while any `change-me` value is left.
# Writes go to a temp file in the same folder and are moved into place (atomic, mode 600).
# Usage: env-init.sh <repo root>. Works in Git Bash and on Linux.
set -euo pipefail

root=${1:?usage: env-init.sh <repo root>}
env_file="$root/.env"
example="$root/.env.example"

random_hex() { od -An -tx1 -N24 /dev/urandom | tr -d ' \n'; }

umask 077
tmp=$(mktemp "$root/.env.tmp.XXXXXX")
trap 'rm -f "$tmp"' EXIT

if [ ! -f "$env_file" ]; then
  while IFS= read -r line || [ -n "$line" ]; do
    if [[ $line =~ ^([A-Z0-9_]+)=change-me$ ]]; then
      printf '%s=%s\n' "${BASH_REMATCH[1]}" "$(random_hex)"
    else
      printf '%s\n' "$line"
    fi
  done <"$example" >"$tmp"
  mv "$tmp" "$env_file"
  echo "env-init: created .env with generated secrets (never commit it)"
else
  cp "$env_file" "$tmp"
  added=()
  while IFS= read -r line || [ -n "$line" ]; do
    if [[ $line =~ ^([A-Z0-9_]+)=change-me$ ]] && ! grep -q "^${BASH_REMATCH[1]}=" "$env_file"; then
      [ -z "$(tail -c1 "$tmp")" ] || echo >>"$tmp"
      printf '%s=%s\n' "${BASH_REMATCH[1]}" "$(random_hex)" >>"$tmp"
      added+=("${BASH_REMATCH[1]}")
    fi
  done <"$example"
  if [ "${#added[@]}" -gt 0 ]; then
    mv "$tmp" "$env_file"
    echo "env-init: added to .env with generated values: ${added[*]}"
  fi
fi

if grep -Eq '^[A-Z0-9_]+=.*change-me' "$env_file"; then
  echo "env-init: .env still has change-me values; set them or delete .env to regenerate" >&2
  exit 1
fi
