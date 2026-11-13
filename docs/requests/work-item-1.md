# Fix: revenue and EPS in the stock report can reference different fiscal years

> Sharpened request for GitLab work item #1 (`cyic/stockyard`, formerly `cyic/warren_bot`). See `docs/adr/0001-align-annual-fundamentals-on-period-end.md` and `CONTEXT.md`.

> **Superseded in part (2026-11-11):** the algorithm, threshold and location below were amended for v1. See ADR-0001's amendment and `docs/design/v1.md` §5.2. Kept for history.

## Summary

The `!stock_report` output compares **revenue** (from `stock.financials`, real fiscal period-end
dates) against **Reported EPS** (from `get_earnings_dates()`, announcement dates shifted −2 months
and stamped to `YYYY-12-31`). Each report section slices these frames independently with
`[-1]`/`iloc[-years:]`, so "most recent year" sales can be FY2025 while EPS is FY2026. Tables print
no year labels, so the drift is invisible.

## Root cause

No single definition of "fiscal year." Two data paths use two date heuristics, and five report
sections re-derive year membership independently.

## Decision (see ADR-0001)

- **Income-statement period-end date is the single source of truth** for fiscal-year membership.
- Add **`get_aligned_annual_fundamentals(ticker)`** in `yfinance_integration.py` returning:
  - `complete` — DataFrame keyed by period-end, one row per **Complete Fiscal Year** (4 quarters
    present, both revenue + EPS), columns `fiscal_year`, `revenue`, `reported_eps`. Revenue = annual
    figure if present else sum of 4 quarters; `reported_eps` = sum of the 4 aligned quarters.
  - `current` — the in-progress fiscal year (< 4 quarters), or `None`.
  - `complete_year_count` + `sufficient_history` (false when `< YRS_LOOKBACK + 1` = 6).
- EPS is **re-keyed to period-ends** by matching each announcement to the immediately preceding
  quarter-end (via `quarterly_financials`) — drops the −2-month heuristic and Dec-31 stamp, so
  **non-December fiscal years work** with no special-casing.
- Raw per-statement getters stay untouched.

## Scope

- **Refactor onto the builder:** `past_sales_records`, `past_eps`, `record_of_stock` (annual EPS +
  present-year), `revenue_growth` (annual revenue), annual-EPS use in the prediction fn (`:766`).
- **Leave on raw quarterly frames:** `trend` plot, quarterly polynomial forecasts.
- **Presentation:** every comparable row labeled with its actual `FY####`; the Current Year rendered
  as a distinct per-section line (`"Current FY2026 (2 of 4 quarters) … excluded from comparison"`);
  non-blocking warning line when `sufficient_history` is false.

## Acceptance criteria

- [ ] AC#1 — In a generated report, revenue and EPS rows of the comparable history refer to
  identical fiscal years (proven by reproduction + presentation tests; FY labels visible).
- [ ] AC#2 — A fiscal year with < 4 reported quarters never appears in the comparable history; it is
  shown separately as the labeled Current Year.

## Verification (mocked `yf.Ticker`, no network)

- Reproduction: revenue ends FY2025, Q4-FY2025 EPS announced Jan/Feb 2026 → `complete` rows share
  fiscal year; in-progress year in `current`.
- Non-December FYE (Sept-30) bucketing; no Dec-31 stamp.
- 3-of-4-quarters year → `current`, `quarters_reported = 3`, excluded from `complete`.
- `< 6` complete years → `sufficient_history is False`.
- Presentation: `past_sales_records` / `past_eps` contain `FY####` labels + current-year line; the
  comparable table excludes the in-progress year.

## Out of scope

- Semiannual filers (hard 4-quarter rule accepted; revisit later).
- `!graham_value` — no such code exists in the repo today.
