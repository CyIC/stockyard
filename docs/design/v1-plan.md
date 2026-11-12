# Stockyard v1.0 — Implementation Plan

Revision 3 (signed off with changes by independent review, 2026-11-11; changes applied). Companion to `docs/design/v1.md`.

Every step is red → green → refactor: write the failing test, watch it fail for the right reason, write
the minimum code to pass, clean up, commit. **No production code without a failing test first**
(`CLAUDE.md`). Each phase ends with the suite green and small commits on `feature/v1`. **The deployed
bot must work at every commit.**

## Phase 0 — Groundwork ✅

`92b7890` calculation fixes merged · `ae67c13` club features removed · `f3c00cb` renamed to stockyard ·
`e0896a9` design docs.

## Phase 1 — Foundations ✅

`6a881ed` silent import, `configure_logging()` to stderr, `LOGGING_LEVEL` · `0e6c211` orphans ·
`223915c` `Settings`, `STOCKYARD_DATA_DIR` · `5ed7fc5` architecture guard.
Follow-up in this revision: the guard walks every submodule (review finding 14).

## Phase 2 — Data layer

1. **Tickers.** `validate_ticker`: accepts `msft`, `BRK.B`, `^GSPC`; rejects `../x`, empty, 16+ chars,
   spaces → `InvalidTicker`.
2. **Fixture loader without date shifting.** Remove `_shift_years`. New code is tested with `as_of`
   pinned to the snapshot date. The legacy `stock_analysis` functions still read `datetime.now()` (10
   places) and take no `as_of`, so their tests freeze the clock at the snapshot date (a fixture patching
   `stock_analysis.datetime`) until each function is replaced in Phase 4.
3. **`StockData`** frozen bundle + `fetch_stock_data` (mocked `yf.Ticker`): each dataset fetched once;
   earnings fetched with `limit = 4 × annual periods + 12` (≥ 28); daily prices with dividends start at
   the oldest annual period's start; no `_earnings_from_basic` fallback.
4. **`load_stock_data(name)`** builds `StockData` from recorded fixtures.
5. **Record fixtures** with `scripts/refresh_test_fixtures.py` (network, run once): MSFT (FY ends 30 June)
   and a recent IPO.
6. **Errors.** Empty everything → `DataUnavailable`; raised request error → `UpstreamError`.
7. **Cache.** Same New-York-day hit; next day miss; `use_cache=False` neither reads nor writes; JSON not
   pickle; atomic write; empty or failed fetches not cached; cache path built only from a validated
   ticker.

## Phase 3 — Aligned Annual Fundamentals (design §5.2)

One rule per test, synthetic frames first, then fixtures:

1. Fiscal years = annual period-ends ≤ `as_of`.
2. Derived quarter-ends (Dec, Sep-30, Jun-30; 52/53-week end such as 2025-09-27).
3. Attribution: latest derived quarter-end strictly before announcement, ≤ 120 days; later rows after
   `as_of` ignored; duplicates keep earliest + `eps_duplicate`; orphans dropped + `eps_unattributed`.
4. Fiscal-year rows keep revenue and net income when EPS is incomplete (pre-IPO years); Complete vs
   Current Year (`quarters_reported` 0–4; 4 of 4 without an annual row → `awaiting_annual_statement`,
   excluded from comparisons).
5. `sufficient_history` true at 4 complete years, false at 3 (D17).
6. Balance sheet and cash flow: annual rows only at real period-ends; latest quarter separate.
7. Fiscal-year price windows `(Pᵢ₋₁, Pᵢ]` from daily bars; partially covered (pre-IPO) years → `null`.
8. `history` block.

## Phase 4 — Definitions, then sections ✅

`a4d999e` definitions · `98f3e3d` shared price stats · `4408649` New York clock · sections:
`7bd4da0` past sales · `732c997` past EPS · `fe22cd5` earnings growth · `37abb8d` cash position (D18) ·
`742c461` revenue growth + Lynch (D15) · `7c485a2` record of stock · `2c510a7` trend + thread-safe charts
(phase 6.3 pulled forward) · `00ba1e6`/`7d304b1` risk & reward, `!sr` fully on the new core ·
`9daa901` D19 · fundamentals. Remaining legacy modules (`yfinance_integration.py`, the IBM legacy
fixture and its loader, `prettytable`) are removed in phase 6.

### Original plan

**4.0 Switch the pipeline first.** `stock_analysis.run()` obtains `StockData` via `fetch_stock_data` and
passes `as_of = today`; existing behaviour otherwise unchanged. (Keeps the bot working as sections move.)

