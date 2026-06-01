---
name: reviewing-code
description: Use when reviewing a diff, branch, or PR, or when acting on review feedback — after completing a task or feature, before merging, when stuck, or whenever the user says "review this" or "check the PR".
---

# Reviewing Code

Two jobs: **conduct** a review (dispatch focused reviewer sub-agents over a diff) and **receive** review (act on feedback by verifying, not performing). Reviewers get precisely crafted context — never your session history — which keeps them focused and preserves your context.

**Core principle:** Review early, review often. Verify before implementing.

---

## Part 1 — Conducting a Review

### When
Mandatory: after each task in plan execution, after a major feature, before merge to main. Valuable: when stuck (fresh eyes), before a risky refactor (baseline).

### Pin the diff
```bash
BASE_SHA=$(git rev-parse origin/main)   # or HEAD~1, a tag, a merge-base
HEAD_SHA=$(git rev-parse HEAD)
```
Use three-dot `git diff <base>...HEAD` to compare against the merge-base. Note the commit list: `git log <base>..HEAD --oneline`.

### Pick the axes — run them in parallel
Independent review axes go to **separate sub-agents in one message** so they don't pollute each other's context. Aggregate their reports afterward; don't merge or re-rank — separate axes let the user see each clearly.

- **Quality** (default, always) — correctness, tests, simplicity/YAGNI, clarity, conventions. Use `code-reviewer-prompt.md`.
- **Spec** (when there's an originating issue/PRD/plan) — missing or partial requirements, scope creep, requirements implemented wrongly. Quote the spec line per finding.
- **Standards** (when the repo documents how code should be written — `CLAUDE.md`/`AGENTS.md`, `CONTRIBUTING.md`, ADRs, STYLE/STANDARDS docs) — cite the rule per finding. Skip anything tooling (linter/formatter/type-checker) already enforces.

A change can pass one axis and fail another (right thing, wrong conventions — or vice versa). That's why they're separate.

### Severity discipline
Reviewers tag every finding **Critical / Important / Minor** with `file:line`, what's wrong, why it matters, and how to fix. Don't inflate Minor to Critical. "Looks good" without evidence is not a review; zero findings on clean code is a valid outcome.

### Act on what comes back
- **Critical** → fix immediately. **Important** → fix before proceeding. **Minor** → note for later.
- If a reviewer is wrong, push back with technical reasoning (see Part 2).

---

## Part 2 — Receiving Review (feedback from a reviewer or the user)

Code review is technical evaluation, not emotional performance.

**Response pattern:** READ fully (don't react) → RESTATE the requirement in your own words (or ask) → VERIFY against the codebase → EVALUATE if it's right *for this codebase* → RESPOND (acknowledge or reasoned pushback) → IMPLEMENT one item at a time, testing each.

### Forbidden responses
Never: "You're absolutely right!", "Great point!", "Thanks for catching that!", or any gratitude/performative agreement — and never "let me implement that" before verifying. Instead: restate the requirement, ask, push back with reasoning, or just make the fix and show it. If you catch yourself typing "Thanks" or "You're right" — delete it, state the fix instead.

### Unclear feedback
If ANY item is unclear, STOP — implement nothing yet, ask about the unclear items first. Items are often related; partial understanding produces wrong implementation. ("I understand 1, 2, 3, 6. Need clarification on 4 and 5 before proceeding.")

### Verify before implementing (external feedback especially)
Before applying a suggestion: is it correct for THIS codebase/stack/platform? Does it break existing behavior? Is there a reason the current code is the way it is? If a suggestion seems wrong, push back with technical reasoning. If you can't verify, say so: "I can't verify this without X — should I investigate, ask, or proceed?" If it conflicts with a prior decision by the user, stop and discuss.

### YAGNI check
If a reviewer says "implement this properly", grep for actual usage first. Unused → propose removing it (YAGNI). Used → implement properly.

### Push back when
The suggestion breaks something, the reviewer lacks full context, it violates YAGNI, it's wrong for this stack, or legacy/compat reasons exist. Use technical reasoning, not defensiveness. If you pushed back and were wrong: "You were right — I checked X, it does Y. Fixing." State it factually, no long apology.

### Implementation order
Clarify everything unclear first → then blocking issues (breaks, security) → simple fixes (typos, imports) → complex fixes (logic, refactor). Test each fix individually; verify no regressions.

### GitHub threads
Reply to inline review comments in the comment thread (`gh api repos/{owner}/{repo}/pulls/{pr}/comments/{id}/replies`), not as a top-level PR comment.

## Template
- `code-reviewer-prompt.md` — fill and dispatch for the Quality axis. For Spec/Standards axes, adapt it with the briefs above.
