# 2. Deterministic scoring, no model in the loop

- **Status:** Accepted
- **Date:** 2025-07

## Context

Every repository-quality tool now has the option of asking a language model to
judge code. It is an appealing shortcut: a model can assess things a static
rule cannot, like whether documentation is genuinely useful.

Deval's output is used as a **CI gate**. A build passes or fails on it.

## Decision

No model participates in scanning or scoring. Deval is deterministic: the same
repository produces byte-identical findings and an identical score on every
run, on every machine, at every point in the future.

LLM-as-judge is declined, not deferred.

## Consequences

**Good:**

- A failing gate is arguable. A developer can read the rule, run
  `deval explain`, and either fix the finding or make a case that the rule is
  wrong. Neither is possible against a model's opinion.
- Scores are comparable across time. A repository scoring 85 last quarter and
  85 today genuinely did not change.
- No API key, no network call, no per-scan cost, no data leaving the machine.
  This is what allows the browser demo to run entirely client-side.
- Findings are reproducible, so a regression in Deval itself is detectable.

**Bad, and accepted:**

- Deval cannot assess whether documentation is *good*, only whether it exists
  and covers the public API. `documented-public-api` counts docstrings; it
  cannot tell a real one from a restatement of the function name.
- Some genuinely valuable signals are out of reach.

That trade is deliberate. A gate that is sometimes wrong in a way nobody can
interrogate is worse than a narrower gate that is always explicable.

## Note on the browser demo

The demo calls `scan(run_integrations=False, load_plugins=False)`. Visitor
zips are untrusted input; executing plugin code out of an uploaded archive
would be arbitrary code execution in the visitor's browser. Also a deliberate
decision, for the same reason as this one: the tool must not become the risk.
