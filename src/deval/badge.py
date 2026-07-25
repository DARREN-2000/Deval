"""Public health badge, like a coverage badge but for engineering health.

Produces a self-contained SVG (no external requests) plus a Markdown snippet the
team can paste into a README. Color follows the grade.
"""

from __future__ import annotations

from .model import ScanResult


def _color(score: int) -> str:
    if score >= 90:
        return "#2ea44f"  # green
    if score >= 80:
        return "#a3c14a"  # yellow-green
    if score >= 70:
        return "#dfb317"  # yellow
    if score >= 60:
        return "#fe7d37"  # orange
    return "#e05d44"      # red


def render_svg(result: ScanResult) -> str:
    label = "engineering health"
    value = f"{result.grade}  {result.overall_score}"
    color = _color(result.overall_score)
    # Approximate width from text length (6px/char + padding).
    lw = 6 * len(label) + 20
    vw = 6 * len(value) + 24
    total = lw + vw
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{total}" height="20" role="img" aria-label="{label}: {value}">
  <linearGradient id="s" x2="0" y2="100%">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <clipPath id="r"><rect width="{total}" height="20" rx="3" fill="#fff"/></clipPath>
  <g clip-path="url(#r)">
    <rect width="{lw}" height="20" fill="#555"/>
    <rect x="{lw}" width="{vw}" height="20" fill="{color}"/>
    <rect width="{total}" height="20" fill="url(#s)"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="11">
    <text x="{lw / 2:.0f}" y="15" fill="#010101" fill-opacity=".3">{label}</text>
    <text x="{lw / 2:.0f}" y="14">{label}</text>
    <text x="{lw + vw / 2:.0f}" y="15" fill="#010101" fill-opacity=".3">{value}</text>
    <text x="{lw + vw / 2:.0f}" y="14">{value}</text>
  </g>
</svg>
"""


def markdown_snippet(result: ScanResult, badge_path: str = "deval-badge.svg") -> str:
    return f"![Engineering Health: {result.grade} {result.overall_score}]({badge_path})"
