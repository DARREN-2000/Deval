"""Policy checks: opt-in rules that profiles and organizations can enable.

Every rule here defaults to OFF in ``deval/recommended`` and only runs when a
config or profile turns it on, so default scans are unaffected. Detection is
heuristic and language-agnostic - deterministic facts, never guesses.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from ..model import Finding, Severity
from ..registry import CheckContext, check

OFF = Severity.OFF
_SRC = (".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".java", ".rb")


def _is_test(relpath: str) -> bool:
    low = relpath.lower()
    return (
        "test" in low.split("/")
        or low.endswith(("_test.py", ".test.ts", ".test.js", ".spec.ts", ".spec.js"))
        or low.startswith("tests/")
        or "/tests/" in low
    )


@check("require-editorconfig", "repository")
def require_editorconfig(ctx: CheckContext) -> Iterable[Finding]:
    if not ctx.enabled("require-editorconfig", OFF):
        return
    if ctx.index.has(".editorconfig"):
        yield ctx.ok("require-editorconfig", "repository", ".editorconfig present")
    else:
        yield ctx.fail("require-editorconfig", "repository", "Missing .editorconfig",
                       remediation="Add an .editorconfig for consistent formatting.")


@check("require-dockerignore", "repository")
def require_dockerignore(ctx: CheckContext) -> Iterable[Finding]:
    if not ctx.enabled("require-dockerignore", OFF):
        return
    has_dockerfile = any(
        rf.name == "Dockerfile" or rf.name.startswith("Dockerfile")
        for rf in ctx.index.files
    )
    if not has_dockerfile:
        return
    if ctx.index.has(".dockerignore"):
        yield ctx.ok("require-dockerignore", "repository", ".dockerignore present")
    else:
        yield ctx.fail("require-dockerignore", "repository",
                       "Dockerfile present but no .dockerignore",
                       remediation="Add a .dockerignore to shrink build context and avoid leaking secrets.")


@check("no-console-log", "maintainability")
def no_console_log(ctx: CheckContext) -> Iterable[Finding]:
    if not ctx.enabled("no-console-log", OFF):
        return
    pat = re.compile(r"\bconsole\.log\s*\(|(^|\s)print\s*\(")
    hits = 0
    for rf in ctx.index.by_suffix(*_SRC):
        if _is_test(rf.relpath):
            continue
        for i, line in enumerate(ctx.index.read_text(rf).splitlines(), start=1):
            if pat.search(line):
                hits += 1
                yield ctx.fail("no-console-log", "maintainability",
                               "Debug print/console.log in shipped code",
                               path=rf.relpath, line=i,
                               remediation="Use a structured logger instead.")
                break
    if hits == 0:
        yield ctx.ok("no-console-log", "maintainability", "No stray debug prints")


@check("no-direct-sql", "architecture")
def no_direct_sql(ctx: CheckContext) -> Iterable[Finding]:
    if not ctx.enabled("no-direct-sql", OFF):
        return
    pat = re.compile(r"\b(SELECT\s+.+\s+FROM|INSERT\s+INTO|UPDATE\s+\w+\s+SET|DELETE\s+FROM)\b", re.IGNORECASE)
    flagged = 0
    for rf in ctx.index.by_suffix(*_SRC):
        rel = rf.relpath.lower()
        if any(tok in rel for tok in ("repository", "repositories", "repo", "dao", "store")):
            continue
        if _is_test(rel):
            continue
        for i, line in enumerate(ctx.index.read_text(rf).splitlines(), start=1):
            if pat.search(line):
                flagged += 1
                yield ctx.fail("no-direct-sql", "architecture",
                               "Raw SQL outside the repository layer",
                               path=rf.relpath, line=i,
                               remediation="Move queries into the repository/data layer or an ORM.")
                break
    if flagged == 0:
        yield ctx.ok("no-direct-sql", "architecture", "No raw SQL outside the data layer")


@check("require-opentelemetry", "observability")
def require_opentelemetry(ctx: CheckContext) -> Iterable[Finding]:
    if not ctx.enabled("require-opentelemetry", OFF):
        return
    found = False
    for rf in ctx.index.by_suffix(*_SRC):
        text = ctx.index.read_text(rf)
        if "opentelemetry" in text.lower() or "otel" in text.lower():
            found = True
            break
    if found:
        yield ctx.ok("require-opentelemetry", "observability", "OpenTelemetry instrumentation detected")
    else:
        yield ctx.fail("require-opentelemetry", "observability", "No OpenTelemetry instrumentation found",
                       remediation="Add OpenTelemetry SDK setup and instrument entry points.")


@check("require-authentication", "security")
def require_authentication(ctx: CheckContext) -> Iterable[Finding]:
    if not ctx.enabled("require-authentication", OFF):
        return
    # Only meaningful when the repo exposes HTTP routes.
    route_pat = re.compile(r"@(app|router)\.(get|post|put|delete|patch)\(|\.route\(", re.IGNORECASE)
    auth_pat = re.compile(r"auth|login|jwt|oauth|Depends\(|@login_required|Authorize", re.IGNORECASE)
    exposes_routes = False
    has_auth = False
    for rf in ctx.index.by_suffix(*_SRC):
        text = ctx.index.read_text(rf)
        if route_pat.search(text):
            exposes_routes = True
        if auth_pat.search(text):
            has_auth = True
    if not exposes_routes:
        return
    if has_auth:
        yield ctx.ok("require-authentication", "security", "Authentication mechanism detected on routes")
    else:
        yield ctx.fail("require-authentication", "security",
                       "HTTP routes found but no authentication mechanism detected",
                       remediation="Apply an auth dependency/middleware to exposed endpoints.")
