# ADR-002: TanStack Query for server state and offline, Zustand for local state

- Status: proposed
- Date: 2026-10-26
- Deciders: Orchestrator, mobile-engineer, project owner
- Related: E0-03, ADR-001, ADR-003, blueprint §4, §10

## Context

Most app data comes from the API: profile, wardrobe, consultation history, guides. It needs caching, retries, background refresh and offline reading (blueprint §10: guide history available offline, queued messages sent on reconnect). Truly local state is small: draft message, onboarding step, UI preferences. Mixing the two in one store is the usual source of stale data and hand-written loading flags, and two offline stores for the same data would be two sources of truth.

## Options

1. **TanStack Query + Zustand** — Query owns everything that comes from the server, including offline: a persisted cache for history and persisted paused mutations replayed on reconnect; Zustand holds a few small local stores with no boilerplate. Cons: two libraries, and the team must keep the boundary clean.
2. **Redux Toolkit + RTK Query** — one ecosystem for both kinds of state, strong devtools. Lost: more ceremony for a small app, and offline persistence of the query cache is less direct than TanStack's persister.
3. **React Context + `fetch` hooks** — no dependencies. Lost: we would hand-write caching, retries, deduplication and offline replay, which is exactly the code that breaks.

## Decision

All server data goes through TanStack Query: offline history is the persisted query cache (MMKV persister, ADR-003) and queued messages are persisted paused mutations; only client-only state lives in small Zustand stores, never copies of server data. Packages: `@tanstack/react-query`, `@tanstack/react-query-persist-client` with a sync storage persister, `@react-native-community/netinfo` (wired to `onlineManager`), `AppState` → `focusManager`, `zustand`.

## Consequences

- Easier: loading, error and retry states come for free; offline history and replay use built-in features; one offline mechanism.
- Harder: persisted mutations need `setMutationDefaults` per mutation key (functions are not serialised) and `resumePausedMutations()` after hydration; every queued send carries a client-generated idempotency key (contract change, backend-engineer); persist only allow-listed queries (`shouldDehydrateQuery`) with `gcTime` ≥ the persister's `maxAge`.
- We will monitor: memory after a 10-minute session, cache hydration time at cold start, stale-data bugs in QA.
- Revisit when: real-time sync (e.g. multi-device chat) needs a different model, or offline needs outgrow query-cache persistence (see ADR-003 triggers).
