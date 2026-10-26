# ADR-009: LangGraph for the agent graph

- Status: proposed
- Date: 2026-10-26
- Deciders: Orchestrator, ai-engineer, project owner
- Related: E0-03, ADR-005, ADR-006, ADR-010, blueprint §6

## Context

A consultation is a multi-step flow (blueprint §6): understand the request, ask follow-ups, read photos, reuse the user's wardrobe, retrieve trends, assemble outfits, then check the budget in plain code before answering. It pauses for user answers, resumes later, streams tokens, and every step must be testable with fixtures and traced. Model quality on 8–14B local models is limited, so control flow must be explicit, not left to the model.

## Options

1. **LangGraph** — an explicit state graph with typed state, conditional edges, checkpoints (pause for a follow-up, resume from Postgres), streaming and per-node tracing; nodes are plain functions, easy to unit-test. Cons: a fast-moving library with API changes; we use the graph core only, not the wider LangChain stack.
2. **Hand-written state machine in plain Python** — no dependency, full control. Lost: we would rebuild checkpointing, resumable pauses and streaming of intermediate steps ourselves.
3. **Autonomous agent frameworks (CrewAI, OpenAI Agents SDK-style tool loops)** — quick to start. Lost: the model decides the control flow, which is unreliable on small local models and makes the budget check and evals harder to guarantee.

## Decision

Implement the consultation agent as a LangGraph state graph in `apps/api/modules/agent`, with typed state, one responsibility per node, Postgres checkpoints for pauses, and model calls only through the gateway (ADR-010).

## Consequences

- Easier: follow-up questions are a pause and resume, not custom session code; each node has fixture tests and its own trace span; the budget validator is a deterministic node.
- Harder: pin the LangGraph version and budget time for upgrades; keep LangChain integrations out unless a card justifies one.
- We will monitor: node latency and failure rate, eval scores per node change.
- Revisit when: LangGraph breaks its API in a way that costs more than a rewrite of the graph core, or the graph becomes simpler than the framework (a straight pipeline).
