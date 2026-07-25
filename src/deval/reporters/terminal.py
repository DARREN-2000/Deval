"""Human-friendly terminal report with an at-a-glance scorecard."""

from __future__ import annotations

from ..model import ScanResult, Severity

_RESET = "\033[0m"
_BOLD = "\033[1m"
_DIM = "\033[2m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_RED = "\033[31m"
_CYAN = "\033[36m"

_SEV_COLOR = {Severity.ERROR: _RED, Severity.WARNING: _YELLOW, Severity.INFO: _CYAN}
_SEV_MARK = {Severity.ERROR: "\u2717", Severity.WARNING: "\u2717", Severity.INFO: "\u2717"}


class _C:
    def __init__(self, enabled: bool):
        self.enabled = enabled

    def __call__(self, code: str, text: str) -> str:
        if not self.enabled:
            return text
        return f"{code}{text}{_RESET}"


def _score_color(c, score: int) -> str:
    if score >= 90:
        return c(_GREEN, str(score))
    if score >= 75:
        return c(_YELLOW, str(score))
    return c(_RED, str(score))


def _bar(score: int, width: int = 20) -> str:
    filled = round(score / 100 * width)
    return "\u2588" * filled + "\u2591" * (width - filled)


def render(result: ScanResult, color: bool = True) -> str:
    """Render ``result`` as the human-facing terminal report.

    Set ``color=False`` for pipes, log files, and CI systems that do not
    interpret ANSI escapes; the layout is identical either way.
    """
    c = _C(color)
    lines = []
    lines.append("")
    lines.append(c(_BOLD, "  Deval \u2014 Engineering Health"))
    lines.append(c(_DIM, f"  {result.repository}"))
    lines.append(c(_DIM, f"  standard: {result.standard}  \u00b7  deval {result.deval_version}"))
    lines.append("")

    for cat in result.categories:
        if cat.passed + cat.failed == 0:
            continue
        label = cat.label.ljust(16)
        bar = _bar(cat.score)
        grade = c(_DIM, cat.grade.rjust(2))
        lines.append(f"  {label} {bar}  {_score_color(c, cat.score)}  {grade}")
    lines.append("")

    overall = _score_color(c, result.overall_score)
    lines.append(c(_BOLD, f"  Overall  {overall}/100   Grade {result.grade}"))

    if result.passed_gate:
        lines.append("  " + c(_GREEN + _BOLD, "PASS") + c(_DIM, "  quality gate satisfied"))
    else:
        lines.append("  " + c(_RED + _BOLD, "FAIL") + c(_DIM, "  quality gate not satisfied"))
        for reason in result.gate_reasons:
            lines.append(c(_RED, f"    \u2717 {reason}"))
    lines.append("")

    failed = result.failed_findings
    if failed:
        lines.append(c(_BOLD, "  Findings"))
        for f in failed:
            col = _SEV_COLOR.get(f.severity, "")
            mark = c(col, _SEV_MARK.get(f.severity, "\u2717"))
            loc = f" {c(_DIM, f.path)}" if f.path else ""
            if f.path and f.line:
                loc = f" {c(_DIM, f'{f.path}:{f.line}')}"
            src = c(_DIM, f" [{f.source}]") if f.source != "native" else ""
            ident = f"{f.code} {f.rule_id}" if f.code else f.rule_id
            lines.append(f"    {mark} {c(_DIM, ident)}  {f.message}{loc}{src}")
            if f.remediation:
                lines.append(c(_DIM, f"        \u2192 {f.remediation}"))
    else:
        lines.append("  " + c(_GREEN, "\u2713 No violations. Every standard is satisfied."))

    passed_count = sum(1 for f in result.findings if f.passed)
    lines.append("")
    lines.append(c(_DIM, f"  {passed_count} checks passed, {len(failed)} failed"))
    if result.integrations_run:
        lines.append(c(_DIM, f"  integrations: {', '.join(result.integrations_run)}"))
    if result.duplicates_removed:
        lines.append(c(_DIM, f"  {result.duplicates_removed} duplicate finding(s) merged"))
    lines.append("")
    return "\n".join(lines)
