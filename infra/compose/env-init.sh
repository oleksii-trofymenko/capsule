#!/usr/bin/env bash
# Keeps the repo-root .env in step with .env.example and creates the file secrets (ADR-015):
# - first run: creates .env from .env.example with a fresh random value for every `change-me`;
# - later runs: appends any `change-me` variable that .env lacks (new secrets added by an
#   upgrade), with a fresh random value; existing values are never changed;
# - creates secrets/jwt_signing_keys (`<UTC date>=<32 random bytes as hex>`) if missing and never
#   overwrites it; prints file names, never values;
# - applies the file layout on every run (skipped with `generate-only`, which CI uses to mask the
#   values before the layout makes them unreadable). The folder is restricted before a key file is
#   written, so a new key is born restricted (Windows: a key created in a run that then fails is removed).
#   Windows: secrets/ is restricted first; the .env temp file is created inside it, restricted and
#   checked before any secret is written to it. Unsupported systems stop before .env is created.
#     Git Bash: secrets/ and .env readable only by the current user (SID) and SYSTEM (icacls),
#               then verified from the SDDL (SIDs, not localised names);
#     Linux:    secrets/ 0700, each secret file root:<consumer GID> 0440 (root or sudo);
# - refuses to continue while any `change-me` value is left.
# Writes go to a temp file on the same volume and are moved into place (atomic, mode 600).
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
# hex_value <bytes> <var>: sets <var> to <bytes> random bytes as lowercase hex, checked before use
# (a glob, not =~, so the caller's BASH_REMATCH survives).
hex_value() {
  local v
  v=$(random_hex "$1")
  [[ ${#v} -eq $(($1 * 2)) && $v != *[!0-9a-f]* ]] ||
    die "random value is not $(($1 * 2)) hex digits (od or /dev/urandom failed)"
  printf -v "$2" '%s' "$v"
}

umask 077
ktmp=
tmp=
aclout=
created_key=
layout=
# A key created in this run is removed if the Windows layout then fails (its ACL is unverified).
# On Linux it is born 0600 under umask 077 and kept, so the printed root commands still apply.
cleanup() {
  local rc=$?
  rm -f ${tmp:+"$tmp"} ${ktmp:+"$ktmp"} ${aclout:+"$aclout"}
  if [ "$rc" -ne 0 ] && [ -n "$created_key" ] && [ "$layout" = windows ]; then
    rm -f "$jwt_file" && echo "env-init: removed secrets/jwt_signing_keys created in this failed run" >&2
  fi
}
trap cleanup EXIT

# --- Windows (Git Bash) layout ---
sid=
# acl_check <path>: the DACL may name only the user SID and SYSTEM. Read as SDDL (`icacls /save`),
# which uses SIDs and fixed aliases (SY = S-1-5-18) whatever the display language.
acl_check() {
  local sddl ace trustee n=0 name=${1#"$root"/}
  # Global, so the EXIT trap removes it if anything below fails.
  aclout=$(mktemp "$root/.acl.tmp.XXXXXX")
  icacls "$(cygpath -w "$1")" /save "$(cygpath -w "$aclout")" /q >/dev/null || die "icacls /save on $name failed"
  sddl=$(tr -d '\000\r' <"$aclout" | sed -n 2p)
  rm -f "$aclout"
  aclout=
  # The whole line must be a DACL of plain allow (A) or deny (D) entries: no other ACE type, no
  # nested parentheses (conditional ACEs), nothing after the last entry. Anything else fails closed.
  local shape='^D:[A-Z]*(\((A|D);[^()]*\))+$'
  [[ $sddl =~ $shape ]] || die "unexpected access list format for $name (only allow/deny entries are accepted)"
  while IFS= read -r ace; do
    trustee=$(cut -d';' -f6 <<<"$ace")
    case $trustee in
      SY | S-1-5-18 | "$sid") n=$((n + 1)) ;;
      *) die "$name also grants access to '$trustee'; expected only the current user and SYSTEM" ;;
    esac
  done < <(grep -o '([^)]*)' <<<"${sddl#D:}" | tr -d '()')
  [ "$n" -gt 0 ] || die "$name has an empty access list"
}

# windows_sid: sets $sid to the current user's SID.
windows_sid() {
  # Stops Git Bash from turning `/grant:r`, `/user` and `*S-1-...` into Windows paths. Paths are
  # passed through `cygpath -w` instead.
  export MSYS2_ARG_CONV_EXCL='*'
  # Git Bash's own `whoami` prints only the name; a name could also match a same-named group.
  sid=$("$(cygpath -u "$SYSTEMROOT")/System32/whoami.exe" /user /fo csv /nh | tr -d '\r"' | cut -d, -f2) ||
    die "whoami.exe /user failed; cannot restrict .env and secrets/"
  # Local and Microsoft accounts only; an Entra ID account (S-1-12-1-...) needs a change here.
  [[ $sid =~ ^S-1-5-21-[0-9-]+$ ]] || die "unexpected user SID from whoami.exe /user: '$sid'"
}

# restrict_file <path>: inheritance removed, only the user and SYSTEM. Files take plain F:
# inheritance flags apply to folders only.
restrict_file() {
  local w name=${1#"$root"/}
  w=$(cygpath -w "$1")
  icacls "$w" /inheritance:r /grant:r "*$sid:F" /grant:r "*S-1-5-18:F" >/dev/null ||
    die "icacls on $name failed"
  icacls "$w" /remove:g "*S-1-5-32-544" >/dev/null || die "icacls /remove:g Administrators on $name failed"
}

layout_windows_dir() {
  local dir
  dir=$(cygpath -w "$secrets_dir")
  # Inheritance removed; only the user and SYSTEM (S-1-5-18), inherited by every file inside.
  icacls "$dir" /inheritance:r /grant:r "*$sid:(OI)(CI)F" /grant:r "*S-1-5-18:(OI)(CI)F" >/dev/null ||
    die "icacls on secrets/ failed"
  # Git Bash mkdir adds an explicit Administrators (S-1-5-32-544) entry.
  icacls "$dir" /remove:g "*S-1-5-32-544" >/dev/null || die "icacls /remove:g Administrators on secrets/ failed"
}

layout_windows_files() {
  local f
  # Each file keeps only what it inherits from secrets/ (drops any explicit entry). A .env temp
  # file left by a killed run keeps its own restricted list; the check below still covers it.
  for f in "$secrets_dir"/* "$secrets_dir"/.[!.]*; do
    [ -e "$f" ] || continue
    case ${f##*/} in .env.tmp.*) continue ;; esac
    icacls "$(cygpath -w "$f")" /reset >/dev/null || die "icacls /reset on ${f#"$root"/} failed"
  done
  # Re-applied on every run: also covers a .env copied in by hand.
  restrict_file "$env_file"
  acl_check "$secrets_dir"
  for f in "$secrets_dir"/* "$secrets_dir"/.[!.]*; do
    [ -e "$f" ] || continue
    acl_check "$f"
  done
  acl_check "$env_file"
  echo "env-init: secrets/ and .env restricted to the current user and SYSTEM (checked)"
}

# --- Linux layout ---
layout_linux_dir() {
  chmod 700 "$secrets_dir" || die "chmod 700 secrets/ failed (is it owned by someone else?)"
}

layout_linux_files() {
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
    MINGW* | MSYS*) layout=windows ;;
    Linux) layout=linux ;;
    *) die "no secrets layout for $(uname -s); supported: Git Bash on Windows, Linux (ADR-015)" ;;
  esac
fi

# Windows: secrets/ is restricted first and the .env temp file is created inside it (same volume, so
# the move stays a rename), so the temp file is never readable by anyone else. It is then given its
# own access list and checked while still empty, so every .env this run moves into place (created
# or appended) is born restricted. A failure here exits before any secret is written; the trap
# removes the temp file and an existing .env stays as it was.
if [ "$layout" = windows ]; then
  windows_sid
  mkdir -p "$secrets_dir"
  layout_windows_dir
  tmp=$(mktemp "$secrets_dir/.env.tmp.XXXXXX")
  restrict_file "$tmp"
  acl_check "$tmp"
else
  tmp=$(mktemp "$root/.env.tmp.XXXXXX")
fi

if [ ! -f "$env_file" ]; then
  while IFS= read -r line || [ -n "$line" ]; do
    if [[ $line =~ ^([A-Z0-9_]+)=change-me$ ]]; then
      hex_value 24 value
      printf '%s=%s\n' "${BASH_REMATCH[1]}" "$value"
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
      hex_value 24 value
      printf '%s=%s\n' "${BASH_REMATCH[1]}" "$value" >>"$tmp"
      added+=("${BASH_REMATCH[1]}")
    fi
  done <"$example"
  if [ "${#added[@]}" -gt 0 ]; then
    mv "$tmp" "$env_file"
    echo "env-init: added to .env with generated values: ${added[*]}"
  fi
fi
unset value
# Gone before layout_windows_files walks secrets/.
rm -f "$tmp"
tmp=

# The folder is restricted first, so the key file below is born restricted (Windows: done above).
mkdir -p "$secrets_dir"
[ "$layout" != linux ] || layout_linux_dir

# JWT signing keys (ADR-014, ADR-015): one `kid=hexkey` line per key; the first line signs.
if [ -e "$jwt_file" ] || [ -L "$jwt_file" ]; then
  # Docker creates a folder at a bind-mount source that is missing when a container starts.
  [ -f "$jwt_file" ] && [ ! -L "$jwt_file" ] ||
    die "secrets/jwt_signing_keys exists but is not a regular file (Docker creates a folder there when the stack starts without it). If it is an empty folder: rmdir \"$jwt_file\" (Linux: sudo rmdir, Docker created it as root), then make up again"
else
  hex_value 32 key
  ktmp=$(mktemp "$secrets_dir/.jwt_signing_keys.tmp.XXXXXX")
  printf '%s=%s\n' "$(date -u +%F)" "$key" >"$ktmp"
  unset key
  mv "$ktmp" "$jwt_file"
  ktmp=
  created_key=1
  echo "env-init: created secrets/jwt_signing_keys (never commit it)"
fi

[ -z "$layout" ] || "layout_${layout}_files"
created_key=

if grep -Eq '^[A-Z0-9_]+=.*change-me' "$env_file"; then
  echo "env-init: .env still has change-me values; set them or delete .env to regenerate" >&2
  exit 1
fi
