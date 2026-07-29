---
name: architecture-analysis
description: Use when the user explicitly requests an architecture audit, architecture analysis, deepening opportunities, consolidation of tightly coupled modules, or codebase-wide refactoring opportunities for testability and navigability.
metadata:
  source: https://github.com/mattpocock/skills
  source-revision: aaf2453f
  source-skill: improve-codebase-architecture
---

# Architecture Analysis

Surface architectural friction and propose **deepening opportunities** — refactors that turn shallow modules into deep ones. The aim is testability and AI-navigability.

## Glossary

Use these terms exactly in every suggestion. Consistent language is the point — don't drift into "component," "service," "API," or "boundary." Full definitions in [LANGUAGE.md](LANGUAGE.md).

- **Module** — anything with an interface and an implementation (function, class, package, slice).
- **Interface** — everything a caller must know to use the module: types, invariants, error modes, ordering, config. Not just the type signature.
- **Implementation** — the code inside.
- **Depth** — leverage at the interface: a lot of behaviour behind a small interface. **Deep** = high leverage. **Shallow** = interface nearly as complex as the implementation.
- **Seam** — where an interface lives; a place behaviour can be altered without editing in place. (Use this, not "boundary.")
- **Adapter** — a concrete thing satisfying an interface at a seam.
- **Leverage** — what callers get from depth.
- **Locality** — what maintainers get from depth: change, bugs, knowledge concentrated in one place.

Key principles (see [LANGUAGE.md](LANGUAGE.md) for the full list):

- **Deletion test**: imagine deleting the module. If complexity vanishes, it was a pass-through. If complexity reappears across N callers, it was earning its keep.
- **The interface is the test surface.**
- **One adapter = hypothetical seam. Two adapters = real seam.**

This skill is _informed_ by the project's domain model. The domain language gives names to good seams; ADRs record decisions the skill should not re-litigate.

## Process

### 1. Explore

Read the project's domain glossary and any ADRs in the area you're touching first when they exist.

Explore the codebase organically and note where you experience friction:

- Where does understanding one concept require bouncing between many small modules?
- Where are modules **shallow** — interface nearly as complex as the implementation?
- Where have pure functions been extracted just for testability, but the real bugs hide in how they're called (no **locality**)?
- Where do tightly-coupled modules leak across their seams?
- Which parts of the codebase are untested, or hard to test through their current interface?

Apply the **deletion test** to anything you suspect is shallow: would deleting it concentrate complexity, or just move it? A "yes, concentrates" is the signal you want.

### 2. Present candidates

Use a concise textual audit unless the user requested a visual report or diagrams materially improve comprehension. For each candidate include:

- **Files** — which files/modules are involved
- **Problem** — why the current architecture is causing friction
- **Solution** — plain English description of what would change
- **Benefits** — explained in terms of locality and leverage, and how tests would improve
- **Recommendation strength** — one of `Strong`, `Worth exploring`, `Speculative`

End with a **Top recommendation**: which candidate you'd tackle first and why.

When a visual report is warranted, write a self-contained HTML file to the OS temp directory and tell the user its absolute path. See [HTML-REPORT.md](HTML-REPORT.md) for the report scaffold, diagram patterns, and styling guidance. Do not write the report into the repository unless the user asks.

**Use the project's domain vocabulary and [LANGUAGE.md](LANGUAGE.md) vocabulary for the architecture.** If the project defines "Order," talk about "the Order intake module" — not "the FooBarHandler," and not "the Order service."

**ADR conflicts**: if a candidate contradicts an existing ADR, only surface it when the friction is real enough to warrant revisiting the ADR. Mark the conflict clearly. Don't list every theoretical refactor an ADR forbids.

Do not propose detailed interfaces yet. Ask the user which candidate they would like to explore.

### 3. Focused clarification loop

Once the user picks a candidate, clarify its constraints, dependencies, the shape of the deepened module, what sits behind the seam, and what tests survive. Update project domain documentation only with the user's approval and only when that documentation exists or the user asks to create it.

If the user rejects a candidate for a durable, load-bearing reason, offer to record an ADR so future architecture reviews do not re-suggest it. Skip ephemeral reasons and self-evident decisions.

For alternative interfaces for the deepened module, follow [INTERFACE-DESIGN.md](INTERFACE-DESIGN.md).
