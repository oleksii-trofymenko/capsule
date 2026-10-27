# Runbook: a secret leaked (ADR-015)

Use this when a secret value may have left the host: a log line, a screenshot, a commit, an issue or chat paste, a CI log that shows the value instead of `***`, a lost or stolen disk, or a restore (ADR-022 restore step 4). The CI `stack` job fails with `a generated secret appears in the stack logs` when a value from `secrets/` reaches the container logs. That is a leak in code, not in a real key, because CI keys are throwaway. Fix the code that logged it, and check that the same path cannot log the real key.

Commands run from the repository root, in Git Bash on Windows (Linux: prefix edits in `secrets/` with `sudo`). `C` below stands for:

```sh
C="docker compose --project-name capsule --env-file .env -f infra/compose/compose.base.yml"
```

Never paste a secret value into an issue, a card, a chat or a commit, including while handling the leak. Refer to keys by file name and `kid` (the part before `=`).

## 1. Contain

Stop the public entry point so nothing outside the host can use the leaked value.

- Once the named tunnel exists (E8-01): `$C stop cloudflared`.
- Until then the API listens on `127.0.0.1` only, so there is nothing to stop.

## 2. Rotate the leaked secret with no overlap

Use the row for the leaked secret. Restart only the services named in the row.

| Secret | Where | What to do |
| --- | --- | --- |
| JWT signing key | `secrets/jwt_signing_keys` (`api`) | See "JWT signing key" below. |
| Rate-limit HMAC key (E1-08) | `secrets/ratelimit_hmac_key` (`api`) | Replace the value, then `$C restart api`. The sign-in throttle resets for up to one window. |
| Email encryption keys, blind-index key (E1-24) | `secrets/email_*` (`api`) | New key, re-encrypt or re-index every row, then remove the old key. Follow the E1-24 procedure. Update the off-host copies. |
| SeaweedFS JWT or filer key | `.env` today (`secrets/seaweedfs_security.toml` after E1-25) | New values, then `make up`. Then run `bash infra/compose/check-seaweedfs.sh`. |
| Infra credentials (Postgres, Redis, SeaweedFS S3) | `.env` | Change the value in the service and in `.env`, then `make up`. See "Credentials in `.env`" in `compose-stack.md`. |
| Email-provider API key (E1-17), tunnel token (E8-01) | `secrets/` | Revoke it at the provider first, then put the new one in the file and restart its service. |
| Backup age identity (E1-23) | off-host only | Make a new pair and set `BACKUP_AGE_RECIPIENT`. If the backup disk was exposed, delete the backups encrypted to the old identity. |

### JWT signing key

The file has one `kid=hexkey` line per key, at most two. The first line signs, and a second line only verifies. Access tokens live 10 minutes. Refresh tokens are not JWTs, so this procedure logs nobody out.

1. See which `kid`s are in the file, without printing values:

   ```sh
   cut -d= -f1 secrets/jwt_signing_keys        # Linux: sudo cut -d= -f1 secrets/jwt_signing_keys
   ```

2. Decide by which line leaked. If you are not sure, treat every line as leaked.
   - **The first line (signing key) leaked, or everything leaked:** replace the whole file with one new line. Every access token stops working at once, and clients refresh silently. Replacing the whole file also drops the previous key, if there was one. That is stricter than ADR-015 asks, and it ends early the (at most 10 minutes of) tokens signed with the previous key.

     ```sh
     # Git Bash. Writes in place, so the folder ACL and the file stay the same. The key is
     # generated inside the redirect and never shown.
     printf '%s=%s\n' "$(date -u +%F)" "$(od -An -tx1 -N32 /dev/urandom | tr -d ' \n')" > secrets/jwt_signing_keys
     # Linux
     sudo sh -c 'printf "%s=%s\n" "$(date -u +%F)" "$(od -An -tx1 -N32 /dev/urandom | tr -d " \n")" > secrets/jwt_signing_keys'
     ```

     If the new `kid` equals the one you are replacing (same day), edit the file and add `-2` to the `kid` (`2026-10-27-2`).
   - **Only the second line (previous key) leaked:** delete it and keep the first line.

     ```sh
     l=$(head -n1 secrets/jwt_signing_keys); printf '%s\n' "$l" > secrets/jwt_signing_keys   # Git Bash
     sudo sh -c 'l=$(head -n1 "$1"); printf "%s\n" "$l" > "$1"' sh secrets/jwt_signing_keys  # Linux
     ```

3. Restart `api` only, then check it is ready:

   ```sh
   $C restart api && make up
   cut -d= -f1 secrets/jwt_signing_keys       # 1 line, the new kid
   ```

   On Linux, `make up` puts back `root:10001 0440` if the edit changed it. On Windows, `make up` re-applies the ACL (only you and SYSTEM).
4. Revoke every refresh family only if the database leaked too (from E1-05 on, follow its admin command). A leaked signing key alone does not expose refresh tokens: they are random and stored only as hashes.

Until E1-05 lands, the API does not read the key yet. The steps above still apply, so the file holds no leaked key when it does.

## 3. Check the logs for misuse

- API logs since the leak: `$C logs --since <time> api`. Look for sign-ins, refreshes and 401 bursts you cannot explain. The API logs `kid`s, never values.
- If the value is still somewhere it can be read (issue, chat, CI log), delete it there too. GitHub: delete the comment or the log of the run.

## 4. Purge Git history (only if it was committed)

Rotate first. The repository is public, so anyone may already have a copy, and rotation is what protects us. Then remove the value from history if it is still useful to do so, and check with `make lint` (gitleaks scans history).

## 5. Write an incident note

On the card whose change caused the leak: what leaked, how, when it was found, what was rotated (file name and `kid`, never the value), and the follow-up card that stops it from happening again.
