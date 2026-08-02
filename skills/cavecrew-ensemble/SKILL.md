---
name: cavecrew-ensemble
description: >
  Best-of-N task execution. Dispatch 2-3 proposal-only subagents to work the
  same bounded task in parallel, then have the dispatching agent review their
  proposals, pick the best or merge complementary parts, and apply the result.
  Workers read but never write shared files; each returns a caveman-compressed
  edit proposal so main-context cost stays low. Orchestration, review, and
  combining all happen on the main thread — no reviewer subagent. Use for
  bounded 1-2 file changes where solution variance or edge cases matter:
  "spawn 2-3 builders in parallel", "try this a few ways and pick the best",
  "best of N", "delegate to 2-3 agents on the same task", "combine subagent
  results". Do NOT use for single known-answer edits (one worker inline),
  one-line answers, 3+ file refactors, or review-by-a-fresh-agent requests.
---

Adapted from `cavecrew` (juliusbrussee/caveman) with a different core: instead of one builder per task plus a reviewer subagent, this skill runs **2-3 proposal-only workers on the same task in parallel** and leaves orchestration, review, and combining to the dispatching agent itself.

The win is unchanged: worker output is caveman-compressed, so the tool-results injected back into main context are ~60% smaller — main context lasts longer across long sessions.

## Core principle

2-3 workers, same task, isolated context → main agent reviews proposals → picks best or merges complementary parts → applies and verifies.

## When to use vs alternatives

| Task | Use |
|---|---|
| Bounded 1-2 file change with solution variance or correctness at stake | 2-3 proposal-only workers + main-thread combine |
| Surgical edit, single known answer, scope obvious | One worker inline, no ensemble |
| "Where is X defined / what calls Y / list uses of Z" | Read-only scout (1 worker or 2-3 angles) |
| New feature / 3+ files / cross-cutting refactor | Main thread, no subagents |
| Diff/branch review for bugs | Main thread, or a reviewer role — never ensemble workers |
| One-line answer you already know | Main thread, no subagent |

Rule of thumb: **if multiple defensible solutions exist, run the ensemble. If there is one known answer, don't pay for N workers.**

## Workflow

1. **Spawn 2-3 workers in ONE message**, each with identical isolated context: task spec, exact file paths, constraints (style, scope, no new abstractions). Construct what they need; never let them inherit session context or history.
2. **Review** each proposal against the task spec: correctness, scope discipline, minimality, edge cases. Read the before/after diff blocks, not just the receipts.
3. **Combine**: pick the best proposal, or merge complementary parts (e.g. worker A's approach + worker B's edge-case fix). Never merge hunks that touch the same lines unless they agree; dedupe identical proposals.
4. **Apply** the merged result yourself with a real edit on the real file — workers never wrote it.
5. **Verify**: re-read the changed file; run the focused test if one exists.

## Worker proposal contract

Each worker returns a receipt plus a before/after diff block:

```
<path:line-range> — <change ≤10 words>.
<path:line-range> — <change ≤10 words>.
verified: <re-read OK | mismatch @ path:line>.
--- diff
<path> before:
<exact lines being replaced>
<path> after:
<exact replacement lines>
```
Or one of: `too-big.` / `needs-confirm.` / `ambiguous.` / `regressed.` (terminal first token).

## Combine rules

- Identical proposals → apply once.
- Disjoint hunks that are each correct → merge both.
- Same lines, conflicting solutions → apply one, don't blend blindly.
- A worker that returned a refusal (`too-big.`, `ambiguous.`, etc.) is not a proposal — resolve its concern before proceeding.
- If 2 of 3 agree and the third differs, prefer the agreement unless the minority proposal demonstrably covers an edge case the others miss.

## What NOT to do

- Don't have workers edit the real file in parallel — same-line writes race and corrupt the diff. Workers are proposal-only by construction.
- Don't run the ensemble for a single known answer; one worker is cheaper.
- Don't ask workers for prose or architecture opinions — the contracts are structured; if a human will read the output directly, paraphrase.
- Don't dispatch a reviewer subagent in the ensemble path — the dispatching agent does review and combine.
- Don't run 2-3 workers per task on a 10-task plan; that is 20-30 delegations. Use the ensemble selectively.

## Auto-clarity (inherited)

Workers drop caveman → normal English for security warnings, irreversible-action confirmations, and any output where fragment ambiguity could be misread. Resume caveman after.

## Provenance

Adapted from `cavecrew` in [juliusbrussee/caveman](https://github.com/juliusbrussee/caveman) (skill: `cavecrew`), which this skill keeps in the read-only scout and single-worker paths above. The ensemble workflow and main-thread combine are additions.
