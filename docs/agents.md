# Using stockyard from an agent or script

`stockyard` is built to be called by AI agents and scripts: one process per lookup, a versioned JSON document
on stdout, stable exit codes, and nothing else on stdout. This page is the contract; the design background is
in [ADR-0003](adr/0003-cli-output-contract.md) and [design §8](design/v1.md).

## Calling it

```sh
stockyard report MSFT --json            # every section
stockyard risk-reward MSFT --json       # one section (same envelope, one key in "sections")
```

* Read **stdout** for the result and the **exit code** for success. Logs go to stderr; ignore or capture them
  separately. Never parse stderr for data.
* Tickers are case-insensitive and validated (`[A-Z0-9^][A-Z0-9.\-^=]{0,14}` after upper-casing), e.g. `MSFT`,
  `BRK-B`, `^GSPC`.
* Data is cached for the New York calendar day in `$STOCKYARD_DATA_DIR/cache/`, so repeated calls for one
  ticker on one day are fast and consistent. `--no-cache` forces a fresh fetch.
* `--charts DIR` also writes PNGs (trend and risk/reward). Charts never appear in the JSON.

| Command | `sections` key |
|---|---|
| `report` | all nine, in the order below |
| `fundamentals` | `fundamentals` |
| `past-sales` | `past_sales` |
| `past-eps` | `past_eps` |
| `record` | `record_of_stock` |
| `trend` | `trend` |
| `cash` | `cash_position` |
| `revenue-growth` | `revenue_growth` |
| `earnings-growth` | `earnings_growth` |
| `risk-reward` | `risk_reward` |

## Exit codes

| Exit | Meaning | stdout with `--json` |
|---|---|---|
| 0 | success; check `warnings` | `stockyard.report/1` |
| 1 | internal error (a bug) | `stockyard.error/1`, code `internal_error` |
| 2 | usage error or invalid ticker | empty; plain-text message on stderr |
| 3 | no data for the ticker (e.g. delisted or misspelled) | `stockyard.error/1`, code `data_unavailable` |
| 4 | Yahoo Finance failed (network, rate limit) — worth one retry later | `stockyard.error/1`, code `upstream_error` |

```json
{"schema": "stockyard.error/1", "code": "data_unavailable", "message": "..."}
```

## The report document

```json
{
  "schema": "stockyard.report/1",
  "ticker": "IBM",
  "as_of": "2026-11-11",
  "source": "yfinance",
  "history": {"complete_fiscal_years": 5, "quarters_reported": 3, "price_history_start": "2021-01-04", "sufficient_history": true},
  "warnings": [{"code": "range_inverted", "message": "linear_regression 457.52 is not below the forecast high",
                "section": "risk_reward", "figure": "linear_regression", "needed": null, "available": null}],
  "sections": {"past_eps": {"...": "..."}, "risk_reward": {"...": "..."}}
}
```

Conventions:

* **Percentages are fractions:** `0.0379` means 3.79 %. Multiples (P/E, up/down ratio, `lynch_ratio`) are plain
  numbers. Money is in the company's reporting currency (no `currency` field in v1).
* **`null` means "not available"**, never zero; there is always a warning explaining it. NaN and infinities
  never appear.
* Dates are ISO-8601. Fiscal years are `"FY2025"`, with `period_end` where a row needs the exact date.
* `as_of` is the New York date the figures are computed for; the same data and date give the same document.
* A section that crashed is `null` with a `section_failed` warning; the other sections are unaffected.
* `history.sufficient_history` is false when there are fewer than 4 complete fiscal years (recent IPOs). EPS
  growth figures that need more years and the risk/reward forecast are then `null`.

### Sections

