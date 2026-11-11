---
status: accepted
---

# CLI output contract: text by default, versioned JSON on request

## Context

The CLI has two audiences: a human doing quick lookups in a terminal, and (primarily) an AI agent
invoking it as a tool. The agent needs machine-readable output whose shape does not silently change.

## Decision

- Text output by default; `--json` selects JSON. No TTY auto-detection.
- Every JSON document is an envelope with a `schema` field: `stockyard.report/1` for results,
  `stockyard.error/1` for failures. Adding fields is non-breaking; removing, renaming or changing the
  meaning of a field bumps the version.
- stdout carries only the result; all logging goes to stderr.
- Missing values are `null`; ratios are fractions; dates are ISO-8601.
- Exit codes: 0 success, 1 internal error, 2 usage, 3 data unavailable, 4 upstream/network failure.
- Built on stdlib `argparse` (no new dependency).

## Considered options

- **Auto-detect (JSON when stdout is not a TTY)** — zero flags for agents, but `stockyard report X | less`
  would surprise a human and identical commands would behave differently by environment; rejected.
- **JSON always, `--pretty` for humans** — optimises for the agent at the expense of the human
  lookups the CLI also serves; rejected.
- **Click / Typer** — nicer ergonomics, unnecessary for a small command surface; rejected.

## Consequences

- Agent instructions are simply "always pass `--json`".
- A schema-shape test guards the `/1` contract; the v1.1 MCP server reuses the same payloads.
