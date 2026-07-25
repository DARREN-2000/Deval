"""Tests for the v0.2.0 platform capabilities.

Profiles, structured rule docs, suppressions, baselines, autofix, incremental
review, monorepo, badges, architecture graph, XML output, benchmark, plugins,
and the Rule SDK. Every test is deterministic and offline.

IMPORTANT: any rule loaded here persists in the process-global registry, so the
test plugin below is inert unless a unique marker file is present. This keeps
other tests' scores unchanged.
"""


from helpers import make_good_repo, write

from deval.config import load_config
from deval.engine import scan
from deval.model import Severity
from deval.reporters import FORMATS, render
from deval.standards import PROFILES, STANDARDS, list_standards

# --- 1. Profiles -----------------------------------------------------------

def test_profiles_are_registered():
    for name in PROFILES:
        assert f"deval/{name}" in STANDARDS
        assert name in STANDARDS
    assert len(list_standards()) >= 10


def test_profile_changes_severities(tmp_path):
    make_good_repo(tmp_path)
    base = load_config(str(tmp_path))
    assert base.rules.get("require-opentelemetry") == Severity.OFF
    backend = load_config(str(tmp_path), profiles=["backend"])
    assert backend.rules.get("require-opentelemetry") != Severity.OFF
    assert backend.rules.get("no-direct-sql") == Severity.ERROR
    assert backend.standard == "deval/backend"


def test_user_rules_win_over_profile(tmp_path):
    make_good_repo(tmp_path)
    write(tmp_path, ".deval.yml",
          "extends:\n  - deval/recommended\nrules:\n  no-direct-sql: off\n")
    cfg = load_config(str(tmp_path), profiles=["backend"])
    # backend sets no-direct-sql=error, but explicit user rule turns it off.
    assert cfg.rules.get("no-direct-sql") == Severity.OFF


# --- 2 & 13. Rule documentation / explain ----------------------------------

def test_rule_docs_are_structured():
    from deval.rules_doc import RULE_DOCS, explain
    doc = RULE_DOCS["require-readme"]
    assert doc.description and doc.why and doc.fix
    rendered = explain("require-readme")
    # Every finding teaches with the same five sections.
    for section in ("Problem", "Why", "Example", "Fix", "References"):
        assert section in rendered
    # The stable DV code and dimension label are part of the rendered doc.
    assert "DV1001" in rendered
    assert "Repository" in rendered
    assert explain("does-not-exist") is None


# --- 12. Suppressions ------------------------------------------------------

def test_file_suppression(tmp_path):
    write(tmp_path, "main.py", "print(1)\n")
    write(tmp_path, "deval-ignore.yml", "ignore:\n  - require-readme\n")
    result = scan(str(tmp_path), run_integrations=False)
    failed = {f.rule_id for f in result.failed_findings}
    assert "require-readme" not in failed
    assert result.suppressed >= 1


def test_inline_suppression(tmp_path):
    write(tmp_path, "README.md", "# P\n\n## Installation\n\n## Usage\n\n## License\n")
    write(tmp_path, "src/app.py", 'API_KEY = "AKIA1234567890ABCDEF"  # deval-ignore no-hardcoded-secrets\n')
    result = scan(str(tmp_path), run_integrations=False)
    failed = {f.rule_id for f in result.failed_findings}
    assert "no-hardcoded-secrets" not in failed


# --- 4. Baselines ----------------------------------------------------------

def test_baseline_hides_existing_violations(tmp_path):
    write(tmp_path, "main.py", "print(1)\n")
    from deval.baseline import create_baseline, load_baseline
    first = scan(str(tmp_path), run_integrations=False)
    assert first.failed_findings
    create_baseline(first, str(tmp_path))
    fps = load_baseline(str(tmp_path))
    assert fps
    second = scan(str(tmp_path), run_integrations=False, baseline=fps)
    assert second.baselined > 0
    assert len(second.failed_findings) == 0


# --- 5. Autofix ------------------------------------------------------------

def test_autofix_creates_missing_files(tmp_path):
    write(tmp_path, "README.md", "# P\n\n## Installation\n\n## Usage\n\n## License\n")
    write(tmp_path, "src/app.py", "def f():\n    return 1\n")
    from deval.fix import apply_fixes, plan_fixes
    result = scan(str(tmp_path), run_integrations=False)
    actions = plan_fixes(result)
    rule_ids = {a.rule_id for a in actions}
    assert "require-license" in rule_ids
    # dry run writes nothing
    apply_fixes(actions, str(tmp_path), dry_run=True)
    assert not (tmp_path / "LICENSE").exists()
    # real run creates the file
    written = apply_fixes(actions, str(tmp_path), dry_run=False)
    assert "LICENSE" in written
    assert (tmp_path / "LICENSE").exists()


# --- 6. Incremental review -------------------------------------------------

