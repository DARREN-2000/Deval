"""Built-in standards and profiles.

A *standard* is a map of rule id -> default severity. ``deval/recommended`` is
the opinionated baseline that makes ``deval scan .`` useful with zero config.

*Profiles* are standards tuned for a domain (python, backend, startup,
enterprise, oss, ml, kubernetes). They are the killer differentiator: instead of
one baseline, a team picks the profile that matches how they build software and
extends it:

    extends:
      - deval/backend
    rules:
      require-opentelemetry: error

Profiles are layered by the ``extends`` resolver, so ``[deval/recommended,
deval/oss]`` merges cleanly, later entries winning.
"""

from __future__ import annotations

from .model import Severity

E = Severity.ERROR
W = Severity.WARNING
I = Severity.INFO
OFF = Severity.OFF


def recommended_standard() -> dict[str, Severity]:
    """Broadly accepted engineering best practices. Sensible for most repos."""
    return {
        # repository
        "require-readme": E,
        "require-license": E,
        "require-contributing": W,
        "require-gitignore": W,
        "require-code-of-conduct": I,
        "require-changelog": I,
        # documentation
        "readme-has-sections": W,
        "no-broken-relative-links": W,
        "documented-public-api": I,
        # architecture
        "respect-layering": W,
        "no-cross-module-cycles": W,
        # structure
        "conventional-source-layout": W,
        "tests-directory-present": W,
        # dependencies
        "require-lockfile": W,
        "no-duplicate-dependencies": W,
        "no-abandoned-markers": I,
        "pinned-github-actions": W,
        # testing
        "tests-present": E,
        "reasonable-test-ratio": W,
        "coverage-config-present": I,
        # ci
        "require-ci": E,
        "ci-runs-tests": W,
        "ci-has-security-scan": I,
        "ci-uses-cache": I,
        # security
        "no-hardcoded-secrets": E,
        "no-unsafe-files": E,
        "require-security-policy": I,
        "no-world-writable": W,
        # maintainability
        "no-huge-files": W,
        "bounded-todo-debt": I,
        "no-committed-build-artifacts": W,
        # ownership
        "require-codeowners": W,
        "require-maintainers": I,
        # observability
        "observable-logging": I,
        "error-tracking": OFF,
        # operations
        "deployable-artifact": I,
        "dockerfile-healthcheck": I,
        # compliance
        "declared-license": I,
        "dependency-audit": OFF,
        # opt-in policy rules (off by default, enable via config/profile)
        "require-opentelemetry": OFF,
        "require-authentication": OFF,
        "no-direct-sql": OFF,
        "no-console-log": OFF,
        "require-dockerignore": OFF,
        "require-editorconfig": OFF,
    }


def strict_standard() -> dict[str, Severity]:
    """Everything in recommended, escalated for production-critical repos."""
    base = recommended_standard()
    base.update({
        "require-contributing": E,
        "require-gitignore": E,
        "require-changelog": W,
        "no-broken-relative-links": E,
        "documented-public-api": W,
        "respect-layering": E,
        "no-cross-module-cycles": E,
        "conventional-source-layout": E,
        "tests-directory-present": E,
        "require-lockfile": E,
        "no-duplicate-dependencies": E,
        "pinned-github-actions": E,
        "reasonable-test-ratio": E,
        "coverage-config-present": W,
        "ci-runs-tests": E,
        "ci-has-security-scan": W,
        "require-security-policy": W,
        "no-huge-files": E,
        "bounded-todo-debt": W,
        "no-committed-build-artifacts": E,
        "require-codeowners": E,
        "require-maintainers": W,
        "require-dockerignore": W,
        "require-editorconfig": I,
    })
    return base


def minimal_standard() -> dict[str, Severity]:
    """The smallest useful gate: a repo must at least be documented and tested."""
    return {
        "require-readme": E,
        "require-license": W,
        "tests-present": E,
        "require-ci": W,
        "no-hardcoded-secrets": E,
        "no-unsafe-files": E,
    }


