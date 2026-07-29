#!/usr/bin/env python3
"""Validate OpenCode skill metadata and evaluation fixtures."""

import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT / "opencode-skills.json"
TRIGGER_CASES_PATH = REPO_ROOT / "tests/fixtures/trigger-cases.json"
OUTCOME_CASES_PATH = REPO_ROOT / "tests/fixtures/outcome-cases.json"
NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ALLOWED_FRONTMATTER_FIELDS = {
    "name",
    "description",
    "license",
    "compatibility",
    "metadata",
}
CANONICAL_SKILLS = {
    "formal-design",
    "formal-planning",
    "hard-debugging",
    "code-review",
    "skill-development",
}
REFERENCE_DEFINITION_PATTERN = re.compile(
    r"^ {0,3}\[([^\]\n]+)\]:[ \t]*(.*)$", re.MULTILINE
)
REFERENCE_LINK_PATTERN = re.compile(r"\[([^\]\n]+)\](?:\[([^\]\n]*)\])?")


def single_line(value):
    return " ".join(str(value).splitlines())


def diagnostic_repr(value):
    return repr(single_line(value))


def load_json(path, errors):
    def reject_duplicate_keys(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate key {diagnostic_repr(key)}")
            result[key] = value
        return result

    try:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle, object_pairs_hook=reject_duplicate_keys)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        errors.append(f"{path.relative_to(REPO_ROOT)}: {single_line(exc)}")
        return None


def valid_name(value):
    return (
        isinstance(value, str)
        and 1 <= len(value) <= 64
        and NAME_PATTERN.fullmatch(value) is not None
    )


def validate_frontmatter(skill_file, expected_name, errors):
    relative_path = skill_file.relative_to(REPO_ROOT)
    try:
        text = skill_file.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        errors.append(f"{relative_path}: {single_line(exc)}")
        return None

    lines = text.splitlines()
    if not lines or lines[0] != "---":
        errors.append(f"{relative_path}: missing opening YAML frontmatter delimiter")
        return text

    try:
        closing_index = lines.index("---", 1)
    except ValueError:
        errors.append(f"{relative_path}: missing closing YAML frontmatter delimiter")
        return text

    try:
        frontmatter = yaml.safe_load("\n".join(lines[1:closing_index]))
    except yaml.YAMLError as exc:
        errors.append(f"{relative_path}: malformed YAML frontmatter: {single_line(exc)}")
        return text

    if not isinstance(frontmatter, dict):
        errors.append(f"{relative_path}: frontmatter must be a mapping")
        return text

    unsupported = sorted(
        (key for key in frontmatter if key not in ALLOWED_FRONTMATTER_FIELDS),
        key=str,
    )
    if unsupported:
        errors.append(
            f"{relative_path}: unsupported frontmatter fields: "
            f"{', '.join(single_line(key) for key in unsupported)}"
        )

    name = frontmatter.get("name")
    if not valid_name(name):
        errors.append(f"{relative_path}: name must match {NAME_PATTERN.pattern} and be 1-64 characters")
    elif name != expected_name:
        errors.append(
            f"{relative_path}: frontmatter name {diagnostic_repr(name)} does not match "
            f"{diagnostic_repr(expected_name)}"
        )

    description = frontmatter.get("description")
    if not isinstance(description, str) or not 1 <= len(description) <= 1024:
        errors.append(f"{relative_path}: description must be a string of 1-1024 characters")

    for field in ("license", "compatibility"):
        if field in frontmatter and not isinstance(frontmatter[field], str):
            errors.append(f"{relative_path}: {field} must be a string")

    if "metadata" in frontmatter:
        metadata = frontmatter["metadata"]
        if not isinstance(metadata, dict) or any(
            not isinstance(key, str) or not isinstance(value, str)
            for key, value in metadata.items()
        ):
            errors.append(f"{relative_path}: metadata must map strings to strings")

    return text


