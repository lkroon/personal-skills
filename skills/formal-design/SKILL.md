---
name: formal-design
description: Use when the user explicitly requests brainstorming, a design, or a specification, or when work materially involves an architectural or public-interface decision; security, privacy, authorization, or sensitive-data impact; data migration, destructive behavior, or difficult rollback; ambiguous behavior spanning systems or ownership boundaries; a weak test oracle or otherwise difficult verification; unfamiliar technology combined with a high cost of failure; or coordinated checkpoints across multiple stages.
metadata:
  source: personal-skills
  replaces: brainstorming
---

# Formal Design

Resolve consequential uncertainty before implementation. Routine local, reversible work belongs on the direct execution route.

## Workflow

1. Confirm formal treatment is warranted by an explicit request or a material risk named in the description. Otherwise inspect, edit, verify, and report directly.
2. Inspect relevant code, documentation, constraints, and prior decisions before asking questions.
3. Clarify consequential unknowns one question at a time. Resolve minor ambiguity from repository evidence. When the user explicitly asks for a self-contained design from only the supplied request, state necessary assumptions and proceed instead of blocking on questions.
4. Present two or three viable approaches with tradeoffs and a recommendation. Omit artificial alternatives when only one is credible.
5. Present the design in appropriately sized sections and seek approval incrementally. Cover only relevant boundaries, data flow, failure behavior, compatibility, rollout, and verification.
6. Self-review for unresolved ambiguity, internal contradictions, speculative scope, and unaddressed risks. Revise before requesting final approval.

For self-contained design responses, explicitly label `Approaches`, `Tradeoffs`, `Recommendation`, and `Approval request` so the decision is auditable.

## Output

A short approved design may remain in the conversation. Save a specification only when later stages need a durable reference or the decision itself needs a record. Never require a commit or automatically hand off to planning.

## Routing

| Situation | Route |
| --- | --- |
| Clear, local, reversible implementation | Direct execution |
| Existing proposal needs pressure-testing | `grill-me` |
| Approved design needs coordinated execution checkpoints | `formal-planning` |
