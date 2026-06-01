# personal-skills

Condensed, general-purpose skills distilled from third-party skill collections and tuned to a single end-to-end workflow:

```
brainstorming ──► writing-plans ──► executing-plans ──► reviewing-code
     │                                                        ▲
     └── grill-me (stress-test an existing design/plan) ──────┘
```

## Skills

| Skill | Use it when | Distilled from |
|-------|-------------|----------------|
| `brainstorming` | A fuzzy idea needs to become an approved design/spec before any code. | superpowers:brainstorming |
| `grill-me` | You already have a plan/design and want it interrogated and stress-tested. | obra:grill-me, obra:grill-with-docs |
| `writing-plans` | You have an approved spec and need a bite-sized, TDD-structured implementation plan. | superpowers:writing-plans |
| `executing-plans` | You have a plan to implement — fresh sub-agent per task, two-stage review, parallel where independent. | superpowers:executing-plans, subagent-driven-development, dispatching-parallel-agents |
| `reviewing-code` | Reviewing a diff/branch/PR, or acting on review feedback. | superpowers:requesting/receiving-code-review, obra:review |

## Conventions baked in
- **Full rigor:** TDD (test-first), git worktree isolation, commit-per-step, two-stage spec+quality review.
- **Plans** save to `~/agents/plans/YYYY-MM-DD-<name>.md`; **specs** to `~/agents/specs/YYYY-MM-DD-<topic>-design.md`. Project/user preferences override.
- **Sub-agents** never inherit session context or read plan files — the coordinator hands them exactly what they need.

## Layout
```
skills/<skill-name>/SKILL.md           # required, the skill itself
skills/<skill-name>/*-prompt.md        # sub-agent dispatch templates (executing-plans, reviewing-code)
_superseded/                            # earlier project-specific skills kept for reference, not active
```

`_superseded/code-reviewer/` is the previous VO-COLOS-specific review skill,
replaced by the general-purpose `reviewing-code`. Kept because it encodes real
project conventions (delegation model, protocol/error-handling rules) — fold it
back into the VO-COLOS repo as a project-level skill if useful.