def strip_fenced_code(text):
    visible_lines = []
    fence = None
    for line in text.splitlines(keepends=True):
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
        if fence is None and marker:
            fence = (marker.group(1)[0], len(marker.group(1)))
            visible_lines.append("\n" if line.endswith("\n") else "")
            continue
        if fence is not None:
            closing = re.match(rf"^ {{0,3}}{re.escape(fence[0])}{{{fence[1]},}}[ \t]*$", line.rstrip("\n"))
            if closing:
                fence = None
            visible_lines.append("\n" if line.endswith("\n") else "")
            continue
        visible_lines.append(line)
    return "".join(visible_lines)


def unescape_markdown(value):
    return re.sub(r"\\([!\"#$%&'()*+,\-./:;<=>?@\[\\\]^_`{|}~])", r"\1", value)


def parse_reference_destination(value):
    value = value.lstrip()
    if value.startswith("<"):
        end = value.find(">", 1)
        return None if end == -1 else unescape_markdown(value[1:end])

    depth = 0
    escaped = False
    for index, character in enumerate(value):
        if escaped:
            escaped = False
        elif character == "\\":
            escaped = True
        elif character == "(":
            depth += 1
        elif character == ")":
            if depth == 0:
                return None
            depth -= 1
        elif character.isspace() and depth == 0:
            return unescape_markdown(value[:index])
    return unescape_markdown(value) if value and depth == 0 else None


def parse_inline_destination(text, start):
    cursor = start
    while cursor < len(text) and text[cursor].isspace():
        cursor += 1
    if cursor == len(text):
        return None, start

    if text[cursor] == "<":
        end = cursor + 1
        while end < len(text):
            if text[end] == ">" and text[end - 1] != "\\":
                target = unescape_markdown(text[cursor + 1 : end])
                cursor = end + 1
                break
            end += 1
        else:
            return None, start
    else:
        target_start = cursor
        depth = 0
        escaped = False
        while cursor < len(text):
            character = text[cursor]
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == "(":
                depth += 1
            elif character == ")":
                if depth == 0:
                    return unescape_markdown(text[target_start:cursor]), cursor + 1
                depth -= 1
            elif character.isspace() and depth == 0:
                break
            cursor += 1
        target = unescape_markdown(text[target_start:cursor])

    while cursor < len(text) and text[cursor].isspace():
        cursor += 1
    if cursor < len(text) and text[cursor] in "\"'(":
        opener = text[cursor]
        closer = ")" if opener == "(" else opener
        depth = 1
        cursor += 1
        while cursor < len(text) and depth:
            if text[cursor] == "\\":
                cursor += 2
                continue
            if opener == "(" and text[cursor] == opener:
                depth += 1
            elif text[cursor] == closer:
                depth -= 1
            cursor += 1
        if depth:
            return None, start
        while cursor < len(text) and text[cursor].isspace():
            cursor += 1
    if cursor < len(text) and text[cursor] == ")":
        return target, cursor + 1
    return None, start


def normalize_reference_label(label):
    return " ".join(label.split()).casefold()


def markdown_link_targets(text):
    text = strip_fenced_code(text)
    definitions = {}
    definition_spans = []
    for match in REFERENCE_DEFINITION_PATTERN.finditer(text):
        target = parse_reference_destination(match.group(2))
        if target is not None:
            definitions.setdefault(normalize_reference_label(match.group(1)), target)
        definition_spans.append(match.span())

    without_definitions = list(text)
    for start, end in definition_spans:
        without_definitions[start:end] = " " * (end - start)
    content = "".join(without_definitions)

    targets = []
    cursor = 0
    while True:
        marker = content.find("](", cursor)
        if marker == -1:
            break
        if marker == 0 or content[marker - 1] != "\\":
            target, end = parse_inline_destination(content, marker + 2)
            if target is not None:
                targets.append(target)
                cursor = end
                continue
        cursor = marker + 2

    for match in REFERENCE_LINK_PATTERN.finditer(content):
        if match.end() < len(content) and content[match.end()] == "(":
            continue
        label = match.group(2)
        if label is None or label == "":
            label = match.group(1)
        target = definitions.get(normalize_reference_label(label))
        if target is not None:
            targets.append(target)
    return targets


