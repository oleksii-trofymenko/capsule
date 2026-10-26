---
name: adr
description: Write an Architecture Decision Record from the template and register it in the index. Use when a decision affects structure, dependencies, data, security or cost, or when work conflicts with an accepted ADR.
---

# ADR

1. **Number.** Next free number in `docs/adr/README.md` (or the planned number listed there). File: `docs/adr/NNN-short-title.md`.
2. **Template.** Copy `docs/adr/000-template.md`. One page at most.
3. **Context.** The problem and constraints in plain words, with numbers where they exist (VRAM, latency, cost, team size).
4. **Options.** At least two real alternatives, each with why it lost.
5. **Decision.** One sentence a newcomer can act on.
6. **Consequences.** What gets easier, what gets harder, what we will monitor, and the trigger to revisit.
7. **Status.** `proposed` until the Orchestrator accepts. Accepted ADRs are never edited; a change is a new ADR that marks the old one `superseded by ADR-NNN`.
8. **Index.** Add a row to `docs/adr/README.md`.
