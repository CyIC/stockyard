# -*- coding: utf-8 -*-
"""Section results: frozen, structured, never formatted text (ADR-0002, design §5.4)."""
from dataclasses import dataclass


@dataclass(frozen=True)
class GrowthRecord:
    """A per-fiscal-year series and its growth: pair-average increase (4+ years) and CAGR (2+ years)."""

    years: tuple  # ((fiscal_year, value), ...), oldest first
    recent_pair_average: float | None
    oldest_pair_average: float | None
    pair_increase: float | None
    cagr: float | None
    warnings: tuple


@dataclass(frozen=True)
class PastSalesResult(GrowthRecord):
    """Revenue per fiscal year (statement years with revenue)."""


@dataclass(frozen=True)
class PastEpsResult(GrowthRecord):
    """Reported EPS per Complete Fiscal Year."""


@dataclass(frozen=True)
class EarningsGrowthResult:
    """Net income per fiscal year with its change from the prior year."""

    years: tuple  # ((fiscal_year, net_income, change, pct_change), ...); change/pct None for the first year
    warnings: tuple


@dataclass(frozen=True)
class CashRow:  # pylint: disable=too-many-instance-attributes
    """One Cash Position metric across the two latest fiscal years and the latest quarter."""

    metric: str
    group: str  # "cash" or "working_capital"
    latest: float | None
    prior: float | None
    difference: float | None
    pct_difference: float | None
    quarter: float | None


@dataclass(frozen=True)
class CashPositionResult:
    """Balance-sheet comparison: latest vs prior fiscal year, plus the latest quarter."""

    latest_label: str | None
    prior_label: str | None
    quarter_label: str | None
    rows: tuple
    warnings: tuple


@dataclass(frozen=True)
class RevenueGrowthResult:  # pylint: disable=too-many-instance-attributes
    """Revenue growth plus the valuation figures behind Lynch's dividend-adjusted ratio (D15)."""

    years: tuple  # ((fiscal_year, revenue, change, pct_change), ...)
    average_growth: float | None
    ttm_dividends_per_share: float | None
    dividend_yield: float | None
    present_price: float | None
    ttm_eps: float | None
    current_pe: float | None
    eps_cagr: float | None
    lynch_ratio: float | None
    warnings: tuple


@dataclass(frozen=True)
class RecordOfStockResult:  # pylint: disable=too-many-instance-attributes
    """Fiscal-year price history (shared PriceStatsRow rows), its averages and today's comparison."""

    rows: tuple
    average_high: float | None
    average_low: float | None
    average_pe_high: float | None
    average_pe_low: float | None
    average_pe: float | None
    average_payout: float | None
    present_price: float | None
    ttm_eps: float | None
    current_pe: float | None
    oldest_fiscal_year: str | None
    change_from_oldest_high: float | None
    warnings: tuple


@dataclass(frozen=True)
class TrendResult:
    """Chart data within five years of as_of; dates are ISO strings, months "YYYY-MM"."""

    quarterly_revenue: tuple  # ((quarter_end, revenue), ...)
    quarterly_eps: tuple  # ((announced, reported_eps), ...)
    monthly_prices: tuple  # ((month, high, low, avg_high_4m, avg_low_4m), ...)
    warnings: tuple
