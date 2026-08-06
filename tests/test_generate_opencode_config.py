#!/usr/bin/env python3
"""Unit tests for the OpenCode configuration generator."""

import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parent.parent / "tools/generate_opencode_config.py"
SPEC = importlib.util.spec_from_file_location("generate_opencode_config", MODULE_PATH)
generate_opencode_config = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(generate_opencode_config)

ConfigError = generate_opencode_config.ConfigError

BASE_CONFIG = {
    "$schema": "https://opencode.ai/config.json",
    "instructions": ["{{REPO}}/instructions/opencode-development.md"],
    "permission": {
        "*": "allow",
        "bash": {"*": "allow", "sudo *": "ask"},
        "edit": {"*": "allow", "{{HOME}}/.claude/skills/**": "deny"},
        "doom_loop": "ask",
    },
}


class FixtureRepository:
    """A minimal personal-skills checkout on disk."""

    def __init__(self, root, skills=("alpha", "beta"), nested=()):
        self.root = Path(root)
        entries = {}
        for name in skills:
            directory = self.root / "skills" / name
            directory.mkdir(parents=True)
            (directory / "SKILL.md").write_text(f"# {name}\n", encoding="utf-8")
            entries[name] = f"skills/{name}"
        for name in nested:
            directory = self.root / "opencode/skills" / name
            directory.mkdir(parents=True)
            (directory / "SKILL.md").write_text(f"# {name}\n", encoding="utf-8")
            entries[name] = f"opencode/skills/{name}"
        self.write_manifest(entries)
        instructions = self.root / "instructions"
        instructions.mkdir(parents=True)
        (instructions / "opencode-development.md").write_text("# rules\n", encoding="utf-8")
        self.base_path = self.root / "opencode-base.json"
        self.base_path.write_text(json.dumps(BASE_CONFIG, indent=2), encoding="utf-8")

    def write_manifest(self, skills):
        (self.root / "opencode-skills.json").write_text(
            json.dumps({"skills": skills}, indent=2), encoding="utf-8"
        )

    def build(self, home="/home/tester"):
        return generate_opencode_config.build_config(
            repository=self.root, home=home, base_path=self.base_path
        )


class GenerateConfigTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.repository = FixtureRepository(self.temporary.name)

    # --- derivation -----------------------------------------------------

    def test_skill_paths_are_derived_from_the_manifest_in_order(self):
        config = self.repository.build()

        self.assertEqual(
            config["skills"]["paths"],
            [
                str(self.repository.root / "skills/alpha"),
                str(self.repository.root / "skills/beta"),
            ],
        )

    def test_skill_permissions_deny_by_default_and_allow_every_manifest_skill(self):
        config = self.repository.build()

        self.assertEqual(
            config["permission"]["skill"],
            {"*": "deny", "alpha": "allow", "beta": "allow"},
        )

    def test_adding_a_skill_to_the_manifest_updates_both_derived_sections(self):
        directory = self.repository.root / "skills/gamma"
        directory.mkdir(parents=True)
        (directory / "SKILL.md").write_text("# gamma\n", encoding="utf-8")
        self.repository.write_manifest(
            {"alpha": "skills/alpha", "beta": "skills/beta", "gamma": "skills/gamma"}
        )

        config = self.repository.build()

        self.assertIn(str(directory), config["skills"]["paths"])
        self.assertEqual(config["permission"]["skill"]["gamma"], "allow")

    def test_nested_opencode_skill_directories_are_resolved(self):
        repository = FixtureRepository(
            Path(self.temporary.name) / "nested", skills=("alpha",), nested=("grill-me",)
        )

        config = repository.build()

        self.assertIn(str(repository.root / "opencode/skills/grill-me"), config["skills"]["paths"])

    def test_instructions_resolve_to_the_checkout(self):
        config = self.repository.build()

        self.assertEqual(
            config["instructions"],
            [str(self.repository.root / "instructions/opencode-development.md")],
        )

    # --- substitution and preservation -----------------------------------

    def test_home_placeholder_is_substituted(self):
        config = self.repository.build(home="/home/other")

        self.assertIn("/home/other/.claude/skills/**", config["permission"]["edit"])
        self.assertNotIn("{{HOME}}/.claude/skills/**", config["permission"]["edit"])

    def test_static_sections_are_preserved_verbatim(self):
        config = self.repository.build()

        self.assertEqual(config["permission"]["bash"], {"*": "allow", "sudo *": "ask"})
        self.assertEqual(config["permission"]["doom_loop"], "ask")
        self.assertEqual(config["$schema"], "https://opencode.ai/config.json")

    def test_no_placeholder_survives_generation(self):
        rendered = generate_opencode_config.render(self.repository.build())

        self.assertNotIn("{{REPO}}", rendered)
        self.assertNotIn("{{HOME}}", rendered)

    def test_generation_is_deterministic(self):
        first = generate_opencode_config.render(self.repository.build())
        second = generate_opencode_config.render(self.repository.build())

        self.assertEqual(first, second)

    # --- manifest rejection ----------------------------------------------

    def test_a_manifest_skill_without_a_skill_file_is_rejected(self):
        (self.repository.root / "skills/beta/SKILL.md").unlink()

        with self.assertRaises(ConfigError) as caught:
            self.repository.build()

        self.assertIn("beta", str(caught.exception))
        self.assertIn("SKILL.md", str(caught.exception))

    def test_an_absolute_manifest_path_is_rejected(self):
        self.repository.write_manifest({"alpha": "/etc"})

        with self.assertRaises(ConfigError) as caught:
            self.repository.build()

        self.assertIn("must be relative", str(caught.exception))

    def test_a_manifest_path_escaping_the_repository_is_rejected(self):
        self.repository.write_manifest({"alpha": "../outside"})

        with self.assertRaises(ConfigError) as caught:
            self.repository.build()

        self.assertIn("escapes the repository", str(caught.exception))

    def test_a_duplicate_manifest_key_is_rejected(self):
        (self.repository.root / "opencode-skills.json").write_text(
            '{"skills": {"alpha": "skills/alpha", "alpha": "skills/beta"}}', encoding="utf-8"
        )

        with self.assertRaises(ConfigError) as caught:
            self.repository.build()

        self.assertIn("duplicate key", str(caught.exception))

    def test_an_empty_manifest_is_rejected(self):
        self.repository.write_manifest({})

        with self.assertRaises(ConfigError) as caught:
            self.repository.build()

        self.assertIn("nonempty", str(caught.exception))

    def test_an_unexpected_manifest_root_key_is_rejected(self):
        (self.repository.root / "opencode-skills.json").write_text(
            '{"skills": {"alpha": "skills/alpha"}, "extra": 1}', encoding="utf-8"
        )

        with self.assertRaises(ConfigError) as caught:
            self.repository.build()

        self.assertIn("only a skills mapping", str(caught.exception))

    # --- verification -----------------------------------------------------

    def _write_generated(self, name="opencode.jsonc"):
        target = self.repository.root / name
        target.write_text(
            generate_opencode_config.render(self.repository.build()), encoding="utf-8"
        )
        return target

    def test_generated_configuration_verifies_clean(self):
        target = self._write_generated()

        self.assertEqual(generate_opencode_config.verify(target, self.repository.root), [])

    def test_verification_detects_a_missing_skill_path(self):
        target = self._write_generated()
        config = json.loads(target.read_text(encoding="utf-8"))
        config["skills"]["paths"] = config["skills"]["paths"][:1]
        target.write_text(json.dumps(config), encoding="utf-8")

        drift = generate_opencode_config.verify(target, self.repository.root)

        self.assertEqual(len(drift), 1)
        self.assertIn("skills.paths", drift[0])
        self.assertIn("beta", drift[0])

    def test_verification_detects_a_missing_skill_permission(self):
        target = self._write_generated()
        config = json.loads(target.read_text(encoding="utf-8"))
        del config["permission"]["skill"]["beta"]
        target.write_text(json.dumps(config), encoding="utf-8")

        drift = generate_opencode_config.verify(target, self.repository.root)

        self.assertEqual(len(drift), 1)
        self.assertIn("permission.skill", drift[0])
        self.assertIn("beta", drift[0])

    def test_verification_detects_an_unexpected_skill_permission(self):
        target = self._write_generated()
        config = json.loads(target.read_text(encoding="utf-8"))
        config["permission"]["skill"]["retired"] = "allow"
        target.write_text(json.dumps(config), encoding="utf-8")

        drift = generate_opencode_config.verify(target, self.repository.root)

        self.assertIn("unexpected", drift[0])
        self.assertIn("retired", drift[0])

    def test_verification_detects_a_skill_downgraded_to_deny(self):
        target = self._write_generated()
        config = json.loads(target.read_text(encoding="utf-8"))
        config["permission"]["skill"]["beta"] = "deny"
        target.write_text(json.dumps(config), encoding="utf-8")

        drift = generate_opencode_config.verify(target, self.repository.root)

        self.assertIn("changed", drift[0])
        self.assertIn("beta", drift[0])

    def test_verification_detects_a_missing_section(self):
        target = self._write_generated()
        config = json.loads(target.read_text(encoding="utf-8"))
        del config["skills"]
        target.write_text(json.dumps(config), encoding="utf-8")

        drift = generate_opencode_config.verify(target, self.repository.root)

        self.assertEqual(drift, ["skills.paths: missing"])

    def test_verification_detects_relocated_instructions(self):
        target = self._write_generated()
        config = json.loads(target.read_text(encoding="utf-8"))
        config["instructions"] = ["/somewhere/else.md"]
        target.write_text(json.dumps(config), encoding="utf-8")

        drift = generate_opencode_config.verify(target, self.repository.root)

        self.assertTrue(any("instructions" in item for item in drift))

    # --- writing ----------------------------------------------------------

    def test_writing_backs_up_an_existing_configuration(self):
        target = self.repository.root / "config/opencode.jsonc"
        target.parent.mkdir(parents=True)
        target.write_text("original\n", encoding="utf-8")

        backup = generate_opencode_config.write_config(self.repository.build(), target)

        self.assertIsNotNone(backup)
        self.assertEqual(backup.read_text(encoding="utf-8"), "original\n")
        self.assertIn("skills", json.loads(target.read_text(encoding="utf-8")))

    def test_writing_a_new_configuration_creates_no_backup(self):
        target = self.repository.root / "fresh/opencode.jsonc"

        backup = generate_opencode_config.write_config(self.repository.build(), target)

        self.assertIsNone(backup)
        self.assertTrue(target.is_file())

    # --- command line -----------------------------------------------------

    @staticmethod
    def _run(arguments):
        """Invoke the command line without leaking output into the test report."""
        with contextlib.redirect_stdout(io.StringIO()) as out:
            with contextlib.redirect_stderr(io.StringIO()) as err:
                status = generate_opencode_config.main(arguments)
        return status, out.getvalue() + err.getvalue()

    def test_verify_exits_nonzero_on_drift(self):
        target = self._write_generated()
        config = json.loads(target.read_text(encoding="utf-8"))
        config["skills"]["paths"] = []
        target.write_text(json.dumps(config), encoding="utf-8")

        status, output = self._run(
            ["--verify", str(target), "--repository", str(self.repository.root)]
        )

        self.assertEqual(status, 1)
        self.assertIn("drifted", output)

    def test_verify_exits_zero_when_consistent(self):
        target = self._write_generated()

        status, _ = self._run(
            ["--verify", str(target), "--repository", str(self.repository.root)]
        )

        self.assertEqual(status, 0)

    def test_verify_reports_a_missing_configuration(self):
        status, output = self._run(
            [
                "--verify",
                str(self.repository.root / "absent.jsonc"),
                "--repository",
                str(self.repository.root),
            ]
        )

        self.assertEqual(status, 1)
        self.assertIn("no configuration", output)

    def test_a_broken_manifest_exits_with_a_usage_status(self):
        self.repository.write_manifest({"alpha": "/etc"})
        target = self.repository.root / "opencode.jsonc"
        target.write_text("{}", encoding="utf-8")

        status, output = self._run(
            ["--verify", str(target), "--repository", str(self.repository.root)]
        )

        self.assertEqual(status, 2)
        self.assertIn("must be relative", output)

    def test_default_output_is_the_rendered_configuration(self):
        status, output = self._run(["--repository", str(self.repository.root)])

        self.assertEqual(status, 0)
        self.assertEqual(json.loads(output)["permission"]["skill"]["*"], "deny")

    # --- resolved-skill checking ------------------------------------------

    def _write_resolved(self, names):
        target = self.repository.root / "resolved.json"
        target.write_text(
            json.dumps([{"name": name, "location": f"/somewhere/{name}"} for name in names]),
            encoding="utf-8",
        )
        return target

    def test_resolved_check_accepts_the_full_manifest(self):
        target = self._write_resolved(["alpha", "beta"])

        missing, extra = generate_opencode_config.check_resolved(target, self.repository.root)

        self.assertEqual(missing, [])
        self.assertEqual(extra, [])

    def test_resolved_check_reports_a_skill_opencode_did_not_load(self):
        target = self._write_resolved(["alpha"])

        missing, _ = generate_opencode_config.check_resolved(target, self.repository.root)

        self.assertEqual(missing, ["beta"])

    def test_resolved_check_treats_builtin_skills_as_extra_not_missing(self):
        target = self._write_resolved(["alpha", "beta", "customize-opencode"])

        missing, extra = generate_opencode_config.check_resolved(target, self.repository.root)

        self.assertEqual(missing, [])
        self.assertEqual(extra, ["customize-opencode"])

    def test_resolved_check_accepts_an_object_wrapped_list(self):
        target = self.repository.root / "resolved.json"
        target.write_text(
            json.dumps({"skills": [{"name": "alpha"}, {"name": "beta"}]}), encoding="utf-8"
        )

        missing, _ = generate_opencode_config.check_resolved(target, self.repository.root)

        self.assertEqual(missing, [])

    def test_resolved_check_exits_nonzero_when_a_skill_is_missing(self):
        target = self._write_resolved(["alpha"])

        status, output = self._run(
            ["--check-resolved", str(target), "--repository", str(self.repository.root)]
        )

        self.assertEqual(status, 1)
        self.assertIn("beta", output)

    def test_resolved_check_exits_zero_when_complete(self):
        target = self._write_resolved(["alpha", "beta"])

        status, output = self._run(
            ["--check-resolved", str(target), "--repository", str(self.repository.root)]
        )

        self.assertEqual(status, 0)
        self.assertIn("all 2 manifest skills", output)

    def test_unreadable_debug_output_is_skipped_rather_than_failing(self):
        target = self.repository.root / "resolved.json"
        target.write_text("opencode debug skill\n", encoding="utf-8")

        status, output = self._run(
            ["--check-resolved", str(target), "--repository", str(self.repository.root)]
        )

        self.assertEqual(status, 0)
        self.assertIn("skipping skill verification", output)

    def test_unreadable_debug_output_raises_a_distinct_error(self):
        target = self.repository.root / "resolved.json"
        target.write_text("{}not json", encoding="utf-8")

        with self.assertRaises(generate_opencode_config.ResolvedOutputError):
            generate_opencode_config.check_resolved(target, self.repository.root)


