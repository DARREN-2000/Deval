"""Marketplace pack: example company security policy (\"company/security\").

Demonstrates how an organization ships private rules. Inert unless the repo has
source files; rules land in the security category and roll into the health
score.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from deval.sdk import CheckContext, Finding, rule

_SRC = (".py", ".js", ".ts", ".go", ".java", ".rb")
_INSECURE = re.compile(r"verify\s*=\s*False|rejectUnauthorized\s*:\s*false|InsecureSkipVerify\s*:\s*true", re.IGNORECASE)


@rule("company-no-insecure-tls", "security")
def company_no_insecure_tls(ctx: CheckContext) -> Iterable[Finding]:
    src = ctx.index.by_suffix(*_SRC)
    if not src:
        return
    flagged = False
    for rf in src:
        for i, line in enumerate(ctx.index.read_text(rf).splitlines(), start=1):
            if _INSECURE.search(line):
                flagged = True
                yield ctx.fail("company-no-insecure-tls", "security",
                               "TLS verification disabled",
                               path=rf.relpath, line=i,
                               remediation="Never disable TLS certificate verification.")
                break
    if not flagged:
        yield ctx.ok("company-no-insecure-tls", "security", "No disabled TLS verification found")
