import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).with_name("evaluate_skills.py")
SPEC = importlib.util.spec_from_file_location("evaluate_skills", MODULE_PATH)
evaluate_skills = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = evaluate_skills
SPEC.loader.exec_module(evaluate_skills)


def manifest(root, count=12):
    skills = {}
    for index in range(count):
        name = f"skill-{index}"
        skill_directory = root / "skills" / name
        skill_directory.mkdir(parents=True)
        (skill_directory / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: Test skill.\n---\n",
            encoding="utf-8",
        )
        skills[name] = f"skills/{name}"
    return {"skills": skills}


class ArgumentTests(unittest.TestCase):
    def test_refuses_implicit_all_cases(self):
        args = evaluate_skills.parse_arguments(["--suite", "trigger"])

        with self.assertRaisesRegex(evaluate_skills.UsageError, "--all"):
            evaluate_skills.select_cases([{"id": "one"}], args.case, args.all)

    def test_selects_only_explicit_repeatable_case_ids(self):
        args = evaluate_skills.parse_arguments(
            ["--suite", "trigger", "--case", "two", "--case", "one"]
        )

        selected = evaluate_skills.select_cases(
            [{"id": "one"}, {"id": "two"}, {"id": "three"}],
            args.case,
            args.all,
        )

        self.assertEqual([case["id"] for case in selected], ["two", "one"])


