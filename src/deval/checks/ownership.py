"""Ownership: CODEOWNERS and declared maintainers."""

from __future__ import annotations

from collections.abc import Iterable

from ..model import Finding
from ..registry import CheckContext, check

_CODEOWNERS = ("CODEOWNERS", ".github/CODEOWNERS", "docs/CODEOWNERS", ".gitlab/CODEOWNERS")


@check("require-codeowners", "ownership")
def require_codeowners(ctx: CheckContext) -> Iterable[Finding]:
    rf = None
    for name in _CODEOWNERS:
        rf = ctx.index.find(name)
        if rf:
            break
    if not rf:
        yield ctx.fail(
            "require-codeowners",
            "ownership",
            "No CODEOWNERS file",
            remediation="Add a CODEOWNERS file mapping paths to responsible reviewers.",
        )
        return
    meaningful = [
        ln
        for ln in ctx.index.read_text(rf).splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    if meaningful:
        yield ctx.ok("require-codeowners", "ownership", "CODEOWNERS defines reviewers")
    else:
        yield ctx.fail(
            "require-codeowners",
            "ownership",
            "CODEOWNERS is empty",
            path=rf.relpath,
            remediation="Assign owners for at least the critical paths.",
        )


@check("require-maintainers", "ownership")
def require_maintainers(ctx: CheckContext) -> Iterable[Finding]:
    markers = ("MAINTAINERS", "MAINTAINERS.md", "OWNERS", "AUTHORS", "AUTHORS.md")
    if ctx.index.has(*markers):
        yield ctx.ok("require-maintainers", "ownership", "Maintainers are declared")
        return
    # A populated CODEOWNERS also satisfies the intent.
    for name in _CODEOWNERS:
        if ctx.index.has(name):
            return
    yield ctx.fail(
        "require-maintainers",
        "ownership",
        "No maintainers declared",
        remediation="Add a MAINTAINERS file or populate CODEOWNERS.",
    )
