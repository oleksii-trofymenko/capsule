# Runbook: planned key rotation (ADR-015)

Planned rotations only. After a leak, or after a restore (ADR-022 restore step 4), do not use this page. Use `secret-leak.md`, which rotates with no overlap.

Commands run from the repository root, in Git Bash on Windows. On Linux every edit in `secrets/` needs `sudo` (the files are `root:<GID> 0440`). `C` below stands for:

```sh
C="docker compose --project-name capsule --env-file .env -f infra/compose/compose.base.yml"
```

Never print a key value. Refer to keys by `kid`, the part before `=`.

## JWT signing keys (`secrets/jwt_signing_keys`, `api` only)

- **When:** every 90 days, by hand (owner decision, 2026-10-27). The age is the date in the first line's `kid`: `head -n1 secrets/jwt_signing_keys | cut -d= -f1` (Linux: `sudo head -n1 … | cut -d= -f1`). An E2 dashboard panel with an alert above 100 days is planned. Until it exists, put the next date in your calendar after each rotation.
- **Format:** one `kid=hexkey` line per key, at most two lines. The first line signs; the second only verifies. `kid` is the UTC creation date (`2026-10-27`; add `-2` for a second key on the same day). The key is 32 random bytes as 64 hex characters.
- **Effect:** nobody is logged out. Refresh tokens are not JWTs, and access tokens signed with the old key keep working until the second step. From E1-05 on, `api` refuses to start with zero lines or more than two.
- **Edit in place.** Write into the existing file (`>` on the file itself), never a new file moved over it. The owner and mode (Linux) and the ACL (Windows) stay as they are. `make up` re-applies them anyway.

### Step 1: add the new key as the first line

The file must have exactly one line before this step (`wc -l secrets/jwt_signing_keys` prints `1`). If it has two, a previous rotation was not finished: do step 2 first.

```sh
# Git Bash. The new key is generated inside the command and never shown.
f=secrets/jwt_signing_keys
old=$(head -n1 "$f")
printf '%s=%s\n%s\n' "$(date -u +%F)" "$(od -An -tx1 -N32 /dev/urandom | tr -d ' \n')" "$old" > "$f"
unset old
cut -d= -f1 "$f"          # two kids: the new one first

# Linux
sudo sh -c 'old=$(head -n1 "$1"); printf "%s=%s\n%s\n" "$(date -u +%F)" "$(od -An -tx1 -N32 /dev/urandom | tr -d " \n")" "$old" > "$1"' sh secrets/jwt_signing_keys
sudo cut -d= -f1 secrets/jwt_signing_keys
```

If both `kid`s are the same date, change the first one to `<date>-2` in an editor (Linux: `sudoedit`).

Then restart `api` only and wait until it is ready:

```sh
$C restart api && make up
```

### Step 2: after at least 15 minutes, remove the old key

15 minutes is the 10-minute access token plus a margin for restarts and requests in flight. Waiting longer is fine. Do not leave two lines for days: then the old key stays valid.

```sh
# Git Bash
f=secrets/jwt_signing_keys; l=$(head -n1 "$f"); printf '%s\n' "$l" > "$f"; unset l
cut -d= -f1 "$f"          # one kid: the new one
# Linux
sudo sh -c 'l=$(head -n1 "$1"); printf "%s\n" "$l" > "$1"' sh secrets/jwt_signing_keys
sudo cut -d= -f1 secrets/jwt_signing_keys
```

Restart again: `$C restart api && make up`.

### Restore, host rebuild or leak

The JWT key has no off-host copy. After a restore, a rebuilt host or a lost `secrets/` folder, use `secret-leak.md` ("JWT signing key"): one new line, no overlap. If the file is simply missing, `make up` creates a fresh one. Access tokens signed with the old key fail with 401 and clients refresh. After a restore, ADR-022 step 4 also revokes every refresh family, so everyone signs in again.

### If it goes wrong

- `make up` fails with `secrets/jwt_signing_keys exists but is not a regular file`: the stack started while the file was missing, and Docker created a folder in its place. See "Secrets" in `compose-stack.md`.
- `api` keeps restarting after an edit (from E1-05 on): check the line count and format without printing values: `awk -F= '{print NR": "$1", "length($2)" chars"}' secrets/jwt_signing_keys`. Each line needs a `kid`, `=` and 64 hex characters, with at most two lines. Fix the file, then `$C restart api`.
