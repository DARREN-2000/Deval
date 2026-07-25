"""Tests for Domain Standards: detection, inert-until-detected, auto-apply,
universal-vs-domain classification, and organization standards.
"""

from __future__ import annotations

from helpers import make_good_repo, write

from deval import detect
from deval.config import load_config
from deval.engine import scan
from deval.fsindex import build_index
from deval.model import Severity
from deval.standards import DOMAIN_RULES, UNIVERSAL_RULES, is_universal

_DOMAIN_PREFIXES = (
    "fastapi-", "react-", "k8s-", "terraform-", "ml-", "llm-",
    "microservices-", "data-", "docker-", "security-sbom", "security-signed",
)


def _domain_findings(result):
    return [f for f in result.findings
            if any(f.rule_id.startswith(p) for p in _DOMAIN_PREFIXES)]


def _write_fastapi_repo(root):
    make_good_repo(root)
    write(root, "requirements.txt", "fastapi\nuvicorn\n")
    write(root, "app/main.py",
          "from fastapi import FastAPI\n"
          "app = FastAPI()\n\n"
          "@app.get('/items')\n"
          "def items():\n"
          "    return []\n")


def _write_k8s_repo(root):
    make_good_repo(root)
    write(root, "deploy/app.yaml",
          "apiVersion: apps/v1\n"
          "kind: Deployment\n"
          "spec:\n"
          "  template:\n"
          "    spec:\n"
          "      containers:\n"
          "        - name: web\n"
          "          image: myapp:latest\n")


# --- detection --------------------------------------------------------------

def test_detects_fastapi(tmp_path):
    _write_fastapi_repo(tmp_path)
    index = build_index(str(tmp_path))
    keys = {d.key for d in detect.detect(index)}
    assert "python" in keys
    assert "fastapi" in keys


def test_detects_kubernetes(tmp_path):
    _write_k8s_repo(tmp_path)
    index = build_index(str(tmp_path))
    keys = {d.key for d in detect.detect(index)}
    assert "kubernetes" in keys


def test_plain_repo_detects_nothing_domain(tmp_path):
    make_good_repo(tmp_path)
    index = build_index(str(tmp_path))
    keys = {d.key for d in detect.detect(index)}
    # A plain repo has no framework/infra signals.
    assert "fastapi" not in keys
    assert "kubernetes" not in keys


# --- inert until detected ---------------------------------------------------

def test_domain_rules_are_inert_on_plain_repo(tmp_path):
    make_good_repo(tmp_path)
    result = scan(str(tmp_path))
    assert _domain_findings(result) == []


# --- auto-apply -------------------------------------------------------------

def test_fastapi_domain_rules_fire_when_detected(tmp_path):
    _write_fastapi_repo(tmp_path)
    result = scan(str(tmp_path))
    fired = {f.rule_id for f in _domain_findings(result)}
    assert "fastapi-endpoint-auth" in fired
    # This minimal app has no auth/health, so those must fail.
    failed = {f.rule_id for f in _domain_findings(result) if not f.passed}
    assert "fastapi-endpoint-auth" in failed
    assert "fastapi-health-endpoint" in failed


def test_autodetect_records_applied_standards(tmp_path):
    _write_fastapi_repo(tmp_path)
    result = scan(str(tmp_path))
    assert "deval/recommended" in result.applied_standards
    assert "deval/fastapi" in result.applied_standards
    assert "FastAPI" in result.detected_technologies


def test_autodetect_can_be_disabled(tmp_path):
    _write_fastapi_repo(tmp_path)
    write(tmp_path, ".deval.yml", "autodetect: false\nextends: [deval/recommended]\n")
    result = scan(str(tmp_path))
    assert result.detected_technologies == []
    assert _domain_findings(result) == []


# --- universal vs domain ----------------------------------------------------

def test_universal_vs_domain_classification():
    assert is_universal("require-readme")
    assert is_universal("require-license")
    assert not is_universal("fastapi-endpoint-auth")
    assert not is_universal("k8s-non-root")
    # The two sets must be disjoint.
    assert not (set(UNIVERSAL_RULES) & set(DOMAIN_RULES))


# --- organization standards -------------------------------------------------

def test_org_standard_resolves_from_repo(tmp_path):
    write(tmp_path, ".deval/standards/company/backend.yml",
          "extends: [deval/recommended]\nrules:\n  require-changelog: error\n")
    write(tmp_path, ".deval.yml",
          "autodetect: false\nextends: [deval/recommended, company/backend]\n")
    cfg = load_config(str(tmp_path))
    assert cfg.severity_for("require-changelog", Severity.OFF) == Severity.ERROR


def test_repository_override_beats_detected_domain(tmp_path):
    _write_fastapi_repo(tmp_path)
    # Repo explicitly turns a fastapi domain rule off; override must win even
    # though auto-detection would otherwise enable it.
    write(tmp_path, ".deval.yml", "rules:\n  fastapi-endpoint-auth: off\n")
    result = scan(str(tmp_path))
    fired = {f.rule_id for f in _domain_findings(result)}
    assert "fastapi-endpoint-auth" not in fired


def test_detectable_keys_have_standards():
    from deval.standards import STANDARDS
    for key in detect.detectable_keys():
        assert f"deval/{key}" in STANDARDS, key
