---
name: formal-planning
description: Invoke formal-planning with the skill tool before writing an implementation plan after an approved design, or when materially risky multi-stage work needs explicit dependencies and coordinated checkpoints, especially migrations, public-interface rollouts, cross-system changes, difficult rollback, or weak verification.
metadata:
  source: personal-skills
  replaces: writing-plans
---

# Formal Planning

Create an execution map only when dependencies, risk, or coordination justify one. Execute routine work safely in-session instead of planning it.

## Workflow

1. Confirm requirements or an approved design are sufficient and formal planning is warranted. Route unresolved consequential design questions to `formal-design`.
2. Inspect repository structure, relevant implementation, tests, operational constraints, and prior decisions.
3. Map dependencies and order tasks so each produces a coherent, verifiable outcome. Identify exact files where repository evidence permits; mark genuinely unresolved locations explicitly.
4. Place checkpoints around risky transitions, external coordination, destructive operations, and difficult rollback.
5. Self-review requirement coverage, dependency order, scope, and whether each acceptance check proves its task goal.

## Plan Contract

Each task states:

- **Files:** exact files to create, modify, or verify.
- **Goal:** the observable result, not a list of keystrokes.
- **Dependencies:** prior tasks, decisions, systems, or owners required.
- **Acceptance checks:** commands or observations that prove completion.
- **Risk and rollback:** when failure has material impact or reversal is nontrivial.

Keep task size natural. Do not require tiny steps, full code listings, TDD, commits per task, subagents, or a particular execution workflow.
