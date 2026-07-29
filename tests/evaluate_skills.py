#!/usr/bin/env python3
"""Evaluate OpenCode skill triggering and deterministic workflow outcomes."""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT / "opencode-skills.json"
TRIGGER_CASES_PATH = REPO_ROOT / "tests/fixtures/trigger-cases.json"
OUTCOME_CASES_PATH = REPO_ROOT / "tests/fixtures/outcome-cases.json"
BUILTIN_SKILL_ALLOWLIST = {"customize-opencode"}
ISOLATION_ENVIRONMENT = {
    "OPENCODE_PURE": "1",
    "OPENCODE_DISABLE_CLAUDE_CODE_SKILLS": "1",
    "OPENCODE_DISABLE_EXTERNAL_SKILLS": "1",
    "OPENCODE_DISABLE_DEFAULT_PLUGINS": "1",
    "OPENCODE_DISABLE_PROJECT_CONFIG": "1",
}


class EvaluationError(Exception):
    """Base class for expected evaluation failures."""


class UsageError(EvaluationError):
    pass


class PreflightError(EvaluationError):
    pass


class MalformedEventError(EvaluationError):
    def __init__(self, message, event_stream=""):
        self.event_stream = event_stream
        super().__init__(message)


class TrialTimeout(EvaluationError):
    def __init__(self, message, event_stream=""):
        self.event_stream = event_stream
        super().__init__(message)


class OpenCodeEventError(EvaluationError):
    def __init__(self, message, event_stream=""):
        self.event_stream = event_stream
        super().__init__(message)


class LabeledTrialError(EvaluationError):
    def __init__(self, message, event_streams):
        self.event_streams = event_streams
        super().__init__(message)


class ProcessFailure(EvaluationError):
    def __init__(self, command, returncode, event_stream, stderr):
        self.command = command
        self.returncode = returncode
        self.event_stream = event_stream
        self.stderr = stderr
        super().__init__(
            f"command exited {returncode}: {' '.join(command)}"
            + (f"; stderr: {' '.join(stderr.splitlines())}" if stderr else "")
        )


@dataclass
class Observation:
    skill_calls: set
    tools: set
    text: str


