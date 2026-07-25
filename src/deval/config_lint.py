"""Configuration validation for ``.deval.yml``.

Deval merges unknown configuration keys silently by design (forward
compatibility). The downside is that a typo such as ``require-readmee: error``
simply does nothing — the gate you *think* you configured is not the gate you
get. ``deval config`` closes that gap: it reads your configuration exactly the
way the engine does and reports mistakes with actionable, "did you mean"
suggestions before they cost you a bad merge.

This protects the integrity of the *standard itself*, which is the first-class
artifact in Deval's Standard → Evaluation → Policy → Integrations ordering.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from pathlib import Path

from .catalog import all_rule_ids
from .codes import RULE_BY_CODE
from .config import CONFIG_FILENAMES, _load_org_standard, _load_yaml
from .model import CATEGORIES
from .standards import STANDARDS

# Severity spellings the engine accepts (Severity.coerce aliases included).
_VALID_SEVERITIES = {
    "error", "warning", "info", "off",
    "true", "false", "on", "enabled", "disabled", "none", "warn", "err",
}
_VALID_INTEGRATION_MODES = {"auto", "on", "off", "true", "false", "no", "yes"}
_KNOWN_TOP_LEVEL = {
    "version", "extends", "rules", "weights", "thresholds",
    "ignore", "integrations", "autodetect", "standard",
}


@dataclass
class Issue:
    level: str    # "error" | "warning"
    field: str
    message: str

    def to_dict(self) -> dict:
        return {"level": self.level, "field": self.field, "message": self.message}


@dataclass
class ValidationReport:
    config_path: str | None
    issues: list[Issue] = field(default_factory=list)

    def add(self, level: str, field_name: str, message: str) -> None:
        self.issues.append(Issue(level=level, field=field_name, message=message))

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.level == "error"]

    @property
    def warnings(self) -> list[Issue]:
        return [i for i in self.issues if i.level == "warning"]

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict:
        return {
            "schema_version": 1,
            "ok": self.ok,
            "config_path": self.config_path,
            "errors": len(self.errors),
            "warnings": len(self.warnings),
            "issues": [issue.to_dict() for issue in self.issues],
        }


def find_config(repo_root: str, explicit: str | None = None) -> Path | None:
    if explicit:
        p = Path(explicit)
        return p if p.exists() else None
    root = Path(repo_root)
    for name in CONFIG_FILENAMES:
        candidate = root / name
        if candidate.exists():
            return candidate
    return None


def _suggest(name, candidates) -> str:
    matches = difflib.get_close_matches(str(name), [str(c) for c in candidates], n=1, cutoff=0.6)
    return f" (did you mean '{matches[0]}'?)" if matches else ""


def _is_known_standard(name: str, repo_root: str) -> bool:
    key = name.split("/", 1)[-1] if name.startswith("deval/") else name
    if name in STANDARDS or key in STANDARDS:
        return True
    return _load_org_standard(name, repo_root) is not None


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate_config(repo_root: str, config_path: str | None = None) -> ValidationReport:
    cfg_file = find_config(repo_root, config_path)
    report = ValidationReport(config_path=str(cfg_file) if cfg_file else None)

    if cfg_file is None:
        report.add("warning", "config",
                   "no .deval.yml found; the repository would be evaluated against deval/recommended.")
        return report

    try:
        text = Path(cfg_file).read_text(encoding="utf-8", errors="replace")
    except Exception as exc:  # pragma: no cover - unusual IO failure
        report.add("error", "config", f"could not read file: {exc}")
        return report

    data = _load_yaml(text)
    if not isinstance(data, dict):
        report.add("error", "config", "top-level configuration must be a mapping of key: value.")
        return report
    if not data:
        report.add("warning", "config", "configuration is empty; deval/recommended will be used.")
        return report

    for key in data:
        if key not in _KNOWN_TOP_LEVEL:
            report.add("warning", key, f"unknown top-level key '{key}'{_suggest(key, _KNOWN_TOP_LEVEL)}.")

    # extends -----------------------------------------------------------
    extends = data.get("extends")
    if extends is not None:
        if isinstance(extends, str):
            extends = [extends]
        if not isinstance(extends, list):
            report.add("error", "extends", "must be a list of standard names.")
        else:
            std_candidates = [k for k in STANDARDS if k.startswith("deval/")]
            for name in extends:
                if not _is_known_standard(str(name), repo_root):
                    report.add("error", "extends",
                               f"unknown standard '{name}'{_suggest(name, std_candidates)}.")

    # rules -------------------------------------------------------------
    rules = data.get("rules")
    if rules is not None:
        if not isinstance(rules, dict):
            report.add("error", "rules", "must be a mapping of rule -> severity.")
        else:
            known_rules = set(all_rule_ids())
            rule_candidates = sorted(known_rules)
            for rid, value in rules.items():
                is_code = str(rid).upper() in RULE_BY_CODE
                if not is_code and str(rid) not in known_rules:
                    report.add("error", "rules",
                               f"unknown rule '{rid}'{_suggest(rid, rule_candidates)}.")
                    continue
                if str(value).strip().lower() not in _VALID_SEVERITIES:
                    report.add("error", "rules",
                               f"rule '{rid}' has invalid severity '{value}' "
                               f"(use error | warning | info | off).")

    # weights -----------------------------------------------------------
    weights = data.get("weights")
    if weights is not None:
        if not isinstance(weights, dict):
            report.add("error", "weights", "must be a mapping of dimension -> number.")
        else:
            for cat, value in weights.items():
                if cat not in CATEGORIES:
                    report.add("warning", "weights",
                               f"unknown dimension '{cat}'{_suggest(cat, CATEGORIES)}.")
                if not _is_number(value):
                    report.add("error", "weights",
                               f"weight for '{cat}' must be a number, got '{value}'.")

    # thresholds --------------------------------------------------------
    thresholds = data.get("thresholds")
    if thresholds is not None:
        if not isinstance(thresholds, dict):
            report.add("error", "thresholds", "must be a mapping.")
        else:
            known_th = {"min_score", "fail_on", "max_errors"}
            for k in thresholds:
                if k not in known_th:
                    report.add("warning", "thresholds", f"unknown key '{k}'{_suggest(k, known_th)}.")
            min_score = thresholds.get("min_score")
            if min_score is not None and (not _is_number(min_score) or not 0 <= min_score <= 100):
                report.add("error", "thresholds", f"min_score must be a number 0-100, got '{min_score}'.")
            fail_on = thresholds.get("fail_on")
            if fail_on is not None and str(fail_on).strip().lower() not in _VALID_SEVERITIES:
                report.add("error", "thresholds", f"fail_on has invalid severity '{fail_on}'.")
            max_errors = thresholds.get("max_errors")
            if max_errors is not None and (not isinstance(max_errors, int) or isinstance(max_errors, bool) or max_errors < 0):
                report.add("error", "thresholds", f"max_errors must be a non-negative integer, got '{max_errors}'.")

    # integrations ------------------------------------------------------
    integrations = data.get("integrations")
    if integrations is not None:
        if not isinstance(integrations, dict):
            report.add("error", "integrations", "must be a mapping of name -> mode.")
        else:
            try:
                from .integrations import default_integrations
                known = {i.name for i in default_integrations()}
            except Exception:
                known = set()
            for name, mode in integrations.items():
                if name != "*" and known and name not in known:
                    report.add("warning", "integrations",
                               f"unknown integration '{name}'{_suggest(name, known)}.")
                if str(mode).strip().lower() not in _VALID_INTEGRATION_MODES:
                    report.add("error", "integrations",
                               f"integration '{name}' has invalid mode '{mode}' (use auto | on | off).")

    # autodetect / ignore ----------------------------------------------
    autodetect = data.get("autodetect")
    if autodetect is not None and not isinstance(autodetect, bool):
        report.add("error", "autodetect", "must be true or false.")
    ignore = data.get("ignore")
    if ignore is not None and not isinstance(ignore, list):
        report.add("error", "ignore", "must be a list of glob patterns.")

    return report