def validate_links(skill_file, text, errors):
    relative_path = skill_file.relative_to(REPO_ROOT)
    for target in markdown_link_targets(text):
        if not target or target.startswith("#") or target.startswith("//"):
            continue
        try:
            parsed = urlsplit(target)
        except ValueError as exc:
            errors.append(
                f"{relative_path}: invalid Markdown link {diagnostic_repr(target)}: "
                f"{single_line(exc)}"
            )
            continue
        if parsed.scheme or not parsed.path:
            continue
        try:
            linked_path = (skill_file.parent / unquote(parsed.path)).resolve()
        except (OSError, ValueError) as exc:
            errors.append(
                f"{relative_path}: invalid Markdown link path {diagnostic_repr(target)}: "
                f"{single_line(exc)}"
            )
            continue
        if not linked_path.exists():
            errors.append(
                f"{relative_path}: dangling local Markdown link {diagnostic_repr(target)}"
            )


def validate_manifest(errors):
    manifest = load_json(MANIFEST_PATH, errors)
    if manifest is None:
        return {}
    if not isinstance(manifest, dict) or set(manifest) != {"skills"}:
        errors.append("opencode-skills.json: root must contain only a skills mapping")
        return {}
    skills = manifest.get("skills")
    if not isinstance(skills, dict):
        errors.append("opencode-skills.json: skills must be a mapping")
        return {}

    active_skills = {}
    resolved_paths = {}
    for name, raw_path in skills.items():
        if not valid_name(name):
            errors.append(
                f"opencode-skills.json: skill name {diagnostic_repr(name)} must match "
                f"{NAME_PATTERN.pattern} and be 1-64 characters"
            )
        if not isinstance(raw_path, str) or not raw_path:
            errors.append(
                f"opencode-skills.json: path for {diagnostic_repr(name)} must be a nonempty string"
            )
            continue

        manifest_path = Path(raw_path)
        if manifest_path.is_absolute():
            errors.append(
                f"opencode-skills.json: path for {diagnostic_repr(name)} must be relative"
            )
            continue
        try:
            skill_directory = (REPO_ROOT / manifest_path).resolve()
        except (OSError, ValueError) as exc:
            errors.append(
                f"opencode-skills.json: invalid path {diagnostic_repr(raw_path)} for "
                f"{diagnostic_repr(name)}: {single_line(exc)}"
            )
            continue
        try:
            skill_directory.relative_to(REPO_ROOT)
        except ValueError:
            errors.append(
                f"opencode-skills.json: path for {diagnostic_repr(name)} escapes the repository"
            )
            continue

        if skill_directory in resolved_paths:
            errors.append(
                f"opencode-skills.json: duplicate path {diagnostic_repr(raw_path)} for "
                f"{diagnostic_repr(name)} and "
                f"{diagnostic_repr(resolved_paths[skill_directory])}"
            )
        else:
            resolved_paths[skill_directory] = name

        skill_file = skill_directory / "SKILL.md"
        if not skill_file.is_file():
            errors.append(
                f"opencode-skills.json: path for {diagnostic_repr(name)} has no SKILL.md"
            )
            continue
        try:
            skill_file.resolve().relative_to(REPO_ROOT)
        except ValueError:
            errors.append(
                f"opencode-skills.json: SKILL.md for {diagnostic_repr(name)} escapes the repository"
            )
            continue
        if skill_directory.name != name:
            errors.append(
                f"opencode-skills.json: skill {diagnostic_repr(name)} does not match directory "
                f"{diagnostic_repr(skill_directory.name)}"
            )

        text = validate_frontmatter(skill_file, name, errors)
        if text is not None:
            validate_links(skill_file, text, errors)
        active_skills[name] = skill_directory

    return active_skills


