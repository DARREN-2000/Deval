"""Technology auto-detection.

The flagship user experience of Deval is that ``deval scan .`` requires no
configuration: Deval inspects the repository, deterministically detects the
technologies in use, and automatically applies the matching **Domain
Standards** on top of the universal baseline. As the codebase grows, Deval gets
progressively smarter without the user changing a single line of config.

Detection is intentionally conservative and evidence-based. We never guess from
a loose substring anywhere in the tree; we look for real signals — an import
statement, a dependency declaration in a manifest, a manifest file, or a
characteristic config file. This keeps detection deterministic and avoids false
positives (for example, the word "fastapi" appearing in documentation does not
make a repository a FastAPI service).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

from .fsindex import RepoIndex

# Manifest files whose contents legitimately declare dependencies. We only look
# for dependency *names* inside these, never across arbitrary source files.
_MANIFESTS = (
    "pyproject.toml", "setup.py", "setup.cfg", "requirements.txt",
    "requirements-dev.txt", "Pipfile", "poetry.lock", "package.json",
    "go.mod", "pom.xml", "build.gradle", "build.gradle.kts", "Gemfile",
    "Cargo.toml", "composer.json",
)

_PY = (".py",)
_JS = (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs")


def _read_all(index: RepoIndex, files) -> str:
    return "\n".join(index.read_text(rf) for rf in files)


def manifest_text(index: RepoIndex) -> str:
    """Lowercased concatenation of dependency manifests only."""
    parts: list[str] = []
    for name in _MANIFESTS:
        rf = index.find(name)
        if rf:
            parts.append(index.read_text(rf).lower())
    # package.json can live in subfolders too (monorepos)
    for rf in index.glob("**/package.json"):
        parts.append(index.read_text(rf).lower())
    return "\n".join(parts)


def dep_declared(index: RepoIndex, *names: str) -> bool:
    """True if any of the dependency names appears in a manifest, as a word."""
    text = manifest_text(index)
    return any(re.search(r"\b" + re.escape(n.lower()) + r"\b", text) for n in names)


def _import_regex(modules) -> re.Pattern[str]:
    alt = "|".join(re.escape(m) for m in modules)
    # Matches: `import <mod>` or `from <mod>` / `require('<mod>')` style roots.
    return re.compile(r"(?m)^[ \t]*(?:import|from)[ \t]+(?:" + alt + r")(?:[.\s,;]|$)")


def imports_any(index: RepoIndex, modules, suffixes=_PY) -> bool:
    """True if any source file contains an import of one of the modules.

    Only real import statements count, so a module name mentioned in a string or
    comment never triggers detection.
    """
    rx = _import_regex(modules)
    for rf in index.by_suffix(*suffixes):
        if rx.search(index.read_text(rf)):
            return True
    return False


def _yaml_files(index: RepoIndex):
    return index.by_suffix(".yaml", ".yml")


def _has_k8s_manifest(index: RepoIndex) -> bool:
    for rf in _yaml_files(index):
        text = index.read_text(rf)
        if re.search(r"(?m)^apiVersion:", text) and re.search(r"(?m)^kind:", text):
            return True
    if index.find("Chart.yaml") or index.find_any_dir("charts"):
        return True
    for d in ("k8s", "kubernetes", "manifests"):
        if index.find_any_dir(d):
            return True
    return False


def _has_compose(index: RepoIndex) -> bool:
    return index.has("docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml")


def _compose_text(index: RepoIndex) -> str:
    for name in ("docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"):
        rf = index.find(name)
        if rf:
            return index.read_text(rf)
    return ""


def _is_microservices(index: RepoIndex) -> bool:
    # Two or more services declared in a compose file...
    compose = _compose_text(index)
    if compose:
        m = re.search(r"(?m)^services:\s*$", compose)
        if m:
            body = compose[m.end():]
            names = re.findall(r"(?m)^  ([A-Za-z0-9_.-]+):\s*$", body)
            if len(names) >= 2:
                return True
    # ...or a services/ (or apps/) directory with 2+ subprojects.
    for parent in ("services", "apps"):
        subs = set()
        for rf in index.files:
            parts = rf.relpath.split("/")
            if len(parts) >= 3 and parts[0] == parent:
                subs.add(parts[1])
        if len(subs) >= 2:
            return True
    return False


def _is_data(index: RepoIndex) -> bool:
    if index.has("dbt_project.yml", "dbt_project.yaml"):
        return True
    if index.find_any_dir("great_expectations"):
        return True
    if imports_any(index, ["dbt", "pandera", "great_expectations", "soda", "airflow"]):
        return True
    # dbt-style SQL models
    return bool(index.find_any_dir("models") and index.by_suffix(".sql"))


@dataclass(frozen=True)
class Detection:
    key: str
    label: str

    @property
    def standard(self) -> str:
        return f"deval/{self.key}"


# Ordered so the report reads naturally: language, then frameworks, then infra,
# cloud, and finally data/AI. Order is stable and drives the "Detected" list.
_DETECTORS: dict[str, tuple[str, Callable[[RepoIndex], bool]]] = {
    "python": ("Python", lambda i: bool(i.by_suffix(".py")) or i.has(
        "pyproject.toml", "setup.py", "setup.cfg", "requirements.txt", "Pipfile")),
    "go": ("Go", lambda i: i.has("go.mod") or bool(i.by_suffix(".go"))),
    "java": ("Java", lambda i: i.has("pom.xml", "build.gradle", "build.gradle.kts")
             or bool(i.by_suffix(".java"))),
    "react": ("React", lambda i: dep_declared(i, "react") or bool(i.by_suffix(".jsx", ".tsx"))),
    "nextjs": ("Next.js", lambda i: dep_declared(i, "next")
               or i.has("next.config.js", "next.config.mjs", "next.config.ts")),
    "fastapi": ("FastAPI", lambda i: imports_any(i, ["fastapi"]) or dep_declared(i, "fastapi")),
    "spring": ("Spring", lambda i: dep_declared(i, "springframework", "spring-boot")),
    "docker": ("Docker", lambda i: i.has("Dockerfile") or _has_compose(i)),
    "kubernetes": ("Kubernetes", _has_k8s_manifest),
    "terraform": ("Terraform", lambda i: bool(i.by_suffix(".tf"))),
    "aws": ("AWS", lambda i: imports_any(i, ["boto3", "botocore", "aioboto3"])
            or dep_declared(i, "boto3", "aws-sdk", "aws-cdk-lib")
            or bool(re.search(r'provider\s+"aws"|resource\s+"aws_', _read_all(i, i.by_suffix(".tf"))))),
    "gcp": ("Google Cloud", lambda i: imports_any(i, ["google.cloud"])
            or dep_declared(i, "google-cloud", "google-cloud-storage")
            or bool(re.search(r'provider\s+"google"', _read_all(i, i.by_suffix(".tf"))))),
    "postgres": ("PostgreSQL", lambda i: dep_declared(i, "psycopg", "psycopg2", "asyncpg", "pg8000", "pg", "postgres")
                 or bool(re.search(r"postgres", _compose_text(i), re.IGNORECASE))),
    "github": ("GitHub Actions", lambda i: bool(i.glob(".github/workflows/*.yml") or i.glob(".github/workflows/*.yaml"))),
    "ml": ("Machine Learning", lambda i: imports_any(
        i, ["torch", "tensorflow", "sklearn", "keras", "xgboost", "lightgbm", "jax", "catboost"])),
    "llm": ("LLM / AI", lambda i: imports_any(
        i, ["openai", "anthropic", "langchain", "llama_index", "llamaindex", "cohere", "mistralai", "litellm"])),
    "data": ("Data Engineering", _is_data),
    "microservices": ("Microservices", _is_microservices),
}


def matches(index: RepoIndex, key: str) -> bool:
    """Return True if the given technology key is detected in the repository."""
    entry = _DETECTORS.get(key)
    if not entry:
        return False
    try:
        return bool(entry[1](index))
    except Exception:
        return False


def detect(index: RepoIndex) -> list[Detection]:
    """Return every detected technology, in stable presentation order."""
    out: list[Detection] = []
    for key, (label, pred) in _DETECTORS.items():
        try:
            if pred(index):
                out.append(Detection(key=key, label=label))
        except Exception:
            continue
    return out


def detectable_keys() -> list[str]:
    return list(_DETECTORS.keys())