def test_incremental_filters_to_changed_files(tmp_path):
    write(tmp_path, "README.md", "# P\n\n## Installation\n\n## Usage\n\n## License\n")
    write(tmp_path, "src/clean.py", "def f():\n    return 1\n")
    write(tmp_path, "src/dirty.py", 'API_KEY = "AKIA1234567890ABCDEF"\n')
    full = scan(str(tmp_path), run_integrations=False)
    changed = scan(str(tmp_path), run_integrations=False, changed_files={"src/clean.py"})
    # A finding located on dirty.py should be excluded from the changed set.
    dirty_full = [f for f in full.findings if f.path == "src/dirty.py"]
    dirty_changed = [f for f in changed.findings if f.path == "src/dirty.py"]
    assert dirty_full  # baseline: full scan sees dirty.py
    assert not dirty_changed


# --- 7. Monorepo -----------------------------------------------------------

def test_monorepo_detection_and_rollup(tmp_path):
    write(tmp_path, "apps/web/package.json", '{"name":"web"}\n')
    write(tmp_path, "services/api/pyproject.toml", "[project]\nname='api'\n")
    from deval.monorepo import detect_subprojects, render_monorepo, scan_monorepo
    subs = detect_subprojects(str(tmp_path))
    assert "apps/web" in subs and "services/api" in subs
    mr = scan_monorepo(str(tmp_path), run_integrations=False)
    assert len(mr.projects) == 2
    assert 0 <= mr.overall_score <= 100
    assert "Monorepo Health" in render_monorepo(mr)


# --- 10. Badge -------------------------------------------------------------

def test_badge_svg(tmp_path):
    make_good_repo(tmp_path)
    from deval.badge import markdown_snippet, render_svg
    result = scan(str(tmp_path), run_integrations=False)
    svg = render_svg(result)
    assert svg.startswith("<svg") and "engineering health" in svg
    assert result.grade in svg
    assert "![Engineering Health" in markdown_snippet(result)


# --- 16. Architecture graph ------------------------------------------------

def test_architecture_graph(tmp_path):
    write(tmp_path, "src/controllers/user_controller.py", "from services import user_service\n")
    write(tmp_path, "src/services/user_service.py", "from repositories import user_repo\n")
    write(tmp_path, "src/repositories/user_repo.py", "def get():\n    return 1\n")
    from deval.fsindex import build_index
    from deval.graph import render_graph
    index = build_index(str(tmp_path))
    mermaid = render_graph(index, fmt="mermaid")
    assert mermaid.startswith("```mermaid")
    assert "Controller" in mermaid and "Service" in mermaid and "Repository" in mermaid
    dot = render_graph(index, fmt="dot")
    assert "digraph" in dot


# --- 15. Multiple outputs (xml) --------------------------------------------

def test_xml_reporter(tmp_path):
    make_good_repo(tmp_path)
    assert "xml" in FORMATS
    result = scan(str(tmp_path), run_integrations=False)
    out = render("xml", result)
    assert out.startswith("<?xml")
    assert "<testsuites" in out
    assert 'overall_score=' in out


# --- 17. Benchmark ---------------------------------------------------------

def test_benchmark(tmp_path):
    make_good_repo(tmp_path)
    from deval.benchmark import REFERENCES, render_benchmark
    result = scan(str(tmp_path), run_integrations=False)
    out = render_benchmark(result)
    assert "fastapi" in out and "kubernetes" in out
    assert "Reference" in out
    assert set(REFERENCES) == {"fastapi", "kubernetes", "react", "langchain"}


# --- 8, 9, 19. Plugins + SDK + marketplace ---------------------------------

_TEST_PLUGIN = '''
from deval.sdk import rule, CheckContext, Finding

@rule("custom-needs-manifest", "documentation")
def check_manifest(ctx: CheckContext):
    # Inert unless a unique marker file is present (keeps other tests clean).
    if not ctx.index.has("SPECIAL_MARKER.txt"):
        return
    if ctx.index.has("MANIFEST.txt"):
        yield ctx.ok("custom-needs-manifest", "documentation", "manifest present")
    else:
        yield ctx.fail("custom-needs-manifest", "documentation",
                       "Missing MANIFEST.txt", remediation="Add MANIFEST.txt")
'''


def test_sdk_plugin_is_loaded_and_runs(tmp_path):
    write(tmp_path, "README.md", "# P\n\n## Installation\n\n## Usage\n\n## License\n")
    write(tmp_path, "SPECIAL_MARKER.txt", "trigger\n")
    write(tmp_path, ".deval/plugins/custom.py", _TEST_PLUGIN)
    result = scan(str(tmp_path), run_integrations=False)
    failed = {f.rule_id for f in result.failed_findings}
    assert "custom-needs-manifest" in failed


def test_marketplace_install(tmp_path):
    from deval.plugins import available_packs, install_pack
    packs = available_packs()
    assert "kubernetes" in packs and "react" in packs
    dest = tmp_path / ".deval" / "plugins"
    target = install_pack("kubernetes", str(dest))
    assert target.exists()
    assert target.name == "kubernetes.py"


# --- 20. One health score (serialization carries new fields) ---------------

def test_scan_result_serializes_new_fields(tmp_path):
    make_good_repo(tmp_path)
    result = scan(str(tmp_path), run_integrations=False)
    data = result.to_dict()
    assert "suppressed" in data and "baselined" in data
    assert isinstance(data["overall_score"], int)
