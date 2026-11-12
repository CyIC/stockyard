# -*- coding: utf-8 -*-
"""Stock Selection Guide sections: ``section(data, fundamentals, as_of) -> Result`` (design §5.4).

Sections are pure: they read StockData and Aligned Fundamentals, never another section's result, and
explain every missing figure with a warning (design §5.6).
"""
import datetime
from statistics import mean

from stockyard.data.fundamentals import AlignedFundamentals
from stockyard.data.snapshot import StockData
from stockyard.report_warning import ReportWarning
from stockyard.research import definitions
from stockyard.research.models import EarningsGrowthResult, PastEpsResult, PastSalesResult


def _unavailable(section: str, figure: str, needed: int, available: int, unit: str) -> ReportWarning:
    return ReportWarning(
        code="figure_unavailable",
        message=f"{figure} needs {needed} {unit}; {available} available",
        section=section,
        figure=figure,
        needed=needed,
        available=available,
    )


def _growth(section: str, years: tuple, unit: str, non_positive_code: str) -> dict:
    """Pair-average increase and CAGR of ``years`` with a warning for each missing figure."""
    values = [value for _, value in years]
    warnings = []
    cagr = None
    if len(values) < 2:
        warnings.append(_unavailable(section, "cagr", 2, len(values), unit))
    else:
        cagr = definitions.cagr(values[0], values[-1], len(values) - 1)
        if cagr is None:
            warnings.append(
                ReportWarning(non_positive_code, f"cagr undefined: base year value {values[0]:,.2f}", section, "cagr")
            )
    recent = oldest = increase = None
    if len(values) < 4:
        warnings.append(_unavailable(section, "pair_increase", 4, len(values), unit))
    else:
        recent, oldest = mean(values[-2:]), mean(values[:2])
        increase = definitions.pair_increase(values)
        if increase is None:
            warnings.append(
                ReportWarning(non_positive_code, "pair_increase undefined: non-positive base", section, "pair_increase")
            )
    return {
        "years": years,
        "recent_pair_average": recent,
        "oldest_pair_average": oldest,
        "pair_increase": increase,
        "cagr": cagr,
        "warnings": tuple(warnings),
    }


def past_sales(data: StockData, fundamentals: AlignedFundamentals, as_of: datetime.date) -> PastSalesResult:
    """Past Sales Records: revenue per fiscal year, pair-average increase and CAGR."""
    del data, as_of  # revenue comes from the aligned fiscal years, already bounded by as_of
    years = tuple((year.fiscal_year, year.revenue) for year in fundamentals.years if year.revenue is not None)
    return PastSalesResult(**_growth("past_sales", years, "fiscal years with revenue", "figure_unavailable"))


def past_eps(data: StockData, fundamentals: AlignedFundamentals, as_of: datetime.date) -> PastEpsResult:
    """Past EPS: reported EPS per Complete Fiscal Year, pair-average increase and CAGR."""
    del data, as_of
    years = tuple((year.fiscal_year, year.reported_eps) for year in fundamentals.years if year.complete)
    return PastEpsResult(**_growth("past_eps", years, "complete fiscal years", "non_positive_eps"))


def earnings_growth(data: StockData, fundamentals: AlignedFundamentals, as_of: datetime.date) -> EarningsGrowthResult:
    """Earnings Growth: net income per fiscal year; % change divides by the absolute prior value."""
    del data, as_of
    incomes = [(year.fiscal_year, year.net_income) for year in fundamentals.years if year.net_income is not None]
    rows = []
    for index, (fiscal_year, income) in enumerate(incomes):
        if index == 0:
            rows.append((fiscal_year, income, None, None))
            continue
        prior = incomes[index - 1][1]
        change = income - prior
        rows.append((fiscal_year, income, change, change / abs(prior) if prior else None))
    warnings = () if len(rows) >= 2 else (_unavailable("earnings_growth", "change", 2, len(rows), "fiscal years"),)
    return EarningsGrowthResult(years=tuple(rows), warnings=warnings)
