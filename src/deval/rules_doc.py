"""Educational documentation for every rule.

Every finding is teachable. Each rule carries the same five sections a good
code review would give you - **Problem, Why, Example, Fix, References** - so
``deval explain <rule>`` (and the ``--explain`` flag) reads like a compiler
diagnostic that also mentors. Rules are addressable by their slug or their
stable DV code (e.g. ``deval explain DV1001``).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .codes import code_for
from .dimensions import label_for


@dataclass
class RuleDoc:
    rule_id: str
    category: str
    description: str
    why: str
    fix: str
    examples: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)

    def render(self) -> str:
        """Render this rule's documentation as plain text for ``deval explain``.

        The heading leads with the stable DV code when one exists, so the output
        can be pasted into a review comment and still identify the rule after a
        human-readable rule id is renamed.
        """
        code = code_for(self.rule_id)
        heading = f"{code}  {self.rule_id}" if code else self.rule_id
        lines = [
            heading,
            f"{label_for(self.category)} dimension",
            "",
            "Problem",
            f"  {self.description}",
            "",
            "Why",
            f"  {self.why}",
        ]
        lines += ["", "Example"]
        lines += [f"  - {e}" for e in (self.examples or [f"Evidence for {self.rule_id}"])]
        lines += ["", "Fix", f"  {self.fix}"]
        lines += ["", "References"]
        lines += [f"  - {r}" for r in (self.references or ["Deval Engineering Standards catalog (`deval rules`)."])]
        return "\n".join(lines)


def _d(rule_id, category, description, why, fix, examples=None, references=None) -> RuleDoc:
    return RuleDoc(rule_id, category, description, why, fix, examples or [], references or [])


_DOCS: list[RuleDoc] = [
    _d("require-readme", "repository",
       "The repository must contain a README.",
       "A README is the first point of entry; without it newcomers cannot tell what the project does or how to run it.",
       "Create README.md with a short description, install steps, and usage.",
       ["README.md", "README.rst"],
       ["https://www.makeareadme.com/"]),
    _d("require-license", "repository",
       "The repository must contain a LICENSE.",
       "Without a license, others have no legal right to use, modify, or distribute the code.",
       "Add a LICENSE file. MIT and Apache-2.0 are common permissive choices.",
       ["LICENSE", "COPYING"],
       ["https://choosealicense.com/"]),
    _d("require-contributing", "repository",
       "A contributing guide should be present.",
       "CONTRIBUTING tells people how to set up the project and submit high-quality changes, lowering review cost.",
       "Add CONTRIBUTING.md describing setup, tests, and the PR process."),
    _d("require-gitignore", "repository",
       "A .gitignore should be present.",
       "Without it, caches, build output, and secrets are easily committed by accident.",
       "Add a .gitignore covering your language and tooling."),
    _d("require-code-of-conduct", "repository",
       "A code of conduct should be present.",
       "It sets clear expectations for community behavior and makes reports actionable.",
       "Add CODE_OF_CONDUCT.md (the Contributor Covenant is a good default).",
       references=["https://www.contributor-covenant.org/"]),
    _d("require-changelog", "repository",
       "A changelog should be present.",
       "A changelog lets users understand what changed between releases without reading git history.",
       "Add CHANGELOG.md following Keep a Changelog.",
       references=["https://keepachangelog.com/"]),
    _d("readme-has-sections", "documentation",
       "The README should cover installation, usage, and licensing.",
       "A README that omits how to install or use the project leaves readers stuck.",
       "Add ## Installation, ## Usage, and license information to the README."),
    _d("no-broken-relative-links", "documentation",
       "Relative links in Markdown should resolve to files that exist.",
       "Broken links frustrate readers and signal that docs have drifted from the code.",
       "Fix or remove the link, or add the missing file."),
    _d("documented-public-api", "documentation",
       "Public functions and classes should have docstrings.",
       "Undocumented public APIs are hard to adopt and easy to misuse.",
       "Add a docstring to each public function/class explaining inputs and outputs."),
    _d("respect-layering", "architecture",
       "Controllers must not import Repositories directly.",
       "Skipping the Service layer couples transport/HTTP concerns to storage and defeats testability.",
       "Call a Service from the Controller and let the Service use the Repository.",
       ["Controller -> Service -> Repository"]),
    _d("no-cross-module-cycles", "architecture",
       "Modules should not import each other cyclically.",
       "Import cycles make code impossible to reason about and test in isolation.",
       "Extract shared code into a third module or invert one dependency."),
    _d("conventional-source-layout", "structure",
       "Source should live under a conventional directory.",
       "A predictable layout (src/, lib/, app/, pkg/) makes packaging and tooling just work.",
       "Move source into src/ (or your ecosystem's convention)."),
    _d("tests-directory-present", "structure",
       "A dedicated tests directory should exist.",
       "Co-locating tests in tests/ keeps them discoverable by test runners and humans.",
       "Create a tests/ directory and move tests there."),
    _d("require-lockfile", "dependencies",
       "A dependency lockfile should be committed.",
       "Lockfiles pin exact versions so installs are reproducible and supply-chain safe.",
       "Commit poetry.lock / uv.lock / package-lock.json / requirements.txt."),
    _d("no-duplicate-dependencies", "dependencies",
       "A dependency should be declared only once.",
       "Duplicate declarations cause ambiguous version resolution and confusing bugs.",
       "Remove the duplicate entry from your manifest."),
    _d("no-abandoned-markers", "dependencies",
       "Avoid dependencies marked deprecated/abandoned.",
       "Abandoned packages accrue unpatched security and compatibility risk.",
       "Replace the dependency with a maintained alternative."),
    _d("pinned-github-actions", "dependencies",
       "GitHub Actions should be pinned to a tag or SHA.",
       "Floating refs let a compromised action run arbitrary code in your pipeline.",
       "Pin uses: actions/checkout@v4 (or a full commit SHA).",
       references=["https://docs.github.com/actions/security-guides"]),
    _d("tests-present", "testing",
       "The repository must contain automated tests.",
       "Tests are the single biggest predictor of safe change and maintainability.",
       "Add tests under tests/ (files named test_*.py, *.test.ts, *_test.go, etc.)."),
    _d("reasonable-test-ratio", "testing",
       "Maintain a healthy ratio of test files to source files.",
       "Very few tests relative to code usually means large untested surface area.",
       "Add tests for core modules until the ratio is reasonable."),
    _d("coverage-config-present", "testing",
       "Coverage measurement should be configured.",
       "You cannot enforce a coverage bar you do not measure.",
       "Add coverage config (e.g. [tool.coverage] or a jest coverage threshold)."),
    _d("require-ci", "ci",
       "A CI pipeline should be configured.",
       "CI catches problems automatically on every change instead of in production.",
       "Add a workflow under .github/workflows/ (or your CI provider's config)."),
    _d("ci-runs-tests", "ci",
       "CI should execute the test suite.",
       "A pipeline that never runs tests provides false confidence.",
       "Add a test step (pytest, npm test, go test, ...) to CI."),
    _d("ci-has-security-scan", "ci",
       "CI should include a security scan.",
       "Catching secrets and vulnerable dependencies in CI is far cheaper than after release.",
       "Add SAST/secret/dependency scanning to the pipeline."),
    _d("ci-uses-cache", "ci",
       "CI should cache dependencies.",
       "Caching keeps the feedback loop fast, which keeps developers running CI.",
       "Enable dependency caching in your workflow."),
    _d("ci-runs-fuzzing", "ci",
       "CI should run the fuzz targets that already exist.",
       "A fuzz harness nobody executes is decoration; regressions only surface if it runs.",
       "Add a CI job that runs the fuzz targets with a bounded case budget.",
       references=["https://google.github.io/oss-fuzz/"]),
    _d("ci-has-sast", "ci",
       "CI should run static application security testing.",
       "SAST catches injection, unsafe deserialization and path traversal before release.",
       "Add CodeQL, Semgrep, Bandit or an equivalent SAST job.",
       references=["https://codeql.github.com/"]),
    _d("require-fuzz-targets", "security",
       "Code that parses untrusted input should ship a fuzz harness.",
       "Parsers fail on input their author never imagined; fuzzing finds those cases cheaply. "
       "This rule stays inert unless the repository really does parse untrusted input.",
       "Add a fuzz target per parser entry point using Atheris, libFuzzer, cargo-fuzz or Hypothesis.",
       references=["https://owasp.org/www-community/Fuzzing", "https://google.github.io/oss-fuzz/"]),
    _d("release-attestation", "security",
       "Release workflows should attest build provenance.",
       "Provenance lets a consumer prove an artifact came from your workflow and commit, "
       "rather than from a compromised token.",
       "Add actions/attest-build-provenance, cosign or sigstore to the release workflow.",
       references=["https://slsa.dev/"]),
    _d("dependency-review", "dependencies",
       "Dependency changes should be reviewed automatically.",
       "Most supply-chain compromise arrives through a routine dependency bump.",
       "Enable Dependabot or Renovate, or add actions/dependency-review-action.",
       references=["https://docs.github.com/code-security/supply-chain-security"]),
    _d("no-hardcoded-secrets", "security",
       "No secrets should be hardcoded in source.",
       "Committed credentials leak instantly and permanently via git history.",
       "Move secrets to environment variables or a secret manager; rotate any exposed keys.",
       references=["https://owasp.org/www-community/vulnerabilities/Use_of_hard-coded_credentials"]),
    _d("no-unsafe-files", "security",
       "Private keys and credential dumps must not be committed.",
       "Files like .env or id_rsa in git are an immediate compromise.",
       "Remove the file, add it to .gitignore, and rotate the credentials."),
    _d("require-security-policy", "security",
       "A security policy should be present.",
       "SECURITY.md tells researchers how to report vulnerabilities responsibly.",
       "Add SECURITY.md with a private reporting channel and response SLA."),
    _d("no-world-writable", "security",
       "No files should be world-writable.",
       "World-writable files are a local tampering and privilege-escalation risk.",
       "chmod o-w the offending files."),
    _d("no-huge-files", "maintainability",
       "Avoid very large files.",
       "Huge files are hard to review and usually indicate missing decomposition.",
       "Split the file, or move large binaries/datasets out of git (e.g. LFS)."),
    _d("bounded-todo-debt", "maintainability",
       "Keep TODO/FIXME debt bounded.",
       "An ever-growing pile of markers is untracked technical debt nobody owns.",
       "Convert TODOs into tracked issues or resolve them."),
    _d("no-committed-build-artifacts", "maintainability",
       "Do not commit generated build output.",
       "Checked-in build output causes merge noise and drifts from source.",
       "Add dist/, build/, and bundles to .gitignore and remove them from git."),
    _d("require-codeowners", "ownership",
       "A CODEOWNERS file should be present.",
       "CODEOWNERS ensures every change gets an accountable, auto-requested reviewer.",
       "Add CODEOWNERS mapping paths to teams.",
       references=["https://docs.github.com/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners"]),
    _d("require-maintainers", "ownership",
       "Maintainers should be declared.",
       "Naming maintainers clarifies who is accountable for the project.",
       "Add a MAINTAINERS file or a maintainers section to the README."),
    _d("require-governance", "ownership",
       "Published projects should document how decisions get made.",
       "Contributors need to know who decides what before they invest effort in a "
       "change. Undocumented governance is the most common reason a promising "
       "outside contribution is abandoned mid-review. Inert unless the repository "
       "has both a licence and a readme, so private repos are never asked.",
       "Add GOVERNANCE.md covering who has merge rights, how maintainers are added "
       "or removed, and how disagreements are resolved. A contributing guide that "
       "explains the review process also satisfies this rule.",
       references=["https://opensource.guide/leadership-and-governance/"]),
    _d("require-support-policy", "ownership",
       "Published projects should say where users get help.",
       "Without a stated channel, support requests arrive as bug reports, and "
       "maintainers burn triage time separating the two. Saying what response "
       "time to expect also sets a boundary that protects the maintainer.",
       "Add SUPPORT.md pointing at issues, discussions or chat, or add a Support "
       "section to the README.",
       references=["https://docs.github.com/communities/setting-up-your-project-for-healthy-contributions/adding-support-resources-to-your-project"]),
    _d("require-opentelemetry", "observability",
       "(Policy) Require OpenTelemetry instrumentation.",
       "Distributed tracing is essential to debug and operate services in production.",
       "Add OpenTelemetry SDK setup and instrument entry points.",
       references=["https://opentelemetry.io/"]),
    _d("require-authentication", "security",
       "(Policy) Require authentication on exposed endpoints.",
       "Unauthenticated endpoints are a common and severe security gap.",
       "Apply an auth dependency/middleware to routes."),
    _d("require-adr", "architecture",
       "Significant architectural decisions should be written down.",
       "Code records what was built, never why, or which alternatives were "
       "rejected. Without that record every past decision gets relitigated, and "
       "new maintainers cannot tell a deliberate trade-off from an accident. "
       "Inert below 40 source files, where a decision log would be overhead.",
       "Add docs/adr/ with short numbered records (context, decision, "
       "consequences), or an ARCHITECTURE.md explaining the structure and its "
       "trade-offs.",
       references=["https://adr.github.io/"]),
    _d("no-direct-sql", "architecture",
       "(Policy) Forbid raw SQL outside the repository layer.",
       "Scattered SQL bypasses the data layer and invites injection and coupling.",
       "Move queries into the repository layer or an ORM."),
    _d("require-pre-commit", "maintainability",
       "Projects with CI should also run checks locally before commit.",
       "A formatting failure caught in CI costs a full pipeline run and a "
       "context switch; caught by a local hook it costs a second. Hooks also keep "
       "the diff clean, so review attention goes to the change rather than to "
       "whitespace. Inert when the repository has no CI at all.",
       "Add .pre-commit-config.yaml wiring the same formatter and linter that CI "
       "runs, then 'pre-commit install'.",
       references=["https://pre-commit.com/"]),
    _d("no-console-log", "maintainability",
       "(Policy) Forbid console.log/print debugging in shipped code.",
       "Debug prints leak into production logs and hide real logging.",
       "Use a structured logger; remove stray prints."),
    _d("require-dockerignore", "repository",
       "(Policy) Require a .dockerignore when a Dockerfile is present.",
       "Without .dockerignore, build context balloons and secrets can enter images.",
       "Add a .dockerignore excluding VCS, caches, and secrets."),
    _d("require-editorconfig", "repository",
       "(Policy) Require an .editorconfig.",
       "An .editorconfig keeps formatting consistent across editors and contributors.",
       "Add an .editorconfig with indentation and newline rules.",
       references=["https://editorconfig.org/"]),
    # --- Architecture (clean architecture) ---
    _d("respect-clean-architecture", "architecture",
       "Inner layers must not depend on outer layers.",
       "In Clean Architecture, dependencies point inward: Domain knows nothing about Application or Infrastructure. When the Domain imports a database or framework, business rules become impossible to test or reuse.",
       "Depend on abstractions defined in the inner layer and inject implementations from the outside.",
       ["Domain -> Application -> Infrastructure",
        "infrastructure/ may import domain/, never the reverse"],
       ["https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html"]),
    # --- Observability ---
    _d("observable-logging", "observability",
       "Long-running services should emit structured logs.",
       "When something breaks at 3am, logs are the first thing anyone reaches for; a service with no logging is a black box.",
       "Adopt a structured logger and log request lifecycle and errors.",
       ["Python: structlog / logging", "Node: pino / winston", "Go: zap / slog"],
       ["https://12factor.net/logs"]),
    _d("error-tracking", "observability",
       "Production services should report errors to a tracker.",
       "Unaggregated exceptions are invisible; error tracking turns crashes into actionable, deduplicated alerts.",
       "Integrate Sentry, Rollbar, or OpenTelemetry error reporting at the process boundary.",
       ["sentry_sdk.init(dsn=...)"],
       ["https://opentelemetry.io/"]),
    # --- Operations ---
    _d("deployable-artifact", "operations",
       "The project should be packageable or deployable.",
       "Software that cannot be built into an artifact cannot be shipped reliably or reproducibly.",
       "Add packaging metadata (pyproject.toml/package.json/go.mod) or a Dockerfile / deployment descriptor.",
       ["Dockerfile", "pyproject.toml", "charts/ (Helm)"]),
    _d("dockerfile-healthcheck", "operations",
       "A Dockerfile that exposes a port should declare a HEALTHCHECK.",
       "Without a healthcheck, orchestrators cannot tell a hung container from a healthy one and keep routing traffic to it. "
       "This applies to service images only: the rule stays inert for CLI and batch images (no EXPOSE), because Docker runs a "
       "healthcheck only while a container is alive, so an image that does its work and exits has nothing to probe.",
       "Add a HEALTHCHECK instruction that probes a liveness endpoint.",
       ["HEALTHCHECK CMD curl -f http://localhost:8000/health || exit 1"],
       ["https://docs.docker.com/reference/dockerfile/#healthcheck"]),
    # --- Compliance ---
    _d("declared-license", "compliance",
       "The license must be declared in machine-readable form.",
       "Automated compliance and SBOM tooling reads license metadata; a license only humans can find does not satisfy audits.",
       "Add a LICENSE file and declare the license in package metadata (e.g. pyproject [project] license).",
       ["LICENSE", "pyproject.toml -> [project] license"],
       ["https://spdx.org/licenses/"]),
    _d("dependency-audit", "compliance",
       "Dependencies should be automatically audited for vulnerabilities.",
       "Manual dependency review does not scale; automated auditing catches known CVEs as they are disclosed.",
       "Enable Dependabot, Renovate, or Snyk to track and update vulnerable dependencies.",
       [".github/dependabot.yml", "renovate.json"],
       ["https://docs.github.com/code-security/dependabot"]),

    # --- Domain Standards -------------------------------------------------
    # These only apply when the matching technology is detected. Universal
    # rules run everywhere; domain rules make Deval progressively smarter.
    _d("fastapi-endpoint-auth", "security",
       "FastAPI routes should be protected by an authentication dependency.",
       "An unauthenticated endpoint is an open door; auth belongs at the route boundary, not scattered in handlers.",
       "Attach Depends()/Security() with OAuth2 or an API-key scheme to routers or routes.",
       ["Depends(get_current_user)", "Security(oauth2_scheme)"],
       ["https://fastapi.tiangolo.com/tutorial/security/"]),
    _d("fastapi-health-endpoint", "operations",
       "A FastAPI service should expose a health endpoint.",
       "Load balancers and orchestrators need a cheap liveness signal to route traffic and restart bad pods.",
       "Add GET /health returning 200 when the process is serving.",
       ["@app.get('/health')"],
       ["https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/"]),
    _d("fastapi-cors-configured", "security",
       "CORS should be configured explicitly.",
       "A missing or wildcard CORS policy either breaks browsers or exposes the API to any origin.",
       "Add CORSMiddleware with an explicit allow-list of origins, methods, and headers.",
       ["app.add_middleware(CORSMiddleware, allow_origins=[...])"],
       ["https://fastapi.tiangolo.com/tutorial/cors/"]),
    _d("fastapi-pydantic-models", "architecture",
       "Request and response bodies should use Pydantic models.",
       "Typed models give validation, docs, and serialization for free and stop untyped dict payloads leaking through.",
       "Declare BaseModel schemas and annotate endpoints with them.",
       ["class Item(BaseModel): ..."],
       ["https://docs.pydantic.dev/"]),
    _d("react-error-boundaries", "maintainability",
       "React apps should use error boundaries.",
       "Without a boundary, one render error unmounts the whole tree and shows users a blank screen.",
       "Wrap route/tree roots in an ErrorBoundary (or react-error-boundary).",
       ["<ErrorBoundary>...</ErrorBoundary>"],
       ["https://react.dev/reference/react/Component#catching-rendering-errors-with-an-error-boundary"]),
    _d("react-accessibility", "documentation",
       "Components should be accessible.",
       "Accessibility is correctness: missing alt text, roles, and ARIA locks out real users and fails audits.",
       "Add alt/ARIA attributes and enable eslint-plugin-jsx-a11y in CI.",
       ["<img alt=...>", "aria-label=..."],
       ["https://www.w3.org/WAI/ARIA/apg/"]),
    _d("k8s-resource-limits", "operations",
       "Containers should declare resource requests and limits.",
       "Without limits a single pod can starve a node; without requests the scheduler cannot place workloads safely.",
       "Set resources.requests and resources.limits for cpu and memory.",
       ["resources:"],
       ["https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/"]),
    _d("k8s-non-root", "security",
       "Containers should not run as root.",
       "A root container that is compromised can more easily escalate to the node.",
       "Set securityContext.runAsNonRoot: true and a numeric runAsUser.",
       ["runAsNonRoot: true"],
       ["https://kubernetes.io/docs/tasks/configure-pod-container/security-context/"]),
    _d("k8s-image-pinning", "dependencies",
       "Container images should be pinned.",
       "The :latest tag makes deployments non-reproducible and can silently ship a different image.",
       "Pin images to an immutable tag or a sha256 digest.",
       ["image: app@sha256:..."],
       ["https://kubernetes.io/docs/concepts/containers/images/"]),
    _d("terraform-encryption", "security",
       "Stateful Terraform resources should enable encryption.",
       "Unencrypted storage and state can leak secrets and data at rest.",
       "Enable encryption (KMS/SSE) on buckets, disks, databases, and remote state.",
       ["server_side_encryption { ... }"],
       ["https://developer.hashicorp.com/terraform"]),
    _d("terraform-least-privilege-iam", "security",
       "IAM policies should follow least privilege.",
       "Wildcard actions/resources grant far more than needed and turn any leak into a full compromise.",
       "Scope Action and Resource to the specific operations required.",
       ["Action: s3:GetObject"],
       ["https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html"]),
    _d("ml-experiment-tracking", "maintainability",
       "ML projects should track experiments.",
       "Untracked runs cannot be compared or reproduced; results become anecdotes.",
       "Log params, metrics, and artifacts to MLflow, Weights & Biases, or TensorBoard.",
       ["mlflow.log_metric(...)"],
       ["https://mlflow.org/"]),
    _d("ml-random-seeds", "maintainability",
       "ML code should set random seeds.",
       "Unseeded runs are not reproducible, so regressions and improvements cannot be trusted.",
       "Seed Python, NumPy, and your framework at startup.",
       ["torch.manual_seed(0)", "np.random.seed(0)"],
       ["https://pytorch.org/docs/stable/notes/randomness.html"]),
    _d("ml-model-card", "documentation",
       "Models should ship a model card.",
       "A model card documents intended use, data, metrics, and limitations - essential for responsible ML.",
       "Add MODEL_CARD.md describing the model, data, metrics, and caveats.",
       ["MODEL_CARD.md"],
       ["https://modelcards.withgoogle.com/about"]),
    _d("llm-eval-datasets", "testing",
       "LLM apps should keep evaluation datasets.",
       "Without an eval set you cannot tell if a prompt or model change made quality better or worse.",
       "Store labelled eval cases (e.g. evals/*.jsonl) and run them in CI.",
       ["evals/qa.jsonl"],
       ["https://github.com/openai/evals"]),
    _d("llm-safety-tests", "security",
       "LLM apps should have safety tests.",
       "Prompt injection and unsafe outputs are the top LLM risks; they need explicit regression tests.",
       "Add guardrail/moderation and prompt-injection tests around model calls.",
       ["test_prompt_injection"],
       ["https://owasp.org/www-project-top-10-for-large-language-model-applications/"]),
    _d("llm-retry-policies", "operations",
       "Model calls should use retry/backoff.",
       "Provider APIs fail transiently; without retries a single blip becomes a user-facing error.",
       "Wrap calls with tenacity/backoff and cap max retries with jitter.",
       ["@retry(stop=stop_after_attempt(3))"],
       ["https://tenacity.readthedocs.io/"]),
    _d("microservices-health-endpoint", "operations",
       "Each service should expose a health endpoint.",
       "Orchestration and service meshes need per-service health to route and heal.",
       "Expose /health (and optionally /ready) per service.",
       ["GET /health"],
       ["https://microservices.io/patterns/observability/health-check-api.html"]),
    _d("microservices-timeouts", "maintainability",
       "Outbound calls should set timeouts.",
       "A call without a timeout can hang forever and cascade into a full outage.",
       "Set explicit connect/read timeouts on every outbound client.",
       ["httpx.Client(timeout=5)"],
       ["https://microservices.io/patterns/reliability/circuit-breaker.html"]),
    _d("data-dbt-tests", "testing",
       "dbt models should declare tests.",
       "Untested transformations silently corrupt downstream analytics.",
       "Add not_null/unique/relationships tests in schema.yml.",
       ["tests: [not_null]"],
       ["https://docs.getdbt.com/docs/build/tests"]),
    _d("data-schema-validation", "compliance",
       "Data pipelines should validate schemas.",
       "Schema drift breaks pipelines far downstream where it is expensive to trace.",
       "Validate with pandera/Great Expectations or enforce data contracts.",
       ["pandera.DataFrameSchema(...)"],
       ["https://greatexpectations.io/"]),
    _d("security-sbom", "compliance",
       "Projects should publish an SBOM.",
       "A software bill of materials is required to answer 'are we affected?' when a CVE lands.",
       "Generate a CycloneDX or SPDX SBOM in CI and attach it to releases.",
       ["cyclonedx-bom", "syft"],
       ["https://cyclonedx.org/"]),
    _d("docker-nonroot-user", "security",
       "Docker images should run as a non-root user.",
       "Running as root widens the blast radius of any container escape.",
       "Create and switch to a non-root USER in the Dockerfile.",
       ["USER app"],
       ["https://docs.docker.com/develop/develop-images/dockerfile_best-practices/"]),
    _d("docker-pin-base-image", "dependencies",
       "Docker base images should be pinned.",
       "An unpinned or :latest base image makes builds non-reproducible and can pull in breaking changes.",
       "Pin FROM to a specific tag or digest.",
       ["FROM python:3.12-slim"],
       ["https://docs.docker.com/develop/develop-images/dockerfile_best-practices/"]),
]

RULE_DOCS: dict[str, RuleDoc] = {d.rule_id: d for d in _DOCS}

# Some domain checks were introduced before their educational entries. Keep the
# public promise that every stable DV rule is explainable. These concise entries
# are intentionally generated from an explicit category map (not guessed at
# runtime), while richer hand-authored entries above remain authoritative.
_SUPPLEMENTAL_CATEGORIES = {
    "fastapi-error-handlers": "operations", "fastapi-openapi-docs": "documentation",
    "k8s-liveness-probe": "operations", "k8s-readiness-probe": "operations",
    "k8s-security-context": "security", "llm-prompt-versioning": "maintainability",
    "llm-structured-outputs": "architecture", "llm-telemetry": "observability",
    "microservices-graceful-shutdown": "operations",
    "microservices-metrics-endpoint": "observability", "microservices-tracing": "observability",
    "ml-dataset-versioning": "compliance", "ml-evaluation-metrics": "testing",
    "ml-model-versioning": "maintainability", "react-component-organization": "architecture",
    "react-lazy-loading": "maintainability", "react-testing": "testing",
    "security-signed-commits": "compliance", "terraform-remote-state": "operations",
    "terraform-tags": "compliance", "terraform-version-pinning": "dependencies",
    "data-contracts": "compliance", "data-freshness-checks": "operations",
}
_CATEGORY_WHY = {
    "architecture": "Explicit structure prevents accidental coupling and keeps change local.",
    "compliance": "Auditable evidence reduces governance risk and makes controls repeatable.",
    "dependencies": "Pinned inputs make builds reproducible and reduce supply-chain drift.",
    "documentation": "Discoverable contracts reduce misuse and shorten onboarding time.",
    "maintainability": "Repeatable conventions keep the system safe to change as it grows.",
    "observability": "Production systems need evidence that explains behavior and failures.",
    "operations": "Reliable runtime behavior requires explicit deployment and lifecycle controls.",
    "security": "Secure defaults reduce blast radius before an incident occurs.",
    "testing": "Automated evidence is the only reliable way to detect regressions before release.",
}
for _rule_id, _category in _SUPPLEMENTAL_CATEGORIES.items():
    if _rule_id not in RULE_DOCS:
        _label = _rule_id.replace("-", " ")
        RULE_DOCS[_rule_id] = _d(
            _rule_id, _category,
            f"The repository should enforce {_label}.",
            _CATEGORY_WHY[_category],
            f"Add evidence for {_label}, validate it automatically, and enforce it in CI.",
            [f"Expected evidence: {_label}"],
        )


def explain(rule_id: str) -> str | None:
    """Return the full explanation for ``rule_id``, or ``None`` if undocumented.

    Not every rule ships an ``explain`` doc; callers should treat ``None`` as
    "no documentation available" rather than an unknown rule.
    """
    doc = RULE_DOCS.get(rule_id)
    return doc.render() if doc else None


def why(rule_id: str) -> str | None:
    """Return the rationale for ``rule_id``, or ``None`` if undocumented.

    This is the "why should I care" paragraph shown next to a finding, kept
    separate from the fix so reports can surface motivation without remediation.
    """
    doc = RULE_DOCS.get(rule_id)
    return doc.why if doc else None


def fix_hint(rule_id: str) -> str | None:
    """Return the remediation advice for ``rule_id``, or ``None`` if undocumented.

    Used to populate the ``remediation`` field on findings so every violation
    tells the reader what to actually do about it.
    """
    doc = RULE_DOCS.get(rule_id)
    return doc.fix if doc else None