def parse_arguments(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", choices=("trigger", "outcome"), required=True)
    parser.add_argument("--case", action="append", default=[])
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--model")
    parser.add_argument("--timeout", type=float, default=120.0)
    args = parser.parse_args(arguments)
    if args.runs < 1:
        parser.error("--runs must be at least 1")
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    if args.all and args.case:
        parser.error("--all and --case cannot be combined")
    return args


def select_cases(cases, case_ids, run_all):
    if not run_all and not case_ids:
        raise UsageError("refusing model-costing evaluation without --case; use --all explicitly")
    if run_all:
        return cases
    by_id = {case["id"]: case for case in cases}
    missing = [case_id for case_id in case_ids if case_id not in by_id]
    if missing:
        raise UsageError(f"unknown case IDs: {', '.join(missing)}")
    return [by_id[case_id] for case_id in case_ids]


def load_json(path):
    try:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise EvaluationError(f"cannot load {path}: {exc}") from exc


def manifest_paths(repository, manifest, omitted_skill=None):
    paths = {}
    for name, relative_path in manifest["skills"].items():
        if name == omitted_skill:
            continue
        path = (repository / relative_path).resolve()
        if not (path / "SKILL.md").is_file():
            raise EvaluationError(f"manifest skill {name!r} has no SKILL.md at {path}")
        paths[name] = path
    return paths


def write_isolated_config(xdg_root, repository, manifest, omitted_skill=None):
    expected_paths = manifest_paths(repository, manifest, omitted_skill)
    config_path = xdg_root / "opencode/opencode.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    instructions = (repository / "instructions/opencode-development.md").resolve()
    configured_instructions = instructions
    if omitted_skill is not None:
        configured_instructions = config_path.with_name("baseline-instructions.md")
        lines = instructions.read_text(encoding="utf-8").splitlines(keepends=True)
        configured_instructions.write_text(
            "".join(line for line in lines if f"`{omitted_skill}`" not in line),
            encoding="utf-8",
        )
    config = {
        "plugin": [],
        "instructions": [str(configured_instructions)],
        "skills": {"paths": [str(path) for path in expected_paths.values()]},
    }
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    return config_path, expected_paths, configured_instructions


def build_environment(xdg_root, parent=None):
    environment = dict(os.environ if parent is None else parent)
    for variable in (
        "GITHUB_TOKEN",
        "OPENCODE_CONFIG",
        "OPENCODE_CONFIG_CONTENT",
        "OPENCODE_CONFIG_DIR",
    ):
        environment.pop(variable, None)
    environment["XDG_CONFIG_HOME"] = str(xdg_root)
    environment.update(ISOLATION_ENVIRONMENT)
    return environment


def parse_json_document(output, label):
    try:
        return json.loads(output)
    except json.JSONDecodeError as exc:
        raise PreflightError(f"{label} did not return valid JSON: {exc}") from exc


def inventory_entries(document):
    if isinstance(document, list):
        return document
    if isinstance(document, dict):
        for key in ("skills", "data"):
            if isinstance(document.get(key), list):
                return document[key]
        if all(isinstance(value, dict) for value in document.values()):
            return [dict(value, name=value.get("name", name)) for name, value in document.items()]
    raise PreflightError("debug skill output must be a skill list or mapping")


def entry_location(entry):
    for key in ("location", "path", "file"):
        value = entry.get(key)
        if isinstance(value, str) and value:
            if value == "<built-in>":
                return None
            return Path(value).resolve()
    return None


def is_builtin_entry(entry):
    if entry.get("builtin") is True or entry.get("builtIn") is True:
        return True
    if entry.get("location") == "<built-in>":
        return True
    source = entry.get("source")
    return isinstance(source, str) and source.casefold() in {"builtin", "built-in"}


def entry_source(entry):
    source = entry.get("source")
    return source.casefold() if isinstance(source, str) else None


def validate_preflight(config_output, skill_output, expected_paths, expected_instruction):
    config = parse_json_document(config_output, "debug config")
    if not isinstance(config, dict):
        raise PreflightError("debug config output must be a JSON object")
    if config.get("plugin"):
        raise PreflightError(f"resolved config contains plugin entries: {config['plugin']!r}")
    expected_instructions = [str(expected_instruction.resolve())]
    if config.get("instructions") != expected_instructions:
        raise PreflightError(
            f"resolved instructions differ from personal instructions: expected "
            f"{expected_instructions!r}, got {config.get('instructions')!r}"
        )
    configured_paths = config.get("skills", {}).get("paths", [])
    expected_path_strings = [str(path.resolve()) for path in expected_paths.values()]
    if configured_paths != expected_path_strings:
        raise PreflightError(
            f"resolved skill paths differ from manifest: expected {expected_path_strings!r}, "
            f"got {configured_paths!r}"
        )

    entries = inventory_entries(parse_json_document(skill_output, "debug skill"))
    seen = {}
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("name"), str):
            raise PreflightError(f"malformed debug skill entry: {entry!r}")
        name = entry["name"]
        if name in seen:
            raise PreflightError(f"duplicate resolved skill name: {name}")
        seen[name] = entry

    for name, expected_directory in expected_paths.items():
        entry = seen.get(name)
        if entry is None:
            raise PreflightError(f"manifest skill {name} is missing from debug skill output")
        location = entry_location(entry)
        expected_file = (expected_directory / "SKILL.md").resolve()
        if location not in {expected_directory.resolve(), expected_file}:
            raise PreflightError(
                f"manifest skill {name} resolved from wrong path: {location}; expected {expected_file}"
            )
        if entry_source(entry) in {"plugin", "external"}:
            raise PreflightError(
                f"manifest skill {name} has rejected source marker {entry['source']!r}"
            )

    additional = sorted(set(seen) - set(expected_paths))
    unexpected = sorted(set(additional) - BUILTIN_SKILL_ALLOWLIST)
    if unexpected:
        raise PreflightError(f"unexpected additional skills: {', '.join(unexpected)}")
    for name in additional:
        entry = seen[name]
        contradictory = (
            entry_source(entry) in {"plugin", "external"}
            or entry.get("builtin") is False
            or entry.get("builtIn") is False
        )
        if contradictory:
            raise PreflightError(f"allowlisted built-in {name} has contradictory source markers")
        if entry_location(entry) is not None or not is_builtin_entry(entry):
            raise PreflightError(f"allowlisted built-in {name} is disk-backed or not marked built-in")
    return {"additional_builtin_skills": additional}


