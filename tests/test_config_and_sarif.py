from deval.config import _mini_yaml, load_config
from deval.integrations.sarif import findings_from_sarif
from deval.model import Severity


def test_extends_and_override(tmp_path):
    (tmp_path / ".deval.yml").write_text(
        "extends:\n  - deval/recommended\n"
        "rules:\n  require-readme: warning\n  no-console-log: error\n"
        "weights:\n  security: 2.0\n"
        "thresholds:\n  min_score: 80\n  fail_on: warning\n",
        encoding="utf-8",
    )
    cfg = load_config(tmp_path)
    assert cfg.rules["require-readme"] == Severity.WARNING
    assert cfg.rules["no-console-log"] == Severity.ERROR
    assert cfg.weight_for("security") == 2.0
    assert cfg.thresholds.min_score == 80
    assert cfg.thresholds.fail_on == Severity.WARNING


def test_default_config_is_recommended(tmp_path):
    cfg = load_config(tmp_path)
    assert cfg.rules["require-readme"] == Severity.ERROR
    assert cfg.rules["require-opentelemetry"] == Severity.OFF


def test_mini_yaml_parses_lists_and_maps():
    data = _mini_yaml("extends:\n  - a\n  - b\nrules:\n  x: error\n")
    assert data["extends"] == ["a", "b"]
    assert data["rules"]["x"] == "error"


def test_sarif_ingest():
    doc = {
        "runs": [{
            "tool": {"driver": {"rules": [{"id": "R1",
                "defaultConfiguration": {"level": "error"}}]}},
            "results": [{
                "ruleId": "R1",
                "message": {"text": "bad thing"},
                "locations": [{"physicalLocation": {
                    "artifactLocation": {"uri": "a.py"},
                    "region": {"startLine": 5}}}],
            }],
        }]
    }
    findings = findings_from_sarif(doc, "trivy", "security")
    assert len(findings) == 1
    assert findings[0].severity == Severity.ERROR
    assert findings[0].path == "a.py" and findings[0].line == 5
