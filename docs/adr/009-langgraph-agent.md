# ADR-009: LangGraph for the agent graph

- Status: proposed
- Date: 2026-10-26
- Deciders: Orchestrator, ai-engineer, project owner
- Related: E0-03, ADR-005, ADR-006, ADR-007, ADR-010, blueprint §6

## Context

A consultation is a multi-step flow (blueprint §6): understand the request, ask follow-ups, read photos, reuse the user's wardrobe, retrieve trends, assemble outfits, then check the budget in plain code before answering. It pauses for user answers, resumes later, streams tokens, and every step must be testable with fixtures and traced. Model quality on 8–14B local models is limited, so control flow must be explicit, not left to the model. Graph state holds personal data.

## Options

1. **LangGraph** — an explicit state graph with typed state, conditional edges, checkpoints (pause for a follow-up, resume from Postgres), streaming and per-node tracing; nodes are plain functions, easy to unit-test. Cons: still young (1.x since October 2025) and brings `langchain-core` in as a dependency.
2. **Hand-written state machine in plain Python** — no dependency, full control. Lost: we would rebuild checkpointing, resumable pauses and streaming of intermediate steps ourselves.
3. **Autonomous agent frameworks (CrewAI, OpenAI Agents SDK-style tool loops)** — quick to start. Lost: the model decides the control flow, which is unreliable on small local models and makes the budget check and evals harder to guarantee.

## Decision

Implement the consultation agent as a LangGraph state graph in `apps/api/modules/agent`, with typed state and one responsibility per node, Postgres checkpoints via `langgraph-checkpoint-postgres` in a separate `agent_checkpoint` schema created by an Alembic migration (never by `setup()` at runtime), and model calls only through the gateway (ADR-010) with the `openai` client, never LangChain chat-model wrappers.

## Consequences

- Easier: follow-up questions are a pause and resume, not custom session code; each node has fixture tests and its own trace span; the budget validator is a deterministic node.
- Harder: the checkpointer uses psycopg 3 next to SQLAlchemy; checkpoints are deleted when the consultation closes or its TTL expires, because state holds personal data; pin the LangGraph version and keep other LangChain integrations out unless a card justifies one.
- We will monitor: node latency and failure rate, checkpoint resume failures, eval scores per node change.
- Revisit when: an upgrade (e.g. LangGraph 2.0) needs more than 2 days of migration work, checkpoint resume fails in production, or the clarify and budget-swap loops are removed and the graph becomes a straight pipeline.
