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
agent-env check    .   # run the quality gates: Ruff, pytest, coverage
agent-env down     .   # remove this checkout's containers and volumes
```

Replace `.` with the repository path if you are not in it.

## The loop

1. **`doctor`** once at the start. It prints what it derived and whether the host
   is usable. If it fails, fix that before anything else — do not work around it.
2. **`prepare`** once. This is the slow step: it builds the image and installs
   locked dependencies.
3. **Edit, then `check`.** Repeat. The checkout is mounted into the container, so
   an edit is checked without a rebuild.
4. **`prepare` again** only after changing `pyproject.toml`, `uv.lock`, the
   `Dockerfile`, or a Compose file. `check` warns you when it detects this.
5. **`down`** when you are finished, so nothing is left running.

Do not invent your own `docker` or `docker compose` invocation, and do not run
`pytest`, `ruff`, or `uv` on the host. The host has neither the dependencies nor
the database, and a hand-built Compose command will collide with the developer's
stack.

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

`check` runs the gates that fail the authoritative reusable CI workflow: Ruff,
the full pytest suite, a coverage threshold, and mypy where the repository
enables it. It is fast, honest, functional feedback.

It is **not** a guarantee that CI passes. CI builds from a clean checkout and
lints with its own Ruff build. Trusted CI and human diff review remain
authoritative.

Report what you ran and what it returned. Do not claim CI parity.

## When something fails

- **`agent-env: command not found`** — the launcher is not installed on this
  host. Report that and stop; do not fall back to running Docker yourself.
- **`doctor` reports `PIP_ACCESS_TOKEN` missing** — the image build needs it for
  the private package index. **Report that and stop.** Do not attempt an install
  without it, and do not go looking for a replacement value anywhere on the host.
- **`docker compose` is too old** — 2.24 or newer is required. Older Compose does
  not reject the `!reset` tag, it merges it wrongly, which would silently put your
  environment on the developer's containers. Report the version and stop.
- **A refusal naming missing evidence** (`no Dockerfile`, `no uv.lock`, `no
  application service`) — the repository is not one this launcher can drive.
  Report the message; it names exactly what was missing.
- **`check` fails** — that is the tool working. Read the output, fix the code, run
  `check` again.

## Scope

- The environment is disposable and dedicated to this checkout. Use only its
  database. Never point tests, scripts, or a connection string at a shared,
  staging, or production database.
- Never deploy, publish an image, push a tag, or trigger a release.
- Changing `pyproject.toml` or `uv.lock` changes what the trusted build installs.
  Say so explicitly in your report rather than treating it as an ordinary edit.

## Installing the launcher

If `agent-env` is missing, the developer installs it once per host:

```bash
uv tool install git+https://github.com/lkroon/agentic-dev-tools
```

Suggest that and stop. Do not install it yourself unless you were asked to.
