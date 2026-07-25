"""Documentation quality: README depth, broken links, and public API docs."""

from __future__ import annotations

import re
from collections.abc import Iterable

from ..model import Finding
from ..registry import CheckContext, check

_README_NAMES = ("README.md", "README.rst", "README.txt", "README")
_EXPECTED_SECTIONS = ("install", "usage", "license")
_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


@check("readme-sections", "documentation")
def readme_sections(ctx: CheckContext) -> Iterable[Finding]:
    rf = None
    for name in _README_NAMES:
        rf = ctx.index.find(name)
        if rf:
            break
    if not rf:
        return
    text = ctx.index.read_text(rf).lower()
    missing = [s for s in _EXPECTED_SECTIONS if s not in text]
    if missing:
        yield ctx.fail(
            "readme-has-sections",
            "documentation",
            f"README is missing section(s): {', '.join(missing)}",
            path=rf.relpath,
            remediation="Document installation, usage, and licensing in the README.",
        )
    else:
        yield ctx.ok("readme-has-sections", "documentation", "README covers key sections")


@check("broken-relative-links", "documentation")
def broken_relative_links(ctx: CheckContext) -> Iterable[Finding]:
    broken = 0
    checked = 0
    for rf in ctx.index.by_suffix(".md", ".markdown"):
        text = ctx.index.read_text(rf)
        base = (ctx.index.root / rf.relpath).parent
        for match in _LINK_RE.finditer(text):
            target = match.group(1).strip()
            if target.startswith(("http://", "https://", "#", "mailto:", "tel:")):
                continue
            target = target.split("#", 1)[0].split("?", 1)[0].strip()
            if not target:
                continue
            checked += 1
            resolved = (base / target).resolve()
            if not resolved.exists():
                broken += 1
                yield ctx.fail(
                    "no-broken-relative-links",
                    "documentation",
                    f"Broken relative link to '{target}'",
                    path=rf.relpath,
                    remediation="Fix or remove the link target.",
                )
    if checked and broken == 0:
        yield ctx.ok(
            "no-broken-relative-links", "documentation", "All relative doc links resolve"
        )


@check("documented-public-api", "documentation")
def documented_public_api(ctx: CheckContext) -> Iterable[Finding]:
    py = [rf for rf in ctx.index.by_suffix(".py") if "test" not in rf.relpath.lower()]
    if not py:
        return
    undocumented = 0
    total = 0
    for rf in py:
        text = ctx.index.read_text(rf)
        lines = text.splitlines()
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("def ") and not stripped[4:].startswith("_"):
                total += 1
                nxt = lines[i + 1].strip() if i + 1 < len(lines) else ""
                if not (nxt.startswith(('"""', "'''"))):
                    undocumented += 1
    if total == 0:
        return
    ratio = undocumented / total
    if ratio > 0.5:
        yield ctx.fail(
            "documented-public-api",
            "documentation",
            f"{undocumented}/{total} public functions lack docstrings",
            remediation="Add docstrings to public functions and classes.",
        )
    else:
        yield ctx.ok(
            "documented-public-api",
            "documentation",
            f"Most public functions documented ({total - undocumented}/{total})",
        )
