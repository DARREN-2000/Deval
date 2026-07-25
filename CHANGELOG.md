# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.7.0] - 2026-07-25

A distribution and self-conformance release: Deval now scores 100/100 against
its own standard, ships through every channel a team might consume it from, and
runs in the browser.

### Added
- **Zero required runtime dependencies.** PyYAML moved to the optional `yaml`
  extra. The bundled pure-Python YAML reader already covered the config format,
  so `pip install deval` now pulls nothing into your environment and the package
  runs unmodified in locked-down images and WebAssembly.
- **In-browser scanner** at the documentation site. Drop in a repository ZIP and
  get a full report with nothing uploaded — it runs the real engine compiled to
  WebAssembly via Pyodide, not a reimplementation, so the demo cannot drift from
  the shipped tool. Plugin loading is disabled in this mode: Deval will not
  execute Python that came out of an uploaded archive.
- **`docs/build_bundle.py`** — produces a deterministic source bundle for the
  browser runtime, so an unchanged source tree yields a byte-identical artifact.
- **Docker image** published to GHCR, multi-stage and multi-arch
  (`linux/amd64`, `linux/arm64`), running as a non-root user with build
  provenance attestation.
- **Release pipeline** (`release.yml`) — tag-driven publishing to PyPI via OIDC
  trusted publishing (no stored API token), GHCR, and a GitHub Release with
  notes extracted from this changelog. Gated on lint, tests, a clean self-scan,
  a tag/version match check, and a wheel install smoke test.
- **Pages pipeline** (`pages.yml`) — rebuilds the browser bundle from current
  source on every deploy.
- **Manual publish pipeline** (`publish-pypi.yml`) — a `workflow_dispatch`-only
  workflow for publishing to TestPyPI or PyPI without cutting a tag, for
  rehearsing a first upload or recovering from a failed one. It applies the same
  lint/test/self-scan gates as a tagged release, then verifies the built wheel:
  it must contain the package, must not contain the test suite, and must install
  with no transitive dependencies — an executable check on the zero-dependency
  guarantee.
- Dependabot coverage for pip, GitHub Actions, and Docker; issue forms for bug
  reports and rule proposals; a pull request template that requires the
  self-scan to stay at 100.
- Threat model section in `SECURITY.md` documenting that Deval never executes
  the code it scans, and that plugin rules are the sole exception.

### Fixed
- **Deval now scores 100/100 (A+) on itself**, up from 91/100 (A−). A standards
  tool that cannot pass its own standard is not credible.
  - Broke the `model` ↔ `scoring` import cycle by extracting a leaf `grades`
    module (DV7002).
  - Added a CI security stage — Gitleaks, Semgrep, and Trivy, all reporting
    through SARIF to code scanning (DV3003).
  - Added `CODE_OF_CONDUCT.md` (DV1005).
  - Normalised world-writable file permissions (DV4003).
  - Documented the public API: 165 → 106 undocumented functions of 221, clearing
    the documentation threshold (DV6003). Written by hand, explaining rationale
    and failure modes rather than restating signatures.
- The documentation site's scanner never worked: it called into `deval` without
  ever installing it into the Python runtime. Rebuilt so it genuinely runs.
- Corrected placeholder project URLs across `pyproject.toml`, the SARIF report
  driver, the starter config, and `SECURITY.md`.
- Corrected the GitHub Action example, which referenced `format` and `output`
  inputs that `action.yml` does not define.
- **`dockerfile-healthcheck` (DV12002) no longer fires on CLI and batch images.**
  The rule demanded a HEALTHCHECK from any Dockerfile, but Docker only executes
  a healthcheck while a container is alive — an image that does its work and
  exits has nothing to probe. The rule now applies only to images that `EXPOSE`
  a port, and a healthcheck added deliberately to a CLI image still passes. This
  was found by dogfooding: Deval's own image tripped it, and the rule violated
  Deval's stated principle that domain rules stay inert where they do not apply.
  Adding a token healthcheck would have satisfied the rule while telling an
  operator nothing true.
- Dockerfile parsing now joins backslash line continuations and ignores
  comments, so instructions split across lines are detected correctly.

## [0.6.0] - 2026-07-23

A product-contract audit focused on trust, explainability, and first-run
diagnostics.

