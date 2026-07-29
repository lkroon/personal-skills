# OpenCode Skill System Implementation Plan

**Goal:** Replace the mandatory Superpowers pipeline and duplicate skill inventory with a risk-routed, versioned skill system that executes ordinary changes directly and reserves formal workflows for material risk.

**Architecture:** `personal-skills` becomes the only OpenCode skill source and also owns a concise global instruction file plus a small OpenCode-native evaluation harness. Machine-local OpenCode config points at that repository; a launcher disables automatic `.claude` and `.agents` skill discovery without deleting those installations for other consumers.

**Tech Stack:** Markdown Agent Skills, JSON/JSONC, Python 3.10 standard library plus PyYAML 5.3.1, OpenCode 1.18.x CLI.

## Global Constraints

- Preserve existing non-OpenCode consumers and do not delete or rewrite `~/.claude/skills` or `~/.agents/skills`.
- Preserve unrelated worktree changes in `personal-skills/CLAUDE.md` and `personal-skills/README.md`, integrating rather than reverting them.
- Do not update the stale Matt Pocock repository in place; migrate reviewed files into `personal-skills` with provenance metadata.
- Do not commit, push, or alter git configuration unless explicitly requested.
- Use ASCII in new files except where retained source material already requires Unicode.
- OpenCode must restart after config-time changes before interactive verification.

---

### Task 1: Add Static Skill Validation and Initial Regression Fixtures

**Files:**
- Create: `opencode-skills.json`
- Create: `tests/fixtures/trigger-cases.json`
- Create: `tests/fixtures/outcome-cases.json`
- Create: `tests/validate_skills.py`

**Interfaces:**
- Consumes: skill directories below repository `skills/` and OpenCode's documented frontmatter rules.
- Produces: `python3 tests/validate_skills.py`, exiting nonzero for malformed frontmatter, path/name mismatch, duplicate names, unsupported fields, missing evaluation fixtures, or dangling local Markdown links.

- [ ] **Step 1: Add the OpenCode-owned skill manifest**

Create `opencode-skills.json` as the source of truth for OpenCode activation. Initially map the six current personal skill names to repository-relative directories so static validation can pass before migration:

```json
{
  "skills": {
    "brainstorming": "skills/brainstorming",
    "development-guidelines": "skills/development-guidelines",
    "executing-plans": "skills/executing-plans",
    "grill-me": "skills/grill-me",
    "reviewing-code": "skills/reviewing-code",
    "writing-plans": "skills/writing-plans"
  }
}
```

Later tasks replace this list with the five canonical workflow skills and reviewed domain skills. OpenCode config and the evaluation harness use one explicit directory path per manifest entry. This lets the repository retain legacy Claude Code skill targets without exposing them to OpenCode.

- [ ] **Step 2: Add trigger and outcome fixtures before changing active skills**

Create `tests/fixtures/trigger-cases.json` with this shape:

```json
{
  "require_active_skill_references": false,
  "require_canonical_coverage": false,
  "require_outcome_coverage": false,
  "cases": [
    {
      "id": "direct-small-code-change",
      "prompt": "Change the text of one existing validation error and run its focused test.",
      "expected_skills": [],
      "forbidden_skills": ["formal-design", "formal-planning", "hard-debugging"]
    },
    {
      "id": "direct-multifile-mechanical-change",
      "prompt": "Rename getCwd to getCurrentWorkingDirectory across the repository and run the existing checks.",
      "expected_skills": [],
      "forbidden_skills": ["formal-design", "formal-planning"]
    },
    {
      "id": "formal-architecture",
      "prompt": "Design how two services should share authorization policy without duplicating rules. The public API is not decided yet.",
      "expected_skills": ["formal-design"],
      "forbidden_skills": []
    },
    {
      "id": "formal-security",
      "prompt": "Plan a migration from API keys to short-lived OAuth tokens without locking out existing clients.",
      "expected_skills": ["formal-design"],
      "forbidden_skills": []
    },
    {
      "id": "formal-existing-design",
      "prompt": "The approved architecture is in docs/auth-design.md. Write an implementation plan with dependencies and verification checkpoints.",
      "expected_skills": ["formal-planning"],
      "forbidden_skills": ["formal-design"]
    },
    {
      "id": "hard-debugging-intermittent",
      "prompt": "Diagnose an intermittent race that fails one CI run in twenty and has resisted two fixes.",
      "expected_skills": ["hard-debugging"],
      "forbidden_skills": []
    },
    {
      "id": "direct-obvious-bug",
      "prompt": "The traceback points to a misspelled dictionary key on this line. Fix it and add a regression test.",
      "expected_skills": [],
      "forbidden_skills": ["hard-debugging"]
    },
    {
      "id": "explicit-review",
      "prompt": "Review the current branch against main and report bugs first with file and line references.",
      "expected_skills": ["code-review"],
      "forbidden_skills": []
    },
    {
      "id": "review-feedback",
      "prompt": "Check whether this PR feedback is technically correct before applying it.",
      "expected_skills": ["code-review"],
      "forbidden_skills": []
    },
    {
      "id": "skill-create-reusable",
      "prompt": "We repeat the same release-note audit in every repository. Determine whether it deserves a skill and create and evaluate one if justified.",
      "expected_skills": ["skill-development"],
      "forbidden_skills": []
    },
    {
      "id": "skill-improve-misfire",
      "prompt": "The architecture skill keeps triggering on simple refactors. Improve its trigger description and add this failure as a regression case.",
      "expected_skills": ["skill-development"],
      "forbidden_skills": []
    },
    {
      "id": "not-a-skill",
      "prompt": "Add this repository-specific test command to AGENTS.md.",
      "expected_skills": [],
      "forbidden_skills": ["skill-development"]
    }
  ]
}
```

