"""The ``deval`` command line interface.

Deval is the open platform for engineering standards. Every capability is one
subcommand of one CLI, and everything ultimately rolls up into a single
Engineering Health score.

Commands
--------
- ``scan``       evaluate a repository and enforce the quality gate
- ``review``     incremental scan of only changed files (fast, for PRs)
- ``report``     scan and show the score plus the delta vs. the last run
- ``trend``      show Repository Health over time
- ``init``       write a starter .deval.yml
- ``explain``    describe a rule (by slug or DV code): Problem / Why / Example / Fix / References
- ``standards``  list the built-in standards
- ``profiles``   list the built-in profiles (python, backend, startup, ...)
- ``rules``      list the full rule catalog (code, dimension, scope, severity)
- ``config``     validate a .deval.yml and surface typos with suggestions
- ``doctor``     preflight config, detection, rule contract, and integrations
- ``baseline``   create/show a baseline so legacy repos don't fail overnight
- ``fix``        safely autofix deterministic findings (missing LICENSE, ...)
- ``graph``      generate the Controller -> Service -> Repository graph
- ``badge``      generate a public Engineering Health SVG badge
- ``benchmark``  compare your score against published reference repositories
- ``plugins``    list installed and available plugin rule packs
- ``install``    install a marketplace rule pack (kubernetes, react, ...)
- ``test-rule``  run rule test cases (for rule authors)

Exit codes: 0 = success/gate passed, 1 = gate failed, 2 = usage/error.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from . import __version__
from .codes import rule_for_code
from .engine import scan as run_scan
from .history import append_history, load_history, previous_score
from .reporters import FORMATS, render
from .rules_doc import RULE_DOCS
from .rules_doc import explain as explain_rule
from .standards import PROFILE_DESCRIPTIONS, PROFILES, STANDARDS, list_standards

_STARTER_CONFIG = """# Deval configuration. Docs: https://github.com/DARREN-2000/deval#configuration
version: 1

# Start from a profile that matches how you build software, then extend it.
# Profiles: deval/recommended, deval/python, deval/backend, deval/startup,
#           deval/enterprise, deval/oss, deval/ml, deval/kubernetes
extends:
  - deval/recommended

# Override severities or enable opt-in policies (error | warning | info | off).
rules:
  # require-opentelemetry: error
  # require-authentication: error
  # no-console-log: warning

# Weight the categories your team cares about most.
weights:
  security: 1.5

# The quality gate.
thresholds:
  min_score: 80
  fail_on: error

# Control external tools: auto (default) | on | off
integrations:
  "*": auto
