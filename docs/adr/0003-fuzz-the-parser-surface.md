# 3. Fuzz the parser surface, but never fuzz during a scan

- **Status:** Accepted
- **Date:** 2025-07

## Context

Deval parses input it did not author: `.deval.yml`, Dockerfiles, and workflow
files belonging to whatever repository is being scanned. [ADR 1](0001-zero-required-runtime-dependencies.md)
means some of that parsing is done by our own hand-written code rather than a
battle-tested library.

An unhandled exception in that code does not produce a bad score — it produces
a crashed quality gate and a red build the user cannot explain.

Separately, there was a question of whether `deval scan` should *run* a fuzzer
against the repository under test.

## Decision

Two distinct things, deliberately kept apart:

1. **Deval fuzzes itself.** `fuzz/run_fuzz.py` is a dependency-free harness
   over `_mini_yaml`, `_coerce_scalar` and the Dockerfile parser. It runs on
   every push (20,000 cases) and is seeded and replayable.
   `fuzz/fuzz_atheris.py` provides coverage-guided runs where Atheris is
   available, degrading with a clear message where it is not.
2. **Deval never runs a fuzzer during a scan.** It instead *checks that you
   fuzz*: `require-fuzz-targets` (DV4012) and `ci-runs-fuzzing` (DV3005).

## Consequences

**Why not fuzz during a scan:** fuzzing is unbounded work with
nondeterministic output. A scan must terminate quickly and return the same
result twice — see [ADR 2](0002-deterministic-scoring-no-model-in-the-loop.md).
Embedding a fuzzer would violate both properties.

**The harness earns its place.** On its first run it reported a crash in
`_coerce_scalar`. Investigation showed the *invariant was wrong*, not the
parser: `_coerce_scalar` deliberately supports YAML inline-list syntax
(`[a, b]`), so returning a list is correct behaviour. The assertion was
corrected to allow a list only for genuinely bracketed input.

This is recorded because the lesson generalises: when a fuzzer reports a
crash, the invariant is as likely to be wrong as the code, and weakening an
assertion to make a fuzzer quiet is how fuzzing becomes theatre.

**Cost:** the fuzz job adds roughly a minute to CI. Crashing inputs are
uploaded as an artifact on failure and are replayable by seed and iteration.