The validator will also require at least three trigger and three outcome cases per canonical workflow skill before deployment. Add more cases during Tasks 2-5 until that condition is met; preserve these initial observed-policy cases as the first regression set. The temporary `false` gates allow fixtures to name planned canonical skills before those directories and outcome cases become active.

Create `tests/fixtures/outcome-cases.json` with an initially empty `cases` list. Task 5 adds executable cases after the canonical skill bodies exist. Its final case shape is:

```json
{
  "cases": [
    {
      "id": "formal-design-stops-before-implementation",
      "skill": "formal-design",
      "prompt": "Design a shared authorization contract for two services. Do not implement it yet.",
      "required_tools": ["skill"],
      "forbidden_tools": ["apply_patch"],
      "required_text_patterns": ["(?i)(option|approach|trade-off)"],
      "forbidden_text_patterns": ["(?i)implementation complete"]
    }
  ]
}
```

- [ ] **Step 3: Run the validator before it exists**

Run:

```bash
python3 tests/validate_skills.py
```

Expected: fail because `tests/validate_skills.py` does not exist. This establishes the first red check without running expensive model evaluations.

- [ ] **Step 4: Implement static validation**

`tests/validate_skills.py` must:

1. Parse frontmatter with `yaml.safe_load`.
2. Accept only `name`, `description`, `license`, `compatibility`, and string-to-string `metadata`.
3. Enforce OpenCode's name regex `^[a-z0-9]+(-[a-z0-9]+)*$`, 1-64 character names, matching directory names, and descriptions of 1-1024 characters.
4. Validate every manifest path, ensure it stays inside the repository, and ensure it resolves to a `SKILL.md` whose name matches the manifest key and containing directory.
5. Resolve relative Markdown links from each `SKILL.md` and fail on missing local files while ignoring URLs and anchors.
6. Parse `opencode-skills.json`; reject malformed names, duplicate paths, absolute paths, and paths that escape the repository.
7. Parse `tests/fixtures/trigger-cases.json` and require valid IDs, prompts, lists of expected and forbidden skill names, and no overlap between the two lists. When `require_active_skill_references` is true, require every referenced name to be in the manifest.
8. Parse `tests/fixtures/outcome-cases.json`; require unique IDs, an active skill name, a prompt, string lists for tool and regular-expression fields, and compilable regular expressions.
9. When `require_canonical_coverage` is true, require at least three trigger cases mentioning each canonical workflow skill in `expected_skills`. When `require_outcome_coverage` is true, require at least three outcome cases targeting each canonical workflow skill.
10. Print one error per line to stderr and `Validated N active skills, M trigger cases, and K outcome cases` on success.

- [ ] **Step 5: Verify the validator against the current inventory**

Run:

```bash
python3 tests/validate_skills.py
```

Expected: the current six manifest skills, twelve trigger fixtures, and empty outcome fixture file validate, or the command exposes concrete existing frontmatter/link problems to resolve without weakening the checks.

---

### Task 2: Replace Mandatory Workflow Skills with Risk-Routed Canonical Skills

