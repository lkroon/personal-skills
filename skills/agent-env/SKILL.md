---
name: agent-env
description: Run this repository's linting, tests, and coverage gate in a disposable Docker environment dedicated to this checkout. Use whenever you need to validate a change in an application whose tests run in Docker rather than on the host — a Pyramid application generated from template-pyramid-app, or any repository whose AGENTS.md points here. Triggers on "run the tests", "check my work", "does this lint", "verify the change", "did I break anything", pytest, ruff, mypy, or coverage in such a repository.
---

# Checking your work with `agent-env`

`agent-env` is a trusted host-side launcher. You edit the checkout on the host; it
builds, starts, and runs the checks in a container dedicated to **this** checkout,
so your environment can never collide with the developer's own stack.

```bash
agent-env doctor   .   # validate the repository and host tooling; run this first
agent-env prepare  .   # build the image, start services, install locked deps
agent-env check    .   # run the full quality gates
agent-env exec     . -- pytest tests/test_module.py::test_name  # targeted feedback
agent-env audit    .   # report where build credentials survive
agent-env ls            # list prepared environments and their use
agent-env down     .   # remove this checkout's containers and volumes
```

Replace `.` with the repository path if you are not in it.

## The loop

1. **`doctor`** once at the start. It prints what it derived and whether the host
   is usable. If it fails, fix that before anything else — do not work around it.
2. **`prepare`** once. This is the slow step: it builds the image and installs
   locked dependencies.
3. **Edit, then `check`.** Repeat. The checkout is mounted into the container,
   so an edit is checked without a rebuild. A full check can take about a minute
   on a small application and about 8 minutes on a large one such as
   `pyramid-app-metis`; allow at least 15 minutes.
4. **`prepare` again** after changing the dependency manifest or lock file, the
   `Dockerfile`, or a Compose file. `check` warns when it detects this.
5. Keep the environment warm for the duration of the work. Run **`down` only
   when the feature or fix is finished, or when the user asks**, not after each
   `check`.

Do not interrupt `check`, and do not pipe it through `tail` or `head`: its exit
code is the result and it is easy to discard. Only one `check` or targeted `exec`
may run for a project at a time; a concurrent invocation refuses with a message.
If an older launcher was killed before it could clean up, the next invocation
will reclaim its stale lock and clean up its in-container process before running.

Do not invent your own `docker` or `docker compose` invocation, and do not run
`pytest`, `ruff`, or `uv` on the host. The host has neither the dependencies nor
the database, and a hand-built Compose command will collide with the developer's
stack.

`.coverage`, `.pytest_cache/`, and `.ruff_cache/` in the checkout are written by
the container through the source mount. They are not evidence that tools ran on
the host.

## What it runs, and where that comes from

Most repositories commit no configuration. `agent-env` derives what it needs from
files the application already has to keep correct:

| What | Derived from |
| --- | --- |
| The container workspace | the last `WORKDIR` in the `Dockerfile` |
| Which Compose files to layer | the `docker-compose*.yml` files present |
| The service names | the Compose `services` |
| The gates | the reusable workflow the repository's CI calls |

`agent-env doctor` prints every derived value and the file it came from. When a
value looks wrong, that list tells you which file to look at.

A repository that genuinely diverges can commit `.agent/agent-env.toml` to
declare its own values, and that file then wins over derivation. Most should not
need one — check `doctor` output before assuming a repository does.

## What a passing check does and does not mean

`check` runs the full gates that fail the authoritative reusable CI workflow:
Ruff, the full pytest suite, the coverage threshold, and mypy where the
repository enables it. Gates run under `set -euo pipefail` and stop at the first
failure. If pytest fails, the coverage gate did not run; report coverage as
**unknown**, never as passing. A coverage table in the output may come from the
application's own `pytest-cov` configuration and is not the coverage-gate result.

The default check timeout is 15 minutes. The command is **not** a guarantee that
CI passes. CI builds from a clean checkout and lints with its own Ruff build.
Trusted CI and human diff review remain authoritative.

Report which gates ran, which did not, the exit code, and the full-log path. Do
not claim CI parity.

`exec` runs an operator-supplied command in the prepared application container;
it is **not the gate** and its result must never be reported as a passing check.
It is deliberately only iteration feedback. Test isolation is per module, not
per test: the schema is dropped and recreated once per test module, with no
per-test rollback, so a test that passes alone can fail in suite order. A green
targeted run must be followed by a full `check` before reporting a fix.

## When something fails

- **`agent-env: command not found`** — the launcher is not installed on this
  host. Report that and stop; do not fall back to running Docker yourself.
- **`doctor` reports `PIP_ACCESS_TOKEN` missing** — the image build needs it for
  the private package index. **Report that and stop.** Do not attempt an install
  without it, and do not go looking for a replacement value anywhere on the host.
- **`docker compose` is too old** — 2.24 or newer is required. Older Compose
  does not reject the `!reset` tag, it merges it wrongly, which would silently
  put your environment on the developer's containers. Report the version and
  stop.
- **A refusal naming missing evidence** (`no Dockerfile`, `no lock file`, or
  `no application service`) — this is one of the older pip-based applications
  that this launcher cannot drive. Report the refusal and report your change as
  **unverified**. Do not assemble an environment or work around the refusal.
- **Another check is running** — do not bypass the refusal or start Docker
  manually. Wait for the owner to finish, or use the stated cleanup guidance.
- **`check` fails** — that is the tool working. Read the summary and full log,
  fix the code, and run `check` again. If pytest failed, do not describe the
  coverage gate as having passed.

## Scope

- The environment is disposable and dedicated to this checkout. Use only its
  database. Never point tests, scripts, or a connection string at a shared,
  staging, or production database.
- Never deploy, publish an image, push a tag, or trigger a release.
- Changing the dependency manifest or lock file changes what the trusted build
  installs. Say so explicitly in your report and run `prepare` before `check`.

## Installing the launcher

If `agent-env` is missing, the developer installs it once per host:

```bash
uv tool install git+https://github.com/lkroon/agentic-dev-tools
```

Suggest that and stop. Do not install it yourself unless you were asked to.

> **Maintenance:** This skill is distributed in two repositories. Keep both
> `SKILL.md` copies synchronized whenever either copy changes.
