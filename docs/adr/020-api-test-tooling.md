# ADR-020: API test tooling: httpx, PyYAML and jsonschema as dev-only dependencies

- Status: accepted (2026-10-26)
- Date: 2026-10-26
- Deciders: Orchestrator, backend-engineer, project owner
- Related: E0-06, ADR-005, ADR-016, ADR-018, ADR-019

## Context

E0-06 needs two kinds of API tests that the named stack (pytest, Hypothesis, real Postgres and Redis, ADR-016) does not cover by itself. First, an HTTP client that calls the FastAPI app in-process. FastAPI's `TestClient` and the async `ASGITransport` both come from httpx, which is not installed with FastAPI. Second, a contract test: responses must be checked against `contracts/openapi.yaml`, which is YAML (ADR-005) and whose schemas are JSON Schema 2020-12 (OpenAPI 3.1). Python's standard library reads neither YAML nor JSON Schema. Budget is €0; every dependency adds audit surface (pip-audit in CI, ADR-019).

## Options

1. **httpx + PyYAML + jsonschema (dev group only; typeshed stubs types-PyYAML and types-jsonschema for mypy strict)** — httpx is the client FastAPI documents for tests; PyYAML parses the contract; jsonschema validates bodies with the same 2020-12 dialect OpenAPI 3.1 uses, and also checks that the contract's schemas are valid. About 80 lines of our own test helpers tie them together (operation lookup, `$ref` to `components`, content type, `X-Request-ID`). Cons: we keep the small helper ourselves; it checks responses we choose to send, not generated ones.
2. **Schemathesis** — generates requests from the spec and checks every response, built on Hypothesis. Lost: a much larger dependency tree (its own HTTP stack, GraphQL and CLI pieces) for two GET endpoints with no input; generated cases against real Postgres and Redis are slow and hard to keep deterministic in the integration job; it still needs httpx or requests. Worth revisiting when endpoints take real input.
3. **openapi-core** — validates requests and responses against a spec. Lost: it pulls jsonschema, an OpenAPI spec validator and more on top of option 1, and its FastAPI integration expects middleware we would not ship.
4. **No new dependencies: hand-written client and assertions** — call the ASGI app directly and compare dicts. Lost: a hand-rolled ASGI client and a schema checker are more code to own than option 1, and they would drift from the contract.

## Decision

Add httpx, PyYAML and jsonschema (plus their typeshed stubs types-PyYAML and types-jsonschema) to the `dev` dependency group of `apps/api` only, pinned in `apps/api/uv.lock`, and validate API responses against `contracts/openapi.yaml` with them; none of them ships in the runtime image.

## Consequences

- Easier: in-process API tests with lifespan; every response in unit, contract and integration tests is checked against the contract the mobile client is generated from.
- Harder: three more packages (and their transitive dependencies: httpcore, h11, attrs, referencing, rpds-py, jsonschema-specifications) in pip-audit's scope; `$ref` resolution in our helper covers `#/components/...` only.
- Versions are resolved with `exclude-newer` in `apps/api/pyproject.toml` (initially 2026-10-19T00:00:00Z), so every release is at least 7 days old (ADR-018, ADR-019).
- Format checks: jsonschema only checks formats whose optional libraries are installed, so `format: uri-reference` in the contract is not enforced by the contract tests (no extra dependency is added for it); patterns, enums, types and required fields are.
- We will monitor: pip-audit findings for these packages, contract-test failures that turn out to be helper bugs.
- Revisit when: endpoints accept user input and property-based contract testing (Schemathesis) pays for itself, or the helper grows past ~200 lines.