| Section | Fields |
|---|---|
| `fundamentals` | `years[]` (`fiscal_year`, `period_end`, `revenue`, `net_income`, `reported_eps`); `current` (`fiscal_year`, `quarters_reported`, `eps_to_date`, `awaiting_annual_statement`); `history` (`complete_fiscal_years`, `quarters_reported`, `price_history_start`, `sufficient_history`) |
| `past_sales` | `years[]` (`fiscal_year`, `revenue`); `recent_pair_average`; `oldest_pair_average`; `pair_increase`; `cagr` |
| `past_eps` | `years[]` (`fiscal_year`, `reported_eps`); `recent_pair_average`; `oldest_pair_average`; `pair_increase`; `cagr` |
| `record_of_stock` | `rows[]` (`fiscal_year`, `period_end`, `eps`, `high`, `low`, `dividends_per_share`, `pe_high`, `pe_low`, `payout`, `high_yield`); `average_high`; `average_low`; `average_pe_high`; `average_pe_low`; `average_pe`; `average_payout`; `present_price`; `ttm_eps`; `current_pe`; `oldest_fiscal_year`; `change_from_oldest_high` |
| `trend` | `quarterly_revenue[]` (`quarter_end`, `revenue`); `quarterly_eps[]` (`announced`, `reported_eps`); `monthly_prices[]` (`month`, `high`, `low`, `average_high_4m`, `average_low_4m`) |
| `cash_position` | `latest_label`; `prior_label`; `quarter_label`; `rows[]` (`metric`, `group`, `latest`, `prior`, `difference`, `pct_difference`, `quarter`) |
| `revenue_growth` | `years[]` (`fiscal_year`, `revenue`, `change`, `pct_change`); `average_growth`; `ttm_dividends_per_share`; `dividend_yield`; `present_price`; `ttm_eps`; `current_pe`; `eps_cagr`; `lynch_ratio` |
| `earnings_growth` | `years[]` (`fiscal_year`, `net_income`, `change`, `pct_change`) |
| `risk_reward` | `present_price`; `average_pe_high`; `projected_eps`; `forecast_high`; `price_target_appreciation`; `lows[]` (`name`, `value`, `zones`, `position`, `up_down_ratio`); `eps_points[]` (`announced`, `ttm_eps`); `eps_forecast_line[]` (`date`, `value`); `monthly_lows[]` (`month`, `low`); `low_forecast_line[]` (`date`, `value`) |

Notes on the less obvious fields:

* `risk_reward.lows[].name` is `linear_regression`, `average_low`, `severe_low` or `dividend_support`. Each low
  has its own `zones` (`{"buy": [from, to], "maybe": [...], "sell": [...]}`, 25/50/25 % of the range),
  `position` of the present price (`buy`, `maybe`, `sell`, `below_range`, `above_range`) and `up_down_ratio`.
  Zones are `null` when that low is not below the forecast high (`range_inverted`).
* `cash_position.rows[].metric` names the line item (`cash`, `short_term_investments`, `total_cash`,
  `long_term_debt`, `net_cash`, `working_capital`, …); `latest` and `prior` are the two latest fiscal years
  (`latest_label`, `prior_label`) and `quarter` the latest quarter (`quarter_label`).
* `revenue_growth.lynch_ratio` is Peter Lynch's dividend-adjusted PEG, `(EPS growth % + dividend yield %) / P/E`
  with whole-number percentages: below 1 poor, 1.5 okay, 2 or more what Lynch looked for.
* `record_of_stock.rows` covers only fiscal years whose price window is fully covered by the price history.
* `trend` and the `*_line` / `*_points` / `monthly_lows` series in `risk_reward` are the data behind the charts.

Definitions of every figure are in the README's [Calculation Notes](../README.md#calculation-notes) and
[design §5.7](design/v1.md).

### Warnings

Each warning has `code`, `message` (human-readable), `section` (`null` for report-wide warnings) and, where
relevant, `figure`, `needed` and `available`.

| Code | Meaning |
|---|---|
| `figure_unavailable` | a figure is `null`: not enough history (`needed` vs `available`) or a missing input |
| `insufficient_history` | fewer than 4 complete fiscal years; report-wide |
| `awaiting_annual_statement` | all four quarters of the current year are reported but the annual statement isn't published yet |
| `non_positive_eps` | a year with EPS ≤ 0 was left out of an average, or a growth rate is undefined |
| `assumed_zero` | a balance-sheet item Yahoo omitted was counted as zero in a total |
| `range_inverted` | a low estimate is not below the forecast high, so it has no zones |
| `price_above_range` | the present price is above the forecast high, so there is no up/down ratio |
| `eps_duplicate` | two EPS announcements matched one quarter; the earlier was used |
| `eps_unattributed` | an EPS announcement could not be matched to a quarter and was dropped |
| `section_failed` | the section raised an error and is `null` |

## Compatibility

`stockyard.report/1` only grows: new fields and new warning codes can appear without notice, so ignore what you
don't recognise. Renaming, removing or changing the meaning of a field bumps the schema to `/2`. Check `schema`
before reading.