# --- Profiles ---------------------------------------------------------------

def python_profile() -> dict[str, Severity]:
    """Python services and libraries: reproducibility and typed, tested code."""
    base = recommended_standard()
    base.update({
        "require-lockfile": E,
        "coverage-config-present": W,
        "reasonable-test-ratio": W,
        "conventional-source-layout": E,
        "require-editorconfig": I,
    })
    return base


def backend_profile() -> dict[str, Severity]:
    """Backend services: architecture discipline, security, and observability."""
    base = recommended_standard()
    base.update({
        "respect-layering": E,
        "no-cross-module-cycles": E,
        "no-direct-sql": E,
        "require-authentication": W,
        "require-opentelemetry": W,
        "observable-logging": W,
        "error-tracking": W,
        "deployable-artifact": W,
        "ci-has-security-scan": W,
        "require-security-policy": W,
        "require-lockfile": E,
    })
    return base


def fastapi_profile() -> dict[str, Severity]:
    """FastAPI services: clean layering, auth, tracing, and typed endpoints."""
    base = backend_profile()
    base.update({
        "respect-layering": E,
        "respect-clean-architecture": W,
        "no-direct-sql": E,
        "require-authentication": E,
        "require-opentelemetry": W,
        "observable-logging": E,
        "error-tracking": W,
        "deployable-artifact": W,
        "dockerfile-healthcheck": W,
        "documented-public-api": W,
        "coverage-config-present": W,
    })
    return base


def react_profile() -> dict[str, Severity]:
    """React front-ends: no stray console logging, tested components, clean layout."""
    base = recommended_standard()
    base.update({
        "no-console-log": W,
        "reasonable-test-ratio": W,
        "conventional-source-layout": W,
        "documented-public-api": I,
        "require-lockfile": E,
        "no-committed-build-artifacts": E,
        "observable-logging": OFF,
        "deployable-artifact": I,
    })
    return base


def startup_profile() -> dict[str, Severity]:
    """Move fast without breaking security: a lenient but safe gate."""
    base = recommended_standard()
    base.update({
        "require-contributing": OFF,
        "require-code-of-conduct": OFF,
        "require-changelog": OFF,
        "documented-public-api": OFF,
        "require-maintainers": OFF,
        "reasonable-test-ratio": I,
        # keep the guardrails that actually hurt if broken
        "no-hardcoded-secrets": E,
        "no-unsafe-files": E,
        "tests-present": W,
    })
    return base


def enterprise_profile() -> dict[str, Severity]:
    """Governance-grade: ownership, security policy, and auditability enforced."""
    base = strict_standard()
    base.update({
        "require-codeowners": E,
        "require-maintainers": E,
        "require-security-policy": E,
        "require-authentication": E,
        "require-opentelemetry": W,
        "no-direct-sql": E,
        "ci-has-security-scan": E,
        "bounded-todo-debt": W,
    })
    return base


def oss_profile() -> dict[str, Severity]:
    """Open-source projects: welcoming, licensed, and contributor-friendly."""
    base = recommended_standard()
    base.update({
        "require-license": E,
        "require-contributing": E,
        "require-code-of-conduct": W,
        "require-changelog": W,
        "require-security-policy": W,
        "readme-has-sections": E,
        "no-broken-relative-links": E,
        "require-codeowners": W,
    })
    return base


def ml_profile() -> dict[str, Severity]:
    """Machine-learning repos: reproducibility, data hygiene, and tests."""
    base = recommended_standard()
    base.update({
        "require-lockfile": E,
        "no-hardcoded-secrets": E,
        "no-huge-files": E,          # datasets/checkpoints do not belong in git
        "no-committed-build-artifacts": E,
        "tests-present": W,
        "coverage-config-present": I,
        "require-opentelemetry": OFF,
    })
    return base


