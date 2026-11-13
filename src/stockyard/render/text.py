# -*- coding: utf-8 -*-
"""Plain-text rendering of section results, shared by the CLI and (wrapped) Discord (design §6)."""
from dataclasses import dataclass

from stockyard.data.fundamentals import YRS_LOOKBACK
from stockyard.research.models import (
    CashPositionResult,
    EarningsGrowthResult,
    FundamentalsResult,
    PastEpsResult,
    PastSalesResult,
    RecordOfStockResult,
    RevenueGrowthResult,
    RiskRewardResult,
    TrendResult,
)

NA = "n/a"


@dataclass(frozen=True)
class RenderedSection:
    """A section ready to print: a title and a plain-text body."""

    title: str
    body: str


def _money(value: float | None) -> str:
    if value is None:
        return NA
    return f"-${-value:,.0f}" if value < 0 else f"${value:,.0f}"


def _pct(value: float | None) -> str:
    return NA if value is None else f"{value:.2%}"


def _rows(rows) -> list[str]:
    width = max(len(label) for label, _ in rows)
    return [f"{label:<{width}}  {value:>20}" for label, value in rows]


def _warnings(warnings) -> list[str]:
    return [f"⚠ {warning.message}" for warning in warnings]


def _per_share(value: float | None) -> str:
    if value is None:
        return NA
    return f"-${-value:,.2f}" if value < 0 else f"${value:,.2f}"


def _growth(title: str, result, value_format, increase_label: str) -> RenderedSection:
    """A per-fiscal-year series followed by its growth figures and the years they span."""
    labels = [fiscal_year for fiscal_year, _ in result.years]
    lines = _rows([(fiscal_year, value_format(value)) for fiscal_year, value in result.years]) if labels else []
    if labels:
        lines.append("")
        span = f"{labels[0]}→{labels[-1]}"
        recent = f"{labels[-2]}–{labels[-1]}" if len(labels) >= 2 else NA
        oldest = f"{labels[0]}–{labels[1]}" if len(labels) >= 2 else NA
        lines += _rows(
            [
                (f"Recent two-year average ({recent})", value_format(result.recent_pair_average)),
                (f"Oldest two-year average ({oldest})", value_format(result.oldest_pair_average)),
                (increase_label, _pct(result.pair_increase)),
                (f"Compound annual growth ({span})", _pct(result.cagr)),
            ]
        )
    lines += _warnings(result.warnings)
    return RenderedSection(title, "\n".join(lines))


def past_sales(result: PastSalesResult) -> RenderedSection:
    """Past Sales Records: revenue by fiscal year and its growth."""
    return _growth("Past Sales Records", result, _money, "% increase in sales")


def past_eps(result: PastEpsResult) -> RenderedSection:
    """Past EPS: reported EPS per share by Complete Fiscal Year and its growth."""
    return _growth("Past EPS", result, _per_share, "% increase in earnings")


def _table(header: list[str], rows: list[list[str]]) -> list[str]:
    """Left-aligned first column, right-aligned figures."""
    widths = [max(len(row[i]) for row in [header, *rows]) for i in range(len(header))]
    return [
        "  ".join(cell.ljust(widths[0]) if i == 0 else cell.rjust(widths[i]) for i, cell in enumerate(row))
        for row in [header, *rows]
    ]


def earnings_growth(result: EarningsGrowthResult) -> RenderedSection:
    """Earnings Growth: net income by fiscal year with change and % change."""
    rows = [
        [fiscal_year, _money(income), _money(change), _pct(pct)] for fiscal_year, income, change, pct in result.years
    ]
    lines = _table(["Fiscal year", "Net income", "Change", "% change"], rows) + _warnings(result.warnings)
    return RenderedSection("Earnings Growth", "\n".join(lines))


