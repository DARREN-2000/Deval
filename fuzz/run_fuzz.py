#!/usr/bin/env python3
"""Zero-dependency fuzzer for Deval's parser surface.

Deval parses input it did not author: a ``.deval.yml`` from whatever repository
is being scanned, plus that repository's Dockerfiles and suppression files. A
crash in any of those paths turns a quality gate into a broken CI step.

This fuzzer is hand-rolled on purpose. Deval guarantees **zero required runtime
dependencies** and CI verifies it, so a fuzzer that needed ``hypothesis`` or
``atheris`` could not run in the default matrix. ``fuzz_atheris.py`` provides
coverage-guided fuzzing when that engine is available.

Every run is seeded, so a failure is always reproducible::

    python3 fuzz/run_fuzz.py
    python3 fuzz/run_fuzz.py -n 50000
    python3 fuzz/run_fuzz.py --target mini_yaml --seed 41337
"""

from __future__ import annotations

import argparse
import os
import random
import string
import sys
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from deval.checks.operations import _dockerfile_instructions, _serves_traffic  # noqa: E402
from deval.config import _coerce_scalar, _mini_yaml  # noqa: E402

# Exceptions the callers already handle. Anything else escaping a parser is a
# bug: a RecursionError on nested YAML or an IndexError on a truncated
# continuation would take down a whole scan.
_ALLOWED = (ValueError, TypeError, KeyError)

_CRASH_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crashes")

# Fragments chosen to hit structural edges rather than random noise: comments,
# anchors, tags, tabs, BOMs, unterminated quotes, and Dockerfile continuations.
_FRAGMENTS = (
    "a:", "a: b", "- item", "  ", "\t", "\n", "#comment", "---", "...",
    ": ", "key:", "'", '"', "[", "]", "{", "}", ",", "&anchor", "*ref",
    "!!str", "!!python/object:os.system", "null", "true", "false", "0", "-1",
    "1.5e10", "0x1f", "\ufeff", "\x00", "\\", "\\\n", "FROM x", "RUN echo",
    "EXPOSE 80", "CMD [\"a\"]", "HEALTHCHECK", "ENTRYPOINT", "é", "\U0001f600",
)


def _random_text(rng: random.Random) -> str:
    """Build one hostile input by splicing structural fragments and noise."""
    parts = []
    for _ in range(rng.randint(1, 40)):
        if rng.random() < 0.75:
            parts.append(rng.choice(_FRAGMENTS))
        else:
            length = rng.randint(1, 12)
            alphabet = string.printable if rng.random() < 0.8 else string.punctuation
            parts.append("".join(rng.choice(alphabet) for _ in range(length)))
        if rng.random() < 0.5:
            parts.append("\n" + " " * rng.randint(0, 8))
    return "".join(parts)


def _t_mini_yaml(text: str) -> None:
    """The fallback YAML parser must always return a dict, never raise oddly."""
    result = _mini_yaml(text)
    assert isinstance(result, dict), f"_mini_yaml returned {type(result).__name__}"


def _t_coerce_scalar(text: str) -> None:
    """Scalar coercion must never raise and never invent structure.

    A list is legitimate: ``_coerce_scalar`` supports YAML inline-list syntax,
    so ``"[a, b]"`` correctly becomes ``["a", "b"]``. What must never happen is
    a list appearing for input that was not bracketed, or a dict appearing at
    all — either would mean the scalar path invented structure that the caller
    is not expecting to handle.
    """
    value = _coerce_scalar(text)
    assert not isinstance(value, dict), "scalar coercion produced a dict"
    if isinstance(value, list):
        stripped = text.strip().strip('"').strip("'")
        assert stripped.startswith("[") and stripped.endswith("]"), (
            "scalar coercion produced a list for non-bracketed input"
        )


def _t_dockerfile(text: str) -> None:
    """The Dockerfile parser must return upper-cased pairs and a real bool."""
    instructions = _dockerfile_instructions(text)
    assert isinstance(instructions, list), "instructions must be a list"
    for item in instructions:
        assert len(item) == 2, f"expected (name, arg) pairs, got {item!r}"
        name, _arg = item
        assert name == name.upper(), f"instruction not upper-cased: {name!r}"
    assert _serves_traffic(instructions) in (True, False), "_serves_traffic must return a bool"


TARGETS = {
    "mini_yaml": _t_mini_yaml,
    "coerce_scalar": _t_coerce_scalar,
    "dockerfile": _t_dockerfile,
}


def fuzz_target(name: str, iterations: int = 2000, seed: int = 0) -> list[dict]:
    """Fuzz one target and return a list of crash records (empty means clean).

    The same ``name``, ``iterations`` and ``seed`` always produce the same
    verdict, which is what makes a reported crash triageable.
    """
    fn = TARGETS[name]
    rng = random.Random(seed)
    crashes: list[dict] = []
    for i in range(iterations):
        text = _random_text(rng)
        try:
            fn(text)
        except _ALLOWED:
            continue
        except Exception:
            crashes.append(
                {
                    "target": name,
                    "seed": seed,
                    "iteration": i,
                    "input": text,
                    "traceback": traceback.format_exc(),
                }
            )
    return crashes


def _save_crash(record: dict) -> str:
    """Persist a crashing input so it can be replayed and pinned as a test."""
    os.makedirs(_CRASH_DIR, exist_ok=True)
    path = os.path.join(_CRASH_DIR, f"{record['target']}-{record['seed']}-{record['iteration']}.txt")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(record["input"])
    return path


def main(argv: list[str] | None = None) -> int:
    """Run every selected target and report crashes; exit non-zero on failure."""
    parser = argparse.ArgumentParser(description="Fuzz Deval's parser surface.")
    parser.add_argument("-n", "--iterations", type=int, default=2000, help="cases per target")
    parser.add_argument("--seed", type=int, default=0, help="random seed (for reproduction)")
    parser.add_argument("--target", choices=sorted(TARGETS), help="fuzz a single target")
    args = parser.parse_args(argv)

    names = [args.target] if args.target else sorted(TARGETS)
    total = 0
    all_crashes: list[dict] = []

    for name in names:
        crashes = fuzz_target(name, iterations=args.iterations, seed=args.seed)
        total += args.iterations
        status = "ok  " if not crashes else "FAIL"
        print(f"  {status} {name:<16} {args.iterations} cases, seed {args.seed}")
        all_crashes.extend(crashes)

    print()
    if not all_crashes:
        print(f"No crashes across {total} cases.")
        return 0

    print(f"{len(all_crashes)} crash(es) found:")
    for record in all_crashes[:10]:
        path = _save_crash(record)
        first = record["traceback"].strip().splitlines()[-1]
        print(f"  {record['target']} iteration {record['iteration']}: {first}")
        print(f"    saved: {path}")
        print(f"    replay: python3 fuzz/run_fuzz.py --target {record['target']} --seed {record['seed']}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
