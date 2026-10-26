---
description: Run a task card through the full flow — plan, implement, review, QA, accept.
argument-hint: <card id, e.g. E0-03>
---

Act as the Orchestrator from the root CLAUDE.md for card `$ARGUMENTS`.

1. Find and read `docs/tasks/*/$ARGUMENTS*.md`. If it has no metric line (a metric, an SLO or "n/a — reason"), acceptance criteria or allowed files, stop and tell me what is missing.
2. Pick the owner named on the card. If it is a specialist agent, send it a short brief (card path, linked ADRs and specs) and ask for a plan only. If the owner is the Orchestrator, draft the plan yourself with the skills the card names. If the owner is me, stop and tell me.
3. Show me the plan in five lines or fewer and wait for my OK.
4. After my OK, let the owner implement on `feat/$ARGUMENTS-<slug>`.
5. Run `code-reviewer`, plus `security-engineer` and/or `product-designer` when the card's area needs them, in parallel. Return blockers to the owner until review approves.
6. Run `qa-engineer`. Return failures to the owner until QA passes.
7. Update the card: status `done`, decisions, numbers, what is left. Propose the squash-commit message. Do not push unless I ask.
