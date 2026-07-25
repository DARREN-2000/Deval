"""Continuous integration health: pipeline presence, tests, scans, caching."""

from __future__ import annotations

from collections.abc import Iterable

from ..fsindex import RepoFile
from ..model import Finding
from ..registry import CheckContext, check

_CI_GLOBS = (
    ".github/workflows/*.yml",
    ".github/workflows/*.yaml",
    ".gitlab-ci.yml",
    ".circleci/config.yml",
    "azure-pipelines.yml",
    "Jenkinsfile",
    ".drone.yml",
    "bitbucket-pipelines.yml",
)

_TEST_TOKENS = ("pytest", "unittest", "npm test", "npm run test", "go test", "cargo test",
                "mvn test", "gradle test", "jest", "tox", "rspec", "phpunit", "make test")
_SCAN_TOKENS = ("codeql", "trivy", "snyk", "gitleaks", "semgrep", "bandit", "dependabot",
                "grype", "checkov", "security")
_CACHE_TOKENS = ("actions/cache", "cache:", "cache-dependency", "save-cache", "restore-cache")


def _ci_files(ctx: CheckContext) -> list[RepoFile]:
    found: list[RepoFile] = []
    for pattern in _CI_GLOBS:
        if "*" in pattern:
            found.extend(ctx.index.glob(pattern))
        else:
            rf = ctx.index.find(pattern)
            if rf:
                found.append(rf)
    return found


@check("require-ci", "ci")
def require_ci(ctx: CheckContext) -> Iterable[Finding]:
    files = _ci_files(ctx)
    if files:
        yield ctx.ok("require-ci", "ci", f"CI configuration present ({len(files)} file(s))")
    else:
        yield ctx.fail(
            "require-ci",
            "ci",
            "No CI configuration found",
            remediation="Add a CI pipeline (e.g. a GitHub Actions workflow).",
        )


@check("ci-quality", "ci")
def ci_quality(ctx: CheckContext) -> Iterable[Finding]:
    files = _ci_files(ctx)
    if not files:
        return
    blob = "\n".join(ctx.index.read_text(rf).lower() for rf in files)

    if any(tok in blob for tok in _TEST_TOKENS):
        yield ctx.ok("ci-runs-tests", "ci", "CI runs the test suite")
    else:
        yield ctx.fail(
            "ci-runs-tests",
            "ci",
            "CI does not appear to run tests",
            remediation="Add a test step to the CI pipeline.",
        )

    if any(tok in blob for tok in _SCAN_TOKENS):
        yield ctx.ok("ci-has-security-scan", "ci", "CI includes a security scan")
    else:
        yield ctx.fail(
            "ci-has-security-scan",
            "ci",
            "CI has no security scanning step",
            remediation="Add SAST/secret/dependency scanning to CI.",
        )

    if any(tok in blob for tok in _CACHE_TOKENS):
        yield ctx.ok("ci-uses-cache", "ci", "CI caches dependencies")
    else:
        yield ctx.fail(
            "ci-uses-cache",
            "ci",
            "CI does not cache dependencies",
            remediation="Cache dependencies to speed up CI.",
        )
