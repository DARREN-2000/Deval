"""Preflight diagnostics for a trustworthy Deval quality gate.

``deval doctor`` answers the question users should ask *before* enforcing a
standard: what configuration was resolved, which technologies and standards
will apply, how complete the built-in rule contract is, and which optional
integration tools are available for this repository.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import __version__
from .catalog import build_catalog, catalog_stats
from .config import load_config
from .config_lint import Issue, validate_config
from .detect import detect
from .fsindex import build_index
from .integrations import default_integrations
from .model import Severity


@dataclass
class IntegrationStatus:
    name: str
    applicable: bool
    available: bool
    mode: str
    status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "applicable": self.applicable,
            "available": self.available,
            "mode": self.mode,
            "status": self.status,
        }


@dataclass
class DoctorReport:
    repository: str
    version: str = __version__
    config_path: str | None = None
    issues: list[Issue] = field(default_factory=list)
    detected: list[str] = field(default_factory=list)
    standards: list[str] = field(default_factory=list)
    enabled_rules: int = 0
    catalog: dict[str, int] = field(default_factory=dict)
    integrations: list[IntegrationStatus] = field(default_factory=list)

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.level == "error"]

    @property
    def warnings(self) -> list[Issue]:
        return [i for i in self.issues if i.level == "warning"]

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "deval_version": self.version,
            "repository": self.repository,
            "ok": self.ok,
            "config": {
                "path": self.config_path,
                "issues": [i.to_dict() for i in self.issues],
            },
            "detected_technologies": self.detected,
            "applied_standards": self.standards,
            "enabled_rules": self.enabled_rules,
            "catalog": dict(self.catalog),
            "integrations": [i.to_dict() for i in self.integrations],
        }


def diagnose(repo_root: str, config_path: str | None = None) -> DoctorReport:
    root = Path(repo_root).resolve()
    report = DoctorReport(repository=str(root))
    if not root.exists():
        report.issues.append(Issue("error", "repository", f"path does not exist: {root}"))
        return report
    if not root.is_dir():
        report.issues.append(Issue("error", "repository", f"path is not a directory: {root}"))
        return report

    config_report = validate_config(str(root), config_path)
    report.config_path = config_report.config_path
    report.issues.extend(config_report.issues)
    report.catalog = catalog_stats()

    # Invalid configuration must never be partially interpreted by diagnostics.
    if config_report.errors:
        return report

    cfg = load_config(str(root), config_path)
    index = build_index(str(root), cfg.ignore)
    detections = detect(index) if cfg.autodetect else []
    report.detected = [d.label for d in detections]
    cfg.with_detected([d.standard for d in detections])
    report.standards = list(cfg.applied_standards)

    by_id = {r.rule_id: r for r in build_catalog()}
    report.enabled_rules = sum(
        1 for rid, info in by_id.items()
        if cfg.rules.get(rid, info.default_severity) != Severity.OFF
    )

    for integration in default_integrations():
        applicable = integration.applicable(index)
        available = integration.available()
        mode = cfg.integration_mode(integration.name).strip().lower()
        if mode in {"off", "false", "no"}:
            status = "disabled"
        elif not applicable:
            status = "not-applicable"
        elif available:
            status = "ready"
        else:
            status = "missing"
            if mode in {"on", "true", "yes"}:
                report.issues.append(Issue(
                    "error", "integrations",
                    f"integration '{integration.name}' is required but '{integration.binary}' is not on PATH.",
                ))
        report.integrations.append(IntegrationStatus(
            integration.name, applicable, available, mode, status,
        ))

    if report.catalog.get("documented") != report.catalog.get("total"):
        report.issues.append(Issue(
            "error", "catalog", "one or more built-in rules are missing explain documentation.",
        ))
    if report.catalog.get("coded") != report.catalog.get("total"):
        report.issues.append(Issue(
            "error", "catalog", "one or more built-in rules are missing stable DV codes.",
        ))
    return report
