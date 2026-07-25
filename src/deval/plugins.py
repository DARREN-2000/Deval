"""Plugins: language packs and community rules loaded at runtime.

The core stays language-agnostic. Everything language- or domain-specific ships
as a plugin: a Python file that registers rules through :mod:`deval.sdk`. Plugins
are discovered from, in order:

1. ``<repo>/.deval/plugins/*.py``           (project-local, committed rules)
2. ``~/.deval/plugins/*.py``                (user-installed, e.g. via ``deval install``)
3. ``$DEVAL_PLUGIN_PATH`` (os.pathsep list) (extra directories)

Deval also bundles a small marketplace of rule packs (kubernetes, react,
company/security). ``deval install <pack>`` copies a bundled pack into a plugin
directory. Bundled packs are inert until their trigger files are present, so
installing one never changes an unrelated repository's score.
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path

_MARKETPLACE_DIR = Path(__file__).parent / "marketplace"
_loaded_paths: set = set()


def _marketplace_file(name: str) -> Path:
    return _MARKETPLACE_DIR / (name.replace("/", "_").replace("-", "_") + ".py")


def available_packs() -> list[str]:
    """Bundled marketplace packs, using their install names (e.g. company/security)."""
    if not _MARKETPLACE_DIR.exists():
        return []
    out = []
    for p in sorted(_MARKETPLACE_DIR.glob("*.py")):
        if p.name == "__init__.py":
            continue
        out.append(p.stem.replace("company_security", "company/security"))
    return out


def plugin_search_dirs(repo_root: str) -> list[Path]:
    """Return the directories searched for rule plugins, in priority order.

    Repository-local plugins come first, then the user's home directory, then
    any paths listed in the ``DEVAL_PLUGIN_PATH`` environment variable. The
    directories need not exist; callers are expected to skip missing ones.
    """
    dirs: list[Path] = [Path(repo_root) / ".deval" / "plugins",
                        Path.home() / ".deval" / "plugins"]
    env = os.environ.get("DEVAL_PLUGIN_PATH")
    if env:
        for part in env.split(os.pathsep):
            if part.strip():
                dirs.append(Path(part.strip()))
    return dirs


def installed_plugins(repo_root: str) -> list[str]:
    """Return the paths of every plugin file discoverable from ``repo_root``.

    Results are sorted within each search directory so plugin load order (and
    therefore scan output) is deterministic across machines.
    """
    found: list[str] = []
    for d in plugin_search_dirs(repo_root):
        if d.exists():
            for p in sorted(d.glob("*.py")):
                if p.name != "__init__.py":
                    found.append(str(p))
    return found


def _import_path(path: Path) -> bool:
    key = str(path.resolve())
    if key in _loaded_paths:
        return True
    try:
        spec = importlib.util.spec_from_file_location(f"deval_plugin_{path.stem}", path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)  # registers rules via @rule on import
            _loaded_paths.add(key)
            return True
    except Exception:
        return False
    return False


def load_plugins(repo_root: str) -> list[str]:
    """Import every discovered plugin file so its rules register. Returns paths."""
    loaded: list[str] = []
    for d in plugin_search_dirs(repo_root):
        if not d.exists():
            continue
        for path in sorted(d.glob("*.py")):
            if path.name == "__init__.py":
                continue
            if _import_path(path):
                loaded.append(str(path))
    return loaded


def install_pack(name: str, dest_dir: str) -> Path:
    """Copy a bundled marketplace pack into ``dest_dir``. Returns the written path."""
    src = _marketplace_file(name)
    if not src.exists():
        raise FileNotFoundError(
            f"Unknown pack '{name}'. Available: {', '.join(available_packs()) or 'none'}"
        )
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    target = dest / src.name
    target.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    return target
