"""Markdown report, ideal for PR comments and CI job summaries."""

from __future__ import annotations

from ..model import ScanResult, Severity

_SEV_EMOJI = {Severity.ERROR: "\U0001f534", Severity.WARNING: "\U0001f7e1", Severity.INFO: "\U0001f535"}


def _gauge(score: int) -> str:
    if score >= 90:
        return "\U0001f7e2"
    if score >= 75:
        return "\U0001f7e1"
    return "\U0001f534"


def render(result: ScanResult) -> str:
    """Render ``result`` as GitHub-flavoured Markdown.

    Sized for a pull request comment or ``$GITHUB_STEP_SUMMARY``: the score,
    grade, and gate verdict come first so a reviewer sees the outcome without
    expanding anything.
    """
    lines = []
    gate = "\u2705 PASS" if result.passed_gate else "\u274c FAIL"
    lines.append(f"## Deval Report \u2014 {result.overall_score}/100 (Grade {result.grade}) {gate}")
    lines.append("")
    lines.append(f"_Standard: `{result.standard}` \u00b7 Deval {result.deval_version}_")
    lines.append("")
    lines.append("| Dimension | Score | Grade | |")
    lines.append("|---|---:|:--:|:--|")
    for cat in result.categories:
        if cat.passed + cat.failed == 0:
            continue
        lines.append(f"| {cat.label} | {cat.score} | {cat.grade} | {_gauge(cat.score)} |")
    lines.append(f"| **Overall** | **{result.overall_score}** | **{result.grade}** | {_gauge(result.overall_score)} |")
    lines.append("")

    if not result.passed_gate and result.gate_reasons:
        lines.append("### Why the gate failed")
        for reason in result.gate_reasons:
            lines.append(f"- {reason}")
        lines.append("")

    failed = result.failed_findings
    if failed:
        lines.append(f"### Findings ({len(failed)})")
        lines.append("")
        for f in failed:
            emoji = _SEV_EMOJI.get(f.severity, "\u26aa")
            loc = f" (`{f.path}{':' + str(f.line) if f.line else ''}`)" if f.path else ""
            src = f" _[{f.source}]_" if f.source != "native" else ""
            ident = f"{f.code} {f.rule_id}" if f.code else f.rule_id
            lines.append(f"- {emoji} **{ident}** \u2014 {f.message}{loc}{src}")
            if f.remediation:
                lines.append(f"  - _Fix:_ {f.remediation}")
    else:
        lines.append("### \u2705 No violations \u2014 every standard is satisfied.")
    lines.append("")
    if result.integrations_run:
        lines.append(f"_Integrations run: {', '.join(result.integrations_run)}._")
    return "\n".join(lines)
