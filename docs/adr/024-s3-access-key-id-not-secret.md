# ADR-024: The SeaweedFS S3 access key ID is an identifier; one SeaweedFS startup log line may contain it

- Status: proposed
- Date: 2026-10-27
- Deciders: Orchestrator, security-engineer, platform-engineer
- Related: E1-05b, ADR-015, ADR-008, ADR-019, E1-25, E2-01

## Context

ADR-015 says CI masks every generated value and "CI fails if any of those values appears in the stack logs". E1-05b added every `.env` value to that check. The CI `stack` job then failed on one line, which SeaweedFS 4.48 writes at every start (INFO, `auth_credentials.go:582`, no `]` after the line number):

```text
Added admin identity from AWS environment variables: name=admin-<first 8 hex of the ID>, accessKey=<SEAWEEDFS_S3_ACCESS_KEY>
```

- **What the value is:** `SEAWEEDFS_S3_ACCESS_KEY` is the SigV4 access key ID. Every signed request sends it in clear in the `Authorization` header, and every presigned URL carries it as `X-Amz-Credential`.
- **What it cannot do:** it cannot sign anything without `SEAWEEDFS_S3_SECRET_KEY`, a 192-bit random value.
- **Where it is used:** S3 is reachable only on the internal `backend` network (no published port).
- **What else is in the logs (checked 2026-10-27):** the secret key does not appear. No other generated value appears. A wrong-secret request (403) at the default verbosity logs no line with the ID.
- **Constraints:** SeaweedFS has no flag that silences this one line without hiding other logs. Moving the S3 identity to a config file (ADR-015 option 5) is deferred.

## Options

1. **Line filter (chosen).** Before the leak grep, drop only this message, and only from the `seaweedfs` service. The ID anywhere else, or in any other service, still fails. If an upgrade changes the message, the line is no longer dropped, so CI fails closed. Cost: one regex to maintain.
2. **Remove the ID from the leak patterns.** Simpler, but an ID that leaks somewhere new (for example into API logs next to a secret) would pass unseen.
3. **Move the S3 identity to an identities file now.** It may stop the log line. This is untested, and it touches three services and CI (ADR-015 option 5). It is a revisit trigger below.

## Decision

The S3 access key ID is treated as an identifier, not secret material, for one purpose only: the CI leak check ignores the SeaweedFS startup line above, from the `seaweedfs` service only. This narrows ADR-015's clause "CI fails if any of those values appears in the stack logs" for that one log line.

- Everything else in ADR-015 is unchanged. The ID stays in `.env`, stays masked in CI (`::add-mask::`), and stays in the leak-pattern file. Every other value has no exception.
- The access key ID must never be reused as secret material: not as a seed, a salt, a key prefix or part of any other secret.
- The filter is the `adr024` regex in `.github/workflows/ci.yml` (job `stack`, `leak-check.sh`).
  - It matches the full line shape, from the `seaweedfs-N  | ` prefix to the end of the line: `name=admin-<8 hex>, accessKey=<48 lowercase hex>`.
  - It fails closed. A line with appended text (for example a second value after the ID) or reworded text is not dropped, so any generated value in it fails CI.
  - Its self-test must catch three lines: the same message from another service, the real line with text appended, and a reworded line.

## Consequences

- **Easier:** the leak check covers every `.env` value, as ADR-015 asks, and CI is green.
- **Harder:**
  - A SeaweedFS upgrade that rewords the line fails CI until the regex is updated. That is intended.
  - Raising SeaweedFS `-v` above the default needs the leak check re-run (comment in `compose.base.yml`).
- **We will monitor:** the CI `stack` leak check.
- **Revisit when:**
  - E1-25 moves the SeaweedFS config into `secrets/` and the S3 identity moves to an identities file. If that stops this log line, withdraw this ADR and remove the filter.
  - A SeaweedFS upgrade.
  - The cloud move, when the S3 provider and its logs change.
