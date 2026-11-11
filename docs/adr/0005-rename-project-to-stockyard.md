---
status: accepted
---

# Rename the project to stockyard; Warren remains the persona

## Context

The package `warren_bot` was named after the Discord bot. From v1 it is a stock research library with
several front ends, and the name misdescribes it. Warren (after Warren Buffett) is the persona members
talk to, not the codebase.

## Decision

- Project, distribution, import package and CLI command: **`stockyard`**. The name nods to Omaha's Union
  Stockyards and works as an umbrella for future CyIC tooling (`stockyard.club`, `stockyard.mcp`).
- **Warren** remains the Discord bot (console script `warren`) and the future agent persona; Docker
  service and image names for the bot deployment keep `warren-bot`.
- The GitHub repository is renamed `CyIC/warren_bot` → `CyIC/stockyard`.

## Considered options

- **Keep `warren_bot`** — zero churn, misleading name; rejected.
- **`warren`** — taken on PyPI; conflates persona and library; rejected.
- **`cyic`, `ssg-engine`, `mrmarket`, `taxodium`** — considered; `stockyard` preferred.

## Consequences

- Breaking import path change, done as one mechanical commit (`f3c00cb`) before redesign work.
