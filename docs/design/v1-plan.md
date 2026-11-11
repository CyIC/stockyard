# Stockyard v1.0 — Implementation Plan

Companion to `docs/design/v1.md`. Every step is red → green → refactor: write the failing test, watch it
fail for the right reason, write the minimum code to pass, clean up, commit. **No production code
without a failing test first** (`CLAUDE.md`). Each phase ends with the full suite green
(`tox -e py313`) and one or more small commits on `feature/v1`.

## Phase 0 — Groundwork ✅ done

| Commit | What |
|---|---|
| `92b7890` | Merge unmerged calculation fixes + IBM yfinance fixtures from `bugfix/confusing_errors` |
| `ae67c13` | Remove club features and their dependencies (ADR-0004) |
| `f3c00cb` | Rename `warren_bot` → `stockyard` (ADR-0005) |
| this commit | Design doc, ADR-0002 … 0005, glossary, this plan |

## Phase 1 — Foundations

1. **Quiet import.** Test: importing `stockyard` writes nothing to stdout. → remove the import-time log line.
2. **Logs to stderr.** Test: after `configure_logging()`, a log record lands on stderr, not stdout.
3. **Settings.** Test: `Settings.from_env()` reads `STOCKYARD_DATA_DIR`, defaults to cwd. → `config.py`;
   `utilities.data_path` delegates to it.
4. **Architecture guard.** Test (subprocess, clean interpreter): importing `stockyard.research` and
   `stockyard.data` does not put `discord`, `matplotlib` or `prettytable` in `sys.modules`. Starts green
   on empty packages and stays green as they grow.

*Verify:* suite green; `python -c "import stockyard"` prints nothing.

## Phase 2 — Data layer

1. **`StockData`** frozen bundle + `fetch_stock_data(ticker)` composed from the existing getters
   (mocked `yf.Ticker`). Test: six datasets fetched once each.
2. **Fixture loader → `StockData`.** Test: `load_stock_data("IBM")` builds a `StockData` from
   `IBM.yfinance.json` with no network.
3. **New fixtures** via `scripts/refresh_test_fixtures.py` (needs network; run once and commit the JSON):
   a **non-December filer** (MSFT, FY ends 30 June) and a **short-history** ticker for #2.
4. **Errors.** Tests: empty earnings → `DataUnavailable`; a request exception → `UpstreamError`.
5. **Cache.** Tests: second fetch on the same day reads disk; next day refetches; `use_cache=False`
   never reads or writes; files are JSON (`orient="split"`), never pickle.

*Verify:* no section code yet; existing calculation tests still green.

## Phase 3 — Aligned Annual Fundamentals (ADR-0001, issue #5)

Implement `aligned_annual_fundamentals(data)` against the verification list in
`docs/requests/work-item-1.md`, one test at a time:

1. Reproduction: revenue ends FY2025, Q4-FY2025 EPS announced Jan/Feb 2026 → both in the same
   complete row.
2. Non-December year end (30 Sep) buckets correctly; no Dec-31 stamping.
3. 3-of-4 quarters → `current` with `quarters_reported == 3`, excluded from `complete`.
4. Fewer than 6 complete years → `sufficient_history is False`.
5. Revenue: annual figure when present, else sum of four quarters; EPS: always sum of four aligned
   quarters.

*Verify:* AC#1 and AC#2 of work item 1 covered by named tests.

## Phase 4 — Sections onto the core, one at a time

For each section, in this order (simplest first, Risk & Reward last):

`past_sales` → `past_eps` → `earnings_growth` → `cash_position` → `revenue_growth` → `record_of_stock`
→ `trend` → `risk_reward`

1. **Red:** test the new pure function `research.sections.<id>(data, fundamentals, as_of)` returns
   a frozen result with definition-derived expected values (hand-computed from fixture inputs; port the
   relevant assertions from `test_stock_analysis_calculations.py`).
2. **Green:** implement it, reading Aligned Annual Fundamentals for any year-over-year figure and
   `as_of` instead of `datetime.now()`.
