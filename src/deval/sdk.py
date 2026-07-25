"""Public Rule SDK for third-party and community rule authors.

Writing a rule should feel like writing a function, not subclassing a framework.
Drop a Python file into a plugin directory (``.deval/plugins/`` in a repo, or
``~/.deval/plugins/``) and decorate a function with ``@rule``::

    from deval.sdk import rule

    @rule
    def check_license(repo):
        # Every repository must carry an explicit license file.
        return repo.has("LICENSE", "LICENSE.md") or "Missing LICENSE"

That is the whole contract. A rule receives a :class:`Repo` (a friendly view of
the repository) and may return:

* ``True``  - the standard is satisfied (a passing finding)
* ``False`` - a violation, with a generic message
* ``str``   - a violation, using the string as the message
* a :class:`Finding` (via ``repo.ok(...)`` / ``repo.fail(...)``) or an iterable
  of them, for full control
* ``None``  - emit nothing (the rule did not apply)

The rule id defaults to the function name (``check_license`` -> ``check-license``)
and can be set explicitly. Categories must be one of the engineering dimensions
so findings roll up into the Engineering Health score.

    @rule("require-license", "compliance")
    def license_rule(repo):
        # Same rule, with an explicit id and engineering dimension.
        ...

The lower-level ``@check(name, category)`` decorator (a generator that takes a
:class:`CheckContext` and yields findings) is still exported for advanced use
and is what the built-in checks use.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Callable

from .fsindex import RepoFile, RepoIndex
from .model import CATEGORIES, Finding, Severity
from .registry import CheckContext, check

__all__ = [
    "CATEGORIES",
    "CheckContext",
    "Finding",
    "Repo",
    "RepoFile",
    "RepoIndex",
    "Severity",
    "check",
    "rule",
]

_DEFAULT_CATEGORY = "maintainability"


@dataclass
class Repo(CheckContext):
    """A friendly, read-only view of the repository passed to SDK rules.

    Subclasses :class:`CheckContext`, so ``repo.ok(...)`` / ``repo.fail(...)`` and
    ``repo.index`` behave exactly as in the built-in checks, while adding terse
    helpers so simple rules read like plain questions about the repo.
    """

    rule_id: str = ""
    category: str = _DEFAULT_CATEGORY

    # --- terse helpers -----------------------------------------------------
    def has(self, *names: str) -> bool:
        """Return ``True`` if the repository contains any of ``names``.

        Pass several spellings at once, e.g. ``repo.has("LICENSE", "LICENSE.md")``.
        """
        return self.index.has(*names)

    def find(self, relpath: str):
        """Return the :class:`RepoFile` at ``relpath``, or ``None`` if absent."""
        return self.index.find(relpath)

    def glob(self, pattern: str):
        """Return every repository file matching the glob ``pattern``."""
        return self.index.glob(pattern)

    def by_suffix(self, *suffixes: str):
        """Return every repository file with one of the given extensions.

        Extensions include the leading dot, e.g. ``repo.by_suffix(".ts", ".tsx")``.
        """
        return self.index.by_suffix(*suffixes)

    def read_text(self, rf, max_bytes: int = 2_000_000) -> str:
        """Read ``rf`` as text, returning ``""`` if it cannot be read.

        Never raises, so a rule cannot be broken by an unreadable file.
        """
        return self.index.read_text(rf, max_bytes=max_bytes)

    @property
    def files(self):
        """Every indexed file in the repository, sorted by relative path."""
        return self.index.files

    @property
    def root(self):
        """Absolute :class:`~pathlib.Path` to the repository root."""
        return self.index.root

    # --- zero-argument convenience emitters --------------------------------
    def passed(self, message: str, **kw) -> Finding:
        """Emit a passing finding for the current rule.

        The rule id and category are filled in automatically, so a rule body
        only supplies the human-readable ``message``.
        """
        return self.ok(self.rule_id, self.category, message, **kw)

    def violation(self, message: str, **kw) -> Finding:
        """Emit a failing finding for the current rule.

        Supply ``remediation=`` (and ``path=``/``line=`` when known) to tell the
        developer how and where to fix it.
        """
        return self.fail(self.rule_id, self.category, message, **kw)


def _infer_id(func_name: str) -> str:
    name = func_name.replace("_", "-").strip("-")
    for prefix in ("check-", "rule-"):
        name = name.removeprefix(prefix)
    return name or func_name


def _normalize(out: Any, repo: Repo) -> Iterable[Finding]:
    if out is None:
        return
    if isinstance(out, Finding):
        yield out
        return
    if isinstance(out, bool):
        yield (repo.passed(f"{repo.rule_id} satisfied")
               if out else repo.violation(f"{repo.rule_id} failed"))
        return
    if isinstance(out, str):
        yield repo.violation(out)
        return
    if isinstance(out, Iterable):
        for item in out:
            if isinstance(item, Finding):
                yield item
        return


def _adapt(fn: Callable[[Repo], Any], rule_id: str, category: str) -> Callable:
    @check(rule_id, category)
    def _wrapped(ctx: CheckContext) -> Iterable[Finding]:
        repo = Repo(index=ctx.index, config=ctx.config, rule_id=rule_id, category=category)
        yield from _normalize(fn(repo), repo)

    return fn


def rule(arg: Any = None, category: str = _DEFAULT_CATEGORY, *, id: str | None = None):
    """Register a rule. Usable bare (``@rule``) or parameterized.

    ``@rule``                      - id inferred from the function name
    ``@rule("require-x", "security")`` - explicit id and dimension
    ``@rule(category="testing")``  - keyword-only category
    """
    # Bare usage: @rule on the function directly.
    if callable(arg):
        return _adapt(arg, id or _infer_id(arg.__name__), category)

    explicit_id = arg if isinstance(arg, str) else id

    def decorator(fn: Callable[[Repo], Any]) -> Callable:
        """Adapt and register ``fn`` as a rule, returning the wrapped check."""
        return _adapt(fn, explicit_id or _infer_id(fn.__name__), category)

    return decorator
