## Card

<ID> · <title> — `docs/tasks/<epic>/<file>.md`

## What and why

<two or three sentences>

## How it was verified

- [ ] `make lint`
- [ ] `make test`
- [ ] `make eval` (agent, prompts or models changed)
- [ ] Manual check on device / stack: <what you did>

## Numbers

| Metric | Before | After |
| --- | --- | --- |
| | | |

## Evidence

<query plans, eval report path, screenshots of every UI state>

## Risks and rollback

<what could go wrong, how to undo>

## Checklist

- [ ] Only files allowed by the card are changed
- [ ] Contract updated first (if the API changed)
- [ ] No secrets, personal data or user photos in code, logs or fixtures
- [ ] New dependency has an ADR
- [ ] Card notes updated
