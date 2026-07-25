#!/usr/bin/env python3
"""Bundle the Deval source tree for the in-browser (Pyodide) scanner.

The documentation site runs the real Deval engine in WebAssembly rather than a
reimplementation, so the demo can never drift from the shipped tool. That is
only possible because Deval has zero required runtime dependencies: the entire
package is pure Python and can simply be dropped onto ``sys.path`` inside the
browser.

Run from anywhere::

    python docs/build_bundle.py

Writes ``docs/deval-src.zip`` plus ``docs/bundle-info.json`` (version and build
metadata the page displays, so a stale deploy is visible rather than silent).
"""

from __future__ import annotations

import hashlib
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path

DOCS = Path(__file__).resolve().parent
ROOT = DOCS.parent
SRC = ROOT / "src" / "deval"
BUNDLE = DOCS / "deval-src.zip"
INFO = DOCS / "bundle-info.json"


def package_version() -> str:
    """Read the version from pyproject without importing a TOML parser.

    Python 3.9 has no ``tomllib``, and this script must run on the same
    interpreter range Deval supports, so a narrow regex is preferable to adding
    a build-time dependency.
    """
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    return match.group(1) if match else "unknown"


def build() -> None:
    """Write the source bundle and its metadata sidecar."""
    if not SRC.is_dir():
        raise SystemExit(f"Cannot find Deval source at {SRC}")

    files = sorted(
        p for p in SRC.rglob("*")
        if p.is_file()
        and p.suffix in {".py", ".yml", ".yaml", ".json", ".md", ".txt"}
        and "__pycache__" not in p.parts
    )

    # Deterministic archive: fixed timestamps and sorted entries mean an
    # unchanged source tree produces a byte-identical bundle, so Pages deploys
    # and caches only change when the code actually changes.
    with zipfile.ZipFile(BUNDLE, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in files:
            arcname = str(Path("deval") / path.relative_to(SRC))
            info = zipfile.ZipInfo(arcname, date_time=(1980, 1, 1, 0, 0, 0))
            info.external_attr = 0o644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, path.read_bytes())

    digest = hashlib.sha256(BUNDLE.read_bytes()).hexdigest()
    INFO.write_text(
        json.dumps(
            {
                "version": package_version(),
                "files": len(files),
                "bytes": BUNDLE.stat().st_size,
                "sha256": digest,
                "built": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"Wrote {BUNDLE.relative_to(ROOT)}  ({len(files)} files, {BUNDLE.stat().st_size:,} bytes)")
    print(f"Wrote {INFO.relative_to(ROOT)}   (version {package_version()}, sha256 {digest[:12]})")


if __name__ == "__main__":
    build()