def validate_string_list(case_label, field, value, errors, names=False):
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        errors.append(f"{case_label}: {field} must be a list of strings")
        return []
    if names:
        for item in value:
            if not valid_name(item):
                errors.append(
                    f"{case_label}: {field} contains invalid skill name {diagnostic_repr(item)}"
                )
    return value


def validate_project_files(case_label, files, errors, field="project files"):
    if not isinstance(files, dict) or any(
        not isinstance(path, str) or not isinstance(content, str)
        for path, content in files.items()
    ):
        errors.append(f"{case_label}: {field} must map relative paths to strings")
        return
    for path in files:
        candidate = Path(path)
        if not path or candidate.is_absolute() or ".." in candidate.parts:
            errors.append(
                f"{case_label}: project file path {diagnostic_repr(path)} must stay relative"
            )


def validate_project_fixture(case_label, project, errors):
    if not isinstance(project, dict) or not set(project).issubset({"files", "git"}):
        errors.append(f"{case_label}: project must contain only files and optional git")
        return
    if "files" not in project:
        errors.append(f"{case_label}: project must contain files")
    else:
        validate_project_files(case_label, project["files"], errors)
    git = project.get("git")
    if git is None:
        return
    if not isinstance(git, dict) or set(git) != {"base_branch", "branch", "changes"}:
        errors.append(
            f"{case_label}: project git must contain base_branch, branch, and changes"
        )
        return
    for field in ("base_branch", "branch"):
        if not isinstance(git[field], str) or not git[field]:
            errors.append(f"{case_label}: project git {field} must be a nonempty string")
    validate_project_files(case_label, git["changes"], errors, "project git changes")


def validate_trigger_cases(active_names, errors):
    fixtures = load_json(TRIGGER_CASES_PATH, errors)
    if fixtures is None:
        return [], {}
    required_fields = {
        "require_active_skill_references",
        "require_canonical_coverage",
        "require_outcome_coverage",
        "cases",
    }
    if not isinstance(fixtures, dict) or set(fixtures) != required_fields:
        errors.append(
            "tests/fixtures/trigger-cases.json: expected the three coverage gates and cases"
        )
        return [], {}

    gates = {}
    for field in required_fields - {"cases"}:
        value = fixtures.get(field)
        if not isinstance(value, bool):
            errors.append(f"tests/fixtures/trigger-cases.json: {field} must be a boolean")
            value = False
        gates[field] = value

    cases = fixtures.get("cases")
    if not isinstance(cases, list):
        errors.append("tests/fixtures/trigger-cases.json: cases must be a list")
        return [], gates

    seen_ids = set()
    for index, case in enumerate(cases):
        label = f"tests/fixtures/trigger-cases.json: case {index + 1}"
        if not isinstance(case, dict):
            errors.append(f"{label} must be a mapping")
            continue
        expected_fields = {"id", "prompt", "expected_skills", "forbidden_skills"}
        if set(case) not in (expected_fields, expected_fields | {"project"}):
            errors.append(
                f"{label} must contain id, prompt, expected_skills, forbidden_skills, "
                "and optional project"
            )
        if "project" in case:
            validate_project_fixture(label, case["project"], errors)

        case_id = case.get("id")
        if not valid_name(case_id):
            errors.append(f"{label}: id must be a valid name")
        elif case_id in seen_ids:
            errors.append(f"{label}: duplicate id {diagnostic_repr(case_id)}")
        else:
            seen_ids.add(case_id)

        prompt = case.get("prompt")
        if not isinstance(prompt, str) or not prompt:
            errors.append(f"{label}: prompt must be a nonempty string")

        expected = validate_string_list(
            label, "expected_skills", case.get("expected_skills"), errors, names=True
        )
        forbidden = validate_string_list(
            label, "forbidden_skills", case.get("forbidden_skills"), errors, names=True
        )
        overlap = sorted(set(expected) & set(forbidden))
        if overlap:
            errors.append(
                f"{label}: expected and forbidden skills overlap: "
                f"{', '.join(single_line(skill_name) for skill_name in overlap)}"
            )
        if gates.get("require_active_skill_references"):
            for skill_name in sorted(set(expected + forbidden) - active_names):
                errors.append(
                    f"{label}: referenced skill {diagnostic_repr(skill_name)} is not active"
                )

    if gates.get("require_canonical_coverage"):
        for skill_name in sorted(CANONICAL_SKILLS):
            count = sum(
                isinstance(case.get("expected_skills"), list)
                and skill_name in case["expected_skills"]
                for case in cases
                if isinstance(case, dict)
            )
            if count < 3:
                errors.append(
                    "tests/fixtures/trigger-cases.json: "
                    f"{diagnostic_repr(skill_name)} has {count} expected trigger cases; "
                    "at least 3 required"
                )
    return cases, gates


