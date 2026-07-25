"""The rule catalog — a single, enumerable source of truth for every rule.

Deval knows a lot of rules, but before this module there was no way to *browse*
them: you could ``explain`` one rule or list ``standards``, yet never see the
whole catalog at once. ``deval rules`` uses :func:`build_catalog` to present
every rule with its stable DV code, engineering dimension, universal/domain
scope, default severity, and whether it ships an ``explain`` doc.

The catalog is derived, never hand-maintained: it unions the implemented checks
(from the registry) with every rule referenced by a built-in standard, so it is
impossible for a rule to exist and be missing from the catalog.
"""

from __future__ import annotations

from dataclasses import dataclass

from .codes import CODE_BY_RULE, code_for
from .dimensions import label_for
from .model import Severity
from .registry import load_builtin_checks, registered_checks
from .rules_doc import RULE_DOCS
from .standards import STANDARDS, is_universal, recommended_standard

# DV code leading block -> engineering dimension (see codes.py).
_BLOCK_TO_DIM: dict[int, str] = {
    1: "repository",
    2: "testing",
    3: "ci",
    4: "security",
    5: "dependencies",
    6: "documentation",
    7: "architecture",
    8: "maintainability",
    9: "ownership",
    10: "structure",
    11: "observability",
    12: "operations",
    13: "compliance",
}


@dataclass(frozen=True)
class RuleInfo:
    rule_id: str
    code: str | None
    dimension: str            # internal category key (stable)
    dimension_label: str      # outward-facing dimension name
    scope: str                # "universal" or "domain"
    default_severity: Severity  # severity in deval/recommended (OFF if opt-in)
    documented: bool          # has an `explain` doc
    description: str

    def to_dict(self) -> dict:
        """Serialise this catalog entry as a JSON-safe dictionary.

        ``default_severity`` is flattened to its string value so ``deval rules
        --json`` output stays stable even if the enum's internals change.
        """
        return {
            "rule_id": self.rule_id,
            "code": self.code,
            "dimension": self.dimension,
            "dimension_label": self.dimension_label,
            "scope": self.scope,
            "default_severity": self.default_severity.value,
            "documented": self.documented,
            "description": self.description,
        }


def _dimension_from_code(code: str | None) -> str:
    """Best-effort dimension for a rule that has no registered check."""
    if not code:
        return "repository"
    digits = "".join(ch for ch in code if ch.isdigit())
    if not digits:
        return "repository"
    return _BLOCK_TO_DIM.get(int(digits) // 1000, "repository")


def all_rule_ids() -> list[str]:
    """Every public rule id Deval knows about.

    Registry entries can be orchestration checks that emit several public
    findings (for example ``ci-quality`` emits three CI rules), so registry
    function names are deliberately not exposed as rules. Stable codes,
    standards, and documentation form the public contract.
    """
    load_builtin_checks()
    ids = set(CODE_BY_RULE)
    for std in STANDARDS.values():
        ids.update(std.keys())
    ids.update(RULE_DOCS)
    return sorted(ids)


def build_catalog() -> list[RuleInfo]:
    """Return the full rule catalog, sorted by rule id."""
    load_builtin_checks()
    categories = {rc.name: rc.category for rc in registered_checks()}
    recommended = recommended_standard()
    catalog: list[RuleInfo] = []
    for rule_id in all_rule_ids():
        code = code_for(rule_id)
        dimension = categories.get(rule_id) or _dimension_from_code(code)
        doc = RULE_DOCS.get(rule_id)
        catalog.append(
            RuleInfo(
                rule_id=rule_id,
                code=code,
                dimension=dimension,
                dimension_label=label_for(dimension),
                scope="universal" if is_universal(rule_id) else "domain",
                default_severity=recommended.get(rule_id, Severity.OFF),
                documented=doc is not None,
                description=(doc.description if doc else ""),
            )
        )
    return catalog


def catalog_stats() -> dict[str, int]:
    """Small summary used by reports and tests."""
    catalog = build_catalog()
    return {
        "total": len(catalog),
        "universal": sum(1 for r in catalog if r.scope == "universal"),
        "domain": sum(1 for r in catalog if r.scope == "domain"),
        "documented": sum(1 for r in catalog if r.documented),
        "coded": sum(1 for r in catalog if r.code),
    }
