"""Integration base class.

An integration wraps an external tool. Deval only runs a tool when it is both
detected on PATH and applicable to the repository (e.g. Ruff only runs when
Python files exist). Output is normalized into Deval :class:`Finding` objects so
everything folds into a single score. Integrations never crash a scan: any error
is captured and the integration is simply skipped.
"""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass, field

from ..fsindex import RepoIndex
from ..model import Finding


@dataclass
class ToolRun:
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False


@dataclass
class Integration:
    name: str
    category: str
    binary: str
    applies_suffixes: Sequence[str] = field(default_factory=tuple)
    applies_files: Sequence[str] = field(default_factory=tuple)
    timeout: int = 120

    # --- lifecycle -------------------------------------------------------
    def available(self) -> bool:
        """Whether this tool's binary is present on ``PATH``.

        Deval never installs external tools; a missing binary simply means the
        integration is skipped and its findings are absent from the report.
        """
        return shutil.which(self.binary) is not None

    def applicable(self, index: RepoIndex) -> bool:
        """Whether this tool is relevant to the repository described by ``index``.

        An integration applies when the repository contains one of its file
        extensions or marker files. Integrations that declare neither are
        considered universally applicable.
        """
        if self.applies_suffixes and index.by_suffix(*self.applies_suffixes):
            return True
        if self.applies_files and index.has(*self.applies_files):
            return True
        return not (self.applies_suffixes or self.applies_files)

    def command(self, index: RepoIndex) -> list[str]:
        """Return the argv used to invoke the tool. Subclasses must implement.

        Returning an empty list signals that there is nothing to run for this
        repository, and the integration is skipped without being treated as an
        error.
        """
        raise NotImplementedError

    def normalize(self, run: ToolRun, index: RepoIndex) -> list[Finding]:
        """Convert raw tool output into Deval findings. Subclasses must implement.

        Normalising here is what allows results from very different tools to be
        deduplicated and folded into a single Engineering Health score.
        """
        raise NotImplementedError

    # --- execution -------------------------------------------------------
    def run(self, index: RepoIndex) -> ToolRun | None:
        """Execute the tool inside the repository and capture its output.

        Returns ``None`` when there is nothing to run or the process could not
        be started. A tool that exceeds ``timeout`` yields a :class:`ToolRun`
        flagged ``timed_out`` rather than raising, so one slow or hanging tool
        can never wedge a CI pipeline.
        """
        cmd = self.command(index)
        if not cmd:
            return None
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(index.root),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout,
                check=False,
            )
            return ToolRun(proc.returncode, proc.stdout, proc.stderr)
        except subprocess.TimeoutExpired:
            return ToolRun(-1, "", "timed out", timed_out=True)
        except (OSError, ValueError):
            return None

    def collect(self, index: RepoIndex) -> list[Finding]:
        """Run the tool and return its findings, tagged with this tool's name.

        This is the method the engine calls. Any failure to run or parse the
        tool degrades to an empty list: a broken or unexpectedly-updated
        external tool must never crash a scan or silently corrupt the score.
        """
        run = self.run(index)
        if run is None:
            return []
        try:
            findings = self.normalize(run, index)
        except Exception:
            return []
        for f in findings:
            f.source = self.name
        return findings
