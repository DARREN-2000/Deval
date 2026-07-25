"""Safe, deterministic autofix.

Deval only autofixes things it can generate correctly without guessing: missing
scaffolding files (LICENSE, CODEOWNERS, .editorconfig, .gitignore, SECURITY.md,
CODE_OF_CONDUCT.md, CONTRIBUTING.md, .dockerignore, and a README stub). It never
touches source code or rewrites content it cannot fully determine.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .model import ScanResult


def _license(root: Path) -> str:
    year = _dt.date.today().year
    return (
        "MIT License\n\n"
        f"Copyright (c) {year} {root.name}\n\n"
        "Permission is hereby granted, free of charge, to any person obtaining a copy\n"
        "of this software and associated documentation files (the \"Software\"), to deal\n"
        "in the Software without restriction, including without limitation the rights\n"
        "to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n"
        "copies of the Software, and to permit persons to whom the Software is\n"
        "furnished to do so, subject to the following conditions:\n\n"
        "The above copyright notice and this permission notice shall be included in all\n"
        "copies or substantial portions of the Software.\n\n"
        "THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND.\n"
    )


def _codeowners(root: Path) -> str:
    return "# Every path needs a responsible reviewer. Replace with real teams.\n*    @owners\n"


def _editorconfig(root: Path) -> str:
    return (
        "root = true\n\n[*]\n"
        "charset = utf-8\n"
        "end_of_line = lf\n"
        "insert_final_newline = true\n"
        "trim_trailing_whitespace = true\n"
        "indent_style = space\n"
        "indent_size = 4\n"
    )


def _gitignore(root: Path) -> str:
    return (
        "# Caches and build output\n"
        "__pycache__/\n*.py[cod]\n.venv/\nvenv/\nnode_modules/\ndist/\nbuild/\n"
        ".pytest_cache/\n.ruff_cache/\n.coverage\nhtmlcov/\n"
        "# Deval\ndeval.json\nreport.sarif\n"
    )


def _security(root: Path) -> str:
    return (
        "# Security Policy\n\n"
        "## Reporting a vulnerability\n\n"
        "Please report security issues privately via the repository's security\n"
        "advisories, or email the maintainers. We aim to respond within 72 hours.\n"
    )


def _code_of_conduct(root: Path) -> str:
    return (
        "# Code of Conduct\n\n"
        "This project follows the Contributor Covenant. Be respectful and\n"
        "constructive. Report unacceptable behavior to the maintainers.\n\n"
        "See https://www.contributor-covenant.org/ for the full text.\n"
    )


def _contributing(root: Path) -> str:
    return (
        "# Contributing\n\n"
        "1. Fork and create a feature branch.\n"
        "2. Install dependencies and run the test suite.\n"
        "3. Open a pull request describing the change and its impact.\n"
    )


def _dockerignore(root: Path) -> str:
    return ".git\n.gitignore\n__pycache__/\n*.pyc\n.venv/\nnode_modules/\ndist/\nbuild/\n.env\n"


def _readme(root: Path) -> str:
    return (
        f"# {root.name}\n\n"
        "> One-line description of what this project does.\n\n"
        "## Installation\n\n```bash\n# install steps\n```\n\n"
        "## Usage\n\n```bash\n# usage example\n```\n\n"
        "## License\n\nSee LICENSE.\n"
    )


@dataclass
class Fixer:
    rule_id: str
    filename: str
    builder: Callable[[Path], str]
    description: str


# rule id -> how to generate the missing file
FIXERS: dict[str, Fixer] = {
    "require-license": Fixer("require-license", "LICENSE", _license, "Add an MIT LICENSE"),
    "require-codeowners": Fixer("require-codeowners", "CODEOWNERS", _codeowners, "Generate a CODEOWNERS"),
    "require-editorconfig": Fixer("require-editorconfig", ".editorconfig", _editorconfig, "Create an .editorconfig"),
    "require-gitignore": Fixer("require-gitignore", ".gitignore", _gitignore, "Create a .gitignore"),
    "require-security-policy": Fixer("require-security-policy", "SECURITY.md", _security, "Add SECURITY.md"),
    "require-code-of-conduct": Fixer("require-code-of-conduct", "CODE_OF_CONDUCT.md", _code_of_conduct, "Add CODE_OF_CONDUCT.md"),
    "require-contributing": Fixer("require-contributing", "CONTRIBUTING.md", _contributing, "Add CONTRIBUTING.md"),
    "require-dockerignore": Fixer("require-dockerignore", ".dockerignore", _dockerignore, "Create a .dockerignore"),
    "require-readme": Fixer("require-readme", "README.md", _readme, "Add a README stub"),
}


@dataclass
class FixAction:
    rule_id: str
    filename: str
    description: str


def plan_fixes(result: ScanResult) -> list[FixAction]:
    """Which failing findings can be safely autofixed."""
    seen = set()
    actions: list[FixAction] = []
    for f in result.failed_findings:
        fixer = FIXERS.get(f.rule_id)
        if fixer and fixer.rule_id not in seen:
            seen.add(fixer.rule_id)
            actions.append(FixAction(fixer.rule_id, fixer.filename, fixer.description))
    return actions


def apply_fixes(actions: list[FixAction], repo_root: str, dry_run: bool = False) -> list[str]:
    """Write the scaffolding files. Never overwrites an existing file."""
    root = Path(repo_root)
    written: list[str] = []
    for action in actions:
        fixer = FIXERS[action.rule_id]
        target = root / fixer.filename
        if target.exists():
            continue
        if not dry_run:
            target.write_text(fixer.builder(root), encoding="utf-8")
        written.append(fixer.filename)
    return written
