"""SARIF 2.1.0 output for GitHub Code Scanning and other SARIF consumers."""

from __future__ import annotations

import json

from ..model import ScanResult, Severity

_SEVERITY_TO_LEVEL = {
    Severity.ERROR: "error",
    Severity.WARNING: "warning",
    Severity.INFO: "note",
    Severity.OFF: "none",
}


def render(result: ScanResult) -> str:
    """Render ``result`` as a SARIF 2.1.0 document.

    Only failed findings are emitted, since SARIF describes problems rather
    than successful checks. Each distinct rule is declared once in the tool
    driver and referenced by result, which is what lets GitHub code scanning
    group, deduplicate, and track a finding across commits.
    """
    rules = {}
    results = []
    for f in result.failed_findings:
        rule_key = f.rule_id
        if rule_key not in rules:
            rules[rule_key] = {
                "id": rule_key,
                "name": rule_key,
                "shortDescription": {"text": rule_key},
                "defaultConfiguration": {"level": _SEVERITY_TO_LEVEL.get(f.severity, "warning")},
                "properties": {"category": f.category},
            }
        location = {}
        if f.path:
            region = {"startLine": f.line} if f.line else {}
            location = {
                "physicalLocation": {
                    "artifactLocation": {"uri": f.path},
                    **({"region": region} if region else {}),
                }
            }
        results.append({
            "ruleId": rule_key,
            "level": _SEVERITY_TO_LEVEL.get(f.severity, "warning"),
            "message": {"text": f.message + (f"\n{f.remediation}" if f.remediation else "")},
            "locations": [location] if location else [],
            "properties": {"source": f.source, "category": f.category},
        })

    doc = {
        "version": "2.1.0",
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "runs": [{
            "tool": {
                "driver": {
                    "name": "Deval",
                    "informationUri": "https://github.com/DARREN-2000/deval",
                    "version": result.deval_version,
                    "rules": list(rules.values()),
                }
            },
            "properties": {
                "overall_score": result.overall_score,
                "grade": result.grade,
                "passed_gate": result.passed_gate,
            },
            "results": results,
        }],
    }
    return json.dumps(doc, indent=2)
