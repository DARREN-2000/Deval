"""Optional score history, stored as newline-delimited JSON.

History is opt-in (``--save-history``) and powers the trend line in the HTML
dashboard and the delta shown by ``deval report``. It is deliberately simple and
human-readable.
"""

from __future__ import annotations

import json
from pathlib import Path

from .model import ScanResult

_HISTORY_PATH = ".deval/history.jsonl"


def append_history(result: ScanResult, repo_root: str | None = None) -> Path:
    root = Path(repo_root or result.repository)
    path = root / _HISTORY_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "generated_at": result.generated_at,
        "overall_score": result.overall_score,
        "grade": result.grade,
        "passed_gate": result.passed_gate,
        "categories": {c.category: c.score for c in result.categories},
    }
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")
    return path


def load_history(repo_root: str) -> list[dict]:
    path = Path(repo_root) / _HISTORY_PATH
    if not path.exists():
        return []
    out: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def previous_score(repo_root: str) -> int | None:
    hist = load_history(repo_root)
    if not hist:
        return None
    return hist[-1].get("overall_score")