**Files:**
- Create: `instructions/opencode-development.md`
- Create: `skills/formal-design/SKILL.md`
- Create: `skills/formal-planning/SKILL.md`
- Create: `skills/hard-debugging/SKILL.md`
- Create: `opencode/skills/grill-me/SKILL.md`
- Modify: `opencode-skills.json`
- Modify: `tests/fixtures/trigger-cases.json`

**Interfaces:**
- Consumes: approved risk criteria from `docs/2026-07-29-opencode-skill-system-design.md`.
- Produces: direct execution as global default plus opt-in/risk-triggered formal design, planning, and hard-debugging workflows.

- [ ] **Step 1: Add concise always-on instructions**

Create `instructions/opencode-development.md` containing these enforceable defaults:

```markdown
# Development Workflow

Default to direct execution for clear, local, reversible work:

`inspect relevant context -> edit -> targeted verification -> report`

- Prefer the smallest correct change. Avoid speculative abstractions and unrelated cleanup.
- Preserve unrelated worktree changes. Every changed line must trace to the request.
- Resolve minor ambiguity from repository evidence. Ask only when ambiguity changes behavior, scope, risk, or compatibility.
- Use brief acceptance criteria or todos for bounded multi-step work without creating a spec or implementation plan.
- Use tests first when they materially improve feedback, especially for regressions and complex behavior; do not impose TDD mechanically.
- Verify with the narrowest command that proves the claim, broadening checks with blast radius.

Load formal workflow skills only when explicitly requested or when risk is material: architecture or public APIs; security, privacy, or authorization; migrations or destructive/irreversible operations; cross-system ambiguity; weak verification; unfamiliar technology with high failure cost; or coordinated multi-stage checkpoints. File count, feature work, and behavior changes alone are not formal-workflow triggers. If material risk appears during direct execution, stop and escalate then.
```

- [ ] **Step 2: Create `formal-design`**

Adapt the useful context exploration, one-question-at-a-time clarification, alternatives, incremental approval, and self-review from the old `brainstorming` skill. Change the contract so that:

- its description names only explicit design/spec requests and the approved material-risk criteria;
- its first step confirms that formal treatment is warranted;
- a short approved design may remain in the conversation;
- a saved spec is created only when it will guide later stages or record a durable decision;
- there is no required commit and no automatic handoff to planning;
- routine local, reversible work is explicitly routed back to direct execution.

Add `metadata.source: personal-skills` and `metadata.replaces: brainstorming`.

- [ ] **Step 3: Create `formal-planning`**

Adapt the useful dependency mapping, exact file identification, risk checkpoints, and verifiable outcomes from the old `writing-plans` skill. Remove mandatory 2-5 minute steps, full code listings, TDD, commit-per-step, and subagent execution. Require each plan task to state files, goal, dependencies, acceptance checks, and rollback/risk notes when applicable. Do not plan routine work that can be executed safely in-session.

Add `metadata.source: personal-skills` and `metadata.replaces: writing-plans`.

- [ ] **Step 4: Create `hard-debugging`**

Create a concise workflow for intermittent, performance, distributed, high-impact, or repeatedly failed defects:

```text
reproduce -> minimize -> form ranked hypotheses -> instrument one variable -> fix root cause -> regression-test
```

Require evidence between stages and a regression test when one can reliably reproduce the defect. Explicitly exclude obvious localized defects whose cause is already demonstrated by a traceback, failing assertion, or typo. Add provenance metadata noting that it consolidates `diagnose` and `systematic-debugging` concepts.

- [ ] **Step 5: Replace superseded entries in the OpenCode manifest**

Copy `skills/grill-me/SKILL.md` to `opencode/skills/grill-me/SKILL.md`, replace its legacy `brainstorming` and `writing-plans` cross-references with conditional references to `formal-design` and `formal-planning`, and point the manifest at the copy. Replace `brainstorming`, `development-guidelines`, `executing-plans`, and `writing-plans` in `opencode-skills.json` with `formal-design`, `formal-planning`, and `hard-debugging`. Keep all old skill directories untouched because existing Claude Code symlinks target them. Task 7 excludes Claude-compatible discovery, so they are not active in OpenCode.

- [ ] **Step 6: Expand fixtures and run static validation**

Add enough positive and difficult near-negative prompts that `formal-design`, `formal-planning`, and `hard-debugging` each have at least three expected cases. Include explicit negatives for a multi-file rename, a routine feature with complete requirements, an obvious bug, and a user-supplied implementation plan that needs execution rather than replanning.

