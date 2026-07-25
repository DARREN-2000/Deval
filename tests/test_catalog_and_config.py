"""Tests for the rule catalog (`deval rules`) and config validation
(`deval config`).
"""

from __future__ import annotations

from helpers import make_good_repo, write

from deval import cli
from deval.catalog import all_rule_ids, build_catalog, catalog_stats
from deval.config_lint import validate_config

# --- catalog ---------------------------------------------------------------

def test_catalog_is_a_complete_public_contract():
    catalog = build_catalog()
    assert catalog
    assert all(r.code for r in catalog)
    assert all(r.documented for r in catalog)
    assert len({r.code for r in catalog}) == len(catalog)


def test_catalog_classifies_scope_dimension_and_code():
    by_id = {r.rule_id: r for r in build_catalog()}
    readme = by_id["require-readme"]
    assert readme.scope == "universal"
    assert readme.code == "DV1001"
    assert readme.dimension == "repository"
    assert readme.documented
    auth = by_id["fastapi-endpoint-auth"]
    assert auth.scope == "domain"
    assert auth.dimension == "security"


def test_all_rule_ids_sorted_and_substantial():
    ids = all_rule_ids()
    assert ids == sorted(ids)
    assert "require-readme" in ids
    assert len(ids) > 50


def test_catalog_stats_add_up():
    stats = catalog_stats()
    assert stats["total"] == stats["universal"] + stats["domain"]
    assert stats["documented"] >= 1
    assert stats["coded"] >= 1
    assert stats["documented"] == stats["total"]
    assert stats["coded"] == stats["total"]


# --- config validation -----------------------------------------------------

def test_valid_config_has_no_errors(tmp_path):
    write(tmp_path, ".deval.yml",
          "version: 1\n"
          "extends:\n  - deval/recommended\n  - deval/python\n"
          "rules:\n  require-readme: error\n  require-changelog: off\n"
          "weights:\n  security: 1.5\n"
          "thresholds:\n  min_score: 80\n  fail_on: error\n")
    report = validate_config(str(tmp_path))
    assert report.ok
    assert report.errors == []


def test_unknown_rule_flagged_with_suggestion(tmp_path):
    write(tmp_path, ".deval.yml", "rules:\n  require-readmee: error\n")
    report = validate_config(str(tmp_path))
    assert not report.ok
    joined = " ".join(i.message for i in report.errors)
    assert "require-readmee" in joined
    assert "require-readme" in joined  # did-you-mean suggestion


def test_invalid_severity_flagged(tmp_path):
    write(tmp_path, ".deval.yml", "rules:\n  require-readme: critical\n")
    report = validate_config(str(tmp_path))
    assert not report.ok
    assert any("invalid severity" in i.message for i in report.errors)


def test_unknown_standard_flagged(tmp_path):
    write(tmp_path, ".deval.yml", "extends:\n  - deval/pythonn\n")
    report = validate_config(str(tmp_path))
    assert not report.ok
    assert any("unknown standard" in i.message for i in report.errors)


def test_unknown_weight_dimension_is_warning(tmp_path):
    write(tmp_path, ".deval.yml", "weights:\n  securty: 2\n")
    report = validate_config(str(tmp_path))
    assert any(i.level == "warning" and "securty" in i.message for i in report.issues)


def test_org_standard_reference_accepted(tmp_path):
    write(tmp_path, ".deval/standards/company/backend.yml",
          "extends: [deval/recommended]\nrules:\n  require-changelog: error\n")
    write(tmp_path, ".deval.yml", "extends:\n  - deval/recommended\n  - company/backend\n")
    report = validate_config(str(tmp_path))
    assert report.ok


def test_dv_code_as_rule_key_accepted(tmp_path):
    write(tmp_path, ".deval.yml", "rules:\n  DV1001: warning\n")
    report = validate_config(str(tmp_path))
    assert report.ok


def test_missing_config_is_warning_not_error(tmp_path):
    make_good_repo(tmp_path)
    report = validate_config(str(tmp_path))
    assert report.ok
    assert any(i.level == "warning" for i in report.issues)


def test_unknown_top_level_key_is_warning(tmp_path):
    write(tmp_path, ".deval.yml", "rulez:\n  require-readme: error\n")
    report = validate_config(str(tmp_path))
    assert any(i.level == "warning" and "rulez" in i.message for i in report.issues)


# --- CLI smoke -------------------------------------------------------------

def test_cli_rules_runs():
    assert cli.main(["rules"]) == 0


def test_cli_rules_filtered_json_runs():
    assert cli.main(["rules", "--json", "--scope", "domain", "--dimension", "security"]) == 0


def test_cli_rules_under_standard_runs():
    assert cli.main(["rules", "--standard", "deval/fastapi"]) == 0


def test_cli_config_ok(tmp_path):
    write(tmp_path, ".deval.yml", "extends:\n  - deval/recommended\n")
    assert cli.main(["config", str(tmp_path)]) == 0


def test_cli_config_detects_error(tmp_path):
    write(tmp_path, ".deval.yml", "rules:\n  bogus-rule: error\n")
    assert cli.main(["config", str(tmp_path)]) == 1


def test_cli_config_json_runs(tmp_path):
    write(tmp_path, ".deval.yml", "extends:\n  - deval/recommended\n")
    assert cli.main(["config", str(tmp_path), "--json"]) == 0
