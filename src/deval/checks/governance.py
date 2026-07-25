"""Project governance maturity: decision-making, support, ADRs, local hooks.

These rules cover the artifacts that separate a published project from a
personal repository: how decisions get made, where users go for help, why the
architecture is the way it is, and whether problems are caught before CI.

Every rule is gated on :func:`_is_published_project`. A private script, a
scratch repo, or a coursework directory has no business being told it needs a
governance charter, and a rule nobody can satisfy honestly is worse than no
rule at all. All four default to INFO or WARNING rather than ERROR for the
same reason: these are maturity signals, not correctness failures.
"""

from __future__ import annotations

from collections.abc import Iterable

from ..model import Finding, Severity
from ..registry import CheckContext, check

_LICENSES = ("LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING")
_READMES = ("README.md", "README.rst", "README.txt", "README")
_CONTRIBUTING = ("CONTRIBUTING.md", "CONTRIBUTING.rst", ".github/CONTRIBUTING.md")

_GOVERNANCE = ("GOVERNANCE.md", "GOVERNANCE", "docs/GOVERNANCE.md", ".github/GOVERNANCE.md")
_SUPPORT = ("SUPPORT.md", "SUPPORT", ".github/SUPPORT.md", "docs/SUPPORT.md")
_ADR_DOCS = (
    "ARCHITECTURE.md", "docs/ARCHITECTURE.md", "DESIGN.md", "docs/DESIGN.md",
    "docs/architecture.md", "docs/design.md",
)
_PRE_COMMIT = (
    ".pre-commit-config.yaml", ".pre-commit-config.yml",
    "lefthook.yml", ".husky/pre-commit", ".githooks/pre-commit",
)


def _is_published_project(ctx: CheckContext) -> bool:
    """Whether this repository looks like something other people consume.

    Requires a license plus a readme: the two things a project acquires when it
    stops being private. Without both, every rule in this module stays silent.
    """
    return ctx.index.has(*_LICENSES) and ctx.index.has(*_READMES)


def _has_adr_directory(ctx: CheckContext) -> bool:
    """Whether the repo keeps numbered architecture decision records."""
    for pattern in ("docs/adr/*.md", "docs/adrs/*.md", "adr/*.md", "doc/adr/*.md",
                    "docs/decisions/*.md", "docs/rfcs/*.md"):
        if ctx.index.glob(pattern):
            return True
    return False


@check("require-governance", "ownership")
def require_governance(ctx: CheckContext) -> Iterable[Finding]:
    """Expect a written account of how project decisions get made."""
    if not _is_published_project(ctx):
        return
    if ctx.index.has(*_GOVERNANCE):
        yield ctx.ok("require-governance", "ownership", "Governance model documented")
        return
    # A contributing guide that explains decision-making covers the intent.
    for name in _CONTRIBUTING:
        rf = ctx.index.find(name)
        if rf:
            text = ctx.index.read_text(rf).lower()
            if any(tok in text for tok in ("governance", "decision", "maintainer", "review process")):
                yield ctx.ok(
                    "require-governance",
                    "ownership",
                    "Decision-making documented in the contributing guide",
                )
                return
    yield ctx.fail(
        "require-governance",
        "ownership",
        "No governance model documented",
        severity=ctx.sev("require-governance", Severity.INFO),
        remediation=(
            "Add GOVERNANCE.md explaining who decides what, how maintainers are "
            "added, and how disputes are resolved."
        ),
    )


@check("require-support-policy", "ownership")
def require_support_policy(ctx: CheckContext) -> Iterable[Finding]:
    """Expect a stated channel for users who need help."""
    if not _is_published_project(ctx):
        return
    if ctx.index.has(*_SUPPORT):
        yield ctx.ok("require-support-policy", "ownership", "Support channel documented")
        return
    for name in _READMES:
        rf = ctx.index.find(name)
        if rf:
            text = ctx.index.read_text(rf).lower()
            if any(tok in text for tok in ("## support", "getting help", "## help", "discussions")):
                yield ctx.ok("require-support-policy", "ownership", "Support channel documented in README")
                return
    yield ctx.fail(
        "require-support-policy",
        "ownership",
        "No support channel documented",
        severity=ctx.sev("require-support-policy", Severity.INFO),
        remediation=(
            "Add SUPPORT.md pointing users at issues, discussions or a chat "
            "channel, and say what response time to expect."
        ),
    )


@check("require-adr", "architecture")
def require_adr(ctx: CheckContext) -> Iterable[Finding]:
    """Expect significant architectural decisions to be written down.

    Only asked of projects large enough for the question to be fair: a repo
    with fewer than 40 source files does not need a decision log.
    """
    if not _is_published_project(ctx):
        return
    source_count = len(ctx.index.by_suffix(".py", ".js", ".ts", ".tsx", ".go", ".rs", ".java"))
    if source_count < 40:
        return
    if _has_adr_directory(ctx):
        yield ctx.ok("require-adr", "architecture", "Architecture decision records present")
        return
    if ctx.index.has(*_ADR_DOCS):
        yield ctx.ok("require-adr", "architecture", "Architecture documented")
        return
    yield ctx.fail(
        "require-adr",
        "architecture",
        f"No architecture decisions recorded ({source_count} source files)",
        severity=ctx.sev("require-adr", Severity.INFO),
        remediation=(
            "Add docs/adr/ with numbered decision records, or an ARCHITECTURE.md "
            "explaining the structure and the trade-offs behind it."
        ),
    )


@check("require-pre-commit", "maintainability")
def require_pre_commit(ctx: CheckContext) -> Iterable[Finding]:
    """Expect local hooks so problems are caught before they reach CI.

    Inert unless the project already has CI: a repo with no pipeline at all has
    a more basic problem, and ``require-ci`` already reports it.
    """
    if not _is_published_project(ctx):
        return
    has_ci = bool(
        ctx.index.glob(".github/workflows/*.yml")
        or ctx.index.glob(".github/workflows/*.yaml")
        or ctx.index.has(".gitlab-ci.yml", "Jenkinsfile", ".circleci/config.yml")
    )
    if not has_ci:
        return
    if ctx.index.has(*_PRE_COMMIT):
        yield ctx.ok("require-pre-commit", "maintainability", "Pre-commit hooks configured")
    else:
        yield ctx.fail(
            "require-pre-commit",
            "maintainability",
            "No pre-commit hooks configured",
            severity=ctx.sev("require-pre-commit", Severity.INFO),
            remediation=(
                "Add .pre-commit-config.yaml so formatting and lint failures are "
                "caught locally instead of burning a CI run."
            ),
        )
