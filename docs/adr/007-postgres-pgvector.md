# ADR-007: PostgreSQL 16 + pgvector as the single database; SQLAlchemy 2 (async) and Alembic

- Status: accepted (2026-10-26)
- Date: 2026-10-26
- Deciders: Orchestrator, backend-engineer, ai-engineer, project owner
- Related: E0-03, ADR-005, ADR-009, ADR-010, blueprint §3, §4, §6, §10

## Context

Capsule stores users, consultations, wardrobe items, guides and feedback (relational), embeddings for RAG over trends and user memory, and agent checkpoints (blueprint §6). MVP scale is small: tens of thousands of trend and catalogue chunks and a wardrobe of tens to hundreds of items per user. With a 1024-dim embedding model (e.g. bge-m3, float32 ≈ 4 KB per vector), 50k chunks ≈ 200 MB raw and < 0.5 GB with HNSW; 1M vectors ≈ 4 GB raw, ~6–8 GB with HNSW. Everything runs on one PC with 32 GB RAM, shared with Redis, the worker and model inference.

## Options

1. **PostgreSQL 16 + pgvector (≥ 0.8, HNSW), SQLAlchemy 2 async, Alembic migrations** — one database for data, vectors and checkpoints; a vector search can filter by user, budget or season in the same SQL query and transaction; one backup, one connection pool. Cons: vector search tuning shares resources with transactional load.
2. **PostgreSQL + a separate vector database (Qdrant, Weaviate)** — purpose-built ANN features and scaling. Lost: up to ~1M vectors the index fits in RAM next to inference, so a second store adds a stateful service to run, back up and secure on the home PC, duplicates data with no shared transactions, and adds no capacity.
3. **SQLite (with a vector extension)** — zero operations. Lost: one writer at a time limits the API and worker running in parallel; weaker concurrency and migration tooling for a server.

## Decision

Use one PostgreSQL 16 instance with pgvector for relational data and embeddings, accessed through SQLAlchemy 2 (async), with every schema change made by an Alembic migration — including the LangGraph checkpoint schema (ADR-009); the only exception is the LiteLLM proxy's own database in the same instance, managed by its own migrations (ADR-010).

## Consequences

- Easier: one backup and restore, transactional writes of data and its embedding, filtered vector search in plain SQL.
- Harder: we tune HNSW parameters and memory ourselves; filtered ANN relies on pgvector ≥ 0.8 iterative index scans, while per-user wardrobe search (hundreds of rows) uses a B-tree on `user_id` and an exact scan, not HNSW; heavy re-embedding runs off-peak.
- We will monitor: vector query p95, index size versus RAM, recall on the eval set, `pg_stat_statements` for slow queries.
- Revisit when: HNSW index size exceeds ~8 GB (~25 % of RAM; roughly 1.5M 1024-dim vectors, or 3M with `halfvec`), vector query p95 exceeds 100 ms after tuning, or vector load raises simple-endpoint p95 above 200 ms.
