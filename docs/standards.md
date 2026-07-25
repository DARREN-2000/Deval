# Deval Standards

> Deval understands *what you're building*. It starts with a strong universal
> baseline and becomes progressively smarter as it recognizes the technologies
> in your repository.

Standards are the heart of the platform. In Deval's deliberate order
**Standard → Evaluation → Policy → Integrations**, the *Standard* comes first:
the engine, the score, and every integration exist to serve it.

---

## The five-level hierarchy

Every effective ruleset for a repository is resolved by layering standards from
the most general to the most specific. Later levels win.

```
Global Standard          engineering truths that hold for any codebase
        │
        ▼
Deval Recommended        the opinionated, battle-tested baseline
        │
        ▼
Domain Standard          expertise for what you build (fastapi, react, ml, …)
        │
        ▼
Organization Standard    your company's house rules (company/backend)
        │
        ▼
Repository Overrides     the final say for this one repo (rules: in .deval.yml)
```

You compose them explicitly with `extends`:

```yaml
# .deval.yml
extends:
  - deval/recommended
  - deval/python
  - deval/fastapi
  - company/backend

# Repository overrides always win over everything above.
rules:
  require-changelog: error
```

**Precedence, low to high:** `Global → Deval Recommended → extends (domain/org,
in listed order) → auto-detected domain standards → repository rules:`. A repo
override beats an org standard, which beats a domain default, which beats the
baseline.

---

## Standards are packages

Think of a standard like a package: **each one is just a named collection of
rules.** You install (extend) the ones you need and compose them freely.

| Group | Standards |
| --- | --- |
| **Base** | `deval/recommended`, `deval/strict`, `deval/minimal` |
| **Audience** | `deval/startup`, `deval/enterprise`, `deval/oss` |
| **Language** | `deval/python`, `deval/go`, `deval/java` |
| **Framework** | `deval/react`, `deval/nextjs`, `deval/fastapi`, `deval/spring` |
| **Infrastructure** | `deval/docker`, `deval/kubernetes`, `deval/terraform`, `deval/github` |
| **Cloud** | `deval/aws`, `deval/gcp` |
| **Data & AI** | `deval/ml`, `deval/llm`, `deval/data`, `deval/postgres` |
| **Cross-cutting** | `deval/backend`, `deval/microservices`, `deval/security` |

List them any time with `deval standards`.

---

## Universal vs. Domain rules

Deval separates rules into two kinds. This is what lets a brand-new repo get a
useful score immediately while a specialized repo gets deep, relevant scrutiny.

### Universal rules — apply everywhere

They encode engineering practices that are valuable for *any* repository:

- **README** and project documentation
- **LICENSE** and legal clarity
- **Tests** exist and run in CI
- **CI/CD** is present and healthy
- **Dependency hygiene** — lockfiles, audited dependencies

### Domain rules — apply only when relevant

They encode *domain expertise* and only ever run when the matching technology
is detected. On an unrelated repository they are completely inert — they never
fire, pass or fail, and never move the score.

| Domain | A few of the checks |
| --- | --- |
| **FastAPI** | endpoint authentication, health endpoint, OpenAPI docs, Pydantic models, CORS, error handlers |
| **React** | error boundaries, accessibility, lazy loading, component organization, tested components |
| **Kubernetes** | resource limits, liveness/readiness probes, security context, non-root, image pinning |
| **Terraform** | remote state, version pinning, encryption, tags, least-privilege IAM |
| **ML** (`deval/ml`) | experiment tracking, random seeds, dataset & model versioning, evaluation metrics, model cards |
| **LLM / AI** (`deval/llm`) | prompt versioning, evaluation datasets, safety tests, retry policies, structured outputs, telemetry |
| **Microservices** | health & metrics endpoints, tracing, graceful shutdown, timeouts |
| **Data Engineering** (`deval/data`) | dbt tests, schema validation, freshness checks, data contracts |
| **Security** (`deval/security`) | secrets, SBOM, signed commits, dependency risk |
| **Docker** | pinned base image, non-root user |

> ML and LLM deserve special mention: packaging machine-learning and LLM
> engineering best practices into a single *deterministic* standard —
> reproducibility, evaluation datasets, safety tests — is a niche where Deval
> genuinely stands out.

---

## Auto-detection: zero configuration

You don't have to list anything. `deval scan .` inspects the repository,
recognizes the stack, and applies the matching Domain Standards automatically:

```
$ deval scan .

  Detected
    ✓ Python
    ✓ FastAPI
    ✓ Docker
    ✓ GitHub Actions
    ✓ PostgreSQL
    ✓ Terraform

  Applying
    deval/python
    deval/fastapi
    deval/docker
    deval/github
    deval/postgres
    deval/terraform
```

Preview it without scanning:

```bash
deval detect .
```

Detection is conservative and evidence-based (manifests, real import lines, and
config files), so it won't apply a standard it isn't sure about. You always keep
control: set `autodetect: false` in `.deval.yml` to pin an explicit `extends`
chain, and repository `rules:` always override an auto-applied domain default.

---

## Organization standards

Companies compose their own house rules and reference them like any package.
An org standard `company/backend` lives in the repo (or a shared template) at:

```
.deval/standards/company/backend.yml
```

It uses the same shape as a config file and may itself `extend` other standards:

```yaml
# .deval/standards/company/backend.yml
extends:
  - deval/recommended
  - deval/fastapi
rules:
  require-security-policy: error
  fastapi-endpoint-auth: error
```

Then any repository opts in with `extends: [company/backend]`.

---

## Why this fits Deval's identity

Domain Standards make Deval an **Engineering Standards Platform**, not just
another scanner. Standards evolve from generic engineering practices to
domain-specific expertise **without changing the core model**: it is still one
command, one deterministic evaluation, one policy engine, and one Engineering
Health score. The intelligence simply grows with your repository.