**4.1 Definitions** (`research/definitions.py`), each with hand-computed tests including its `null`
rules (design §5.7): `cagr`, `pair_increase`, `ttm_eps`, `pe`, `payout`, `high_yield`, `up_down_ratio`,
`zones` (25/50/25; top of Buy = 3:1), `dividend_yield`, and **`lynch_ratio`** (12 % growth, 2 % yield,
PE 20 → 0.7; a test that fails if fractions are passed where whole-number percentages belong; docstring
cites Lynch, *One Up on Wall Street*, 1989).

**4.2 Shared helpers:** `fiscal_year_price_stats` (high, low, EPS, PE high/low excluding EPS ≤ 0,
dividends per share from the price history, payout, high yield) per Complete Fiscal Year, and
`ttm_dividends_per_share`. All dividend figures come from this one source (design §5.7).

**4.3 Sections**, one at a time: `fundamentals` → `past_sales` → `past_eps` → `earnings_growth` →
`cash_position` → `revenue_growth` → `record_of_stock` → `trend` → `risk_reward`. For each:

1. Red: `research.sections.<id>(data, fundamentals, as_of)` returns its frozen result with
   definition-derived values, plus its short-history `null` + warning cases (design §5.6).
2. Green: implement on Aligned Fundamentals and the definitions.
3. Write its **final** text renderer in `render/text.py` (tested), and point the bot's `run()` at
   section + renderer. Delete the old function and its superseded tests.

Section-specific: `revenue_growth` reports dividends per share, yield and `lynch_ratio` (labelled
"Lynch dividend-adjusted ratio" in text); `risk_reward` uses average of FY lows, 25/50/25 zones, the
corrected "Forecast high (avg PE × projected EPS)" label, `null` up/down when price ≤ low or ≥ forecast
high, `range_inverted` when a low ≥ forecast high, and price position `below_range`/`above_range`.

## Phase 5 — Report

`build_report` gathers sections and warnings; `history` block; a raising section becomes `null` +
`section_failed` without affecting others.

## Phase 6 — Renderers

1. **JSON:** envelope, `null` for missing/NaN/±∞, error envelope; **key-set snapshot per section**.
2. **Discord:** wraps text renderers; chunks ≤ 2000 characters.
3. **Charts:** OO `Figure` API, every figure closed, output only in the given directory; a test renders
   from several threads concurrently and asserts correct files and zero open figures.

## Phase 7 — Bot port (Warren) — before the CLI

1. `stockyard.bot` package; token resolved in `main()`; importing needs no token.
2. `!sr` runs report generation in `asyncio.to_thread`, posts rendered chunks and charts from a
   per-request temp directory; `!help` lists real commands; `!bug` removed; invalid ticker and no-data
   messages.
3. Console script `warren`; Docker `CMD ["-m", "stockyard.bot"]`; compose files updated. Bot verified
   running from the new entry point before Phase 8.

## Phase 8 — CLI

Tests call `stockyard.cli.main(argv)` with a fake data source:

1. `report TICKER --json`: valid JSON only on stdout, exit 0.
2. Each command maps to its section id (design §8.1 table); envelope contains exactly that section.
3. Text default; `--charts DIR` writes PNGs.
4. Exit codes: invalid ticker / usage 2 (plain text on stderr), data unavailable 3, upstream 4,
   internal 1; `--json` errors use `stockyard.error/1` for 1, 3, 4.
5. `--no-cache` reaches the data layer.
6. Finally `python -m stockyard` runs the CLI (the bot already moved in Phase 7).

## Phase 9 — Packaging, deployment, docs

1. Console scripts `stockyard`, `warren`; lock regenerated.
2. Compose healthcheck fixed; CI per design §17.1; `.do/` per §17.2.
3. README (including **calculation notes: every §5.7 definition, with Lynch's ratio attributed**),
   `CLAUDE.md` (architecture, commands; drop `!graham_value`/`!cr`), `DOCKER.md`, CHANGELOG, and
   `docs/agents.md` (how an agent calls the CLI and reads the JSON).
4. Optional, one commit: `black` over the whole tree (pre-existing formatting drift).

## Phase 10 — Release

1. Owner reviews text output for IBM, MSFT and the recent IPO against an independent source (D5).
2. `bump-my-version major` → `1.0.0`.
3. Owner re-signs (`git rebase --exec "git commit --amend --no-edit -S" main`), merges, pushes.

## Decisions outstanding

| Needed by | Item |
|---|---|
| Phase 9 | design §17.1 CI platform; §17.2 `.do/` |