def validate_outcome_cases(active_names, require_coverage, errors):
    fixtures = load_json(OUTCOME_CASES_PATH, errors)
    if fixtures is None:
        return []
    if not isinstance(fixtures, dict) or set(fixtures) != {"cases"}:
        errors.append("tests/fixtures/outcome-cases.json: root must contain only cases")
        return []
    cases = fixtures["cases"]
    if not isinstance(cases, list):
        errors.append("tests/fixtures/outcome-cases.json: cases must be a list")
        return []

    fields = {
        "id",
        "skill",
        "prompt",
        "required_tools",
        "forbidden_tools",
        "required_text_patterns",
        "forbidden_text_patterns",
    }
    seen_ids = set()
    for index, case in enumerate(cases):
        label = f"tests/fixtures/outcome-cases.json: case {index + 1}"
        if not isinstance(case, dict):
            errors.append(f"{label} must be a mapping")
            continue
        if set(case) not in (fields, fields | {"project"}):
            errors.append(
                f"{label}: fields must be {', '.join(sorted(fields))} and optional project"
            )
        if "project" in case:
            validate_project_fixture(label, case["project"], errors)

        case_id = case.get("id")
        if not valid_name(case_id):
            errors.append(f"{label}: id must be a valid name")
        elif case_id in seen_ids:
            errors.append(f"{label}: duplicate id {diagnostic_repr(case_id)}")
        else:
            seen_ids.add(case_id)

        skill_name = case.get("skill")
        if not valid_name(skill_name):
            errors.append(f"{label}: skill must be a valid name")
        elif skill_name not in active_names:
            errors.append(f"{label}: skill {diagnostic_repr(skill_name)} is not active")
        prompt = case.get("prompt")
        if not isinstance(prompt, str) or not prompt:
            errors.append(f"{label}: prompt must be a nonempty string")

        for field in ("required_tools", "forbidden_tools"):
            validate_string_list(label, field, case.get(field), errors)
        for field in ("required_text_patterns", "forbidden_text_patterns"):
            patterns = validate_string_list(label, field, case.get(field), errors)
            for pattern in patterns:
                try:
                    re.compile(pattern)
                except re.error as exc:
                    errors.append(f"{label}: invalid regex in {field}: {single_line(exc)}")

    if require_coverage:
        for skill_name in sorted(CANONICAL_SKILLS):
            count = sum(
                case.get("skill") == skill_name for case in cases if isinstance(case, dict)
            )
            if count < 3:
                errors.append(
                    "tests/fixtures/outcome-cases.json: "
                    f"{diagnostic_repr(skill_name)} has {count} outcome cases; at least 3 required"
                )
    return cases


def main():
    errors = []
    active_skills = validate_manifest(errors)
    trigger_cases, gates = validate_trigger_cases(set(active_skills), errors)
    outcome_cases = validate_outcome_cases(
        set(active_skills), gates.get("require_outcome_coverage", False), errors
    )

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print(
        f"Validated {len(active_skills)} active skills, {len(trigger_cases)} trigger cases, "
        f"and {len(outcome_cases)} outcome cases"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
