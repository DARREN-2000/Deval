"""Marketplace pack: React project conventions.

Inert unless the repository is a React project (a package.json that depends on
\"react\"). Rules land in the testing and maintainability categories.
"""

from __future__ import annotations

from collections.abc import Iterable

from deval.sdk import CheckContext, Finding, rule


def _is_react(ctx: CheckContext) -> bool:
    pkg = ctx.index.find("package.json")
    if pkg is None:
        return False
    return '"react"' in ctx.index.read_text(pkg)


@rule("react-testing-library", "testing")
def react_testing_library(ctx: CheckContext) -> Iterable[Finding]:
    if not _is_react(ctx):
        return
    pkg = ctx.index.find("package.json")
    text = ctx.index.read_text(pkg) if pkg else ""
    if "@testing-library/react" in text:
        yield ctx.ok("react-testing-library", "testing", "React Testing Library configured")
    else:
        yield ctx.fail("react-testing-library", "testing",
                       "No @testing-library/react dependency found",
                       path="package.json",
                       remediation="Add @testing-library/react to test components.")


@rule("react-no-dangerous-html", "maintainability")
def react_no_dangerous_html(ctx: CheckContext) -> Iterable[Finding]:
    if not _is_react(ctx):
        return
    flagged = False
    for rf in ctx.index.by_suffix(".jsx", ".tsx", ".js", ".ts"):
        for i, line in enumerate(ctx.index.read_text(rf).splitlines(), start=1):
            if "dangerouslySetInnerHTML" in line:
                flagged = True
                yield ctx.fail("react-no-dangerous-html", "maintainability",
                               "Use of dangerouslySetInnerHTML (XSS risk)",
                               path=rf.relpath, line=i,
                               remediation="Avoid raw HTML injection; sanitize or render safely.")
                break
    if not flagged:
        yield ctx.ok("react-no-dangerous-html", "maintainability", "No dangerouslySetInnerHTML usage")
