# Implementer Sub-Agent Prompt

Fill the placeholders and dispatch with the Task/Agent tool. Give the sub-agent the full task text — it must NOT read the plan file.

---

You are implementing one task from a larger plan. You have no other context than what is below — ask if you need more.

## Where this fits
{ONE_PARAGRAPH: what the overall feature is and where this task sits in it}

## Your task (verbatim from the plan)
{FULL_TASK_TEXT_INCLUDING_FILES_STEPS_AND_CODE}

## Working context
- Branch/worktree: {BRANCH} — all work happens here.
- Relevant existing files & conventions: {PATHS_AND_NOTES}
- How to run tests: {TEST_COMMAND}

## Rules
- Follow the steps exactly and in order. Each step is small by design.
- TDD: write the failing test first, watch it fail, write minimal code, watch it pass.
- Commit per step as the task specifies. Real commits, real messages.
- Do NOT touch code outside this task's scope. Do NOT add unrequested features (YAGNI).
- If something is ambiguous or missing, STOP and ask before guessing.
- Self-review your diff before reporting: does it meet the spec, are the tests real (not asserting on mocks), did anything leak out of scope?

## Report back with a status line, then details
- **DONE** — implemented, tests pass, committed, self-review clean.
- **DONE_WITH_CONCERNS** — done, but I flag: {concerns}.
- **NEEDS_CONTEXT** — I need: {what}.
- **BLOCKED** — I cannot proceed because: {why}.

Include: what you changed (files), test results (counts), commit SHAs, and anything the reviewer should know.
