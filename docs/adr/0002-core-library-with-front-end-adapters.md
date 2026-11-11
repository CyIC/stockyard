---
status: accepted
---

# A pure core library with front-end adapters

## Context

Every Stock Selection Guide section in `stock_analysis.py` both computed its numbers and formatted them
as a Discord message, and `run()` took a `discord.Message` and posted to its channel. A second consumer
(a CLI used mostly by AI agents) could not reuse any of it. Agents need numbers, not markdown: parsing
rendered tables costs the tokens the CLI exists to save. An MCP server is planned as a third consumer.

## Decision

Split the package into layers with a one-way dependency rule:

- **core** — `stockyard.data` (fetch once into an immutable `StockData`, cache, ADR-0001 alignment) and
  `stockyard.research` (one pure function per section returning a frozen dataclass result, plus
  `build_report`). No Discord, printing, chart drawing, hidden file writes, or `datetime.now()`;
  callers pass `as_of`.
- **renderers** — `stockyard.render` turns results into Discord markdown, terminal text, JSON or chart PNGs.
- **front ends** — `stockyard.bot` (Warren) and `stockyard.cli`, later `stockyard.mcp`, which only parse
  input, call the core, pick a renderer and map errors.

A test asserts the core never imports `discord`, `matplotlib`, or `prettytable`.

## Considered options

- **Wrap existing strings in JSON** — fast, but agents would parse markdown tables; rejected.
- **Structured data only for agent-relevant sections** — leaves two styles in the codebase and
  defers the same refactor to v2; rejected.
- **Separate repositories per front end** — needless versioning overhead for one maintainer; rejected
  in favour of one package with console scripts per front end.

## Consequences

- `stock_analysis.py` is rewritten section by section; result field names become a public contract
  through the JSON schema (ADR-0003).
- The MCP server (v1.1) adds an adapter only.
- Calculations become deterministic and testable without the network or a clock.
