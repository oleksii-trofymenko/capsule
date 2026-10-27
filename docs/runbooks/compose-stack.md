# Runbook: Compose stack (E0-07)

Commands run from the repository root, in Git Bash on Windows. `C` below stands for:

```sh
C="docker compose --project-name capsule --env-file .env -f infra/compose/compose.base.yml"
```

No alerts exist yet (observability epic, E2). Until then, failures show up as `make up` failing or `/v1/ready` returning 503.

## `make up` fails or times out

1. `$C ps`: which service is `unhealthy`, `restarting` or `exited`?
2. `$C logs --tail=100 <service>`. API lines are JSON once logging is configured. An invalid setting stops the API before that: it prints a plain Python traceback ending in `core.config.ConfigError: Invalid settings: DATABASE_URL: ...`. It names the variable and the rule, never the value.
3. Common causes:
   - Docker Desktop is not running: start it, then run `make up` again.
   - Port 8000 is taken: set `API_HOST_PORT` in `.env`, then `make up`.
   - `env-init: .env still has change-me values`: set those values, or delete `.env` before the first start (see below).
   - `required variable ... is missing a value`: compare `.env` with `.env.example` and add the missing variable.
   - Image pull failures: check the network and the Docker Hub rate limit (`docker pull <image>`).
4. Still failing: `$C down`, then `make up`. Data volumes are kept.

## `/v1/ready` returns 503

The body lists the dependencies that are `failing`.

- After a dependency recovers from a hang, `/v1/ready` may keep failing for up to about 10 s. Wait 15 s and check again.
- Check that dependency with `$C ps` and `$C logs <service>`. To restart it: `$C restart postgres` (or `redis`).
- The API itself is healthy as long as `/v1/health` returns 200. It is not restarted for readiness failures.

## API keeps restarting

`docker inspect capsule-api-1 --format '{{.RestartCount}} {{.State.Health.Status}}'`, then the API logs. A config error in `.env` makes it exit on start: fix `.env`, then `make up`.

## Migrations (E1-05a)

`make up` runs the one-shot `migrate` service (`alembic upgrade head`, same image as the api) after Postgres is healthy. The api starts only if it exits 0. Afterwards `$C ps --all` shows `migrate` as `Exited (0)`, which is normal. It has no health check on purpose: the image's check probes `/v1/health`, which a one-shot never serves.

