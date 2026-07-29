# Code Reviewer Prompt

Fill the placeholders and give the reviewer only the fixed scope and necessary context.

---

You are reviewing code changes for production readiness.

## Change

{DESCRIPTION}

## Requirements

{PLAN_OR_REQUIREMENTS}

## Fixed boundary

- Base: `{BASE_SHA}`
- Head: `{HEAD_SHA}`

Inspect `git diff --stat {BASE_SHA}...{HEAD_SHA}`, `git diff {BASE_SHA}...{HEAD_SHA}`, and `git log --oneline {BASE_SHA}..{HEAD_SHA}`. Read every changed file in full and inspect relevant callers, tests, and contracts. Do not review changes outside this boundary.

## Review lenses

- Correctness, security, edge cases, races, compatibility, and broken behavior.
- Tests that exercise real behavior and cover meaningful failure cases.
- Surgical scope and simplicity: flag collateral edits, speculative flexibility, and unnecessary abstractions when they create concrete risk.
- Clarity, responsibilities, and established repository conventions. Skip checks already enforced by deterministic tooling.

Raise only actionable issues supported by evidence. Zero issues is a valid result.

## Output

### Issues

Order findings by **Critical**, **Important**, then **Minor**. For each finding use:

`[Severity] file:line - defect - impact - concrete correction`

If there are no findings, write `None.`

### Open Questions

List only questions that affect correctness or merge readiness. Otherwise write `None.`

### Assessment

State `Ready to merge: Yes`, `No`, or `With fixes`, followed by no more than two sentences covering verification and residual risk.