Run:

```bash
python3 tests/validate_skills.py
```

Expected: all new canonical skills validate and no removed name is referenced by active skill links or trigger fixtures.

---

### Task 3: Consolidate Review and Skill Creation Lifecycles

**Files:**
- Create: `skills/code-review/SKILL.md`
- Create: `skills/code-review/code-reviewer-prompt.md`
- Create: `skills/skill-development/SKILL.md`
- Create: `skills/skill-development/references/evaluation.md`
- Create: `skills/skill-development/references/eval-schema.md`
- Modify: `opencode-skills.json`
- Modify: `tests/fixtures/trigger-cases.json`

**Interfaces:**
- Consumes: explicit review requests, materially risky pre-merge changes, review feedback, and recurring skill-system failures.
- Produces: findings-first review behavior and one lifecycle for deciding, creating, measuring, improving, consolidating, and retiring skills.

- [ ] **Step 1: Create `code-review` from the existing combined review skill**

Retain findings-first severity discipline, fixed diff boundaries, full-file reading, independent spec/quality/standards axes when relevant, and verification of incoming feedback. Remove mandatory review after every task, generic "review early, review often" pressure, and performative-response policing that does not improve technical outcomes. Trigger on explicit review requests, acting on review feedback, and pre-merge work with material risk.

Move and simplify `code-reviewer-prompt.md` so its output starts with `Issues`, ordered Critical/Important/Minor, followed by open questions and a short assessment. Add provenance metadata referencing the previous personal review skill and Superpowers requesting/receiving review concepts.

Replace `reviewing-code` with `code-review` in `opencode-skills.json`. Leave the old directory in place for its existing Claude Code symlink.

- [ ] **Step 2: Create `skill-development`**

The main skill must first classify the need:

| Mechanism | Use when |
|---|---|
| Global instruction | Behavior applies to nearly every task. |
| Project docs/AGENTS.md | Knowledge or commands are repository-specific. |
| Command | Workflow should run only when explicitly requested. |
| Dedicated agent | Workflow needs distinct permissions, model, or context. |
| Deterministic tool | A machine can enforce or calculate the behavior reliably. |
| Skill | Reusable judgment or procedure needs contextual discovery. |
| No change | The issue is one-off or the base agent already handles it reliably. |

Permit a new skill after repeated observed friction or immediately when a distinct reusable workflow has clear users, triggers, near-negatives, and measurable outcomes. Require baseline comparison, minimal revision, failed-transcript inspection, and adding real failures to the regression suite. Include consolidation and retirement, not just creation.

- [ ] **Step 3: Add progressive evaluation references**

`references/evaluation.md` must adapt the useful Anthropic methodology to OpenCode:

- positive and difficult near-negative trigger cases;
- at least three outcome cases;
- no-skill or previous-version baseline;
- repeated trials only when variance matters;
- trigger precision/recall plus outcome correctness;
- transcript inspection before changing wording;
- `opencode run --format json` tool-call detection;
- real failures promoted into regressions;
- no requirement for detailed ongoing telemetry.

`references/eval-schema.md` must define the repository's compact trigger fixture fields and outcome fixture shape. Record Anthropic's repository URL and the installed snapshot date in frontmatter metadata or a source note.

- [ ] **Step 4: Verify the OpenCode-owned `grill-me` copy**

Confirm `opencode/skills/grill-me/SKILL.md` keeps its explicit user-invoked stress-test role, uses conditional references to `formal-design` and `formal-planning`, and has no automatic handoff. Confirm the original file and its Claude Code symlink target remain unchanged.

- [ ] **Step 5: Expand fixtures and validate**

Add at least three expected cases each for `code-review` and `skill-development`, including near-negatives for ordinary implementation self-checks, one-off instructions, project-specific docs, and deterministic lint rules. Add `skill-development` to `opencode-skills.json`, then set `"require_active_skill_references": true` and `"require_canonical_coverage": true`. Leave `"require_outcome_coverage": false` until Task 5 adds the executable outcome cases.

Run:

```bash
python3 tests/validate_skills.py
```

Expected: five canonical workflow skills meet fixture coverage and all skill frontmatter and local links pass.

---

### Task 4: Migrate the Reviewed Domain Skill Set into the Canonical Repository

