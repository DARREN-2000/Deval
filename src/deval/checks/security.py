"""Security policies: secrets, unsafe files, policy doc, permissions.

The secret detector is intentionally conservative: it targets high-signal
provider tokens and obvious hardcoded credentials, and skips well-known
placeholders and example values to keep false positives low. External tools such
as Gitleaks (Layer 3) provide deeper coverage; native detection guarantees a
baseline even with no tools installed.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from ..model import Finding
from ..registry import CheckContext, check

_SECRET_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("AWS access key id", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("AWS secret access key", re.compile(r"(?i)aws_secret_access_key\s*[=:]\s*['\"][0-9a-zA-Z/+]{40}['\"]")),
    ("Google API key", re.compile(r"AIza[0-9A-Za-z\-_]{35}")),
    ("Slack token", re.compile(r"xox[baprs]-[0-9A-Za-z-]{10,48}")),
    ("GitHub token", re.compile(r"gh[pousr]_[0-9A-Za-z]{36,}")),
    ("Private key block", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----")),
    ("Generic assigned secret", re.compile(
        r"(?i)(secret|password|passwd|api[_-]?key|token|access[_-]?key)\s*[=:]\s*['\"][^'\"]{8,}['\"]"
    )),
]

_PLACEHOLDER = re.compile(
    r"(?i)(example|dummy|placeholder|changeme|your[_-]?|xxx+|<[^>]+>|\$\{|os\.environ|getenv|process\.env|redacted|test)"
)

_UNSAFE_FILES = (
    "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519", ".env", ".env.local",
    ".npmrc", ".pypirc", ".netrc", "credentials.json", "serviceaccount.json",
)
_UNSAFE_SUFFIXES = (".pem", ".key", ".pfx", ".p12", ".keystore", ".jks")
_SCANNABLE = (
    ".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".java", ".rb", ".rs", ".php",
    ".yml", ".yaml", ".json", ".env", ".sh", ".txt", ".cfg", ".ini", ".toml", ".properties",
)


@check("no-hardcoded-secrets", "security")
def no_hardcoded_secrets(ctx: CheckContext) -> Iterable[Finding]:
    found = False
    scanned = False
    for rf in ctx.index.files:
        if rf.is_binary or rf.suffix not in _SCANNABLE:
            continue
        low = rf.relpath.lower()
        if "test" in low or "fixture" in low or "example" in low or "sample" in low:
            continue
        scanned = True
        text = ctx.index.read_text(rf)
        for lineno, line in enumerate(text.splitlines(), start=1):
            if len(line) > 500:
                continue
            for label, pattern in _SECRET_PATTERNS:
                m = pattern.search(line)
                if not m:
                    continue
                if _PLACEHOLDER.search(m.group(0)) or _PLACEHOLDER.search(line):
                    continue
                found = True
                yield ctx.fail(
                    "no-hardcoded-secrets",
                    "security",
                    f"Possible hardcoded secret ({label})",
                    path=rf.relpath,
                    line=lineno,
                    remediation="Move secrets to environment variables or a secret manager.",
                )
                break
    if scanned and not found:
        yield ctx.ok("no-hardcoded-secrets", "security", "No hardcoded secrets detected")


@check("no-unsafe-files", "security")
def no_unsafe_files(ctx: CheckContext) -> Iterable[Finding]:
    offenders = []
    for rf in ctx.index.files:
        if rf.name in _UNSAFE_FILES or rf.suffix in _UNSAFE_SUFFIXES:
            offenders.append(rf.relpath)
    if offenders:
        for path in offenders[:10]:
            yield ctx.fail(
                "no-unsafe-files",
                "security",
                f"Sensitive file committed: {path}",
                path=path,
                remediation="Remove the file from version control and rotate any exposed secrets.",
            )
    else:
        yield ctx.ok("no-unsafe-files", "security", "No sensitive files committed")


@check("require-security-policy", "security")
def require_security_policy(ctx: CheckContext) -> Iterable[Finding]:
    if ctx.index.has("SECURITY.md", ".github/SECURITY.md", "docs/SECURITY.md"):
        yield ctx.ok("require-security-policy", "security", "Security policy present")
    else:
        yield ctx.fail(
            "require-security-policy",
            "security",
            "No SECURITY.md policy",
            remediation="Add SECURITY.md explaining how to report vulnerabilities.",
        )


@check("no-world-writable", "security")
def no_world_writable(ctx: CheckContext) -> Iterable[Finding]:
    import stat

    offenders = []
    for rf in ctx.index.files:
        try:
            mode = rf.path.stat().st_mode
        except OSError:
            continue
        if mode & stat.S_IWOTH:
            offenders.append(rf.relpath)
    if offenders:
        for path in offenders[:10]:
            yield ctx.fail(
                "no-world-writable",
                "security",
                f"World-writable file: {path}",
                path=path,
                remediation="Tighten file permissions (remove world-write).",
            )
    # No positive finding: absence is the norm and would add noise.