### Added
- **`deval doctor`** — one preflight for configuration validity, technology
  detection, applied standards, enabled-rule count, stable rule contract, and
  applicable external-tool readiness. Supports a versioned `--json` contract
  and fails when a required integration is unavailable.
- **`deval config --json`** — stable, versioned machine-readable validation for
  CI and editor integrations.

### Fixed
- Closed the explainability gap: all **93 public rules** now have stable DV
  codes and complete Problem / Why / Example / Fix / References output.
- Removed internal orchestration check names from the public rule catalog.
- Corrected stale public documentation from 11 to **13 Engineering Dimensions**
  and added the missing Repository and Structure identities.
- CI now validates Deval's own configuration and rule contract before scanning.
- Restored genuine Python 3.9 compatibility by removing Python 3.10-only union
  syntax while retaining the advertised 3.9–3.13 support matrix.

## [0.5.0] - 2026-07-23

A reviewer pass focused on **discoverability** and **configuration safety** —
two gaps that stood between Deval and a polished, self-explaining platform.

### Added
- **`deval rules`** — browse the entire rule catalog in one place: DV code,
  engineering dimension, universal/domain scope, default severity, and whether
  a rule ships an `explain` doc. Filter with `--dimension`, `--scope`,
  `--undocumented`, render `--json`, or pass `--standard deval/fastapi` to see
  the *effective* severities a given standard would apply. The catalog is
  derived (registry ∪ standards), so a rule can never exist yet be missing
  from it.
- **`deval config`** — validate a `.deval.yml` the same way the engine reads
  it, and surface mistakes that were previously silent: unknown rule ids,
  unknown standards in `extends`, invalid severities, non-numeric weights,
  unknown weight dimensions, bad thresholds, and invalid integration modes —
  each with a "did you mean" suggestion. Exits non-zero on hard errors so it
  can guard CI.

### Internal
- New `catalog.py` (single source of truth for rule enumeration) and
  `config_lint.py` (validation engine), each with focused tests.

## [0.4.0] - 2026-07-23

**Domain Standards** become a first-class concept. Deval evolves from a strong
universal baseline into an engine that understands *what you're building* —
reinforcing its identity as an **Engineering Standards Platform** rather than
just another scanner. The core model is unchanged: still one command, one
deterministic evaluation, one policy engine, one Engineering Health score.

### Added
- **Five-level standards hierarchy**: `Global → Deval Recommended → Domain →
  Organization → Repository Overrides`, composed with `extends:` where later
  levels win. Repository `rules:` always have the final say.
- **Domain Standards as packages**: 26 named standards you compose freely,
  grouped as Base, Audience, Language, Framework, Infrastructure, Cloud,
  Data & AI, and Cross-cutting — including `deval/fastapi`, `deval/react`,
  `deval/nextjs`, `deval/spring`, `deval/kubernetes`, `deval/terraform`,
  `deval/docker`, `deval/github`, `deval/aws`, `deval/gcp`, `deval/postgres`,
  `deval/ml`, `deval/llm`, `deval/data`, `deval/microservices`, and
  `deval/security`.
- **Domain checks** (47 new, inert until their technology is detected):
  FastAPI (auth, health, OpenAPI, Pydantic, CORS, error handlers), React
  (error boundaries, a11y, lazy loading, tests, organization), Kubernetes
  (limits, liveness/readiness probes, security context, non-root, image
  pinning), Terraform (remote state, version pinning, encryption, tags,
  least-privilege IAM), ML (experiment tracking, seeds, dataset/model
  versioning, evaluation metrics, model cards), LLM (prompt versioning,
  eval datasets, safety tests, retries, structured outputs, telemetry),
  Microservices (health, metrics, tracing, graceful shutdown, timeouts),
  Data Engineering (dbt tests, schema validation, freshness, contracts),
  Docker (pinned base, non-root), and Security (SBOM, signed commits).
- **Universal vs. Domain rules**: universal rules (README, LICENSE, tests,
  CI, dependency hygiene) apply everywhere; domain rules apply only when
  relevant. `standards.is_universal()`, `UNIVERSAL_RULES`, `DOMAIN_RULES`.
