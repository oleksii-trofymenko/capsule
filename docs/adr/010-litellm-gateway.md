# ADR-010: LiteLLM proxy as the provider-agnostic LLM gateway

- Status: proposed
- Date: 2026-10-26
- Deciders: Orchestrator, ai-engineer, security-engineer, project owner
- Related: E0-03, ADR-007, ADR-009, ADR-011 (planned), ADR-012 (planned), ADR-013 (planned), ADR-015 (planned), blueprint §3, §4

## Context

Models run locally on an RTX 5070 Ti (16 GB VRAM) through Ollama now and maybe vLLM later, with cloud LLM APIs as fallback on errors and timeouts. Moving to cloud providers must stay a config change. We need routing (chat, vision, embeddings to different backends), fallback, timeouts and usage numbers per request. Fallback sends user text and photos to a third party, so it is a data transfer, not just routing. On 2026-03-24 LiteLLM releases 1.82.7 and 1.82.8 on PyPI were compromised and stole credentials; the official Docker image was not affected and 1.83.0 is a clean rebuild ([LiteLLM](https://docs.litellm.ai/blog/security-update-march-2026)).

## Options

1. **LiteLLM proxy (OpenAI-compatible) as its own container** — one endpoint for every backend, routing, timeouts and fallback in YAML config, usage and latency logging, wide provider support. Cons: another service to run; a high-value supply-chain target.
2. **Call providers directly from the agent via each SDK** — no extra hop. Lost: provider choice leaks into code; every switch to the cloud becomes a code change and a deploy.
3. **Own thin router over the OpenAI-compatible API** — minimal and auditable. Lost: we would rebuild fallback, retries, cost tracking and provider quirks that LiteLLM already handles.

## Decision

All model calls go through a LiteLLM proxy container, and model names, providers, routes and fallbacks live only in its config, so moving to cloud providers is a config change, never a code change; application code calls the proxy with the `openai` client using logical route names only (e.g. `agent-parse`, `agent-guide`, `vision`, `embed`) and sends the node name as request metadata; a cloud fallback route may use only providers with a DPA, EU or SCC-covered processing, zero data retention and no training on inputs, and a route that sends photos needs security-engineer sign-off.

## Consequences

- Easier: swapping Ollama for vLLM or a cloud provider edits one config file; one place for timeouts, fallback and usage metrics; every call reaches traces with node, model, tokens and latency.
- Harder: supply chain — official image ≥ 1.83.0 pinned by digest; the `litellm` PyPI package is never a direct or transitive dependency of the API, worker, CI or dev setup (1.82.7 and 1.82.8 blocked; lockfiles with hashes); upgrades only through a reviewed PR. Data — prompt and response storage in spend logs is off and images are redacted before any callback. Exposure — internal Docker network only, admin UI off, master key only in the secret store (ADR-015), API and worker each with a scoped virtual key, outbound traffic limited to configured provider hosts. The proxy keeps usage logs in its own database in the shared Postgres (managed by its own migrations, outside Alembic). A busy GPU falls back only via per-route timeouts, because Ollama queues instead of rejecting.
- We will monitor: gateway latency overhead, fallback rate per route, cost per 1,000 guides, upstream security advisories.
- Revisit when: the gateway adds > 50 ms p95, another supply-chain incident hits it, or a simpler gateway covers our routing and fallback needs.