3. **Refactor:** the old string-building function in `stock_analysis.py` becomes a thin renderer over
   the result (temporary), so the bot keeps working at every commit. Delete superseded tests.

Section-specific tests to add on the way:

* `past_sales`, `past_eps`: rows labelled `FY####`; Current Year excluded and reported separately.
* `record_of_stock`: price high/low windows are fiscal-year windows (design §5.2, *pending approval*).
* `revenue_growth`: behaviour of the dividend and growth-with-dividends figures per the owner's triage of
  design §16 items 1–2.
* `risk_reward`: no price target when the EPS forecast is ≤ 0 (already tested; port); zero-division
  guards.
* Every section: short history → `None` fields + a Warning, no exception (#2).

*Verify per section:* the new tests pass, the bot path still renders the section, coverage does not drop.

## Phase 5 — Report

1. `build_report(data, as_of, sections=ALL)` runs the selected sections and gathers Warnings.
2. A report-level `insufficient_history` warning when `sufficient_history` is false.
3. One section failing unexpectedly yields a section error Warning; others still produced.

## Phase 6 — Renderers

1. **JSON:** envelope fields, `schema == "stockyard.report/1"`, `NaN` → `null`, dates ISO, error envelope.
   A shape test pins `/1`.
2. **Text:** each section renders; FY labels and warnings visible.
3. **Discord:** same as text with Discord markdown; chunks never exceed 2000 characters.
4. **Charts:** given a result and a directory, writes the expected PNGs there and nowhere else.

Then delete the temporary renderers from Phase 4 and `stock_analysis.py` itself.

## Phase 7 — CLI

Tests call `stockyard.cli.main(argv)` in-process with a fake data source:

1. `report TICKER --json` → valid JSON on stdout, exit 0, nothing but JSON on stdout.
2. Each section subcommand → envelope with exactly that section.
3. Text mode default; `--charts DIR` writes PNGs.
4. Exit codes: unknown ticker 3, upstream failure 4, bad usage 2; `--json` errors use `stockyard.error/1`.
5. `--no-cache` passes through to the data layer.
6. `python -m stockyard` runs the CLI.

## Phase 8 — Bot port (Warren)

1. Token resolved in `main()`, not at import. Test: importing `stockyard.bot` needs no token.
2. `!sr TICKER` → handler calls the core via `asyncio.to_thread` and posts rendered chunks plus charts
   from a per-request temp directory (fake message/channel objects).
3. `!help` lists only real commands; `!bug` stub removed (*pending approval*, design §15.5).
4. Unknown ticker → "No data available for X"; upstream failure → friendly error.

## Phase 9 — Packaging, deployment, docs

1. `pyproject.toml`: console scripts `stockyard`, `warren`; regenerate `poetry.lock`.
2. Dockerfile `CMD ["-m", "stockyard.bot"]`; env `STOCKYARD_DATA_DIR`; compose healthcheck fixed
   (design §16.6, *pending approval*).
3. CI per the answer to design §17.1.
4. Rewrite README, `CLAUDE.md` (architecture, commands, remove `!graham_value`/`!cr`), `DOCKER.md`,
   CHANGELOG; add `docs/agents.md`: how an AI agent should call the CLI.

## Phase 10 — Release

1. Owner reviews the text output for IBM, MSFT and the short-history ticker against an independent
   source (mitigation for design decision D5).
2. `bump-my-version major` → `1.0.0`.
3. Owner re-signs: `git rebase --exec "git commit --amend --no-edit -S" main`, then merges to `main`
   and pushes to GitHub.

## Decisions needed before the phase that uses them

| Needed by | Item |
|---|---|
| Phase 4 (`record_of_stock`) | Design §15.4: fiscal-year price windows |
| Phase 4 (`revenue_growth`) | Design §16.1–16.2: dividend figure and growth-with-dividends formula |
| Phase 8 | Design §15.5: remove `!bug` |
| Phase 9 | Design §16.6 healthcheck; §17.1 CI; §17.2 `.do/` |
