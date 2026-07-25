# Roadmap

What is actually planned, and what is deliberately not. Dates are absent on
purpose — this is a single-maintainer project and a date would be fiction.

## Shipped (0.7.0)

- 13 engineering dimensions, 102 rules, 43 checks
- Zero required runtime dependencies
- 6 reporters: terminal, JSON, HTML, Markdown, SARIF, XML
- Plugin rule SDK, baselines, autofix, profiles, standards hierarchy
- Integration normalisation for Ruff, Semgrep, Trivy, Gitleaks into SARIF
- Self-scanning GitHub Action; the project scores 100/100 on its own ruleset
- Browser demo via Pyodide — scan a zip with nothing installed
- Dependency-free fuzz harness over the parser surface, plus an Atheris
  harness for coverage-guided runs
- CodeQL, dependency review, and build provenance attestation in CI

## Next

- **Standard lockfile.** Record which standard version a scan ran against,
  with a checksum, so a team can prove the gate did not silently move under
  them. Groundwork for auditability.
- **Rule stability tiers.** Mark each rule stable / preview / deprecated so
  consumers can opt out of churn.
- **Incremental scanning.** Reuse results for unchanged files; `--changed-files`
  already exists but does not yet cache.
- **More language coverage in structure and architecture checks.** Present
  coverage is strongest for Python and TypeScript.

## Under consideration

- SBOM generation (CycloneDX) as a first-class reporter
- A hosted scan endpoint, if the browser demo proves the demand

## Explicitly not planned

These are declined rather than unscheduled, and the reasons matter:

- **LLM-as-judge scoring.** Deval's value is that it is deterministic: the same
  repository scores identically on every run, on every machine, forever. A
  model in the scoring path destroys that, makes findings unreproducible, and
  makes the gate unarguable in code review. Non-negotiable.
- **Running a fuzzer inside `deval scan`.** Fuzzing is unbounded work with
  nondeterministic output; a scan must terminate quickly and return the same
  result twice. Deval instead *checks that you fuzz* (`require-fuzz-targets`,
  `ci-runs-fuzzing`) and fuzzes its own parsers in its own CI.
- **Auto-fixing security findings.** Autofix is limited to mechanical,
  reviewable changes. Silently rewriting security-relevant code is how a tool
  becomes the vulnerability.
- **A score that can be gamed by adding empty files.** Every rule must be
  satisfiable only by doing the real thing. See the bar for new rules in
  [GOVERNANCE.md](GOVERNANCE.md).
