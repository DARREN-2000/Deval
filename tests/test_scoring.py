from deval.config import Config, Thresholds
from deval.model import Finding, Severity
from deval.scoring import _grade, compute_scores, evaluate_gate


def _f(category, passed, sev=Severity.ERROR, rule="r"):
    return Finding(rule_id=rule, category=category, passed=passed, message="m", severity=sev)


def test_perfect_repo_scores_100():
    findings = [_f("security", True), _f("testing", True)]
    _cats, overall, grade = compute_scores(findings, Config())
    assert overall == 100
    assert grade == "A+"


def test_error_penalizes_more_than_warning():
    err = compute_scores([_f("security", False, Severity.ERROR)], Config())[1]
    warn = compute_scores([_f("security", False, Severity.WARNING)], Config())[1]
    assert err < warn


def test_empty_categories_do_not_drag_score():
    _cats, overall, _ = compute_scores([_f("ci", True)], Config())
    assert overall == 100


def test_weights_shift_overall():
    findings = [_f("security", False, Severity.ERROR), _f("documentation", True)]
    base = compute_scores(findings, Config())[1]
    weighted = compute_scores(findings, Config(weights={"security": 5.0}))[1]
    assert weighted <= base


def test_grade_boundaries():
    assert _grade(97) == "A+"
    assert _grade(80) == "B"
    assert _grade(59) == "F"


def test_gate_fails_on_error():
    cfg = Config(thresholds=Thresholds(min_score=0, fail_on=Severity.ERROR))
    passed, reasons = evaluate_gate(100, [_f("security", False, Severity.ERROR)], cfg)
    assert not passed and reasons


def test_gate_passes_when_only_warnings_and_fail_on_error():
    cfg = Config(thresholds=Thresholds(min_score=0, fail_on=Severity.ERROR))
    passed, reasons = evaluate_gate(90, [_f("security", False, Severity.WARNING)], cfg)
    assert passed and not reasons


def test_gate_min_score():
    cfg = Config(thresholds=Thresholds(min_score=95, fail_on=Severity.OFF))
    passed, _reasons = evaluate_gate(80, [], cfg)
    assert not passed