- A successful run prints nothing. To see the current revision: `$C run --rm --no-deps migrate alembic current` (Postgres must be up).
- `make up` fails and names `migrate` (`didn't complete successfully`), and `api` does not start. **On an upgrade this is a full outage:** Compose has already stopped the running `api` to recreate it, and it stays down until `migrate` succeeds. Fix forward, or check out the last good commit and run `make up`. Read `$C logs migrate`:
  - `ConfigError: Invalid settings: DATABASE_URL: ...`: `.env` is wrong (see "Credentials in `.env`" below). The value is never printed.
  - `migration failed: <type>; sqlstate=<code>; constraint=<name>` is all a failed run prints (ADR-022). The driver message, which can quote row values, is dropped on purpose. Look the SQLSTATE up in the Postgres error codes table, for example `23505` unique violation or `42P07` duplicate table.
  - `migration failed: OperationalError (OperationalError)` with no SQLSTATE: connecting failed. The reason is in `$C logs postgres` (for example `password authentication failed for user`). See "Credentials in `.env`" below.
  - `migration failed: ValueError` (no SQLSTATE) usually means a malformed `DATABASE_URL` that the config check lets through, for example a non-numeric port. Fix `.env`; the value is never printed.
  - `migration failed: OperationalError (LockNotAvailable); sqlstate=55P03`: a migration waited longer than `lock_timeout` (5 s, set in `migrations/env.py`, E1-27) for a lock that another session holds. It fails fast on purpose: while a migration waits for an `ACCESS EXCLUSIVE` lock, every api query on that table queues behind it. The run was rolled back and nothing was applied, except what ran before and inside a finished `autocommit_block()` (it commits the open transaction; see the exception below). Find the blocker, usually a long open transaction. Once `migrate` has exited nothing waits any more, so `pg_blocking_pids` only lists it while another session is queued; the query also lists transactions open for over a minute: `$C exec postgres psql -U capsule -c "SELECT pid, state, xact_start, left(query, 60) FROM pg_stat_activity WHERE pid IN (SELECT unnest(pg_blocking_pids(pid)) FROM pg_stat_activity) OR xact_start < now() - interval '1 minute';"`. Let it finish, or stop it with `SELECT pg_cancel_backend(<pid>);` (cancels the query) or `SELECT pg_terminate_backend(<pid>);` (ends the session, needed for `idle in transaction`). Then run `make up` again.
  - A migration that really needs to wait longer (for example on a busy table at a quiet hour) raises the limit for itself as its first step: `op.execute("SET LOCAL lock_timeout = '30s'")`. `SET LOCAL` lasts until the transaction ends: the end of the run (Alembic runs the whole `upgrade` in one transaction, so later migrations of the same run get the higher limit too), or the next `autocommit_block()`, which commits it. Inside an `autocommit_block()` there is no transaction to scope it to: use a plain `SET lock_timeout = '30s'` there and `RESET lock_timeout` after the step. The trade-off: api queries on that table can queue for up to that long. Keep it short and say why in the migration.
  - Any other error is a broken migration. A normal migration runs in one transaction, so Postgres rolls the whole run back and nothing is half-applied. Fix the migration in a PR, then `make up`. Never edit `alembic_version` by hand.
  - **Exception:** steps inside `autocommit_block()` (for example `CREATE INDEX CONCURRENTLY`) commit on their own. A failed concurrent index build leaves an `INVALID` index behind; that includes a build that hits `lock_timeout` (`55P03`), because `lock_timeout` is per session and covers these steps too. Find it with `SELECT indexrelid::regclass FROM pg_index WHERE NOT indisvalid;`, drop it with `DROP INDEX CONCURRENTLY <name>;`, then run `make up` again. Keep each autocommit block in a migration file of its own, so a failure cannot leave other changes of the same file applied.
- Downgrades are for development only: `$C run --rm --no-deps migrate alembic downgrade -1`. On data you keep, write a new forward migration instead.

## Credentials in `.env`

- Postgres stores its user and password in its volume on the first start only. Editing them in `.env` afterwards breaks the login: the API logs `OperationalError` on the readiness check. To rotate the password: `$C exec postgres psql -U capsule -c "ALTER USER capsule PASSWORD '<new>'"`, update `.env`, then `make up`.
- Redis, the SeaweedFS S3 identity and the SeaweedFS JWT keys are read on every start. To rotate them: update `.env`, then `make up`. Tested for the S3 identity: after a restart the old key gets 403 and the new one 200.
- `make up` adds any secret that `.env.example` has and `.env` lacks (for example after an upgrade) with a fresh random value. It never changes existing values.
- Lost `.env` and no data to keep: reset (below).

## Secrets (`secrets/`, ADR-015, E1-05b)

Application secrets are files in the gitignored repo-root `secrets/`, not variables in `.env`. Today there is one: `secrets/jwt_signing_keys`, mounted only into `api` at `/run/secrets/jwt_signing_keys`. `make up` (`infra/compose/env-init.sh`) creates it if missing, never overwrites it, and applies the layout on every run. Any failure stops `make up`. Rotation: `key-rotation.md`. A leaked or lost key: `secret-leak.md`.

Expected layout, and how to check it without printing values:

