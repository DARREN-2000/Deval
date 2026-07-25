"""Repository hygiene: the files every healthy project is expected to have."""

from __future__ import annotations

from collections.abc import Iterable

from ..model import Finding
from ..registry import CheckContext, check

# (rule_id, human name, candidate filenames, remediation)
_PRESENCE: list[tuple[str, str, tuple[str, ...], str]] = [
    ("require-readme", "README", ("README.md", "README.rst", "README.txt", "README"),
     "Add a README.md describing what the project does and how to use it."),
    ("require-license", "LICENSE", ("LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING"),
     "Add a LICENSE file so others know how they may use the code."),
    ("require-contributing", "CONTRIBUTING", ("CONTRIBUTING.md", "CONTRIBUTING.rst", ".github/CONTRIBUTING.md"),
     "Add CONTRIBUTING.md to explain how to set up and submit changes."),
    ("require-gitignore", ".gitignore", (".gitignore",),
     "Add a .gitignore so build artifacts and secrets are not committed."),
    ("require-code-of-conduct", "Code of Conduct",
     ("CODE_OF_CONDUCT.md", ".github/CODE_OF_CONDUCT.md"),
     "Add CODE_OF_CONDUCT.md to set community expectations."),
    ("require-changelog", "CHANGELOG", ("CHANGELOG.md", "CHANGES.md", "HISTORY.md"),
     "Add a CHANGELOG.md to record notable changes per release."),
]


@check("repository-presence", "repository")
def repository_presence(ctx: CheckContext) -> Iterable[Finding]:
    for rule_id, name, candidates, remediation in _PRESENCE:
        if ctx.index.has(*candidates):
            yield ctx.ok(rule_id, "repository", f"{name} present")
        else:
            yield ctx.fail(
                rule_id, "repository", f"Missing {name}", remediation=remediation
            )
