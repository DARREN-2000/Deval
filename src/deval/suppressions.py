"""Suppressions: silence a finding a team has consciously accepted.

Two mechanisms, mirroring tools developers already know:

1. A ``deval-ignore.yml`` file at the repo root::

     ignore:
       - require-changelog                 # everywhere
       - rule: no-hardcoded-secrets         # scoped to a path glob
         path: "tests/**"

2. Inline comments on (or directly above) the offending line::

     API_KEY = "..."  # deval-ignore no-hardcoded-secrets

Suppressed findings are removed from the score and the gate, and counted so the
report stays honest about how much was silenced.
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from pathlib import Path

from .fsindex import RepoIndex
from .model import Finding

IGNORE_FILENAMES = ("deval-ignore.yml", "deval-ignore.yaml", ".deval-ignore.yml")
_INLINE_TOKEN = "# deval-ignore"  # deval-ignore no-hardcoded-secrets
_INLINE_TOKEN_ALT = "// deval-ignore"  # deval-ignore no-hardcoded-secrets


@dataclass
class Suppression:
    rule_id: str
    path_glob: str | None = None

    def matches(self, finding: Finding) -> bool:
        """Whether this suppression covers ``finding``.

        A ``rule_id`` of ``"*"`` matches every rule. When ``path_glob`` is set,
        the finding must also carry a path matching it, so a path-scoped
        suppression can never silently hide a repository-wide violation.
        """
        if self.rule_id not in ("*", finding.rule_id):
            return False
        if self.path_glob is None:
            return True
        if not finding.path:
            return False
        return fnmatch.fnmatch(finding.path, self.path_glob)


def load_suppressions(repo_root: str) -> list[Suppression]:
    """Load declared suppressions from the repository's ignore file.

    The first filename in :data:`IGNORE_FILENAMES` that exists wins. A missing
    file is not an error: it simply means nothing is suppressed.
    """
    root = Path(repo_root)
    path = next((root / n for n in IGNORE_FILENAMES if (root / n).exists()), None)
    if path is None:
        return []
    from .config import _load_yaml  # local import to avoid a cycle

    data = _load_yaml(path.read_text(encoding="utf-8", errors="replace"))
    raw = data.get("ignore") or data.get("suppress") or []
    if isinstance(raw, (str, dict)):
        raw = [raw]
    out: list[Suppression] = []
    for entry in raw:
        if isinstance(entry, str):
            out.append(Suppression(rule_id=entry.strip()))
        elif isinstance(entry, dict):
            rid = str(entry.get("rule") or entry.get("rule_id") or "*").strip()
            glob = entry.get("path")
            out.append(Suppression(rule_id=rid, path_glob=str(glob) if glob else None))
    return out


def _inline_suppressed(finding: Finding, index: RepoIndex) -> bool:
    """True if the finding's line (or the line above) carries an inline ignore."""
    if not finding.path:
        return False
    rf = index.find(finding.path)
    if rf is None or rf.is_binary:
        return False
    text = index.read_text(rf)
    lines = text.splitlines()
    if not lines:
        return False

    def _line_ignores(line: str) -> bool:
        for token in (_INLINE_TOKEN, _INLINE_TOKEN_ALT):
            idx = line.find(token)
            if idx == -1:
                continue
            rest = line[idx + len(token):].strip()
            if not rest:  # bare token: ignore any rule on this line
                return True
            targets = {t.strip().strip(",") for t in rest.replace(",", " ").split()}
            if finding.rule_id in targets or "*" in targets:
                return True
        return False

    if finding.line and 1 <= finding.line <= len(lines):
        i = finding.line - 1
        if _line_ignores(lines[i]):
            return True
        if i - 1 >= 0 and _line_ignores(lines[i - 1]):
            return True
    # A file-level directive on the very first line suppresses the whole file.
    if lines and ("deval-ignore-file" in lines[0]):
        if finding.rule_id in lines[0] or lines[0].strip().endswith("deval-ignore-file"):
            return True
    return False


def apply_suppressions(
    findings: list[Finding],
    index: RepoIndex,
    suppressions: list[Suppression],
) -> tuple[list[Finding], int]:
    """Filter suppressed violations out of ``findings``.

    Both declared suppressions and inline ``deval: ignore`` comments are
    honoured. Passing findings are never suppressed, so suppression can only
    ever hide a violation, not fabricate a success.

    Returns:
        The surviving findings and the number that were suppressed.
    """
    kept: list[Finding] = []
    suppressed = 0
    for f in findings:
        if not f.passed and (any(s.matches(f) for s in suppressions) or _inline_suppressed(f, index)):
            suppressed += 1
            continue
        kept.append(f)
    return kept, suppressed
