# Support

## Where to go

| I want to... | Go here |
|---|---|
| Report a bug | [Open an issue](https://github.com/DARREN-2000/deval/issues/new/choose) |
| Report that a rule fired wrongly | [Open an issue](https://github.com/DARREN-2000/deval/issues/new/choose) — use the bug template |
| Propose a new rule | [Rule proposal template](https://github.com/DARREN-2000/deval/issues/new/choose) |
| Report a security vulnerability | **Not here.** See [SECURITY.md](SECURITY.md) |
| Ask a question | [Discussions](https://github.com/DARREN-2000/deval/discussions) |

## What to expect

Deval is maintained by one person alongside full-time work. Best-effort
response within a week. There is no SLA, and none is implied.

## Before you open an issue

Most reports are about a rule firing where it should not have. Two things make
those reports quick to act on:

1. **Run `deval explain <rule>`.** Every rule documents what it looks for, why,
   and when it stays inert. This often answers the question outright.
2. **Include the scan output and the relevant part of your repo layout.**
   Deval is deterministic — given the same tree it produces the same finding —
   so a description of the layout is usually enough to reproduce it.

If a rule is wrong for your repository, that is a bug in the rule's inert
conditions and worth reporting. Suppressing it in `.deval.yml` will unblock
you today, but please still file the issue.

## Self-service

- `deval rules` — list all 102 rules
- `deval explain <rule>` — problem, why, example, fix, references
- `deval scan . --explain` — scan with inline explanations
- [Browser demo](https://darren-2000.github.io/deval/) — scan a zip without installing anything
