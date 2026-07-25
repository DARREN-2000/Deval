"""Baselines: adopt Deval on a legacy repo without failing overnight.

``deval baseline create`` records the fingerprints of today's violations into
``.deval/baseline.json``. Later scans (``deval scan --use-baseline`` or in CI)
suppress those known violations, so only *new* problems fail the gate. This is
the adoption pattern used by mature tools, and it makes the score reflect
forward progress.
"""

from __future__ import annotations

import json
from pathlib import Path

from .model import Finding, ScanResult

BASELINE_PATH = ".deval/baseline.json"


def create_baseline(result: ScanResult, repo_root: str) -> Path:
    root = Path(repo_root)
    path = root / BASELINE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    fingerprints = sorted({f.stable_fingerprint() for f in result.failed_findings})
    payload = {
        "version": 1,
        "created_at": result.generated_at,
        "deval_version": result.deval_version,
        "overall_score": result.overall_score,
        "count": len(fingerprints),
        "fingerprints": fingerprints,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def load_baseline(repo_root: str) -> set[str]:
    path = Path(repo_root) / BASELINE_PATH
    if not path.exists():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return set()
    return set(data.get("fingerprints", []))


def baseline_exists(repo_root: str) -> bool:
    return (Path(repo_root) / BASELINE_PATH).exists()


def apply_baseline(findings: list[Finding], fingerprints: set[str]) -> tuple[list[Finding], int]:
    """Drop failing findings already present in the baseline. Returns (kept, n)."""
    if not fingerprints:
        return findings, 0
    kept: list[Finding] = []
    baselined = 0
    for f in findings:
        if not f.passed and f.stable_fingerprint() in fingerprints:
            baselined += 1
            continue
        kept.append(f)
    return kept, baselined
