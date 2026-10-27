#!/usr/bin/env bash
# Keeps the repo-root .env in step with .env.example and creates the file secrets (ADR-015):
# - first run: creates .env from .env.example with a fresh random value for every `change-me`;
# - later runs: appends any `change-me` variable that .env lacks (new secrets added by an
#   upgrade), with a fresh random value; existing values are never changed;
# - creates secrets/jwt_signing_keys (`<UTC date>=<32 random bytes as hex>`) if missing and never
#   overwrites it; prints file names, never values;
# - applies the file layout on every run (skipped with `generate-only`, which CI uses to mask the
#   values before the layout makes them unreadable):
#     Git Bash: secrets/ and .env readable only by the current user (SID) and SYSTEM (icacls);
#     Linux:    secrets/ 0700, each secret file root:<consumer GID> 0440 (root or sudo);
# - refuses to continue while any `change-me` value is left.
# Writes go to a temp file in the same folder and are moved into place (atomic, mode 600).
# Every failure exits non-zero, which stops `make up`. Runbook: docs/runbooks/compose-stack.md.
# Usage: env-init.sh <repo root> [generate-only]. Works in Git Bash and on Linux.
set -euo pipefail

root=${1:?usage: env-init.sh <repo root> [generate-only]}
mode=${2:-}
case $mode in
  "" | generate-only) ;;
  *) echo "usage: env-init.sh <repo root> [generate-only]" >&2; exit 2 ;;
esac
env_file="$root/.env"
example="$root/.env.example"
secrets_dir="$root/secrets"
jwt_file="$secrets_dir/jwt_signing_keys"
# GID of the api image's user (apps/api/Dockerfile). A change is a change to ADR-015's inventory.
API_GID=10001

die() { echo "env-init: $*" >&2; exit 1; }
random_hex() { od -An -tx1 -N"$1" /dev/urandom | tr -d ' \n'; }

umask 077
ktmp=
tmp=$(mktemp "$root/.env.tmp.XXXXXX")
trap 'rm -f "$tmp" ${ktmp:+"$ktmp"}' EXIT

if [ ! -f "$env_file" ]; then
  while IFS= read -r line || [ -n "$line" ]; do
    if [[ $line =~ ^([A-Z0-9_]+)=change-me$ ]]; then
      printf '%s=%s\n' "${BASH_REMATCH[1]}" "$(random_hex 24)"
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
      printf '%s=%s\n' "${BASH_REMATCH[1]}" "$(random_hex 24)" >>"$tmp"
      added+=("${BASH_REMATCH[1]}")
    fi
  done <"$example"
  if [ "${#added[@]}" -gt 0 ]; then
    mv "$tmp" "$env_file"
    echo "env-init: added to .env with generated values: ${added[*]}"
  fi
fi

# JWT signing keys (ADR-014, ADR-015): one `kid=hexkey` line per key; the first line signs.
mkdir -p "$secrets_dir"
if [ -e "$jwt_file" ] || [ -L "$jwt_file" ]; then
  # Docker creates a folder at a bind-mount source that is missing when a container starts.
  [ -f "$jwt_file" ] && [ ! -L "$jwt_file" ] ||
    die "secrets/jwt_signing_keys exists but is not a regular file (Docker creates a folder there when the stack starts without it). If it is an empty folder: rmdir \"$jwt_file\", then make up again"
else
  ktmp=$(mktemp "$secrets_dir/.jwt_signing_keys.tmp.XXXXXX")
  printf '%s=%s\n' "$(date -u +%F)" "$(random_hex 32)" >"$ktmp"
  mv "$ktmp" "$jwt_file"
  ktmp=
  echo "env-init: created secrets/jwt_signing_keys (never commit it)"
fi

layout_windows() {
  # Stops Git Bash from turning `/grant:r`, `/user` and `*S-1-...` into Windows paths.
  export MSYS2_ARG_CONV_EXCL='*'
  local sid dir envw
  # Git Bash's own `whoami` prints only the name; a name could also match a same-named group.
  sid=$("$(cygpath -u "$SYSTEMROOT")/System32/whoami.exe" /user /fo csv /nh | tr -d '\r"' | cut -d, -f2) ||
    die "whoami.exe /user failed; cannot restrict secrets/"
  [[ $sid =~ ^S-1-5-21-[0-9-]+$ ]] || die "unexpected user SID from whoami.exe /user: '$sid'"
  dir=$(cygpath -w "$secrets_dir")
  envw=$(cygpath -w "$env_file")
  # Inheritance removed; only the user and SYSTEM (S-1-5-18), inherited by every file inside.
  icacls "$dir" /inheritance:r /grant:r "*$sid:(OI)(CI)F" /grant:r "*S-1-5-18:(OI)(CI)F" >/dev/null ||
    die "icacls on secrets/ failed"
  # Git Bash mkdir adds an explicit Administrators (S-1-5-32-544) entry.
  icacls "$dir" /remove:g "*S-1-5-32-544" >/dev/null || die "icacls /remove:g Administrators on secrets/ failed"
  # Files take plain F: inheritance flags apply to folders only.
  icacls "$envw" /inheritance:r /grant:r "*$sid:F" /grant:r "*S-1-5-18:F" >/dev/null ||
    die "icacls on .env failed"
  icacls "$envw" /remove:g "*S-1-5-32-544" >/dev/null || die "icacls /remove:g Administrators on .env failed"
  echo "env-init: secrets/ and .env restricted to the current user and SYSTEM"
}

layout_linux() {
  chmod 700 "$secrets_dir" || die "chmod 700 secrets/ failed (is it owned by someone else?)"
  # Already right: no sudo prompt on every make up.
  [ "$(stat -c '%u:%g %a' "$jwt_file")" != "0:$API_GID 440" ] || return 0
  if [ "$(id -u)" = 0 ]; then
    chown "root:$API_GID" "$jwt_file" || die "chown root:$API_GID secrets/jwt_signing_keys failed"
    chmod 0440 "$jwt_file" || die "chmod 0440 secrets/jwt_signing_keys failed"
  elif command -v sudo >/dev/null 2>&1; then
    echo "env-init: setting secrets/jwt_signing_keys to root:$API_GID 0440 (sudo)"
    sudo chown "root:$API_GID" "$jwt_file" || die "sudo chown root:$API_GID secrets/jwt_signing_keys failed"
    sudo chmod 0440 "$jwt_file" || die "sudo chmod 0440 secrets/jwt_signing_keys failed"
  else
    die "secrets/jwt_signing_keys must be root:$API_GID mode 0440; that needs sudo (or root), which is missing. Run as root: chown root:$API_GID \"$jwt_file\" && chmod 0440 \"$jwt_file\""
  fi
}

if [ "$mode" != generate-only ]; then
  case $(uname -s) in
    MINGW* | MSYS*) layout_windows ;;
    Linux) layout_linux ;;
    *) die "no secrets layout for $(uname -s); supported: Git Bash on Windows, Linux (ADR-015)" ;;
  esac
fi

if grep -Eq '^[A-Z0-9_]+=.*change-me' "$env_file"; then
  echo "env-init: .env still has change-me values; set them or delete .env to regenerate" >&2
  exit 1
fi
