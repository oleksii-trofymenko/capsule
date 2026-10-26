# ADR-007: PostgreSQL 16 + pgvector as the single database; SQLAlchemy 2 (async) and Alembic

- Status: proposed
- Date: 2026-10-26
- Deciders: Orchestrator, backend-engineer, ai-engineer, project owner
- Related: E0-03, ADR-005, ADR-009, blueprint §3, §4, §10

## Context

Capsule stores users, consultations, wardrobe items, guides and feedback (relational), plus embeddings for RAG over trends and user memory. MVP scale is small: tens of thousands of trend and catalogue chunks and a wardrobe of tens to hundreds of items per user, so well under a few million vectors. Everything runs on one PC with 32 GB RAM, already shared with Redis, the worker and model inference.

## Options

1. **PostgreSQL 16 + pgvector (HNSW indexes), SQLAlchemy 2 async, Alembic migrations** — one database for data and vectors; a vector search can filter by user, budget or season in the same SQL query and transaction; one backup, one connection pool. Cons: vector search tuning shares resources with transactional load.
2. **PostgreSQL + a separate vector database (Qdrant, Weaviate)** — purpose-built ANN features and scaling. Lost: a second stateful service to run, back up and secure on the home PC, data duplicated across two stores with no shared transactions, and no gain at a few million vectors.
3. **SQLite (with a vector extension)** — zero operations. Lost: one writer at a time limits the API and worker running in parallel; weaker concurrency and migration tooling for a server.

## Decision

Use one PostgreSQL 16 database with pgvector for both relational data and embeddings, accessed through SQLAlchemy 2 (async) and changed only through Alembic migrations.

## Consequences

- Easier: one backup and restore, transactional writes of data and its embedding, filtered vector search in plain SQL.
- Harder: we tune HNSW parameters and memory ourselves; heavy re-embedding jobs must run off-peak.
- We will monitor: vector query p95, index size versus RAM, recall on the eval set, `pg_stat_statements` for slow queries.
- Revisit when: vectors exceed ~5 million, vector query p95 exceeds 100 ms after tuning, or vector load measurably hurts transactional p95.
