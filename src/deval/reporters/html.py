"""Self-contained HTML dashboard: scorecard, trend line, and violations.

The dashboard has zero external dependencies (no CDN, no JS framework). The
trend sparkline is drawn as inline SVG from optional score history, so the file
opens correctly offline and can be published as a CI artifact or on Pages.
"""

from __future__ import annotations

import html as _html

from ..model import ScanResult, Severity

_SEV_CLASS = {Severity.ERROR: "error", Severity.WARNING: "warning", Severity.INFO: "info"}


def _color(score: int) -> str:
    if score >= 90:
        return "#16a34a"
    if score >= 75:
        return "#d97706"
    return "#dc2626"


def _trend_svg(history: list[dict]) -> str:
    scores = [h.get("overall_score", 0) for h in history][-30:]
    if len(scores) < 2:
        return '<p class="muted">Run with <code>--save-history</code> to build a trend line.</p>'
    w, h, pad = 640, 120, 8
    n = len(scores)
    step = (w - 2 * pad) / (n - 1)
    pts = []
    for i, s in enumerate(scores):
        x = pad + i * step
        y = h - pad - (s / 100) * (h - 2 * pad)
        pts.append(f"{x:.1f},{y:.1f}")
    poly = " ".join(pts)
    last = scores[-1]
    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" height="{h}" role="img" aria-label="Score trend">'
        f'<polyline fill="none" stroke="{_color(last)}" stroke-width="2.5" points="{poly}"/>'
        f'</svg>'
    )