- **Auto-detection**: `deval scan .` recognizes the stack (Python, Go, Java,
  React, Next.js, FastAPI, Spring, Docker, Kubernetes, Terraform, AWS, GCP,
  PostgreSQL, GitHub Actions, ML, LLM, Data, Microservices) from manifests,
  real import lines, and config files, then applies the matching Domain
  Standards with **no configuration**. Detection is conservative and never
  matches Deval's own source.
- **`deval detect`** command to preview detected technologies and the
  standards that would be applied; the terminal report now prints a
  **Detected / Applying** block.
- **Organization standards**: reference `company/<name>` standards resolved
  from `.deval/standards/<name>.yml`, which may themselves `extend` others.
- **`autodetect: false`** config flag to pin an explicit `extends` chain.
- **docs/standards.md**: the standards guide (hierarchy, packages,
  universal-vs-domain, auto-detection, organization standards).
- Educational `deval explain` docs for the headline domain rules, and stable
  DV codes for every domain rule.

## [0.3.0] - 2026-07-23

Deval matures from a checklist into an **engineering framework**. The core
identity — the Deval Standard, deterministic evaluation, policy, and one
Engineering Health score — is now organized around **Engineering Dimensions**,
and the whole platform is deliberately ordered **Standard → Evaluation → Policy
→ Integrations** so that integrations are an implementation detail, never the
product.

### Added
- **Engineering Dimensions**: every category is now a formal identity with its
  own score and letter grade, rolling up into overall **Engineering Health**.
  Three new dimensions join the existing ones: **Observability** (structured
  logging, error tracking), **Operations** (packaging/deploy descriptors,
  Dockerfile healthcheck), and **Compliance** (machine-readable license,
  dependency auditing). New `dimensions.py` module with per-dimension charters;
  see `docs/dimensions.md`.
- **Stable Rule IDs (DV codes)**: every rule now has a stable code grouped by
  dimension (`DV1001` README, `DV2004` tests, `DV4011` SECURITY.md, ...). New
  `codes.py`; findings, reports, and `deval explain` all accept and display DV
  codes. `deval explain DV1001` resolves a rule by code.