class IsolationTests(unittest.TestCase):
    def test_writes_twelve_explicit_paths_and_personal_instructions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository = root / "repository"
            repository.mkdir()
            fixture_manifest = manifest(repository)
            instructions = repository / "instructions/opencode-development.md"
            instructions.parent.mkdir()
            instructions.write_text("# Instructions\n", encoding="utf-8")
            xdg_root = root / "xdg"

            config_path, expected_paths, instruction_path = evaluate_skills.write_isolated_config(
                xdg_root, repository, fixture_manifest
            )

            config = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertEqual(config_path, xdg_root / "opencode/opencode.json")
            self.assertEqual(config["skills"]["paths"], [str(path) for path in expected_paths.values()])
            self.assertEqual(config["instructions"], [str(instructions.resolve())])
            self.assertEqual(instruction_path, instructions.resolve())
            self.assertEqual(len(config["skills"]["paths"]), 12)
            self.assertEqual(config.get("plugin", []), [])

    def test_environment_disables_all_external_discovery_without_config_dir(self):
        parent = {
            "PATH": "/bin",
            "GITHUB_TOKEN": "personal-access-token",
            "OPENCODE_CONFIG_DIR": "/unsafe/additive/config",
            "OPENCODE_CONFIG": "/unsafe/extra.json",
            "OPENCODE_CONFIG_CONTENT": '{"plugin":["unsafe"]}',
            "XDG_CONFIG_HOME": "/old/config",
        }

        environment = evaluate_skills.build_environment(Path("/isolated/xdg"), parent)

        self.assertEqual(environment["PATH"], "/bin")
        self.assertEqual(environment["XDG_CONFIG_HOME"], "/isolated/xdg")
        self.assertEqual(environment["OPENCODE_PURE"], "1")
        self.assertEqual(environment["OPENCODE_DISABLE_CLAUDE_CODE_SKILLS"], "1")
        self.assertEqual(environment["OPENCODE_DISABLE_EXTERNAL_SKILLS"], "1")
        self.assertEqual(environment["OPENCODE_DISABLE_DEFAULT_PLUGINS"], "1")
        self.assertEqual(environment["OPENCODE_DISABLE_PROJECT_CONFIG"], "1")
        self.assertNotIn("OPENCODE_CONFIG_DIR", environment)
        self.assertNotIn("OPENCODE_CONFIG", environment)
        self.assertNotIn("OPENCODE_CONFIG_CONTENT", environment)
        self.assertNotIn("GITHUB_TOKEN", environment)

    def test_baseline_config_omits_only_target_skill(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository = root / "repository"
            repository.mkdir()
            fixture_manifest = manifest(repository)
            instructions = repository / "instructions/opencode-development.md"
            instructions.parent.mkdir()
            instructions.write_text(
                "# Instructions\n\n"
                "Load `skill-4` before changing it.\n"
                "Load `skill-5` before changing it.\n",
                encoding="utf-8",
            )

            config_path, expected_paths, instruction_path = evaluate_skills.write_isolated_config(
                root / "xdg", repository, fixture_manifest, omitted_skill="skill-4"
            )

            config = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertEqual(set(expected_paths), set(fixture_manifest["skills"]) - {"skill-4"})
            self.assertNotIn(str((repository / "skills/skill-4").resolve()), config["skills"]["paths"])
            self.assertEqual(config["instructions"], [str(instruction_path)])
            baseline_instructions = instruction_path.read_text(encoding="utf-8")
            self.assertNotIn("`skill-4`", baseline_instructions)
            self.assertIn("`skill-5`", baseline_instructions)


class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.paths = {
            "formal-design": Path("/repo/skills/formal-design").resolve(),
            "code-review": Path("/repo/skills/code-review").resolve(),
        }
        self.config = json.dumps(
            {
                "plugin": [],
                "instructions": ["/repo/instructions/opencode-development.md"],
                "skills": {"paths": [str(path) for path in self.paths.values()]},
            }
        )
        self.instructions = Path("/repo/instructions/opencode-development.md").resolve()
        self.inventory = json.dumps(
            [
                {
                    "name": name,
                    "location": str(path / "SKILL.md"),
                }
                for name, path in self.paths.items()
            ]
            + [{"name": "customize-opencode", "builtin": True}]
        )

    def test_accepts_exact_manifest_inventory_plus_builtin_allowlist(self):
        result = evaluate_skills.validate_preflight(
            self.config, self.inventory, self.paths, self.instructions
        )

        self.assertEqual(result["additional_builtin_skills"], ["customize-opencode"])

    def test_accepts_1189_builtin_location_marker(self):
        inventory = json.loads(self.inventory)
        inventory[-1] = {"name": "customize-opencode", "location": "<built-in>"}

        result = evaluate_skills.validate_preflight(
            self.config, json.dumps(inventory), self.paths, self.instructions
        )

        self.assertEqual(result["additional_builtin_skills"], ["customize-opencode"])

    def test_rejects_plugins_in_resolved_config(self):
        config = json.dumps({"plugin": ["superpowers"], "skills": {"paths": []}})

        with self.assertRaisesRegex(evaluate_skills.PreflightError, "plugin"):
            evaluate_skills.validate_preflight(
                config, self.inventory, self.paths, self.instructions
            )

    def test_rejects_additional_resolved_instruction(self):
        config = json.loads(self.config)
        config["instructions"].append("/global/AGENTS.md")

        with self.assertRaisesRegex(evaluate_skills.PreflightError, "instructions"):
            evaluate_skills.validate_preflight(
                json.dumps(config), self.inventory, self.paths, self.instructions
            )

    def test_preflight_rejects_substituted_resolved_instruction(self):
        config = json.loads(self.config)
        config["instructions"] = ["/evil/instructions.md"]

        with mock.patch.object(
            evaluate_skills,
            "run_process",
            side_effect=[json.dumps(config), self.inventory],
        ), self.assertRaisesRegex(evaluate_skills.PreflightError, "instructions"):
            evaluate_skills.preflight(
                "opencode",
                {},
                self.paths,
                timeout=10,
                expected_instruction=self.instructions,
            )

    def test_rejects_manifest_skill_resolved_from_wrong_path(self):
        inventory = json.loads(self.inventory)
        inventory[0]["location"] = "/global/formal-design/SKILL.md"

        with self.assertRaisesRegex(evaluate_skills.PreflightError, "formal-design.*path"):
            evaluate_skills.validate_preflight(
                self.config, json.dumps(inventory), self.paths, self.instructions
            )

    def test_rejects_manifest_skill_with_plugin_source_at_expected_path(self):
        inventory = json.loads(self.inventory)
        inventory[0]["source"] = "plugin"

        with self.assertRaisesRegex(evaluate_skills.PreflightError, "formal-design.*source"):
            evaluate_skills.validate_preflight(
                self.config, json.dumps(inventory), self.paths, self.instructions
            )

    def test_rejects_manifest_skill_with_external_source_at_expected_path(self):
        inventory = json.loads(self.inventory)
        inventory[0]["source"] = "external"

        with self.assertRaisesRegex(evaluate_skills.PreflightError, "formal-design.*source"):
            evaluate_skills.validate_preflight(
                self.config, json.dumps(inventory), self.paths, self.instructions
            )

    def test_rejects_unexpected_additional_skill(self):
        inventory = json.loads(self.inventory)
        inventory.append({"name": "using-superpowers", "location": "/cache/SKILL.md"})

        with self.assertRaisesRegex(evaluate_skills.PreflightError, "using-superpowers"):
            evaluate_skills.validate_preflight(
                self.config, json.dumps(inventory), self.paths, self.instructions
            )

    def test_rejects_disk_backed_copy_of_allowlisted_builtin(self):
        inventory = json.loads(self.inventory)
        inventory[-1] = {
            "name": "customize-opencode",
            "location": "/global/customize-opencode/SKILL.md",
        }

        with self.assertRaisesRegex(evaluate_skills.PreflightError, "disk-backed"):
            evaluate_skills.validate_preflight(
                self.config, json.dumps(inventory), self.paths, self.instructions
            )

    def test_rejects_allowlisted_builtin_with_plugin_source(self):
        inventory = json.loads(self.inventory)
        inventory[-1] = {
            "name": "customize-opencode",
            "location": "<built-in>",
            "source": "plugin",
        }

        with self.assertRaisesRegex(evaluate_skills.PreflightError, "contradictory"):
            evaluate_skills.validate_preflight(
                self.config, json.dumps(inventory), self.paths, self.instructions
            )

    def test_rejects_allowlisted_builtin_with_false_builtin_marker(self):
        inventory = json.loads(self.inventory)
        inventory[-1] = {
            "name": "customize-opencode",
            "location": "<built-in>",
            "builtin": False,
        }

        with self.assertRaisesRegex(evaluate_skills.PreflightError, "contradictory"):
            evaluate_skills.validate_preflight(
                self.config, json.dumps(inventory), self.paths, self.instructions
            )


class EventParsingTests(unittest.TestCase):
    def test_rejects_empty_event_stream(self):
        with self.assertRaisesRegex(evaluate_skills.MalformedEventError, "no JSON events"):
            evaluate_skills.parse_event_stream("")

    def test_parses_1189_tool_use_and_text_events(self):
        stream = "\n".join(
            [
                json.dumps(
                    {
                        "type": "tool_use",
                        "part": {
                            "tool": "skill",
                            "state": {"input": {"name": "code-review"}},
                        },
                    }
                ),
                json.dumps(
                    {
                        "type": "tool_use",
                        "part": {"tool": "read", "state": {"input": {"filePath": "/tmp/a"}}},
                    }
                ),
                json.dumps({"type": "text", "part": {"text": "Issues\n"}}),
                json.dumps({"type": "text", "part": {"text": "Critical: file.py:7"}}),
            ]
        )

        observation = evaluate_skills.parse_event_stream(stream)

        self.assertEqual(observation.skill_calls, {"code-review"})
        self.assertEqual(observation.tools, {"skill", "read"})
        self.assertEqual(observation.text, "Issues\nCritical: file.py:7")

    def test_rejects_malformed_json_with_line_number(self):
        stream = '{"type":"step_start"}\nnot-json\n'

        with self.assertRaisesRegex(evaluate_skills.MalformedEventError, "line 2") as caught:
            evaluate_skills.parse_event_stream(stream)

        self.assertEqual(caught.exception.event_stream, stream)

    def test_rejects_tool_event_missing_skill_name(self):
        stream = json.dumps(
            {"type": "tool_use", "part": {"tool": "skill", "state": {"input": {}}}}
        )

        with self.assertRaisesRegex(evaluate_skills.MalformedEventError, "skill.*name"):
            evaluate_skills.parse_event_stream(stream)

    def test_rejects_text_event_with_non_string_text(self):
        stream = json.dumps({"type": "text", "part": {"text": 17}})

        with self.assertRaisesRegex(evaluate_skills.MalformedEventError, "text"):
            evaluate_skills.parse_event_stream(stream)

    def test_raises_nested_diagnostic_for_1189_error_event(self):
        stream = json.dumps(
            {
                "type": "error",
                "timestamp": 1785342230552,
                "sessionID": "ses_example",
                "error": {
                    "name": "APIError",
                    "data": {
                        "message": "Bad Request: checking third-party user token",
                        "statusCode": 400,
                        "responseBody": "Personal Access Tokens are not supported\n",
                    },
                },
            }
        )

        with self.assertRaisesRegex(
            evaluate_skills.OpenCodeEventError,
            "APIError.*status 400.*Personal Access Tokens",
        ) as caught:
            evaluate_skills.parse_event_stream(stream)

        self.assertEqual(caught.exception.event_stream, stream)


class ProjectFixtureTests(unittest.TestCase):
    def test_creates_files_without_initializing_git(self):
        project = {
            "files": {
                "src/auth.py": "def allowed(user):\n    return bool(user)\n",
                "README.md": "Review fixture\n",
            }
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            evaluate_skills.prepare_project(root, project)

            self.assertEqual(
                (root / "src/auth.py").read_text(encoding="utf-8"),
                project["files"]["src/auth.py"],
            )
            self.assertFalse((root / ".git").exists())

    def test_creates_committed_base_and_review_branch_when_requested(self):
        project = {
            "files": {"auth.py": "def allowed(user):\n    return user.is_admin\n"},
            "git": {
                "base_branch": "main",
                "branch": "review",
                "changes": {"auth.py": "def allowed(user):\n    return bool(user)\n"},
            },
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            evaluate_skills.prepare_project(root, project)

            branch = evaluate_skills.run_process(
                ["git", "branch", "--show-current"], os.environ.copy(), 5, cwd=root
            ).strip()
            changed = evaluate_skills.run_process(
                ["git", "diff", "main...review", "--", "auth.py"],
                os.environ.copy(),
                5,
                cwd=root,
            )
            self.assertEqual(branch, "review")
            self.assertIn("return bool(user)", changed)


class ScoringTests(unittest.TestCase):
    def observation(self, skills=(), tools=(), text=""):
        return evaluate_skills.Observation(set(skills), set(tools), text)

    def test_trigger_requires_exact_called_skill_set(self):
        case = {
            "expected_skills": ["code-review"],
            "forbidden_skills": [],
        }

        passed = evaluate_skills.score_trigger(
            case, self.observation(["code-review"], ["skill"])
        )
        failed = evaluate_skills.score_trigger(
            case,
            self.observation(["code-review", "formal-design"], ["skill"]),
        )

        self.assertTrue(passed["passed"])
        self.assertFalse(failed["passed"])
        self.assertIn("formal-design", failed["unexpected_skills"])

    def test_direct_trigger_case_fails_on_any_skill_call(self):
        result = evaluate_skills.score_trigger(
            {"expected_skills": [], "forbidden_skills": ["hard-debugging"]},
            self.observation(["prototype"], ["skill"]),
        )

        self.assertFalse(result["passed"])
        self.assertEqual(result["unexpected_skills"], ["prototype"])

    def test_outcome_passes_when_current_passes_and_improves_failing_baseline(self):
        case = {
            "skill": "code-review",
            "required_tools": ["read"],
            "forbidden_tools": ["apply_patch"],
            "required_text_patterns": [r"(?i)^issues", r"file\.py:7"],
            "forbidden_text_patterns": [r"(?i)looks good"],
        }
        current = self.observation(
            ["code-review"], ["skill", "read"], "Issues\nImportant file.py:7"
        )
        baseline = self.observation([], [], "I cannot review this.")

        result = evaluate_skills.score_outcome(case, current, baseline)

        self.assertTrue(result["passed"])
        self.assertTrue(result["current"]["outcome_passed"])
        self.assertFalse(result["baseline"]["outcome_passed"])
        self.assertEqual(result["comparison"], "improved_failing_baseline")

    def test_outcome_reports_already_passing_baseline_without_failing(self):
        case = {
            "skill": "formal-planning",
            "required_tools": [],
            "forbidden_tools": ["apply_patch"],
            "required_text_patterns": [r"(?i)acceptance"],
            "forbidden_text_patterns": [r"mandatory commit"],
        }
        current = self.observation(
            ["formal-planning"], ["skill"], "Acceptance checks"
        )
        baseline = self.observation([], [], "Acceptance checks")

        result = evaluate_skills.score_outcome(case, current, baseline)

        self.assertTrue(result["passed"])
        self.assertEqual(result["comparison"], "already_passing_baseline")

    def test_outcome_fails_when_current_checks_fail(self):
        case = {
            "skill": "formal-design",
            "required_tools": [],
            "forbidden_tools": ["apply_patch"],
            "required_text_patterns": [r"trade-?offs?"],
            "forbidden_text_patterns": [],
        }
        current = self.observation(
            ["formal-design"], ["skill", "apply_patch"], "One approach"
        )
        baseline = self.observation([], [], "One approach")

        result = evaluate_skills.score_outcome(case, current, baseline)

        self.assertFalse(result["passed"])
        self.assertIn("apply_patch", result["current"]["present_forbidden_tools"])

    def test_outcome_fails_if_current_does_not_call_exact_target(self):
        case = {
            "skill": "hard-debugging",
            "required_tools": [],
            "forbidden_tools": [],
            "required_text_patterns": [],
            "forbidden_text_patterns": [],
        }
        current = self.observation(
            ["hard-debugging", "formal-design"], ["skill"], "Evidence"
        )
        baseline = self.observation([], [], "No evidence")

        result = evaluate_skills.score_outcome(case, current, baseline)

        self.assertFalse(result["passed"])
        self.assertFalse(result["current"]["trigger_passed"])

    def test_outcome_fails_if_baseline_invokes_omitted_target(self):
        case = {
            "skill": "skill-development",
            "required_tools": [],
            "forbidden_tools": [],
            "required_text_patterns": [],
            "forbidden_text_patterns": [],
        }
        current = self.observation(["skill-development"], ["skill"], "No change")
        baseline = self.observation(["skill-development"], ["skill"], "No change")

        result = evaluate_skills.score_outcome(case, current, baseline)

        self.assertFalse(result["passed"])
        self.assertFalse(result["baseline"]["target_absent"])

    def test_repeated_trials_aggregate_into_one_case_result(self):
        trials = [
            {"id": "case", "run": 1, "passed": True, "called_skills": ["code-review"]},
            {"id": "case", "run": 2, "passed": False, "called_skills": []},
        ]

        result = evaluate_skills.aggregate_trials("trigger", "case", trials)

        self.assertEqual(result["id"], "case")
        self.assertFalse(result["passed"])
        self.assertEqual(result["runs"], trials)


class ProcessAndTranscriptTests(unittest.TestCase):
    def test_timeout_has_clear_diagnostic(self):
        with self.assertRaisesRegex(evaluate_skills.TrialTimeout, "0.05"):
            evaluate_skills.run_process(
                [sys.executable, "-c", "import time; time.sleep(1)"],
                os.environ.copy(),
                timeout=0.05,
            )

    def test_timeout_preserves_partial_event_stream(self):
        event = json.dumps({"type": "text", "part": {"text": "partial"}})

        with self.assertRaises(evaluate_skills.TrialTimeout) as caught:
            evaluate_skills.run_process(
                [
                    sys.executable,
                    "-c",
                    f"import time; print({event!r}, flush=True); time.sleep(1)",
                ],
                os.environ.copy(),
                timeout=0.05,
            )

        self.assertIn(event, caught.exception.event_stream)

    def test_failed_process_includes_exit_status_and_event_stream(self):
        event = json.dumps({"type": "text", "part": {"text": "partial"}})

        with self.assertRaises(evaluate_skills.ProcessFailure) as caught:
            evaluate_skills.run_process(
                [sys.executable, "-c", f"import sys; print({event!r}); sys.exit(7)"],
                os.environ.copy(),
                timeout=1,
            )

        self.assertEqual(caught.exception.returncode, 7)
        self.assertIn(event, caught.exception.event_stream)

    def test_success_transcript_is_not_retained(self):
        with tempfile.TemporaryDirectory() as directory:
            path = evaluate_skills.retain_failure_stream(
                Path(directory), "case-id", "events", passed=True
            )

            self.assertIsNone(path)
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_failure_transcript_is_saved_and_path_returned(self):
        with tempfile.TemporaryDirectory() as directory:
            path = evaluate_skills.retain_failure_stream(
                Path(directory), "case-id", "event-one\nevent-two\n", passed=False
            )

            self.assertEqual(path.read_text(encoding="utf-8"), "event-one\nevent-two\n")
            self.assertIn("case-id", path.name)

    def test_outcome_failure_retains_separately_labeled_streams(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = evaluate_skills.retain_failure_streams(
                Path(directory),
                "case-id-run-1",
                {"current": "current-event\n", "baseline": "baseline-event\n"},
                passed=False,
            )

            self.assertEqual(set(paths), {"current", "baseline"})
            self.assertIn("current", paths["current"].name)
            self.assertIn("baseline", paths["baseline"].name)
            self.assertEqual(paths["current"].read_text(encoding="utf-8"), "current-event\n")
            self.assertEqual(paths["baseline"].read_text(encoding="utf-8"), "baseline-event\n")

    def test_baseline_error_preserves_current_and_baseline_streams(self):
        case = {"id": "outcome", "prompt": "Prompt", "skill": "code-review"}
        current = evaluate_skills.Observation({"code-review"}, {"skill"}, "Findings")
        baseline_error = evaluate_skills.OpenCodeEventError(
            "provider failed", "baseline-error-event\n"
        )

        with mock.patch.object(
            evaluate_skills,
            "run_trial",
            side_effect=[(current, "current-event\n"), baseline_error],
        ), self.assertRaises(evaluate_skills.LabeledTrialError) as caught:
            evaluate_skills.evaluate_outcome_case(
                case, 1, "opencode", {}, {}, None, 10
            )

        self.assertEqual(
            caught.exception.event_streams,
            {"current": "current-event\n", "baseline": "baseline-error-event\n"},
        )

    def test_current_error_still_runs_and_retains_baseline(self):
        case = {"id": "outcome", "prompt": "Prompt", "skill": "code-review"}
        current_error = evaluate_skills.OpenCodeEventError(
            "current provider failed", "current-error-event\n"
        )
        baseline = evaluate_skills.Observation(set(), set(), "Baseline")

        with mock.patch.object(
            evaluate_skills,
            "run_trial",
            side_effect=[current_error, (baseline, "baseline-event\n")],
        ) as trial, self.assertRaises(evaluate_skills.LabeledTrialError) as caught:
            evaluate_skills.evaluate_outcome_case(
                case, 1, "opencode", {}, {}, None, 10
            )

        self.assertEqual(trial.call_count, 2)
        self.assertEqual(
            caught.exception.event_streams,
            {"current": "current-error-event\n", "baseline": "baseline-event\n"},
        )


class MainContractTests(unittest.TestCase):
    def make_repository(self, root, cases):
        repository = root / "repository"
        repository.mkdir()
        fixture_manifest = manifest(repository)
        instructions = repository / "instructions/opencode-development.md"
        instructions.parent.mkdir()
        instructions.write_text("# Instructions\n", encoding="utf-8")
        manifest_path = repository / "opencode-skills.json"
        manifest_path.write_text(json.dumps(fixture_manifest), encoding="utf-8")
        trigger_path = repository / "trigger.json"
        trigger_path.write_text(json.dumps({"cases": cases}), encoding="utf-8")
        return repository, manifest_path, trigger_path

    def run_main(self, cases, observations, arguments):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository, manifest_path, trigger_path = self.make_repository(root, cases)
            output = io.StringIO()
            errors = io.StringIO()
            streams = [(observation, f'{{"type":"text","part":{{"text":"{index}"}}}}\n')
                       for index, observation in enumerate(observations)]
            with mock.patch.multiple(
                evaluate_skills,
                REPO_ROOT=repository,
                MANIFEST_PATH=manifest_path,
                TRIGGER_CASES_PATH=trigger_path,
            ), mock.patch.object(
                evaluate_skills, "locate_opencode", return_value="opencode"
            ), mock.patch.object(
                evaluate_skills, "preflight", return_value={}
            ), mock.patch.object(
                evaluate_skills, "run_trial", side_effect=streams
            ), redirect_stdout(output), redirect_stderr(errors):
                status = evaluate_skills.main(arguments)
            return status, [json.loads(line) for line in output.getvalue().splitlines()], errors.getvalue()

    def test_main_emits_selected_case_results_in_order_then_summary(self):
        cases = [
            {"id": "first", "prompt": "First", "expected_skills": [], "forbidden_skills": []},
            {"id": "second", "prompt": "Second", "expected_skills": [], "forbidden_skills": []},
        ]

        status, documents, errors = self.run_main(
            cases,
            [evaluate_skills.Observation(set(), set(), "one"), evaluate_skills.Observation(set(), set(), "two")],
            ["--suite", "trigger", "--case", "second", "--case", "first"],
        )

        self.assertEqual(status, 0)
        self.assertEqual([document.get("id") for document in documents[:-1]], ["second", "first"])
        self.assertEqual(
            documents[-1],
            {"summary": {"suite": "trigger", "results": 2, "passed": 2, "failed": 0, "already_passing_baselines": 0}},
        )
        self.assertEqual(errors, "")

    def test_main_returns_one_and_summarizes_case_mismatch(self):
        cases = [
            {"id": "review", "prompt": "Review", "expected_skills": ["code-review"], "forbidden_skills": []}
        ]

        status, documents, _ = self.run_main(
            cases,
            [evaluate_skills.Observation(set(), set(), "")],
            ["--suite", "trigger", "--case", "review"],
        )

        self.assertEqual(status, 1)
        self.assertFalse(documents[0]["passed"])
        self.assertEqual(documents[-1]["summary"]["failed"], 1)

    def test_main_returns_two_for_unknown_case_without_result_summary(self):
        cases = [
            {"id": "known", "prompt": "Known", "expected_skills": [], "forbidden_skills": []}
        ]

        status, documents, errors = self.run_main(
            cases, [], ["--suite", "trigger", "--case", "unknown"]
        )

        self.assertEqual(status, 2)
        self.assertEqual(documents, [])
        self.assertIn("unknown case IDs", errors)


if __name__ == "__main__":
    unittest.main()
