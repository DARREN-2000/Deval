"""Dependency health: lockfiles, duplicates, and pinned GitHub Actions."""

from __future__ import annotations

import re
from collections.abc import Iterable

from ..model import Finding
from ..registry import CheckContext, check

_MANIFESTS = {
    "package.json": ("package-lock.json", "pnpm-lock.yaml", "yarn.lock", "npm-shrinkwrap.json"),
    "pyproject.toml": ("poetry.lock", "uv.lock", "pdm.lock", "requirements.txt"),
    "requirements.in": ("requirements.txt",),
    "Gemfile": ("Gemfile.lock",),
    "go.mod": ("go.sum",),
    "Cargo.toml": ("Cargo.lock",),
}

_ACTION_USES_RE = re.compile(r"uses:\s*([^\s#]+)")


@check("require-lockfile", "dependencies")
def require_lockfile(ctx: CheckContext) -> Iterable[Finding]:
    seen_manifest = False
    for manifest, locks in _MANIFESTS.items():
        if not ctx.index.has(manifest):
            continue
        seen_manifest = True
        if ctx.index.has(*locks):
            yield ctx.ok("require-lockfile", "dependencies", f"Lockfile present for {manifest}")
        else:
            yield ctx.fail(
                "require-lockfile",
                "dependencies",
                f"{manifest} has no lockfile ({' / '.join(locks)})",
                path=manifest,
                remediation="Commit a lockfile for reproducible installs.",
            )
    if not seen_manifest:
        return


@check("no-duplicate-dependencies", "dependencies")
def no_duplicate_dependencies(ctx: CheckContext) -> Iterable[Finding]:
    rf = ctx.index.find("requirements.txt")
    if not rf:
        return
    names = {}
    dupes = set()
    for line in ctx.index.read_text(rf).splitlines():
        line = line.strip()
        if not line or line.startswith(("#", "-")):
            continue
        name = re.split(r"[<>=!~\[ ]", line, maxsplit=1)[0].strip().lower()
        if not name:
            continue
        if name in names:
            dupes.add(name)
        names[name] = True
    if dupes:
        yield ctx.fail(
            "no-duplicate-dependencies",
            "dependencies",
            f"Duplicate dependencies: {', '.join(sorted(dupes))}",
            path=rf.relpath,
            remediation="Declare each dependency once.",
        )
    else:
        yield ctx.ok("no-duplicate-dependencies", "dependencies", "No duplicate dependencies")


@check("pinned-github-actions", "dependencies")
def pinned_github_actions(ctx: CheckContext) -> Iterable[Finding]:
    workflows = ctx.index.glob(".github/workflows/*.yml") + ctx.index.glob(
        ".github/workflows/*.yaml"
    )
    if not workflows:
        return
    unpinned = []
    for rf in workflows:
        for m in _ACTION_USES_RE.finditer(ctx.index.read_text(rf)):
            ref = m.group(1).strip().strip('"').strip("'")
            if ref.startswith(".") or "@" not in ref:
                continue
            tag = ref.split("@", 1)[1]
            if tag in ("main", "master") or (tag.startswith("v") and tag[1:].split(".")[0].isdigit() is False) or tag in ("latest",):
                unpinned.append(f"{ref} ({rf.relpath})")
    if unpinned:
        yield ctx.fail(
            "pinned-github-actions",
            "dependencies",
            "Actions pinned to a mutable ref: " + "; ".join(unpinned[:5]),
            remediation="Pin actions to a version tag or commit SHA.",
        )
    else:
        yield ctx.ok("pinned-github-actions", "dependencies", "GitHub Actions are pinned")
