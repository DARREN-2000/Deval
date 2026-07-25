"""Machine-readable JSON report (deval.json)."""

from __future__ import annotations

import json

from ..model import ScanResult


def render(result: ScanResult) -> str:
    """Serialise ``result`` as indented JSON.

    Key order follows :meth:`ScanResult.to_dict` rather than being sorted, so
    the document reads top-down (score and grade first) and diffs cleanly
    between runs.
    """
    return json.dumps(result.to_dict(), indent=2, sort_keys=False)
