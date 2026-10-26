# ADR-002: TanStack Query for server state, Zustand for local state

- Status: proposed
- Date: 2026-10-26
- Deciders: Orchestrator, mobile-engineer, project owner
- Related: E0-03, ADR-001, ADR-003, blueprint §4, §10

## Context

Most app data comes from the API: profile, wardrobe, consultation history, guides. It needs caching, retries, background refresh and offline reading (blueprint §10: guide history available offline, queued messages sent on reconnect). Truly local state is small: draft message, onboarding step, UI preferences. Mixing the two in one store is the usual source of stale data and hand-written loading flags.

## Options

1. **TanStack Query + Zustand** — Query owns everything that comes from the server (cache, retry, invalidation, persisted cache for offline, paused mutations replayed on reconnect); Zustand holds a few small local stores with no boilerplate. Cons: two libraries, and the team must keep the boundary clean.
2. **Redux Toolkit + RTK Query** — one ecosystem for both kinds of state, strong devtools. Lost: more ceremony for a small app, and offline persistence of the query cache is less direct than TanStack's persister.
3. **React Context + `fetch` hooks** — no dependencies. Lost: we would hand-write caching, retries, deduplication and offline replay, which is exactly the code that breaks.

## Decision

All server data goes through TanStack Query (with a persisted cache for offline history); only client-only state lives in small Zustand stores, never copies of server data.

## Consequences

- Easier: loading, error and retry states come for free; offline history and replay of queued messages use built-in features.
- Harder: cache keys and invalidation rules need discipline; review checks that server data never lands in Zustand.
- We will monitor: memory after a 10-minute session, stale-data bugs reported in QA.
- Revisit when: real-time sync (e.g. multi-device chat) needs a different model, or offline needs outgrow query-cache persistence.
