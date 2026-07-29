# Evaluation Fixture Schema

The repository keeps routing and outcome assertions separate so static validation can mature before executable model trials.

## Trigger Fixtures

`tests/fixtures/trigger-cases.json` has three coverage gates and a `cases` array:

```json
{
  "require_active_skill_references": true,
  "require_canonical_coverage": true,
  "require_outcome_coverage": true,
  "cases": [
    {
      "id": "review-request",
      "prompt": "Review this branch against main.",
      "expected_skills": ["code-review"],
      "forbidden_skills": []
    }
  ]
}
```

| Field | Shape |
| --- | --- |
| `id` | Unique lowercase hyphenated identifier. |
| `prompt` | Nonempty realistic user request. |
| `expected_skills` | Skill names that should be invoked. Empty means direct execution. |
| `forbidden_skills` | Skill names whose invocation is a false positive. |

The gates require referenced names to be active, at least three positive trigger cases for every canonical skill, and at least three outcome cases respectively.

## Outcome Fixtures

`tests/fixtures/outcome-cases.json` contains only a `cases` array:

```json
{
  "cases": [
    {
      "id": "review-findings-first",
      "skill": "code-review",
      "prompt": "Review the supplied risky diff.",
      "required_tools": ["skill"],
      "forbidden_tools": [],
      "required_text_patterns": ["(?m)^### Issues"],
      "forbidden_text_patterns": ["(?m)^### Strengths"],
      "project": {
        "files": {"src/example.py": "value = 1\n"},
        "git": {
          "base_branch": "main",
          "branch": "review",
          "changes": {"src/example.py": "value = 2\n"}
        }
      }
    }
  ]
}
```

| Field | Shape |
| --- | --- |
| `id` | Unique lowercase hyphenated identifier. |
| `skill` | One active canonical skill under evaluation. |
| `prompt` | Nonempty task prompt. |
| `required_tools` | Tool names that must appear in structured events. |
| `forbidden_tools` | Tool names that must not appear. |
| `required_text_patterns` | Regular expressions that must match the final output. |
| `forbidden_text_patterns` | Regular expressions that must not match the final output. |
| `project` | Optional deterministic temporary-project setup. `files` maps safe relative paths to contents. Optional `git` supplies `base_branch`, `branch`, and changed files, creating committed review boundaries. |

The same optional `project` field is available to trigger fixtures. Cases without `git` remain ordinary non-git temporary directories. Keep patterns behavioral and robust to harmless phrasing changes; prefer required positive behavior and forbidden tools over regexes that can match negated prose.

## Source

Schema and workflow adapted from Anthropic's skill evaluation guidance at https://github.com/anthropics/skills. Installed source snapshot: 2026-07-29.
