"""Stable Deval rule codes (DV####).

Every rule has a short, permanent identifier - like a compiler diagnostic code
(``DV1001``) - in addition to its human-readable slug (``require-readme``). Codes
make documentation, dashboards, and suppressions concise and unambiguous, and
they never change once assigned even if a rule is renamed.

The leading block encodes the engineering dimension:

===== ==================
Block Dimension
===== ==================
1xxx  Repository
2xxx  Testing
3xxx  CI/CD
4xxx  Security
5xxx  Dependencies
6xxx  Documentation
7xxx  Architecture
8xxx  Maintainability
9xxx  Ownership
10xxx Structure
11xxx Observability
12xxx Operations
13xxx Compliance
===== ==================
"""

from __future__ import annotations

# rule_id -> DV code. Codes are permanent; append new rules, never renumber.
CODE_BY_RULE: dict[str, str] = {
    # Repository (1xxx)
    "require-readme": "DV1001",
    "require-license": "DV1002",
    "require-contributing": "DV1003",
    "require-gitignore": "DV1004",
    "require-code-of-conduct": "DV1005",
    "require-changelog": "DV1006",
    "require-editorconfig": "DV1007",
    "require-dockerignore": "DV1008",
    # Testing (2xxx)
    "reasonable-test-ratio": "DV2002",
    "coverage-config-present": "DV2003",
    "tests-present": "DV2004",
    # CI/CD (3xxx)
    "require-ci": "DV3001",
    "ci-runs-tests": "DV3002",
    "ci-has-security-scan": "DV3003",
    "ci-uses-cache": "DV3004",
    "ci-runs-fuzzing": "DV3005",
    "ci-has-sast": "DV3006",
    # Security (4xxx)
    "no-hardcoded-secrets": "DV4001",
    "no-unsafe-files": "DV4002",
    "no-world-writable": "DV4003",
    "require-authentication": "DV4004",
    "require-security-policy": "DV4011",
    "require-fuzz-targets": "DV4012",
    "release-attestation": "DV4013",
    # Dependencies (5xxx)
    "require-lockfile": "DV5001",
    "no-duplicate-dependencies": "DV5002",
    "no-abandoned-markers": "DV5003",
    "pinned-github-actions": "DV5004",
    "dependency-review": "DV5005",
    # Documentation (6xxx)
    "readme-has-sections": "DV6001",
    "no-broken-relative-links": "DV6002",
    "documented-public-api": "DV6003",
    # Architecture (7xxx)
    "respect-layering": "DV7001",
    "no-cross-module-cycles": "DV7002",
    "respect-clean-architecture": "DV7003",
    "no-direct-sql": "DV7004",
    "require-adr": "DV7005",
    # Maintainability (8xxx)
    "no-huge-files": "DV8001",
    "bounded-todo-debt": "DV8002",
    "no-committed-build-artifacts": "DV8003",
    "no-console-log": "DV8004",
    "require-pre-commit": "DV8005",
    # Ownership (9xxx)
    "require-codeowners": "DV9001",
    "require-maintainers": "DV9002",
    "require-governance": "DV9003",
    "require-support-policy": "DV9004",
    # Structure (10xxx)
    "conventional-source-layout": "DV10001",
    "tests-directory-present": "DV10002",
    # Observability (11xxx)
    "observable-logging": "DV11001",
    "require-opentelemetry": "DV11002",
    "error-tracking": "DV11003",
    # Operations (12xxx)
    "deployable-artifact": "DV12001",
    "dockerfile-healthcheck": "DV12002",
    # Compliance (13xxx)
    "declared-license": "DV13001",
    "dependency-audit": "DV13002",
    # --- Domain rules -----------------------------------------------------
    # Domain rules are still classified by engineering dimension, so they
    # continue their dimension's numbering block in a reserved domain range.
    # Testing (2xxx, domain range 21xx)
    "react-testing": "DV2101",
    "ml-evaluation-metrics": "DV2102",
    "llm-eval-datasets": "DV2103",
    "data-dbt-tests": "DV2104",
    # Security (4xxx, domain range 41xx)
    "fastapi-endpoint-auth": "DV4101",
    "fastapi-cors-configured": "DV4102",
    "k8s-security-context": "DV4103",
    "k8s-non-root": "DV4104",
    "terraform-encryption": "DV4105",
    "terraform-least-privilege-iam": "DV4106",
    "llm-safety-tests": "DV4107",
    "docker-nonroot-user": "DV4108",
    # Dependencies (5xxx, domain range 51xx)
    "k8s-image-pinning": "DV5101",
    "terraform-version-pinning": "DV5102",
    "docker-pin-base-image": "DV5103",
    # Documentation (6xxx, domain range 61xx)
    "fastapi-openapi-docs": "DV6101",
    "react-accessibility": "DV6102",
    "ml-model-card": "DV6103",
    # Architecture (7xxx, domain range 71xx)
    "fastapi-pydantic-models": "DV7101",
    "react-component-organization": "DV7102",
    "llm-structured-outputs": "DV7103",
    # Maintainability (8xxx, domain range 81xx)
    "react-error-boundaries": "DV8101",
    "react-lazy-loading": "DV8102",
    "ml-experiment-tracking": "DV8103",
    "ml-random-seeds": "DV8104",
    "ml-model-versioning": "DV8105",
    "llm-prompt-versioning": "DV8106",
    "microservices-timeouts": "DV8107",
    # Observability (11xxx, domain range 111xx)
    "llm-telemetry": "DV11101",
    "microservices-metrics-endpoint": "DV11102",
    "microservices-tracing": "DV11103",
    # Operations (12xxx, domain range 121xx)
    "fastapi-health-endpoint": "DV12101",
    "fastapi-error-handlers": "DV12102",
    "k8s-resource-limits": "DV12103",
    "k8s-liveness-probe": "DV12104",
    "k8s-readiness-probe": "DV12105",
    "terraform-remote-state": "DV12106",
    "llm-retry-policies": "DV12107",
    "microservices-health-endpoint": "DV12108",
    "microservices-graceful-shutdown": "DV12109",
    "data-freshness-checks": "DV12110",
    # Compliance (13xxx, domain range 131xx)
    "terraform-tags": "DV13101",
    "ml-dataset-versioning": "DV13102",
    "data-schema-validation": "DV13103",
    "data-contracts": "DV13104",
    "security-sbom": "DV13105",
    "security-signed-commits": "DV13106",
}

RULE_BY_CODE: dict[str, str] = {code: rule for rule, code in CODE_BY_RULE.items()}


def code_for(rule_id: str) -> str | None:
    """Return the DV code for a rule id, or None for unregistered/plugin rules."""
    return CODE_BY_RULE.get(rule_id)


def rule_for_code(code: str) -> str | None:
    """Resolve a DV code (case-insensitive) back to its rule id."""
    return RULE_BY_CODE.get(code.strip().upper())


def labeled(rule_id: str) -> str:
    """'DV1001 require-readme' when a code exists, else just the rule id."""
    code = code_for(rule_id)
    return f"{code} {rule_id}" if code else rule_id
