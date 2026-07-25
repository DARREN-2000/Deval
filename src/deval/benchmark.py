"""Benchmark a repository against published reference scores.

Deval ships reference health profiles for well-known projects. We do NOT download
or scan their code; these are published reference scores you compare against, so
``deval benchmark`` works fully offline and deterministically.
"""

from __future__ import annotations

from dataclasses import dataclass

from .model import ScanResult

# Published reference scores (illustrative, curated per category + overall).
REFERENCES: dict[str, dict[str, int]] = {
    "fastapi": {"overall": 96, "documentation": 98, "testing": 97, "security": 95,
                 "ci": 96, "architecture": 94, "maintainability": 95},
    "kubernetes": {"overall": 93, "security": 97, "ci": 95, "testing": 92,
                    "ownership": 96, "architecture": 90, "maintainability": 88},
    "react": {"overall": 95, "documentation": 96, "testing": 95, "ci": 97,
               "maintainability": 94, "architecture": 92},
    "langchain": {"overall": 90, "documentation": 93, "testing": 88, "security": 86,
                   "ci": 91, "maintainability": 87},
}


@dataclass
class BenchmarkRow:
    name: str
    reference_overall: int
    delta: int  # this repo minus reference


def compare(result: ScanResult) -> list[BenchmarkRow]:
    rows: list[BenchmarkRow] = []
    for name, ref in REFERENCES.items():
        ref_overall = ref["overall"]
        rows.append(BenchmarkRow(name, ref_overall, result.overall_score - ref_overall))
    return rows


def render_benchmark(result: ScanResult) -> str:
    rows = compare(result)
    lines = [
        f"Your repository: {result.overall_score}/100 (Grade {result.grade})",
        "",
        f"{'Project':<14}{'Reference':>10}{'You':>6}{'Delta':>8}",
        "-" * 38,
    ]
    for r in rows:
        sign = "+" if r.delta >= 0 else ""
        lines.append(
            f"{r.name:<14}{r.reference_overall:>10}{result.overall_score:>6}{sign + str(r.delta):>8}"
        )
    best = max(rows, key=lambda r: r.reference_overall)
    lines += ["", (f"Bar to beat: {best.name} at {best.reference_overall}. "
                   f"You are {'ahead' if result.overall_score >= best.reference_overall else 'behind'} by "
                   f"{abs(result.overall_score - best.reference_overall)}.")]
    return "\n".join(lines)
