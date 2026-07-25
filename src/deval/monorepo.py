"""Monorepo support: one health score, plus a score per subproject.

Deval detects subprojects under conventional roots (``apps/``, ``packages/``,
``services/``, ``libs/``, ``modules/``) by looking for project markers
(package.json, pyproject.toml, go.mod, Cargo.toml, etc.). Each subproject is
scanned independently for its own score, and the repository-level score is the
weighted roll-up - so teams get both the big number and the drill-down.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .model import ScanResult
from .grades import grade_for

_WORKSPACE_ROOTS = ("apps", "packages", "services", "libs", "modules", "projects")
_PROJECT_MARKERS = (
    "package.json", "pyproject.toml", "setup.py", "go.mod", "Cargo.toml",
    "pom.xml", "build.gradle", "composer.json", "Gemfile",
)


@dataclass
class SubprojectResult:
    name: str
    path: str
    result: ScanResult


@dataclass
class MonorepoResult:
    root: str
    overall_score: int
    grade: str
    projects: list[SubprojectResult] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialise the monorepo roll-up and a summary row per subproject.

        Each subproject is reduced to score, grade, and gate status rather than
        its full result, keeping the aggregate document small enough to publish
        as a CI artifact.
        """
        return {
            "root": self.root,
            "overall_score": self.overall_score,
            "grade": self.grade,
            "projects": [
                {"name": p.name, "path": p.path, "score": p.result.overall_score,
                 "grade": p.result.grade, "passed_gate": p.result.passed_gate}
                for p in self.projects
            ],
        }


def detect_subprojects(repo_root: str) -> list[str]:
    """Find subprojects beneath the conventional workspace directories.

    A child directory counts as a project only when it contains a recognised
    manifest (``package.json``, ``pyproject.toml``, ``go.mod``, ...), so vendored
    assets and stray folders are not mistaken for projects. Paths are returned
    relative to ``repo_root`` with forward slashes on every platform.
    """
    root = Path(repo_root)
    found: list[str] = []
    for ws in _WORKSPACE_ROOTS:
        ws_dir = root / ws
        if not ws_dir.is_dir():
            continue
        for child in sorted(ws_dir.iterdir()):
            if not child.is_dir():
                continue
            if any((child / m).exists() for m in _PROJECT_MARKERS):
                found.append(str(child.relative_to(root)).replace("\\", "/"))
    return found


def scan_monorepo(
    repo_root: str,
    profiles: list[str] | None = None,
    run_integrations: bool = True,
) -> MonorepoResult:
    """Scan every detected subproject and roll the results into one score.

    Each subproject is scanned independently so it keeps its own config and
    detected stack, then the overall figure is aggregated across them. A
    repository with no detected subprojects is scanned as a single project, so
    this is safe to call on any repository.
    """
    from .engine import scan as run_scan

    root = Path(repo_root)
    subprojects = detect_subprojects(repo_root)
    projects: list[SubprojectResult] = []

    if subprojects:
        for rel in subprojects:
            res = run_scan(str(root / rel), profiles=profiles, run_integrations=run_integrations)
            projects.append(SubprojectResult(name=rel, path=rel, result=res))
        # Roll-up: simple average of subproject scores (each project counts once).
        overall = round(sum(p.result.overall_score for p in projects) / len(projects))
    else:
        # No subprojects: fall back to a single whole-repo scan.
        res = run_scan(repo_root, profiles=profiles, run_integrations=run_integrations)
        projects.append(SubprojectResult(name=".", path=".", result=res))
        overall = res.overall_score

    overall = max(0, min(100, int(overall)))
    return MonorepoResult(root=str(root), overall_score=overall, grade=grade_for(overall), projects=projects)


def render_monorepo(mr: MonorepoResult, color: bool = True) -> str:
    lines = [
        "Monorepo Health",
        "=" * 40,
        f"Overall: {mr.overall_score}/100  Grade {mr.grade}   ({len(mr.projects)} projects)",
        "",
        f"{'Project':<28}{'Score':>6}{'Grade':>7}",
        "-" * 41,
    ]
    for p in sorted(mr.projects, key=lambda x: x.result.overall_score):
        gate = "" if p.result.passed_gate else "  (gate failed)"
        lines.append(f"{p.name:<28}{p.result.overall_score:>6}{p.result.grade:>7}{gate}")
    return "\n".join(lines)
