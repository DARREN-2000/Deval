"""Normalize SARIF 2.1.0 documents into Deval findings.

SARIF is the lingua franca of code scanning, so any SARIF-emitting tool plugs
into Deval with almost no code. This module maps SARIF result levels onto Deval
severities and extracts the first physical location for each result.
"""

from __future__ import annotations

from typing import Any

from ..model import Finding, Severity

_LEVEL_TO_SEVERITY = {
    "error": Severity.ERROR,
    "warning": Severity.WARNING,
    "note": Severity.INFO,
    "none": Severity.INFO,
}


def _rule_levels(run: dict[str, Any]) -> dict[str, str]:
    levels: dict[str, str] = {}
    driver = (run.get("tool") or {}).get("driver") or {}
    for rule in driver.get("rules") or []:
        rid = rule.get("id")
        cfg = rule.get("defaultConfiguration") or {}
        if rid and cfg.get("level"):
            levels[rid] = cfg["level"]
    return levels


def findings_from_sarif(doc: dict[str, Any], source: str, category: str) -> list[Finding]:
    findings: list[Finding] = []
    for run in doc.get("runs") or []:
        rule_levels = _rule_levels(run)
        for result in run.get("results") or []:
            rule_id = result.get("ruleId") or "unknown"
            level = result.get("level") or rule_levels.get(rule_id, "warning")
            severity = _LEVEL_TO_SEVERITY.get(level, Severity.WARNING)
            message = ""
            msg = result.get("message") or {}
            if isinstance(msg, dict):
                message = msg.get("text") or msg.get("markdown") or ""
            path = None
            line = None
            locations = result.get("locations") or []
            if locations:
                phys = (locations[0] or {}).get("physicalLocation") or {}
                path = (phys.get("artifactLocation") or {}).get("uri")
                region = phys.get("region") or {}
                line = region.get("startLine")
            findings.append(
                Finding(
                    rule_id=f"{source}/{rule_id}",
                    category=category,
                    passed=False,
                    message=message or f"{source} reported {rule_id}",
                    severity=severity,
                    path=path,
                    line=line,
                    source=source,
                )
            )
    return findings
