---
name: review
description: >
  Review the current repository pull request as a senior Python package developer.
  Checks architecture alignment (activities vs vessels), protocol correctness,
  API cleanliness, error handling conventions, control flow patterns, simplicity,
  docstring quality, and test coverage. Saves a structured Markdown note to
  .reviews/ in the repo with numbered, severity-tagged findings and a clear recommendation.
  Use this whenever you want to review a PR, audit the public API surface,
  check whether new code fits the delegation model, or evaluate code quality
  in this repository — even if the user just says "review this" or "check the PR".
argument-hint: [pr-number]
allowed-tools: Bash, Read, Write, Glob
---

# PR Review — repository

Arguments: $ARGUMENTS
Date: !`date +%Y-%m-%d`
Timestamp: !`date +%Y%m%d%H%M`

**Announce at start:** "Using the review skill — gathering PR material."

## Role

You are a senior Python package developer reviewing against the repository codebase.
Produce an honest, specific, actionable review focused on whether the changes are
architecturally sound, API-clean, appropriately minimal, and a good example for
users learning from the tutorial series.

This is not a checklist exercise — use judgment, cite concrete evidence, and skip
sections where the code is already clean. A clean PR with zero findings is a valid outcome.

---

## Step 1: Identify the PR and detect tooling

First, check whether `gh` is available:

```bash
gh --version 2>/dev/null && echo "gh_available" || echo "gh_unavailable"
```

**If `gh` is available:**

```bash
gh pr view --json number,title,body,headRefName,baseRefName,url
```

If `$ARGUMENTS` contains a number, use that as the PR number: `gh pr view <N> --json number,title,body,headRefName,baseRefName,url`

**If `gh` is not available:**

Work from local git. Identify the base branch and current branch:

```bash
git branch --show-current
git merge-base HEAD origin/main 2>/dev/null || git merge-base HEAD main
```

Record PR metadata as "unknown — gh not available" in the review note and continue with the git-based diff.

---

## Step 2: Gather material

**If `gh` is available**, run in parallel:

```bash
gh pr diff                          # full unified diff
gh pr view --json files             # list of changed files
just check 2>&1 | tail -30          # baseline CI health
```

**If `gh` is not available**, run in parallel:

```bash
git diff $(git merge-base HEAD main)...HEAD   # full diff against main
git diff --name-only $(git merge-base HEAD main)...HEAD  # changed files
just check 2>&1 | tail -30          # baseline CI health
```

If `just` is not available, fall back to:
```bash
pytest 2>&1 | tail -20
ruff check . 2>&1 | tail -20
```

If any notebook files (`.py` Marimo) changed and `marimo` is available, also run:
```bash
marimo check <notebook_file>
```

---

## Step 3: Read the full context

For every changed file, read the **full file**, not just the diff hunk.
Surrounding code is where abstraction leaks and API drift become visible.

Also read:
- `AGENTS.md` — current architecture contract
- `src/vo_colos2/_protocols/vessel.py` — existing protocol surface
- Relevant test files — to judge coverage gaps

---

## Step 4: Review through each lens

Work through these systematically. Only raise findings that are real issues with
specific evidence. If something is clean, move on — do not manufacture concerns.

### 4a. Architecture: the delegation model

The core invariant:
**Activities are thin coordinators. Vessels own the physics. SimPy owns time.**

Activities call vessel methods. They must never perform SimPy `yield` operations
directly — that is the vessel's job. Vessel methods hold domain logic: duration,
speed calculations, resource validation.

Flag when:
- An activity calculates durations or quantities that should live on the vessel.
- An activity yields SimPy events directly (instead of delegating to a vessel method).
- A vessel method bypasses `yield from super()...` chains without good reason.
- A new vessel subclass overrides something that was working fine in the base class.

### 4b. Protocols: the contract surface

Protocols in `src/vo_colos2/_protocols/vessel.py` define what activities can depend on.

- New vessel capabilities → new `@runtime_checkable Protocol` (or extend an existing one).
- Activities validate `vessel` with `isinstance(v, SomeProtocol)` inside a `@field_validator("vessel", mode="before")`.
- Protocol method signatures follow the pattern:
  `(self, env: SimulationEnv, *, metadata: dict[str, object] | None = None, ...) -> Generator`
- A public method on a vessel that is not on a protocol is invisible to activities and type checkers.

Flag when:
- A new vessel method has no corresponding protocol entry.
- An activity skips validator-based type checking or uses `hasattr` / duck-typing.
- Protocol and implementation signatures diverge.

### 4c. Error handling: structured errors only

Raw `ValueError` / `TypeError` are not acceptable for user-facing errors.

- Construction-time mistakes → `ConfigurationError` + `ErrorDetail(code=ErrorCode.X, loc=..., got=..., expected=..., fixes=...)`.
- Runtime violations → `SimulationError` (same structure).
- New error conditions require a matching entry in `ErrorCode`.
- `NotImplementedError` is only acceptable for abstract/placeholder methods, not domain logic.

Flag when:
- A validator raises bare `ValueError` or `TypeError`.
- A new error condition has no `ErrorCode` entry.
- An error message lacks `got / expected / fixes` (no actionability for the user).
- `NotImplementedError` is used for domain logic.

### 4d. API shape: naming and types

- Fields and parameters: `snake_case`, descriptive names with auxiliary verbs (`is_active`, `has_permission`).
- Types: `X | None`, `list[str]`, `dict[str, int]` — never `Optional`, `List`, `Dict`.
- `VocolosModel` optional fields use `Field(default=..., kw_only=True)`.
- No uppercase parameter names (e.g., `IAC_resource` → `iac_resource`).
- New public parameters should not expose internal resource key strings when the model can derive or validate them.
- Public API surface: anything exported via a package `__init__.py` is a commitment. New exports should be intentional.

