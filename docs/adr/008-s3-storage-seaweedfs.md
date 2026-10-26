# ADR-008: S3 API for media; SeaweedFS on the home server; deletion within 24 h enforced by our own job

- Status: accepted (2026-10-26)
- Date: 2026-10-26
- Deciders: Orchestrator, backend-engineer, security-engineer, project owner
- Related: E0-03, ADR-005, ADR-006, ADR-014 (planned), ADR-015 (planned), blueprint §3, §4, §12, §14

## Context

Users upload outfit photos (≤ 1 MB after on-device compression) and voice notes. These are personal data: they must be deleted soon after processing, never logged and never used to rate appearance, and a stolen disk must not expose them. Only the API is reachable through the tunnel. Moving to the cloud must stay a config change, so the app talks a standard API. The blueprint chose MinIO, but its community edition stopped shipping images in October 2025 and was archived in April 2026, so it no longer gets security fixes ([InfoQ](https://infoq.com/news/2025/12/minio-s3-api-alternatives/), [Pinggy](https://pinggy.io/blog/minio_archived_self_hosted_s3_alternatives/)).

## Options

1. **S3 API in code; SeaweedFS (Apache 2.0) as the local store** — actively developed, single-node friendly, documents lifecycle expiration, presigned URLs and server-side encryption (to be verified by an integration test before `media` relies on them). Cons: configuration and IAM model differ from MinIO's; smaller ecosystem of guides.
2. **S3 API in code; Garage (AGPLv3)** — very light single binary. Lost: no SSE-S3/KMS encryption at rest (SSE-C only), no bucket policies, and a design aimed at multi-site clusters rather than one node; smaller community.
3. **MinIO, pinned to the last community image** — familiar and well documented. Lost: archived, no security fixes, for a store that holds user photos.

## Decision

All media code uses only the S3 API (bucket and endpoint from config) against private buckets reachable only on the internal network; uploads go through the API (size and type validation, EXIF stripped before storage); media are encrypted at rest and deleted after processing and in any case within 24 h (value in config, upper bound fixed here) by a scheduled worker job, with bucket lifecycle rules as a second line of defence; locally the store is SeaweedFS.

## Consequences

- Easier: moving to AWS S3, Cloudflare R2 or another provider is an endpoint and credentials change; deletion does not depend on any one store's lifecycle support.
- Harder: we own the deletion job and its tests; the media bucket is never backed up (ephemeral by design), so the blueprint §12 backup plan covers Postgres only; if presigned URLs are ever used, each is single-object, single-method, expires in ≤ 5 minutes and is issued after an ownership check; SeaweedFS needs an upgrade routine.
- We will monitor: objects older than 24 h (must be zero), storage size, deletion-job failures.
- Revisit when: an S3 call used by `media` fails against SeaweedFS in the integration suite, no SeaweedFS release with security fixes ships for 6 months, or we move media to a managed cloud store.
