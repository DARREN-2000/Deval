## What this changes

<!-- One or two sentences. What problem does this solve? -->

## Why

<!-- Link an issue, or explain the motivation. -->

## Checklist

- [ ] `pytest -q` passes (or `python run_tests.py` if pytest is unavailable)
- [ ] `ruff check .` is clean
- [ ] `deval scan .` still scores 100/100 — Deval must pass its own standard
- [ ] `CHANGELOG.md` updated under `## [Unreleased]`

## If this adds or changes a rule

- [ ] The rule has a stable `DV####` code
- [ ] `deval explain <rule>` returns Problem / Why / Example / Fix / References
- [ ] It is assigned to an Engineering Dimension
- [ ] It is inert on repositories where it does not apply
- [ ] A test covers both the passing and the failing case
