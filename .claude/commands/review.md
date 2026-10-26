---
description: Independent review of the current branch against main.
argument-hint: [card id]
---

Run an independent review of the current branch against `main`.

1. Find the card: `$ARGUMENTS` if given, otherwise from the branch name.
2. Start `code-reviewer` with the card path. In parallel, start `security-engineer` if the diff touches auth, media, prompts, secrets, dependencies or infra, and `product-designer` if it touches `apps/mobile` UI.
3. Give each reviewer only the card path and the diff range, not your opinion of the code.
4. Merge their verdicts into one list: blockers first, then suggestions, each with file and line.