class ShippedConfigurationTests(unittest.TestCase):
    """The real repository must stay generatable."""

    def test_the_repository_generates_a_configuration_for_every_manifest_skill(self):
        skills = generate_opencode_config.load_manifest()
        config = generate_opencode_config.build_config()

        self.assertEqual(len(config["skills"]["paths"]), len(skills))
        self.assertEqual(config["permission"]["skill"]["*"], "deny")
        for name in skills:
            self.assertEqual(config["permission"]["skill"][name], "allow")

    def test_the_base_configuration_denies_edits_to_installed_skill_directories(self):
        config = generate_opencode_config.build_config(home="/home/tester")

        edit = config["permission"]["edit"]
        self.assertEqual(edit["/home/tester/.claude/skills/**"], "deny")
        self.assertEqual(edit["/home/tester/.agents/skills/**"], "deny")

    def test_the_base_configuration_still_guards_destructive_commands(self):
        config = generate_opencode_config.build_config()

        bash = config["permission"]["bash"]
        for command in ("sudo *", "rm *", "git push*", "docker push*"):
            self.assertEqual(bash[command], "ask", f"{command} must require confirmation")

    def test_generated_configuration_verifies_against_itself(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "opencode.jsonc"
            target.write_text(
                generate_opencode_config.render(generate_opencode_config.build_config()),
                encoding="utf-8",
            )

            self.assertEqual(generate_opencode_config.verify(target), [])

    def test_the_readme_documents_every_manifest_skill(self):
        readme = (MODULE_PATH.parent.parent / "README.md").read_text(encoding="utf-8")

        undocumented = [
            name for name in generate_opencode_config.load_manifest() if f"`{name}`" not in readme
        ]

        self.assertEqual(undocumented, [], "add these skills to the README inventory tables")


if __name__ == "__main__":
    unittest.main()