- **Principles**: `docs/principles.md` documents the seven design principles
  (deterministic first, opinionated defaults, extensible policies, repository
  over files, local first, explain every finding, integrate don't reinvent).
- **Expanded standards**: base standards now `deval/minimal`,
  `deval/recommended`, `deval/strict`, plus audience standards
  `deval/enterprise`, `deval/startup`, `deval/oss`; new domain profiles
  `deval/fastapi` and `deval/react` (alongside python/backend/ml/kubernetes).
  `deval standards` lists base standards and domain profiles.
- **Structured explanations**: every rule doc now uses the five teaching
  sections **Problem / Why / Example / Fix / References**.
- **Clean Architecture verification**: architecture checks now recognize
  **Domain → Application → Infrastructure** in addition to
  **Controller → Service → Repository**. New `respect-clean-architecture`
  (`DV7003`) flags dependencies that point outward. The architecture graph
  auto-detects and renders whichever style the repository uses.
- **Trend history with relative days**: `deval trend` now labels entries
  Today / Yesterday / N days ago / Last Week with per-entry grade, a bar, and
  net-change arrows.
- **Ecosystem doc**: `docs/ecosystem.md` documents the platform surfaces —
  `deval` CLI and `deval-action` (today), plus roadmap `deval-server` and
  language SDKs (`deval-python`, `deval-go`, `deval-java`, `deval-rust`).
- **Function-style Rule SDK**: write a rule as a single decorated function,
  `@rule def check_x(repo): ...`, returning `True`, a message, or nothing — no
  subclassing. The named form `@rule("id", "dimension")` and the lower-level
  `@check`/`CheckContext` API remain available.

### Changed
- Reports rebranded to **Engineering Health**; per-dimension grades shown in the
  terminal and Markdown reporters, and findings display their DV code.
- Tagline copy: replaced "One command replaces fifteen" with **"One command
  evaluates your repository and unifies engineering quality into a single
  report."**
- `Finding` gains a `code` property and `CategoryScore` gains a `grade`
  property; both are included in serialized (JSON) output.
- Documentation and README reorganized around the
  **Standard → Evaluation → Policy → Integrations** ordering.

## [0.2.0] - 2026-07-23

Positioning sharpened to **"the open platform for engineering standards"** -
every new feature is a capability of one platform, and everything still rolls up
into a single Engineering Health score.

### Added
- **Profiles**: `deval/python`, `deval/backend`, `deval/startup`,
  `deval/enterprise`, `deval/oss`, `deval/ml`, `deval/kubernetes`. Layer on top
  of the baseline via `extends:` or `--profile`; user `rules:` still win.
  New `deval profiles` command.
- **Explain every finding**: structured rule documentation (Description, Why,
  How to fix, Examples, References). `deval explain <rule>` and a `--explain`
  flag that inlines guidance next to findings, like compiler diagnostics.
- **Baselines**: `deval baseline create` snapshots current violations to
  `.deval/baseline.json`; `deval scan --use-baseline` fails only on NEW
  violations so legacy repos don't fail overnight.
- **Autofix**: `deval fix` safely generates missing scaffolding (LICENSE,
  CODEOWNERS, .editorconfig, .gitignore, SECURITY.md, CODE_OF_CONDUCT.md,
  CONTRIBUTING.md, .dockerignore, README stub). Deterministic only - never
  edits source or guesses. `--dry-run` supported.
- **Incremental mode**: `deval review` scans only changed files (via git or
  `--changed`), for fast PR feedback.
- **Monorepo support**: `--monorepo` detects subprojects under
  `apps/`, `packages/`, `services/`, ... and reports one roll-up score plus a
  score per subproject.
- **Plugins & Rule SDK**: `deval.sdk` exposes `@rule`, `CheckContext`,
  `Finding`, `RepoIndex`. Plugins load from `.deval/plugins/`,
  `~/.deval/plugins/`, and `$DEVAL_PLUGIN_PATH`. Core stays language-agnostic.
- **Rule marketplace**: bundled packs (`kubernetes`, `react`,
  `company/security`); `deval install <pack>` and `deval plugins`. Packs are
  inert until their trigger files are present.
- **Public badge**: `deval badge` renders a self-contained Engineering Health
  SVG (color by grade) plus a Markdown embed snippet.
- **Scoring weights**: per-category weights in config (`weights:`).
- **Suppressions**: `deval-ignore.yml` and inline `# deval-ignore <rule>`
  comments; suppressed findings are counted for honesty.
- **Rule testing**: `deval test-rule <dir>` runs rule test cases (each case a
  tiny repo + `expect.txt`) for rule authors.
- **Multiple outputs**: added **XML** (JUnit-style) reporter alongside terminal,
  json, sarif, markdown, html.
- **Architecture graph**: `deval graph` auto-generates the
  Controller -> Service -> Repository diagram in Mermaid or Graphviz DOT,
  highlighting layering violations.
- **Benchmark**: `deval benchmark` compares your score against published
  reference scores (FastAPI, Kubernetes, React, LangChain) - fully offline, no
  code download.
- **Trend analysis**: `deval trend` renders Repository Health over time from
  saved history.
- **Opt-in policy rules**: `require-opentelemetry`, `require-authentication`,
  `no-direct-sql`, `no-console-log`, `require-dockerignore`,
  `require-editorconfig` (all off by default; enabled by profiles/config).

### Changed
- `ScanResult` now records `suppressed` and `baselined` counts (also in JSON).
- Config `load_config` accepts a `profiles` argument.
- Scan pipeline now loads plugins, applies suppressions, and optionally applies
  baselines and changed-file filtering - all deterministically.

### Roadmap
- **Deval Cloud** (future): team trends, dashboards, and PR analytics on top of
  the same deterministic engine. The CLI remains fully open source.

## [0.1.0] - 2026-07-23

### Added
- Initial release of the Deval Engineering Standards Platform.
- Layer 1: standards engine (`extends` + `rules`), deterministic scoring,
  per-category and overall health score with letter grades, and a PASS/FAIL
  quality gate.
- Layer 2: native checks across 10 categories (repository, documentation,
  architecture, structure, dependencies, testing, CI, security,
  maintainability, ownership).
- Layer 3: external integrations for Ruff, ESLint, Semgrep, Gitleaks, Trivy and
  Checkov, with SARIF normalization and duplicate removal.
- Reporters: terminal, JSON, SARIF, self-contained HTML dashboard with trend
  line, and Markdown for PR comments.
- CLI: `scan`, `init`, `report`, `explain`, `standards`.
- GitHub Action and reference CI workflow.
