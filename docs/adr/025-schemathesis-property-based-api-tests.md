# ADR-025: Schemathesis for property-based API tests, in-process with fakes

- Status: proposed
- Date: 2026-10-28
- Deciders: Orchestrator, backend-engineer, security-engineer, project owner
- Related: E1-06; ADR-016, ADR-018, ADR-019, ADR-020 (partly supersedes its option 2 reasoning)

## Context

ADR-020 rejected Schemathesis while the API had two GET endpoints with no input. It set the trigger to revisit "when endpoints accept user input". Since E1-05 and E1-05c, `POST /v1/auth/guest`, `/refresh` and `/logout` take request bodies. Hand-picked tests check the inputs we think of; generated requests find 500s and contract drift on the ones we do not. Budget is €0, and every dependency adds pip-audit scope (ADR-019). Releases must be at least 7 days old: `apps/api/pyproject.toml` resolves with `exclude-newer = 2026-10-19T00:00:00Z` (ADR-018, ADR-019). Release dates were checked on PyPI on 2026-10-28.

A first run against `main` (2c15150) found two contract bugs within seconds:

- The `X-Request-ID` request parameter declared a `pattern`, but the server ignores an invalid value and uses a new id. The contract said "reject"; the server accepts.
- A body that is not UTF-8 gets FastAPI's own 400 problem document, which no operation declared.

## Options

1. **Schemathesis 4.32.0 in the `dev` group, run in-process under pytest with a fake auth service (chosen).**
   - It generates valid and invalid requests from `contracts/openapi.yaml` (Hypothesis, already in ADR-016) and checks every response: no 5xx, a declared status, content type, headers and body schema; invalid input rejected, valid input accepted; unsupported methods refused.
   - In-process: its ASGI client calls the app with no network and no server. The auth service is replaced through `dependency_overrides` by an in-memory fake that raises the real exceptions and issues real tokens. Readiness probes and the engine of the last-activity middleware are fakes too.
   - Released 2026-10-18 (before the cutoff). New transitive packages, all resolved under the cutoff: charset-normalizer 3.5.2, graphql-core 3.2.13, harfile 0.5.0, hypothesis-graphql 0.13.2, jsonschema-rs 0.59.0, markdown-it-py 4.2.0, mdurl 0.1.2, pyrate-limiter 4.5.0, requests 2.34.2, rich 15.0.0, urllib3 2.8.0, werkzeug 3.1.9. pip-audit 2.10.1 reports no known vulnerabilities (with the existing certifi exception only).
   - Cons: 13 more packages in audit scope; a GraphQL and CLI stack we do not use; it registers a pytest plugin that loads in every test run; the fake can drift from `AuthService`.
2. **Schemathesis against the throwaway Postgres and Redis of `make test`.** Lost: SQL and lock behaviour would be fuzzed too, but its ASGI client runs the app in its own event-loop thread, where psycopg's async mode needs a selector loop on Windows; runs are slower and harder to keep deterministic, since the database keeps state across cases. The card rules out fuzzing against real databases. `tests/integration` already covers the SQL with hand-written cases.
3. **Hypothesis strategies written by hand from the contract schemas.** Lost: we would rebuild what Schemathesis does (body, header and negative generation, response checks) and keep it in sync with the contract ourselves.
4. **Stay with ADR-020 only.** Lost: the two bugs above shipped past the ADR-020 helper, which only checks responses to requests we chose.

## Decision

Add `schemathesis==4.32.0` (exact pin) to the `dev` dependency group of `apps/api` only, and run it in `tests/contract/test_schemathesis.py` against the in-process app with fake auth, probes and engine, over every operation of `contracts/openapi.yaml`, with all default checks, `max_examples=100`, `derandomize=True` and `database=None`.

### Rules

- Stateless only: no OpenAPI `links`, so generated cases never hold a valid refresh token or guest credential.
- The fake keeps the public method names and signatures of `AuthService`; a test fails when they differ.
- The ADR-020 helper (`tests/support.py`) stays. It checks what generated cases cannot reach: real rotation and logout against Postgres in `tests/integration`, the 503 `failing` list, the empty 204 body and the `X-Request-ID` format on every response. It adds no dependency.
- No Schemathesis CLI, GraphQL or network transport is used without a new ADR.

## Consequences

- Easier: every operation gets generated valid and invalid requests in `unit (api)` with no new CI job; the run takes a few seconds. A new operation is covered as soon as it is in the contract.
- Harder: 13 more dev packages in pip-audit's scope. A bump is an exact-pin change in its own PR, at least 7 days after the release, release notes linked, security-engineer review (ADR-018, ADR-019). New default checks in a bump may fail on contract wording that was accepted before.
- Not covered: SQL, locks, the grace rule and token reuse (integration tests own those); success paths that need a valid secret (refresh 200, guest sign-in 200, logout of a live family).
- Follow-up card: a stateful run with OpenAPI `links` (guest 201 → refresh → logout), so generated sequences reach the success paths above.
- We will monitor: run time of the property test in `unit (api)` (budget: 30 s); pip-audit findings for the new packages; failures that turn out to be fake drift rather than app bugs.
- Revisit when: the stateful follow-up lands, the fake grows past ~100 lines, the run exceeds 30 s, or Schemathesis 5 changes the Python API.