**Files:**
- Create: `skills/prototype/SKILL.md`
- Create: `skills/prototype/UI.md`
- Create: `skills/prototype/LOGIC.md`
- Create: `skills/architecture-analysis/SKILL.md`
- Create: `skills/architecture-analysis/DEEPENING.md`
- Create: `skills/architecture-analysis/LANGUAGE.md`
- Create: `skills/architecture-analysis/HTML-REPORT.md`
- Create: `skills/architecture-analysis/INTERFACE-DESIGN.md`
- Create: `skills/triage/SKILL.md`
- Create: `skills/triage/AGENT-BRIEF.md`
- Create: `skills/triage/OUT-OF-SCOPE.md`
- Create: `skills/handoff/SKILL.md`
- Create: `skills/technical-html-presentations/SKILL.md`
- Create: `skills/technical-html-presentations/scripts/validate_deck.py`
- Create: `skills/technical-html-presentations/evals/evals.json`
- Create: `skills/worked-example-documentation/SKILL.md`
- Create: `skills/worked-example-documentation/evals/evals.json`
- Modify: `opencode-skills.json`

**Interfaces:**
- Consumes: reviewed source snapshots from the Matt Pocock repository and existing global `.agents` skills.
- Produces: self-contained, uniquely named domain skills under the canonical personal path.

- [ ] **Step 1: Copy `prototype` with provenance and narrow triggers**

Copy its three files from the reviewed local source. Preserve the throwaway/runnable constraints. Narrow the description to explicit prototype, mockup, or "let me try it" requests so it does not compete with `formal-design` merely because alternatives are being discussed. Add metadata with source repository and source revision `aaf2453f`.

- [ ] **Step 2: Migrate architecture analysis under a non-colliding name**

Copy the five supporting files, rename frontmatter and folder to `architecture-analysis`, and retain its explicit architecture-audit purpose. Remove dependencies on unavailable slash commands and translate references to canonical skill names or plain behavior. Do not make an HTML report mandatory when a concise textual audit satisfies the user's request. Add source revision metadata.

- [ ] **Step 3: Copy and decouple `triage`**

Retain the issue-state workflow and its supporting templates. Replace the broad "create an issue" trigger with explicit triage, classify, label, prepare-for-agent, or review-incoming-issues triggers. Remove the setup-skill precondition; if tracker labels are unknown, read project instructions and ask once. When an issue needs design fleshing, use a focused clarification loop or `formal-design`; reserve `grill-me` for stress-testing an existing proposed design. Add source revision metadata.

- [ ] **Step 4: Copy `handoff` with supported frontmatter**

Remove unsupported `argument-hint`, retain temporary-file output, cross-reference rather than duplicate artifacts, and redact secrets. Trigger only on explicit handoff/compact-session requests. Add source revision metadata.

- [ ] **Step 5: Copy the two existing evaluated documentation skills**

Copy their current `SKILL.md`, scripts, and `evals/evals.json` into `personal-skills`; do not move or edit the originals under `~/.agents/skills`. Update the copied presentation validator command from `~/.agents/skills/...` to a path relative to the copied skill base directory. Preserve their existing outcome fixtures. Add metadata identifying their local source and migration date. Compare hashes before and after migration to verify the global originals are byte-for-byte unchanged.

- [ ] **Step 6: Validate all copied links and scripts**

Add `prototype`, `architecture-analysis`, `triage`, `handoff`, `technical-html-presentations`, and `worked-example-documentation` to `opencode-skills.json`. Keep the existing `grill-me` entry. The final manifest contains exactly twelve active skills: five canonical workflow skills plus seven reviewed domain skills.

Run:

```bash
python3 tests/validate_skills.py
python3 skills/technical-html-presentations/scripts/validate_deck.py --help
```

Expected: all skills validate; the deck validator prints usage and exits successfully without depending on its old global path.

---

### Task 5: Add the OpenCode-Native Trigger Evaluation Harness

**Files:**
- Create: `tests/evaluate_skills.py`
- Modify: `tests/fixtures/outcome-cases.json`
- Modify: `skills/skill-development/references/evaluation.md`

**Interfaces:**
- Consumes: trigger and outcome fixtures, an OpenCode executable, and canonical skills.
- Produces: isolated trigger, baseline, and outcome comparisons with machine-readable results and a regression-check exit status.

- [ ] **Step 1: Implement single-case execution and JSON-event parsing**

`tests/evaluate_skills.py` must:

