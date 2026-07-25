"""Supply-chain and fuzzing rules.

Every rule here follows Deval's domain-rule principle: a rule must be
**completely inert** where it does not apply. A repository that parses no
untrusted input is never asked for a fuzz harness, and a repository that
releases nothing is never asked for build provenance. A standards tool that
nags every small project on earth loses its credibility, and a rule nobody can
satisfy honestly is worse than no rule at all.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from ..fsindex import RepoFile
from ..model import Finding
from ..registry import CheckContext, check

_FUZZ_ENGINES = (
    "atheris", "libfuzzer", "cargo-fuzz", "cargo fuzz", "go-fuzz", "jazzer", "jqf",
    "afl", "honggfuzz", "hypothesis", "fast-check", "jsfuzz", "oss-fuzz", "clusterfuzz",
)

_SAST_TOOLS = (
    "codeql", "semgrep", "bandit", "sonarqube", "sonarcloud", "snyk",
    "checkmarx", "veracode", "gosec", "brakeman",
)

_ATTESTATION_MARKERS = (
    "attest-build-provenance", "actions/attest", "cosign", "sigstore",
    "slsa-framework", "provenance: true", "id-token: write",
)

_RELEASE_HINTS = ("release", "publish", "deploy", "cd")

_DEP_MANIFESTS = (
    "requirements.txt", "pyproject.toml", "Pipfile", "setup.py",
    "package.json", "go.mod", "Cargo.toml", "pom.xml", "build.gradle",
    "Gemfile", "composer.json",
)

# Signals that a codebase consumes data it did not author.
_UNTRUSTED_INPUT = re.compile(
    r"json\.loads|yaml\.safe_load|yaml\.load|tomllib|toml\.load|pickle\.loads|"
    r"xml\.etree|lxml|csv\.reader|configparser|zipfile|tarfile|base64\.b64decode|"
    r"struct\.unpack|ast\.parse|JSON\.parse|encoding/json|serde_json|ObjectMapper",
    re.IGNORECASE,
)

# Files whose *name* suggests they implement a parser.
_PARSER_NAME = re.compile(
    r"parser?|lexer|tokeni[sz]er|decoder?|deserial|unmarshal|codec", re.IGNORECASE
)

_SOURCE_SUFFIXES = (".py", ".js", ".ts", ".go", ".rs", ".java", ".rb", ".c", ".cc", ".cpp")


def _workflows(ctx: CheckContext) -> list[tuple[str, str]]:
    """Return ``(relpath, lowercased content)`` for every GitHub workflow."""
    out: list[tuple[str, str]] = []
    for pattern in (".github/workflows/*.yml", ".github/workflows/*.yaml"):
        for rf in ctx.index.glob(pattern):
            out.append((rf.relpath, ctx.index.read_text(rf).lower()))
    return out


def _fuzz_files(ctx: CheckContext) -> list[RepoFile]:
    """Find fuzz harnesses, by conventional path first then by engine name."""
    hits = [rf for rf in ctx.index.files if "fuzz" in rf.relpath.lower() and not rf.is_binary]
    if hits:
        return hits
    found: list[RepoFile] = []
    for rf in ctx.index.by_suffix(*_SOURCE_SUFFIXES):
        text = ctx.index.read_text(rf).lower()
        if any(engine in text for engine in _FUZZ_ENGINES):
            found.append(rf)
    return found


def _parses_untrusted_input(ctx: CheckContext) -> bool:
    """Whether this repository looks like it parses input it did not author.

    Deliberately conservative: it requires at least three parser-shaped files.
    A single ``json.loads`` is not a fuzzing obligation, and a false positive
    here would nag every small project on earth for a fuzz harness.
    """
    matches = 0
    for rf in ctx.index.by_suffix(*_SOURCE_SUFFIXES):
        text = ctx.index.read_text(rf)
        if _UNTRUSTED_INPUT.search(text) or _PARSER_NAME.search(rf.name):
            matches += 1
            if matches >= 3:
                return True
    return False


@check("require-fuzz-targets", "security")
def require_fuzz_targets(ctx: CheckContext) -> Iterable[Finding]:
    """Expect a fuzz harness where the code parses untrusted input."""
    if not _parses_untrusted_input(ctx):
        return
    targets = _fuzz_files(ctx)
    if targets:
        yield ctx.ok(
            "require-fuzz-targets",
            "security",
            f"Fuzz harness present ({len(targets)} file(s))",
        )
    else:
        yield ctx.fail(
            "require-fuzz-targets",
            "security",
            "Code parses untrusted input but ships no fuzz harness",
            remediation=(
                "Add a fuzz target for each parser entry point — for example a "
                "fuzz/ directory using Atheris, libFuzzer, cargo-fuzz or Hypothesis."
            ),
        )


@check("ci-runs-fuzzing", "ci")
def ci_runs_fuzzing(ctx: CheckContext) -> Iterable[Finding]:
    """Expect CI to actually execute the fuzz harnesses that already exist."""
    workflows = _workflows(ctx)
    if not workflows or not _fuzz_files(ctx):
        return
    blob = "\n".join(text for _, text in workflows)
    if "fuzz" in blob:
        yield ctx.ok("ci-runs-fuzzing", "ci", "CI runs fuzzing")
    else:
        yield ctx.fail(
            "ci-runs-fuzzing",
            "ci",
            "Fuzz targets exist but CI never runs them",
            remediation="Add a CI job that runs the fuzz targets with a bounded budget.",
        )


@check("ci-has-sast", "ci")
def ci_has_sast(ctx: CheckContext) -> Iterable[Finding]:
    """Expect static application security testing in CI."""
    workflows = _workflows(ctx)
    if not workflows:
        return
    blob = "\n".join(text for _, text in workflows)
    hit = next((tool for tool in _SAST_TOOLS if tool in blob), None)
    if hit:
        yield ctx.ok("ci-has-sast", "ci", f"CI runs static analysis ({hit})")
    else:
        yield ctx.fail(
            "ci-has-sast",
            "ci",
            "CI has no static application security testing step",
            remediation="Add CodeQL, Semgrep, Bandit or an equivalent SAST job.",
        )


@check("dependency-review", "dependencies")
def dependency_review(ctx: CheckContext) -> Iterable[Finding]:
    """Expect automated review of incoming dependency changes."""
    if not ctx.index.has(*_DEP_MANIFESTS):
        return
    if ctx.index.has(".github/dependabot.yml", ".github/dependabot.yaml", ".github/renovate.json", "renovate.json"):
        yield ctx.ok("dependency-review", "dependencies", "Automated dependency review configured")
        return
    blob = "\n".join(text for _, text in _workflows(ctx))
    if "dependency-review" in blob or "snyk" in blob:
        yield ctx.ok("dependency-review", "dependencies", "Dependency review runs in CI")
    else:
        yield ctx.fail(
            "dependency-review",
            "dependencies",
            "No automated dependency review",
            remediation=(
                "Enable Dependabot or Renovate, or add actions/dependency-review-action "
                "so vulnerable dependencies are caught in review."
            ),
        )


@check("release-attestation", "security")
def release_attestation(ctx: CheckContext) -> Iterable[Finding]:
    """Expect build provenance on workflows that publish artifacts."""
    release_flows = [
        (path, text)
        for path, text in _workflows(ctx)
        if any(hint in path.lower() for hint in _RELEASE_HINTS)
    ]
    if not release_flows:
        return
    for path, text in release_flows:
        if any(marker in text for marker in _ATTESTATION_MARKERS):
            yield ctx.ok("release-attestation", "security", f"Release provenance attested ({path})")
            return
    yield ctx.fail(
        "release-attestation",
        "security",
        "Release workflow publishes artifacts without build provenance",
        remediation=(
            "Add actions/attest-build-provenance (or cosign/sigstore) so consumers "
            "can verify an artifact was built by this workflow from this commit."
        ),
        path=release_flows[0][0],
    )
