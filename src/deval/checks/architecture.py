"""Architecture: layering discipline and module import cycles.

Deval enforces the classic Controller -> Service -> Repository layering. A
controller that imports a repository directly (bypassing the service layer) is a
violation. Import cycles between modules are also flagged. Detection is heuristic
and language-agnostic, based on file naming and import statements; it is precise
enough to catch real regressions without a full type graph.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from ..model import Finding
from ..registry import CheckContext, check

_IMPORT_RE = re.compile(
    r"^\s*(?:from\s+([\w\.]+)\s+import|import\s+([\w\.]+)|"
    r"(?:const|let|var)?\s*.*?require\(['\"]([^'\"]+)['\"]\)|"
    r"import\s+.*?from\s+['\"]([^'\"]+)['\"])",
    re.MULTILINE,
)

_LAYER_OF = {
    "controller": 0, "controllers": 0, "handler": 0, "handlers": 0,
    "route": 0, "routes": 0, "api": 0, "view": 0, "views": 0, "endpoint": 0,
    "service": 1, "services": 1, "usecase": 1, "usecases": 1, "domain": 1,
    "repository": 2, "repositories": 2, "repo": 2, "dao": 2, "store": 2,
    "model": 2, "models": 2, "entity": 2, "entities": 2,
}
_LAYER_NAME = {0: "Controller", 1: "Service", 2: "Repository"}
_CODE_SUFFIXES = (".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".java")

# Clean Architecture: dependencies must point inward (0 = innermost Domain).
_CLEAN_LAYER = {
    "domain": 0, "domains": 0, "entity": 0, "entities": 0,
    "application": 1, "applications": 1, "usecase": 1, "usecases": 1, "app": 1,
    "infrastructure": 2, "infra": 2, "adapter": 2, "adapters": 2,
    "persistence": 2, "gateway": 2, "gateways": 2, "framework": 2,
    "frameworks": 2,
}
_CLEAN_NAME = {0: "Domain", 1: "Application", 2: "Infrastructure"}


def _layer_of(relpath: str) -> int:
    tokens = re.split(r"[\W_]+", relpath.lower())
    for tok in tokens:
        if tok in _LAYER_OF:
            return _LAYER_OF[tok]
    return -1


def _clean_layer_of(relpath: str) -> int:
    tokens = re.split(r"[\W_]+", relpath.lower())
    for tok in tokens:
        if tok in _CLEAN_LAYER:
            return _CLEAN_LAYER[tok]
    return -1


def _uses_clean_architecture(index) -> bool:
    """True only when the repo actually organizes code into clean-arch layers."""
    seen: set = set()
    for rf in index.by_suffix(*_CODE_SUFFIXES):
        layer = _clean_layer_of(rf.relpath)
        if layer >= 0:
            seen.add(layer)
    # Need the Domain layer plus at least one outer layer to be meaningful.
    return 0 in seen and bool(seen & {1, 2})


def _imports(text: str) -> list[str]:
    out: list[str] = []
    for m in _IMPORT_RE.finditer(text):
        target = next((g for g in m.groups() if g), None)
        if target:
            out.append(target)
    return out


@check("respect-layering", "architecture")
def respect_layering(ctx: CheckContext) -> Iterable[Finding]:
    code = ctx.index.by_suffix(*_CODE_SUFFIXES)
    controllers = [rf for rf in code if _layer_of(rf.relpath) == 0]
    if not controllers:
        return
    violations = 0
    for rf in controllers:
        text = ctx.index.read_text(rf)
        for imp in _imports(text):
            target_layer = _layer_of(imp)
            if target_layer == 2:
                violations += 1
                yield ctx.fail(
                    "respect-layering",
                    "architecture",
                    f"{_LAYER_NAME[0]} '{rf.name}' imports a {_LAYER_NAME[2]} directly ('{imp}')",
                    path=rf.relpath,
                    remediation="Route data access through the Service layer.",
                )
                break
    if violations == 0:
        yield ctx.ok(
            "respect-layering", "architecture", "Controller -> Service -> Repository layering respected"
        )


@check("respect-clean-architecture", "architecture")
def respect_clean_architecture(ctx: CheckContext) -> Iterable[Finding]:
    # Inert unless the repository is organized into clean-architecture layers,
    # so it never penalizes projects that use a different (or no) style.
    if not _uses_clean_architecture(ctx.index):
        return
    code = ctx.index.by_suffix(*_CODE_SUFFIXES)
    violations = 0
    for rf in code:
        src_layer = _clean_layer_of(rf.relpath)
        if src_layer < 0:
            continue
        for imp in _imports(ctx.index.read_text(rf)):
            dst_layer = _clean_layer_of(imp)
            if dst_layer < 0:
                continue
            # Dependencies must point inward: a layer may only import layers
            # with an equal-or-lower index (Infrastructure -> Domain is fine).
            if dst_layer > src_layer:
                violations += 1
                yield ctx.fail(
                    "respect-clean-architecture",
                    "architecture",
                    f"{_CLEAN_NAME[src_layer]} '{rf.name}' depends outward on "
                    f"{_CLEAN_NAME[dst_layer]} ('{imp}')",
                    path=rf.relpath,
                    remediation="Depend on an inner-layer abstraction; inject the outer implementation.",
                )
                break
    if violations == 0:
        yield ctx.ok(
            "respect-clean-architecture", "architecture",
            "Domain -> Application -> Infrastructure dependencies point inward",
        )


@check("no-cross-module-cycles", "architecture")
def no_cross_module_cycles(ctx: CheckContext) -> Iterable[Finding]:
    py = ctx.index.by_suffix(".py")
    if len(py) < 2:
        return

    def module_name(relpath: str) -> str:
        parts = relpath[:-3].split("/")
        if parts and parts[-1] == "__init__":
            parts = parts[:-1]
        return ".".join(parts)

    modules: dict[str, set[str]] = {}
    names = {module_name(rf.relpath): rf for rf in py}
    for rf in py:
        mod = module_name(rf.relpath)
        deps: set[str] = set()
        for imp in _imports(ctx.index.read_text(rf)):
            for known in names:
                tail = known.split(".")[-1]
                if imp == known or imp.endswith("." + tail) or imp.split(".")[-1] == tail:
                    if known != mod:
                        deps.add(known)
        modules[mod] = deps

    reported: set[frozenset] = set()
    for a, deps in modules.items():
        for b in deps:
            if a in modules.get(b, set()):
                pair = frozenset((a, b))
                if pair in reported:
                    continue
                reported.add(pair)
                yield ctx.fail(
                    "no-cross-module-cycles",
                    "architecture",
                    f"Import cycle between '{a}' and '{b}'",
                    remediation="Break the cycle by extracting shared code or inverting a dependency.",
                )
    if not reported and modules:
        yield ctx.ok("no-cross-module-cycles", "architecture", "No import cycles detected")
