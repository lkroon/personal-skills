#!/usr/bin/env python3
"""Generate or verify the machine-local OpenCode configuration.

`opencode-skills.json` is the only hand-edited inventory. The `skills.paths`
list and the `permission.skill` allowlist are derived from it here, so the two
cannot drift apart. Everything else is copied from `tools/opencode-base.json`
with `{{REPO}}` and `{{HOME}}` substituted.
"""

import argparse
import json
import os
import sys
from collections import OrderedDict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT / "opencode-skills.json"
BASE_CONFIG_PATH = REPO_ROOT / "tools/opencode-base.json"
INSTRUCTIONS_RELATIVE = "instructions/opencode-development.md"
DERIVED_SECTIONS = ("instructions", "skills.paths", "permission.skill")


class ConfigError(Exception):
    """A configuration could not be generated or verified."""


class ResolvedOutputError(ConfigError):
    """`opencode debug skill` produced output that could not be interpreted."""


def default_config_path():
    config_home = os.environ.get("XDG_CONFIG_HOME")
    root = Path(config_home) if config_home else Path.home() / ".config"
    return root / "opencode/opencode.jsonc"


def load_json(path):
    def reject_duplicate_keys(pairs):
        result = OrderedDict()
        for key, value in pairs:
            if key in result:
                raise ConfigError(f"{path}: duplicate key {key!r}")
            result[key] = value
        return result

    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ConfigError(f"{path}: {exc}") from exc
    try:
        return json.loads(text, object_pairs_hook=reject_duplicate_keys)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"{path}: {exc}") from exc


def load_manifest(repository=None):
    """Return an ordered name -> absolute skill directory mapping."""
    repository = REPO_ROOT if repository is None else Path(repository).resolve()
    manifest = load_json(repository / "opencode-skills.json")
    if not isinstance(manifest, dict) or set(manifest) != {"skills"}:
        raise ConfigError("opencode-skills.json: root must contain only a skills mapping")
    skills = manifest["skills"]
    if not isinstance(skills, dict) or not skills:
        raise ConfigError("opencode-skills.json: skills must be a nonempty mapping")

    resolved = OrderedDict()
    for name, relative_path in skills.items():
        if not isinstance(relative_path, str) or not relative_path:
            raise ConfigError(f"opencode-skills.json: path for {name!r} must be a nonempty string")
        if Path(relative_path).is_absolute():
            raise ConfigError(f"opencode-skills.json: path for {name!r} must be relative")
        directory = (repository / relative_path).resolve()
        try:
            directory.relative_to(repository)
        except ValueError:
            raise ConfigError(
                f"opencode-skills.json: path for {name!r} escapes the repository"
            ) from None
        if not (directory / "SKILL.md").is_file():
            raise ConfigError(f"opencode-skills.json: {name!r} has no SKILL.md at {directory}")
        resolved[name] = directory
    return resolved


def substitute(value, replacements):
    if isinstance(value, str):
        for placeholder, replacement in replacements.items():
            value = value.replace(placeholder, replacement)
        return value
    if isinstance(value, dict):
        return OrderedDict(
            (substitute(key, replacements), substitute(item, replacements))
            for key, item in value.items()
        )
    if isinstance(value, list):
        return [substitute(item, replacements) for item in value]
    return value


def derived_sections(skills, repository=None):
    """Return the three sections that must follow the manifest."""
    repository = REPO_ROOT if repository is None else Path(repository).resolve()
    permission = OrderedDict([("*", "deny")])
    for name in skills:
        permission[name] = "allow"
    return OrderedDict(
        [
            ("instructions", [str(repository / INSTRUCTIONS_RELATIVE)]),
            ("skills.paths", [str(path) for path in skills.values()]),
            ("permission.skill", permission),
        ]
    )


def build_config(repository=None, home=None, base_path=None):
    repository = REPO_ROOT if repository is None else Path(repository).resolve()
    home = Path.home() if home is None else Path(home)
    base = load_json(BASE_CONFIG_PATH if base_path is None else Path(base_path))
    if not isinstance(base, dict):
        raise ConfigError("opencode-base.json: root must be an object")

    config = substitute(base, {"{{REPO}}": str(repository), "{{HOME}}": str(home)})
    skills = load_manifest(repository)
    sections = derived_sections(skills, repository)

    config["instructions"] = sections["instructions"]
    config["skills"] = OrderedDict([("paths", sections["skills.paths"])])
    permission = config.setdefault("permission", OrderedDict())
    if not isinstance(permission, dict):
        raise ConfigError("opencode-base.json: permission must be an object")
    permission["skill"] = sections["permission.skill"]
    return config


