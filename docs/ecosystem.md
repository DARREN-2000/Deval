# Deval Ecosystem

Deval is a platform, not a single binary. The core — the Deval Standard, the
evaluation engine, the policy layer, and the Engineering Health score — is the
product. Everything below is a distribution channel for that same core, so the
score you get locally is the score you get everywhere.

> **Status:** the CLI and the GitHub Action (`action.yml`) ship today. The
> language SDKs and the server are on the roadmap; this page documents the
> intended shape so the platform grows coherently.

## Shipping today

### `deval` (CLI)
The reference implementation. Scans, scores, explains, baselines, trends,
graphs, and enforces the gate — fully offline and deterministic.

### `deval-action` (CI)
The GitHub Action wrapper (`action.yml`). Runs `deval scan` on every push and
pull request, posts the Markdown report as a job summary, and fails the check
when the gate is not satisfied.

## On the roadmap

### `deval-server`
A central service that ingests reports from many repositories to power
organization-wide dashboards, trend history, and policy roll-out. It stores and
aggregates results — it never becomes a hidden dependency of the local engine.

### Language rule SDKs
Write rules in the language your team already uses; each SDK speaks the same
finding contract and the same dimensions, so a rule's verdict is identical no
matter where it runs.

| Package | Ecosystem |
|---|---|
| `deval-python` | Python rule authors (the reference SDK) |
| `deval-go` | Go |
| `deval-java` | JVM |
| `deval-rust` | Rust |

## The contract every component shares

Whatever the surface — CLI, Action, server, or SDK — all of it agrees on:

1. **The Deval Standard** — the versioned set of rules and their DV codes.
2. **Engineering Dimensions** — the thirteen categories every finding rolls up into.
3. **Deterministic findings** — same input, same output, everywhere.
4. **One Engineering Health score** — comparable across repos and over time.

That shared contract is why the ecosystem can grow without fragmenting: add a
new language SDK or a new integration, and it still produces the same Deval
Standard verdict as `deval scan .` on your laptop.