def render(result: ScanResult, history: list[dict] | None = None) -> str:
    """Render ``result`` as a standalone, self-contained HTML report.

    No external CSS, fonts, or scripts are referenced, so the file can be
    published as a CI artifact or opened offline and still look correct.
    When ``history`` is supplied, a score trend is drawn alongside the summary.
    """
    history = history or []
    cats = [c for c in result.categories if c.passed + c.failed > 0]
    ring_color = _color(result.overall_score)
    circumference = 326.7
    dash = circumference * result.overall_score / 100

    cat_rows = "".join(
        f'<div class="cat"><div class="cat-head"><span>{_html.escape(c.label)}</span>'
        f'<b style="color:{_color(c.score)}">{c.score}</b></div>'
        f'<div class="track"><div class="fill" style="width:{c.score}%;background:{_color(c.score)}"></div></div></div>'
        for c in cats
    )

    def finding_row(f):
        """Render a single finding as an HTML table row.

        All interpolated values are HTML-escaped: findings contain file paths
        and tool messages from the scanned repository, which is untrusted input.
        """
        loc = ""
        if f.path:
            loc = _html.escape(f.path + (f":{f.line}" if f.line else ""))
        rem = f'<div class="rem">{_html.escape(f.remediation)}</div>' if f.remediation else ""
        src = f'<span class="src">{_html.escape(f.source)}</span>' if f.source != "native" else ""
        return (
            f'<tr class="{_SEV_CLASS.get(f.severity, "info")}">'
            f'<td class="sev">{f.severity.value}</td>'
            f'<td><code>{_html.escape(f.rule_id)}</code> {src}<div>{_html.escape(f.message)}</div>{rem}</td>'
            f'<td class="loc">{loc}</td></tr>'
        )

    failed = result.failed_findings
    findings_html = "".join(finding_row(f) for f in failed) or (
        '<tr><td colspan="3" class="ok">\u2713 No violations \u2014 every standard is satisfied.</td></tr>'
    )
    gate_badge = (
        '<span class="badge pass">PASS</span>'
        if result.passed_gate
        else '<span class="badge fail">FAIL</span>'
    )
    gate_reasons = ""
    if not result.passed_gate and result.gate_reasons:
        items = "".join(f"<li>{_html.escape(r)}</li>" for r in result.gate_reasons)
        gate_reasons = f'<ul class="reasons">{items}</ul>'

    passed_count = sum(1 for f in result.findings if f.passed)

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Deval Report \u2014 {result.overall_score}/100</title>
<style>
:root{{--bg:#0b0f17;--card:#111826;--line:#1f2937;--text:#e5e7eb;--muted:#9ca3af;}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--text);font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}}
.wrap{{max-width:960px;margin:0 auto;padding:32px 20px}}
h1{{font-size:22px;margin:0}}
.sub{{color:var(--muted);font-size:13px;margin-top:4px}}
.top{{display:flex;gap:24px;flex-wrap:wrap;align-items:center;background:var(--card);border:1px solid var(--line);border-radius:16px;padding:24px;margin:20px 0}}
.ring{{position:relative;width:132px;height:132px;flex:0 0 auto}}
.ring .score{{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center}}
.ring .score b{{font-size:34px}}
.ring .score span{{color:var(--muted);font-size:12px}}
.grade{{font-size:28px;font-weight:700}}
.badge{{padding:4px 12px;border-radius:999px;font-weight:700;font-size:13px}}
.badge.pass{{background:#052e1a;color:#4ade80;border:1px solid #14532d}}
.badge.fail{{background:#3f1212;color:#f87171;border:1px solid #7f1d1d}}
.reasons{{color:#f87171;font-size:13px;margin:8px 0 0}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}
@media(max-width:640px){{.grid{{grid-template-columns:1fr}}}}
.cat{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 14px}}
.cat-head{{display:flex;justify-content:space-between;font-size:14px;margin-bottom:8px}}
.track{{height:8px;background:#0b1220;border-radius:6px;overflow:hidden}}
.fill{{height:100%}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:20px;margin-top:20px}}
.card h2{{font-size:16px;margin:0 0 12px}}
table{{width:100%;border-collapse:collapse;font-size:14px}}
td{{border-top:1px solid var(--line);padding:10px 8px;vertical-align:top}}
.sev{{text-transform:uppercase;font-size:11px;font-weight:700;white-space:nowrap}}
tr.error .sev{{color:#f87171}} tr.warning .sev{{color:#fbbf24}} tr.info .sev{{color:#60a5fa}}
code{{background:#0b1220;padding:1px 6px;border-radius:5px;font-size:12px}}
.rem{{color:var(--muted);font-size:12px;margin-top:4px}}
.src{{color:var(--muted);font-size:11px;margin-left:6px}}
.loc{{color:var(--muted);font-size:12px;white-space:nowrap}}
.ok{{color:#4ade80;text-align:center;padding:20px}}
.muted{{color:var(--muted);font-size:13px}}
.foot{{color:var(--muted);font-size:12px;margin-top:24px;text-align:center}}
</style></head>
<body><div class="wrap">
<h1>Deval \u2014 Engineering Standards Report</h1>
<div class="sub">{_html.escape(result.repository)} \u00b7 standard <code>{_html.escape(result.standard)}</code> \u00b7 deval {result.deval_version}</div>
<div class="top">
  <div class="ring">
    <svg width="132" height="132" viewBox="0 0 120 120">
      <circle cx="60" cy="60" r="52" fill="none" stroke="#1f2937" stroke-width="12"/>
      <circle cx="60" cy="60" r="52" fill="none" stroke="{ring_color}" stroke-width="12"
        stroke-linecap="round" stroke-dasharray="{dash:.1f} {circumference:.1f}"
        transform="rotate(-90 60 60)"/>
    </svg>
    <div class="score"><b>{result.overall_score}</b><span>/ 100</span></div>
  </div>
  <div>
    <div class="grade" style="color:{ring_color}">Grade {result.grade}</div>
    <div style="margin-top:8px">{gate_badge}</div>
    {gate_reasons}
    <div class="sub" style="margin-top:10px">{passed_count} checks passed \u00b7 {len(failed)} failed
    {(' &#183; integrations: ' + ', '.join(result.integrations_run)) if result.integrations_run else ''}</div>
  </div>
</div>
<div class="grid">{cat_rows}</div>
<div class="card"><h2>Score trend</h2>{_trend_svg(history)}</div>
<div class="card"><h2>Findings</h2>
<table><tbody>{findings_html}</tbody></table></div>
<div class="foot">Generated by Deval {result.deval_version} at {result.generated_at}</div>
</div></body></html>
"""