- **Git Bash:** `secrets/` and `.env` are readable only by you and SYSTEM. There is no inheritance and no Administrators entry. Check with `MSYS2_ARG_CONV_EXCL='*' icacls secrets` and `icacls .env`. You should see two lines, `NT AUTHORITY\SYSTEM` and your user. On `secrets/` both have `(OI)(CI)(F)`, and the file shows `(I)(F)` for both. `make up` resets each file in `secrets/` to inherited entries only, then reads the access lists back as SIDs and stops if anyone else appears. Inside the container the file appears as `root 0777`, so the host ACL is the only barrier.
- **Linux:** `secrets/` is `0700` and owned by you. The key file is `root:10001 0440` (10001 = the api image's group). Check with `stat -c '%n %U:%g %a' secrets secrets/jwt_signing_keys`. Reading or editing it needs `sudo`.
- **Both:** `MSYS_NO_PATHCONV=1 $C exec -T api test -r /run/secrets/jwt_signing_keys && echo ok` while the stack runs. Without `MSYS_NO_PATHCONV=1`, Git Bash rewrites `/run/...` into a Windows path and the check fails even when the file is fine. In the container the file shows as `root 0777`, which is expected.

`make up` fails in env-init:

- `secrets/jwt_signing_keys exists but is not a regular file`: the stack was started while the file was missing, and Docker created an empty folder at that path. This happens with `docker compose up` without `make up`, or after deleting `secrets/` while the stack ran. Run `$C down`, then `rmdir secrets/jwt_signing_keys` (Linux: `sudo rmdir`, because Docker created it as root), then `make up`. A new key is generated. If an old key existed, follow `secret-leak.md` (lost key).
- `unexpected user SID from whoami.exe /user` or `whoami.exe /user failed`: run `"$(cygpath -u "$SYSTEMROOT")/System32/whoami.exe" /user /fo csv /nh` yourself. A local or Microsoft account prints a SID starting with `S-1-5-21-`. Run `make up` as that normal user, not from an elevated shell under another account. Only `S-1-5-21-` SIDs are accepted. An Entra ID (work or school) account prints `S-1-12-1-...` and needs a change to `env-init.sh` (and security review) first.
- `icacls on secrets/ failed` (or on `.env`): the error line above it comes from icacls. Usually the repo sits on a drive without ACLs (FAT/exFAT, network share) or in a synced folder. Move the repo to a local NTFS folder outside OneDrive. A synced folder is an ADR-015 "revisit" trigger. You can always reset the ACL on folders you own: `MSYS2_ARG_CONV_EXCL='*' icacls secrets /reset /T`, then `make up` again. Note that `/reset` puts back the inherited entries (Administrators, and anyone else with access to the parent folder), so the keys are readable more widely until `make up` succeeds. Run `make up` right after, and fix the cause first if it keeps failing.
- `<file> also grants access to '<SID or alias>'; expected only the current user and SYSTEM`: an entry that `make up` does not remove on its own, for example an explicit grant on `.env` (`BU` = Users, `BA` = Administrators). `make up` stops, and removes a key file it created in that run. Look at it with `MSYS2_ARG_CONV_EXCL='*' icacls <file>`, remove the extra entry with `MSYS2_ARG_CONV_EXCL='*' icacls <file> /remove:g "*<SID>"`, then run `make up` again.
- `... must be root:10001 mode 0440; that needs sudo (or root), which is missing`: on a Linux host without sudo, run the two commands it prints as root once. Later `make up` runs see the right owner and skip sudo.
- `chmod 700 secrets/ failed`: `secrets/` belongs to another user, for example after running `sudo make up`. Fix it with `sudo chown "$(id -u):$(id -g)" secrets`, and never run `make up` with sudo.
- `no secrets layout for <OS>`: only Git Bash on Windows and Linux are supported (ADR-015). macOS needs an ADR-015 change first.

Other cases:

- `git clean -fdx`, a reset or a new clone deletes `secrets/`. The next `make up` creates a new key. Every access token then fails once and clients refresh silently. Nothing else is lost, because the JWT key has no off-host copy by design.
- `api` cannot read the file (the CI step `api reads its file secret`, or E1-05's startup error): check the layout above. If `apps/api/Dockerfile` changed the group id from 10001, update `API_GID` in `env-init.sh` and the ADR-015 inventory together.
- To reset the JWT key on a dev machine: `$C down`, `rm secrets/jwt_signing_keys` (Linux: `sudo rm secrets/jwt_signing_keys`), then `make up`. Delete only that file, never the whole folder. From E1-24 on, `secrets/` also holds the email encryption and blind-index keys. Losing those makes every stored email unrecoverable, so check their off-host copies (password manager and USB stick, ADR-015) before deleting anything else in `secrets/`.

CI `stack` job steps for secrets (throwaway values, deleted in `Tear down`):

- `Throwaway secrets`: env-init runs with `generate-only`. Then every `.env` value and each key line in `secrets/` is masked on its own and written to the leak-pattern file. `no files in secrets/ after env-init` means env-init created no key file. `no masking rule for secrets/<file>` means a new secret file needs its masking rule in this step (same PR). `is not kid=<64 hex>` or `has no key lines` means env-init wrote a broken key file. Reproduce it on a temp copy: `d=$(mktemp -d); cp .env.example "$d/"; bash infra/compose/env-init.sh "$d" generate-only; awk -F= '{print $1, length($2)}' "$d/secrets/jwt_signing_keys"; rm -rf "$d"`. It must print the date and `64`.
- `Secrets layout (sudo)`: env-init's Linux layout did not take effect. `the runner can still read` means the chown/chmod did not run. Read the `stat` line above it.
- `api reads its file secret`: the secret is not mounted, or its owner or mode is wrong for uid 10001. See "Other cases" above.
- `a generated secret appears in the stack logs` (inside the restart step, or the step after it): a code path logged a generated value, either a `.env` credential or a `secrets/` key. `leak patterns file is missing or empty`, `leak grep self-test did not match` or `leak grep failed` mean the check itself is broken: fix it, never skip it. After a SeaweedFS bump, a hit can be its startup line with the S3 access key ID in new wording (ADR-024). Compare the line from `$C logs seaweedfs` (redact the ID before you paste it) with the `adr024` regex in `ci.yml`. Update the regex only if it is the same startup message. A new line that carries the ID is not covered by ADR-024. For a real hit, find it with `$C logs` in a local stack, but do not paste the value. Fix the code. Then follow `secret-leak.md` for any real key that went through the same path.

## CI fails in `check-pins.sh`

An image pin in `.github/workflows/ci.yml`, `infra/compose/compose.base.yml` or `apps/api/Dockerfile` changed without the others. Make the Postgres/Redis references (tag and digest) and the uv version identical in the same PR.

## CI job `stack` fails (E0-13)

The `stack (compose smoke)` job in `.github/workflows/ci.yml` runs on PRs that touch `apps/api/`, `infra/compose/`, `.env.example`, the `Makefile`, workflows, `contracts/` or `.pre-commit-config.yaml`, and on every `main` push and daily run. It uses throwaway secrets that env-init generates on the runner. They are masked in the log (`***`) and deleted at the end. The failing step tells you where to look:

- `Throwaway secrets`: `.env.example` has a `change-me` key that env-init did not fill in. Run env-init on a copy in a temp folder (its argument is the folder that holds `.env.example`). It must print `ok`:

  ```sh
  d=$(mktemp -d); cp .env.example "$d/"
  bash infra/compose/env-init.sh "$d" && ! grep '=change-me' "$d/.env" && echo ok
  rm -rf "$d"
  ```

- `Pull images`: Docker Hub or GHCR is unreachable or rate-limited (`toomanyrequests`). Re-run the job. If it keeps failing, check the pins with `bash infra/compose/check-pins.sh`.
- `Build api image`: the Dockerfile or `apps/api/uv.lock` is broken. Reproduce with `$C build api`.
- `make up`: open `Dump stack logs` (`ps --all`, then the last 200 lines from each service) and follow "`make up` fails or times out" above. `not ready after 60 s` means a dependency failed `/v1/ready`. The api log names it.
- `Postgres log settings (ADR-022)`: the `postgres` service `command` in `compose.base.yml` lost `log_error_verbosity=terse` or `log_min_error_statement=panic`. Put both back; without them Postgres error lines can carry row values (DETAIL, STATEMENT).
- `SeaweedFS lockdown check`: see "SeaweedFS exposure check fails" below. Treat any `FAIL` as a security regression in the PR.
- `Restart keeps Postgres, Redis and SeaweedFS data`: after `make down` / `make up`, the job reads back a Postgres row, a Redis key and an S3 object, and expects `postgres: kept  redis: kept  s3: 200 kept`. A missing value means a volume, `user:`, `read_only` or Redis AOF change lost data on restart. `s3: 500 ...InternalError...` means the seaweedfs health check passed before the volume server registered: see "S3 reads fail right after a restart" below. The S3 read is tried once, on purpose. Do not add a retry. Reproduce it under a throwaway project, never `capsule`. Only postgres and redis start, so port 8000 stays free. Tested in Git Bash:

  ```sh
  d=$(mktemp -d); cp .env.example "$d/"; bash infra/compose/env-init.sh "$d"
  R="docker compose --project-name capsule-repro --env-file $d/.env -f infra/compose/compose.base.yml"
  sql() { $R exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tA -c "$1"' sh "$1"; }
  $R up --detach --wait postgres redis
  sql "CREATE TABLE ci_smoke (v text); INSERT INTO ci_smoke VALUES ('kept')"
  $R exec -T redis redis-cli SET ci:smoke kept
  $R down && $R up --detach --wait postgres redis
  sql "SELECT v FROM ci_smoke"; $R exec -T redis redis-cli GET ci:smoke   # both must print kept
  $R down --volumes; rm -rf "$d"
  ```

The log dump shows only `ps` output and container logs. Do not add `compose config` or `docker inspect` to the job, because both print the interpolated secrets.

## Permission denied on a data volume (E0-12)

postgres, redis and seaweedfs start as fixed non-root users with no capabilities (`infra/compose/README.md`, "Container privileges"). They cannot fix the ownership of their volume themselves. This only happens with a volume written by root, for example a restore or a manual copy. Volumes created by `make up` already have the right owner.

Symptoms in `$C logs <service>`:

- postgres restarts; `initdb: error: could not access directory "/var/lib/postgresql/data": Permission denied`
- seaweedfs restarts; `please verify /data is writable ... permission denied`
- redis exits with `Can't open or create append-only dir appendonlydir: Permission denied`, or it stays healthy and logs `Opening the temp file for AOF rewrite ...: Permission denied`. In the second case data written since the last good AOF write is at risk.

Fix the ownership with a one-off root container that has no network and only two capabilities. `CHOWN` changes the owner. `DAC_READ_SEARCH` lets it enter `0700` directories owned by another uid, for example a PGDATA restored from an image that runs Postgres as uid 70. The data is kept. Tested on all three, and on a uid-70 PGDATA:

```sh
$C stop <service>
img=$($C config --images <service>)   # also works after make down
MSYS_NO_PATHCONV=1 docker run --rm --network none --user 0:0 \
  --cap-drop ALL --cap-add CHOWN --cap-add DAC_READ_SEARCH --security-opt no-new-privileges:true \
  -v capsule_<volume>:/v --entrypoint chown "$img" -R <uid:gid> /v
make up
```

For postgres, the restored data directory must also be mode `0700`, or Postgres refuses to start. Before `make up`, run as the new owner, with no capability:

```sh
MSYS_NO_PATHCONV=1 docker run --rm --network none --user 999:999 --cap-drop ALL \
  --security-opt no-new-privileges:true -v capsule_pg_data:/v --entrypoint chmod "$img" 0700 /v
```

| Service | Volume | uid:gid |
| --- | --- | --- |
| postgres | `pg_data` | `999:999` |
| redis | `redis_data` | `999:1000` |
| seaweedfs | `seaweed_data` | `1000:1000` |

After an image bump, a changed uid shows the same symptoms. Check the image's user (`docker run --rm --entrypoint id <image> postgres`, `redis` or `seaweed`) before chowning, and update `user:` in `compose.base.yml` if it differs.

To check the privileges of the running containers (expected: no uid 0, every `Cap*` value all zeros):

```sh
for s in api postgres redis seaweedfs; do
  echo "$s: $(docker inspect --format '{{.Config.User}} add={{.HostConfig.CapAdd}} drop={{.HostConfig.CapDrop}} ro={{.HostConfig.ReadonlyRootfs}}' "$($C ps -q $s)")"
  $C exec $s grep -E '^(Uid|CapEff|CapBnd)' /proc/1/status
done
```

Never start redis as root with a reduced capability set. Without `SETUID`/`SETGID` its entrypoint does not fail. It runs redis-server as root.

## CI fails in `check-privileges`

`check-privileges: <files>: <service>: <problem>` means a service in `compose.base.yml` (or the test overlay) has no non-root `user:`, lacks `cap_drop: [ALL]`, has a `cap_add`, or lacks `no-new-privileges:true`. Restore the setting. If a service truly needs a capability, that is a security decision: get security-engineer review, and change the check in the same PR. Run it locally with `bash infra/compose/check-privileges.sh`.

## Reset the stack (deletes all local data)

Only on a development machine, or with a verified Postgres backup:

```sh
$C down --volumes    # removes capsule_pg_data, capsule_redis_data, capsule_seaweed_data
rm .env              # optional: new secrets on the next make up
make up
```

## Leftovers from `make test`

`make test` removes its `capsule-test` project on exit. After a crash, clean up with:

```sh
docker compose --project-name capsule-test --env-file infra/compose/test.env -f infra/compose/compose.base.yml -f infra/compose/compose.test.yml down --volumes
```

## SeaweedFS exposure check fails

`bash infra/compose/check-seaweedfs.sh` prints `FAIL` lines:

- `unexpected listeners`: a SeaweedFS bump added a listener on `0.0.0.0`. Find its flag in `weed server -h`, then disable it or bind it to loopback in `compose.base.yml`.
- `PutIdentity was not rejected`: `security.toml` is missing or has no `[jwt.filer_signing]` key. Check with `$C exec seaweedfs cat /etc/seaweedfs/security.toml` and check `.env`. Treat it as a security incident: anyone on `backend` may have added an identity.
  1. Rotate the S3 credentials and JWT keys in `.env`, then run `make up` and the check again.
  2. An injected identity vanishes on restart, but what it created stays. With the admin identity, list buckets, bucket policies and IAM policies (for example `$C exec seaweedfs sh -c 'echo "s3.bucket.list; s3.configure" | weed shell'`). Delete anything you do not recognise.
- S3 status mismatch: compare `SEAWEEDFS_S3_*` in `.env` with what the container got (`$C exec seaweedfs env | grep AWS_ACCESS_KEY_ID`).

## S3 reads fail right after a restart, or seaweedfs stays unhealthy (E0-14)

The seaweedfs health check passes only when the S3 API answers and the volume server has registered with the master. A data node must appear in `/dir/status`. Before registration, reads of existing objects return `500 InternalError` and the log shows `not found` lines. Those lines also print chunk keys (E2-01), so do not paste them into issues.

- seaweedfs stays `unhealthy`, or `make up` times out at 300 s: check whether the volume server registered with `$C exec seaweedfs wget -qO- http://127.0.0.1:9333/dir/status`. `"DataCenters":null` means no data node. Then read `$C logs --tail=100 seaweedfs` for the volume server's error. `permission denied` on `/data` is covered in "Permission denied on a data volume" above. A full disk or a damaged volume file also stops it.
- Reads return 500 while seaweedfs is `healthy`: the health check no longer reflects registration, for example because a SeaweedFS bump changed `/dir/status`. Check that the output still has `"PublicUrl"` inside `DataNodes`, then fix the `test:` in `compose.base.yml`.
- Reproduce under a throwaway project (seaweedfs only). Tested in Git Bash:

  ```sh
  d=$(mktemp -d); cp .env.example "$d/"; bash infra/compose/env-init.sh "$d"
  R="docker compose --project-name capsule-repro --env-file $d/.env -f infra/compose/compose.base.yml"
  s3() { $R exec -T seaweedfs sh -c 'curl -s -w " %{http_code}\n" --aws-sigv4 aws:amz:us-east-1:s3 --user "$AWS_ACCESS_KEY_ID:$AWS_SECRET_ACCESS_KEY" "$@"' sh "$@"; }
  $R up --detach --wait seaweedfs
  s3 -X PUT http://127.0.0.1:8333/ci-smoke; printf kept | s3 -T - http://127.0.0.1:8333/ci-smoke/o
  $R down && $R up --detach --wait seaweedfs
  s3 http://127.0.0.1:8333/ci-smoke/o   # must print kept 200
  $R down --volumes; rm -rf "$d"
  ```
