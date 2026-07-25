"""Domain checks: Deval understands *what you're building*.

Universal rules (README, LICENSE, tests, CI, dependency hygiene) apply to every
repository. **Domain rules** only apply when the relevant technology is present:
FastAPI authentication, React accessibility, Kubernetes probes, Terraform
encryption, ML reproducibility, LLM evaluation datasets, and so on.

Every domain check here is *doubly inert* for repositories that don't use the
technology:

1. Its rule is OFF in ``deval/recommended`` and is only enabled when the
   matching Domain Standard is applied (explicitly or via auto-detection).
2. Its ``applies`` gate returns False unless the technology is actually
   detected in the repository, so it never fires — pass or fail — on an
   unrelated repo. This also keeps the shared check registry clean when many
   different repositories are scanned in one process.

Checks are declared as data (:class:`DomainCheck`) and registered generically,
which keeps each rule a couple of lines and makes packs easy to extend.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Optional

from .. import detect
from ..fsindex import RepoIndex
from ..model import Severity
from ..registry import CheckContext, check

OFF = Severity.OFF

# (passed, message, optional path)
EvalResult = tuple[bool, str, Optional[str]]


@dataclass(frozen=True)
class DomainCheck:
    rule_id: str
    category: str            # engineering dimension
    tech: str                # detection key gating this check
    evaluate: Callable[[RepoIndex], EvalResult]
    remediation: str = ""

    def applies(self, index: RepoIndex) -> bool:
        return detect.matches(index, self.tech)


# --- small shared helpers ---------------------------------------------------

def _py_text(index: RepoIndex) -> str:
    return "\n".join(index.read_text(rf) for rf in index.by_suffix(".py"))


def _text_of(index: RepoIndex, *suffixes: str) -> str:
    return "\n".join(index.read_text(rf) for rf in index.by_suffix(*suffixes))


def _yaml_text(index: RepoIndex) -> str:
    return _text_of(index, ".yaml", ".yml")


def _tf_text(index: RepoIndex) -> str:
    return _text_of(index, ".tf")


def _has(text: str, *patterns: str) -> bool:
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def _ok(msg: str, path: str | None = None) -> EvalResult:
    return (True, msg, path)


def _no(msg: str, path: str | None = None) -> EvalResult:
    return (False, msg, path)


def _dockerfiles(index: RepoIndex):
    return [rf for rf in index.files if rf.name == "Dockerfile" or rf.name.startswith("Dockerfile.")]


# --- FastAPI ----------------------------------------------------------------

def _fastapi_auth(index: RepoIndex) -> EvalResult:
    text = _py_text(index)
    if _has(text, r"Depends\(", r"Security\(", r"HTTPBearer", r"OAuth2", r"api[_-]?key"):
        return _ok("Endpoints use authentication dependencies (Depends/Security/OAuth2).")
    return _no("No authentication dependency found on FastAPI endpoints.")


def _fastapi_health(index: RepoIndex) -> EvalResult:
    text = _py_text(index)
    if _has(text, r"[\"']/(health|healthz|livez|readyz|ping)[\"']"):
        return _ok("A health endpoint is exposed.")
    return _no("No health endpoint (e.g. GET /health) found.")


def _fastapi_openapi(index: RepoIndex) -> EvalResult:
    text = _py_text(index)
    if _has(text, r"docs_url\s*=\s*None") and not _has(text, r"openapi_url"):
        return _no("OpenAPI docs are disabled (docs_url=None) with no alternative.")
    return _ok("Interactive OpenAPI docs are available.")


def _fastapi_pydantic(index: RepoIndex) -> EvalResult:
    text = _py_text(index)
    if _has(text, r"class\s+\w+\((?:[\w.]+,\s*)*BaseModel", r"pydantic"):
        return _ok("Request/response bodies use Pydantic models.")
    return _no("No Pydantic models found; endpoints may accept untyped payloads.")


def _fastapi_cors(index: RepoIndex) -> EvalResult:
    text = _py_text(index)
    if _has(text, r"CORSMiddleware"):
        return _ok("CORS is configured via CORSMiddleware.")
    return _no("CORS is not configured (no CORSMiddleware).")


def _fastapi_error_handlers(index: RepoIndex) -> EvalResult:
    text = _py_text(index)
    if _has(text, r"exception_handler", r"add_exception_handler", r"HTTPException"):
        return _ok("Custom error/exception handlers are present.")
    return _no("No exception handlers found.")


# --- React ------------------------------------------------------------------

def _react_text(index: RepoIndex) -> str:
    return _text_of(index, ".js", ".jsx", ".ts", ".tsx")


def _react_error_boundaries(index: RepoIndex) -> EvalResult:
    text = _react_text(index)
    if _has(text, r"componentDidCatch", r"getDerivedStateFromError", r"ErrorBoundary", r"react-error-boundary"):
        return _ok("Error boundaries are implemented.")
    return _no("No React error boundary found.")


def _react_lazy(index: RepoIndex) -> EvalResult:
    text = _react_text(index)
    if _has(text, r"React\.lazy", r"\blazy\(", r"next/dynamic", r"import\("):
        return _ok("Code splitting / lazy loading is used.")
    return _no("No lazy loading or code splitting detected.")


def _react_a11y(index: RepoIndex) -> EvalResult:
    text = _react_text(index)
    manifest = detect.manifest_text(index)
    if _has(manifest, r"jsx-a11y") or _has(text, r"aria-[a-z]+=", r"\balt=", r"role="):
        return _ok("Accessibility attributes / eslint-plugin-jsx-a11y in use.")
    return _no("No accessibility attributes or a11y linting found.")


def _react_testing(index: RepoIndex) -> EvalResult:
    tests = index.glob("**/*.test.jsx") + index.glob("**/*.test.tsx") + \
        index.glob("**/*.spec.tsx") + index.glob("**/*.spec.jsx")
    if tests or index.find_any_dir("__tests__"):
        return _ok("Component tests are present.")
    return _no("No component tests (*.test.tsx / __tests__) found.")


def _react_components(index: RepoIndex) -> EvalResult:
    if index.find_any_dir("components"):
        return _ok("Components are organized under a components/ directory.")
    return _no("No components/ directory; component organization is unclear.")


# --- Kubernetes -------------------------------------------------------------

def _k8s_resource_limits(index: RepoIndex) -> EvalResult:
    text = _yaml_text(index)
    if _has(text, r"limits:") and _has(text, r"requests:"):
        return _ok("Containers declare resource requests and limits.")
    return _no("Containers are missing resource requests/limits.")


def _k8s_liveness(index: RepoIndex) -> EvalResult:
    if _has(_yaml_text(index), r"livenessProbe:"):
        return _ok("Liveness probes are configured.")
    return _no("No livenessProbe configured.")


def _k8s_readiness(index: RepoIndex) -> EvalResult:
    if _has(_yaml_text(index), r"readinessProbe:"):
        return _ok("Readiness probes are configured.")
    return _no("No readinessProbe configured.")


def _k8s_security_context(index: RepoIndex) -> EvalResult:
    if _has(_yaml_text(index), r"securityContext:"):
        return _ok("A securityContext is defined.")
    return _no("No securityContext defined on pods/containers.")


def _k8s_non_root(index: RepoIndex) -> EvalResult:
    if _has(_yaml_text(index), r"runAsNonRoot:\s*true"):
        return _ok("Containers run as non-root (runAsNonRoot: true).")
    return _no("Containers may run as root (no runAsNonRoot: true).")


def _k8s_image_pinning(index: RepoIndex) -> EvalResult:
    text = _yaml_text(index)
    if _has(text, r"image:\s*\S+:latest", r"image:\s*[\"']?\S+[\"']?\s*$"):
        # crude: flags :latest or untagged
        if _has(text, r"image:\s*\S+:latest"):
            return _no("Container images use the :latest tag; pin to a version or digest.")
    if _has(text, r"image:\s*\S+@sha256:", r"image:\s*\S+:\d"):
        return _ok("Container images are pinned to a tag or digest.")
    return _no("Container images are not pinned to an explicit version.")


# --- Terraform --------------------------------------------------------------

def _tf_remote_state(index: RepoIndex) -> EvalResult:
    if _has(_tf_text(index), r"backend\s+[\"']\w+[\"']\s*{"):
        return _ok("Remote state backend is configured.")
    return _no("No remote state backend configured (state may be local).")


def _tf_version_pinning(index: RepoIndex) -> EvalResult:
    text = _tf_text(index)
    if _has(text, r"required_version", r"required_providers", r"version\s*="):
        return _ok("Terraform and provider versions are pinned.")
    return _no("No version pinning for Terraform or providers.")


def _tf_encryption(index: RepoIndex) -> EvalResult:
    text = _tf_text(index)
    if _has(text, r"encrypt(ed|ion)?\s*=\s*true", r"kms_key", r"server_side_encryption"):
        return _ok("Encryption is enabled on stateful resources.")
    return _no("No encryption settings found on resources.")


def _tf_tags(index: RepoIndex) -> EvalResult:
    if _has(_tf_text(index), r"tags\s*="):
        return _ok("Resources are tagged.")
    return _no("Resources are missing tags.")


def _tf_least_privilege(index: RepoIndex) -> EvalResult:
    text = _tf_text(index)
    if _has(text, r'"Action"\s*:\s*"\*"', r'actions\s*=\s*\[\s*"\*"', r'resources\s*=\s*\[\s*"\*"'):
        return _no("IAM policy grants wildcard (*) permissions.")
    return _ok("No wildcard IAM permissions detected.")


# --- Machine Learning -------------------------------------------------------

def _ml_experiment_tracking(index: RepoIndex) -> EvalResult:
    if detect.imports_any(index, ["mlflow", "wandb", "tensorboard", "neptune", "clearml", "comet_ml"]):
        return _ok("Experiment tracking is wired in (MLflow/W&B/TensorBoard/...).")
    return _no("No experiment tracking library detected.")


def _ml_random_seeds(index: RepoIndex) -> EvalResult:
    text = _py_text(index)
    if _has(text, r"manual_seed", r"seed_everything", r"set_seed", r"random\.seed", r"np\.random\.seed", r"tf\.random\.set_seed"):
        return _ok("Random seeds are set for reproducibility.")
    return _no("No random seed is set; runs may not be reproducible.")


def _ml_model_versioning(index: RepoIndex) -> EvalResult:
    if index.has(".dvc", "dvc.yaml") or index.find_any_dir(".dvc") or detect.imports_any(index, ["mlflow"]):
        return _ok("Models are versioned (DVC / model registry).")
    return _no("No model versioning (DVC or model registry) detected.")


def _ml_dataset_versioning(index: RepoIndex) -> EvalResult:
    if index.has("dvc.yaml", ".dvcignore") or index.glob("**/*.dvc") or detect.imports_any(index, ["dvc"]):
        return _ok("Datasets are versioned with DVC.")
    return _no("No dataset versioning detected (e.g. DVC).")


def _ml_eval_metrics(index: RepoIndex) -> EvalResult:
    text = _py_text(index)
    if _has(text, r"sklearn\.metrics", r"accuracy_score", r"f1_score", r"roc_auc", r"precision_score", r"recall_score"):
        return _ok("Evaluation metrics are computed.")
    return _no("No evaluation metrics found.")


def _ml_model_card(index: RepoIndex) -> EvalResult:
    if index.glob("**/MODEL_CARD*") or index.glob("**/model_card*") or index.glob("**/modelcard*"):
        return _ok("A model card documents the model.")
    return _no("No model card (MODEL_CARD.md) found.")


# --- LLM / AI ---------------------------------------------------------------

def _llm_prompt_versioning(index: RepoIndex) -> EvalResult:
    if index.find_any_dir("prompts") or index.glob("**/prompts/*") or index.glob("**/*.prompt"):
        return _ok("Prompts are stored as versioned files.")
    return _no("No versioned prompt files/dir found; prompts may be inline only.")


def _llm_eval_datasets(index: RepoIndex) -> EvalResult:
    if index.find_any_dir("evals") or index.find_any_dir("eval") or index.glob("**/eval*/*.jsonl"):
        return _ok("Evaluation datasets are present.")
    return _no("No evaluation datasets (evals/) found.")


def _llm_safety_tests(index: RepoIndex) -> EvalResult:
    text = _py_text(index)
    if _has(text, r"guardrail", r"moderation", r"jailbreak", r"safety", r"prompt_?injection"):
        return _ok("Safety / guardrail tests are present.")
    return _no("No safety or guardrail tests detected.")


def _llm_retry(index: RepoIndex) -> EvalResult:
    text = _py_text(index)
    if detect.imports_any(index, ["tenacity", "backoff"]) or _has(text, r"max_retries", r"retry\(", r"with_retry"):
        return _ok("Retry/backoff policies wrap model calls.")
    return _no("No retry policy around model calls detected.")


def _llm_structured_outputs(index: RepoIndex) -> EvalResult:
    text = _py_text(index)
    if _has(text, r"response_model", r"response_format", r"with_structured_output", r"json_schema", r"BaseModel"):
        return _ok("Structured outputs (schemas) are enforced.")
    return _no("No structured output schema detected.")


def _llm_telemetry(index: RepoIndex) -> EvalResult:
    if detect.imports_any(index, ["langsmith", "langfuse", "openllmetry", "opentelemetry", "helicone", "phoenix"]):
        return _ok("LLM telemetry / tracing is configured.")
    return _no("No LLM telemetry/tracing detected.")


# --- Microservices ----------------------------------------------------------

def _ms_health(index: RepoIndex) -> EvalResult:
    if _has(_py_text(index), r"[\"']/(health|healthz|livez|readyz)[\"']"):
        return _ok("Service exposes a health endpoint.")
    return _no("No health endpoint found.")


def _ms_metrics(index: RepoIndex) -> EvalResult:
    text = _py_text(index)
    if _has(text, r"[\"']/metrics[\"']") or detect.imports_any(index, ["prometheus_client", "prometheus_fastapi_instrumentator"]):
        return _ok("Service exposes a metrics endpoint.")
    return _no("No /metrics endpoint or Prometheus client found.")


def _ms_tracing(index: RepoIndex) -> EvalResult:
    if detect.imports_any(index, ["opentelemetry", "jaeger", "zipkin", "ddtrace"]):
        return _ok("Distributed tracing is configured.")
    return _no("No distributed tracing detected.")


def _ms_graceful_shutdown(index: RepoIndex) -> EvalResult:
    text = _py_text(index)
    if _has(text, r"SIGTERM", r"SIGINT", r"lifespan", r"on_event\([\"']shutdown", r"atexit"):
        return _ok("Graceful shutdown handling is present.")
    return _no("No graceful shutdown handling (SIGTERM/lifespan) found.")


def _ms_timeouts(index: RepoIndex) -> EvalResult:
    text = _py_text(index)
    if _has(text, r"timeout\s*=", r"Timeout\("):
        return _ok("Outbound calls configure timeouts.")
    return _no("No timeouts configured on outbound calls.")


# --- Data Engineering -------------------------------------------------------

def _data_dbt_tests(index: RepoIndex) -> EvalResult:
    for rf in index.by_suffix(".yml", ".yaml"):
        if _has(index.read_text(rf), r"tests:", r"data_tests:"):
            return _ok("dbt tests are declared.")
    if index.find_any_dir("tests") and index.has("dbt_project.yml"):
        return _ok("dbt tests directory present.")
    return _no("No dbt tests declared.")


def _data_schema_validation(index: RepoIndex) -> EvalResult:
    if detect.imports_any(index, ["pandera", "great_expectations", "pydantic", "cerberus"]) or \
            _has(_yaml_text(index), r"contract:", r"constraints:"):
        return _ok("Schema validation is in place.")
    return _no("No schema validation detected.")


def _data_freshness(index: RepoIndex) -> EvalResult:
    if _has(_yaml_text(index), r"freshness:", r"loaded_at_field"):
        return _ok("Source freshness checks are configured.")
    return _no("No data freshness checks configured.")


def _data_contracts(index: RepoIndex) -> EvalResult:
    if _has(_yaml_text(index), r"contract:\s*\n?\s*enforced:\s*true", r"data_contract", r"contract:"):
        return _ok("Data contracts are declared.")
    return _no("No data contracts declared.")


# --- Docker -----------------------------------------------------------------

def _docker_pin_base(index: RepoIndex) -> EvalResult:
    for rf in _dockerfiles(index):
        text = index.read_text(rf)
        if _has(text, r"(?m)^FROM\s+\S+:latest", r"(?m)^FROM\s+[^\s:@]+\s*(?:AS\s+\w+)?\s*$"):
            return _no("Base image is unpinned or uses :latest.", rf.relpath)
        return _ok("Base image is pinned to a version or digest.", rf.relpath)
    return _no("No Dockerfile found.")


def _docker_nonroot(index: RepoIndex) -> EvalResult:
    for rf in _dockerfiles(index):
        if _has(index.read_text(rf), r"(?m)^USER\s+(?!root\b)\S+"):
            return _ok("Container drops to a non-root USER.", rf.relpath)
        return _no("No non-root USER instruction; container runs as root.", rf.relpath)
    return _no("No Dockerfile found.")


# --- Security pack ----------------------------------------------------------

def _sec_sbom(index: RepoIndex) -> EvalResult:
    if index.glob("**/*sbom*") or index.glob("**/*cyclonedx*") or index.glob("**/*.spdx*") or index.glob("**/bom.json"):
        return _ok("An SBOM is published.")
    return _no("No SBOM (CycloneDX/SPDX) found.")


def _sec_signed_commits(index: RepoIndex) -> EvalResult:
    # Best-effort offline signal: a committed policy requiring signed commits.
    for rf in index.glob(".github/**"):
        if _has(index.read_text(rf), r"verify.*signature", r"gpg", r"gitsign", r"sigstore"):
            return _ok("Commit signing is enforced in CI.", rf.relpath)
    return _no("No commit-signing enforcement detected.")


# --- registry ---------------------------------------------------------------

DOMAIN_CHECKS: list[DomainCheck] = [
    # FastAPI
    DomainCheck("fastapi-endpoint-auth", "security", "fastapi", _fastapi_auth,
                "Protect routes with an auth dependency (Depends/Security/OAuth2)."),
    DomainCheck("fastapi-health-endpoint", "operations", "fastapi", _fastapi_health,
                "Expose GET /health for orchestrators and load balancers."),
    DomainCheck("fastapi-openapi-docs", "documentation", "fastapi", _fastapi_openapi,
                "Keep interactive OpenAPI docs enabled (or provide an alternative)."),
    DomainCheck("fastapi-pydantic-models", "architecture", "fastapi", _fastapi_pydantic,
                "Type request/response bodies with Pydantic models."),
    DomainCheck("fastapi-cors-configured", "security", "fastapi", _fastapi_cors,
                "Configure CORSMiddleware with an explicit allow-list."),
    DomainCheck("fastapi-error-handlers", "operations", "fastapi", _fastapi_error_handlers,
                "Register exception handlers for consistent error responses."),
    # React
    DomainCheck("react-error-boundaries", "maintainability", "react", _react_error_boundaries,
                "Wrap trees in an error boundary to contain render failures."),
    DomainCheck("react-lazy-loading", "maintainability", "react", _react_lazy,
                "Use React.lazy/dynamic imports to code-split heavy routes."),
    DomainCheck("react-accessibility", "documentation", "react", _react_a11y,
                "Add ARIA/alt attributes and enable eslint-plugin-jsx-a11y."),
    DomainCheck("react-testing", "testing", "react", _react_testing,
                "Add component tests (*.test.tsx or __tests__)."),
    DomainCheck("react-component-organization", "architecture", "react", _react_components,
                "Group UI under a components/ directory."),
    # Kubernetes
    DomainCheck("k8s-resource-limits", "operations", "kubernetes", _k8s_resource_limits,
                "Set resources.requests and resources.limits on every container."),
    DomainCheck("k8s-liveness-probe", "operations", "kubernetes", _k8s_liveness,
                "Add a livenessProbe so unhealthy pods restart."),
    DomainCheck("k8s-readiness-probe", "operations", "kubernetes", _k8s_readiness,
                "Add a readinessProbe to gate traffic until ready."),
    DomainCheck("k8s-security-context", "security", "kubernetes", _k8s_security_context,
                "Define a securityContext (drop capabilities, read-only rootfs)."),
    DomainCheck("k8s-non-root", "security", "kubernetes", _k8s_non_root,
                "Set runAsNonRoot: true so containers never run as root."),
    DomainCheck("k8s-image-pinning", "dependencies", "kubernetes", _k8s_image_pinning,
                "Pin images to a version or digest instead of :latest."),
    # Terraform
    DomainCheck("terraform-remote-state", "operations", "terraform", _tf_remote_state,
                "Configure a remote state backend with locking."),
    DomainCheck("terraform-version-pinning", "dependencies", "terraform", _tf_version_pinning,
                "Pin required_version and provider versions."),
    DomainCheck("terraform-encryption", "security", "terraform", _tf_encryption,
                "Enable encryption (KMS/SSE) on stateful resources."),
    DomainCheck("terraform-tags", "compliance", "terraform", _tf_tags,
                "Tag resources for cost, ownership, and compliance."),
    DomainCheck("terraform-least-privilege-iam", "security", "terraform", _tf_least_privilege,
                "Avoid wildcard (*) IAM actions/resources; scope least privilege."),
    # Machine Learning
    DomainCheck("ml-experiment-tracking", "maintainability", "ml", _ml_experiment_tracking,
                "Track runs with MLflow / Weights & Biases / TensorBoard."),
    DomainCheck("ml-random-seeds", "maintainability", "ml", _ml_random_seeds,
                "Set random seeds across libraries for reproducibility."),
    DomainCheck("ml-model-versioning", "maintainability", "ml", _ml_model_versioning,
                "Version models with a registry or DVC."),
    DomainCheck("ml-dataset-versioning", "compliance", "ml", _ml_dataset_versioning,
                "Version datasets (e.g. DVC) so runs are reproducible."),
    DomainCheck("ml-evaluation-metrics", "testing", "ml", _ml_eval_metrics,
                "Compute and record evaluation metrics."),
    DomainCheck("ml-model-card", "documentation", "ml", _ml_model_card,
                "Document the model with a model card."),
    # LLM / AI
    DomainCheck("llm-prompt-versioning", "maintainability", "llm", _llm_prompt_versioning,
                "Store prompts as versioned files, not inline strings."),
    DomainCheck("llm-eval-datasets", "testing", "llm", _llm_eval_datasets,
                "Keep evaluation datasets to measure quality over time."),
    DomainCheck("llm-safety-tests", "security", "llm", _llm_safety_tests,
                "Add safety/guardrail tests (moderation, prompt-injection)."),
    DomainCheck("llm-retry-policies", "operations", "llm", _llm_retry,
                "Wrap model calls with retry/backoff (tenacity/backoff)."),
    DomainCheck("llm-structured-outputs", "architecture", "llm", _llm_structured_outputs,
                "Enforce structured outputs via schemas/response_model."),
    DomainCheck("llm-telemetry", "observability", "llm", _llm_telemetry,
                "Instrument LLM calls (LangSmith/Langfuse/OpenTelemetry)."),
    # Microservices
    DomainCheck("microservices-health-endpoint", "operations", "microservices", _ms_health,
                "Expose a health endpoint per service."),
    DomainCheck("microservices-metrics-endpoint", "observability", "microservices", _ms_metrics,
                "Expose /metrics for Prometheus scraping."),
    DomainCheck("microservices-tracing", "observability", "microservices", _ms_tracing,
                "Propagate distributed tracing across services."),
    DomainCheck("microservices-graceful-shutdown", "operations", "microservices", _ms_graceful_shutdown,
                "Handle SIGTERM to drain and shut down gracefully."),
    DomainCheck("microservices-timeouts", "maintainability", "microservices", _ms_timeouts,
                "Set timeouts on every outbound call."),
    # Data Engineering
    DomainCheck("data-dbt-tests", "testing", "data", _data_dbt_tests,
                "Declare dbt tests (not_null, unique, relationships)."),
    DomainCheck("data-schema-validation", "compliance", "data", _data_schema_validation,
                "Validate schemas with pandera / Great Expectations / contracts."),
    DomainCheck("data-freshness-checks", "operations", "data", _data_freshness,
                "Configure source freshness checks."),
    DomainCheck("data-contracts", "compliance", "data", _data_contracts,
                "Define enforced data contracts for critical models."),
    # Docker
    DomainCheck("docker-pin-base-image", "dependencies", "docker", _docker_pin_base,
                "Pin the FROM base image to a version or digest."),
    DomainCheck("docker-nonroot-user", "security", "docker", _docker_nonroot,
                "Add a non-root USER instruction."),
    # Security pack
    DomainCheck("security-sbom", "compliance", "security", _sec_sbom,
                "Publish an SBOM (CycloneDX or SPDX)."),
    DomainCheck("security-signed-commits", "compliance", "security", _sec_signed_commits,
                "Enforce signed commits (GPG / Sigstore / gitsign)."),
]


def _register(dc: DomainCheck) -> None:
    @check(dc.rule_id, dc.category)
    def _fn(ctx: CheckContext, _dc: DomainCheck = dc):
        # Domain rules default to OFF. They only run when an applied standard
        # (explicit or auto-detected) enables them *and* the technology is
        # actually present. This keeps them inert everywhere else — including
        # when autodetect is disabled — and keeps the shared registry clean.
        if not ctx.enabled(_dc.rule_id, OFF):
            return
        if not _dc.applies(ctx.index):
            return  # inert: technology not present
        passed, message, path = _dc.evaluate(ctx.index)
        kw = {"path": path} if path else {}
        if passed:
            yield ctx.ok(_dc.rule_id, _dc.category, message, **kw)
        else:
            yield ctx.fail(_dc.rule_id, _dc.category, message, remediation=_dc.remediation, **kw)


for _dc in DOMAIN_CHECKS:
    _register(_dc)


def domain_checks_for(tech: str) -> list[DomainCheck]:
    return [dc for dc in DOMAIN_CHECKS if dc.tech == tech]
