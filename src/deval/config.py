"""Configuration loading and the ``extends`` resolution mechanism.

Deval is opinionated by default. With no config file, a repository is evaluated
against ``deval/recommended``. Organizations extend that baseline instead of
replacing it:

    version: 1
    extends:
      - deval/recommended
    rules:
      require-opentelemetry: error
      no-console-log: warning
      require-changelog: off
    weights:
      security: 2.0
    thresholds:
      min_score: 80
      fail_on: error
    ignore:
      - "examples/**"
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .model import Severity
from .standards import STANDARDS, recommended_standard

CONFIG_FILENAMES = (".deval.yml", ".deval.yaml", "deval.yml", "deval.yaml")


def _load_yaml(text: str) -> dict[str, Any]:
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(text)
        return data or {}
    except Exception:
        return _mini_yaml(text)


def _mini_yaml(text: str) -> dict[str, Any]:
    """Very small YAML subset parser (nested maps, lists, scalars). Used only if
    PyYAML is unavailable so Deval keeps working with zero dependencies.

    Implemented as an indentation-driven recursive descent, which handles the
    map-vs-list ambiguity (``key:`` followed by ``- item`` versus ``sub: val``)
    by inspecting the first child line of each block.
    """
    lines = [
        (len(raw) - len(raw.lstrip(" ")), raw.strip())
        for raw in text.splitlines()
        if raw.strip() and not raw.strip().startswith("#")
    ]
    pos = [0]

    def parse_block(min_indent: int) -> Any:
        if pos[0] >= len(lines):
            return {}
        _, first_line = lines[pos[0]]
        if first_line.startswith("- ") or first_line == "-":
            return _parse_list(min_indent)
        return _parse_map(min_indent)

    def _parse_list(min_indent: int) -> list:
        result: list = []
        while pos[0] < len(lines):
            indent, line = lines[pos[0]]
            if indent < min_indent or not (line.startswith("- ") or line == "-"):
                break
            item = line[1:].strip()
            pos[0] += 1
            if item == "":
                result.append(parse_block(indent + 1))
            else:
                result.append(_coerce_scalar(item))
        return result

    def _parse_map(min_indent: int) -> dict[str, Any]:
        result: dict[str, Any] = {}
        while pos[0] < len(lines):
            indent, line = lines[pos[0]]
            if indent < min_indent or line.startswith("- "):
                break
            if ":" not in line:
                pos[0] += 1
                continue
            key, _, rest = line.partition(":")
            key = key.strip()
            rest = rest.strip()
            pos[0] += 1
            if rest == "":
                if pos[0] < len(lines) and lines[pos[0]][0] > indent:
                    result[key] = parse_block(lines[pos[0]][0])
                else:
                    result[key] = None
            else:
                result[key] = _coerce_scalar(rest)
        return result

    parsed = parse_block(0)
    return parsed if isinstance(parsed, dict) else {}


def _coerce_scalar(value: str) -> Any:
    v = value.strip().strip('"').strip("'")
    low = v.lower()
    if low in ("true", "false"):
        return low == "true"
    if low in ("null", "~", "none"):
        return None
    try:
        if "." in v:
            return float(v)
        return int(v)
    except ValueError:
        if v.startswith("[") and v.endswith("]"):
            return [x.strip() for x in v[1:-1].split(",") if x.strip()]
        return v


@dataclass
class Thresholds:
    min_score: int = 0
    fail_on: Severity = Severity.ERROR
    max_errors: int | None = None


@dataclass
class Config:
    standard: str = "deval/recommended"
    rules: dict[str, Severity] = field(default_factory=dict)
    weights: dict[str, float] = field(default_factory=dict)
    thresholds: Thresholds = field(default_factory=Thresholds)
    ignore: list[str] = field(default_factory=list)
    integrations: dict[str, str] = field(default_factory=dict)
    source_path: str | None = None
    # 5-level hierarchy support
    extends: list[str] = field(default_factory=list)
    explicit_rules: dict[str, Severity] = field(default_factory=dict)
    autodetect: bool = True
    applied_standards: list[str] = field(default_factory=list)
    repo_root: str | None = None

    def severity_for(self, rule_id: str, default: Severity) -> Severity:
        """Return the configured severity for ``rule_id``, else ``default``."""
        return self.rules.get(rule_id, default)

    def is_enabled(self, rule_id: str, default: Severity) -> bool:
        """Whether ``rule_id`` should run at all.

        A rule resolved to ``off`` is skipped entirely: it produces no finding
        and does not affect the score.
        """
        return self.severity_for(rule_id, default) != Severity.OFF

    def weight_for(self, category: str) -> float:
        """Return the scoring weight for a dimension.

        Weights let a team say that, for example, Security matters more than
        Documentation when the dimensions are averaged into one score.
        """
        return float(self.weights.get(category, 1.0))

    def integration_mode(self, name: str) -> str:
        """Return how the external tool ``name`` should be used.

        Controls whether an integration is run, skipped, or only consumed when
        the tool is already present on the machine.
        """
        return str(self.integrations.get(name, self.integrations.get("*", "auto")))

    def with_detected(self, detected_standards: list[str]) -> Config:
        """Fold auto-detected Domain Standards into the resolution chain.

        The full precedence, low to high, is:

            Global -> Deval Recommended -> file ``extends`` (Domain/Org) ->
            auto-detected Domain Standards -> Repository Overrides (repo ``rules:``)

        Detected standards slot in *below* the repository's explicit rules, so a
        repo override always wins over an auto-applied domain default.
        """
        if not detected_standards:
            # still record what was applied (just the extends chain)
            self.applied_standards = list(dict.fromkeys(self.extends))
            return self
        chain = list(self.extends)
        for s in detected_standards:
            if s not in chain:
                chain.append(s)
        rules = _resolve_extends(chain, self.repo_root)
        # repository overrides win over everything, including detected domains
        rules.update(self.explicit_rules)
        self.rules = rules
        self.applied_standards = list(dict.fromkeys(chain))
        return self


def _load_org_standard(name: str, repo_root: str | None) -> dict[str, Severity] | None:
    """Resolve an organization standard such as ``company/backend``.

    Org standards live in the repository under ``.deval/standards/<name>.yml``
    (e.g. ``company/backend`` -> ``.deval/standards/company/backend.yml``). They
    use the same shape as a config file and may themselves ``extend`` other
    standards, so companies can compose their own hierarchy.
    """
    if not repo_root:
        return None
    base = Path(repo_root) / ".deval" / "standards"
    for candidate in (base / f"{name}.yml", base / f"{name}.yaml"):
        if candidate.exists():
            data = _load_yaml(candidate.read_text(encoding="utf-8", errors="replace"))
            rules: dict[str, Severity] = {}
            parent = data.get("extends") or []
            if isinstance(parent, str):
                parent = [parent]
            if parent:
                rules.update(_resolve_extends(list(parent), repo_root))
            for rule_id, value in (data.get("rules") or {}).items():
                try:
                    rules[rule_id] = Severity.coerce(value)
                except ValueError:
                    continue
            return rules
    return None


def _resolve_extends(names: list[str], repo_root: str | None = None) -> dict[str, Severity]:
    rules: dict[str, Severity] = {}
    for name in names:
        key = name.split("/", 1)[-1] if name.startswith("deval/") else name
        standard = STANDARDS.get(key) or STANDARDS.get(name)
        if standard is None:
            # Not a built-in Deval standard: treat as an organization standard
            # (e.g. company/backend) resolved from .deval/standards/.
            org = _load_org_standard(name, repo_root)
            if org is None:
                continue
            standard = org
        for rule_id, sev in standard.items():
            rules[rule_id] = sev
    return rules


def load_config(
    repo_root: str | os.PathLike,
    explicit_path: str | None = None,
    profiles: list[str] | None = None,
) -> Config:
    root = Path(repo_root)
    path: Path | None = None
    if explicit_path:
        path = Path(explicit_path)
    else:
        for name in CONFIG_FILENAMES:
            candidate = root / name
            if candidate.exists():
                path = candidate
                break

    data: dict[str, Any] = {}
    if path and path.exists():
        data = _load_yaml(path.read_text(encoding="utf-8", errors="replace"))

    extends = data.get("extends") or ["deval/recommended"]
    if isinstance(extends, str):
        extends = [extends]

    # A CLI ``--profile`` layers on top of the file's extends chain (it wins
    # over the baseline; explicit ``rules:`` below still win over everything).
    if profiles:
        extends = list(extends) + [
            p if p.startswith("deval/") else f"deval/{p}" for p in profiles
        ]

    rules: dict[str, Severity] = _resolve_extends(extends, str(root))
    if not rules:
        rules = dict(recommended_standard())

    explicit_rules: dict[str, Severity] = {}
    for rule_id, value in (data.get("rules") or {}).items():
        try:
            explicit_rules[rule_id] = Severity.coerce(value)
        except ValueError:
            continue
    # Repository overrides win over the resolved extends chain.
    rules.update(explicit_rules)

    autodetect = data.get("autodetect")
    autodetect = True if autodetect is None else bool(autodetect)

    weights: dict[str, float] = {}
    for cat, value in (data.get("weights") or {}).items():
        try:
            weights[cat] = float(value)
        except (TypeError, ValueError):
            continue

    th = data.get("thresholds") or {}
    thresholds = Thresholds(
        min_score=int(th.get("min_score", 0)),
        fail_on=Severity.coerce(th.get("fail_on", "error")),
        max_errors=(int(th["max_errors"]) if th.get("max_errors") is not None else None),
    )

    ignore = data.get("ignore") or []
    if isinstance(ignore, str):
        ignore = [ignore]

    integrations: dict[str, str] = {}
    raw_integrations = data.get("integrations") or {}
    if isinstance(raw_integrations, dict):
        for k, v in raw_integrations.items():
            integrations[k] = str(v)
    elif isinstance(raw_integrations, list):
        for k in raw_integrations:
            integrations[str(k)] = "on"

    if profiles:
        primary = profiles[0]
        standard_label = primary if primary.startswith("deval/") else f"deval/{primary}"
    else:
        standard_label = extends[0] if extends else "deval/recommended"

    return Config(
        standard=standard_label,
        rules=rules,
        weights=weights,
        thresholds=thresholds,
        ignore=[str(x) for x in ignore],
        integrations=integrations,
        source_path=str(path) if path else None,
        extends=list(extends),
        explicit_rules=explicit_rules,
        autodetect=autodetect,
        applied_standards=list(extends),
        repo_root=str(root),
    )
