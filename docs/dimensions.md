# Engineering Dimensions

Deval does not produce a flat checklist. It scores your repository across thirteen
**Engineering Dimensions** — each a formal identity with its own score and
letter grade. Together they roll up into a single **Engineering Health** score.

This is the difference between a linter and an engineering framework. A linter
tells you a line is wrong. Engineering Dimensions tell you *what kind* of
healthy (or unhealthy) your repository is.

```
Engineering Health

  Architecture      A
  Security          A+
  Testing           B
  Operations        A
  Observability     C

  Overall           93
```

## The dimensions

| Dimension | What it measures |
|---|---|
| **Architecture** | Layering and dependency direction: Controller → Service → Repository, or Domain → Application → Infrastructure. No cycles, no layer-skipping. |
| **Documentation** | Can a newcomer understand and use the project? README sections, public API docs, working links. |
| **Testing** | Is change safe? Presence of tests, a healthy test-to-source ratio, coverage configuration. |
| **Security** | Are there obvious ways to get owned? Hardcoded secrets, unsafe files, a security policy, authenticated endpoints. |
| **Dependencies** | Is the supply chain sound? Lockfiles, pinned actions, no duplicates or abandoned packages. |
| **CI/CD** | Does every change get checked automatically? Pipeline presence, tests in CI, security scans, caching. |
| **Ownership** | Is someone accountable? CODEOWNERS and declared maintainers. |
| **Maintainability** | Will this age well? File size, TODO/FIXME debt, no committed build artifacts, no stray debug logging. |
| **Observability** | Can you see what a running service is doing? Structured logging and error tracking (only asserted for services). |
| **Operations** | Can it be built, shipped, and run? Packaging metadata, deployment descriptors, container healthchecks. |
| **Compliance** | Is it audit-ready? Machine-readable license declaration and automated dependency auditing. |
| **Repository** | Does the project have the baseline artifacts needed for adoption and collaboration? README, license, contribution guide, changelog. |
| **Structure** | Is code laid out predictably for humans and tooling? Conventional source and test directories. |

## How a dimension is scored

1. Every native check and every integration finding is tagged with exactly one
   dimension.
2. Each finding carries a severity: `error`, `warning`, `info`, or `off`.
3. A dimension starts at 100 and subtracts a penalty per failing finding
   (`error` 18, `warning` 7, `info` 2). Passing findings cost nothing.
4. The dimension's score maps to a letter grade (A+ ≥ 97, A ≥ 93, A- ≥ 90,
   B+ ≥ 85, B ≥ 80, C+ ≥ 75, C ≥ 70, D ≥ 60, F < 60).
5. **Engineering Health (Overall)** is the weight-adjusted average of every
   dimension that actually ran. Dimensions with no applicable checks are simply
   omitted — they never drag the score down.

Because the mapping from findings to dimensions is fixed and deterministic, the
same repository always earns the same per-dimension grades and the same overall
score. Weight the dimensions your team cares about most in `.deval.yml`:

```yaml
weights:
  security: 1.5
  architecture: 1.25
```

## Rule codes

Every rule has a stable **DV code** grouped by dimension, so findings and docs
stay clean and greppable:

- `DV1001` Missing README
- `DV2004` Missing Tests
- `DV4011` Missing SECURITY.md
- `DV7003` Clean-architecture dependency points outward

Look any of them up with `deval explain DV1001` (or `deval explain require-readme`).
