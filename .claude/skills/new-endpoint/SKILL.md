---
name: new-endpoint
description: Add or change a FastAPI endpoint contract-first — OpenAPI, Pydantic schemas, service, router, tests, mobile client. Use whenever an API endpoint is created or its request or response changes.
---

# New endpoint

1. **Contract.** Edit `contracts/openapi.yaml`: path under `/v1`, request and response schemas, every error as `application/problem+json`, auth requirement, idempotency key for creating POSTs. Get Orchestrator approval if the change breaks existing clients.
2. **Schemas.** Pydantic v2 models in the module's `schemas.py` that match the contract exactly. Validate limits (lengths, ranges, enums).
3. **Service.** Business logic in the module's service, no FastAPI imports. Timeouts and retries on external calls.
4. **Router.** Thin handler: validate, call the service, map domain errors to problem responses. Dependencies through `Depends`.
5. **Authorisation.** Check the caller owns every object they touch (object-level auth).
6. **Observability.** A span around the service call; a metric if the card names one; structured log on failure without personal data.
7. **Tests.** Unit (service), integration (router + real DB), contract (response matches the spec). Happy, failure and edge case.
8. **Client.** Regenerate the mobile API client; commit the generated file in the same PR.
9. **Check.** `make lint`, `make test`. Put sample request and response in the PR.