1. Accept `--suite trigger|outcome`, `--case ID` (repeatable), `--all`, `--runs N` (default 1), `--model PROVIDER/MODEL`, and `--timeout SECONDS`.
2. Refuse to run every case unless `--all` is explicit because trials have model cost.
3. Build a temporary XDG config root containing `opencode/opencode.json` whose `skills.paths` entries are the twelve explicit directories from `opencode-skills.json` and whose instructions point to `instructions/opencode-development.md`.
4. Set `XDG_CONFIG_HOME` to that temporary root plus `OPENCODE_PURE=1`, `OPENCODE_DISABLE_CLAUDE_CODE_SKILLS=1`, `OPENCODE_DISABLE_EXTERNAL_SKILLS=1`, `OPENCODE_DISABLE_DEFAULT_PLUGINS=1`, and `OPENCODE_DISABLE_PROJECT_CONFIG=1` for subprocesses. Do not set `OPENCODE_CONFIG_DIR`, whose config is additive to the normal global config.
5. Before model trials, execute `opencode debug config` and `opencode debug skill` with the same environment. Abort unless resolved config has no plugin, every manifest name resolves to its manifest path, and every additional skill is in an explicit documented built-in allowlist containing `customize-opencode`. Reject any unexpected disk-backed or plugin-provided skill. This proves the temporary XDG root isolated the normal global config and caches.
6. Run each prompt with `opencode run --format json --dir <empty-temp-project>`.
7. Parse newline-delimited events. Record `part.tool == "skill"` and `part.state.input.name` from `type == "tool_use"` events.
8. Require the called-skill set to equal `expected_skills` exactly. Direct cases therefore fail on any skill call, and positive cases fail on competing or incidental skills. Keep `forbidden_skills` for clearer diagnostics.
9. For outcome cases, run both the current skill configuration and a baseline config with the target skill omitted. The current run must invoke exactly the fixture's target skill; the baseline must not invoke it. Parse other tool names and concatenated text events, evaluate the fixture's required/forbidden tools and regular expressions, and record whether the current configuration improves on or preserves an already-passing baseline. A skill that does not outperform a failing baseline fails; an already-passing baseline is reported as evidence that the skill may be unnecessary.
10. Print one JSON result per case followed by a summary; exit nonzero on mismatch, timeout, malformed event, failed subprocess, or outcome regression.
11. Avoid retaining full transcripts by default; on failure, save the event stream under a temporary directory and print its path for inspection.

- [ ] **Step 2: Add executable canonical outcome cases**

Add at least three cases per canonical workflow skill to `tests/fixtures/outcome-cases.json`, spanning normal use, a boundary case, and the primary failure the skill is intended to prevent:

- `formal-design`: invokes the skill, compares alternatives, and does not edit files before approval;
- `formal-planning`: produces dependency-aware tasks and acceptance checks without mandatory commit/TDD/subagent language;
- `hard-debugging`: gathers reproduction evidence or requests the missing evidence before proposing a fix;
- `code-review`: leads with findings and severity plus file/line evidence;
- `skill-development`: chooses among skill, instruction, docs, command, agent, deterministic tool, or no change before authoring.

Use temporary fixture repositories for cases that require file evidence. Keep grading deterministic through tool and text patterns; do not add a second model grader in the first version.

Set `"require_outcome_coverage": true` in `tests/fixtures/trigger-cases.json`, then run `python3 tests/validate_skills.py` before model trials.

- [ ] **Step 3: Verify the harness with one explicit skill case**

Run:

```bash
python3 tests/evaluate_skills.py --suite trigger --case explicit-review
```

Expected: one result showing `code-review` was invoked and a passing summary.

- [ ] **Step 4: Verify direct-route near-negatives**

Run:

```bash
python3 tests/evaluate_skills.py --suite trigger \
  --case direct-small-code-change \
  --case direct-multifile-mechanical-change \
  --case direct-obvious-bug \
  --case not-a-skill
```

Expected: no formal, hard-debugging, or skill-development calls; all four cases pass.

- [ ] **Step 5: Run one representative trigger per canonical workflow**

Run:

```bash
python3 tests/evaluate_skills.py --suite trigger \
  --case formal-architecture \
  --case formal-existing-design \
  --case hard-debugging-intermittent \
  --case explicit-review \
  --case skill-improve-misfire
```

Expected: each case invokes its expected canonical skill. Inspect and fix trigger wording for any mismatch, then preserve the failure as a harder fixture rather than weakening expected behavior.

- [ ] **Step 6: Run canonical outcome and baseline comparisons**

Run:

```bash
python3 tests/evaluate_skills.py --suite outcome --all
```

