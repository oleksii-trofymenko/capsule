# ADR-003: Tokens in expo-secure-store (this device only); query cache in MMKV

- Status: accepted (2026-10-26)
- Date: 2026-10-26
- Deciders: Orchestrator, mobile-engineer, security-engineer, project owner
- Related: E0-03, ADR-001, ADR-002, ADR-014 (planned), blueprint §10

## Context

The app holds a short-lived access token and a rotating refresh token (ADR-014, planned). Blueprint §10 requires tokens in Keychain/Keystore and zero secrets in plain storage. It also needs a fast key-value store for the persisted query cache (ADR-002), which holds guide and wardrobe text: personal data that must not leak into OS cloud backups or survive account deletion.

## Options

1. **expo-secure-store for tokens; MMKV for the query cache and settings** — tokens are protected by the OS keystore; MMKV is synchronous and fast for the persister. Cons: two storage APIs to wrap behind one `shared/storage` module; MMKV needs a development build (ADR-001).
2. **AsyncStorage for everything** — simplest, one API. Lost: unencrypted, so tokens there would break the security requirement; slow for a large persisted cache.
3. **Encrypted MMKV for everything, including tokens** — one fast API. Lost: the encryption key itself must live somewhere, which brings us back to the keystore; the OS keystore is the stronger, audited boundary for credentials.

## Decision

Tokens and other credentials live only in expo-secure-store with `AFTER_FIRST_UNLOCK_THIS_DEVICE_ONLY` (no iCloud sync or device migration); the query cache and settings use MMKV, which holds no credentials and no photos and is excluded from OS cloud backup; expo-sqlite is deferred until a card shows a need for queryable offline data; all access goes through `apps/mobile/shared/storage`.

## Consequences

- Easier: one clear rule for reviewers ("credentials → secure-store, nothing else"); fast cold start with a synchronous cache.
- Harder: the iOS Keychain survives uninstall, so logout, account deletion and first launch after install wipe both stores; secure-store and MMKV are excluded from Android Auto Backup (config plugin) and iOS backup; the refresh token stays opaque and small (secure-store values ~2 KB); photos and voice files are not kept on the device after upload succeeds; react-native-mmkv is pinned to its Nitro-based major (needs `react-native-nitro-modules`).
- We will monitor: bundle scan for secrets, a test that logout and reinstall clear both stores, persisted cache size.
- Revisit when: MMKV hydration adds > 150 ms to cold start or the persisted cache exceeds 10 MB, a storage library drops New Architecture support, or store or security review flags our storage handling.