CASH_LABELS = {
    "cash": "Cash and equivalents",
    "short_term_investments": "Short-term investments",
    "total_cash": "Total cash",
    "long_term_debt": "Long-term debt",
    "net_cash": "Net cash",
    "shares_outstanding": "Shares outstanding",
    "net_cash_per_share": "Net cash per share",
    "receivables": "Receivables",
    "inventory": "Inventory",
    "other_current_assets": "Other current assets",
    "current_assets": "Current assets",
    "payables": "Payables",
    "short_term_debt": "Short-term debt",
    "other_current_liabilities": "Other current liabilities",
    "current_liabilities": "Current liabilities",
    "working_capital": "Working capital",
    "working_capital_per_share": "Working capital per share",
}


def _count(value: float | None) -> str:
    return NA if value is None else f"{value:,.0f}"


def _cash_value(metric: str, value: float | None) -> str:
    if metric == "shares_outstanding":
        return _count(value)
    return _per_share(value) if metric.endswith("_per_share") else _money(value)


def cash_position(result: CashPositionResult) -> RenderedSection:
    """Cash Position: a cash table and a working-capital table, latest vs prior fiscal year and latest quarter."""
    lines = []
    for group in ("cash", "working_capital"):
        header = ["LINE ITEM", result.latest_label or NA, result.prior_label or NA, "Difference", "% Difference"]
        if result.quarter_label:
            header.append(result.quarter_label)
        rows = []
        for row in (row for row in result.rows if row.group == group):
            cells = [
                CASH_LABELS[row.metric],
                _cash_value(row.metric, row.latest),
                _cash_value(row.metric, row.prior),
                _cash_value(row.metric, row.difference),
                _pct(row.pct_difference),
            ]
            if result.quarter_label:
                cells.append(_cash_value(row.metric, row.quarter))
            rows.append(cells)
        if lines:
            lines.append("")
        lines += _table(header, rows)
    lines += _warnings(result.warnings)
    return RenderedSection("Cash Position", "\n".join(lines))


LYNCH_READING = "Lynch: below 1 poor, 1.5 okay, 2 or more what you're looking for"


def _number(value: float | None) -> str:
    return NA if value is None else f"{value:,.2f}"


def revenue_growth(result: RevenueGrowthResult) -> RenderedSection:
    """Revenue Growth: revenue by year, then dividends, P/E and Lynch's dividend-adjusted ratio (D15)."""
    rows = [[fy, _money(revenue), _money(change), _pct(pct)] for fy, revenue, change, pct in result.years]
    lines = _table(["Fiscal year", "Revenue", "Change", "% change"], rows) + [""]
    lines += _rows(
        [
            ("Average growth", _pct(result.average_growth)),
            ("Dividends per share (TTM)", _per_share(result.ttm_dividends_per_share)),
            ("Dividend yield", _pct(result.dividend_yield)),
            ("EPS growth (CAGR)", _pct(result.eps_cagr)),
            ("Current P/E (price / TTM EPS)", _number(result.current_pe)),
            ("Lynch dividend-adjusted ratio", _number(result.lynch_ratio)),
        ]
    )
    lines.append(f"  ({LYNCH_READING})")
    lines += _warnings(result.warnings)
    return RenderedSection("Revenue Growth", "\n".join(lines))


def record_of_stock(result: RecordOfStockResult) -> RenderedSection:
    """Record of Stock: per fiscal year prices, EPS, P/E and dividends; averages; today against history."""
    header = ["Fiscal year", "High", "Low", "EPS", "P/E high", "P/E low", "Dividends", "% payout", "% high yield"]
    rows = [
        [
            row.fiscal_year,
            _per_share(row.high),
            _per_share(row.low),
            _per_share(row.eps),
            _number(row.pe_high),
            _number(row.pe_low),
            _per_share(row.dividends_per_share),
            _pct(row.payout),
            _pct(row.high_yield),
        ]
        for row in result.rows
    ]
    rows.append(
        [
            "Averages",
            _per_share(result.average_high),
            _per_share(result.average_low),
            "",
            _number(result.average_pe_high),
            _number(result.average_pe_low),
            "",
            _pct(result.average_payout),
            "",
        ]
    )
    lines = _table(header, rows) + [""]
    lines += _rows(
        [
            ("Present price", _per_share(result.present_price)),
            ("EPS (TTM)", _per_share(result.ttm_eps)),
            ("Average P/E", _number(result.average_pe)),
            ("Current P/E (price / TTM EPS)", _number(result.current_pe)),
            (f"Present price vs {result.oldest_fiscal_year or NA} high", _pct(result.change_from_oldest_high)),
        ]
    )
    lines += _warnings(result.warnings)
    return RenderedSection("Record of Stock", "\n".join(lines))


