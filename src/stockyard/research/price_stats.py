# -*- coding: utf-8 -*-
"""Price figures shared by several sections, so no section consumes another's result (design §5.4)."""
import datetime
from dataclasses import dataclass

from stockyard.data.fundamentals import PRICE_EDGE_TOLERANCE_DAYS, AlignedFundamentals
from stockyard.data.snapshot import StockData
from stockyard.research import definitions


@dataclass(frozen=True)
class PriceStatsRow:  # pylint: disable=too-many-instance-attributes
    """One Complete Fiscal Year's prices, earnings and dividends; price figures are None if not fully traded."""

    fiscal_year: str
    period_end: datetime.date
    eps: float
    high: float | None
    low: float | None
    dividends_per_share: float | None
    pe_high: float | None
    pe_low: float | None
    payout: float | None
    high_yield: float | None


def fiscal_year_price_stats(data: StockData, fundamentals: AlignedFundamentals, as_of: datetime.date) -> tuple:
    """One row per Complete Fiscal Year on or before ``as_of``, prices taken from its window (P-1, P]."""
    rows = []
    prices = data.daily_prices
    for year in fundamentals.years:
        if not year.complete or year.period_end > as_of:
            continue
        if not year.prices_covered:
            rows.append(PriceStatsRow(year.fiscal_year, year.period_end, year.reported_eps, *([None] * 7)))
            continue
        window = prices[(prices.index.date > year.window_start) & (prices.index.date <= year.period_end)]
        high, low = float(window["high"].max()), float(window["low"].min())
        dividends = float(window["dividend"].sum())
        rows.append(
            PriceStatsRow(
                fiscal_year=year.fiscal_year,
                period_end=year.period_end,
                eps=year.reported_eps,
                high=high,
                low=low,
                dividends_per_share=dividends,
                pe_high=definitions.pe(high, year.reported_eps),
                pe_low=definitions.pe(low, year.reported_eps),
                payout=definitions.payout(dividends, year.reported_eps),
                high_yield=definitions.high_yield(dividends, low),
            )
        )
    return tuple(rows)


def ttm_dividends_per_share(data: StockData, as_of: datetime.date) -> float | None:
    """Per-share dividends in the 365 days up to ``as_of``; None without a full year of price history."""
    prices = data.daily_prices
    start = as_of - datetime.timedelta(days=365)
    if prices.empty or prices.index.min().date() > start + datetime.timedelta(days=PRICE_EDGE_TOLERANCE_DAYS):
        return None
    window = prices[(prices.index.date > start) & (prices.index.date <= as_of)]
    return float(window["dividend"].sum())
