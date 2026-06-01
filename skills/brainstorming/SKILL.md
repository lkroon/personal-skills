---
name: brainstorming
description: Use before any creative or build work — new features, components, behavior changes, or whenever requirements are fuzzy — and before writing code or a plan.
---

# Brainstorming Ideas Into Designs

Turn a rough idea into an approved design through collaborative dialogue, then hand off to `writing-plans`. The output is a written, user-approved spec — not code.

**Announce at start:** "I'm using the brainstorming skill to shape this into a design."

<HARD-GATE>
Do NOT write code, scaffold, or invoke any implementation/plan skill until you have presented a design AND the user has approved it. Applies to EVERY task regardless of perceived simplicity. "Too simple to need a design" is the rationalization that causes the most wasted work — the design can be three sentences, but it must be presented and approved.
</HARD-GATE>

## Checklist (create a todo for each, do in order)

1. **Explore context** — read relevant files, docs, recent commits before asking anything.
2. **Scope check** — if the request spans multiple independent subsystems, say so first and decompose into sub-projects (each gets its own spec → plan → build). Brainstorm the first one.
3. **Ask clarifying questions** — ONE at a time. Prefer multiple-choice. Focus on purpose, constraints, success criteria. If a question is answerable from the codebase, go read it instead of asking.
4. **Propose 2-3 approaches** — with trade-offs; lead with your recommendation and why.
5. **Present the design in sections** — scale each section to its complexity (a sentence to ~250 words). Cover architecture, components, data flow, error handling, testing. Get approval after each section before moving on.
6. **Write the spec** — save to `~/agents/specs/YYYY-MM-DD-<topic>-design.md` (user/project preference overrides). Commit if in a repo.
7. **Spec self-review** — fresh-eyes pass: kill placeholders/TBDs, check internal consistency, confirm single-plan scope, resolve any requirement that could be read two ways. Fix inline.
8. **User review gate** — "Spec written to `<path>`. Review it and tell me what to change before I write the plan." Wait. If changes requested, edit and re-run step 7.
9. **Hand off** — invoke `writing-plans`. That is the ONLY skill you invoke next.

## Design principles

- **YAGNI ruthlessly** — strip every feature not asked for.
- **Isolation & clarity** — break the system into units with one purpose, well-defined interfaces, independently testable. For each: what does it do, how is it used, what does it depend on? Prefer small, focused files.
- **Existing codebases** — explore structure first, follow established patterns, include only targeted improvements that serve the goal. No unrelated refactoring.
- **Incremental validation** — present, get approval, then proceed. Go back and re-clarify whenever something stops making sense.

## When grilling is the better tool

If the user already has a design/plan and wants it stress-tested (not built up from scratch), use `grill-me` instead.
