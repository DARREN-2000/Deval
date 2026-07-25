"""The scan pipeline: index -> native checks -> integrations -> dedupe -> score.

This is the orchestrator behind ``deval scan .``. Every stage is deterministic
and failure-isolated, so a broken check or a misbehaving external tool degrades
gracefully instead of taking down the whole scan.

The same pipeline powers advanced modes without forking logic:

* **Suppressions** always apply (``deval-ignore.yml`` and inline comments).
* **Baselines** (``--use-baseline``) hide pre-existing violations so only new
  problems fail the gate.
* **Incremental** (``deval review``) restricts findings to changed files.
* **Plugins** discovered in the repo/user plugin directories register extra
  rules before checks run.
"""

from __future__ import annotations

import datetime as _dt

from . import __version__
from .config import Config, load_config
from .fsindex import build_index
from .integrations import default_integrations
from .integrations.base import Integration
from .model import Finding, ScanResult, Severity
from .registry import CheckContext, load_builtin_checks, run_checks
from .scoring import compute_scores, evaluate_gate

_SEVERITY_ORDER = {Severity.ERROR: 0, Severity.WARNING: 1, Severity.INFO: 2, Severity.OFF: 3}


def _dedupe(findings: list[Finding]) -> tuple[list[Finding], int]:
    """Remove duplicate violations reported by more than one source.

    Two failing findings are duplicates when they share rule id, path and line.
    Native findings win over external ones so remediation text is preserved.
    """
    seen = {}
    removed = 0
    result: list[Finding] = []
    for f in findings:
        if f.passed:
            result.append(f)
            continue
        key = (f.rule_id, f.path or "", f.line or 0, f.message)
        if key in seen:
            removed += 1
            continue
        # Also dedupe across sources on rule+path+line regardless of message.
        loc_key = (f.rule_id, f.path or "", f.line or 0)
        if loc_key in seen:
            removed += 1
            continue
        seen[key] = True
        seen[loc_key] = True
        result.append(f)
    return result, removed


def _sort_findings(findings: list[Finding]) -> list[Finding]:
    from .model import CATEGORIES

    cat_order = {c: i for i, c in enumerate(CATEGORIES)}
    return sorted(
        findings,
        key=lambda f: (
            0 if not f.passed else 1,
            _SEVERITY_ORDER.get(f.severity, 9),
            cat_order.get(f.category, 99),
            f.rule_id,
            f.path or "",
            f.line or 0,
        ),
    )


def _filter_changed(findings: list[Finding], changed_files: set[str]) -> list[Finding]:
    """Keep repo-level findings plus findings on files that changed."""
    norm = {c.replace("\\", "/").lstrip("./") for c in changed_files}
    out: list[Finding] = []
    for f in findings:
        if f.path is None:
            out.append(f)
            continue
        p = f.path.replace("\\", "/").lstrip("./")
        if p in norm or any(p == c or p.endswith("/" + c) or c.endswith("/" + p) for c in norm):
            out.append(f)
    return out


def scan(
    repo_path: str,
    config: Config | None = None,
    config_path: str | None = None,
    run_integrations: bool = True,
    integrations: list[Integration] | None = None,
    profiles: list[str] | None = None,
    baseline: set[str] | None = None,
    changed_files: set[str] | None = None,
    load_plugins: bool = True,
) -> ScanResult:
    load_builtin_checks()

    cfg = config or load_config(repo_path, config_path, profiles=profiles)
    index = build_index(repo_path, extra_ignores=cfg.ignore)

    # Auto-detection: figure out what the repository is built with and apply the
    # matching Domain Standards on top of the baseline — no configuration needed.
    # Repository overrides still win (they are re-applied inside with_detected).
    from . import detect

    detections = detect.detect(index) if cfg.autodetect else []
    detected_technologies = [d.label for d in detections]
    cfg = cfg.with_detected([d.standard for d in detections])

    if load_plugins:
        try:
            from .plugins import load_plugins as _load_plugins

            _load_plugins(repo_path)
        except Exception:
            pass

    ctx = CheckContext(index=index, config=cfg)

    findings: list[Finding] = run_checks(ctx)

    integrations_run: list[str] = []
    integrations_available: list[str] = []
    if run_integrations:
        for integ in integrations or default_integrations():
            mode = cfg.integration_mode(integ.name)
            if mode in ("off", "false", "no"):
                continue
            if not integ.available():
                continue
            integrations_available.append(integ.name)
            if not integ.applicable(index):
                continue
            produced = integ.collect(index)
            integrations_run.append(integ.name)
            findings.extend(produced)

    findings, duplicates_removed = _dedupe(findings)

    # Suppressions always apply (a team consciously accepted these).
    from .suppressions import apply_suppressions, load_suppressions

    findings, suppressed = apply_suppressions(findings, index, load_suppressions(repo_path))

    # Baseline: hide pre-existing violations so only new ones fail.
    baselined = 0
    if baseline:
        from .baseline import apply_baseline

        findings, baselined = apply_baseline(findings, baseline)

    # Incremental: restrict to changed files (plus repo-level findings).
    if changed_files is not None:
        findings = _filter_changed(findings, changed_files)

    findings = _sort_findings(findings)

    categories, overall, grade = compute_scores(findings, cfg)
    passed, reasons = evaluate_gate(overall, findings, cfg)

    return ScanResult(
        repository=str(index.root),
        generated_at=_dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        deval_version=__version__,
        standard=cfg.standard,
        overall_score=overall,
        grade=grade,
        passed_gate=passed,
        gate_reasons=reasons,
        categories=categories,
        findings=findings,
        integrations_run=sorted(integrations_run),
        integrations_available=sorted(integrations_available),
        duplicates_removed=duplicates_removed,
        suppressed=suppressed,
        baselined=baselined,
        applied_standards=list(cfg.applied_standards),
        detected_technologies=detected_technologies,
    )
