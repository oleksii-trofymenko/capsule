# Tasks

- One folder per epic (`E0/`, `E1/`, …), one file per card: `<ID>-<slug>.md`, from `_template.md`.
- The card is the memory of the work. A new chat starts from the card, not from an old conversation.
- Status lives in the card: `todo` → `in progress` → `review` → `qa` → `done` (or `blocked`, with the reason).
- Size: S ≤ 2 hours, M ≤ 1 day. Anything larger is split.
- Run a card with `/task <ID>`.

## Epics

| Epic | Goal | Demo at the end |
| --- | --- | --- |
| E0 | Foundation and agent harness | Clean clone → `make up` → healthy API; CI green; ADRs 001–010 accepted; design tokens and flows ready |
| E1 | Security and users | Sign up and sign in on a phone through the tunnel |
| E2 | Observability | Dashboards and alerts before the first AI feature |
| E3 | MVP consultation (text) | Ask → follow-up → streamed guide; eval v1 in CI |
| E4 | Budget and products | Real products in the guide, budget enforced by code |
| E5 | Trends (RAG) | Guides cite current trends |
| E6 | Photo and voice | Photo and voice in, guide out |
| E7 | Performance, offline, reliability | Offline mode, load and chaos reports |
| E8 | Benchmark and release | Local vs cloud report, test builds in TestFlight and Internal testing |

## E0 order

E0-01 first. Then E0-03, E0-04, E0-06, E0-08 and E0-09 can run in parallel. E0-05 after E0-04; E0-07 after E0-06. E0-10 (align docs with the accepted ADRs) before E0-06. E0-11 (agent and skill rules vs ADR-010) before the E3 gateway card.

## E1 order

1. E1-01 (threat model) first. E1-18 (Expo scaffold) does not depend on it and can start at the same time.
2. In parallel: the decision cards E1-02 (ADR-014), E1-03 (retention ADR), E1-04 (ADR-015), plus E1-19 (UI primitives ADR) after E1-18. The owner must accept these ADRs before code that depends on them starts.
3. After E1-02 and E1-03: E1-11 (A2/S1 design) and E1-21 (Privacy notice). After E1-02 and E1-04: E1-05a (Alembic) and E1-05b (JWT key plumbing) in parallel, then E1-05d (key loading, database-error logs), E1-05 (guest credential, tables, principal) and E1-05c (refresh and logout), in that order.
4. After E1-05: E1-06, E1-07 and E1-08 in parallel; E1-12 after E1-05c. E1-15 (quick tunnel) after E1-08: no public URL before guest creation is rate limited. E1-20 (base components) after E1-19 and E1-11.
5. E1-09 after E1-07; E1-10 after E1-09. E1-13 after E1-07, E1-11, E1-12 and E1-20.
6. E1-14 after E1-09, E1-12 and E1-20. It can run alongside E1-13.
7. E1-22 (API edge hardening) after E1-05, in parallel with step 4.
8. E1-16 (demo) last: it needs E1-08, E1-13, E1-14, E1-15, E1-22 and E1-26.

E1-23 (Postgres backups) after E1-03 and E1-04. It is not needed for the demo, but it must be in place before accounts hold real data.

Before external beta, not part of the E1 demo:
- E1-17 (password reset by email).
- E1-24 (email field encryption) after E1-04 and E1-07.
- E1-25 (host disk and SeaweedFS keys) after E1-04.
- E1-30 (least-privilege S3 identity for `api`) after E1-25. The first card that gives `api` S3 access lists E1-30 in Depends on.

Hardening follow-ups from E1-05a and E1-05b:
- E1-26 (separate Postgres roles) after E1-05, in parallel with step 4; E1-16 needs it.
- E1-27 (migration lock timeout), E1-28 (`REDIS_URL` error leak) and E1-29 (`.env` ACL after a failed first run) at any time.
- E1-31 (module-boundary lint) after E1-05.

E2-02 (key-age panel) belongs with the first E2 Grafana card.

E8-01 and E8-02 (named tunnel, pinning, bundle scan) wait for the owner's domain purchase. E8-01 may be pulled forward before E3 streaming, because quick tunnels do not support SSE.
