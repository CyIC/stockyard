# -*- coding: utf-8 -*-
"""Section results: frozen, structured, never formatted text (ADR-0002, design §5.4)."""
from dataclasses import dataclass


@dataclass(frozen=True)
class PastSalesResult:
    """Revenue per fiscal year (statement years with revenue) and its growth."""

    years: tuple  # ((fiscal_year, revenue), ...), oldest first
    recent_pair_average: float | None
    oldest_pair_average: float | None
    pair_increase: float | None
    cagr: float | None
    warnings: tuple
