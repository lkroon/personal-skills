---
name: handoff
description: Use when the user explicitly asks to hand off work, compact the current session, or prepare context for another agent or future session.
metadata:
  source: https://github.com/mattpocock/skills
  source-revision: aaf2453f
---

# Handoff

Write a handoff document summarising the current conversation so a fresh agent can continue the work. Save it to the temporary directory of the user's OS, not the current workspace.

Include a "suggested skills" section in the document, which suggests skills that the agent should invoke.

Do not duplicate content already captured in other artifacts (PRDs, plans, ADRs, issues, commits, diffs). Reference them by path or URL instead.

Redact sensitive information, including API keys, passwords, tokens, secrets, and personally identifiable information.

If the user describes what the next session will focus on, tailor the document accordingly.
