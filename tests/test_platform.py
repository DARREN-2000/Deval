"""Tests for the v0.3.0 platform concepts.

Engineering Dimensions, stable DV rule codes, clean-architecture verification,
the expanded standards catalog, explain-by-code, and the bare ``@rule`` SDK.
Every test is deterministic and offline.

NOTE (registry hygiene): any rule registered here persists in the process-
global registry, so the bare-``@rule`` sample below is inert unless a unique
marker file is present. That keeps unrelated repositories' scores unchanged.
"""

from helpers import make_good_repo, write

from deval.engine import scan

# --- Stable DV rule codes --------------------------------------------------

def test_rule_codes_roundtrip():
    from deval.codes import code_for, rule_for_code
    # The named examples the platform documents everywhere.
    assert code_for("require-readme") == "DV1001"
    assert code_for("tests-present") == "DV2004"
    assert code_for("require-security-policy") == "DV4011"
    # Reverse lookup is case-insensitive and inverts code_for.
    assert rule_for_code("DV1001") == "require-readme"
    assert rule_for_code("dv2004") == "tests-present"
    for rule_id in ("require-readme", "tests-present", "require-security-policy"):
        assert rule_for_code(code_for(rule_id)) == rule_id
    # Unknown inputs resolve to falsy, never raise.
    assert not rule_for_code("DV9999")
    assert not code_for("not-a-real-rule")


def test_findings_carry_codes(tmp_path):
    make_good_repo(tmp_path)
    result = scan(str(tmp_path), run_integrations=False)
    by_rule = {f.rule_id: f for f in result.findings}
    assert by_rule["require-readme"].code == "DV1001"
    # Codes also survive serialization.
    data = by_rule["require-readme"].to_dict()
    assert data["code"] == "DV1001"


# --- Engineering Dimensions ------------------------------------------------

def test_engineering_dimensions_present():
    from deval.dimensions import DIMENSIONS, label_for
    expected = {
        "architecture", "documentation", "testing", "security", "dependencies",
        "ci", "ownership", "maintainability", "observability", "operations",
        "compliance",
    }
    assert expected.issubset(set(DIMENSIONS))
    # CI carries its formal, human identity.
    assert label_for("ci") == "CI/CD"
    # Every dimension has a one-line charter.
    for key in expected:
        assert DIMENSIONS[key].charter


def test_category_scores_have_grades(tmp_path):
    make_good_repo(tmp_path)
    result = scan(str(tmp_path), run_integrations=False)
    scored = [c for c in result.categories if c.passed + c.failed > 0]
    assert scored
    for cat in scored:
        assert cat.grade  # e.g. A+, A, B ...
        assert cat.to_dict()["grade"] == cat.grade


# --- Clean architecture (first-class, both styles) -------------------------

def test_clean_architecture_violation_detected(tmp_path):
    # Domain must not depend outward on Infrastructure.
    write(tmp_path, "README.md", "# P\n\n## Installation\n\n## Usage\n\n## License\n")
    write(tmp_path, "src/domain/order.py", "from infrastructure.db import save\n")
    write(tmp_path, "src/application/place_order.py", "from domain.order import Order\n")
    write(tmp_path, "src/infrastructure/db.py", "def save():\n    return 1\n")
    result = scan(str(tmp_path), run_integrations=False)
    failed = {f.rule_id for f in result.failed_findings}
    assert "respect-clean-architecture" in failed


def test_clean_architecture_inert_without_layers(tmp_path):
    # A repo that is not organized into clean-arch layers must not be judged.
    make_good_repo(tmp_path)
    result = scan(str(tmp_path), run_integrations=False)
    rule_ids = {f.rule_id for f in result.findings}
    assert "respect-clean-architecture" not in rule_ids


def test_graph_renders_clean_style(tmp_path):
    write(tmp_path, "src/domain/order.py", "class Order:\n    pass\n")
    write(tmp_path, "src/application/place.py", "from domain.order import Order\n")
    write(tmp_path, "src/infrastructure/db.py", "from application.place import go\n")
    from deval.fsindex import build_index
    from deval.graph import render_graph
    mermaid = render_graph(build_index(str(tmp_path)), fmt="mermaid")
    assert "Domain" in mermaid and "Application" in mermaid and "Infrastructure" in mermaid


# --- Expanded standards catalog --------------------------------------------

def test_expanded_standards_and_profiles():
    from deval.standards import PROFILES, STANDARDS
    for name in ("minimal", "recommended", "strict", "enterprise", "startup",
                 "oss", "ml", "fastapi", "react", "kubernetes"):
        assert f"deval/{name}" in STANDARDS, name
    assert "fastapi" in PROFILES and "react" in PROFILES


# --- Explain by DV code ----------------------------------------------------

def test_cli_explain_by_code(capsys):
    from deval.cli import main
    assert main(["explain", "DV1001"]) == 0
    out = capsys.readouterr().out
    assert "require-readme" in out
    assert "Problem" in out and "Fix" in out


# --- Rule SDK: bare @rule --------------------------------------------------

def test_sdk_bare_rule_decorator(tmp_path):
    from deval.sdk import rule

    @rule
    def check_platform_marker(repo):
        # Inert unless a unique marker file is present (registry hygiene).
        if not repo.has("PLATFORM_MARKER.txt"):
            return None
        return repo.has("LICENSE") or "Missing LICENSE"

    write(tmp_path, "README.md", "# P\n\n## Installation\n\n## Usage\n\n## License\n")
    write(tmp_path, "PLATFORM_MARKER.txt", "x\n")
    result = scan(str(tmp_path), run_integrations=False)
    failed = {f.rule_id for f in result.failed_findings}
    # id inferred from the function name, with the check- prefix stripped.
    assert "platform-marker" in failed
