# Maintainers

| Name | GitHub | Areas |
|---|---|---|
| Morris Darren Babu | [@DARREN-2000](https://github.com/DARREN-2000) | Everything |

Deval has one maintainer. See [GOVERNANCE.md](GOVERNANCE.md) for how decisions
are made and how that list can change.

## Areas of the codebase

Useful if you are opening a PR and wondering who or what it touches:

| Area | Path | Notes |
|---|---|---|
| Rule engine | `src/deval/engine.py`, `registry.py` | Deterministic; no I/O beyond the repo index |
| Checks | `src/deval/checks/` | One module per dimension |
| Rule codes | `src/deval/codes.py` | Stable identifiers; never renumber a shipped code |
| Rule docs | `src/deval/rules_doc.py` | Every rule needs an entry |
| Reporters | `src/deval/reporters/` | terminal, JSON, HTML, Markdown, SARIF, XML |
| Config | `src/deval/config.py` | Dependency-free mini-YAML parser — fuzzed |
| Fuzzing | `fuzz/` | See [fuzz/README.md](fuzz/README.md) |
| Browser demo | `docs/` | Pyodide; runs with integrations and plugins disabled |

## Release process

Releases are cut by tagging `v<version>` matching `pyproject.toml`. The
`release` workflow verifies that match, builds, attests provenance, publishes
to PyPI via trusted publishing, and pushes the container image to GHCR.
