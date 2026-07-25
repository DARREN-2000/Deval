# Governance

Deval is currently a **single-maintainer project**. This document says so
plainly rather than describing a committee structure that does not exist, so
that contributors know what to expect before they spend time on a change.

## Roles

| Role | Who | Rights |
|---|---|---|
| Maintainer | See [MAINTAINERS.md](MAINTAINERS.md) | Merge, release, set direction |
| Contributor | Anyone with a merged PR | Review, propose rules |

There is no formal committee. If the project grows to the point where one is
warranted, this document changes first.

## How decisions are made

The maintainer decides. In practice that means:

- **Bug fixes and documentation** — merged once CI is green and the change is
  understood.
- **New rules** — held to the bar in the section below. Most rejections happen
  here, so read it before opening a PR.
- **Breaking changes** — require a major version bump and a CHANGELOG entry
  describing the migration.

## The bar for a new rule

Deval scores other people's repositories. A rule that fires wrongly costs a
stranger their time and teaches them to ignore the tool, so the bar is
deliberately high. A proposed rule must:

1. **Be deterministic.** Same input, same finding, on every machine. No
   network calls, no clocks, no model output.
2. **State when it is inert.** Every rule must name the conditions under which
   it stays silent. A rule that fires on every repository regardless of
   context is noise. `dockerfile-healthcheck` only fires on images that serve
   traffic; `require-adr` stays silent below 40 source files.
3. **Be satisfiable honestly.** If the only way to pass is a token gesture —
   an empty file, a `HEALTHCHECK` that always exits 0 — the rule is wrong.
4. **Explain itself.** A `rules_doc.py` entry with a real *why*, not a
   restatement of the rule name.
5. **Ship with tests**, including a case proving it does *not* fire where it
   should be inert.
6. **Pass on Deval itself.** The project self-scans at 100/100 in CI. A rule
   that Deval cannot satisfy must either be fixed or withdrawn — suppressing
   it in `.deval.yml` is not an acceptable resolution.

## Disagreements

Open an issue and make the case. If a rule fires wrongly on your repository,
that is a bug report about the rule, not a request for a suppression — the
fix belongs in the rule's inert conditions.

## Adding maintainers

A contributor with a sustained record of merged, well-tested changes may be
invited to maintain. There is no fixed threshold; the invitation comes from
the maintainer and is recorded in `MAINTAINERS.md`.
