# Progressive Skill Evaluation

Evaluate only enough to answer whether the skill is discovered at the right time and improves task outcomes.

## 1. Define Cases

- Add realistic positive trigger cases using varied wording and implicit intent.
- Add difficult near-negatives that share vocabulary but require another mechanism or no skill.
- Add at least three outcome cases covering the workflow's important behavior and failure boundaries.
- Record objective assertions where possible; reserve qualitative review for judgment that cannot be reduced safely.

Use the compact structures in [eval-schema.md](eval-schema.md).

## 2. Establish a Baseline

For a new skill, run the same cases without the skill. For an improvement, preserve and run the previous version. A baseline shows whether the skill adds value rather than merely producing plausible output.

## 3. Run Through OpenCode

Run the repository harness, which creates an isolated temporary XDG config and a fresh temporary project for every prompt. Cases may populate that project with deterministic files or git boundaries:

```bash
python3 tests/evaluate_skills.py --suite trigger --case <case-id>
python3 tests/evaluate_skills.py --suite outcome --case <case-id>
```

Running a whole suite has model cost and requires explicit `--all`. Use `--runs N`, `--model PROVIDER/MODEL`, and `--timeout SECONDS` only when needed.

The harness preflights `opencode debug config` and `opencode debug skill` under the same isolated environment, then runs `opencode run --format json --dir <empty-project>`. It detects invocation only from `type == "tool_use"` events where `part.tool == "skill"` and reads `part.state.input.name`; prose that merely mentions a skill does not count. The called-skill set must equal the fixture's expected set exactly.

Run one trial per deterministic case initially. Repeat trials only when model variance could change the conclusion; report the number of trials with the result.

## 4. Score Both Layers

- **Triggering:** calculate precision from selected cases and recall from expected cases. Treat near-negative false positives as failures.
- **Outcomes:** run both the current manifest and a baseline with the target skill omitted. Check required and forbidden tools plus required and forbidden text patterns. The current run must pass and must improve a failing baseline. An already-passing baseline is reported for review but does not automatically fail the case.

A skill that triggers reliably but does not improve outcomes fails. A useful workflow that cannot be discovered also fails.

## 5. Diagnose Before Revising

Read failed transcripts before changing descriptions or instructions. Classify each failure as discovery, guidance, missing context, tool use, fixture weakness, or base task capability. Revise the smallest responsible layer and rerun the affected cases plus the regression suite.

Promote every real trigger or outcome failure into a regression case. Successful event streams are discarded. Failed event streams are retained in a temporary directory whose path is printed in the JSON result; inspect that transcript before revising skill wording. Detailed ongoing telemetry is not required.

## Source

Adapted for OpenCode from Anthropic's `skill-creator` methodology: https://github.com/anthropics/skills. Installed source snapshot: 2026-07-29.
