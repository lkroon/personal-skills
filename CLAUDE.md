# Repository Maintenance

Default to direct execution for clear, local, reversible repository work: inspect relevant context, make the smallest correct edit, run targeted verification, and report. Use formal design or planning only when explicitly requested or when material risk warrants escalation.

Before creating, changing, evaluating, consolidating, or retiring a skill, use `skill-development`. Define or update realistic positive trigger cases, difficult near-negatives, and targeted outcome cases before revising guidance. Then run:

```bash
python3 tests/validate_skills.py
python3 tests/evaluate_skills.py --suite trigger --case <affected-case-id>
python3 tests/evaluate_skills.py --suite outcome --case <affected-case-id>
```

Use `--all` only when a full model-costing suite is justified.

`opencode-skills.json` is the OpenCode inventory. OpenCode loads only its explicit paths. Legacy skill directories remain in this repository for Claude Code symlinks and other non-OpenCode consumers; they are outside the manifest unless explicitly listed. Do not delete or rewrite those installations as cleanup.
