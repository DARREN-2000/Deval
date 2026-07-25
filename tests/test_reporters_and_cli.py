import json

from helpers import make_good_repo

from deval.cli import main
from deval.engine import scan
from deval.reporters import render


def test_all_reporters_render(tmp_path):
    make_good_repo(tmp_path)
    result = scan(str(tmp_path), run_integrations=False)
    for fmt in ("terminal", "json", "sarif", "html", "markdown"):
        out = render(fmt, result, color=False)
        assert out and isinstance(out, str)
    data = json.loads(render("json", result))
    assert data["overall_score"] == result.overall_score
    assert "summary" in data
    sarif = json.loads(render("sarif", result))
    assert sarif["version"] == "2.1.0"
    html = render("html", result)
    assert "<!doctype html>" in html and "Deval" in html


def test_cli_scan_exit_codes(tmp_path, capsys):
    make_good_repo(tmp_path)
    code = main(["scan", str(tmp_path), "--no-integrations", "--no-color"])
    assert code == 0
    out = capsys.readouterr().out
    assert "PASS" in out


def test_cli_scan_fails_empty(tmp_path):
    (tmp_path / "main.py").write_text("print(1)\n")
    code = main(["scan", str(tmp_path), "--no-integrations", "--no-color"])
    assert code == 1


def test_cli_init_and_standards(tmp_path):
    assert main(["init", str(tmp_path)]) == 0
    assert (tmp_path / ".deval.yml").exists()
    assert main(["standards"]) == 0
    assert main(["explain", "require-readme"]) == 0
    assert main(["explain", "nope"]) == 2


def test_cli_json_output_file(tmp_path):
    make_good_repo(tmp_path)
    out = tmp_path / "deval.json"
    main(["scan", str(tmp_path), "-f", "json", "-o", str(out), "--no-integrations"])
    data = json.loads(out.read_text())
    assert "categories" in data
