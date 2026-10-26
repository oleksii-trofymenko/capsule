# ADR-008: S3 API for media; SeaweedFS on the home server; TTL deletion enforced by our own job

- Status: proposed
- Date: 2026-10-26
- Deciders: Orchestrator, backend-engineer, security-engineer, project owner
- Related: E0-03, ADR-005, ADR-006, ADR-015 (planned), blueprint §3, §4, §14 (risks)

## Context

Users upload outfit photos (≤ 1 MB after on-device compression) and voice notes. These are personal data: they must be deleted after a short TTL, never logged and never used to rate appearance. Moving to the cloud must stay a config change, so the app must talk to a standard API. The blueprint chose MinIO, but its community edition stopped shipping images in October 2025 and was archived in April 2026, so it no longer receives security fixes.

## Options

1. **S3 API in code; SeaweedFS (Apache 2.0) as the local store** — actively developed, S3-compatible including lifecycle rules, presigned URLs and server-side encryption; light enough for one node. Cons: its configuration and IAM model differ from MinIO's; smaller ecosystem of guides.
2. **S3 API in code; Garage (AGPLv3)** — very light single binary. Lost: lifecycle/expiry support is limited or missing, so the TTL guarantee would rest only on our job; smaller community.
3. **MinIO, pinned to the last community image** — familiar and well documented. Lost: archived, no security fixes, for a store that holds user photos.

## Decision

All media code uses only the S3 API (bucket and endpoint from config); locally the store is SeaweedFS, and TTL deletion is guaranteed by a scheduled worker job that deletes expired objects and their database rows, with bucket lifecycle rules as a second line of defence.

## Consequences

- Easier: moving to AWS S3, Cloudflare R2 or another provider is an endpoint and credentials change; deletion does not depend on any one store's lifecycle support.
- Harder: we own the TTL sweeper and its tests; SeaweedFS needs its own backup and upgrade routine.
- We will monitor: objects older than TTL (must be zero), storage size, sweeper failures.
- Revisit when: SeaweedFS shows S3-compatibility gaps in our flows, its maintenance slows, or we move media to a managed cloud store.