def read_section(config, dotted):
    node = config
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def verify(path, repository=None):
    """Return a list of drift descriptions between `path` and the manifest."""
    repository = REPO_ROOT if repository is None else Path(repository).resolve()
    config = load_json(path)
    if not isinstance(config, dict):
        return [f"{path}: root must be an object"]

    skills = load_manifest(repository)
    expected = derived_sections(skills, repository)
    drift = []
    for dotted, want in expected.items():
        got = read_section(config, dotted)
        if got == want:
            continue
        if got is None:
            drift.append(f"{dotted}: missing")
        elif isinstance(want, list) and isinstance(got, list):
            missing = [item for item in want if item not in got]
            extra = [item for item in got if item not in want]
            detail = []
            if missing:
                detail.append(f"missing {missing}")
            if extra:
                detail.append(f"unexpected {extra}")
            drift.append(f"{dotted}: " + ("; ".join(detail) or "wrong order"))
        elif isinstance(want, dict) and isinstance(got, dict):
            missing = sorted(set(want) - set(got))
            extra = sorted(set(got) - set(want))
            changed = sorted(k for k in set(want) & set(got) if want[k] != got[k])
            detail = []
            if missing:
                detail.append(f"missing {missing}")
            if extra:
                detail.append(f"unexpected {extra}")
            if changed:
                detail.append(f"changed {changed}")
            drift.append(f"{dotted}: " + "; ".join(detail))
        else:
            drift.append(f"{dotted}: expected {want!r}, found {got!r}")
    return drift


def check_resolved(path, repository=None):
    """Return manifest skills that OpenCode did not resolve, plus any extras.

    `path` holds the JSON emitted by `opencode debug skill`.
    """
    repository = REPO_ROOT if repository is None else Path(repository).resolve()
    try:
        document = load_json(Path(path))
    except ConfigError as exc:
        raise ResolvedOutputError(str(exc)) from None
    entries = document if isinstance(document, list) else document.get("skills", [])
    if not isinstance(entries, list):
        raise ResolvedOutputError("'opencode debug skill' output is not a list of skills")
    resolved = {
        entry.get("name") for entry in entries if isinstance(entry, dict) and entry.get("name")
    }
    manifest = set(load_manifest(repository))
    return sorted(manifest - resolved), sorted(resolved - manifest)


def render(config):
    return json.dumps(config, indent=2) + "\n"


def write_config(config, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    backup = None
    if path.exists():
        backup = path.with_suffix(path.suffix + ".backup")
        backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    path.write_text(render(config), encoding="utf-8")
    return backup


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--write",
        nargs="?",
        const="",
        metavar="PATH",
        help="install the generated configuration (default: the OpenCode config path)",
    )
    parser.add_argument(
        "--verify",
        nargs="?",
        const="",
        metavar="PATH",
        help="check that a configuration's derived sections match the manifest",
    )
    parser.add_argument(
        "--check-resolved",
        metavar="PATH",
        help="compare 'opencode debug skill' JSON output against the manifest",
    )
    parser.add_argument(
        "--repository",
        default=None,
        help="path to the personal-skills checkout (default: this repository)",
    )
    args = parser.parse_args(argv)

    if args.write is not None and args.verify is not None:
        parser.error("--write and --verify are mutually exclusive")

    try:
        if args.check_resolved is not None:
            try:
                missing, extra = check_resolved(args.check_resolved, args.repository)
            except ResolvedOutputError:
                print(
                    "note: 'opencode debug skill' gave no readable output; "
                    "skipping skill verification"
                )
                return 0
            if missing:
                print(
                    f"warning: OpenCode did not resolve {len(missing)} manifest "
                    f"skill(s): {', '.join(missing)}",
                    file=sys.stderr,
                )
                print(
                    "         Restart OpenCode, then run 'opencode debug skill' to inspect.",
                    file=sys.stderr,
                )
                return 1
            total = len(load_manifest(args.repository))
            note = f" (plus built-in: {', '.join(extra)})" if extra else ""
            print(f"verified: OpenCode resolves all {total} manifest skills{note}")
            return 0

        if args.verify is not None:
            target = Path(args.verify) if args.verify else default_config_path()
            if not target.is_file():
                print(f"no configuration at {target}", file=sys.stderr)
                return 1
            drift = verify(target, args.repository)
            if drift:
                print(f"{target} has drifted from opencode-skills.json:", file=sys.stderr)
                for item in drift:
                    print(f"  {item}", file=sys.stderr)
                print("regenerate with: tools/generate_opencode_config.py --write", file=sys.stderr)
                return 1
            skills = load_manifest(args.repository)
            print(f"{target} matches the manifest ({len(skills)} skills)")
            return 0

        config = build_config(args.repository)
        if args.write is None:
            sys.stdout.write(render(config))
            return 0

        target = Path(args.write) if args.write else default_config_path()
        backup = write_config(config, target)
        count = len(config["skills"]["paths"])
        if backup is not None:
            print(f"backed up previous configuration to {backup}")
        print(f"wrote {target} with {count} skills")
        return 0
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
