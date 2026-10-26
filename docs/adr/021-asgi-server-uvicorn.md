# ADR-021: uvicorn (without extras) as the ASGI server for the API

- Status: accepted (2026-10-26)
- Date: 2026-10-26
- Deciders: Orchestrator, platform-engineer, project owner
- Related: E0-06, E0-07, ADR-005, ADR-018, ADR-019

## Context

The API is a FastAPI app built by `main:create_app` (ADR-005). It needs an ASGI server to run in its container (E0-07), but neither blueprint §4 nor any ADR names one. The server sits behind Cloudflare Tunnel later (ADR-014, planned) and serves a few hundred requests per second at most on the home PC. Our request middleware already writes one JSON access line per request, so the server's own access log is not needed and must not write client IPs or query strings. Every runtime package is checked by pip-audit (ADR-019). Releases must be at least 7 days old (ADR-018).

## Options

1. **uvicorn, no `[standard]` extras** — the server FastAPI documents and the most widely used ASGI server. Without extras it adds only click and h11 (h11 is already in the lock for httpx). Its asyncio loop runs psycopg's async mode on Linux without changes. `--factory`, `--no-access-log` and `--proxy-headers` cover what we need. Cons: without uvloop and httptools it is slower than it could be. For our load the gateway and the model are the bottleneck, not the HTTP parser.
2. **uvicorn[standard]** — about 20–40 % more throughput with uvloop and httptools. Lost: five more packages (uvloop, httptools, websockets, watchfiles, python-dotenv), some with C extensions. They add audit surface and nothing else we need now.
3. **Hypercorn** — HTTP/2 and HTTP/3 support. Lost: the tunnel terminates HTTP/2 for us, and releases are rare (0.18.0 was the latest as of 2026-10-26, from 2025-11).
4. **Granian** — a Rust server, fast. Lost: a compiled binary that is younger and less documented with FastAPI, and its logging is harder to route through our JSON handler.

## Decision

Run the API with plain `uvicorn` (no extras), pinned in `apps/api/uv.lock`, as `uvicorn main:create_app --factory --no-access-log`; `core/logging.py` routes uvicorn's server loggers to our JSON handler and keeps its access logger silent.

## Consequences

- Easier: one familiar command; startup and error lines are JSON like every other line; no access lines with client IPs.
- Harder: on Windows, running uvicorn outside Docker needs a selector event loop for psycopg. We run the API in a Linux container, so there is no Windows entry point. uvicorn trusts `X-Forwarded-*` headers only from 127.0.0.1 by default, which never matches a container peer; the tunnel card sets `FORWARDED_ALLOW_IPS` to the tunnel container.
- We will monitor: p95 latency of simple endpoints (target < 200 ms, `docs/metrics.md`), and container restarts triggered by the health check.
- Revisit when: simple-endpoint p95 exceeds 200 ms and profiling points at the server; we need several worker processes; or we need HTTP/2 to the origin.
