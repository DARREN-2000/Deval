"""Deterministic scoring.

Each category starts at 100 and loses points for every failed finding, weighted
by severity. The overall score is a weighted average across categories. Grades
make the number instantly legible to managers and developers alike.

The function is pure: identical findings always yield an identical score.
"""

from __future__ import annotations

from .config import Config
from .grades import grade_for
from .model import CATEGORIES, CategoryScore, Finding, Severity

# Points removed from a category's 100 for each failed finding of a severity.
SEVERITY_PENALTY = {
    Severity.ERROR: 18,
    Severity.WARNING: 7,
    Severity.INFO: 2,
    Severity.OFF: 0,
}


# Backwards-compatible alias. The canonical implementation now lives in
# deval.grades so that deval.model can grade a score without importing scoring.
_grade = grade_for


def score_category(category: str, findings: list[Finding], weight: float) -> CategoryScore:
    """Score a single dimension from the findings that belong to it.

    The category starts at 100 and loses ``SEVERITY_PENALTY`` points for every
    failed finding, floored at 0. Findings for other categories are ignored, so
    the caller can pass the full finding list.
    """
    relevant = [f for f in findings if f.category == category]
    passed = sum(1 for f in relevant if f.passed)
    failed = sum(1 for f in relevant if not f.passed)
    penalty = 0
    for f in relevant:
        if not f.passed:
            penalty += SEVERITY_PENALTY.get(f.severity, 0)
    score = max(0, min(100, 100 - penalty))
    return CategoryScore(
        category=category,
        score=score,
        passed=passed,
        failed=failed,
        weight=weight,
    )


def compute_scores(findings: list[Finding], config: Config) -> tuple[list[CategoryScore], int, str]:
    """Score every dimension and roll them into one overall grade.

    Dimensions with no findings are excluded from the weighted average rather
    than counted as perfect, so a repository is never rewarded for the absence
    of evidence. The overall score is clamped to 0-100.

    Returns:
        The per-dimension scores, the overall score, and its letter grade.
    """
    categories: list[CategoryScore] = []
    for cat in CATEGORIES:
        categories.append(score_category(cat, findings, config.weight_for(cat)))

    scored = [c for c in categories if (c.passed + c.failed) > 0]
    if not scored:
        overall = 100
    else:
        total_weight = sum(c.weight for c in scored) or 1.0
        overall = round(sum(c.score * c.weight for c in scored) / total_weight)
    overall = max(0, min(100, int(overall)))
    return categories, overall, grade_for(overall)


def evaluate_gate(
    overall_score: int,
    findings: list[Finding],
    config: Config,
) -> tuple[bool, list[str]]:
    """Decide whether the scan passes the configured quality gate.

    A run fails if the overall score is below ``min_score`` or if any finding
    meets the ``fail_on`` severity. The reasons are returned rather than logged
    so the CLI can explain exactly why a build was blocked.

    Returns:
        Whether the gate passed, and a human-readable reason for each failure.
    """
    reasons: list[str] = []
    th = config.thresholds

    if overall_score < th.min_score:
        reasons.append(
            f"Overall score {overall_score} is below the required minimum of {th.min_score}."
        )

    fail_rank = th.fail_on.rank
    blocking = [
        f
        for f in findings
        if not f.passed and f.severity.rank >= fail_rank and fail_rank > 0
    ]
    if blocking:
        by_sev: dict[str, int] = {}
        for f in blocking:
            by_sev[f.severity.value] = by_sev.get(f.severity.value, 0) + 1
        summary = ", ".join(f"{count} {sev}" for sev, count in sorted(by_sev.items()))
        reasons.append(
            f"{len(blocking)} finding(s) at or above '{th.fail_on.value}' severity ({summary})."
        )

    if th.max_errors is not None:
        error_count = sum(
            1 for f in findings if not f.passed and f.severity == Severity.ERROR
        )
        if error_count > th.max_errors:
            reasons.append(
                f"{error_count} errors exceed the configured maximum of {th.max_errors}."
            )

    return (len(reasons) == 0), reasons
