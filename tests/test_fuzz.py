"""Fuzzing tests for Deval's parser surface.

These run the dependency-free fuzzer from ``fuzz/run_fuzz.py`` with a small
budget on every test run. CI runs the same targets far longer; keeping a short
campaign in the unit suite means a parser regression is caught in seconds.

Seeds are fixed, so these tests are deterministic despite being randomized.
"""

from __future__ import annotations

import sys
from pathlib import Path

_FUZZ_DIR = Path(__file__).resolve().parent.parent / "fuzz"
sys.path.insert(0, str(_FUZZ_DIR))

from run_fuzz import TARGETS, fuzz_target  # noqa: E402

from deval.checks.operations import _dockerfile_instructions, _serves_traffic  # noqa: E402
from deval.config import _coerce_scalar, _mini_yaml  # noqa: E402


def test_fuzz_mini_yaml_finds_no_crashes():
    crashes = fuzz_target("mini_yaml", iterations=400, seed=0)
    assert crashes == [], f"mini_yaml crashed: {crashes[:1]}"


def test_fuzz_coerce_scalar_finds_no_crashes():
    crashes = fuzz_target("coerce_scalar", iterations=400, seed=0)
    assert crashes == [], f"coerce_scalar crashed: {crashes[:1]}"


def test_fuzz_dockerfile_finds_no_crashes():
    crashes = fuzz_target("dockerfile", iterations=400, seed=0)
    assert crashes == [], f"dockerfile crashed: {crashes[:1]}"


def test_fuzz_is_reproducible():
    """Same seed, same verdict — otherwise a reported crash is not triageable."""
    first = fuzz_target("mini_yaml", iterations=50, seed=99)
    second = fuzz_target("mini_yaml", iterations=50, seed=99)
    assert first == second


def test_all_targets_registered():
    assert set(TARGETS) == {"mini_yaml", "coerce_scalar", "dockerfile"}


# --- Regression cases -------------------------------------------------------
# Structural edges worth pinning explicitly. Each would be a real scan failure,
# not a cosmetic bug.


def test_mini_yaml_survives_deep_nesting():
    """Deep indentation must not blow the recursion limit."""
    text = "".join(f"{' ' * (i * 2)}k{i}:\n" for i in range(200))
    assert isinstance(_mini_yaml(text), dict)


def test_mini_yaml_survives_truncated_and_hostile_input():
    for text in (
        "",
        ":",
        "-",
        "a: 'unterminated",
        "\x00\x00",
        "\ufeffkey: value",
        "key:\n\t- tabbed",
        "!!python/object:os.system ['rm -rf /']",
    ):
        assert isinstance(_mini_yaml(text), dict), f"failed on {text!r}"


def test_mini_yaml_never_honours_yaml_tags():
    """The fallback parser must not honour type tags, ever.

    PyYAML's ``load`` is a remote-code-execution primitive. The zero-dependency
    fallback treats a tag as opaque text, and that must stay true.
    """
    result = _mini_yaml("danger: !!python/object/apply:os.system ['echo pwned']")
    assert isinstance(result, dict)
    for value in result.values():
        assert isinstance(value, (str, int, float, bool, list, dict, type(None)))


def test_coerce_scalar_only_builds_lists_from_brackets():
    """Inline lists are intentional; inventing one from plain text is not."""
    assert _coerce_scalar("[a, b]") == ["a", "b"]
    assert _coerce_scalar("plain text, with commas") == "plain text, with commas"
    assert not isinstance(_coerce_scalar("{a: b}"), dict)


def test_dockerfile_parser_survives_dangling_continuation():
    """A file ending mid-continuation must not raise IndexError."""
    instructions = _dockerfile_instructions("FROM x\nRUN echo \\\n")
    assert isinstance(instructions, list)
    assert _serves_traffic(instructions) is False


def test_dockerfile_parser_upper_cases_every_instruction():
    instructions = _dockerfile_instructions("from x\nexpose 80\n")
    assert [name for name, _ in instructions] == ["FROM", "EXPOSE"]
    assert _serves_traffic(instructions) is True
