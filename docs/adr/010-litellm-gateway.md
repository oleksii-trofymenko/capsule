# ADR-010: LiteLLM proxy as the provider-agnostic LLM gateway

- Status: proposed
- Date: 2026-10-26
- Deciders: Orchestrator, ai-engineer, security-engineer, project owner
- Related: E0-03, ADR-009, ADR-011 (planned), ADR-012 (planned), ADR-015 (planned), blueprint §3, §4

## Context

Models run locally on an RTX 5070 Ti (16 GB VRAM) through Ollama now and maybe vLLM later, with cloud LLM APIs as fallback when the GPU is busy or down. Moving to cloud providers must stay a config change. We need routing (chat, vision, embeddings to different backends), fallback, timeouts, per-route rate limits and usage numbers per request. In March 2026 two LiteLLM releases on PyPI (1.82.7 and 1.82.8) were compromised in a supply-chain attack; the official Docker image was not affected.

## Options

1. **LiteLLM proxy (OpenAI-compatible) as its own container** — one endpoint for every backend, routing and fallback in YAML config, spend and latency logging, wide provider support. Cons: another service to run; a high-value supply-chain target.
2. **Call providers directly from the agent via each SDK** — no extra hop. Lost: provider choice leaks into code; every switch to the cloud becomes a code change and a deploy.
3. **Own thin router over the OpenAI-compatible API** — minimal and auditable. Lost: we would rebuild fallback, retries, cost tracking and provider quirks that LiteLLM already handles.

## Decision

All model calls go through a LiteLLM proxy container, and model names, providers, routes and fallbacks live only in its config, so moving to cloud providers is a config change, never a code change.

## Consequences

- Easier: swapping Ollama for vLLM or a cloud provider edits one config file; one place for timeouts, fallback and usage metrics.
- Harder: supply-chain hygiene is mandatory: use the official image pinned by version and digest (never the PyPI package in production), skip the compromised versions, upgrade only through a reviewed PR; provider keys only in the gateway (ADR-015).
- We will monitor: gateway latency overhead, fallback rate, cost per 1,000 guides, upstream security advisories.
- Revisit when: the gateway adds noticeable latency (> 50 ms p95), another supply-chain incident hits it, or a simpler gateway covers our routing and fallback needs.
