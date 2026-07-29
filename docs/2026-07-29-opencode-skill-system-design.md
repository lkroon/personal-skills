# OpenCode Skill System Design

## Goal

Make ordinary development work fast and direct while retaining disciplined workflows for materially risky or ambiguous work. Keep one reviewed, versioned OpenCode skill source and improve it from observed failures rather than accumulating overlapping workflows.

## Decisions

- Default to direct execution for clear, local, reversible changes.
- Activate formal design and planning based on risk, not task size or file count alone.
- Load OpenCode skills only from the explicit `opencode-skills.json` inventory.
- Keep legacy personal skills and global installations intact for non-OpenCode consumers.
- Create or revise skills only when evidence and measurable trigger or outcome cases justify the change.
- Maintain compact regression fixtures rather than detailed ongoing telemetry.

## Routing

The default workflow is:

```text
inspect relevant context -> edit -> targeted verification -> report
```

Brief acceptance criteria or an in-session task list may help bounded multi-step work. They do not require a written spec, implementation plan, worktree, TDD, subagent, or review.

Escalate when one or more of these risks are material:

- an architectural or public-interface decision;
- security, privacy, authorization, or sensitive-data impact;
- data migration, destructive behavior, or difficult rollback;
- ambiguous behavior spanning systems or ownership boundaries;
- a weak test oracle or otherwise difficult verification;
- unfamiliar technology combined with a high cost of failure;
- coordinated checkpoints across multiple stages.

Do not escalate solely because work touches several files, adds a feature, or modifies behavior. If material risk appears during direct execution, stop and escalate at that point.

## Always-On Instructions

`instructions/opencode-development.md` defines behavior shared by ordinary coding tasks:

- prefer the smallest correct change and avoid speculative abstractions;
- touch only lines needed for the request and preserve unrelated worktree changes;
- resolve minor ambiguity from repository evidence and surface consequential ambiguity;
- verify with the narrowest command that proves the claim, broadening with blast radius;
- use tests first when they materially improve feedback, not as mandatory ceremony;
- use formal workflow skills only when explicitly requested or when risk is material.

## Final Inventory

`opencode-skills.json` contains exactly twelve active skills.

The five canonical workflow skills are:

- `formal-design`: resolves consequential uncertainty for explicitly requested designs or materially risky work.
- `formal-planning`: maps dependencies, acceptance checks, and checkpoints for approved or risky multi-stage work.
- `hard-debugging`: applies an evidence-driven loop to intermittent, distributed, performance, high-impact, or repeatedly unresolved defects.
- `code-review`: reviews a fixed diff, branch, or PR boundary and handles review feedback; routine implementation self-checks stay direct.
- `skill-development`: owns mechanism choice and the creation, evaluation, improvement, consolidation, and retirement lifecycle.

The seven retained domain skills are:

- `grill-me`: stress-tests an existing design, plan, or approach.
- `prototype`: builds throwaway logic experiments or UI variants.
- `architecture-analysis`: finds deepening and consolidation opportunities.
- `triage`: manages issue classification and workflow.
- `handoff`: compacts session context for another agent.
- `technical-html-presentations`: creates repository-grounded, self-contained HTML decks.
- `worked-example-documentation`: traces real records through every intermediate representation in technical documentation.

## Discovery And Launcher

The manifest is the source of truth, but OpenCode consumes explicit directories. Supported OpenCode configuration expands the twelve manifest entries into `skills.paths` and loads `instructions/opencode-development.md`; it never points at the whole repository skill tree.

The supported `opencode` launcher sets both discovery controls before invoking the vendor binary:

```bash
export OPENCODE_DISABLE_CLAUDE_CODE_SKILLS=1
export OPENCODE_DISABLE_EXTERNAL_SKILLS=1
exec /home/lkroon/.opencode/bin/opencode "$@"
```

`OPENCODE_DISABLE_CLAUDE_CODE_SKILLS` disables compatibility discovery from `.claude`. `OPENCODE_DISABLE_EXTERNAL_SKILLS` disables external `.agents` discovery. Both are required because a name allowlist cannot distinguish two skills with the same name from different sources.

The evaluation harness applies the same flags in an isolated temporary XDG configuration and derives `skills.paths` from the manifest. Direct vendor-binary calls, desktop integrations, or independently configured services can bypass the launcher; they are unsupported until they use both flags and the same explicit path inventory.

## Preservation And Consolidation

Consolidation is an OpenCode discovery change, not a physical deletion. OpenCode no longer discovers Superpowers, duplicate legacy workflow names, competing debugging or review workflows, or the global `skill-creator` installation. The files remain where another consumer may depend on them.

- Original legacy personal skill directories remain in this repository because Claude Code symlinks in `~/.claude/skills` target them.
- The OpenCode-specific `grill-me` adaptation lives under `opencode/skills/grill-me`; the legacy target remains untouched.
- Existing `~/.agents/skills` installations, including sources copied into this repository, remain intact.
- Existing `.agents` and `.claude` installations are not scanned by supported OpenCode launches, but are not deleted or rewritten.

## Skill Development Loop

For each proposed creation or improvement:

1. Capture a real misfire, recurring friction, or clearly reusable workflow.
2. Choose among a skill, global instruction, project documentation, command, dedicated agent, deterministic tool, or no change.
3. Define realistic positive triggers, difficult near-negatives, and at least three outcome cases.
4. Record a baseline using the current skill or no skill.
5. Make the smallest responsible revision.
6. Run targeted trials through the isolated OpenCode harness and inspect failed transcripts.
7. Promote real failures to regression fixtures.
8. Consolidate or retire skills that overlap, rarely serve a need, or do not improve outcomes.

## Verification

Static structure and fixture validation:

```bash
python3 tests/validate_skills.py
```

Targeted model-based evaluation:

```bash
python3 tests/evaluate_skills.py --suite trigger --case <case-id>
python3 tests/evaluate_skills.py --suite outcome --case <case-id>
```

The system succeeds when supported OpenCode launches have no duplicate-skill warnings, inventory matches the twelve manifest entries plus built-ins, direct-route fixtures avoid unnecessary ceremony, risky fixtures select the formal route, retained skills pass outcome cases, and non-OpenCode consumers remain unchanged.

## Non-Goals

- Building a general-purpose agent evaluation platform.
- Collecting detailed production telemetry, token accounting, or every transcript.
- Automatically installing popular skills without review.
- Preserving old skill names or mandatory workflows inside OpenCode.
- Deleting or modifying legacy skill installations merely because OpenCode no longer discovers them.
