# Deval

[![ci](https://github.com/DARREN-2000/deval/actions/workflows/ci.yml/badge.svg)](https://github.com/DARREN-2000/deval/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/deval.svg)](https://pypi.org/project/deval/)
[![Python](https://img.shields.io/pypi/pyversions/deval.svg)](https://pypi.org/project/deval/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Self-scan](https://img.shields.io/badge/deval%20self--scan-100%2F100%20A%2B-22c55e.svg)](https://darren-2000.github.io/deval/)

**The open platform for engineering standards.**

**[Try it in your browser →](https://darren-2000.github.io/deval/)** — drop in a repository ZIP
and get a full report. No install; the real engine runs locally via WebAssembly.

Define engineering standards once. Continuously evaluate every repository. Enforce quality deterministically.

```bash
deval scan .
```

**One command evaluates your repository and unifies engineering quality into a
single report.** Deval evaluates an entire repository against a strong built-in
standard (or a domain **profile**), performs a **deterministic** code review
(facts, not AI guesses), aggregates results from best-in-class tools, removes
duplicate findings, and produces a single **Engineering Health score** across
thirteen **Engineering Dimensions**.

Deval is built in one deliberate order — **Standard → Evaluation → Policy →
Integrations.** The standard and the native engine are the product; integrations
are an implementation detail. If every integration disappeared tomorrow, Deval
would still be valuable on its own. See [docs/principles.md](docs/principles.md)
for the design philosophy and [docs/dimensions.md](docs/dimensions.md) for the
Engineering Dimensions framework.

---

## Domain Standards — Deval understands what you're building

Deval doesn't just apply generic rules. It recognizes your stack and layers on
**domain expertise**, so a FastAPI service, a Kubernetes chart, and an ML
project are each held to the standards that actually matter for them.

Standards compose in a five-level hierarchy — later levels win:

```
Global Standard → Deval Recommended → Domain Standard → Organization Standard → Repository Overrides
```

```yaml
# .deval.yml
extends:
  - deval/recommended
  - deval/python
  - deval/fastapi
  - company/backend
```

**Think of standards like packages** — each is just a named collection of rules
(`deval/python`, `deval/react`, `deval/ml`, `deval/llm`, `deval/kubernetes`, …).
Rules split into two kinds:

- **Universal** rules apply everywhere: README, LICENSE, tests, CI, dependency
  hygiene. Every repo gets a useful baseline immediately.
- **Domain** rules apply only when the technology is detected: FastAPI auth,
  React accessibility, Kubernetes probes, ML reproducibility, LLM evaluation
  datasets. On unrelated repos they stay completely inert.

### Zero configuration: `deval scan .` auto-detects your stack

```
  Detected
    ✓ Python   ✓ FastAPI   ✓ Docker   ✓ GitHub Actions   ✓ PostgreSQL   ✓ Terraform

  Applying
    deval/python  deval/fastapi  deval/docker  deval/github  deval/postgres  deval/terraform
```

Preview detection with `deval detect .`, or list every standard with
`deval standards`. Full guide: **[docs/standards.md](docs/standards.md)**.

---

## Why Deval

Today engineering quality is fragmented across Ruff, ESLint, Semgrep, Trivy,
Gitleaks, Hadolint, ShellCheck, Markdownlint, Actionlint, Checkov, unit tests
and coverage tools. Every tool has a different config, output, severity and CI
step - and none of them answer the real question:

> **Is this repository production-ready?**

Deval does, with **one number everyone understands**.

## One platform, many capabilities

Deval is *the open platform for engineering standards*. Everything else is a
capability of that one platform:

- ✅ **Deval Standard** & **Profiles** - opinionated baselines you extend
- ✅ **Repository Evaluation** across 13 **Engineering Dimensions**
- ✅ **Stable Rule IDs** - every rule has a DV code (`DV1001`, `DV2004`, ...)
- ✅ **Policy Engine** - opt-in organizational policies
- ✅ **Deterministic Code Review** - pass/fail facts with file/line + fix
- ✅ **Engineering Health Score** - one number, one grade, per-dimension grades
- ✅ **Native Checks** (no external tools required)
- ✅ **Integrations** (Ruff, ESLint, Semgrep, Gitleaks, Trivy, Checkov, ...)
- ✅ **Plugins** & a **Rule SDK** - write a rule as one decorated function
- ✅ **Trends**, **Baselines**, **Autofix (where safe)**, and rich **Reports**

## The three layers

```
                    Deval
     The open platform for engineering standards
------------------------------------------------
  Layer 1  Deval Intelligence          (scoring, gate, standards + profiles)
  Layer 2  Native Deterministic Checks (13 dimensions, zero external tools)
  Layer 3  External Integrations       (detect, run, normalize, de-dupe)
```

The layers exist in a strict order of importance — **Standard → Evaluation →
Policy → Integrations**. Integrations are last on purpose: Deval is a standard
you evaluate against, not a wrapper around other tools.

## Profiles ⭐

Instead of one baseline, pick the profile that matches how you build software
and extend it. Profiles layer on top of `deval/recommended`; your own `rules:`
always win.

```yaml
extends:
  - deval/backend          # or python, startup, enterprise, oss, ml, kubernetes
rules:
  require-opentelemetry: error
```

| Profile | For | Emphasis |
|---|---|---|
| `deval/python` | Python libs & services | reproducibility, layout, coverage |
| `deval/backend` | Backend services | layering, no raw SQL, auth, tracing |
| `deval/startup` | Early-stage teams | lenient, keeps only guardrails that hurt |
| `deval/enterprise` | Regulated orgs | ownership, security policy, auditability |
| `deval/oss` | Open source | license, contributing, code of conduct |
| `deval/ml` | ML repos | reproducibility, no huge artifacts in git |
| `deval/kubernetes` | Infra repos | supply-chain, manifest security |
| `deval/fastapi` | FastAPI services | layering, auth, tracing, typed endpoints |
| `deval/react` | React front-ends | no stray logs, tested components, clean layout |

Base standards escalate in strictness: `deval/minimal` → `deval/recommended`
→ `deval/strict`, plus audience standards `deval/enterprise`, `deval/startup`,
and `deval/oss`.

```bash
deval standards                # list base standards + domain profiles
deval profiles                 # list the domain profiles
deval scan . --profile backend # evaluate against a profile ad-hoc
```

## Engineering Dimensions - one framework, thirteen identities

Deval is not a flat checklist. Every rule rolls up into one of thirteen
**Engineering Dimensions**, each with its own score and letter grade:

```
Engineering Health

  Architecture      A
  Security          A+
  Testing           B
  Operations        A
  Observability     C

  Overall           93
```

| Dimension | Examples |
|---|---|
| Architecture | layering (Controller -> Service -> Repository **or** Domain -> Application -> Infrastructure), import cycles |
| Documentation | required sections, broken relative links, undocumented APIs |
| Testing | tests present, test-to-source ratio, coverage config |
| Security | hardcoded secrets, unsafe files, SECURITY.md, permissions |
| Dependencies | lockfiles, duplicate deps, unpinned actions |
| CI/CD | pipeline present, runs tests, security scan, caching |
| Ownership | CODEOWNERS, maintainers |
| Maintainability | huge files, TODO/FIXME debt, committed build artifacts |
| Observability | structured logging, error tracking (asserted for services) |
| Operations | packaging/deploy descriptors, Dockerfile healthcheck |
| Compliance | machine-readable license, automated dependency auditing |
| Repository | README, LICENSE, CONTRIBUTING, gitignore, changelog |
| Structure | conventional source and test layout |

Every rule has a **stable DV code** grouped by dimension, so findings and docs
stay clean: `DV1001 Missing README`, `DV2004 Missing Tests`,
`DV4011 Missing SECURITY.md`. See [docs/dimensions.md](docs/dimensions.md).

Plus **opt-in policy rules** (off by default, enabled by profiles or config):
`require-opentelemetry`, `require-authentication`, `no-direct-sql`,
`no-console-log`, `require-dockerignore`, `require-editorconfig`.

## Install

```bash
pip install deval
```

**Deval has zero required runtime dependencies.** It ships a small pure-Python
YAML reader and uses PyYAML automatically if it is already installed, so it
never pulls a dependency tree into your environment and runs unmodified in
locked-down CI images and WebAssembly.

```bash
pip install "deval[yaml]"   # opt in to full PyYAML support
pip install -e ".[dev]"     # from source, with the test and lint tooling
```

### Docker

```bash
# Scan the current directory, mounted read-only, running as a non-root user
docker run --rm -v "$PWD:/repo:ro" ghcr.io/darren-2000/deval:latest

# Pin a version for reproducible pipelines
docker run --rm -v "$PWD:/repo:ro" ghcr.io/darren-2000/deval:0.7.0 scan . -f markdown
```

### GitHub Action

```yaml
- uses: DARREN-2000/deval@v1
  id: deval
  with:
    path: .
    min-score: '80'
    upload-sarif: 'true'
- uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: report.sarif
```

The action exposes `score`, `grade`, and `passed` as step outputs.

Requires Python 3.9–3.13.

## Commands

```bash
# Evaluate & enforce
deval scan .                        # terminal report + PASS/FAIL exit code
deval scan . --profile backend      # evaluate against a profile
deval scan . --explain              # append Why + How to fix to each finding
deval scan . --use-baseline         # only NEW violations fail
deval scan . --monorepo             # one score + a score per subproject
deval review                        # incremental: only changed files (fast, for PRs)

# Outputs (terminal | json | sarif | markdown | html | xml)
deval scan . -f sarif -o report.sarif    # GitHub Code Scanning
deval scan . -f xml   -o report.xml      # JUnit-style CI ingestion
deval scan . -f html  -o report.html     # self-contained dashboard w/ trends

# Adoption & insight
deval baseline create               # snapshot today's violations (.deval/baseline.json)
deval trend .                       # Repository Health over time
deval benchmark .                   # compare vs FastAPI / Kubernetes / React / LangChain
deval badge . -o deval-badge.svg    # public Engineering Health badge
deval graph . --format mermaid      # auto-generated architecture graph
deval fix . --dry-run               # safe, deterministic autofix (missing LICENSE, ...)

# Ecosystem
deval plugins                       # list installed + available rule packs
deval install kubernetes            # install a marketplace pack
deval test-rule ./rule_cases        # run rule test cases (for rule authors)

# Basics
deval init                          # write a starter .deval.yml
deval doctor .                      # preflight config, standards, rules + tools
deval config .                      # validate config; typo suggestions + CI exit code
deval config . --json               # stable machine-readable validation contract
deval rules                         # browse all 93 coded, documented rules
deval report .                      # score + delta vs. last run
deval explain require-codeowners    # Problem / Why / Example / Fix / References
deval explain DV1001                # ...or look a rule up by its DV code
deval standards                     # list base standards + domain profiles
```

Exit codes: `0` success/gate passed, `1` gate failed, `2` usage/error.

## Explain every finding

Deval treats findings like compiler diagnostics. Every rule ships with the same
five teaching sections — **Problem, Why, Example, Fix, References** — and is
addressable by slug or DV code:

```
$ deval explain DV1001
DV1001  require-readme
Repository dimension

Problem
  The repository must contain a README.

Why
  A README is the first point of entry; without it newcomers cannot tell what
  the project does or how to run it.

Example
  - README.md
  - README.rst

Fix
  Create README.md with a short description, install steps, and usage.

References
  - https://www.makeareadme.com/
```

Add `--explain` to any scan to inline this guidance next to the findings.

## Baselines - adopt on legacy repos without failing overnight

```bash
deval baseline create          # records current violations to .deval/baseline.json
deval scan . --use-baseline    # only NEW violations fail the gate
```

## Autofix - deterministic only, never guesses

`deval fix` safely generates missing scaffolding it can produce correctly:
LICENSE, CODEOWNERS, .editorconfig, .gitignore, SECURITY.md, CODE_OF_CONDUCT.md,
CONTRIBUTING.md, .dockerignore, and a README stub. It never edits source code.

## Plugins & the Rule SDK

The core stays language-agnostic. Everything language- or domain-specific is a
plugin: a Python file in `.deval/plugins/` (repo-local) or `~/.deval/plugins/`
(user) that registers rules through the SDK.

Writing a rule should feel like writing a function, not subclassing a framework.
A rule receives a friendly `repo` and returns `True`, a message string, or
nothing:

```python
from deval.sdk import rule

@rule
def check_license(repo):
    return repo.has("LICENSE", "LICENSE.md") or "Missing LICENSE"
```

Name it and pin its dimension when you want control — the lower-level
`@check`/`CheckContext` API the built-ins use is still available:

```python
from deval.sdk import rule

@rule("require-license", "compliance")
def license_rule(repo):
    if repo.has("LICENSE", "LICENSE.md"):
        return repo.passed("LICENSE present")
    return repo.violation("Missing LICENSE", remediation="Add a LICENSE file.")
```

The bundled **marketplace** ships packs you can install: `kubernetes`, `react`,
`company/security`. Packs are inert until their trigger files are present, so
installing one never changes an unrelated repository's score.

## Configuration

```yaml
# .deval.yml
version: 1
extends:
  - deval/backend
rules:
  require-authentication: error
  no-console-log: warning
  require-changelog: off
weights:              # tune what your org cares about
  security: 5
  testing: 4
  documentation: 1
thresholds:
  min_score: 80
  fail_on: error
ignore:
  - "examples/**"
```

Suppress consciously-accepted findings via `deval-ignore.yml` or inline
`# deval-ignore <rule>` comments.

Base standards: `deval/minimal`, `deval/recommended`, `deval/strict`,
`deval/enterprise`, `deval/startup`, `deval/oss`.
Domain profiles: `deval/python`, `deval/backend`, `deval/ml`,
`deval/kubernetes`, `deval/fastapi`, `deval/react`.

## CI in one step

```yaml
# .github/workflows/deval.yml
name: deval
on: [push, pull_request]
jobs:
  deval:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: ./            # or deval/action@<sha>
        with:
          min-score: "85"
```

## Ecosystem & roadmap

Deval is a platform, not a single binary. The `deval` CLI and the GitHub Action
(`deval-action`) ship today; language SDKs (`deval-python`, `deval-go`,
`deval-java`, `deval-rust`) and a central `deval-server` for org-wide dashboards
are on the roadmap. Every surface shares one contract: the Deval Standard,
Engineering Dimensions, deterministic findings, and one Engineering Health
score. See [docs/ecosystem.md](docs/ecosystem.md). Nothing in the open-source
gate depends on any server.

## Design principles

Deval's full design philosophy lives in [docs/principles.md](docs/principles.md):

1. **Deterministic first** - identical inputs always produce identical findings.
2. **Opinionated defaults** - `deval scan .` is useful with zero config.
3. **Extensible policies** - your standard is code you version and extend.
4. **Repository over files** - the repository is the unit of quality.
5. **Local first** - the full report runs offline; local == CI.
6. **Explain every finding** - Problem / Why / Example / Fix / References.
7. **Integrate, don't reinvent** - integrations are an implementation detail.

## Architecture

```
src/deval/
  model.py         Finding / CategoryScore / ScanResult
  fsindex.py       one-pass, ignore-aware repository index
  config.py        .deval.yml loading + extends/profile resolution
  standards.py     minimal/recommended/strict + enterprise/startup/oss + domain profiles
  codes.py         stable DV rule codes (DV1001, DV2004, ...)
  dimensions.py    the thirteen Engineering Dimensions + charters
  registry.py      check registration + safe execution
  rules_doc.py     structured Problem/Why/Example/Fix/References
  checks/          Layer 2 native checks (13 dimensions incl. obs/ops/compliance) + policies
  integrations/    Layer 3 adapters + SARIF normalization
  scoring.py       deterministic scores + quality gate
  suppressions.py  deval-ignore.yml + inline suppressions
  baseline.py      baseline create/apply
  fix.py           safe deterministic autofix
  graph.py         architecture graph (mermaid/dot)
  monorepo.py      subproject detection + roll-up
  benchmark.py     reference-score comparison
  badge.py         Engineering Health SVG badge
  plugins.py       plugin discovery + marketplace install
  sdk.py           public Rule SDK
  marketplace/     bundled rule packs (kubernetes, react, company/security)
  reporters/       terminal, json, sarif, html, markdown, xml
  engine.py        the scan pipeline
  cli.py           the deval command
```

## License

MIT - see [LICENSE](LICENSE).
