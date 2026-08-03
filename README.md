# personal-skills

The reviewed, versioned source of OpenCode skills. Clear, local, reversible work uses direct execution by default:

```text
inspect relevant context -> edit -> targeted verification -> report
```

Do not require brainstorming, a specification, a saved plan, a worktree, TDD, subagents, or review for routine work. Escalate when risk is material: architecture or public APIs; security, privacy, authorization, or sensitive data; migrations, destructive behavior, or difficult rollback; cross-system ambiguity; weak verification; unfamiliar technology with a high failure cost; or coordinated multi-stage checkpoints. A multi-file feature or behavior change is not sufficient by itself. If material risk appears during direct execution, stop and escalate then.

## OpenCode Skills

The five canonical workflow skills are:

| Skill | Use it when |
| --- | --- |
| `formal-design` | A user explicitly requests a design/specification, or consequential uncertainty and material risk must be resolved before implementation. |
| `formal-planning` | An approved design or materially risky multi-stage change needs dependencies, acceptance checks, and coordinated checkpoints. |
| `hard-debugging` | A defect is intermittent, performance-related, distributed, high-impact, hard to verify, or unresolved after repeated attempts. |
| `code-review` | Reviewing a diff, branch, or PR; acting on review feedback; or independently scrutinizing materially risky work before merge. |
| `skill-development` | Creating, improving, evaluating, consolidating, or retiring skills or choosing a better mechanism. |

Eight reviewed domain skills remain distinct:

| Skill | Use it when |
| --- | --- |
| `agent-env` | A repository's linting, tests, and coverage gate must run in a disposable Docker environment rather than on the host. |
| `grill-me` | An existing design, plan, or approach needs one-question-at-a-time stress-testing. |
| `prototype` | A throwaway runnable experiment or set of UI variants should answer a design question. |
| `architecture-analysis` | A codebase needs an architecture audit or deepening opportunities for testability and navigability. |
| `triage` | Issues need classification, workflow management, or preparation for an agent. |
| `handoff` | Current-session context must be compacted for another agent or later session. |
| `technical-html-presentations` | Repository evidence must become or update a self-contained technical HTML presentation. |
| `worked-example-documentation` | Documentation needs a verified end-to-end example through every intermediate representation. |

`opencode-skills.json` is the source of truth for this thirteen-skill inventory. OpenCode configuration expands that manifest into explicit `skills.paths`; it does not load the entire `skills/` tree. The supported launcher sets:

- `OPENCODE_DISABLE_CLAUDE_CODE_SKILLS=1` to disable `.claude` compatibility discovery.
- `OPENCODE_DISABLE_EXTERNAL_SKILLS=1` to disable external `.agents` discovery.

These flags prevent legacy or global copies from being rediscovered alongside the manifest and producing duplicate names. Invoking the vendor binary directly or using another integration can bypass the launcher and is unsupported until configured with the same flags and explicit paths.

Legacy personal skill directories are not deleted. They remain available to Claude Code through symlinks in `~/.claude/skills`, while OpenCode loads only manifest entries. Existing `~/.agents/skills` installations are also preserved for non-OpenCode consumers.

## Development

Use `skill-development` before changing this skill system. Static validation is deterministic:

```bash
python3 tests/validate_skills.py
```

Run targeted trigger and outcome evaluations for the affected case IDs:

```bash
python3 tests/evaluate_skills.py --suite trigger --case <case-id>
python3 tests/evaluate_skills.py --suite outcome --case <case-id>
```

Whole suites invoke a model and require explicit `--all`.

GitHub Actions runs the unit tests and static validator on every push and pull request. The model-backed suites run only from **Actions > Test skills > Run workflow** with `run_agent_evaluations` enabled.

The default `opencode/big-pickle` evaluation model currently uses OpenCode's public free access, so it needs no token. To select a paid OpenCode Zen model, create an OpenCode Zen API key and add it as a repository or organization Actions secret named `OPENCODE_API_KEY` (or run `gh secret set OPENCODE_API_KEY`). GitHub's automatic `GITHUB_TOKEN` is only a repository automation token; it cannot call a model provider, and the evaluation harness deliberately removes it before launching OpenCode. Local evaluations instead use provider environment variables or credentials already stored by `opencode auth login` in `~/.local/share/opencode/auth.json`.

## Layout

```text
opencode-skills.json                         # active OpenCode inventory
instructions/opencode-development.md        # always-on OpenCode guidance
skills/<skill-name>/SKILL.md                 # canonical or preserved legacy skills
opencode/skills/<skill-name>/SKILL.md        # OpenCode-specific adaptation
tests/validate_skills.py                     # static validation
tests/evaluate_skills.py                     # isolated trigger/outcome evaluation
```