"""


def _profiles_arg(args) -> list[str] | None:
    prof = getattr(args, "profile", None)
    return [prof] if prof else None


def _add_scan_flags(p: argparse.ArgumentParser) -> None:
    p.add_argument("path", nargs="?", default=".", help="repository path (default: .)")
    p.add_argument("-f", "--format", choices=FORMATS, default="terminal")
    p.add_argument("-o", "--output", help="write the report to a file instead of stdout")
    p.add_argument("-c", "--config", help="path to a .deval.yml file")
    p.add_argument("--profile", choices=PROFILES + tuple(f"deval/{p}" for p in PROFILES),
                   help="evaluate against a built-in profile")
    p.add_argument("--min-score", type=int, default=None, help="override minimum passing score")
    p.add_argument("--no-integrations", action="store_true", help="skip external tools")
    p.add_argument("--use-baseline", action="store_true",
                   help="suppress violations recorded in .deval/baseline.json")
    p.add_argument("--explain", action="store_true",
                   help="append 'why it matters' + 'how to fix' to each finding")
    p.add_argument("--monorepo", action="store_true", help="scan each subproject and roll up")
    p.add_argument("--save-history", action="store_true", help="append this score to history")
    p.add_argument("--no-color", action="store_true", help="disable ANSI colors")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="deval",
        description="Deval \u2014 the open platform for engineering standards.",
    )
    parser.add_argument("--version", action="version", version=f"deval {__version__}")
    sub = parser.add_subparsers(dest="command")

    _add_scan_flags(sub.add_parser("scan", help="evaluate a repository and enforce the gate"))
    _add_scan_flags(sub.add_parser("report", help="scan and show score plus delta vs last run"))

    p_review = sub.add_parser("review", help="incremental scan of only changed files")
    _add_scan_flags(p_review)
    p_review.add_argument("--base", default="HEAD", help="git ref to diff against (default: HEAD)")
    p_review.add_argument("--changed", help="comma-separated files to treat as changed (skip git)")

    p_init = sub.add_parser("init", help="write a starter .deval.yml")
    p_init.add_argument("path", nargs="?", default=".")
    p_init.add_argument("--force", action="store_true", help="overwrite an existing config")

    p_explain = sub.add_parser("explain", help="describe a rule (slug or DV code) and how to fix it")
    p_explain.add_argument("rule_id", help="rule slug (require-readme) or DV code (DV1001)")

    sub.add_parser("standards", help="list the built-in standards")
    sub.add_parser("profiles", help="list the built-in profiles")
    p_detect = sub.add_parser("detect", help="show detected technologies and the standards Deval would apply")
    p_detect.add_argument("path", nargs="?", default=".", help="repository path (default: .)")

    p_rules = sub.add_parser("rules", help="list the full rule catalog")
    p_rules.add_argument("--standard", help="show effective severities under a standard (e.g. deval/fastapi)")
    p_rules.add_argument("--dimension", help="filter by engineering dimension (e.g. security)")
    p_rules.add_argument("--scope", choices=["universal", "domain"], help="filter by rule scope")
    p_rules.add_argument("--undocumented", action="store_true", help="only rules without an explain doc")
    p_rules.add_argument("--json", action="store_true", help="machine-readable output")

    p_config = sub.add_parser("config", help="validate a .deval.yml and surface typos")
    p_config.add_argument("path", nargs="?", default=".", help="repository path (default: .)")
    p_config.add_argument("-c", "--config", help="path to a .deval.yml file")
    p_config.add_argument("--json", action="store_true", help="machine-readable validation report")

    p_doctor = sub.add_parser("doctor", help="run a complete Deval preflight")
    p_doctor.add_argument("path", nargs="?", default=".", help="repository path (default: .)")
    p_doctor.add_argument("-c", "--config", help="path to a .deval.yml file")
    p_doctor.add_argument("--json", action="store_true", help="machine-readable diagnostic report")

    p_baseline = sub.add_parser("baseline", help="manage the baseline of accepted violations")
    p_baseline.add_argument("action", choices=["create", "show"], nargs="?", default="create")
    p_baseline.add_argument("path", nargs="?", default=".")
    p_baseline.add_argument("--profile", choices=PROFILES, default=None)

    p_fix = sub.add_parser("fix", help="safely autofix deterministic findings")
    p_fix.add_argument("path", nargs="?", default=".")
    p_fix.add_argument("--dry-run", action="store_true", help="show what would be created")
    p_fix.add_argument("--profile", choices=PROFILES, default=None)

    p_graph = sub.add_parser("graph", help="generate the architecture graph")
    p_graph.add_argument("path", nargs="?", default=".")
    p_graph.add_argument("--format", choices=["mermaid", "dot"], default="mermaid")
    p_graph.add_argument("-o", "--output", help="write the graph to a file")

    p_badge = sub.add_parser("badge", help="generate a public health SVG badge")
    p_badge.add_argument("path", nargs="?", default=".")
    p_badge.add_argument("-o", "--output", default="deval-badge.svg", help="output SVG path")
    p_badge.add_argument("--profile", choices=PROFILES, default=None)

    p_trend = sub.add_parser("trend", help="show Repository Health over time")
    p_trend.add_argument("path", nargs="?", default=".")

    p_bench = sub.add_parser("benchmark", help="compare against reference repositories")
    p_bench.add_argument("path", nargs="?", default=".")
    p_bench.add_argument("--profile", choices=PROFILES, default=None)

    p_plugins = sub.add_parser("plugins", help="list installed and available rule packs")
    p_plugins.add_argument("path", nargs="?", default=".")

    p_install = sub.add_parser("install", help="install a marketplace rule pack")
    p_install.add_argument("pack", help="pack name, e.g. kubernetes, react, company/security")
    p_install.add_argument("path", nargs="?", default=".")
    p_install.add_argument("--user", action="store_true",
                           help="install into ~/.deval/plugins instead of <repo>/.deval/plugins")

    p_testrule = sub.add_parser("test-rule", help="run rule test cases (for rule authors)")
    p_testrule.add_argument("cases_dir", help="directory of rule test cases")

    return parser


def _append_explanations(output: str, result) -> str:
    rule_ids = sorted({f.rule_id for f in result.failed_findings})
    if not rule_ids:
        return output
    lines = [output, "", "Explanations", "=" * 40]
    from .rules_doc import RULE_DOCS as _docs
    for rid in rule_ids:
        doc = _docs.get(rid)
        if not doc:
            continue
        lines += ["", f"[{rid}]", f"  Why:  {doc.why}", f"  Fix:  {doc.fix}"]
    return "\n".join(lines)


def _git_changed(path: str, base: str) -> set[str] | None:
    try:
        out = subprocess.run(
            ["git", "-C", path, "diff", "--name-only", base],
            capture_output=True, text=True, timeout=15,
        )
        if out.returncode != 0:
            return None
        files = {line.strip() for line in out.stdout.splitlines() if line.strip()}
        return files
    except Exception:
        return None


def _emit(output: str, args) -> None:
    if getattr(args, "output", None):
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"Wrote {getattr(args, 'format', 'report')} report to {args.output}")
    else:
        print(output)


def _run_scan_command(args) -> int:
    if getattr(args, "monorepo", False):
        return _run_monorepo(args)

    baseline = None
    if getattr(args, "use_baseline", False):
        from .baseline import load_baseline
        baseline = load_baseline(args.path)

    scan_path = Path(args.path)
    changed_files = None
    args_path_for_scan = args.path

    if scan_path.is_file():
        repo_path = scan_path.parent
        for p in [scan_path.parent] + list(scan_path.parent.parents):
            if (p / ".deval.yml").exists() or (p / ".git").exists():
                repo_path = p
                break
        try:
            rel_path = scan_path.resolve().relative_to(repo_path.resolve()).as_posix()
            changed_files = {rel_path}
        except ValueError:
            changed_files = {scan_path.name}
        args_path_for_scan = str(repo_path)

    result = run_scan(
        args_path_for_scan,
        config_path=getattr(args, "config", None),
        run_integrations=not args.no_integrations,
        profiles=_profiles_arg(args),
        baseline=baseline,
        changed_files=changed_files,
    )
    if args.min_score is not None:
        from .config import load_config
        from .scoring import evaluate_gate
        cfg = load_config(args.path, getattr(args, "config", None), profiles=_profiles_arg(args))
        cfg.thresholds.min_score = args.min_score
        passed, reasons = evaluate_gate(result.overall_score, result.findings, cfg)
        result.passed_gate = passed
        result.gate_reasons = reasons

    color = sys.stdout.isatty() and not args.no_color
    output = render(args.format, result, color=color)
    if getattr(args, "explain", False) and args.format == "terminal":
        output = _append_explanations(output, result)
    _emit(output, args)

    if getattr(args, "save_history", False):
        append_history(result, args.path)

    if args.command == "report":
        prev = previous_score(args.path)
        if prev is not None:
            delta = result.overall_score - prev
            sign = "+" if delta >= 0 else ""
            print(f"Score {result.overall_score} ({sign}{delta} vs previous {prev})")

    return 0 if result.passed_gate else 1


def _run_review(args) -> int:
    if getattr(args, "changed", None):
        changed = {c.strip() for c in args.changed.split(",") if c.strip()}
    else:
        changed = _git_changed(args.path, args.base)
        if changed is None:
            print("deval review: git unavailable or not a repo; scanning everything.",
                  file=sys.stderr)
            changed = None
    if changed is not None and not changed:
        print("No changed files. Nothing to review.")
        return 0

    result = run_scan(
        args.path,
        config_path=getattr(args, "config", None),
        run_integrations=not args.no_integrations,
        profiles=_profiles_arg(args),
        changed_files=changed,
    )
    color = sys.stdout.isatty() and not args.no_color
    output = render(args.format, result, color=color)
    if getattr(args, "explain", False) and args.format == "terminal":
        output = _append_explanations(output, result)
    _emit(output, args)
    return 0 if result.passed_gate else 1


def _run_monorepo(args) -> int:
    from .monorepo import render_monorepo, scan_monorepo
    mr = scan_monorepo(args.path, profiles=_profiles_arg(args),
                       run_integrations=not args.no_integrations)
    if getattr(args, "format", "terminal") == "json":
        import json
        _emit(json.dumps(mr.to_dict(), indent=2), args)
    else:
        _emit(render_monorepo(mr), args)
    return 0 if all(p.result.passed_gate for p in mr.projects) else 1


def _run_init(args) -> int:
    target = Path(args.path) / ".deval.yml"
    if target.exists() and not args.force:
        print(f"{target} already exists (use --force to overwrite).")
        return 2
    target.write_text(_STARTER_CONFIG, encoding="utf-8")
    print(f"Wrote {target}. Run 'deval scan .' to evaluate your repository.")
    return 0


def _run_explain(args) -> int:
    query = args.rule_id.strip()
    # Accept either a rule slug (require-readme) or a stable DV code (DV1001).
    rule_id = rule_for_code(query) or query
    doc = explain_rule(rule_id)
    if not doc:
        from .codes import code_for
        print(f"Unknown rule '{args.rule_id}'. Documented rules:")
        for rid in sorted(RULE_DOCS):
            code = code_for(rid)
            prefix = f"{code}  " if code else ""
            print(f"  - {prefix}{rid}")
        return 2
    print(doc)
    return 0


def _run_standards(_args) -> int:
    from .standards import STANDARD_GROUPS

    counts = dict(list_standards())

    def _line(name: str) -> None:
        key = f"deval/{name}"
        if key not in STANDARDS:
            return
        enabled = counts.get(key, 0)
        print(f"  {key:<22} {enabled:>2} rules  \u2014 {PROFILE_DESCRIPTIONS.get(name, '')}")

    print("Deval Standards \u2014 think of them like packages. Each is a collection of rules.\n")
    for label, keys in STANDARD_GROUPS:
        print(f"{label}:")
        for name in keys:
            _line(name)
        print()
    print("Compose them in .deval.yml, e.g.:")
    print("  extends: [deval/recommended, deval/python, deval/fastapi, company/backend]")
    print("\nOr let 'deval scan .' auto-detect your stack and apply the matching standards.")
    return 0


def _run_detect(args) -> int:
    """Show what Deval detects in a repository and which standards it would apply."""
    from . import detect as _detect
    from .fsindex import build_index

    index = build_index(args.path)
    detections = _detect.detect(index)
    if not detections:
        print("Detected\n  (no known technologies \u2014 the universal baseline applies)")
        print("\nApplying\n  deval/recommended")
        return 0
    print("Detected")
    for d in detections:
        print(f"  \u2713 {d.label}")
    print("\nApplying")
    print("  deval/recommended")
    for d in detections:
        print(f"  {d.standard}")
    print("\nNo configuration required. Add a .deval.yml only to override or extend.")
    return 0


def _run_profiles(_args) -> int:
    print("Built-in profiles (extends: [deval/<name>]):\n")
    counts = dict(list_standards())
    for name in PROFILES:
        key = f"deval/{name}"
        enabled = counts.get(key, 0)
        print(f"  {key:<20} {enabled:>2} rules  \u2014 {PROFILE_DESCRIPTIONS.get(name, '')}")
    print("\nProfiles layer on top of the baseline; your rules: still win.")
    return 0


def _run_baseline(args) -> int:
    from .baseline import BASELINE_PATH, create_baseline, load_baseline
    if args.action == "show":
        fps = load_baseline(args.path)
        if not fps:
            print("No baseline found. Create one with 'deval baseline create'.")
            return 0
        print(f"Baseline: {len(fps)} accepted violation(s) in {BASELINE_PATH}")
        for fp in sorted(fps):
            print(f"  - {fp}")
        return 0
    profiles = [args.profile] if args.profile else None
    result = run_scan(args.path, profiles=profiles)
    path = create_baseline(result, args.path)
    print(f"Recorded {len(result.failed_findings)} current violation(s) as the baseline.")
    print(f"Wrote {path}. Future scans with --use-baseline only fail on NEW violations.")
    return 0


def _run_fix(args) -> int:
    from .fix import apply_fixes, plan_fixes
    profiles = [args.profile] if args.profile else None
    result = run_scan(args.path, profiles=profiles)
    actions = plan_fixes(result)
    if not actions:
        print("Nothing to autofix. All deterministically-fixable findings are resolved.")
        return 0
    written = apply_fixes(actions, args.path, dry_run=args.dry_run)
    verb = "Would create" if args.dry_run else "Created"
    print(f"Safe autofix ({len(actions)} candidate action(s)):\n")
    for action in actions:
        mark = "\u2713" if (action.filename in written or args.dry_run) else "\u2013"
        print(f"  {mark} {action.description}  ->  {action.filename}")
    if not args.dry_run:
        print(f"\n{verb} {len(written)} file(s). Re-run 'deval scan .' to see the new score.")
    else:
        print("\nDry run: no files were written.")
    return 0


def _run_graph(args) -> int:
    from .fsindex import build_index
    from .graph import render_graph
    index = build_index(args.path)
    out = render_graph(index, fmt=args.format)
    if args.output:
        Path(args.output).write_text(out, encoding="utf-8")
        print(f"Wrote architecture graph to {args.output}")
    else:
        print(out)
    return 0


def _run_badge(args) -> int:
    from .badge import markdown_snippet, render_svg
    profiles = [args.profile] if args.profile else None
    result = run_scan(args.path, profiles=profiles)
    Path(args.output).write_text(render_svg(result), encoding="utf-8")
    print(f"Wrote badge to {args.output} (Engineering Health {result.grade} {result.overall_score}).")
    print("Embed in your README:")
    print(f"  {markdown_snippet(result, args.output)}")
    return 0


def _relative_day(iso: str) -> str:
    """Human label for a history timestamp: Today / Yesterday / Last Week / date."""
    from datetime import datetime
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except Exception:
        return (iso or "")[:10] or "unknown"
    now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
    delta = (now.date() - dt.date()).days
    if delta <= 0:
        return "Today"
    if delta == 1:
        return "Yesterday"
    if delta < 7:
        return f"{delta} days ago"
    if delta < 14:
        return "Last Week"
    return dt.date().isoformat()


def _run_trend(args) -> int:
    hist = load_history(args.path)
    if not hist:
        print("No history yet. Run 'deval scan . --save-history' over time to build a trend.")
        return 0
    from .grades import grade_for as _grade
    print("Engineering Health \u2014 trend\n")
    peak = max(h.get("overall_score", 0) for h in hist) or 1
    for h in reversed(hist[-8:]):
        score = h.get("overall_score", 0)
        label = _relative_day(str(h.get("generated_at", "")))
        grade = h.get("grade") or _grade(score)
        bar = "\u2588" * max(1, round(score / peak * 24))
        print(f"  {label:<12} {score:>3}  {grade:<2}  {bar}")
    first, last = hist[0]["overall_score"], hist[-1]["overall_score"]
    delta = last - first
    sign = "+" if delta >= 0 else ""
    arrow = "\u2191" if delta > 0 else ("\u2193" if delta < 0 else "\u2192")
    print(f"\n  {len(hist)} data point(s). Net change: {sign}{delta} {arrow} ({first} -> {last}).")
    return 0


def _run_benchmark(args) -> int:
    from .benchmark import render_benchmark
    profiles = [args.profile] if args.profile else None
    result = run_scan(args.path, profiles=profiles)
    print(render_benchmark(result))
    return 0


def _run_plugins(args) -> int:
    from .plugins import available_packs, installed_plugins
    installed = installed_plugins(args.path)
    print("Installed plugins:")
    if installed:
        for p in installed:
            print(f"  - {p}")
    else:
        print("  (none)")
    print("\nAvailable marketplace packs (install with 'deval install <name>'):")
    for pack in available_packs():
        print(f"  - {pack}")
    return 0


def _run_install(args) -> int:
    from .plugins import install_pack
    if args.user:
        dest = Path.home() / ".deval" / "plugins"
    else:
        dest = Path(args.path) / ".deval" / "plugins"
    try:
        target = install_pack(args.pack, str(dest))
    except FileNotFoundError as exc:
        print(f"deval: error: {exc}", file=sys.stderr)
        return 2
    print(f"Installed '{args.pack}' to {target}.")
    print("Its rules will run on the next scan (inert until trigger files are present).")
    return 0


def _run_test_rule(args) -> int:
    """Run rule test cases.

    A cases directory contains one subdirectory per case; each case is a tiny
    repository plus an ``expect.txt`` listing the rule ids expected to FAIL
    (one per line). Deval scans each case and checks the expectation, so rule
    authors get a fast, deterministic feedback loop.
    """
    cases_dir = Path(args.cases_dir)
    if not cases_dir.is_dir():
        print(f"deval: error: no such directory: {cases_dir}", file=sys.stderr)
        return 2
    cases = [d for d in sorted(cases_dir.iterdir()) if d.is_dir()]
    if not cases:
        print(f"No test cases found in {cases_dir}.")
        return 2
    passed = 0
    failed = 0
    for case in cases:
        expect_file = case / "expect.txt"
        expected = set()
        if expect_file.exists():
            expected = {ln.strip() for ln in expect_file.read_text().splitlines() if ln.strip()}
        result = run_scan(str(case), run_integrations=False, load_plugins=True)
        actual = {f.rule_id for f in result.failed_findings}
        missing = expected - actual
        if not missing:
            passed += 1
            print(f"  \u2713 {case.name}")
        else:
            failed += 1
            print(f"  \u2717 {case.name}: expected failing rules not found: {', '.join(sorted(missing))}")
    print(f"\n{passed} passed, {failed} failed ({len(cases)} case(s)).")
    return 0 if failed == 0 else 1


def _run_rules(args) -> int:
    from .catalog import build_catalog
    from .dimensions import DIMENSION_ORDER, label_for
    from .model import Severity
    from .standards import STANDARDS

    catalog = build_catalog()

    std_map = None
    if getattr(args, "standard", None):
        name = args.standard
        key = name.split("/", 1)[-1] if name.startswith("deval/") else name
        std_map = STANDARDS.get(name) or STANDARDS.get(key)
        if std_map is None:
            print(f"deval: error: unknown standard '{args.standard}'", file=sys.stderr)
            return 2

    def _sev(info) -> str:
        if std_map is not None:
            return std_map.get(info.rule_id, Severity.OFF).value
        return info.default_severity.value

    rows = catalog
    if getattr(args, "dimension", None):
        want = args.dimension.strip().lower()
        rows = [r for r in rows if r.dimension == want or r.dimension_label.lower() == want]
    if getattr(args, "scope", None):
        rows = [r for r in rows if r.scope == args.scope]
    if getattr(args, "undocumented", False):
        rows = [r for r in rows if not r.documented]

    if getattr(args, "json", False):
        import json
        payload = []
        for r in rows:
            d = r.to_dict()
            d["severity"] = _sev(r)
            payload.append(d)
        print(json.dumps(payload, indent=2))
        return 0

    if not rows:
        print("No rules match the given filters.")
        return 0

    by_dim = {}
    for r in rows:
        by_dim.setdefault(r.dimension, []).append(r)

    header = "Deval rule catalog"
    if std_map is not None:
        header += f" \u2014 effective severities under {args.standard}"
    print(header + "\n")
    total = 0
    for dim in DIMENSION_ORDER:
        group = by_dim.get(dim)
        if not group:
            continue
        print(f"{label_for(dim)}:")
        for r in sorted(group, key=lambda x: (x.code or "zzzzz", x.rule_id)):
            code = (r.code or "").ljust(8)
            scope = "domain" if r.scope == "domain" else "univ. "
            sev = _sev(r).ljust(7)
            print(f"  {code} {sev} {scope}  {r.rule_id}")
            total += 1
        print()
    universal = sum(1 for r in rows if r.scope == "universal")
    print(f"{total} rule(s): {universal} universal, {total - universal} domain.")
    print("Use 'deval explain <rule>' for the Problem / Why / Example / Fix / References.")
    return 0


def _run_config(args) -> int:
    from .config_lint import validate_config
    report = validate_config(args.path, getattr(args, "config", None))
    if getattr(args, "json", False):
        import json
        print(json.dumps(report.to_dict(), indent=2))
        return 1 if report.errors else 0
    if report.config_path:
        print(f"Validating {report.config_path}\n")
    else:
        print("No .deval.yml found; the repository would use deval/recommended.\n")
    if not report.issues:
        print("\u2713 Configuration is valid. No problems found.")
        return 0
    for issue in report.issues:
        mark = "\u2717" if issue.level == "error" else "\u26a0"
        print(f"  {mark} [{issue.field}] {issue.message}")
    n_err, n_warn = len(report.errors), len(report.warnings)
    print(f"\n{n_err} error(s), {n_warn} warning(s).")
    return 1 if n_err else 0


def _run_doctor(args) -> int:
    import json

    from .doctor import diagnose

    report = diagnose(args.path, getattr(args, "config", None))
    if getattr(args, "json", False):
        print(json.dumps(report.to_dict(), indent=2))
        return 0 if report.ok else 1

    print(f"Deval doctor {report.version}\nRepository  {report.repository}\n")
    for issue in report.issues:
        mark = "\u2717" if issue.level == "error" else "\u26a0"
        print(f"{mark} {issue.field}: {issue.message}")
    if report.config_path:
        print(f"\u2713 Config      {report.config_path}")
    else:
        print("\u2713 Config      deval/recommended (zero configuration)")
    if report.catalog:
        print(f"\u2713 Rule contract {report.catalog['total']} coded, documented rules")
    if report.detected:
        print(f"\u2713 Detected    {', '.join(report.detected)}")
    else:
        print("\u2713 Detected    no domain-specific technology")
    if report.standards:
        print(f"\u2713 Applying    {', '.join(report.standards)}")
    print(f"\u2713 Rules       {report.enabled_rules} enabled")
    ready = [i.name for i in report.integrations if i.status == "ready"]
    missing = [i.name for i in report.integrations if i.status == "missing"]
    print(f"\u2713 Integrations ready: {', '.join(ready) if ready else 'native engine only'}")
    if missing:
        print(f"\u2139 Optional tools not installed: {', '.join(missing)}")
    print("\n" + ("READY \u2014 the quality gate is trustworthy." if report.ok
                   else "NOT READY \u2014 fix the errors above before enforcing the gate."))
    return 0 if report.ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 2
    dispatch = {
        "scan": _run_scan_command,
        "report": _run_scan_command,
        "review": _run_review,
        "init": _run_init,
        "explain": _run_explain,
        "standards": _run_standards,
        "profiles": _run_profiles,
        "detect": _run_detect,
        "rules": _run_rules,
        "config": _run_config,
        "doctor": _run_doctor,
        "baseline": _run_baseline,
        "fix": _run_fix,
        "graph": _run_graph,
        "badge": _run_badge,
        "trend": _run_trend,
        "benchmark": _run_benchmark,
        "plugins": _run_plugins,
        "install": _run_install,
        "test-rule": _run_test_rule,
    }
    try:
        handler = dispatch.get(args.command)
        if handler is None:
            parser.print_help()
            return 2
        return handler(args)
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 2
    except Exception as exc:  # never crash with a traceback for users
        print(f"deval: error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
