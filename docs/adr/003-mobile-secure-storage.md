# ADR-003: Tokens in expo-secure-store; cache in MMKV and SQLite

- Status: proposed
- Date: 2026-10-26
- Deciders: Orchestrator, mobile-engineer, security-engineer, project owner
- Related: E0-03, ADR-001, ADR-002, ADR-014 (planned), blueprint §10

## Context

The app holds a short-lived access token and a rotating refresh token (ADR-014, planned). Blueprint §10 requires tokens in Keychain/Keystore and zero secrets in plain storage. It also needs a fast key-value store for the persisted query cache and settings, and structured storage for guide history and queued messages that survives restarts offline.

## Options

1. **expo-secure-store for tokens; MMKV for key-value cache; expo-sqlite for history and the outgoing queue** — tokens are protected by the OS keystore; MMKV is synchronous and fast for the query-cache persister; SQLite handles structured, queryable offline data. Cons: three storage APIs to wrap behind one `shared/storage` module.
2. **AsyncStorage for everything** — simplest, one API. Lost: unencrypted, so tokens there would break the security requirement; slow for a large persisted cache.
3. **Encrypted MMKV for everything, including tokens** — one fast API. Lost: the encryption key itself must live somewhere, which brings us back to the keystore; the OS keystore is the stronger, audited boundary for credentials.

## Decision

Tokens and other credentials live only in expo-secure-store; the query cache and settings use MMKV; offline history and the outgoing message queue use expo-sqlite; all access goes through `apps/mobile/shared/storage`.

## Consequences

- Easier: one clear rule for reviewers ("credentials → secure-store, nothing else"); fast cold start with a synchronous cache.
- Harder: three backends to test; logout and account deletion must wipe all three.
- We will monitor: bundle scan for secrets, a test that logout clears every store.
- Revisit when: a storage library loses New Architecture support, or store review flags our storage handling.
