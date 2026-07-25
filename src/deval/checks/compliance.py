"""Compliance dimension: machine-readable licensing and supply-chain hygiene.

Compliance and SBOM tooling reads metadata, not prose. Deval checks that the
license is declared in a form automation can consume, and (opt-in) that
dependencies are automatically audited for known vulnerabilities.
"""

from __future__ import annotations

from collections.abc import Iterable

from ..model import Finding, Severity
from ..registry import CheckContext, check

OFF = Severity.OFF

_LICENSE_FILES = ("LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING", "COPYING.md")
_LICENSE_METADATA_TOKENS = ("license", "licence", "spdx")
_AUDIT_FILES = (
    ".github/dependabot.yml", ".github/dependabot.yaml", "renovate.json",
    ".renovaterc", ".renovaterc.json", ".snyk",
)


def _declares_license_metadata(ctx: CheckContext) -> bool:
    for name in ("pyproject.toml", "package.json", "Cargo.toml", "composer.json", "setup.cfg"):
        rf = ctx.index.find(name)
        if not rf:
            continue
        text = ctx.index.read_text(rf).lower()
        if any(tok in text for tok in _LICENSE_METADATA_TOKENS):
            return True
    return False


@check("declared-license", "compliance")
def declared_license(ctx: CheckContext) -> Iterable[Finding]:
    if not ctx.enabled("declared-license", OFF):
        return
    if ctx.index.has(*_LICENSE_FILES) or _declares_license_metadata(ctx):
        yield ctx.ok("declared-license", "compliance",
                     "License is declared in a machine-readable form")
    else:
        yield ctx.fail("declared-license", "compliance",
                       "No machine-readable license declaration",
                       remediation="Add a LICENSE file and declare the license in package metadata.")


@check("dependency-audit", "compliance")
def dependency_audit(ctx: CheckContext) -> Iterable[Finding]:
    # Opt-in (OFF by default): enabled by the enterprise profile.
    if not ctx.enabled("dependency-audit", OFF):
        return
    if ctx.index.has(*_AUDIT_FILES):
        yield ctx.ok("dependency-audit", "compliance",
                     "Automated dependency auditing is configured")
    else:
        yield ctx.fail("dependency-audit", "compliance",
                       "No automated dependency vulnerability auditing",
                       remediation="Enable Dependabot, Renovate, or Snyk to track vulnerable dependencies.")
