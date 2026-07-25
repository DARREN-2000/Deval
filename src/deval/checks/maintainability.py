"""Maintainability: oversized files, TODO/FIXME debt, committed build output."""

from __future__ import annotations

import re
from collections.abc import Iterable

from ..model import Finding
from ..registry import CheckContext, check

_CODE_SUFFIXES = (
    ".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".java", ".rb", ".rs", ".php", ".c",
    ".cpp", ".cs", ".kt", ".swift", ".scala",
)
_HUGE_LINES = 800
_TODO_RE = re.compile(r"(?://|#|/\*|<!--)\s*(TODO|FIXME|XXX|HACK)\b", re.IGNORECASE)
_TODO_BUDGET = 25
_BUILD_ARTIFACT_DIRS = ("dist", "build", "out", ".next", "target", "coverage")
_MINIFIED_RE = re.compile(r"\.(min\.js|min\.css|bundle\.js)$")


@check("no-huge-files", "maintainability")
def no_huge_files(ctx: CheckContext) -> Iterable[Finding]:
    offenders = []
    checked = False
    for rf in ctx.index.by_suffix(*_CODE_SUFFIXES):
        if _MINIFIED_RE.search(rf.name):
            continue
        checked = True
        text = ctx.index.read_text(rf)
        lines = text.count("\n") + 1
        if lines > _HUGE_LINES:
            offenders.append((rf.relpath, lines))
    if offenders:
        for path, lines in sorted(offenders, key=lambda x: -x[1])[:10]:
            yield ctx.fail(
                "no-huge-files",
                "maintainability",
                f"{path} is very large ({lines} lines)",
                path=path,
                remediation=f"Split files larger than {_HUGE_LINES} lines into focused modules.",
            )
    elif checked:
        yield ctx.ok("no-huge-files", "maintainability", "No oversized source files")


@check("bounded-todo-debt", "maintainability")
def bounded_todo_debt(ctx: CheckContext) -> Iterable[Finding]:
    count = 0
    for rf in ctx.index.by_suffix(*_CODE_SUFFIXES):
        for line in ctx.index.read_text(rf).splitlines():
            if _TODO_RE.search(line):
                count += 1
    if count > _TODO_BUDGET:
        yield ctx.fail(
            "bounded-todo-debt",
            "maintainability",
            f"{count} TODO/FIXME markers exceed budget of {_TODO_BUDGET}",
            remediation="Track TODOs as issues and pay down the backlog.",
        )
    else:
        yield ctx.ok(
            "bounded-todo-debt", "maintainability", f"TODO/FIXME debt under control ({count})"
        )


@check("no-committed-build-artifacts", "maintainability")
def no_committed_build_artifacts(ctx: CheckContext) -> Iterable[Finding]:
    top = set(ctx.index.top_level_dirs())
    offenders = sorted(top & set(_BUILD_ARTIFACT_DIRS))
    minified = [rf.relpath for rf in ctx.index.files if _MINIFIED_RE.search(rf.name)]
    if offenders or minified:
        detail = ", ".join(offenders + minified[:3])
        yield ctx.fail(
            "no-committed-build-artifacts",
            "maintainability",
            f"Build artifacts appear committed: {detail}",
            remediation="Add build output to .gitignore and remove it from version control.",
        )
    else:
        yield ctx.ok(
            "no-committed-build-artifacts", "maintainability", "No build artifacts committed"
        )
