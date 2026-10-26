---
name: prompt-change
description: Change a prompt safely — new version, eval against baseline, rollout by config. Use whenever any prompt text changes.
---

# Prompt change

1. **Never edit in place.** Copy `ml/prompts/<node>/v<N>.md` to `v<N+1>.md` and edit the copy.
2. **Header.** At the top of the new file: what changed, why, which eval cases it targets.
3. **Separation.** Instructions in the system part; user text, web text and product data in clearly delimited data blocks, labelled as untrusted.
4. **Rules kept.** The prompt must keep: explain "why", rank items (key pieces, base, details), never comment on bodies or appearance, English (en-GB), EUR.
5. **Eval.** Run the `eval-run` skill with the new version. Compare with the current baseline.
6. **Decision.** Ship only if quality is not lower, budget compliance is 100% and hallucinated products are 0. Otherwise iterate or drop.
7. **Rollout.** Switch the active version in config, not in code. Keep the old version file.
8. **PR.** Include the eval table (before → after) and three example answers that changed.
