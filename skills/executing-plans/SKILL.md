---
name: executing-plans
description: Use when you have a written implementation plan to execute, especially one with independent tasks that could be worked on in parallel, and you want isolated sub-agents and review checkpoints rather than implementing inline.
---

# Executing Plans

Execute a plan by dispatching a **fresh sub-agent per task**, reviewing each in two stages (spec compliance, then code quality), and **running independent tasks in parallel**. You stay the coordinator: you never inherit a sub-agent's context and they never inherit yours — you hand each one exactly what it needs.

**Announce at start:** "I'm using the executing-plans skill to implement this plan."

**Core principle:** Fresh sub-agent per task + two-stage review + parallel where independent = high quality, fast iteration.

**Continuous execution:** Do not check in between tasks. Execute the whole plan. The only reasons to stop: an unresolvable BLOCKER, genuine ambiguity, or all tasks done. "Should I continue?" prompts waste the user's time — they asked you to execute the plan.

## Setup (before any task)

1. **Worktree.** Work in an isolated git worktree/branch — never start implementation on main/master without explicit consent.
2. **Read the plan once.** Extract every task with full text and surrounding context. Create a TodoWrite with all tasks. Sub-agents get the task text from you — never make them read the plan file.
3. **Critical review.** Spot gaps, contradictions, or risky assumptions in the plan. Raise them before starting; don't silently work around a broken plan.
4. **Build the dependency map** (below).

## Sequential vs Parallel

```
For each task: does it share files/state with another not-yet-done task,
or depend on its output?
  └─ No, to several tasks  → dispatch those implementers IN PARALLEL
  └─ Yes / uncertain       → run SEQUENTIALLY in dependency order
```

- **Parallel dispatch:** independent tasks (different files, different subsystems, no shared state) → multiple implementer sub-agents in ONE message. Each gets a focused scope and a "don't touch other code" constraint. On return: read each summary, check for conflicts, then review each.
- **Never** run implementers in parallel if they touch the same files or depend on each other — that causes conflicts. When unsure, serialize.
- Reviews still happen per task (see below), even for parallel batches.

## Per-Task Loop

```
Dispatch implementer (implementer-prompt.md)
  → implementer asks questions?  → answer, re-dispatch
  → implements, tests (TDD), commits per step, self-reviews
Dispatch SPEC reviewer (spec-reviewer-prompt.md)
  → not compliant?  → implementer fixes → re-review  (loop until ✅)
Dispatch QUALITY reviewer (code-quality-reviewer-prompt.md)   ← only after spec ✅
  → issues?  → implementer fixes → re-review  (loop until ✅)
Mark task complete in TodoWrite
```

Spec review **always precedes** quality review. Don't move on while either has open issues.

## Implementer Status Handling

- **DONE** → proceed to spec review.
- **DONE_WITH_CONCERNS** → read the concerns. Correctness/scope concerns: resolve before review. Observations ("file getting large"): note and proceed.
- **NEEDS_CONTEXT** → provide the missing info, re-dispatch.
- **BLOCKED** → diagnose: context problem → add context, re-dispatch same model; needs more reasoning → re-dispatch stronger model; task too large → split it; plan is wrong → escalate to user. **Never** retry the same model with no change, and never ignore an escalation.

## Model Selection (cost/speed)

Use the least powerful model that fits each role.
- 1-2 files, complete spec, mechanical → fast/cheap model (most implementation tasks).
- Multi-file integration, pattern-matching, debugging → standard model.
- Architecture, design judgment, all review roles → most capable model.

## Finish

After all tasks: dispatch ONE final reviewer over the whole diff, then run the full test suite. Resolve findings, then present completion options to the user (merge / PR / further work). Use the `reviewing-code` skill's templates for all reviewer dispatches.

## Red Flags — never

- Start on main/master without consent.
- Start before all ambiguities are resolved with the user by verification (unless explicitly stated)
- Make a sub-agent read the plan file instead of giving it the task text.
- Skip a review, start quality review before spec is ✅, or move on with open issues.
- Run conflicting implementers in parallel (same files / dependency).
- Let an implementer's self-review replace actual review — both are required.
- Fix a failed task yourself (context pollution) — dispatch a fix sub-agent with specifics.
- Ignore a sub-agent's question or a BLOCKED escalation.

## Prompt Templates

- `implementer-prompt.md` — dispatch an implementer
- `spec-reviewer-prompt.md` — dispatch the spec-compliance reviewer
- `code-quality-reviewer-prompt.md` — dispatch the quality reviewer
