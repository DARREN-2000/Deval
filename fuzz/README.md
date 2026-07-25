# Fuzzing Deval

Deval parses input it did not author. A `.deval.yml` arrives from whatever
repository is being scanned, and so do that repository's Dockerfiles and
suppression files. A crash in any of those paths turns a quality gate into a
broken CI step, so the parser surface is fuzzed, not just unit-tested.

This directory is also why Deval can enforce `DV4012 require-fuzz-targets` with
a straight face. That rule fires on repositories that parse untrusted input.
Deval is one of them.

## Two harnesses, on purpose

| | `run_fuzz.py` | `fuzz_atheris.py` |
|---|---|---|
| Dependencies | **None** | `atheris` |
| Strategy | Seeded random generation | Coverage-guided mutation |
| Runs in CI | Every push | On demand / nightly |
| Reproducible | Yes, via `--seed` | Via crash corpus |

Deval guarantees **zero required runtime dependencies**, and CI verifies it. A
fuzzer that needed a wheel could not run in the default matrix, so the baseline
fuzzer is hand-rolled. Atheris is the deeper campaign: it instruments bytecode
and mutates toward unexplored branches, finding edges that blind generation
reaches only by luck. Both share the same invariants, defined once in
`run_fuzz.TARGETS`, so the two can never drift apart.

## Running it

```bash
# Baseline: 2000 cases per target, nothing to install
python3 fuzz/run_fuzz.py

# Longer campaign
python3 fuzz/run_fuzz.py -n 50000

# Reproduce a reported crash exactly
python3 fuzz/run_fuzz.py --target mini_yaml --seed 41337

# Coverage-guided
pip install atheris
python3 fuzz/fuzz_atheris.py -atheris_runs=100000
```

## Targets

| Target | Entry point | Why it is attackable |
|---|---|---|
| `mini_yaml` | `deval.config._mini_yaml` | Indentation-driven recursive descent; runs whenever PyYAML is absent |
| `coerce_scalar` | `deval.config._coerce_scalar` | Decides the type of every config value |
| `dockerfile` | `deval.checks.operations._dockerfile_instructions` | Joins continuations and strips comments on arbitrary text |

## What counts as a crash

`ValueError`, `TypeError` and `KeyError` are contract: callers handle them.
Anything else escaping a parser is a bug. A `RecursionError` on deeply nested
YAML or an `IndexError` on a truncated continuation would take down a scan.

The harnesses assert **invariants**, not merely the absence of exceptions:

- `_mini_yaml` must always return a `dict`
- `_coerce_scalar` must never return a `dict`, and may only return a list for
  genuinely bracketed input
- `_dockerfile_instructions` must always return upper-cased `(instruction, argument)` pairs
- `_serves_traffic` must return a real bool

A parser that silently returns `None` fails the run. That matters more than
exception-hunting: a wrong-but-quiet parse produces a wrong score, which is
harder to notice than a crash.

## When a crash is found

Crashing inputs are written to `fuzz/crashes/` and the replay command is
printed. Add the input as a regression case in `tests/test_fuzz.py` **before**
fixing the parser, so the bug cannot come back quietly.

One caveat worth stating plainly: the invariant may be wrong rather than the
parser. The first run of this fuzzer flagged `_coerce_scalar` for returning a
list — which turned out to be correct YAML inline-list behaviour, and the
assertion was the thing that needed fixing. Check which side is wrong before
changing production code.
