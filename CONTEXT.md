# Context & Glossary — Stockyard

The ubiquitous language for the stock-analysis domain. Glossary only — no implementation
details. Terms are canonical; when code or conversation drifts from these, the term wins
until deliberately changed.

## Glossary

### Fiscal Year (FY)
A company's annual reporting period, identified by the **period-end date of its annual income
statement** (yfinance `stock.financials`). This is the *single source of truth* for "which year"
a data point belongs to. All other series (EPS, balance sheet, cash flow) are aligned to a
Fiscal Year by joining on it — they do not derive their own year independently.

Not every company's Fiscal Year ends in December; the period-end date carries the real boundary.

### Reported EPS
Earnings-per-share as announced by the company, retrieved from yfinance earnings announcements
(`get_earnings_dates`). Distinct from **Derived EPS** (Net Income ÷ shares outstanding). An annual
Reported EPS is the sum of its four quarterly Reported EPS values. Reported EPS is *aligned to* a
Fiscal Year, not the definer of one.

### Complete Fiscal Year
A Fiscal Year whose four quarterly Reported EPS figures are all present (attributed to derived
quarter-ends, see ADR-0001 amendment). EPS-based comparisons use only Complete Fiscal Years; revenue and
net-income comparisons use every Fiscal Year that has an annual statement, including pre-IPO years.
(The 4-quarter rule is a deliberate simplification; semiannual filers are out of scope for now.)

### Current Year (in-progress)
The Fiscal Year after the last annual statement: fewer than four reported quarters, or four reported
but its annual statement not yet published ("awaiting annual statement"). Its data is **incomplete** and must
be presented separately from the comparable full-year history (e.g. "Current FY 2026 — 2 of 4
quarters reported"), never placed in the "most recent year" slot as if it were a settled figure.

### Aligned Annual Fundamentals
The company's fiscal-year history keyed on the income-statement period-end: one row per Fiscal Year with
revenue and net income, plus Reported EPS when the year is complete, and the Current Year kept apart.
Every year-over-year comparison reads from it; sections must not re-derive year membership from any
other source. See ADR-0001 and its amendment.

### Stockyard / Warren
**Stockyard** is the project and its library: the research engine and its front ends. **Warren** is the
persona members interact with: the Discord bot today, and the AI agent later. Code is named for
Stockyard; user-facing chat is Warren.

### Stock Selection Guide (SSG)
The BetterInvesting (NAIC) worksheet the stock report follows. Its parts are **Sections**: Fundamentals, Past Sales,
Past EPS, Record of Stock, Trend, Cash Position, Revenue Growth, Earnings Growth, Risk & Reward.

Section ids: `fundamentals`, `past_sales`, `past_eps`, `record_of_stock`, `trend`, `cash_position`,
`revenue_growth`, `earnings_growth`, `risk_reward`.

### Zones
The division of the range between a Risk & Reward forecast low and forecast high: **Buy** is the lowest
25 %, **Maybe** the middle 50 %, **Sell** the top 25 % (current BetterInvesting convention). The top of
the Buy zone is exactly a 3-to-1 Up/Down Ratio.

### Up/Down Ratio
Potential gain versus risk of loss: `(forecast high − present price) / (present price − forecast low)`.

### Lynch Ratio (dividend-adjusted PEG)
Peter Lynch's measure from *One Up on Wall Street* (1989): `(EPS growth % + dividend yield %) / P/E`,
with both percentages as whole numbers. Below 1 is poor, 1.5 okay, 2 or more what you're looking for. Stockyard
uses the EPS CAGR as the growth rate and reports it in the Revenue Growth section as `lynch_ratio`.

### History Block
The part of every Report that states how much data the analysis stood on: Complete Fiscal Years,
quarters reported in the Current Year, first price date, and whether history is sufficient.

### Section Result
The structured outcome of one Section for one ticker as of one date: numbers and series, never
formatted text. Missing values are explicit (null) and explained by a Warning.

### Report
The collection of Section Results for a ticker, plus report-level Warnings, the as-of date and the
data source.

### As-of Date
The date a Report is computed for. Every look-back window, "present price" and forecast horizon is
measured from it. Calculations never read the system clock.

### Warning
A structured, non-fatal notice attached to a Report or Section, e.g. `insufficient_history` when fewer
Complete Fiscal Years exist than the SSG look-back needs.

### Front End
A way of delivering Reports to someone: the Discord bot, the CLI, and later the MCP server. Front ends
parse input, call the core and render; they never compute.

### Renderer
Turns Section Results into one presentation: Discord markdown, terminal text, JSON, or chart images.
