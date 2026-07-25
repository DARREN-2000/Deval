# Security Policy

## Reporting a vulnerability

Please report security issues privately through
[GitHub Security Advisories](https://github.com/DARREN-2000/deval/security/advisories/new)
on this repository. We aim to acknowledge reports within 72 hours and to ship a
fix or mitigation within 30 days.

Do not open public issues for undisclosed vulnerabilities.

## Supported versions

The latest minor release receives security fixes.

## Scope and threat model

Deval reads repositories that may be untrusted. Two properties matter most:

- **Deval never executes the code it scans.** Analysis is static. The one
  exception is plugin rules, which are Python and therefore run with your
  privileges — only enable plugins from sources you trust. The browser scanner
  on the documentation site always disables plugin loading.
- **External integrations are invoked as subprocesses** (Ruff, Semgrep, Trivy,
  Gitleaks). Their own security posture applies when enabled.

Reports of report-format injection (for example, crafted file paths breaking out
of HTML or SARIF output) are in scope and treated as security issues.
