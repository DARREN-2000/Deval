"""Check registry and the context passed to every native check.

A *check* is a small, pure function that inspects the repository and yields
:class:`Finding` objects. Checks register themselves with :func:`check` so that
new checks (and, later, language plugins) can be added without touching the
engine. Every check is deterministic and side-effect free.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Callable

from .config import Config
from .fsindex import RepoIndex
from .model import Finding, Severity


@dataclass
class CheckContext:
    index: RepoIndex
    config: Config

    def sev(self, rule_id: str, default: Severity = Severity.WARNING) -> Severity:
        """Resolve the effective severity for ``rule_id`` after config layering.

        ``default`` is the severity the rule author chose; the user's
        ``.deval.yml`` and any inherited standards may override it.
        """
        return self.config.severity_for(rule_id, default)

    def enabled(self, rule_id: str, default: Severity = Severity.WARNING) -> bool:
        """Whether ``rule_id`` is switched on in the resolved configuration.

        A rule set to ``off`` is skipped entirely and never reaches scoring.
        """
        return self.config.is_enabled(rule_id, default)

    def ok(self, rule_id: str, category: str, message: str, **kw) -> Finding:
        """Build a passing :class:`Finding` for ``rule_id``.

        Passing findings are recorded, not discarded: the score needs to know
        how many checks succeeded, and reports show the full evidence trail.
        """
        return Finding(
            rule_id=rule_id,
            category=category,
            passed=True,
            message=message,
            severity=self.sev(rule_id),
            **kw,
        )

    def fail(self, rule_id: str, category: str, message: str, **kw) -> Finding:
        """Build a failing :class:`Finding` for ``rule_id``.

        Pass ``remediation`` (and ``path``/``line`` where known) so the report
        can tell the developer exactly what to change and where.
        """
        return Finding(
            rule_id=rule_id,
            category=category,
            passed=False,
            message=message,
            severity=self.sev(rule_id),
            **kw,
        )


CheckFn = Callable[[CheckContext], Iterable[Finding]]


@dataclass
class RegisteredCheck:
    name: str
    category: str
    fn: CheckFn


_REGISTRY: list[RegisteredCheck] = []


def check(name: str, category: str) -> Callable[[CheckFn], CheckFn]:
    """Register a function as a native check under ``name`` and ``category``.

    Used as a decorator::

        @check("require-license", "compliance")
        def require_license(ctx: CheckContext) -> Iterable[Finding]:
            ...

    Registration is idempotent: re-importing a module (which happens when
    plugins and built-ins are loaded in different orders) will not duplicate a
    check that is already registered under the same name.
    """

    def decorator(fn: CheckFn) -> CheckFn:
        """Add ``fn`` to the registry and return it unchanged."""
        if not any(rc.name == name for rc in _REGISTRY):
            _REGISTRY.append(RegisteredCheck(name=name, category=category, fn=fn))
        return fn

    return decorator


def registered_checks() -> list[RegisteredCheck]:
    """Return a copy of every currently registered check.

    A copy is returned so callers (the rule catalog, ``deval doctor``, tests)
    cannot mutate the registry by accident.
    """
    return list(_REGISTRY)


def run_checks(ctx: CheckContext) -> list[Finding]:
    """Run every registered check against ``ctx`` and collect the findings.

    Disabled rules are dropped and severities are re-resolved from config, so
    a rule author's default never overrides an explicit user setting.

    A check that raises is contained rather than fatal: the exception becomes
    an informational ``internal-error/<check>`` finding and the scan continues.
    One broken third-party plugin must not be able to take down a CI pipeline.
    """
    findings: list[Finding] = []
    for rc in _REGISTRY:
        try:
            for finding in rc.fn(ctx) or ():
                if finding is None:
                    continue
                if not ctx.enabled(finding.rule_id, finding.severity):
                    continue
                finding.severity = ctx.sev(finding.rule_id, finding.severity)
                findings.append(finding)
        except Exception as exc:  # a broken check must never crash a scan
            findings.append(
                Finding(
                    rule_id=f"internal-error/{rc.name}",
                    category=rc.category,
                    passed=True,
                    message=f"Check '{rc.name}' raised {type(exc).__name__}: {exc}",
                    severity=Severity.INFO,
                )
            )
    return findings


def load_builtin_checks() -> None:
    """Import check modules so their decorators register. Import-time safe."""
    from .checks import (  # noqa: F401
        architecture,
        ci,
        compliance,
        dependencies,
        documentation,
        domains,
        governance,
        maintainability,
        observability,
        operations,
        ownership,
        policies,
        repository,
        security,
        structure,
        supply_chain,
        testing,
    )
