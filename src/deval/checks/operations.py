"""Operations dimension: can this repository be built, shipped, and run?

Deval looks for packaging metadata or deployment descriptors so the artifact is
reproducible, and that service containers declare a healthcheck so orchestrators
can tell a hung container from a healthy one.

The healthcheck rule is scoped deliberately: it applies only to images that
``EXPOSE`` a port. CLI and batch images run once and exit, so a healthcheck
would never execute, and requiring one would be cargo cult rather than a
standard worth enforcing.
"""

from __future__ import annotations

from collections.abc import Iterable

from ..model import Finding, Severity
from ..registry import CheckContext, check

OFF = Severity.OFF

# Packaging / build metadata that yields a distributable artifact.
_PACKAGING = (
    "pyproject.toml", "setup.py", "setup.cfg", "package.json", "go.mod",
    "Cargo.toml", "pom.xml", "build.gradle", "build.gradle.kts", "composer.json",
    "Gemfile",
)
# Deployment descriptors.
_DEPLOY_FILES = (
    "Dockerfile", "docker-compose.yml", "docker-compose.yaml", "Procfile",
    "serverless.yml", "fly.toml", "vercel.json", "app.yaml", "Makefile",
)
_DEPLOY_DIRS = ("charts", "helm", "k8s", "kubernetes", "deploy", "deployment", ".github")


def _has_deploy_dir(ctx: CheckContext) -> bool:
    for name in _DEPLOY_DIRS:
        if ctx.index.find_any_dir(name):
            return True
    return False


@check("deployable-artifact", "operations")
def deployable_artifact(ctx: CheckContext) -> Iterable[Finding]:
    if not ctx.enabled("deployable-artifact", OFF):
        return
    if ctx.index.has(*_PACKAGING) or ctx.index.has(*_DEPLOY_FILES) or _has_deploy_dir(ctx):
        yield ctx.ok("deployable-artifact", "operations",
                     "Project is packageable or deployable")
    else:
        yield ctx.fail("deployable-artifact", "operations",
                       "No packaging or deployment descriptor found",
                       remediation="Add packaging metadata (pyproject.toml/package.json/go.mod) or a Dockerfile.")


def _dockerfile_instructions(text: str) -> list[tuple[str, str]]:
    """Parse a Dockerfile into ``(INSTRUCTION, argument)`` pairs.

    Comments are dropped and backslash line continuations are joined, so an
    ``EXPOSE`` split across lines is still seen as a single instruction. This is
    deliberately not a full Dockerfile parser: it only needs to answer "which
    instructions are present, with roughly what arguments".
    """
    out: list[tuple[str, str]] = []
    buffer = ""
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.endswith("\\"):
            buffer += line[:-1].strip() + " "
            continue
        line = (buffer + line).strip()
        buffer = ""
        parts = line.split(None, 1)
        if not parts:
            continue
        out.append((parts[0].upper(), parts[1].strip() if len(parts) > 1 else ""))
    if buffer.strip():
        parts = buffer.strip().split(None, 1)
        if parts:
            out.append((parts[0].upper(), parts[1].strip() if len(parts) > 1 else ""))
    return out


def _serves_traffic(instructions: list[tuple[str, str]]) -> bool:
    """Whether the image looks like a long-running service.

    ``EXPOSE`` is the signal. A container that publishes a port is something an
    orchestrator keeps alive and routes traffic to, which is exactly the case a
    healthcheck exists to serve.
    """
    return any(name == "EXPOSE" and arg for name, arg in instructions)


@check("dockerfile-healthcheck", "operations")
def dockerfile_healthcheck(ctx: CheckContext) -> Iterable[Finding]:
    if not ctx.enabled("dockerfile-healthcheck", OFF):
        return
    dockerfile = ctx.index.find("Dockerfile")
    if not dockerfile:
        # Inert when there is no Dockerfile to evaluate.
        return
    text = ctx.index.read_text(dockerfile)
    instructions = _dockerfile_instructions(text)

    if any(name == "HEALTHCHECK" for name, _ in instructions):
        yield ctx.ok("dockerfile-healthcheck", "operations",
                     "Dockerfile declares a HEALTHCHECK")
        return

    if not _serves_traffic(instructions):
        # Inert for CLI and batch images. Docker only runs a HEALTHCHECK while a
        # container is alive, so for an image that does its work and exits there
        # is nothing to probe. Demanding one here would push people to write a
        # healthcheck that satisfies the rule while telling an operator nothing
        # true -- the opposite of what this standard is for.
        return

    yield ctx.fail("dockerfile-healthcheck", "operations",
                   "Dockerfile exposes a port but declares no HEALTHCHECK",
                   path=dockerfile.relpath,
                   remediation=("Add a HEALTHCHECK that probes a liveness endpoint, so an "
                                "orchestrator can tell a hung container from a healthy one."))
