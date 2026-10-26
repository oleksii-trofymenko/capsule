---
name: db-migration
description: Create a safe Alembic migration with the right indexes and query plans. Use whenever a table, column, index or constraint changes.
---

# Database migration

1. **Model the query first.** Write down the real queries the feature runs (filters, sort, limit). The schema and indexes follow from them.
2. **Migration.** `alembic revision` with a descriptive name. One concern per migration. Both `upgrade` and `downgrade` implemented.
3. **Safe on a live table.** New columns nullable or with a default; create indexes `CONCURRENTLY` on large tables; split destructive changes (add → backfill → switch → drop) across releases.
4. **Indexes.** One per frequent query shape; composite in filter order; no unused indexes. pgvector columns: choose HNSW or IVFFlat and record why in the PR.
5. **Plans.** Run `EXPLAIN ANALYZE` before and after on realistic seed data. No sequential scans on large tables in hot paths. Paste both plans into the PR.
6. **Test.** Upgrade and downgrade run cleanly in the integration test database.
7. **Personal data.** Mark columns holding personal data in the model docstring; check retention and deletion rules in `docs/security.md` (from E1).
