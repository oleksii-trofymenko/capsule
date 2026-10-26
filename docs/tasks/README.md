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

E0-01 first. Then E0-03, E0-04, E0-06, E0-08 and E0-09 can run in parallel. E0-05 after E0-04; E0-07 after E0-06. E0-10 (align docs with the accepted ADRs) before E0-06.
