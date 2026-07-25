# Contributing to Deval

Thanks for helping make engineering quality deterministic, measurable, and
effortless!

## Development setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

Deval eats its own dog food - run it on itself:

```bash
deval scan .
```

## Adding a check

Checks live in `src/deval/checks/<category>.py` and self-register:

```python
from ..registry import CheckContext, check

@check("my-check", "security")
def my_check(ctx: CheckContext):
    if ctx.index.has("THING"):
        yield ctx.ok("my-rule", "security", "THING present")
    else:
        yield ctx.fail("my-rule", "security", "Missing THING",
                       remediation="Add THING.")
```

Then:

1. Add the rule's default severity to `standards.py`.
2. Add a one-line explanation to `rules_doc.py`.
3. Add a test in `tests/`.

Every check must be **deterministic** and **side-effect free**.

## Adding an integration

Subclass `Integration` in `src/deval/integrations/adapters.py`, implement
`command()` and `normalize()`, and add it to `default_integrations()`. Map
findings onto existing native rule ids where possible so de-duplication works.

## Pull requests

- Keep changes focused and covered by tests.
- Run `pytest` and `deval scan .` before opening a PR.
- Describe the user-facing impact in the PR description.
