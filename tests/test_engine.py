from helpers import make_good_repo, write

from deval.engine import scan


def test_good_repo_passes_gate(tmp_path):
    make_good_repo(tmp_path)
    result = scan(str(tmp_path), run_integrations=False)
    assert result.passed_gate, result.gate_reasons
    assert result.overall_score >= 85
    assert result.grade[0] in {"A", "B"}


def test_empty_repo_fails_on_missing_essentials(tmp_path):
    write(tmp_path, "main.py", "print('hi')\n")
    result = scan(str(tmp_path), run_integrations=False)
    failed_rules = {f.rule_id for f in result.failed_findings}
    assert "require-readme" in failed_rules
    assert "require-license" in failed_rules
    assert not result.passed_gate


def test_determinism(tmp_path):
    make_good_repo(tmp_path)
    a = scan(str(tmp_path), run_integrations=False).to_dict()
    b = scan(str(tmp_path), run_integrations=False).to_dict()
    a.pop("generated_at"); b.pop("generated_at")
    assert a == b


def test_secret_detection(tmp_path):
    make_good_repo(tmp_path)
    write(tmp_path, "src/p/leak.py", "AWS_KEY = 'AKIA1234567890ABCDEF'\n")
    result = scan(str(tmp_path), run_integrations=False)
    assert any(f.rule_id == "no-hardcoded-secrets" and not f.passed for f in result.findings)


def test_placeholder_secret_ignored(tmp_path):
    make_good_repo(tmp_path)
    write(tmp_path, "src/p/ok.py", "password = os.environ['PW']\n")
    result = scan(str(tmp_path), run_integrations=False)
    secret_fail = [f for f in result.findings if f.rule_id == "no-hardcoded-secrets" and not f.passed]
    assert not secret_fail


def test_layering_violation(tmp_path):
    make_good_repo(tmp_path)
    write(tmp_path, "src/p/user_controller.py", "from p.user_repository import UserRepository\n")
    write(tmp_path, "src/p/user_repository.py", "class UserRepository: pass\n")
    from deval.config import load_config
    (tmp_path / ".deval.yml").write_text("extends:\n  - deval/strict\n", encoding="utf-8")
    result = scan(str(tmp_path), config=load_config(tmp_path), run_integrations=False)
    assert any(f.rule_id == "respect-layering" and not f.passed for f in result.findings)


def test_config_can_disable_rule(tmp_path):
    write(tmp_path, "main.py", "print(1)\n")
    (tmp_path / ".deval.yml").write_text(
        "extends:\n  - deval/recommended\nrules:\n  require-readme: off\n", encoding="utf-8")
    result = scan(str(tmp_path), run_integrations=False)
    assert not any(f.rule_id == "require-readme" for f in result.findings)


def test_policy_rule_opt_in(tmp_path):
    make_good_repo(tmp_path)
    (tmp_path / ".deval.yml").write_text(
        "extends:\n  - deval/recommended\nrules:\n  require-editorconfig: error\n", encoding="utf-8")
    result = scan(str(tmp_path), run_integrations=False)
    # require-editorconfig has no check implementation yet; enabling it should not crash,
    # and the scan must still complete deterministically.
    assert result.overall_score >= 0
