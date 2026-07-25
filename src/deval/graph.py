"""Architecture graph generation.

Deval infers each source file's architectural layer and its imports, then emits
a diagram in Mermaid or Graphviz DOT. It supports two first-class architectural
styles and auto-detects which one the repository uses:

* **Layered**: Controller -> Service -> Repository
* **Clean**:   Domain -> Application -> Infrastructure (dependencies point inward)

Violations (a Controller reaching a Repository directly, or an inner clean-arch
layer depending outward) are highlighted so the graph doubles as a review
artifact.
"""

from __future__ import annotations

from .checks.architecture import (
    _CODE_SUFFIXES,
    _clean_layer_of,
    _imports,
    _layer_of,
    _uses_clean_architecture,
)
from .fsindex import RepoIndex

_LAYERED_LABEL = {0: "Controller", 1: "Service", 2: "Repository", -1: "Other"}
_CLEAN_LABEL = {0: "Domain", 1: "Application", 2: "Infrastructure", -1: "Other"}


def _detect_style(index: RepoIndex) -> str:
    return "clean" if _uses_clean_architecture(index) else "layered"


def _collect(index: RepoIndex, style: str):
    """Return edges between layers and the concrete violations, for a style."""
    files = index.by_suffix(*_CODE_SUFFIXES)
    layer_of = _clean_layer_of if style == "clean" else _layer_of
    edges: set[tuple[str, str]] = set()
    violations: list[tuple[str, str]] = []
    label = _CLEAN_LABEL if style == "clean" else _LAYERED_LABEL
    for rf in files:
        src_layer = layer_of(rf.relpath)
        if src_layer < 0:
            continue
        for imp in _imports(index.read_text(rf)):
            dst_layer = layer_of(imp)
            if dst_layer < 0 or dst_layer == src_layer:
                continue
            edges.add((label[src_layer], label[dst_layer]))
            if style == "clean":
                if dst_layer > src_layer:  # inner depending outward
                    violations.append((rf.relpath, imp))
            else:
                if src_layer == 0 and dst_layer == 2:  # controller -> repository
                    violations.append((rf.relpath, imp))
    return edges, violations


def render_graph(index: RepoIndex, fmt: str = "mermaid") -> str:
    style = _detect_style(index)
    edges, violations = _collect(index, style)

    if style == "clean":
        spine = [("Domain", "Application"), ("Application", "Infrastructure")]
        # In clean architecture, source dependencies point inward.
        bad = {("Domain", "Application"), ("Domain", "Infrastructure"),
               ("Application", "Infrastructure")}
        title = "Clean Architecture (dependencies point inward)"
    else:
        spine = [("Controller", "Service"), ("Service", "Repository")]
        bad = {("Controller", "Repository")}
        title = "Layered Architecture (Controller -> Service -> Repository)"

    # Show the canonical spine even if some layers are absent.
    render_edges: set[tuple[str, str]] = set(spine)
    render_edges |= {e for e in edges if e in bad}

    if fmt == "dot":
        lines = [
            "digraph deval_architecture {",
            f'  label="{title}";',
            "  rankdir=TB;",
            "  node [shape=box, style=rounded];",
        ]
        for edge in sorted(render_edges):
            attr = ' [color=red, label="violation"]' if edge in bad and edge not in spine else ""
            # A spine edge that is also "bad" only happens in clean style; mark it.
            if edge in violations_as_edges(violations, style) and edge in bad:
                attr = ' [color=red, label="violation"]'
            lines.append(f'  "{edge[0]}" -> "{edge[1]}"{attr};')
        lines.append("}")
        return "\n".join(lines)

    # default: mermaid
    lines = ["```mermaid", "graph TD", f"    %% {title}"]
    drawn = set()
    for edge in spine:
        lines.append(f"    {edge[0]} --> {edge[1]}")
        drawn.add(edge)
    for edge in sorted(edges):
        if edge in bad and edge not in drawn:
            lines.append(f"    {edge[0]} -. violation .-> {edge[1]}")
            drawn.add(edge)
    if violations:
        lines.append("    %% Dependency-direction violations detected:")
        for src, imp in violations[:10]:
            lines.append(f"    %%   {src} imports {imp}")
    lines.append("```")
    return "\n".join(lines)


def violations_as_edges(violations, style: str) -> set[tuple[str, str]]:
    """Best-effort mapping of concrete violations to layer edges (DOT styling)."""
    label = _CLEAN_LABEL if style == "clean" else _LAYERED_LABEL
    layer_of = _clean_layer_of if style == "clean" else _layer_of
    out: set[tuple[str, str]] = set()
    for src, imp in violations:
        a, b = layer_of(src), layer_of(imp)
        if a >= 0 and b >= 0:
            out.add((label[a], label[b]))
    return out
