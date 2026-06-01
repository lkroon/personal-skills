---
name: development-guidelines
description: Use when writing, reviewing, or refactoring code, or when shaping plan tasks — to avoid the common LLM coding failures of overcomplication, collateral edits, silent assumptions, and vague success criteria. The canonical coding-standard the planning and review skills enforce.
license: MIT
---

# Development Guidelines

Four behavioral standards that reduce the most common LLM coding mistakes, derived from [Andrej Karpathy's observations](https://x.com/karpathy/status/2015883857489522876). This is the single source of truth referenced by `writing-plans` and enforced by the quality reviewers in `executing-plans` and `reviewing-code`.

**Tradeoff:** these bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding
**Don't assume. Don't hide confusion. Surface tradeoffs.**
- State assumptions explicitly; if uncertain, ask.
- Multiple interpretations exist → present them, don't pick silently.
- A simpler approach exists → say so; push back when warranted.
- Something unclear → stop, name what's confusing, ask.

## 2. Simplicity First
**Minimum code that solves the problem. Nothing speculative.**
- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility"/"configurability" that wasn't requested.
- No error handling for impossible scenarios.
- 200 lines that could be 50 → rewrite it.

Test: "Would a senior engineer call this overcomplicated?" If yes, simplify.

## 3. Surgical Changes
**Touch only what you must. Clean up only your own mess.**
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor what isn't broken. Match existing style even if you'd do it differently.
- Notice unrelated dead code → mention it, don't delete it.
- Remove imports/vars/functions *your* changes orphaned; leave pre-existing dead code alone.

Test: **every changed line traces directly to the request.**

## 4. Goal-Driven Execution
**Define success criteria. Loop until verified.**
Turn tasks into verifiable goals:
- "Add validation" → "write tests for invalid inputs, then make them pass"
- "Fix the bug" → "write a test that reproduces it, then make it pass"
- "Refactor X" → "ensure tests pass before and after"

Strong criteria let you loop independently; weak criteria ("make it work") force constant clarification.

## Where this is enforced
- **`writing-plans`** — every task carries a verifiable check (#4); self-review scans for overcomplication (#2).
- **`executing-plans` / `reviewing-code` quality reviewers** — fail a task that violates surgical scope (#3), simplicity/YAGNI (#2), or lacks verification (#4).
- **`brainstorming` / `grill-me`** — surface assumptions and unknowns before code (#1).

**Working if:** fewer unnecessary diff lines, fewer rewrites from overcomplication, and clarifying questions land *before* implementation, not after.
