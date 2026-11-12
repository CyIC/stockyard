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
from stockyard.research.models import PastSalesResult


def _unavailable(section: str, figure: str, needed: int, available: int, unit: str) -> ReportWarning:
    return ReportWarning(
        code="figure_unavailable",
        message=f"{figure} needs {needed} {unit}; {available} available",
        section=section,
        figure=figure,
        needed=needed,
        available=available,
    )


def past_sales(data: StockData, fundamentals: AlignedFundamentals, as_of: datetime.date) -> PastSalesResult:
    """Past Sales Records: revenue per fiscal year, pair-average increase and CAGR."""
    del data, as_of  # revenue comes from the aligned fiscal years, already bounded by as_of
    years = tuple((year.fiscal_year, year.revenue) for year in fundamentals.years if year.revenue is not None)
    revenue = [value for _, value in years]
    warnings = []
    cagr = definitions.cagr(revenue[0], revenue[-1], len(revenue) - 1) if len(revenue) >= 2 else None
    if len(revenue) < 2:
        warnings.append(_unavailable("past_sales", "cagr", 2, len(revenue), "fiscal years with revenue"))
    if len(revenue) >= 4:
        recent, oldest = mean(revenue[-2:]), mean(revenue[:2])
    else:
        recent = oldest = None
        warnings.append(_unavailable("past_sales", "pair_increase", 4, len(revenue), "fiscal years with revenue"))
    return PastSalesResult(
        years=years,
        recent_pair_average=recent,
        oldest_pair_average=oldest,
        pair_increase=definitions.pair_increase(revenue),
        cagr=cagr,
        warnings=tuple(warnings),
    )