def run_process(command, environment, timeout, cwd=None):
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=environment,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        event_stream = exc.stdout or ""
        if isinstance(event_stream, bytes):
            event_stream = event_stream.decode(errors="replace")
        raise TrialTimeout(
            f"command timed out after {timeout} seconds: {' '.join(command)}",
            event_stream,
        ) from exc
    if completed.returncode:
        raise ProcessFailure(command, completed.returncode, completed.stdout, completed.stderr)
    return completed.stdout


def parse_event_stream(stream):
    skill_calls = set()
    tools = set()
    text_parts = []
    event_count = 0
    for line_number, raw_line in enumerate(stream.splitlines(), 1):
        if not raw_line.strip():
            continue
        try:
            event = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            raise MalformedEventError(
                f"malformed JSON event at line {line_number}: {exc}", stream
            ) from exc
        event_count += 1
        if not isinstance(event, dict) or not isinstance(event.get("type"), str):
            raise MalformedEventError(
                f"event at line {line_number} must have a string type", stream
            )
        if event["type"] == "error":
            error = event.get("error")
            if not isinstance(error, dict):
                raise MalformedEventError(
                    f"error event at line {line_number} has no error object", stream
                )
            data = error.get("data") if isinstance(error.get("data"), dict) else {}
            details = [str(error.get("name") or "OpenCode error")]
            if data.get("statusCode") is not None:
                details.append(f"status {data['statusCode']}")
            for key in ("message", "responseBody"):
                value = data.get(key)
                if isinstance(value, str) and value.strip():
                    details.append(" ".join(value.splitlines()))
            raise OpenCodeEventError(": ".join(details), stream)
        if event["type"] not in {"tool_use", "text"}:
            continue
        part = event.get("part")
        if not isinstance(part, dict):
            raise MalformedEventError(
                f"{event['type']} event at line {line_number} has no part object", stream
            )
        if event["type"] == "text":
            text = part.get("text")
            if not isinstance(text, str):
                raise MalformedEventError(
                    f"text event at line {line_number} has non-string text", stream
                )
            text_parts.append(text)
            continue
        tool = part.get("tool")
        if not isinstance(tool, str) or not tool:
            raise MalformedEventError(
                f"tool_use event at line {line_number} has no tool name", stream
            )
        tools.add(tool)
        if tool == "skill":
            state = part.get("state")
            skill_name = state.get("input", {}).get("name") if isinstance(state, dict) else None
            if not isinstance(skill_name, str) or not skill_name:
                raise MalformedEventError(
                    f"skill tool_use event at line {line_number} has no state.input.name",
                    stream,
                )
            skill_calls.add(skill_name)
    if event_count == 0:
        raise MalformedEventError("event stream contains no JSON events", stream)
    return Observation(skill_calls, tools, "".join(text_parts))


def score_trigger(case, observation):
    expected = set(case["expected_skills"])
    forbidden = set(case["forbidden_skills"])
    missing = sorted(expected - observation.skill_calls)
    unexpected = sorted(observation.skill_calls - expected)
    called_forbidden = sorted(observation.skill_calls & forbidden)
    return {
        "passed": not missing and not unexpected,
        "called_skills": sorted(observation.skill_calls),
        "missing_skills": missing,
        "unexpected_skills": unexpected,
        "forbidden_skills_called": called_forbidden,
    }


def score_checks(case, observation):
    required_tools = set(case["required_tools"])
    forbidden_tools = set(case["forbidden_tools"])
    missing_tools = sorted(required_tools - observation.tools)
    present_forbidden_tools = sorted(forbidden_tools & observation.tools)
    missing_patterns = [
        pattern
        for pattern in case["required_text_patterns"]
        if re.search(pattern, observation.text) is None
    ]
    present_forbidden_patterns = [
        pattern
        for pattern in case["forbidden_text_patterns"]
        if re.search(pattern, observation.text) is not None
    ]
    return {
        "outcome_passed": not any(
            (missing_tools, present_forbidden_tools, missing_patterns, present_forbidden_patterns)
        ),
        "called_tools": sorted(observation.tools),
        "missing_required_tools": missing_tools,
        "present_forbidden_tools": present_forbidden_tools,
        "missing_required_text_patterns": missing_patterns,
        "present_forbidden_text_patterns": present_forbidden_patterns,
    }


