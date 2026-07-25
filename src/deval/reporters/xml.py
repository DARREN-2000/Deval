"""XML report (JUnit-compatible) so CI systems can ingest Deval results.

Each category becomes a <testsuite>; each finding becomes a <testcase> that is a
<failure> when the standard is violated. The overall score and grade are
attached as properties on the root <testsuites> element.
"""

from __future__ import annotations

from xml.sax.saxutils import escape, quoteattr

from ..model import ScanResult


def _attr(value) -> str:
    return quoteattr(str(value))


def render(result: ScanResult) -> str:
    """Render ``result`` as a JUnit-style XML test suite.

    Every finding becomes a test case and every violation a failure, so CI
    systems that already understand JUnit (Jenkins, GitLab, Azure Pipelines)
    can display Deval results without a dedicated plugin.
    """
    total = len(result.findings)
    failures = len(result.failed_findings)
    lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    lines.append(
        f"<testsuites name={_attr('deval')} tests={_attr(total)} failures={_attr(failures)} "
        f"overall_score={_attr(result.overall_score)} grade={_attr(result.grade)} "
        f"passed_gate={_attr(str(result.passed_gate).lower())}>"
    )
    for cat in result.categories:
        if cat.passed + cat.failed == 0:
            continue
        cat_findings = [f for f in result.findings if f.category == cat.category]
        lines.append(
            f"  <testsuite name={_attr(cat.label)} tests={_attr(len(cat_findings))} "
            f"failures={_attr(cat.failed)} score={_attr(cat.score)}>"
        )
        for f in cat_findings:
            name = _attr(f.rule_id + ((": " + f.path) if f.path else ""))
            if f.passed:
                lines.append(f"    <testcase name={name} classname={_attr(cat.category)}/>")
            else:
                loc = f"{f.path}:{f.line}" if f.path and f.line else (f.path or "")
                msg = f.message + ((" " + loc) if loc else "")
                body = escape(f.message + ("\n" + f.remediation if f.remediation else ""))
                lines.append(f"    <testcase name={name} classname={_attr(cat.category)}>")
                lines.append(
                    f"      <failure type={_attr(f.severity.value)} message={_attr(msg)}>{body}</failure>"
                )
                lines.append("    </testcase>")
        lines.append("  </testsuite>")
    lines.append("</testsuites>")
    return "\n".join(lines)
