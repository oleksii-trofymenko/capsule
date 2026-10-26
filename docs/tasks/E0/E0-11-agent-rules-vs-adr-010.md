# E0-11 · Align agent and skill rules with ADR-010 and the other accepted ADRs

| Field | Value |
| --- | --- |
| Status | review |
| Owner | Orchestrator (with ai-engineer as reviewer) |
| Reviewers | code-reviewer, ai-engineer |
| Estimate | S |
| Metric | n/a — harness and docs only; prevents the E3 gateway card building to old names |
| Depends on | E0-10 |
| ADRs | 010 (and a sweep of 001–004, 007, 009, 018, 019) |
| Design spec | none |

## Why

The `agent-node` skill names model aliases (`fast`, `guide`, `vision`) and an "invalid → fallback alias" rule, while ADR-010 fixes logical route names (`agent-parse`, `agent-guide`, `vision`, `embed`) and no cloud route at €0. Agents on E3 read the skill first.

## Acceptance criteria

- [x] `.claude/skills/agent-node/SKILL.md` uses ADR-010 route names; a model fallback means another local route, never a cloud route while the budget is €0.
- [x] `.claude/agents/ai-engineer.md` and `ml/CLAUDE.md` fallback wording checked against ADR-010 and fixed if needed.
- [x] Sweep of `.claude/**`, module `CLAUDE.md` files and `docs/blueprint.md` against ADR-001–004, 007, 009, 018, 019; conflicts fixed or listed.
- [x] `.claude/skills/new-endpoint/SKILL.md` checklist gains one line: the first endpoint that accepts user input triggers card E1-06 (Schemathesis, per ADR-020).
- [ ] Tests: none (docs only); CI green.

## Allowed files

- `.claude/**`, `**/CLAUDE.md`, `docs/blueprint.md`, `docs/tasks/E0/E0-11-agent-rules-vs-adr-010.md`

## Out of scope

- Changing any decision; ADRs are not edited.

## Analytics events

- none

## Notes (filled while working)

- Plan approved: 2026-10-26 by the owner ("continue with E0-11").
- Decisions:
  - Model calls (agent-node, ai-engineer, ml, apps/api, blueprint §6): `AsyncOpenAI` to the LiteLLM gateway with route names only, `max_retries=0`, explicit timeout. Two failure paths kept apart: gateway errors/timeouts → the route's configured local fallback (model already resident in the VRAM budget) or nothing; schema-invalid output → one repair retry on the same route → typed failure → "try again later" (checkpoint kept). Per-route timeouts are the only busy-GPU signal (Ollama queues); timeouts nest route × (1 + fallbacks) < node < graph. Chosen by the Orchestrator on ai-engineer's recommendation; ADR-010 unchanged.
  - Checkpoints: `agent_checkpoint` schema by an Alembic migration (backend-engineer card), pinned package, `search_path`, deleted by a SAQ job on close, TTL expiry and "Delete my data".
  - Tracing: one source per model call (gateway callback or node), chosen in the E3 gateway card; records the resolved model.
  - Sweep fixed 21 conflicts across 17 files: release (store/EAS rollout, not flags; source maps; `/v1/ready`), load-test (guest path), security-check (audit and bump rules), db-migration (HNSW vs B-tree), mobile-screen (both themes), eval-run (routes, VRAM settings, fallback rate), agents (platform `ci-ok`, product-designer reads docs/design, mobile dependency rule), apps/mobile (storage, dev build, consent, UI-primitives ADR, borders), apps/api (route names, Ruff boundaries, migrations, SAQ, uvicorn, dev-only test tools), infra (digest pins, compose.test), blueprint (§4–§13 lines, precedence note, E0 roadmap ticked).
  - Blueprint §11 alerts split in two — "try again later" > 1 % of consultations for 10 min (99 % SLO) and gateway fallback rate > 30 % on any route for 10 min. Thresholds proposed by ai-engineer; marked "proposed" in the blueprint until the owner confirms.
- Harness rules beyond the ADRs (fallback only to a model already resident in VRAM; checkpoint migration copies `checkpoint_migrations`; one tracing source): Orchestrator decisions on ai-engineer advice — the E3 gateway card turns them into ADR-011/012 material if the owner treats them as architecture.
- Reviews: ai-engineer request changes (fallback paths mixed, missing busy-GPU trigger, stacked retries, VRAM rule, checkpoint ownership, tracing source, eval contamination, alert split) → applied. code-reviewer request changes (same fallback blocker + 8 suggestions) → applied.
- Numbers: 18 files changed (17 rule/doc files + this card) in four commits (blueprint commits separate); 21 conflicts fixed; 0 ADRs edited.
- Left for later (listed, not fixed here):
  - security-check skill gaps: media (encrypted at rest, private buckets, ≤ 24 h, presigned limits — ADR-008); mobile (MMKV excluded from backup, wipe on logout/reinstall — ADR-003; Sentry/PostHog privacy config — ADR-004); LLM (no cloud route; photo route needs security-engineer sign-off — ADR-010).
  - security-engineer agent: reference the ADR-018/019 bump rules. product-analyst agent: events only after usage consent.
  - blueprint §9 CI pipeline line (~:276) doesn't mention `ci-ok` or path-skipped jobs.
  - E3 gateway card: VRAM budget numbers (ADR-011/012), where the circuit breaker lives (blueprint §10), and a test that a client timeout really stops generation in Ollama through LiteLLM.
  - Checkpoint TTL value comes from the E1 guest-data retention ADR.
