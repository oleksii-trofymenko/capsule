# Runbook: Compose stack (E0-07)

Commands run from the repository root, in Git Bash on Windows. `C` below stands for:

```sh
C="docker compose --project-name capsule --env-file .env -f infra/compose/compose.base.yml"
```

No alerts exist yet (observability epic, E2). Until then, failures show up as `make up` failing or `/v1/ready` returning 503.

## `make up` fails or times out

1. `$C ps`: which service is `unhealthy`, `restarting` or `exited`?
2. `$C logs --tail=100 <service>`. All API lines are JSON. Errors from `uvicorn.error` or `core.*` loggers explain startup failures, for example `Invalid settings: DATABASE_URL: ...`.
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

- Postgres and SeaweedFS store their credentials in their volumes on the first start. Editing them in `.env` afterwards breaks the login: the API logs `OperationalError` on the readiness check.
- To rotate the Postgres password: `$C exec postgres psql -U capsule -c "ALTER USER capsule PASSWORD '<new>'"`, update `.env`, then `make up`.
- Redis and SeaweedFS read theirs on every start: update `.env`, then `make up`.
- Lost `.env` and no data to keep: reset (below).

## CI fails in `check-pins.sh`

An image pin in `.github/workflows/ci.yml`, `infra/compose/compose.base.yml` or `apps/api/Dockerfile` changed without the others. Make the Postgres/Redis references (tag and digest) and the uv version identical in the same PR.

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
