---
name: writing-plans
description: Use when you have an approved spec or clear requirements for a multi-step coding task and need an implementation plan, before touching code.
---

# Writing Plans

Write an implementation plan assuming the engineer is skilled but knows nothing about this codebase, toolset, or domain — and has questionable taste. Document everything: exact files, full code, exact commands, how to test. Bite-sized tasks. **DRY. YAGNI. TDD. Frequent commits.**

**Announce at start:** "I'm using the writing-plans skill to create the implementation plan."

**Save plans to:** `~/agents/plans/YYYY-MM-DD-<feature-name>.md` (user/project preference overrides).

## Scope Check

If the spec covers multiple independent subsystems, split it: one plan per subsystem, each producing working, testable software on its own. Suggest the split before writing.

## File Structure First

Before defining tasks, map which files get created/modified and the single responsibility of each. This locks in decomposition.

- One clear responsibility per file; clear boundaries and interfaces.
- Files that change together live together. Split by responsibility, not by technical layer.
- Prefer small, focused files — you reason and edit more reliably on code you can hold in context at once.
- In existing codebases, follow established patterns. Don't unilaterally restructure; a targeted split of a file you're already modifying is fine.

## Plan Header (required)

```markdown
# [Feature Name] Implementation Plan

> **For executors:** Use the `executing-plans` skill to implement this task-by-task. Steps use `- [ ]` checkboxes for tracking.

**Goal:** [one sentence — what this builds]
**Architecture:** [2-3 sentences — the approach]
**Tech Stack:** [key technologies/libraries]

---
```

## Task Structure (TDD, bite-sized)

Each **step** is one 2-5 minute action. Every code step shows the actual code; every run step shows the command and expected output.

````markdown
### Task N: [Component Name]

**Files:**
- Create: `exact/path/file.py`
- Modify: `exact/path/existing.py:123-145`
- Test:   `tests/exact/path/test_file.py`

- [ ] **Step 1 — Write the failing test**
```python
def test_specific_behavior():
    assert function(input) == expected
```
- [ ] **Step 2 — Run it, verify it fails**
Run: `pytest tests/.../test_file.py::test_specific_behavior -v`
Expected: FAIL ("function not defined")
- [ ] **Step 3 — Minimal implementation**
```python
def function(input):
    return expected
```
- [ ] **Step 4 — Run it, verify it passes**
Run: `pytest tests/.../test_file.py::test_specific_behavior -v`  → PASS
- [ ] **Step 5 — Commit**
```bash
git add tests/.../test_file.py src/.../file.py
git commit -m "feat: add specific behavior"
```
````

## No Placeholders (these are plan failures)

Never write: "TBD"/"TODO"/"implement later"; "add appropriate error handling / validation / edge cases"; "write tests for the above" without the test code; "similar to Task N" instead of repeating the code (tasks may be read out of order); any step that says what without showing how; references to types/functions not defined in some task.

## Self-Review (run it yourself, fix inline)

1. **Spec coverage** — point to a task for each spec requirement; add tasks for any gap.
2. **Placeholder scan** — search for every red flag above; fix.
3. **Type consistency** — method/property names defined in early tasks match their use in later tasks (`clearLayers()` in Task 3 vs `clearFullLayers()` in Task 7 is a bug).

## Execution Handoff

After saving: "Plan complete, saved to `<path>`. Execute it with the `executing-plans` skill — it dispatches a fresh sub-agent per task with spec + quality review, and parallelizes independent tasks. Want me to start?"
