# Development Workflow

Default to direct execution for clear, local, reversible work:

`inspect relevant context -> edit -> targeted verification -> report`

- Prefer the smallest correct change. Avoid speculative abstractions and unrelated cleanup.
- Preserve unrelated worktree changes. Every changed line must trace to the request.
- Resolve minor ambiguity from repository evidence. Ask only when ambiguity changes behavior, scope, risk, or compatibility.
- Use brief acceptance criteria or todos for bounded multi-step work without creating a spec or implementation plan.
- Use tests first when they materially improve feedback, especially for regressions and complex behavior; do not impose TDD mechanically.
- Verify with the narrowest command that proves the claim, broadening checks with blast radius.

Load `code-review` before reviewing a diff, branch, or PR or verifying or acting on review feedback.
Load `skill-development` before choosing among a skill, instruction, project docs, command, dedicated agent, deterministic tool, or no change, and before creating, improving, evaluating, consolidating, or retiring skills or the skill system.
A request to check whether a review suggestion is correct is review-feedback verification and requires `code-review`.
A request to classify whether a behavior needs a skill or another mechanism requires `skill-development`, even when the likely classification is no change.
For these explicit workflow requests, load the named skill before inspecting the workspace or answering.
Load `hard-debugging` before diagnosing intermittent, performance-related, distributed or cross-service, high-impact, difficult-to-verify, or repeatedly unresolved defects.
Ranking hypotheses or selecting diagnostic evidence for these defects counts as diagnosing them.
Load `formal-design` before designing an architecture, public contract, security-sensitive workflow, destructive operation, or other materially risky behavior.
Load `formal-planning` before writing an implementation or rollout plan for approved materially risky work.

Load formal workflow skills only when explicitly requested or when risk is material: architecture or public APIs; security, privacy, or authorization; migrations or destructive/irreversible operations; cross-system ambiguity; weak verification; unfamiliar technology with high failure cost; or coordinated multi-stage checkpoints. File count, feature work, and behavior changes alone are not formal-workflow triggers. If material risk appears during direct execution, stop and escalate then.
