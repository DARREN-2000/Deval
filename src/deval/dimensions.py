"""Engineering Dimensions - the formal identity behind every category.

Deval is not a checklist; it is an engineering framework. Every finding belongs
to exactly one *dimension* of engineering health, each with a name, a one-line
charter, and a DV code block. The Engineering Health score is the weighted roll
up of all dimensions into a single number.

The internal category keys stay stable for backwards compatibility; this module
gives each one its outward-facing identity (label, order, description, code
block). ``ci`` is presented as **CI/CD**; ``repository`` and ``structure`` are
foundational dimensions that sit alongside the rest.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Dimension:
    key: str          # internal category key (stable)
    label: str        # outward-facing name
    code_block: str   # DV code prefix, e.g. "DV1xxx"
    charter: str      # one-line description of what this dimension governs


# Presentation order for the Engineering Health scorecard.
_DIMENSIONS: tuple[Dimension, ...] = (
    Dimension("architecture", "Architecture", "DV7xxx",
              "Layering, boundaries, and dependency direction."),
    Dimension("documentation", "Documentation", "DV6xxx",
              "Whether the project explains itself to humans."),
    Dimension("testing", "Testing", "DV2xxx",
              "Automated verification and its breadth."),
    Dimension("security", "Security", "DV4xxx",
              "Secrets, unsafe files, authentication, and disclosure."),
    Dimension("dependencies", "Dependencies", "DV5xxx",
              "Reproducible, pinned, maintained third-party code."),
    Dimension("ci", "CI/CD", "DV3xxx",
              "Automated pipelines that test and guard every change."),
    Dimension("ownership", "Ownership", "DV9xxx",
              "Clear accountability for every part of the code."),
    Dimension("maintainability", "Maintainability", "DV8xxx",
              "How easy the code is to change safely over time."),
    Dimension("observability", "Observability", "DV11xxx",
              "Logging, tracing, metrics, and error tracking."),
    Dimension("operations", "Operations", "DV12xxx",
              "How the software is packaged, deployed, and run."),
    Dimension("compliance", "Compliance", "DV13xxx",
              "Licensing, governance, and audit evidence."),
    Dimension("repository", "Repository", "DV1xxx",
              "The foundational files every healthy repo carries."),
    Dimension("structure", "Structure", "DV10xxx",
              "Conventional, predictable project layout."),
)

DIMENSIONS: dict[str, Dimension] = {d.key: d for d in _DIMENSIONS}
DIMENSION_ORDER: list[str] = [d.key for d in _DIMENSIONS]


def label_for(category: str) -> str:
    d = DIMENSIONS.get(category)
    return d.label if d else category.replace("_", " ").title()


def charter_for(category: str) -> str:
    d = DIMENSIONS.get(category)
    return d.charter if d else ""
