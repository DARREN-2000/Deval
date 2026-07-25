"""Repository structure conventions: src/, tests/, docs/, .github/."""

from __future__ import annotations

from collections.abc import Iterable

from ..model import Finding
from ..registry import CheckContext, check

_SOURCE_DIRS = ("src", "lib", "app", "pkg", "internal", "cmd")
_TEST_DIRS = ("tests", "test", "spec", "__tests__")


def _has_top_dir(ctx: CheckContext, names) -> bool:
    top = set(ctx.index.top_level_dirs())
    if top & set(names):
        return True
    return any(ctx.index.find_any_dir(n) for n in names)


@check("conventional-layout", "structure")
def conventional_layout(ctx: CheckContext) -> Iterable[Finding]:
    code = ctx.index.by_suffix(
        ".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".java", ".rs", ".rb"
    )
    if not code:
        return
    if _has_top_dir(ctx, _SOURCE_DIRS):
        yield ctx.ok(
            "conventional-source-layout", "structure", "Source code lives in a conventional directory"
        )
    else:
        yield ctx.fail(
            "conventional-source-layout",
            "structure",
            "No conventional source directory (src/, lib/, app/, ...)",
            remediation="Move source files under a src/ (or equivalent) directory.",
        )


@check("tests-directory", "structure")
def tests_directory(ctx: CheckContext) -> Iterable[Finding]:
    if _has_top_dir(ctx, _TEST_DIRS):
        yield ctx.ok("tests-directory-present", "structure", "Dedicated tests directory present")
    else:
        yield ctx.fail(
            "tests-directory-present",
            "structure",
            "No dedicated tests directory",
            remediation="Create a tests/ directory for automated tests.",
        )