def score_outcome(case, current, baseline):
    target = case["skill"]
    current_result = score_checks(case, current)
    baseline_result = score_checks(case, baseline)
    current_result["called_skills"] = sorted(current.skill_calls)
    current_result["trigger_passed"] = current.skill_calls == {target}
    baseline_result["called_skills"] = sorted(baseline.skill_calls)
    baseline_result["target_absent"] = target not in baseline.skill_calls

    if baseline_result["outcome_passed"]:
        comparison = "already_passing_baseline"
        improved = True
    elif current_result["outcome_passed"]:
        comparison = "improved_failing_baseline"
        improved = True
    else:
        comparison = "did_not_improve_failing_baseline"
        improved = False
    passed = (
        current_result["trigger_passed"]
        and current_result["outcome_passed"]
        and baseline_result["target_absent"]
        and improved
    )
    return {
        "passed": passed,
        "comparison": comparison,
        "current": current_result,
        "baseline": baseline_result,
    }


def retain_failure_stream(directory, case_id, stream, passed):
    if passed:
        return None
    directory.mkdir(parents=True, exist_ok=True)
    safe_case_id = re.sub(r"[^a-zA-Z0-9_.-]", "_", case_id)
    path = directory / f"{safe_case_id}.ndjson"
    path.write_text(stream, encoding="utf-8")
    return path


def retain_failure_streams(directory, case_id, streams, passed):
    if passed:
        return {}
    paths = {}
    for label, stream in streams.items():
        paths[label] = retain_failure_stream(
            directory, f"{case_id}-{label}", stream, passed=False
        )
    return paths


def aggregate_trials(suite, case_id, trials):
    if len(trials) == 1:
        return trials[0]
    return {
        "suite": suite,
        "id": case_id,
        "passed": all(trial["passed"] for trial in trials),
        "runs": trials,
    }


def preflight(executable, environment, expected_paths, timeout, expected_instruction):
    config_output = run_process(
        [executable, "debug", "config"], environment, timeout
    )
    skill_output = run_process(
        [executable, "debug", "skill"], environment, timeout
    )
    return validate_preflight(
        config_output, skill_output, expected_paths, expected_instruction
    )


def safe_project_path(root, relative_path):
    path = Path(relative_path)
    if path.is_absolute() or ".." in path.parts:
        raise EvaluationError(f"project file path {relative_path!r} must stay relative")
    return root / path


