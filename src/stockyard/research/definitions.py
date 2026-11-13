# -*- coding: utf-8 -*-
"""Stock Selection Guide financial definitions (design §5.7).

Pure functions on plain numbers. Percentages are fractions (0.12 = 12 %); multiples (P/E, up/down ratio,
Lynch ratio) are plain numbers. Every function returns None where the figure is undefined; the calling
section attaches the explanatory warning.
"""
from dataclasses import dataclass
from statistics import mean


def cagr(first: float, last: float, periods: int) -> float | None:
    """Compound annual growth rate ``(last / first) ** (1 / periods) - 1``; n fiscal years span n - 1 periods."""
    if periods < 1 or first <= 0 or last < 0:
        return None
    return (last / first) ** (1 / periods) - 1


def pair_increase(values) -> float | None:
    """(mean of the last two - mean of the first two) / mean of the first two; needs four values."""
    if len(values) < 4:
        return None
    base = mean(values[:2])
    if base <= 0:
        return None
    return (mean(values[-2:]) - base) / base


def ttm_eps(quarterly_eps) -> float | None:
    """Trailing-twelve-month EPS: the sum of the last four quarters."""
    if len(quarterly_eps) < 4:
        return None
    return sum(quarterly_eps[-4:])


def pe(price: float | None, eps: float | None) -> float | None:
    """Price / earnings; undefined for non-positive earnings."""
    if price is None or eps is None or eps <= 0:
        return None
    return price / eps


def payout(dividends_per_share: float, eps: float) -> float | None:
    """Share of earnings paid as dividends."""
    if eps is None or eps <= 0:
        return None
    return dividends_per_share / eps


def high_yield(dividends_per_share: float, low: float) -> float | None:
    """Dividend yield at the fiscal year's low price."""
    if low is None or low <= 0:
        return None
    return dividends_per_share / low


def dividend_yield(ttm_dividends_per_share: float, price: float) -> float | None:
    """Trailing-twelve-month dividends per share / present price (0 for a non-payer)."""
    if price is None or price <= 0:
        return None
    return ttm_dividends_per_share / price


def appreciation(target: float, price: float) -> float | None:
    """Implied price change to the target; negative when the price is above it."""
    if target is None or price is None or price <= 0:
        return None
    return target / price - 1


def lynch_ratio(  # pylint: disable=redefined-outer-name
    eps_growth: float | None, dividend_yield: float | None, pe: float | None
) -> float | None:
    """Peter Lynch's dividend-adjusted PEG, ``(EPS growth % + dividend yield %) / P/E``.

    From *One Up on Wall Street* (1989). Lynch writes both percentages as whole numbers, so fractions are
    multiplied by 100 here: 12 % growth, 2 % yield, P/E 20 gives (12 + 2) / 20 = 0.7. Lynch's reading:
    below 1 poor, 1.5 okay, 2 or more what you're looking for. Stockyard uses the EPS CAGR as the growth
    rate (design §5.7, D15).
    """
    if eps_growth is None or dividend_yield is None or pe is None or pe <= 0:
        return None
    return (eps_growth * 100 + dividend_yield * 100) / pe


def up_down_ratio(high: float, price: float, low: float) -> float | None:
    """Potential gain versus risk of loss, ``(high - price) / (price - low)``; undefined outside (low, high)."""
    if price <= low or price >= high:
        return None
    return (high - price) / (price - low)


@dataclass(frozen=True)
class Zones:
    """Buy / Maybe / Sell bands of a forecast range, split 25 / 50 / 25 (D14)."""

    buy: tuple
    maybe: tuple
    sell: tuple

    def position(self, price: float) -> str:
        """Where ``price`` sits: below_range, buy, maybe, sell or above_range.

        The top of the Buy band is inclusive: there the up/down ratio is exactly 3 to 1.
        """
        if price < self.buy[0]:
            return "below_range"
        if price <= self.buy[1]:
            return "buy"
        if price < self.sell[0]:
            return "maybe"
        if price <= self.sell[1]:
            return "sell"
        return "above_range"


def zones(low: float, high: float) -> Zones | None:
    """Split ``[low, high]`` into Buy (lowest 25 %), Maybe (middle 50 %) and Sell (top 25 %)."""
    if low >= high:
        return None
    quarter = (high - low) / 4
    return Zones(buy=(low, low + quarter), maybe=(low + quarter, high - quarter), sell=(high - quarter, high))
