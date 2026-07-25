"""Marketplace pack: Kubernetes / infra manifest hygiene.

Inert unless the repository contains Kubernetes manifests (YAML with a top-level
``kind:`` and ``apiVersion:``). Rules land in the security and maintainability
categories so they roll into the single health score.
"""

from __future__ import annotations

from collections.abc import Iterable

from deval.sdk import CheckContext, Finding, rule


def _manifests(ctx: CheckContext) -> list:
    out = []
    for rf in ctx.index.by_suffix(".yaml", ".yml"):
        text = ctx.index.read_text(rf)
        if "kind:" in text and "apiVersion:" in text:
            out.append((rf, text))
    return out


@rule("k8s-no-latest-tag", "security")
def k8s_no_latest_tag(ctx: CheckContext) -> Iterable[Finding]:
    manifests = _manifests(ctx)
    if not manifests:
        return
    flagged = False
    for rf, text in manifests:
        for i, line in enumerate(text.splitlines(), start=1):
            s = line.strip()
            if s.startswith("image:") and (s.endswith(":latest") or ":" not in s.split("image:", 1)[1].strip()):
                flagged = True
                yield ctx.fail("k8s-no-latest-tag", "security",
                               "Container image uses ':latest' or an untagged image",
                               path=rf.relpath, line=i,
                               remediation="Pin images to an immutable tag or digest.")
    if not flagged:
        yield ctx.ok("k8s-no-latest-tag", "security", "All container images are pinned")


@rule("k8s-resource-limits", "maintainability")
def k8s_resource_limits(ctx: CheckContext) -> Iterable[Finding]:
    manifests = _manifests(ctx)
    if not manifests:
        return
    workloads = [(rf, t) for rf, t in manifests
                 if any(k in t for k in ("kind: Deployment", "kind: StatefulSet", "kind: DaemonSet"))]
    if not workloads:
        return
    missing = [rf.relpath for rf, t in workloads if "resources:" not in t]
    if missing:
        for path in missing:
            yield ctx.fail("k8s-resource-limits", "maintainability",
                           "Workload has no resource requests/limits",
                           path=path,
                           remediation="Set resources.requests and resources.limits.")
    else:
        yield ctx.ok("k8s-resource-limits", "maintainability", "Workloads declare resource limits")
