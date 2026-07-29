import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).with_name("validate_skills.py")
SPEC = importlib.util.spec_from_file_location("validate_skills", MODULE_PATH)
validate_skills = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validate_skills)


class ValidateSkillsTests(unittest.TestCase):
    def test_opencode_instructions_preserve_direct_route_and_require_explicit_workflows(self):
        instructions = (
            MODULE_PATH.parent.parent / "instructions/opencode-development.md"
        ).read_text(encoding="utf-8")

        self.assertIn("Default to direct execution", instructions)
        self.assertIn(
            "Load `code-review` before reviewing a diff, branch, or PR or verifying or acting on review feedback.",
            instructions,
        )
        self.assertIn(
            "Load `skill-development` before choosing among a skill, instruction, project docs, command, dedicated agent, deterministic tool, or no change, and before creating, improving, evaluating, consolidating, or retiring skills or the skill system.",
            instructions,
        )
        self.assertIn(
            "Load `hard-debugging` before diagnosing intermittent, performance-related, distributed or cross-service, high-impact, difficult-to-verify, or repeatedly unresolved defects.",
            instructions,
        )
        self.assertIn(
            "Ranking hypotheses or selecting diagnostic evidence for these defects counts as diagnosing them.",
            instructions,
        )
        self.assertIn("Load `formal-design` before designing", instructions)
        self.assertIn("Load `formal-planning` before writing", instructions)
        self.assertIn("A request to check whether a review suggestion is correct", instructions)
        self.assertIn("even when the likely classification is no change", instructions)
        self.assertIn("load the named skill before inspecting the workspace", instructions)

    def test_eval_schema_example_enables_outcome_coverage(self):
        schema = (
            MODULE_PATH.parent.parent
            / "skills/skill-development/references/eval-schema.md"
        ).read_text(encoding="utf-8")

        self.assertIn('"require_outcome_coverage": true', schema)

    def test_workflow_skills_honor_explicit_stop_boundaries(self):
        root = MODULE_PATH.parent.parent
        formal_design = (root / "skills/formal-design/SKILL.md").read_text(encoding="utf-8")
        skill_development = (root / "skills/skill-development/SKILL.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("state necessary assumptions and proceed", formal_design)
        self.assertIn(
            "explicitly label `Approaches`, `Tradeoffs`, `Recommendation`, and `Approval request`",
            formal_design,
        )
        self.assertIn("do not inspect or modify the workspace", skill_development)
        self.assertIn("one response only", skill_development)

    def test_missing_trigger_gate_reports_error_without_raising(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory) / "trigger-cases.json"
            fixture.write_text('{"cases": []}\n', encoding="utf-8")
            errors = []

            with mock.patch.object(validate_skills, "TRIGGER_CASES_PATH", fixture):
                cases, gates = validate_skills.validate_trigger_cases(set(), errors)

            self.assertEqual(cases, [])
            self.assertEqual(gates, {})
            self.assertEqual(len(errors), 1)

    def test_local_markdown_links_support_standard_forms_and_ignore_fences(self):
        markdown = """\
[inline](missing_(inline).md)
[reference][ref]
[collapsed][]
[shortcut]

[ref]: missing_(reference).md "Reference title"
[collapsed]: missing-collapsed.md
[shortcut]: missing-shortcut.md

[anchor](#section)
[url](https://example.com/missing.md)
```markdown
[example](missing-example.md)
[example-ref]: missing-example-ref.md
```
"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            skill_file = root / "SKILL.md"
            skill_file.write_text(markdown, encoding="utf-8")
            errors = []

            with mock.patch.object(validate_skills, "REPO_ROOT", root):
                validate_skills.validate_links(skill_file, markdown, errors)

            self.assertEqual(
                errors,
                [
                    "SKILL.md: dangling local Markdown link 'missing_(inline).md'",
                    "SKILL.md: dangling local Markdown link 'missing_(reference).md'",
                    "SKILL.md: dangling local Markdown link 'missing-collapsed.md'",
                    "SKILL.md: dangling local Markdown link 'missing-shortcut.md'",
                ],
            )

    def test_inline_link_with_parenthesized_title_validates_target(self):
        markdown = "[doc](missing.md (Title))\n"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            skill_file = root / "SKILL.md"
            skill_file.write_text(markdown, encoding="utf-8")
            errors = []

            with mock.patch.object(validate_skills, "REPO_ROOT", root):
                validate_skills.validate_links(skill_file, markdown, errors)

            self.assertEqual(
                errors,
                ["SKILL.md: dangling local Markdown link 'missing.md'"],
            )

    def test_malformed_url_reports_one_line_error(self):
        markdown = "[doc](https://[invalid)\n"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            skill_file = root / "SKILL.md"
            errors = []

            with mock.patch.object(validate_skills, "REPO_ROOT", root):
                validate_skills.validate_links(skill_file, markdown, errors)

            self.assertEqual(len(errors), 1)
            self.assertNotIn("\n", errors[0])

    def test_percent_decoded_nul_link_reports_one_line_error(self):
        markdown = "[doc](missing%00file.md)\n"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            skill_file = root / "SKILL.md"
            errors = []

            with mock.patch.object(validate_skills, "REPO_ROOT", root):
                validate_skills.validate_links(skill_file, markdown, errors)

            self.assertEqual(len(errors), 1)
            self.assertNotIn("\n", errors[0])

    def test_manifest_rejects_skill_file_symlink_outside_repository(self):
        with tempfile.TemporaryDirectory() as repository, tempfile.TemporaryDirectory() as outside:
            root = Path(repository)
            skill_directory = root / "skills/example"
            skill_directory.mkdir(parents=True)
            outside_skill = Path(outside) / "SKILL.md"
            outside_skill.write_text(
                "---\nname: example\ndescription: Example skill.\n---\n",
                encoding="utf-8",
            )
            (skill_directory / "SKILL.md").symlink_to(outside_skill)
            manifest = root / "opencode-skills.json"
            manifest.write_text(
                '{"skills": {"example": "skills/example"}}\n', encoding="utf-8"
            )
            errors = []

            with mock.patch.object(validate_skills, "REPO_ROOT", root), mock.patch.object(
                validate_skills, "MANIFEST_PATH", manifest
            ):
                active_skills = validate_skills.validate_manifest(errors)

            self.assertEqual(active_skills, {})
            self.assertEqual(
                errors,
                ["opencode-skills.json: SKILL.md for 'example' escapes the repository"],
            )

    def test_nul_manifest_path_reports_one_line_error(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "opencode-skills.json"
            manifest.write_text(
                json.dumps({"skills": {"example": "skills/example\x00escape"}}),
                encoding="utf-8",
            )
            errors = []

            with mock.patch.object(validate_skills, "REPO_ROOT", root), mock.patch.object(
                validate_skills, "MANIFEST_PATH", manifest
            ):
                active_skills = validate_skills.validate_manifest(errors)

            self.assertEqual(active_skills, {})
            self.assertEqual(len(errors), 1)
            self.assertNotIn("\n", errors[0])

    def test_unsupported_multiline_frontmatter_key_stays_on_one_error_line(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            skill_file = root / "SKILL.md"
            skill_file.write_text(
                "---\nname: example\ndescription: Example skill.\n? |\n  bad\n  key\n: value\n---\n",
                encoding="utf-8",
            )
            errors = []

            with mock.patch.object(validate_skills, "REPO_ROOT", root):
                validate_skills.validate_frontmatter(skill_file, "example", errors)

            self.assertEqual(len(errors), 1)
            self.assertNotIn("\n", errors[0])

    def test_multiline_overlapping_skill_name_stays_on_one_error_line(self):
        fixtures = {
            "require_active_skill_references": False,
            "require_canonical_coverage": False,
            "require_outcome_coverage": False,
            "cases": [
                {
                    "id": "multiline-overlap",
                    "prompt": "Malformed fixture",
                    "expected_skills": ["bad\nname"],
                    "forbidden_skills": ["bad\nname"],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory) / "trigger-cases.json"
            fixture.write_text(json.dumps(fixtures), encoding="utf-8")
            errors = []

            with mock.patch.object(validate_skills, "TRIGGER_CASES_PATH", fixture):
                validate_skills.validate_trigger_cases(set(), errors)

            self.assertTrue(errors)
            self.assertTrue(all("\n" not in error for error in errors))

    def test_project_fixture_accepts_files_and_optional_git_boundaries(self):
        project = {
            "files": {"src/auth.py": "baseline\n"},
            "git": {
                "base_branch": "main",
                "branch": "review",
                "changes": {"src/auth.py": "changed\n"},
            },
        }
        errors = []

        validate_skills.validate_project_fixture("case", project, errors)

        self.assertEqual(errors, [])

    def test_project_fixture_rejects_escaping_file_path(self):
        errors = []

        validate_skills.validate_project_fixture(
            "case", {"files": {"../outside.py": "bad\n"}}, errors
        )

        self.assertEqual(errors, ["case: project file path '../outside.py' must stay relative"])


if __name__ == "__main__":
    unittest.main()
