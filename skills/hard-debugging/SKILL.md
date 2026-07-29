---
name: hard-debugging
description: Invoke hard-debugging with the skill tool before diagnosing a defect that is intermittent, performance-related, distributed or cross-service, high-impact, difficult to verify, or still unresolved after repeated fixes or investigations.
metadata:
  source: personal-skills
  replaces: diagnose, systematic-debugging
---

# Hard Debugging

Use evidence to reduce uncertainty one variable at a time:

`reproduce -> minimize -> form ranked hypotheses -> instrument one variable -> fix root cause -> regression-test`

## Workflow

1. **Reproduce:** establish symptoms, conditions, frequency, and a baseline. If reproduction is unsafe, define the strongest observable proxy.
2. **Minimize:** reduce the failing inputs, components, timing, or environment while preserving the symptom.
3. **Hypothesize:** rank plausible causes by evidence and discriminating power. Record what each predicts.
4. **Instrument:** change or measure one variable, then compare the result with the prediction. Gather evidence before advancing or revising the ranking.
5. **Fix:** address the demonstrated root cause, not a symptom or speculative neighbor.
6. **Regression-test:** when the defect is reliably reproducible, first prove the test fails without the fix, then prove it passes with the fix. Otherwise preserve a deterministic invariant, diagnostic check, or monitoring signal and state the limitation.

## Direct Route

Do not invoke this workflow for an obvious localized defect whose cause is already demonstrated by a traceback, failing assertion, or typo. Fix it directly and run the focused regression check.

## Evidence Gate

At every transition state the observation that justifies it. If evidence contradicts the current hypothesis, return to ranking rather than layering on another fix.
