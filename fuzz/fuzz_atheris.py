#!/usr/bin/env python3
"""Coverage-guided fuzzing entry point (Atheris / libFuzzer).

``run_fuzz.py`` is the always-on, zero-dependency baseline that runs in every
CI job. This module is the deeper campaign: Atheris instruments the bytecode
and mutates inputs toward unexplored branches, which finds edge cases that
blind random generation reaches only by luck.

Atheris is intentionally an optional extra. Deval's zero-dependency guarantee
is verified in CI, so nothing here may ever be imported by the package itself.

Usage::

    pip install atheris
    python3 fuzz/fuzz_atheris.py -atheris_runs=100000
    python3 fuzz/fuzz_atheris.py fuzz/corpus/

OSS-Fuzz builds call ``TestOneInput`` directly.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

try:
    import atheris
except ImportError:  # pragma: no cover - optional developer tool
    sys.stderr.write(
        "atheris is not installed.\n"
        "  pip install atheris          # coverage-guided fuzzing\n"
        "  python3 fuzz/run_fuzz.py     # dependency-free fallback\n"
    )
    raise SystemExit(2) from None

with atheris.instrument_imports():
    from run_fuzz import _ALLOWED, TARGETS


def TestOneInput(data: bytes) -> None:  # noqa: N802 - name fixed by libFuzzer
    """Drive every parser entry point with one fuzzer-provided buffer.

    The invariants live in ``run_fuzz`` so the two harnesses can never drift
    apart: whatever the baseline fuzzer asserts, the coverage-guided one
    asserts too.
    """
    fdp = atheris.FuzzedDataProvider(data)
    text = fdp.ConsumeUnicodeNoSurrogates(len(data))
    if not text:
        return
    for fn in TARGETS.values():
        try:
            fn(text)
        except _ALLOWED:
            continue


def main() -> None:
    """Hand control to the libFuzzer driver."""
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