def kubernetes_profile() -> dict[str, Severity]:
    """Infra / Kubernetes repos: supply-chain and manifest security first."""
    base = recommended_standard()
    base.update({
        "pinned-github-actions": E,
        "ci-has-security-scan": E,
        "no-unsafe-files": E,
        "no-hardcoded-secrets": E,
        "require-dockerignore": W,
        "require-security-policy": W,
        # domain rules (inert unless Kubernetes manifests are detected)
        "k8s-resource-limits": W,
        "k8s-liveness-probe": W,
        "k8s-readiness-probe": W,
        "k8s-security-context": E,
        "k8s-non-root": E,
        "k8s-image-pinning": W,
    })
    return base


# --- Domain Standards -------------------------------------------------------
#
# Each of these is "just a collection of rules", like a package. They layer a
# handful of *domain rules* (checks that only make sense for a given technology)
# on top of the universal baseline. Every domain rule is OFF in
# ``deval/recommended`` and inert unless the technology is detected, so pulling
# in a domain standard never fires rules for a technology you are not using.

def _domain(overrides: dict[str, Severity]) -> dict[str, Severity]:
    """A domain standard = the recommended baseline + domain-specific rules."""
    base = recommended_standard()
    base.update(overrides)
    return base


def go_profile() -> dict[str, Severity]:
    """Go modules and services."""
    return _domain({
        "require-lockfile": E,          # go.sum
        "conventional-source-layout": W,
        "no-cross-module-cycles": E,
    })


def java_profile() -> dict[str, Severity]:
    """JVM / Java projects."""
    return _domain({
        "require-lockfile": W,
        "respect-layering": W,
        "no-cross-module-cycles": W,
    })


def nextjs_profile() -> dict[str, Severity]:
    """Next.js applications."""
    base = react_profile()
    base.update({
        "react-error-boundaries": W,
        "react-lazy-loading": I,
        "react-accessibility": W,
        "react-testing": W,
        "react-component-organization": I,
    })
    return base


def spring_profile() -> dict[str, Severity]:
    """Spring / Spring Boot services."""
    base = backend_profile()
    base.update({
        "respect-layering": E,
        "no-cross-module-cycles": E,
    })
    return base


def docker_profile() -> dict[str, Severity]:
    """Containerized apps: images should be pinned, non-root, and healthchecked."""
    return _domain({
        "require-dockerignore": W,
        "dockerfile-healthcheck": W,
        "deployable-artifact": W,
        "docker-pin-base-image": W,
        "docker-nonroot-user": W,
    })


def terraform_profile() -> dict[str, Severity]:
    """Terraform / IaC: encrypted, tagged, pinned, least-privilege."""
    return _domain({
        "terraform-remote-state": W,
        "terraform-version-pinning": W,
        "terraform-encryption": E,
        "terraform-tags": W,
        "terraform-least-privilege-iam": E,
    })


def aws_profile() -> dict[str, Severity]:
    """AWS workloads: encryption and least privilege on by default."""
    return _domain({
        "terraform-encryption": E,
        "terraform-least-privilege-iam": E,
        "terraform-tags": W,
        "no-hardcoded-secrets": E,
    })


def gcp_profile() -> dict[str, Severity]:
    """Google Cloud workloads."""
    return _domain({
        "terraform-encryption": E,
        "terraform-least-privilege-iam": E,
        "terraform-tags": W,
        "no-hardcoded-secrets": E,
    })


def postgres_profile() -> dict[str, Severity]:
    """Repositories talking to PostgreSQL."""
    return _domain({
        "no-direct-sql": W,
        "no-hardcoded-secrets": E,
    })


def github_profile() -> dict[str, Severity]:
    """Repositories using GitHub Actions."""
    return _domain({
        "pinned-github-actions": W,
        "ci-runs-tests": W,
        "ci-uses-cache": I,
    })


def llm_profile() -> dict[str, Severity]:
    """LLM / AI applications: evaluated, safe, observable, and reproducible."""
    return _domain({
        "llm-prompt-versioning": W,
        "llm-eval-datasets": W,
        "llm-safety-tests": W,
        "llm-retry-policies": W,
        "llm-structured-outputs": I,
        "llm-telemetry": W,
    })


