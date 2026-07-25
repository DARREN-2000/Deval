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
    tool = run.get("tool")
    if not isinstance(tool, dict):
        return levels
    driver = tool.get("driver")
    if not isinstance(driver, dict):
        return levels
    rules = driver.get("rules")
    if not isinstance(rules, list):
        return levels
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        rid = rule.get("id")
        cfg = rule.get("defaultConfiguration")
        if isinstance(cfg, dict) and rid and cfg.get("level"):
            levels[rid] = cfg["level"]
    return levels


def findings_from_sarif(doc: dict[str, Any], source: str, category: str) -> list[Finding]:
    findings: list[Finding] = []
    if not isinstance(doc, dict):
        return findings
    runs = doc.get("runs")
    if not isinstance(runs, list):
        return findings
    for run in runs:
        if not isinstance(run, dict):
            continue
        rule_levels = _rule_levels(run)
        results = run.get("results")
        if not isinstance(results, list):
            continue
        for result in results:
            if not isinstance(result, dict):
                continue
            rule_id = result.get("ruleId") or "unknown"
            level = result.get("level") or rule_levels.get(rule_id, "warning")
            severity = _LEVEL_TO_SEVERITY.get(level, Severity.WARNING)
            message = ""
            msg = result.get("message")
            if isinstance(msg, dict):
                message = msg.get("text") or msg.get("markdown") or ""
            elif isinstance(msg, str):
                message = msg
            path = None
            line = None
            locations = result.get("locations")
            if isinstance(locations, list) and locations:
                loc = locations[0]
                if isinstance(loc, dict):
                    phys = loc.get("physicalLocation")
                    if isinstance(phys, dict):
                        art = phys.get("artifactLocation")
                        if isinstance(art, dict):
                            path = art.get("uri")
                        region = phys.get("region")
                        if isinstance(region, dict):
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
