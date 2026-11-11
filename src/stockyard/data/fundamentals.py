# -*- coding: utf-8 -*-
"""Aligned Annual Fundamentals (ADR-0001 as amended; design §5.2).

The income-statement fiscal period-end is the single source of truth for which fiscal year a figure
belongs to. Quarter-ends are derived from the annual period-ends, and each earnings announcement is
attributed to the latest derived quarter-end before it.
"""
import datetime
from dataclasses import dataclass

import pandas as pd

from stockyard.data.snapshot import StockData
from stockyard.report_warning import ReportWarning

YRS_LOOKBACK = 5  # Complete Fiscal Years the SSG compares (D12)
QUARTER_OFFSETS_MONTHS = (9, 6, 3, 0)  # quarter-ends of fiscal year P: P-9m, P-6m, P-3m, P
CURRENT_YEAR_OFFSETS_MONTHS = (-3, -6, -9, -12)  # in-progress year after the last period-end P: P+3m ... P+12m
MAX_REPORTING_LAG_DAYS = 120
PRICE_EDGE_TOLERANCE_DAYS = 7  # weekends and holidays between a window edge and the nearest trading day


@dataclass(frozen=True)
class FiscalYear:  # pylint: disable=too-many-instance-attributes
    """One fiscal year keyed by its income-statement period-end."""

    fiscal_year: str
    period_end: datetime.date
    revenue: float | None
    net_income: float | None
    quarter_eps: tuple
    reported_eps: float | None
    window_start: datetime.date
    prices_covered: bool

    @property
    def complete(self) -> bool:
        """True when all four quarters have reported EPS (a Complete Fiscal Year)."""
        return self.reported_eps is not None


@dataclass(frozen=True)
class CurrentYear:
    """The fiscal year after the last annual statement (design §5.2.5)."""

    fiscal_year: str
    quarters_reported: int
    eps_to_date: float | None
    awaiting_annual_statement: bool


@dataclass(frozen=True)
class AlignedFundamentals:
    """Fiscal-year history for one ticker as of one date."""

    years: tuple
    current: CurrentYear | None
    sufficient_history: bool
    history: dict
    warnings: tuple


def _value(row, column):
    value = row.get(column)
    return None if value is None or pd.isna(value) else float(value)


def _quarter_ends(period_ends):
    """Return [(fiscal_year_index, quarter_index, quarter_end)] sorted by quarter_end.

    Index ``len(period_ends)`` is the in-progress year after the last period-end.
    """
    ends = []
    for index, period_end in enumerate(period_ends):
        for quarter, months in enumerate(QUARTER_OFFSETS_MONTHS):
            ends.append((index, quarter, (period_end - pd.DateOffset(months=months)).date()))
    if period_ends:
        for quarter, months in enumerate(CURRENT_YEAR_OFFSETS_MONTHS):
            ends.append((len(period_ends), quarter, (period_ends[-1] - pd.DateOffset(months=months)).date()))
    return sorted(ends, key=lambda item: item[2])


def _attribute(earnings, quarter_ends, as_of, year_count):
    """Place each reported EPS in its quarter slot; return (slots, warnings)."""
    slots = [[None] * 4 for _ in range(year_count + 1)]
    warnings = []
    for announced, row in earnings.sort_index().iterrows():
        day = announced.date()
        if day > as_of or pd.isna(row["reported_eps"]):
            continue
        before = [item for item in quarter_ends if item[2] < day]
        if not before:
            continue  # older than the statement history: belongs to a year we do not report
        year, quarter, quarter_end = before[-1]
        if (day - quarter_end).days > MAX_REPORTING_LAG_DAYS:
            warnings.append(
                ReportWarning("eps_unattributed", f"EPS announced {day} matches no quarter-end within 120 days")
            )
        elif slots[year][quarter] is not None:
            warnings.append(
                ReportWarning("eps_duplicate", f"second EPS release on {day} for quarter ending {quarter_end} ignored")
            )
        else:
            slots[year][quarter] = float(row["reported_eps"])
    return slots, warnings


def _prices_cover(prices, start: datetime.date, end: datetime.date) -> bool:
    if prices.empty:
        return False
    tolerance = datetime.timedelta(days=PRICE_EDGE_TOLERANCE_DAYS)
    return prices.index.min().date() <= start + tolerance and prices.index.max().date() >= end - tolerance


def _current_year(period_ends, quarters) -> CurrentYear | None:
    if not period_ends:
        return None
    reported = [value for value in quarters if value is not None]
    return CurrentYear(
        fiscal_year=f"FY{(period_ends[-1] + pd.DateOffset(months=12)).year}",
        quarters_reported=len(reported),
        eps_to_date=sum(reported) if reported else None,
        awaiting_annual_statement=len(reported) == 4,
    )


def aligned_annual_fundamentals(data: StockData, as_of: datetime.date) -> AlignedFundamentals:
    """Build the fiscal-year history of ``data`` as of ``as_of``."""
    income = data.income_annual
    period_ends = [stamp for stamp in income.index if stamp.date() <= as_of] if not income.empty else []
    slots, warnings = _attribute(data.earnings, _quarter_ends(period_ends), as_of, len(period_ends))
    years = []
    for index, period_end in enumerate(period_ends):
        row = income.loc[period_end]
        quarters = tuple(slots[index])
        start = (period_ends[index - 1] if index else period_end - pd.DateOffset(months=12)).date()
        years.append(
            FiscalYear(
                fiscal_year=f"FY{period_end.year}",
                period_end=period_end.date(),
                revenue=_value(row, "totalRevenue"),
                net_income=_value(row, "netIncome"),
                quarter_eps=quarters,
                reported_eps=None if None in quarters else sum(quarters),
                window_start=start,
                prices_covered=_prices_cover(data.daily_prices, start, period_end.date()),
            )
        )
    current = _current_year(period_ends, slots[len(period_ends)])
    if current and current.awaiting_annual_statement:
        warnings.append(
            ReportWarning(
                "awaiting_annual_statement",
                f"{current.fiscal_year} has four reported quarters but no annual statement yet; "
                "excluded from comparisons",
            )
        )
    complete = sum(1 for year in years if year.complete)
    sufficient = complete >= YRS_LOOKBACK
    if not sufficient:
        warnings.append(
            ReportWarning(
                "insufficient_history",
                f"{complete} complete fiscal years; the Stock Selection Guide compares {YRS_LOOKBACK}",
                needed=YRS_LOOKBACK,
                available=complete,
            )
        )
    prices = data.daily_prices
    return AlignedFundamentals(
        years=tuple(years),
        current=current,
        sufficient_history=sufficient,
        history={
            "complete_fiscal_years": complete,
            "quarters_reported": current.quarters_reported if current else 0,
            "price_history_start": None if prices.empty else prices.index.min().date().isoformat(),
            "sufficient_history": sufficient,
        },
        warnings=tuple(warnings),
    )
