"""Concrete integrations for popular tools.

Each adapter knows how to invoke its tool in a machine-readable mode and map the
output onto Deval findings. Tools that are not installed are skipped silently;
the native checks still guarantee a baseline evaluation.
"""

from __future__ import annotations

import json

from ..fsindex import RepoIndex
from ..model import Finding, Severity
from .base import Integration, ToolRun
from .sarif import findings_from_sarif

_PY = (".py",)
_JS = (".js", ".jsx", ".ts", ".tsx")


class RuffIntegration(Integration):
    def __init__(self):
        super().__init__(name="ruff", category="maintainability", binary="ruff",
                         applies_suffixes=_PY)

    def command(self, index: RepoIndex) -> list[str]:
        return [self.binary, "check", ".", "--output-format", "json", "--exit-zero"]

    def normalize(self, run: ToolRun, index: RepoIndex) -> list[Finding]:
        try:
            data = json.loads(run.stdout or "[]")
        except json.JSONDecodeError:
            return []
        if not isinstance(data, list):
            return []
        out: list[Finding] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            out.append(Finding(
                rule_id=f"ruff/{item.get('code', 'E')}",
                category="maintainability",
                passed=False,
                message=item.get("message", "ruff finding"),
                severity=Severity.WARNING,
                path=item.get("filename"),
                line=(item.get("location") or {}).get("row"),
            ))
        return out


class EslintIntegration(Integration):
    def __init__(self):
        super().__init__(name="eslint", category="maintainability", binary="eslint",
                         applies_suffixes=_JS)

    def command(self, index: RepoIndex) -> list[str]:
        return [self.binary, ".", "-f", "json"]

    def normalize(self, run: ToolRun, index: RepoIndex) -> list[Finding]:
        try:
            data = json.loads(run.stdout or "[]")
        except json.JSONDecodeError:
            return []
        if not isinstance(data, list):
            return []
        out: list[Finding] = []
        for file_result in data:
            if not isinstance(file_result, dict):
                continue
            path = file_result.get("filePath")
            msgs = file_result.get("messages")
            if not isinstance(msgs, list):
                continue
            for msg in msgs:
                if not isinstance(msg, dict):
                    continue
                sev = Severity.ERROR if msg.get("severity") == 2 else Severity.WARNING
                out.append(Finding(
                    rule_id=f"eslint/{msg.get('ruleId') or 'parse'}",
                    category="maintainability",
                    passed=False,
                    message=msg.get("message", "eslint finding"),
                    severity=sev,
                    path=path,
                    line=msg.get("line"),
                ))
        return out


class GitleaksIntegration(Integration):
    def __init__(self):
        super().__init__(name="gitleaks", category="security", binary="gitleaks")

    def command(self, index: RepoIndex) -> list[str]:
        return [self.binary, "detect", "--no-git", "--report-format", "json",
                "--report-path", "/dev/stdout", "-s", "."]

    def normalize(self, run: ToolRun, index: RepoIndex) -> list[Finding]:
        try:
            data = json.loads(run.stdout or "[]")
        except json.JSONDecodeError:
            return []
        if not isinstance(data, list):
            return []
        out: list[Finding] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            out.append(Finding(
                rule_id="no-hardcoded-secrets",  # map onto native rule for dedupe
                category="security",
                passed=False,
                message=f"gitleaks: {item.get('Description', 'secret detected')}",
                severity=Severity.ERROR,
                path=item.get("File"),
                line=item.get("StartLine"),
            ))
        return out


class SemgrepIntegration(Integration):
    def __init__(self):
        super().__init__(name="semgrep", category="security", binary="semgrep")

    def command(self, index: RepoIndex) -> list[str]:
        return [self.binary, "--sarif", "--quiet", "--config", "auto", "."]

    def normalize(self, run: ToolRun, index: RepoIndex) -> list[Finding]:
        try:
            doc = json.loads(run.stdout or "{}")
        except json.JSONDecodeError:
            return []
        return findings_from_sarif(doc, "semgrep", "security")


class GenericSarifIntegration(Integration):
    """For tools invoked with a fixed command that emit SARIF on stdout."""

    def __init__(self, name, binary, category, cmd, applies_suffixes=(), applies_files=()):
        super().__init__(name=name, category=category, binary=binary,
                         applies_suffixes=applies_suffixes, applies_files=applies_files)
        self._cmd = cmd

    def command(self, index: RepoIndex) -> list[str]:
        return list(self._cmd)

    def normalize(self, run: ToolRun, index: RepoIndex) -> list[Finding]:
        try:
            doc = json.loads(run.stdout or "{}")
        except json.JSONDecodeError:
            return []
        return findings_from_sarif(doc, self.name, self.category)


class PresenceOnlyIntegration(Integration):
    """Detects a tool and records that it ran, without parsing output.

    Useful for tools whose value is captured by native checks but whose presence
    we still want to acknowledge in the report (e.g. linters wired into CI).
    """

    def __init__(self, name, binary, category, args, applies_suffixes=(), applies_files=()):
        super().__init__(name=name, category=category, binary=binary,
                         applies_suffixes=applies_suffixes, applies_files=applies_files)
        self._args = args

    def command(self, index: RepoIndex) -> list[str]:
        return [self.binary, *self._args]

    def normalize(self, run: ToolRun, index: RepoIndex) -> list[Finding]:
        return []


def default_integrations() -> list[Integration]:
    return [
        RuffIntegration(),
        EslintIntegration(),
        GitleaksIntegration(),
        SemgrepIntegration(),
        GenericSarifIntegration(
            "trivy", "trivy", "security",
            ["trivy", "fs", "--format", "sarif", "."],
        ),
        GenericSarifIntegration(
            "checkov", "checkov", "security",
            ["checkov", "-d", ".", "-o", "sarif", "--compact"],
            applies_files=("Dockerfile", "main.tf"),
        ),
        PresenceOnlyIntegration(
            "hadolint", "hadolint", "security", ["--version"],
            applies_files=("Dockerfile",),
        ),
        PresenceOnlyIntegration(
            "shellcheck", "shellcheck", "maintainability", ["--version"],
            applies_suffixes=(".sh", ".bash"),
        ),
        PresenceOnlyIntegration(
            "markdownlint", "markdownlint", "documentation", ["--version"],
            applies_suffixes=(".md",),
        ),
        PresenceOnlyIntegration(
            "actionlint", "actionlint", "ci", ["-version"],
            applies_files=(".github/workflows",),
        ),
    ]
