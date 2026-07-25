# Deval Principles

These seven principles are Deval's design philosophy. Every feature, rule, and
interface decision is measured against them. When two designs compete, the one
that better honors these principles wins.

## 1. Deterministic first

Given the same repository and configuration, Deval always produces the same
findings, in the same order, with the same score. No network calls, no
randomness, no time-of-day flakiness in the core engine. Determinism is what
makes the quality gate trustworthy enough to block a merge.

## 2. Opinionated defaults

`deval scan .` should be useful with zero configuration. Deval ships a strong
baseline (`deval/recommended`) so a brand-new repository gets a meaningful score
and actionable findings on day one. You can always override, but you should
rarely have to.

## 3. Extensible policies

Organizations have rules that no upstream tool will ever ship. Deval treats
policy as a first-class, pluggable layer: enable opt-in built-ins, tune
severities per dimension, or drop a Python file into a plugin directory. Your
standard is code, versioned alongside the repositories it governs.

## 4. Repository over files

Most tools ask "is this line wrong?" Deval asks "is this repository healthy?"
Architecture layering, ownership, test presence, licensing, and CI hygiene are
properties of the whole repository, not of any single file. Deval evaluates the
repository as the unit of quality.

## 5. Local first

Everything runs on your machine, offline, in the same way it runs in CI. There
is no mandatory server, no account, and no telemetry required to get a full
report. What you see locally is exactly what the gate sees.

## 6. Explain every finding

A finding that only says "failed" teaches nothing. Every Deval rule carries the
same five sections a good code reviewer would give you — **Problem, Why,
Example, Fix, References** — so `deval explain` reads like a mentor, not a
linter. Developers should leave every scan having learned something.

## 7. Integrate, don't reinvent

Where a best-in-class tool already exists (ruff, eslint, gitleaks, trivy),
Deval integrates it rather than reimplementing it — but integrations are an
implementation detail, never the product. If every integration disappeared
tomorrow, Deval's native engine would still deliver a valuable, standalone
Engineering Health score.

---

> The order matters: **Standard → Evaluation → Policy → Integrations.**
> Deval is a standard you evaluate against and enforce with policy. Tools plug
> in at the end — they never lead.
