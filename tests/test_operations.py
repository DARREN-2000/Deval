"""Tests for the Operations dimension.

The healthcheck rule is the interesting one: it must stay inert for CLI and
batch images while still catching a service image that forgets a healthcheck.
That scoping is the whole point of the rule, so both sides are tested here.
"""

from __future__ import annotations

from helpers import make_good_repo, write

from deval.checks.operations import _dockerfile_instructions, _serves_traffic
from deval.engine import scan

_CLI_DOCKERFILE = (
    "FROM python:3.13-slim\n"
    "COPY . /app\n"
    "RUN pip install /app\n"
    "WORKDIR /repo\n"
    'ENTRYPOINT ["mytool"]\n'
    'CMD ["scan", "."]\n'
)

_SERVICE_DOCKERFILE = (
    "FROM python:3.13-slim\n"
    "COPY . /app\n"
    "EXPOSE 8000\n"
    'CMD ["uvicorn", "app:app"]\n'
)


def _healthcheck_findings(result):
    return [f for f in result.findings if f.rule_id == "dockerfile-healthcheck"]


# --- Dockerfile parsing -----------------------------------------------------

def test_parser_skips_comments_and_blank_lines():
    text = "# a comment\n\nFROM alpine\n   # indented comment\nEXPOSE 80\n"
    assert _dockerfile_instructions(text) == [("FROM", "alpine"), ("EXPOSE", "80")]


def test_parser_joins_line_continuations():
    text = "RUN apt-get update \\\n    && apt-get install -y curl\nEXPOSE 8080\n"
    instructions = _dockerfile_instructions(text)
    names = [name for name, _ in instructions]
    assert names == ["RUN", "EXPOSE"]
    assert "apt-get install -y curl" in instructions[0][1]


def test_parser_uppercases_instruction_names():
    assert _dockerfile_instructions("from alpine\nexpose 80\n") == [
        ("FROM", "alpine"),
        ("EXPOSE", "80"),
    ]


def test_serves_traffic_requires_a_port():
    assert _serves_traffic(_dockerfile_instructions(_SERVICE_DOCKERFILE)) is True
    assert _serves_traffic(_dockerfile_instructions(_CLI_DOCKERFILE)) is False
    # A bare EXPOSE with no port number is not evidence of a service.
    assert _serves_traffic([("EXPOSE", "")]) is False


# --- rule behaviour ---------------------------------------------------------

def test_healthcheck_inert_for_cli_image(tmp_path):
    """A CLI image exits immediately, so Docker would never run a healthcheck."""
    make_good_repo(tmp_path)
    write(tmp_path, "Dockerfile", _CLI_DOCKERFILE)
    result = scan(str(tmp_path), run_integrations=False, load_plugins=False)
    assert _healthcheck_findings(result) == []


def test_healthcheck_fails_for_service_without_one(tmp_path):
    make_good_repo(tmp_path)
    write(tmp_path, "Dockerfile", _SERVICE_DOCKERFILE)
    result = scan(str(tmp_path), run_integrations=False, load_plugins=False)
    findings = _healthcheck_findings(result)
    assert len(findings) == 1
    assert findings[0].passed is False
    assert findings[0].path == "Dockerfile"


def test_healthcheck_passes_for_service_with_one(tmp_path):
    make_good_repo(tmp_path)
    write(tmp_path, "Dockerfile",
          _SERVICE_DOCKERFILE + "HEALTHCHECK CMD curl -f http://localhost:8000/health || exit 1\n")
    result = scan(str(tmp_path), run_integrations=False, load_plugins=False)
    findings = _healthcheck_findings(result)
    assert len(findings) == 1
    assert findings[0].passed is True


def test_healthcheck_passes_for_cli_image_that_declares_one(tmp_path):
    """Inertness must not suppress a healthcheck someone deliberately added."""
    make_good_repo(tmp_path)
    write(tmp_path, "Dockerfile", _CLI_DOCKERFILE + "HEALTHCHECK CMD mytool --version || exit 1\n")
    result = scan(str(tmp_path), run_integrations=False, load_plugins=False)
    findings = _healthcheck_findings(result)
    assert len(findings) == 1
    assert findings[0].passed is True


def test_healthcheck_inert_without_a_dockerfile(tmp_path):
    make_good_repo(tmp_path)
    result = scan(str(tmp_path), run_integrations=False, load_plugins=False)
    assert _healthcheck_findings(result) == []


# --- deployable artifact ----------------------------------------------------

def test_deployable_artifact_passes_with_packaging(tmp_path):
    make_good_repo(tmp_path)
    result = scan(str(tmp_path), run_integrations=False, load_plugins=False)
    findings = [f for f in result.findings if f.rule_id == "deployable-artifact"]
    assert findings and findings[0].passed is True
