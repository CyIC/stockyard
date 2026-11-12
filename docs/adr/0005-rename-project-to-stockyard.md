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

## Amendment (2026-11-12)

At the owner's request, once the GitHub and GitLab repositories were renamed `stockyard`, the remaining
`warren-bot` names were retired: the Docker image is `stockyard`, the Compose service and container that run
the bot are `warren` (matching the `warren` console script), and networks, build scripts and DigitalOcean app
names use `stockyard`. References to "Warren Bot 0.1" as the name of the previous release are kept.