Expected: every current configuration passes its deterministic outcome checks, baseline results are recorded, and no target skill fails to improve a failing baseline. Flag already-passing baselines for user review rather than automatically retaining unnecessary skills.

---

### Task 6: Update Repository Documentation to the New Ownership Model

**Files:**
- Modify: `README.md`
- Modify: `CLAUDE.md`
- Modify: `docs/2026-07-29-opencode-skill-system-design.md`

**Interfaces:**
- Consumes: final canonical inventory and migration behavior.
- Produces: accurate human and agent documentation without reintroducing a mandatory chain.

- [ ] **Step 1: Replace the old workflow diagram and hard gates in `README.md`**

Document direct execution as the default, list the five canonical workflow skills plus retained domain skills, explain risk-based escalation, and link to the evaluation commands. Preserve the user's current statement that legacy personal skills remain available to Claude via symlinks. Explain that OpenCode loads only the manifest's explicit `skills.paths` and disables compatibility discovery to avoid duplicates.

- [ ] **Step 2: Rewrite `CLAUDE.md` as repository maintenance guidance**

Remove the hard gates requiring design and plan before code. Explain that OpenCode agents working in this repository should use `skill-development` for skill changes and run static validation plus targeted trigger and outcome cases. Keep direct execution as the default even within the skill repository. Note that original legacy skill directories remain for Claude Code compatibility and are not part of the OpenCode manifest.

- [ ] **Step 3: Reconcile the design with implementation discoveries**

Ensure the design records both discovery environment flags, the launcher approach, preserved `.agents` installations, and the final retained domain inventory. Remove any statement implying physical deletion of skills used by non-OpenCode consumers.

- [ ] **Step 4: Run documentation and static checks**

Run:

```bash
python3 tests/validate_skills.py
git diff --check
```

Expected: both commands exit zero. Review `git diff -- CLAUDE.md README.md` to confirm the pre-existing discovery edits were integrated, not reverted.

---

### Task 7: Activate the Canonical System in OpenCode

**Files:**
- Create: `/home/lkroon/.local/bin/opencode`
- Create: `/home/lkroon/.config/opencode/AGENTS.md`
- Modify: `/home/lkroon/.config/opencode/opencode.jsonc`

**Interfaces:**
- Consumes: canonical repository instructions and skills.
- Produces: every normal `opencode` invocation disables compatibility skill scans and loads only reviewed personal skills.

- [ ] **Step 1: Add a launcher ahead of the vendor binary**

Create executable `/home/lkroon/.local/bin/opencode`:

```bash
#!/usr/bin/env bash
export OPENCODE_DISABLE_CLAUDE_CODE_SKILLS=1
export OPENCODE_DISABLE_EXTERNAL_SKILLS=1
exec /home/lkroon/.opencode/bin/opencode "$@"
```

This location already precedes `/home/lkroon/.opencode/bin` in `PATH`, so no shell-profile edit is required. Verify before creation that no file exists at the wrapper path.

The launcher is the supported interactive and CLI entry point. Explicit calls to `/home/lkroon/.opencode/bin/opencode`, desktop integrations, or independently configured services can bypass the compatibility-scan environment flags. OpenCode permissions match skill names, not source paths, so they cannot resolve duplicate canonical names safely. Duplicate-free canonical discovery is guaranteed only through the launcher and evaluation harness. Audit and update any additional launch mechanism before treating it as supported.

- [ ] **Step 2: Add concise global agent guidance**

Create `/home/lkroon/.config/opencode/AGENTS.md` with a short statement that global development behavior is loaded from the configured personal instruction file and that explicit project `AGENTS.md` files add project-specific rules. Do not duplicate the full instructions in two machine-local files.

- [ ] **Step 3: Simplify OpenCode configuration**

Change `opencode.jsonc` so:

```jsonc
"instructions": [
  "/home/lkroon/agents/skills/personal-skills/instructions/opencode-development.md"
],
"skills": {
  "paths": [
    "/home/lkroon/agents/skills/personal-skills/skills/formal-design",
    "/home/lkroon/agents/skills/personal-skills/skills/formal-planning",
    "/home/lkroon/agents/skills/personal-skills/skills/hard-debugging",
    "/home/lkroon/agents/skills/personal-skills/skills/code-review",
    "/home/lkroon/agents/skills/personal-skills/skills/skill-development",
    "/home/lkroon/agents/skills/personal-skills/opencode/skills/grill-me",
    "/home/lkroon/agents/skills/personal-skills/skills/prototype",
    "/home/lkroon/agents/skills/personal-skills/skills/architecture-analysis",
    "/home/lkroon/agents/skills/personal-skills/skills/triage",
    "/home/lkroon/agents/skills/personal-skills/skills/handoff",
    "/home/lkroon/agents/skills/personal-skills/skills/technical-html-presentations",
    "/home/lkroon/agents/skills/personal-skills/skills/worked-example-documentation"
  ]
}
```