Flag when:
- Parameter names diverge from the snake_case convention.
- Types use pre-3.10 syntax.
- A public field carries an implementation detail that callers should not need to know.
- An `__init__.py` export appears without a clear reason.

### 4e. Control flow patterns

The control layer provides: `sequence`, `parallel`, `For`, `If`, `While`, `Signal`, `TriggerSignal`, `WaitForSignal`.

- `sequence(...)` — single vessel ordered work plan.
- `parallel(...)` — multi-vessel coordination.
- `For` — campaign loops over sites or items.
- `If` / `While` — conditional or repeat-until logic.
- Signals — when one vessel must wait for another to hit a milestone.

Flag when:
- A new control construct reimplements something already covered by `For`, `If`, or `While`.
- Multi-vessel coordination is done by sharing mutable state instead of using `Signal`.
- A process pattern is duplicated across notebooks or activities when it belongs in the control layer.

### 4f. Simplicity and abstraction

The guiding principle: **only create what is really needed**.

A generalisation is justified when it has at least two realistic, independent consumers.
If a PR broadens a base class or generalises a type to support a single new use case,
the specialisation should usually stay on the specific subclass.

Ask:
- Could this be a function instead of a class?
- Could this stay on `CableSection` instead of moving to `Line`?
- Could this validator live inline instead of becoming a utility?
- Does this new parameter belong in the public API, or is it an internal detail?

Flag when:
- A base class gains a new property/method whose only caller is the new subclass.
- A type is broadened without evidence that multiple callers need the new type.
- A helper class is introduced that is only instantiated once and could be a function.
- The PR adds optional parameters that only exist to support one specific calling pattern.

### 4g. Docstrings and comments

Conventions:
- Google-style, concise.
- Start with a short summary sentence.
- `Args:`, `Returns:`, `Yields:`, `Raises:`, `Attributes:` only when they add information beyond what the type annotations already say.
- Do not repeat type information already in annotations.
- No comments explaining what the code does — only why, when the why is a hidden constraint or non-obvious invariant.

Flag when:
- A public class or method on the public API has no docstring.
- A docstring restates the type annotation.
- A comment explains what the code does rather than a hidden constraint or workaround.

### 4h. Test coverage

New behaviour = new tests, unless the code purely delegates to well-tested lower levels with no own logic.

For a new activity, expect tests for:
- Correct simulated duration (the simulation clock advances as expected).
- Resources consumed/produced in the correct amounts.
- Vessel state after the activity matches the intended domain model.
- Invalid configuration raises the expected `ConfigurationError` with the right `ErrorCode`.

For a new vessel method, expect tests at the activity level via `run(lambda env: activity.process(env))`.

Do not add:
- `test_is_immutable` for frozen dataclasses.
- `test_accepts_positional_only` / `test_requires_keyword` tests.
- Protocol compliance tests outside `tests/test_protocols/`.

Flag any coverage gap specifically — name the scenario, not just "tests are missing".

### 4i. Notebook hygiene

If notebook files changed:
- Broken cell references or undefined variables show up in `marimo check` output.
- Committed output with exception tracebacks means the tutorial documents a broken run.
- Each notebook should introduce one framework concept. Flag scope creep.
- Shared helpers belong in `helpers.py`, not duplicated across notebooks.

---

## Step 5: Save the review note

Create the `.reviews/` directory at the repo root if it does not exist, then save:

`.reviews/<timestamp>-pr<N>.md`

Use this exact structure:

```markdown
# PR <N> Code Review

Date: <today's date>

## Scope

- PR: `#<N> <title>`
- URL: <github url>
- Base branch: `<base-branch>`
- Head branch: `<head-branch>`

## Findings

### 1. <Severity>: <one-line issue title>

- File: `src/vo_colos2/path/to/file.py:<line-range>`
- <What the code does>
- <Why it is a problem — the architectural or API consequence>
- <Concrete suggestion: what to change and how>

(repeat, sorted High → Medium → Low)

## Open Questions

(Questions for the author where the correct answer depends on intent or design
decisions not documented in the PR.)

## Validation

- `just check`: <passed / failed / output excerpt>
- `marimo check`: <result, or "no notebooks changed">

## Recommendation

- **Approve** / **Request changes** / **Needs discussion**
- <One paragraph: the primary concern, what the author needs to address, and
  what you would accept as resolution>
```

### Severity labels

**High** — Architectural regression, semantic bug, or public API breakage that would affect callers or simulation correctness.
**Medium** — Missing test coverage for new behaviour, abstraction leak, naming inconsistency, or docstring gap on public API.
**Low** — Style divergence or minor naming drift that does not affect API consumers.

Sort High → Medium → Low. Within the same severity, follow diff order.

### What makes a good finding

- **Specific**: names the exact file, line range, and code construct.
- **Causal**: explains *why* it matters, not just *that* it differs from a rule.
- **Actionable**: gives a concrete path to resolution.
- **Proportionate**: does not inflate a Low to a High for emphasis.

Do not fill sections if there is nothing to say.

---

## Step 6: Report to the user

After saving the note:
1. Print the full file path.
2. Two-sentence summary: how many findings at each severity level, and the overall recommendation.
3. If this PR establishes a new pattern not yet documented in `AGENTS.md` (new protocol shape,
   new error handling convention, new testing approach, new control flow construct), flag it so the
   user can decide whether to update `AGENTS.md`.