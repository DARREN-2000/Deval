"""Report renderers. Each takes a ScanResult and returns a string.

One health score, many shapes: humans read the terminal/HTML/Markdown reports;
machines ingest JSON, SARIF (code scanning), and XML (JUnit-style CI).
"""

from __future__ import annotations

from ..model import ScanResult
from . import html as _html
from . import json_reporter as _json
from . import markdown as _markdown
from . import sarif as _sarif
from . import terminal as _terminal
from . import xml as _xml

FORMATS = ("terminal", "json", "sarif", "html", "markdown", "xml")


def render(fmt: str, result: ScanResult, color: bool = True) -> str:
    """Render ``result`` in the requested format and return it as a string.

    ``fmt`` must be one of :data:`FORMATS`. ``color`` only affects the terminal
    renderer; the machine-readable formats ignore it so their output stays
    byte-for-byte reproducible.

    Raises:
        ValueError: if ``fmt`` is not a known format.
    """
    if fmt == "terminal":
        return _terminal.render(result, color=color)
    if fmt == "json":
        return _json.render(result)
    if fmt == "sarif":
        return _sarif.render(result)
    if fmt == "html":
        return _html.render(result)
    if fmt == "markdown":
        return _markdown.render(result)
    if fmt == "xml":
        return _xml.render(result)
    raise ValueError(f"Unknown format: {fmt}. Choose one of {', '.join(FORMATS)}.")