Remove the Superpowers `plugin` field and all broad third-party paths. Preserve existing permissions and add a `permission.skill` allowlist with `"*": "deny"` first and each of the twelve manifest names set to `"allow"` afterward; OpenCode evaluates the last matching rule. This hides unrelated legacy/global names but is not source isolation for duplicate names, so it does not make wrapper-bypassing launches supported. Do not manually delete package caches; removing the plugin from resolved config is sufficient, and stale caches are inert.

- [ ] **Step 4: Validate the resolved config and skill inventory in a fresh process**

Run:

```bash
command -v opencode
opencode debug config --print-logs --log-level WARN
opencode debug skill --print-logs --log-level WARN
```

Expected:

- `command -v` resolves `/home/lkroon/.local/bin/opencode`;
- resolved config has the twelve manifest-derived personal skill paths, the personal instruction path, and no Superpowers plugin;
- stderr contains no `duplicate skill name` warnings;
- inventory through the supported launcher contains exactly the reviewed personal skills plus OpenCode built-ins, with no `using-superpowers`, old workflow names, `skill-creator`, or global `.agents` domain duplicates;
- `opencode debug agent build` shows only the twelve manifest skills allowed.

- [ ] **Step 5: Confirm preserved external installations**

Run:

```bash
test -f /home/lkroon/.agents/skills/skill-creator/SKILL.md
test -L /home/lkroon/.claude/skills/brainstorming
```

Expected: both commands exit zero, proving activation did not delete non-OpenCode skill sources.

---

### Task 8: End-to-End Routing and Outcome Verification

**Files:**
- Modify only if a real regression is found: `tests/fixtures/trigger-cases.json` and the responsible `skills/*/SKILL.md`.

**Interfaces:**
- Consumes: fully activated configuration.
- Produces: evidence that direct work stays direct, risky work escalates, and every retained workflow remains usable.

- [ ] **Step 1: Run full static validation**

Run:

```bash
python3 tests/validate_skills.py
git diff --check
```

Expected: both exit zero.

- [ ] **Step 2: Run the complete trigger regression suite**

Run:

```bash
python3 tests/evaluate_skills.py --suite trigger --all
python3 tests/evaluate_skills.py --suite outcome --all
```

Expected: all trigger and outcome/baseline cases pass. For stochastic misses, inspect saved failed transcripts before changing descriptions; use repeated runs only on the failing cases.

- [ ] **Step 3: Run one outcome smoke test per canonical workflow**

Use temporary fixture repositories or read-only prompts so the agent can demonstrate:

- `formal-design`: recognizes material architectural risk, explores alternatives, and does not write implementation before approval;
- `formal-planning`: emits dependency-aware tasks with acceptance checks but no mandatory tiny-step/TDD/commit ceremony;
- `hard-debugging`: gathers reproduction evidence before proposing a fix;
- `code-review`: reports findings first with severity and file/line evidence;
- `skill-development`: chooses among skill, instruction, docs, command, agent, deterministic tool, or no change before authoring.

Save only failing transcripts needed for regression fixtures. Do not retain routine successful transcripts.

- [ ] **Step 4: Smoke-test retained domain skills**

Run targeted read-only or temporary-output prompts for `grill-me`, `prototype`, `architecture-analysis`, `triage`, `handoff`, `technical-html-presentations`, and `worked-example-documentation`. Confirm each invokes only on explicit relevant intent and that supporting links/scripts resolve.

- [ ] **Step 5: Review final scope**

Run:

```bash
git status --short
git diff --stat
git diff --check
```

Expected: only planned `personal-skills` changes plus the pre-existing `README.md` and `CLAUDE.md` edits are present in that repository. Separately inspect the three planned machine-local OpenCode files. No third-party checkout, `~/.claude/skills`, or `~/.agents/skills` content is modified.

- [ ] **Step 6: Restart notice**

Quit and restart any already-running OpenCode TUI or server. Report the final canonical inventory, test results, and any retained failed fixtures. Do not claim existing sessions adopted the new config.
