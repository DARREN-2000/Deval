"""Core data model shared across the whole platform.

Everything Deval produces is expressed as :class:`Finding` objects. A finding is
fully deterministic: given the same repository and configuration, Deval always
produces the same findings in the same order. This is what makes the quality
gate repeatable and trustworthy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Severity(str, Enum):
    """Severity of a finding, ordered from least to most serious."""

    OFF = "off"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"

    @property
    def rank(self) -> int:
        return _SEVERITY_RANK[self]

    @classmethod
    def coerce(cls, value: Severity | str) -> Severity:
        if isinstance(value, Severity):
            return value
        normalized = str(value).strip().lower()
        aliases = {
            "true": "error",
            "on": "error",
            "enabled": "error",
            "false": "off",
            "disabled": "off",
            "none": "off",
            "warn": "warning",
            "err": "error",
        }
        normalized = aliases.get(normalized, normalized)
        return cls(normalized)


_SEVERITY_RANK = {
    Severity.OFF: 0,
    Severity.INFO: 1,
    Severity.WARNING: 2,
    Severity.ERROR: 3,
}


# The Engineering Dimensions of repository health. Each is a formal identity
# with its own score and grade. Order is stable and drives report layout.
CATEGORIES = (
    "repository",
    "documentation",
    "architecture",
    "structure",
    "dependencies",
    "testing",
    "ci",
    "security",
    "maintainability",
    "ownership",
    "observability",
    "operations",
    "compliance",
)

CATEGORY_LABELS = {
    "repository": "Repository",
    "documentation": "Documentation",
    "architecture": "Architecture",
    "structure": "Structure",
    "dependencies": "Dependencies",
    "testing": "Testing",
    "ci": "CI/CD",
    "security": "Security",
    "maintainability": "Maintainability",
    "ownership": "Ownership",
    "observability": "Observability",
    "operations": "Operations",
    "compliance": "Compliance",
}


@dataclass
class Finding:
    """A single deterministic fact about the repository.

    ``passed=True`` renders as a green check (a satisfied standard); ``passed=False``
    renders as a red cross (a violation). Findings emitted by external tools always
    represent violations.
    """

    rule_id: str
    category: str
    passed: bool
    message: str
    severity: Severity = Severity.WARNING
    path: str | None = None
    line: int | None = None
    remediation: str | None = None
    source: str = "native"  # "native" or an integration name such as "ruff"
    fingerprint: str | None = None

    @property
    def code(self) -> str:
        """Stable DV code for this rule (e.g. DV1001), or "" if unmapped."""
        from .codes import code_for
        return code_for(self.rule_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "code": self.code,
            "category": self.category,
            "passed": self.passed,
            "message": self.message,
            "severity": self.severity.value,
            "path": self.path,
            "line": self.line,
            "remediation": self.remediation,
            "source": self.source,
            "fingerprint": self.stable_fingerprint(),
        }

    def stable_fingerprint(self) -> str:
        if self.fingerprint:
            return self.fingerprint
        parts = [self.rule_id, self.path or "", str(self.line or ""), self.message]
        return "|".join(parts)


@dataclass
class CategoryScore:
    category: str
    score: int
    passed: int
    failed: int
    weight: float

    @property
    def label(self) -> str:
        return CATEGORY_LABELS.get(self.category, self.category.title())

    @property
    def grade(self) -> str:
        """Letter grade for this dimension's score (A+, A, B, ...)."""
        from .grades import grade_for
        return grade_for(self.score)

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "label": self.label,
            "score": self.score,
            "grade": self.grade,
            "passed": self.passed,
            "failed": self.failed,
            "weight": self.weight,
        }


@dataclass
class ScanResult:
    """The complete, serializable outcome of a scan."""

    repository: str
    generated_at: str
    deval_version: str
    standard: str
    overall_score: int
    grade: str
    passed_gate: bool
    gate_reasons: list[str]
    categories: list[CategoryScore]
    findings: list[Finding]
    integrations_run: list[str] = field(default_factory=list)
    integrations_available: list[str] = field(default_factory=list)
    duplicates_removed: int = 0
    suppressed: int = 0
    baselined: int = 0
    applied_standards: list[str] = field(default_factory=list)
    detected_technologies: list[str] = field(default_factory=list)

    @property
    def failed_findings(self) -> list[Finding]:
        return [f for f in self.findings if not f.passed]

    def category_score(self, category: str) -> int:
        for c in self.categories:
            if c.category == category:
                return c.score
        return 100

    def to_dict(self) -> dict[str, Any]:
        return {
            "repository": self.repository,
            "generated_at": self.generated_at,
            "deval_version": self.deval_version,
            "standard": self.standard,
            "applied_standards": self.applied_standards,
            "detected_technologies": self.detected_technologies,
            "overall_score": self.overall_score,
            "grade": self.grade,
            "passed_gate": self.passed_gate,
            "gate_reasons": self.gate_reasons,
            "categories": [c.to_dict() for c in self.categories],
            "findings": [f.to_dict() for f in self.findings],
            "integrations_run": self.integrations_run,
            "integrations_available": self.integrations_available,
            "duplicates_removed": self.duplicates_removed,
            "suppressed": self.suppressed,
            "baselined": self.baselined,
            "summary": {
                "total": len(self.findings),
                "passed": sum(1 for f in self.findings if f.passed),
                "failed": len(self.failed_findings),
                "errors": sum(
                    1 for f in self.failed_findings if f.severity == Severity.ERROR
                ),
                "warnings": sum(
                    1 for f in self.failed_findings if f.severity == Severity.WARNING
                ),
                "infos": sum(
                    1 for f in self.failed_findings if f.severity == Severity.INFO
                ),
            },
        }
