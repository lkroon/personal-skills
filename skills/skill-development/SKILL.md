---
name: skill-development
description: Invoke skill-development with the skill tool before choosing among a skill, global instruction, project docs, command, dedicated agent, deterministic tool, or no change; also invoke it before creating or improving a skill, changing trigger descriptions, adding regression cases, evaluating outcomes, or consolidating or retiring skills.
metadata:
  source: anthropics/skills skill-creator and personal-skills
  replaces: skill-creator, write-a-skill, writing-skills
---

# Skill Development

Choose the smallest mechanism that solves the observed problem, then measure whether it improves selection and outcomes. Skill creation is one option, not the default.

## Classify First

| Mechanism | Use when |
| --- | --- |
| Global instruction | Behavior applies to nearly every task. |
| Project docs/AGENTS.md | Knowledge or commands are repository-specific. |
| Command | Workflow should run only when explicitly requested. |
| Dedicated agent | Workflow needs distinct permissions, model, or context. |
| Deterministic tool | A machine can enforce or calculate the behavior reliably. |
| Skill | Reusable judgment or procedure needs contextual discovery. |
| No change | The issue is one-off or the base agent already handles it reliably. |

Route to the selected mechanism before authoring anything. Prefer deterministic enforcement over prose when both can express the rule.
When the user asks only for classification or says not to author yet, do not inspect or modify the workspace; stop after the classification and recommendation.
Formatting or behavior requested for one response only is a one-off: classify it as `No change` and state that it is not reusable.

## Admission Gate

Create a skill after repeated observed friction, or immediately when a distinct reusable workflow has all of:

- identifiable users and realistic triggering situations;
- difficult near-negatives that define when it should stay inactive;
- measurable outcome criteria;
- judgment or procedure that cannot be handled better by the mechanisms above.

Otherwise collect evidence or make no change.

## Lifecycle

1. **Capture evidence.** Preserve the real failure, transcript, recurring friction, or reusable workflow and identify the desired behavior.
2. **Define evaluation first.** Add representative positive and difficult near-negative trigger cases plus at least three outcome cases. Follow [evaluation.md](references/evaluation.md) and [eval-schema.md](references/eval-schema.md).
3. **Record a baseline.** Run the cases with no skill for a new workflow or with the previous version for an improvement.
4. **Make the minimal revision.** Write concise trigger metadata and only the guidance needed to correct observed failures. Put heavy detail in references.
5. **Compare.** Measure trigger precision and recall and outcome correctness. Repeat trials only when variance matters.
6. **Inspect failed transcripts.** Determine whether the failure came from discovery, ambiguous guidance, missing context, tool use, or the underlying task before changing wording.
7. **Promote failures.** Add real failures and near-misses to the regression fixtures before revising again.
8. **Consolidate or retire.** Merge overlapping skills when one lifecycle can own the concern. Retire skills that duplicate stronger mechanisms, rarely serve a real user, or do not improve outcomes over baseline.

Keep provenance when adapting external material. Do not require detailed ongoing telemetry; compact fixtures, saved failed transcripts, and targeted reruns are sufficient.