def trend(result: TrendResult) -> RenderedSection:
    """Trends: a summary of the chart data (the charts themselves come from render.charts)."""
    lines = []
    if result.quarterly_revenue:
        day, value = result.quarterly_revenue[-1]
        lines.append(f"Quarterly revenue: {len(result.quarterly_revenue)} quarters; latest {day}: {_money(value)}")
    if result.quarterly_eps:
        day, value = result.quarterly_eps[-1]
        lines.append(f"Quarterly EPS: {len(result.quarterly_eps)} reports; latest {day}: {_per_share(value)}")
    if result.monthly_prices:
        month, high, low, _, _ = result.monthly_prices[-1]
        lines.append(
            f"Monthly prices: {len(result.monthly_prices)} months; "
            f"{month} high {_per_share(high)}, low {_per_share(low)}"
        )
    lines += _warnings(result.warnings)
    return RenderedSection("Trends", "\n".join(lines))


LOW_LABELS = {
    "linear_regression": "Linear regression of lows",
    "average_low": "Average of fiscal-year lows",
    "severe_low": "Severe low (5 years)",
    "dividend_support": "Dividend support",
}


def _band(band) -> str:
    return f"{_per_share(band[0])}–{_per_share(band[1])}"


def risk_reward(result: RiskRewardResult) -> RenderedSection:
    """Evaluating Risk & Reward: the forecast high, then each low estimate with zones and up/down ratio."""
    lines = _rows(
        [
            ("Present price", _per_share(result.present_price)),
            ("Average P/E at high", _number(result.average_pe_high)),
            ("Projected EPS (TTM trend, 5 years)", _per_share(result.projected_eps)),
            ("Forecast high (avg P/E × projected EPS)", _per_share(result.forecast_high)),
            ("Price target appreciation", _pct(result.price_target_appreciation)),
        ]
    )
    header = ["Low estimate", "Low", "Buy", "Maybe", "Sell", "Position", "Up/down"]
    rows = []
    for low in result.lows:
        zones = low.zones
        rows.append(
            [
                LOW_LABELS[low.name],
                _per_share(low.value),
                _band(zones.buy) if zones else NA,
                _band(zones.maybe) if zones else NA,
                _band(zones.sell) if zones else NA,
                low.position or NA,
                NA if low.up_down_ratio is None else f"{low.up_down_ratio:,.2f} to 1",
            ]
        )
    if rows:
        lines += [""] + _table(header, rows)
    lines += _warnings(result.warnings)
    return RenderedSection("Evaluating Risk & Reward", "\n".join(lines))


def fundamentals(result: FundamentalsResult) -> RenderedSection:
    """Fundamentals: the aligned fiscal-year table, the in-progress year and the depth of history."""
    rows = [
        [fy, end, _money(revenue), _money(income), _per_share(eps)] for fy, end, revenue, income, eps in result.years
    ]
    lines = _table(["Fiscal year", "Period end", "Revenue", "Net income", "EPS"], rows) if rows else []
    current = result.current
    if current:
        status = (
            "awaiting annual statement"
            if current["awaiting_annual_statement"]
            else f"{current['quarters_reported']} of 4 quarters reported"
        )
        lines.append(f"Current {current['fiscal_year']}: {status}, EPS to date {_per_share(current['eps_to_date'])}")
    history = result.history
    verdict = "sufficient" if history["sufficient_history"] else f"insufficient ({YRS_LOOKBACK} needed)"
    lines.append(f"{history['complete_fiscal_years']} complete fiscal year(s); history {verdict}")
    lines += _warnings(result.warnings)
    return RenderedSection("Fundamentals", "\n".join(lines))
