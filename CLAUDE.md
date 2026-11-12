# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:

- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:

- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:

- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:

- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:

```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and
clarifying questions come before implementation rather than after mistakes.

## Test-Driven Development

This project works exclusively in strict test-driven development. You do not write production code without a failing
test proving it's needed first. This is not a style preference — it's the Iron Law you operate under.

## The Iron Law

```
NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST
```

If you catch yourself about to write implementation code before its test exists, stop. Write the test first. If you ever
do write code before its test (e.g. while exploring), delete it — don't keep it "as reference" and don't adapt it while
writing the test afterward. Implement fresh from the test.

**Exceptions** (throwaway prototypes, generated code, config files): ask the user explicitly before skipping TDD for
these. Never decide on your own that "this case is different."

## Project Overview

Stockyard is the Cypress Investment Club's stock research library. It produces the BetterInvesting Stock Selection
Guide (SSG) analysis for a ticker as structured results, and delivers them through front ends: **Warren**, the
Discord bot, and (v1.0, in progress) the `stockyard` CLI for humans and AI agents; an MCP server follows in v1.1.
Warren is the persona; the code is named for Stockyard (ADR-0005).

Read before changing behaviour: `docs/design/v1.md` (design and decision log), `docs/design/v1-plan.md` (phased
plan), `docs/adr/` (decisions), `CONTEXT.md` (glossary; its terms win).

## Architecture

### Core Structure

- **src/stockyard/data/** - `snapshot.py` (fetch everything once into `StockData`), `cache.py` (same-day cache,
  record on miss / replay on hit), `fundamentals.py` (fiscal-year alignment, ADR-0001), `tickers.py` (validation,
  the trust boundary), `errors.py`, `yfinance_source.py` (yfinance labels -> stockyard column names)
- **src/stockyard/research/** - `definitions.py` (SSG formulas, design §5.7), `price_stats.py` (shared per-year
  price figures), `sections.py` (one pure function per section), `report.py` (`build_report`), `models.py`
- **src/stockyard/render/** - `text.py`, `discord.py` (2000-character messages), `json.py`
  (`stockyard.report/1`), `charts.py` (matplotlib OO `Figure` API only, thread-safe)
- **src/stockyard/bot/** - Warren: command parsing, `!sr` built off the event loop
- `clock.py` (the only wall-clock read), `config.py`, `logging_config.py` (stderr), `report_warning.py`,
  `utilities.py`

### Rules

- Dependencies point down only: `data` and `research` never import `discord`, `matplotlib` or `prettytable`
  (`src/tests/test_architecture.py` enforces it).
- Sections are pure `section(data, fundamentals, as_of)`; they never read the clock or another section's result.
- Missing figures are `None` with a `ReportWarning`, never a crash or a fake number.
- Tests never touch the network: use `tests/builders.py` for small exact data and `tests/fixture_replay.py`
  (recorded IBM, MSFT, RDDT in `src/tests/fixtures/`) with `as_of` pinned to the capture date.

## Development Commands

```bash
poetry install                                        # dependencies
tox                                                   # tests, lint and type checks
poetry run pytest src/tests/ --cov=src/stockyard      # tests with coverage
poetry run black src/
poetry run flake8 src/stockyard
poetry run pylint src/stockyard
poetry run python scripts/record_raw_fixtures.py IBM  # re-record fixtures (needs Yahoo Finance access)
poetry run warren                                     # run the Discord bot (or: python -m stockyard.bot)
bump-my-version patch|minor|major                     # version management
```

## Bot Commands

- `!stock_report <ticker>` or `!sr <ticker>` - Stock Selection Guide report with charts
- `!help` - available commands

## Configuration

Environment variables (`STOCKYARD_DATA_DIR`, `LOGGING_LEVEL`, `DISCORD_TOKEN` / `DISCORD_TOKEN_FILE`) are
documented in the README and `.env.template`. Market data comes from Yahoo Finance via yfinance (no API key).

## Code Style Guidelines

- **Line Length**: 120 characters (Black), 120 for flake8
- **Python Version**: 3.13+
- **Linting**: flake8 with docstring requirements, pylint for additional checks
- **Testing**: pytest with coverage reporting
- **Type Hints**: Not consistently used but encouraged for new code

## Key Dependencies

- **yfinance**: market data from Yahoo Finance
- **pandas/numpy**: data processing
- **matplotlib**: charts (object-oriented `Figure` API, never `pyplot`)
- **discord.py**: the Warren bot
- **python-json-logger**, **tzdata**
