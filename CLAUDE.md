# personal-skills — agent router

A workflow of skills for taking work from idea → design → plan → implementation → review.
These skills are **not auto-discovered** (they don't live in `~/.claude/skills`). When you are
working in or pointed at this repo, use this file to pick the right one. Human-oriented overview
is in `README.md`.

## How to use a skill

1. Pick a skill from the table below.
2. **Read `skills/<name>/SKILL.md` in full and follow it exactly** — including its "Announce at start" line.
3. Skills with `*-prompt.md` files (`executing-plans`, `reviewing-code`) dispatch sub-agents.
   **Sub-agents cannot read these skills** — fill the template and paste its text into the
   sub-agent's prompt. Hand them exactly what they need; never tell them to "read the plan/skill."

## Route by intent — start here

| Situation / trigger phrases | Skill | Needs to exist first | Use this, NOT… |
|---|---|---|---|
| Fuzzy idea; new feature/component/behavior change; requirements unclear. "let's build", "I want to add", "how should we do X" | `brainstorming` | nothing | not `writing-plans` (no design yet); not `grill-me` (nothing to stress-test) |
| An existing plan/design to pressure-test. "grill me", "poke holes", "stress-test this", "what am I missing" | `grill-me` | a draft plan or design | not `brainstorming` (that builds from scratch) |
| Approved design, need an implementation plan. "plan this", "write the plan", "break it down" | `writing-plans` | an **approved** spec/design | not `executing-plans` (no plan yet) |
| A written plan to implement. "execute the plan", "implement this", "build it" | `executing-plans` | a **saved plan file** | not `writing-plans` (plan already exists) |
| Review a diff/branch/PR, or act on review feedback. "review this", "check the PR", "is this good?" | `reviewing-code` | a diff / branch / PR | — |
| The coding standard itself (reference). | `development-guidelines` | — | **not invoked directly** — it's the source the reviewers and `writing-plans` enforce |

If two seem to fit, prefer the earliest unmet precondition (e.g. no approved design yet → `brainstorming`, regardless of what was asked).

## Hard gates (navigation rules, not suggestions)

- **No code before an approved design.** Any build/feature/behavior-change request → `brainstorming` first, even "simple" ones.
- **No execution before a written plan.** Implementation work → there must be a plan from `writing-plans`.
- **Reviews enforce `development-guidelines`** (surgical changes, simplicity/YAGNI, verifiable goals) as a hard gate — a violation is at least an Important finding.

## The workflow

```
brainstorming ──► writing-plans ──► executing-plans ──► reviewing-code
     │              (approved        (fresh sub-agent       (also used as the
     │               design in)       per task, parallel     final gate above)
     │                                where independent)
     └── grill-me (stress-test an existing design/plan, then re-enter above)
```

`development-guidelines` sits under the whole flow as the coding standard the others reference.
