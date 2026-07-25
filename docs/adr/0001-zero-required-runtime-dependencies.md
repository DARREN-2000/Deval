# 1. Zero required runtime dependencies

- **Status:** Accepted
- **Date:** 2025-07

## Context

Deval is a quality gate. It runs in CI, inside other people's pipelines, and
inside a browser via Pyodide. Every dependency it declares becomes a
dependency of every repository that installs it, and a potential source of
install failures, version conflicts, and supply-chain exposure in exactly the
places a security-adjacent tool should not add risk.

The obvious dependency was PyYAML, for parsing `.deval.yml`.

## Decision

Deval declares **no required runtime dependencies**. PyYAML is an optional
extra (`deval[yaml]`); when it is absent, a small internal parser in
`config.py` handles the config subset Deval actually uses.

## Consequences

**Good:**

- `pip install deval` cannot fail on a transitive conflict.
- It works unmodified in Pyodide, which is what makes the browser demo
  possible at all.
- The supply-chain rules Deval enforces on others, it satisfies trivially.

**Bad, and accepted:**

- We maintain a YAML parser. That is code we would rather not own, and it
  handles a deliberately restricted subset — not a general YAML
  implementation.
- **That parser processes untrusted input**: `.deval.yml` files belonging to
  whatever repository is being scanned. A crash there turns a quality gate
  into a broken build.

The second point is the reason `fuzz/` exists. `_mini_yaml` and
`_coerce_scalar` are fuzzed on every push, and the CI fuzz job is a direct
consequence of this decision. See [ADR 3](0003-fuzz-the-parser-surface.md).
