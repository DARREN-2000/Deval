"""Testing health: presence, test-to-source ratio, and coverage config."""

from __future__ import annotations

from collections.abc import Iterable

from ..model import Finding
from ..registry import CheckContext, check

_CODE_SUFFIXES = (".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".java", ".rb", ".rs")


def _is_test(relpath: str) -> bool:
    low = relpath.lower()
    name = low.rsplit("/", 1)[-1]
    return (
        "/test" in "/" + low
        or low.startswith("test")
        or name.startswith("test_")
        or name.endswith("_test.py")
        or ".test." in name
        or ".spec." in name
        or "__tests__" in low
    )


@check("tests-present", "testing")
def tests_present(ctx: CheckContext) -> Iterable[Finding]:
    code = ctx.index.by_suffix(*_CODE_SUFFIXES)
    if not code:
        return
    test_files = [rf for rf in code if _is_test(rf.relpath)]
    if test_files:
        yield ctx.ok("tests-present", "testing", f"{len(test_files)} test file(s) found")
    else:
        yield ctx.fail(
            "tests-present",
            "testing",
            "No automated tests found",
            remediation="Add a test suite; even a few tests dramatically reduce risk.",
        )


@check("test-ratio", "testing")
def test_ratio(ctx: CheckContext) -> Iterable[Finding]:
    code = ctx.index.by_suffix(*_CODE_SUFFIXES)
    if not code:
        return
    tests = [rf for rf in code if _is_test(rf.relpath)]
    source = [rf for rf in code if not _is_test(rf.relpath)]
    if not source or not tests:
        return
    ratio = len(tests) / len(source)
    if ratio < 0.15:
        yield ctx.fail(
            "reasonable-test-ratio",
            "testing",
            f"Low test-to-source ratio ({len(tests)} tests / {len(source)} source files)",
            remediation="Increase test coverage of core modules.",
        )
    else:
        yield ctx.ok(
            "reasonable-test-ratio",
            "testing",
            f"Healthy test-to-source ratio ({len(tests)}/{len(source)})",
        )


@check("coverage-config", "testing")
def coverage_config(ctx: CheckContext) -> Iterable[Finding]:
    code = ctx.index.by_suffix(*_CODE_SUFFIXES)
    if not code:
        return
    markers = (
        ".coveragerc",
        "codecov.yml",
        ".codecov.yml",
        "jest.config.js",
        "jest.config.ts",
    )
    if ctx.index.has(*markers):
        yield ctx.ok("coverage-config-present", "testing", "Coverage configuration present")
        return
    for manifest in ("pyproject.toml", "setup.cfg", "tox.ini", "package.json"):
        rf = ctx.index.find(manifest)
        if rf and "coverage" in ctx.index.read_text(rf).lower():
            yield ctx.ok("coverage-config-present", "testing", f"Coverage configured in {manifest}")
            return
    yield ctx.fail(
        "coverage-config-present",
        "testing",
        "No coverage configuration found",
        remediation="Configure coverage measurement and a minimum threshold.",
    )
