"""Repository file index.

Walking the filesystem once and sharing the result with every check keeps scans
fast and deterministic. The index also honours ignore globs (``node_modules``,
virtualenvs, VCS internals, and user-configured patterns).
"""

from __future__ import annotations

import fnmatch
import os
from collections.abc import Iterable
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path

DEFAULT_IGNORES = (
    ".git/**",
    ".hg/**",
    ".svn/**",
    "**/node_modules/**",
    "**/.venv/**",
    "**/venv/**",
    "**/__pycache__/**",
    "**/.mypy_cache/**",
    "**/.pytest_cache/**",
    "**/.ruff_cache/**",
    "**/dist/**",
    "**/build/**",
    "**/.next/**",
    "**/target/**",
    "**/*.egg-info/**",
    "**/.deval/**",
)

BINARY_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".zip", ".gz",
    ".tar", ".7z", ".woff", ".woff2", ".ttf", ".otf", ".mp4", ".mov", ".mp3",
    ".so", ".dylib", ".dll", ".class", ".jar", ".pyc", ".bin", ".wasm",
}


@dataclass
class RepoFile:
    path: Path
    relpath: str
    size: int

    @property
    def suffix(self) -> str:
        """Lowercased file extension including the dot, e.g. ``".py"``."""
        return self.path.suffix.lower()

    @property
    def name(self) -> str:
        """Base filename without any directory component."""
        return self.path.name

    @property
    def is_binary(self) -> bool:
        """Whether this file is binary and should not be read as text.

        Detection is extension-based rather than content-sniffing so that the
        answer is cheap and deterministic across platforms.
        """
        return self.suffix in BINARY_SUFFIXES


@dataclass
class RepoIndex:
    root: Path
    files: list[RepoFile] = field(default_factory=list)
    _by_rel: dict[str, RepoFile] = field(default_factory=dict)

    def add(self, rf: RepoFile) -> None:
        """Register ``rf`` in the index under both its exact and lowercased path.

        Indexing both spellings lets checks look up conventional filenames such
        as ``README.md`` without worrying about case on any platform.
        """
        self.files.append(rf)
        self._by_rel[rf.relpath] = rf
        self._by_rel[rf.relpath.lower()] = rf

    def has(self, *relpaths: str) -> bool:
        """Return ``True`` if *any* of the given relative paths exists.

        Useful for checks that accept several conventional names, for example
        ``index.has("LICENSE", "LICENSE.md", "LICENSE.txt")``.
        """
        return any(self.find(rp) is not None for rp in relpaths)

    def find(self, relpath: str) -> RepoFile | None:
        """Look up a single file by relative path, or ``None`` if absent.

        The exact spelling is tried first, then a case-insensitive fallback.
        """
        return self._by_rel.get(relpath) or self._by_rel.get(relpath.lower())

    def find_any_dir(self, name: str) -> RepoFile | None:
        """Return the first file whose path contains a segment matching name."""
        for rf in self.files:
            if name in rf.relpath.split("/"):
                return rf
        return None

    def glob(self, pattern: str) -> list[RepoFile]:
        """Return every indexed file whose relative path matches ``pattern``.

        Matching uses :mod:`fnmatch` against the forward-slash relative path,
        so patterns behave identically on Windows and POSIX.
        """
        return [rf for rf in self.files if fnmatch.fnmatch(rf.relpath, pattern)]

    def by_suffix(self, *suffixes: str) -> list[RepoFile]:
        """Return every indexed file whose extension is one of ``suffixes``.

        Suffixes are compared case-insensitively and must include the leading
        dot, e.g. ``by_suffix(".py", ".pyi")``.
        """
        s = {x.lower() for x in suffixes}
        return [rf for rf in self.files if rf.suffix in s]

    def top_level_dirs(self) -> list[str]:
        """Return the sorted names of directories directly under the repo root.

        Only directories that actually contain indexed files are reported, so
        ignored and empty directories never appear.
        """
        dirs = set()
        for rf in self.files:
            head = rf.relpath.split("/", 1)
            if len(head) == 2:
                dirs.add(head[0])
        return sorted(dirs)

    @cached_property
    def total_bytes(self) -> int:
        """Combined size in bytes of every indexed file (computed once)."""
        return sum(rf.size for rf in self.files)

    def read_text(self, rf: RepoFile, max_bytes: int = 2_000_000) -> str:
        """Read ``rf`` as UTF-8 text, truncated to ``max_bytes``.

        Undecodable bytes are replaced rather than raising, and unreadable
        files yield an empty string. A check must never crash a scan because a
        single file was oddly encoded, deleted mid-walk, or unreadable.
        """
        try:
            data = rf.path.read_bytes()[:max_bytes]
            return data.decode("utf-8", errors="replace")
        except OSError:
            return ""


def _matches_any(relpath: str, patterns: Iterable[str]) -> bool:
    for pattern in patterns:
        if fnmatch.fnmatch(relpath, pattern):
            return True
        if pattern.startswith("**/"):
            p = pattern[3:]
            if fnmatch.fnmatch(relpath, p):
                return True
            if p.endswith("/**") and (relpath == p[:-3] or relpath.startswith(p[:-2])):
                return True
        if pattern.endswith("/**") and (
            relpath == pattern[:-3] or relpath.startswith(pattern[:-2])
        ):
            return True
    return False


def build_index(root: str | os.PathLike, extra_ignores: Iterable[str] = ()) -> RepoIndex:
    """Walk ``root`` once and return a fully populated :class:`RepoIndex`.

    ``DEFAULT_IGNORES`` (VCS internals, dependency and build directories) are
    always applied; ``extra_ignores`` adds user-configured globs on top.
    Ignored directories are pruned during the walk rather than filtered
    afterwards, so large trees such as ``node_modules`` are never descended.

    The resulting file list is sorted by relative path, which is what makes
    scan output stable across machines and operating systems.
    """
    root_path = Path(root).resolve()
    ignores = tuple(DEFAULT_IGNORES) + tuple(extra_ignores)
    index = RepoIndex(root=root_path)

    for dirpath, dirnames, filenames in os.walk(root_path):
        rel_dir = os.path.relpath(dirpath, root_path)
        rel_dir = "" if rel_dir == "." else rel_dir.replace(os.sep, "/")

        kept = []
        for d in dirnames:
            candidate = f"{rel_dir}/{d}" if rel_dir else d
            if _matches_any(candidate + "/x", ignores) or _matches_any(candidate, ignores):
                continue
            kept.append(d)
        dirnames[:] = sorted(kept)

        for fname in sorted(filenames):
            rel = f"{rel_dir}/{fname}" if rel_dir else fname
            if _matches_any(rel, ignores):
                continue
            fpath = Path(dirpath) / fname
            if fpath.is_symlink():
                continue
            try:
                size = fpath.stat().st_size
            except OSError:
                continue
            index.add(RepoFile(path=fpath, relpath=rel, size=size))

    index.files.sort(key=lambda rf: rf.relpath)
    return index