def write_project_files(root, files):
    for relative_path, content in files.items():
        path = safe_project_path(root, relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def git_command(root, *arguments):
    return run_process(
        ["git", "-c", "user.name=Skill Evaluation", "-c", "user.email=eval@example.invalid", *arguments],
        os.environ.copy(),
        30,
        cwd=root,
    )


def prepare_project(root, project=None):
    if not project:
        return
    write_project_files(root, project.get("files", {}))
    git = project.get("git")
    if git is None:
        return
    git_command(root, "init")
    git_command(root, "checkout", "-b", git["base_branch"])
    git_command(root, "add", ".")
    git_command(root, "commit", "-m", "Fixture base")
    git_command(root, "switch", "-c", git["branch"])
    write_project_files(root, git["changes"])
    git_command(root, "add", ".")
    git_command(root, "commit", "-m", "Fixture change")


def run_trial(executable, prompt, environment, model, timeout, project=None):
    with tempfile.TemporaryDirectory(prefix="opencode-skill-project-") as directory:
        prepare_project(Path(directory), project)
        command = [
            executable,
            "run",
            "--format",
            "json",
            "--dir",
            directory,
        ]
        if model:
            command.extend(["--model", model])
        command.append(prompt)
        stream = run_process(command, environment, timeout)
    return parse_event_stream(stream), stream


def evaluate_trigger_case(case, run_number, executable, environment, model, timeout):
    observation, stream = run_trial(
        executable, case["prompt"], environment, model, timeout, case.get("project")
    )
    result = score_trigger(case, observation)
    return {"suite": "trigger", "id": case["id"], "run": run_number, **result}, stream


def evaluate_outcome_case(
    case,
    run_number,
    executable,
    current_environment,
    baseline_environment,
    model,
    timeout,
):
    streams = {}
    errors = []
    current = None
    baseline = None
    try:
        current, streams["current"] = run_trial(
            executable,
            case["prompt"],
            current_environment,
            model,
            timeout,
            case.get("project"),
        )
    except EvaluationError as exc:
        streams["current"] = getattr(exc, "event_stream", "")
        errors.append(f"current trial failed: {exc}")
    try:
        baseline, streams["baseline"] = run_trial(
            executable,
            case["prompt"],
            baseline_environment,
            model,
            timeout,
            case.get("project"),
        )
    except EvaluationError as exc:
        streams["baseline"] = getattr(exc, "event_stream", "")
        errors.append(f"baseline trial failed: {exc}")
    if errors:
        raise LabeledTrialError("; ".join(errors), streams)
    result = score_outcome(case, current, baseline)
    return (
        {"suite": "outcome", "id": case["id"], "run": run_number, **result},
        streams,
    )


def locate_opencode():
    executable = shutil.which("opencode")
    if executable is None:
        raise EvaluationError("opencode is not available on PATH")
    return executable


def main(arguments=None):
    args = parse_arguments(arguments)
    fixtures_path = TRIGGER_CASES_PATH if args.suite == "trigger" else OUTCOME_CASES_PATH
    try:
        fixtures = load_json(fixtures_path)
        cases = select_cases(fixtures["cases"], args.case, args.all)
        manifest = load_json(MANIFEST_PATH)
        executable = locate_opencode()
        failures = 0
        already_passing = 0
        result_count = 0
        transcript_root = Path(tempfile.mkdtemp(prefix="opencode-skill-failures-"))
        with tempfile.TemporaryDirectory(prefix="opencode-skill-xdg-") as current_xdg:
            _, current_paths, current_instruction = write_isolated_config(
                Path(current_xdg), REPO_ROOT, manifest
            )
            current_environment = build_environment(Path(current_xdg))
            preflight(
                executable,
                current_environment,
                current_paths,
                args.timeout,
                current_instruction,
            )

            for case in cases:
                baseline_context = None
                baseline_environment = None
                try:
                    if args.suite == "outcome":
                        baseline_context = tempfile.TemporaryDirectory(
                            prefix="opencode-skill-baseline-xdg-"
                        )
                        baseline_xdg = Path(baseline_context.name)
                        _, baseline_paths, baseline_instruction = write_isolated_config(
                            baseline_xdg,
                            REPO_ROOT,
                            manifest,
                            omitted_skill=case["skill"],
                        )
                        baseline_environment = build_environment(baseline_xdg)
                        preflight(
                            executable,
                            baseline_environment,
                            baseline_paths,
                            args.timeout,
                            baseline_instruction,
                        )
                    trials = []
                    for run_number in range(1, args.runs + 1):
                        streams = {}
                        try:
                            if args.suite == "trigger":
                                result, stream = evaluate_trigger_case(
                                    case,
                                    run_number,
                                    executable,
                                    current_environment,
                                    args.model,
                                    args.timeout,
                                )
                                streams = {"current": stream}
                            else:
                                result, streams = evaluate_outcome_case(
                                    case,
                                    run_number,
                                    executable,
                                    current_environment,
                                    baseline_environment,
                                    args.model,
                                    args.timeout,
                                )
                        except ProcessFailure as exc:
                            streams = {"current": exc.event_stream}
                            result = {
                                "suite": args.suite,
                                "id": case["id"],
                                "run": run_number,
                                "passed": False,
                                "error": str(exc),
                            }
                        except LabeledTrialError as exc:
                            streams = exc.event_streams
                            result = {
                                "suite": args.suite,
                                "id": case["id"],
                                "run": run_number,
                                "passed": False,
                                "error": str(exc),
                            }
                        except EvaluationError as exc:
                            streams = {"current": getattr(exc, "event_stream", "")}
                            result = {
                                "suite": args.suite,
                                "id": case["id"],
                                "run": run_number,
                                "passed": False,
                                "error": str(exc),
                            }
                        transcripts = retain_failure_streams(
                            transcript_root,
                            f"{case['id']}-run-{run_number}",
                            streams,
                            result["passed"],
                        )
                        if transcripts:
                            result["failure_event_streams"] = {
                                label: str(path) for label, path in transcripts.items()
                            }
                        if result.get("comparison") == "already_passing_baseline":
                            already_passing += 1
                        trials.append(result)
                    case_result = aggregate_trials(args.suite, case["id"], trials)
                    failures += not case_result["passed"]
                    result_count += 1
                    print(json.dumps(case_result, sort_keys=True))
                finally:
                    if baseline_context is not None:
                        baseline_context.cleanup()
        if failures == 0:
            transcript_root.rmdir()
        summary = {
            "suite": args.suite,
            "results": result_count,
            "passed": result_count - failures,
            "failed": failures,
            "already_passing_baselines": already_passing,
        }
        print(json.dumps({"summary": summary}, sort_keys=True))
        return 1 if failures else 0
    except EvaluationError as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