def microservices_profile() -> dict[str, Severity]:
    """Microservices: health, metrics, tracing, timeouts, graceful shutdown."""
    base = backend_profile()
    base.update({
        "microservices-health-endpoint": E,
        "microservices-metrics-endpoint": W,
        "microservices-tracing": W,
        "microservices-graceful-shutdown": W,
        "microservices-timeouts": W,
    })
    return base


def data_profile() -> dict[str, Severity]:
    """Data engineering: tested, validated, contracted, and fresh."""
    return _domain({
        "data-dbt-tests": W,
        "data-schema-validation": W,
        "data-freshness-checks": I,
        "data-contracts": W,
    })


def security_profile() -> dict[str, Severity]:
    """A dedicated security posture: everything security escalated + SBOM."""
    base = recommended_standard()
    base.update({
        "no-hardcoded-secrets": E,
        "no-unsafe-files": E,
        "no-world-writable": E,
        "require-security-policy": W,
        "ci-has-security-scan": E,
        "dependency-audit": W,
        "declared-license": W,
        "pinned-github-actions": E,
        "security-sbom": W,
        "security-signed-commits": I,
    })
    return base


# FastAPI / React / ML gain their domain rules on top of the profiles above.
def _augment(builder, overrides):
    def _b():
        base = builder()
        base.update(overrides)
        return base
    return _b


_fastapi_domain_rules = {
    "fastapi-endpoint-auth": E,
    "fastapi-health-endpoint": W,
    "fastapi-openapi-docs": W,
    "fastapi-pydantic-models": W,
    "fastapi-cors-configured": W,
    "fastapi-error-handlers": W,
}
_react_domain_rules = {
    "react-error-boundaries": W,
    "react-lazy-loading": I,
    "react-accessibility": W,
    "react-testing": W,
    "react-component-organization": I,
}
_ml_domain_rules = {
    "ml-experiment-tracking": W,
    "ml-random-seeds": W,
    "ml-model-versioning": W,
    "ml-dataset-versioning": W,
    "ml-evaluation-metrics": W,
    "ml-model-card": I,
}

fastapi_profile = _augment(fastapi_profile, _fastapi_domain_rules)
react_profile = _augment(react_profile, _react_domain_rules)
ml_profile = _augment(ml_profile, _ml_domain_rules)


_BUILDERS = {
    # base standards
    "recommended": recommended_standard,
    "strict": strict_standard,
    "minimal": minimal_standard,
    # audience standards
    "startup": startup_profile,
    "enterprise": enterprise_profile,
    "oss": oss_profile,
    # language standards
    "python": python_profile,
    "go": go_profile,
    "java": java_profile,
    # framework standards
    "backend": backend_profile,
    "fastapi": fastapi_profile,
    "react": react_profile,
    "nextjs": nextjs_profile,
    "spring": spring_profile,
    # infrastructure standards
    "docker": docker_profile,
    "kubernetes": kubernetes_profile,
    "terraform": terraform_profile,
    "github": github_profile,
    # cloud standards
    "aws": aws_profile,
    "gcp": gcp_profile,
    "postgres": postgres_profile,
    # data & AI standards
    "ml": ml_profile,
    "llm": llm_profile,
    "data": data_profile,
    # cross-cutting standards
    "microservices": microservices_profile,
    "security": security_profile,
}

# Standards grouped for presentation. Base standards are mutually exclusive
# starting points; every other group is a domain/audience overlay you stack on
# top via ``extends``.
STANDARD_GROUPS: list[tuple[str, tuple[str, ...]]] = [
    ("Base", ("recommended", "strict", "minimal")),
    ("Audience", ("startup", "enterprise", "oss")),
    ("Language", ("python", "go", "java")),
    ("Framework", ("backend", "fastapi", "react", "nextjs", "spring")),
    ("Infrastructure", ("docker", "kubernetes", "terraform", "github")),
    ("Cloud", ("aws", "gcp", "postgres")),
    ("Data & AI", ("ml", "llm", "data")),
    ("Cross-cutting", ("microservices", "security")),
]

