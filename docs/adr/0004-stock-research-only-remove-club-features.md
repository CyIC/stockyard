---
status: accepted
---

# v1 is stock research only; club portfolio features are removed

## Context

The club report (`!club_report`/`!cr`, `portfolio_analysis.py`) was non-functional: it read
`./cyic_stocks.csv`, which the bot never ships, and never posted its result to Discord. It also wrote
SEC-enriched data back into `club_info.json` as a side effect of a read, which is unacceptable once AI
agents invoke the code. It carried four dependencies (`scipy`, `jinja2`, `mplfinance`, `xhtml2pdf`)
and, through `xhtml2pdf`, 25 locked packages including `pypdf` and `cryptography`.

## Decision

Delete the club features entirely from v1: modules, helpers, templates, command, deployment mounts and
dependencies (commit `ae67c13`). The 0.1 implementation remains reachable at the local tag `pre-v1`.
If club features return, they are redesigned on the v1 core with reads and writes separated.

## Considered options

- **Move to an unimported `legacy/` folder** — dead code keeps its dependencies and alerts and confuses
  readers; rejected.
- **Long-lived `club-features` branch** — easy to forget; a tag is permanent; rejected.

## Consequences

- `!club_report`/`!cr` no longer exist (breaking).
- Smaller dependency and vulnerability surface.
