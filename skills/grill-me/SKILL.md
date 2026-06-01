---
name: grill-me
description: Use when the user has an existing plan, design, or approach and wants it stress-tested — "grill me", "poke holes in this", "interrogate my design", or to resolve open decisions before committing. Relentless one-question-at-a-time interrogation, not design-from-scratch.
---

# Grill Me

Interview the user relentlessly about every aspect of their plan until you reach genuine shared understanding. Walk down each branch of the design tree, resolving dependencies between decisions one by one.

**Announce at start:** "I'm using the grill-me skill — I'll interrogate this one question at a time."

## The Method

- **One question at a time.** Wait for the answer before the next. Never batch.
- **Always recommend.** For every question, give your recommended answer and a one-line why. The user is reacting to a proposal, not facing a blank prompt.
- **Explore, don't ask, when the codebase knows.** If a question is answerable by reading code, docs, or git history, go read it and report what you found instead of asking.
- **Resolve dependencies in order.** Don't ask about a leaf decision while its parent is still open. Surface the decision tree and walk it.
- **Probe with concrete scenarios.** When a relationship or boundary is fuzzy, invent a specific edge-case scenario that forces precision. "What happens when two of these arrive at once?"
- **Surface contradictions immediately.** If an answer conflicts with an earlier answer, the stated requirements, or the code, stop and name the conflict: "You just said X, but earlier/the code says Y — which holds?"
- **Sharpen fuzzy language.** When a term is vague or overloaded, propose a precise canonical meaning: "You keep saying 'account' — do you mean the user or the billing entity? They behave differently here."

## When to stop

Stop when every branch of the tree is resolved and you could implement the thing without guessing — not before. If new branches keep opening, keep going. If the user tries to cut it short with decisions still open, name the specific unresolved risks so they're choosing knowingly.

## Optional: capture decisions as you go

If the project keeps a glossary or decision log (`CONTEXT.md`, `docs/adr/`, a spec file), update it inline the moment a term or decision is settled — don't batch. Offer an ADR only when a decision is **hard to reverse**, **surprising without context**, AND **the result of a real trade-off**; if any of the three is missing, skip it.

## Relationship to other skills

- Building a design from a vague idea (not stress-testing an existing one) → use `brainstorming`.
- Once the design survives grilling → hand off to `writing-plans`.