# Names that are domain/audience overlays (everything except the base three).
PROFILES: tuple[str, ...] = tuple(
    k for group, keys in STANDARD_GROUPS if group != "Base" for k in keys
)

PROFILE_DESCRIPTIONS = {
    "recommended": "Opinionated baseline for most repositories.",
    "strict": "Production-critical enforcement; everything escalated.",
    "minimal": "Smallest useful gate: documented and tested.",
    "startup": "Lenient but safe; keep only the guardrails that hurt.",
    "enterprise": "Governance-grade ownership, security, and auditability.",
    "oss": "Welcoming, licensed, contributor-friendly open source.",
    "python": "Python services and libraries.",
    "go": "Go modules and services.",
    "java": "JVM / Java projects.",
    "backend": "Backend services: layering, security, observability.",
    "fastapi": "FastAPI services: auth, health, OpenAPI, Pydantic, CORS.",
    "react": "React front-ends: a11y, error boundaries, tests, lazy loading.",
    "nextjs": "Next.js apps: React best practices + app conventions.",
    "spring": "Spring / Spring Boot services: layering and discipline.",
    "docker": "Containers: pinned base image, non-root, healthcheck.",
    "kubernetes": "K8s manifests: probes, limits, security context, non-root.",
    "terraform": "Terraform / IaC: encryption, tags, remote state, least privilege.",
    "github": "GitHub Actions: pinned actions, tests, caching.",
    "aws": "AWS workloads: encryption and least privilege by default.",
    "gcp": "Google Cloud workloads: encryption and least privilege.",
    "postgres": "PostgreSQL users: no raw SQL, no hardcoded credentials.",
    "ml": "ML repos: reproducibility, seeds, versioning, metrics, model cards.",
    "llm": "LLM/AI apps: prompt versioning, evals, safety, retries, telemetry.",
    "data": "Data engineering: dbt tests, schema validation, contracts, freshness.",
    "microservices": "Microservices: health, metrics, tracing, timeouts, shutdown.",
    "security": "Dedicated security posture: escalated security + SBOM.",
}


STANDARDS: dict[str, dict[str, Severity]] = {}
for _key, _builder in _BUILDERS.items():
    STANDARDS[_key] = _builder()
    STANDARDS[f"deval/{_key}"] = _builder()


# --- Universal vs Domain rules ---------------------------------------------
#
# A *universal* rule applies to every repository (README, LICENSE, tests, CI,
# dependency hygiene). A *domain* rule applies only when a technology is present
# (FastAPI auth, React accessibility, Kubernetes probes, ML reproducibility).
# Universal rules are exactly the rules enabled by ``deval/recommended``;
# everything a domain standard adds on top is a domain rule.
UNIVERSAL_RULES: frozenset = frozenset(
    rule for rule, sev in recommended_standard().items() if sev != OFF
)

_ALL_RULES: set = set()
for _std in STANDARDS.values():
    _ALL_RULES.update(_std.keys())

DOMAIN_RULES: frozenset = frozenset(_ALL_RULES - UNIVERSAL_RULES)


def is_universal(rule_id: str) -> bool:
    """True if the rule is part of the universal baseline (applies everywhere)."""
    return rule_id in UNIVERSAL_RULES


def list_standards() -> list[tuple[str, int]]:
    """Return (name, enabled-rule-count) for every base standard and profile."""
    out: list[tuple[str, int]] = []
    for key in _BUILDERS:
        enabled = sum(1 for s in STANDARDS[key].values() if s != OFF)
        out.append((f"deval/{key}", enabled))
    return out


def describe(key: str) -> str:
    """Human description for a standard key (with or without the deval/ prefix)."""
    k = key.split("/", 1)[-1] if key.startswith("deval/") else key
    return PROFILE_DESCRIPTIONS.get(k, "")
