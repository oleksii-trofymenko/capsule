# ADR-005: Python 3.12 + FastAPI modular monolith; OpenAPI 3.1 as the contract

- Status: proposed
- Date: 2026-10-26
- Deciders: Orchestrator, backend-engineer, project owner
- Related: E0-03, E0-06, ADR-006, ADR-007, ADR-009, blueprint §3, §5, §10

## Context

The backend serves one mobile client from one home PC. The agent stack (LangGraph, embeddings, Whisper) is Python, so the API and the agent share a language. Targets (blueprint §10): simple endpoints p95 < 200 ms, first guide token p95 < 3 s with streaming, `/v1` versioning, one error format. The mobile app needs generated types, so the contract must be machine-readable and versioned in the repo.

## Options

1. **Python 3.12 + FastAPI + Pydantic v2, one deployable with isolated modules (`auth`, `consultations`, `media`, `catalog`, `trends`, `agent`), contract in `contracts/openapi.yaml` (OpenAPI 3.1)** — async I/O for streaming, validation from types, same language as the agent. Cons: Python CPU-bound work must leave the request path (ADR-006).
2. **Microservices (separate API, agent, media services)** — independent scaling. Lost: network hops, distributed tracing and deployments for a one-person team and one machine, with no load that needs it.
3. **Node.js (NestJS) API + Python agent service** — one language with the mobile app. Lost: two backend languages and a service boundary in the middle of every consultation.

## Decision

Build one FastAPI application (Python 3.12, Pydantic v2) with modules that talk only through each other's service interfaces, and treat `contracts/openapi.yaml` (OpenAPI 3.1) as the source of truth: the contract changes first, then the code.

## Consequences

- Easier: one deploy, one test run, one trace per request; shared Python with the agent; generated mobile client.
- Harder: module boundaries rely on review and import rules rather than the network; no module reads another module's tables.
- We will monitor: p95 per endpoint, import-boundary violations in review.
- Revisit when: a module needs to scale or deploy independently with numbers to prove it (e.g. the agent saturates while the API idles), or a hot path is proven CPU-bound beyond what workers absorb.
