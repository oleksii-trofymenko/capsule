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

## Credentials in `.env`

- Postgres stores its user and password in its volume on the first start only. Editing them in `.env` afterwards breaks the login: the API logs `OperationalError` on the readiness check. To rotate the password: `$C exec postgres psql -U capsule -c "ALTER USER capsule PASSWORD '<new>'"`, update `.env`, then `make up`.
- Redis, the SeaweedFS S3 identity and the SeaweedFS JWT keys are read on every start. To rotate them: update `.env`, then `make up`. Tested for the S3 identity: after a restart the old key gets 403 and the new one 200.
- `make up` adds any secret that `.env.example` has and `.env` lacks (for example after an upgrade) with a fresh random value. It never changes existing values.
- Lost `.env` and no data to keep: reset (below).

## CI fails in `check-pins.sh`

An image pin in `.github/workflows/ci.yml`, `infra/compose/compose.base.yml` or `apps/api/Dockerfile` changed without the others. Make the Postgres/Redis references (tag and digest) and the uv version identical in the same PR.

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
