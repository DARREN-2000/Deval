"""Product-contract tests for the Deval preflight."""

from __future__ import annotations

from helpers import make_good_repo, write

from deval import cli
from deval.doctor import diagnose
from deval.rules_doc import RULE_DOCS


def test_doctor_reports_resolved_repository(tmp_path):
    make_good_repo(tmp_path)
    write(tmp_path, ".deval.yml", "extends:\n  - deval/recommended\n  - deval/python\n")
    report = diagnose(str(tmp_path))
    assert report.ok
    assert report.catalog["total"] == report.catalog["coded"]
    assert report.catalog["total"] == report.catalog["documented"]
    assert "Python" in report.detected
    assert "deval/python" in report.standards
    assert report.enabled_rules > 0


def test_doctor_fails_invalid_config(tmp_path):
    make_good_repo(tmp_path)
    write(tmp_path, ".deval.yml", "rules:\n  require-readmee: critical\n")
    report = diagnose(str(tmp_path))
    assert not report.ok
    assert any(i.field == "rules" for i in report.errors)


def test_doctor_fails_required_missing_integration(tmp_path):
    make_good_repo(tmp_path)
    write(tmp_path, ".deval.yml", "integrations:\n  tool-that-does-not-exist: on\n")
    # Unknown integrations are warnings because plugins may provide them; use a
    # known applicable binary whose absence is deterministic in the test env.
    write(tmp_path, ".deval.yml", "integrations:\n  semgrep: on\n")
    report = diagnose(str(tmp_path))
    semgrep = next(i for i in report.integrations if i.name == "semgrep")
    if not semgrep.available:
        assert not report.ok
        assert semgrep.status == "missing"


def test_every_rule_renders_all_teaching_sections():
    for rule_id, doc in RULE_DOCS.items():
        rendered = doc.render()
        for heading in ("Problem", "Why", "Example", "Fix", "References"):
            assert f"\n{heading}\n" in "\n" + rendered, (rule_id, heading)


def test_doctor_cli_text_and_json(tmp_path):
    make_good_repo(tmp_path)
    assert cli.main(["doctor", str(tmp_path)]) == 0
    assert cli.main(["doctor", str(tmp_path), "--json"]) == 0
