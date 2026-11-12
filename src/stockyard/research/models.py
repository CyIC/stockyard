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
