---
name: code-review
description: Invoke code-review with the skill tool before reviewing when the user explicitly requests review of a diff, branch, or PR; asks to verify or act on review feedback; or is preparing materially risky work for merge, especially security, migration, public-interface, or difficult-rollback changes.
metadata:
  source: personal-skills/reviewing-code
  concepts: superpowers/requesting-code-review, superpowers/receiving-code-review
  replaces: reviewing-code
---

# Code Review

Find consequential defects within a fixed change boundary and report them before commentary. Routine implementation self-checks do not require this workflow.

## Conducting a Review

1. **Fix the boundary.** Record the base and head commits and list the commits in scope. Use a three-dot diff against the merge base for a branch review. If uncommitted changes are included, state that explicitly and preserve the exact diff being reviewed. Do not silently move the boundary during review.
2. **Read complete files.** Inspect the full changed files and relevant callers, tests, and contracts, not only diff hunks.
3. **Select independent axes.** Review quality by default. Add separate spec and standards passes only when their source material exists:
   - **Quality:** correctness, security, edge cases, compatibility, tests, simplicity, and repository conventions.
   - **Spec:** behavior against the originating issue, requirements, or plan; cite the requirement for each mismatch.
   - **Standards:** behavior against documented project rules; cite the rule and skip checks already enforced deterministically.
4. **Report findings first.** Order issues Critical, Important, then Minor. Every issue needs `file:line`, the defect, impact, and a concrete correction. Zero findings is valid.
5. **Verify.** Run relevant checks when feasible and distinguish observed results from unverified concerns.

Use [code-reviewer-prompt.md](code-reviewer-prompt.md) when dispatching a focused quality reviewer. Run independent axes separately so one conclusion does not anchor another.

## Acting on Feedback

1. Read all feedback and identify unclear or coupled items before editing.
2. Verify each suggestion against the code, requirements, compatibility constraints, and actual usage.
3. Accept technically sound feedback; push back with evidence when it would regress behavior, conflicts with a decision, or adds unused complexity.
4. Implement verified items in dependency order and test each meaningful correction.
5. Report what changed, what was rejected, and any remaining uncertainty.

Do not apply feedback merely because it sounds authoritative. If verification is impossible, state what evidence is missing rather than guessing.

## Severity

| Level | Meaning |
| --- | --- |
| Critical | Security, data loss, or broken core behavior; must fix before merge. |
| Important | Real correctness, compatibility, requirement, design, or test gap; should fix before merge. |
| Minor | Limited maintainability, clarity, documentation, or optimization issue. |

Do not require review after every task or use review as ceremony for small, low-risk changes.
