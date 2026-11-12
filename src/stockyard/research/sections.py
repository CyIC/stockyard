# -*- coding: utf-8 -*-
"""Stock Selection Guide sections: ``section(data, fundamentals, as_of) -> Result`` (design §5.4).

Sections are pure: they read StockData and Aligned Fundamentals, never another section's result, and
explain every missing figure with a warning (design §5.6).
"""
import datetime
import math
from statistics import mean

from stockyard.data.fundamentals import AlignedFundamentals
from stockyard.data.snapshot import StockData
from stockyard.report_warning import ReportWarning
from stockyard.research import definitions
from stockyard.research.models import (
    CashPositionResult,
    CashRow,
    EarningsGrowthResult,
    PastEpsResult,
    PastSalesResult,
)


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


CASH_ITEMS = {
    "cash": "cashAndCashEquivalentsAtCarryingValue",
    "short_term_investments": "shortTermInvestments",
    "long_term_debt": "longTermDebt",
    "shares_outstanding": "commonStockSharesOutstanding",
    "receivables": "currentNetReceivables",
    "inventory": "inventory",
    "other_current_assets": "otherCurrentAssets",
    "current_assets": "totalCurrentAssets",
    "payables": "currentAccountsPayable",
    "short_term_debt": "shortTermDebt",
    "other_current_liabilities": "otherCurrentLiabilities",
    "current_liabilities": "totalCurrentLiabilities",
}
CASH_LAYOUT = (
    (
        "cash",
        (
            "cash",
            "short_term_investments",
            "total_cash",
            "long_term_debt",
            "net_cash",
            "shares_outstanding",
            "net_cash_per_share",
        ),
    ),
    (
        "working_capital",
        (
            "receivables",
            "inventory",
            "other_current_assets",
            "current_assets",
            "payables",
            "short_term_debt",
            "other_current_liabilities",
            "current_liabilities",
            "working_capital",
            "working_capital_per_share",
        ),
    ),
)
SUMMED_ITEMS = ("cash", "short_term_investments", "long_term_debt")  # D18: missing counts as 0 in totals


def _sheet_values(row, label: str) -> tuple[dict, list]:
    """Line items, derived totals and the warnings for one balance sheet (D18)."""
    items = {}
    for metric, column in CASH_ITEMS.items():
        value = row.get(column)
        items[metric] = None if value is None or math.isnan(value) else float(value)
    warnings = []
    for metric in CASH_ITEMS:
        if items[metric] is None and metric != "shares_outstanding":
            summed = metric in SUMMED_ITEMS
            warnings.append(
                ReportWarning(
                    "assumed_zero" if summed else "figure_unavailable",
                    f"{label}: {metric} not reported" + ("; counted as 0 in totals" if summed else ""),
                    "cash_position",
                    metric,
                )
            )
    cash_parts = [items["cash"], items["short_term_investments"]]
    total_cash = None if all(v is None for v in cash_parts) else sum(v or 0.0 for v in cash_parts)
    net_cash = None if total_cash is None else total_cash - (items["long_term_debt"] or 0.0)
    assets, liabilities = items["current_assets"], items["current_liabilities"]
    working_capital = None if assets is None or liabilities is None else assets - liabilities
    shares = items["shares_outstanding"]
    values = {
        **items,
        "total_cash": total_cash,
        "net_cash": net_cash,
        "net_cash_per_share": None if net_cash is None or not shares else net_cash / shares,
        "working_capital": working_capital,
        "working_capital_per_share": None if working_capital is None or not shares else working_capital / shares,
    }
    return values, warnings


def _reported(frame, as_of: datetime.date):
    """Rows on or before as_of that carry at least one value (yfinance pads with an empty oldest column)."""
    if frame.empty:
        return frame
    return frame[(frame.index.date <= as_of) & frame.notna().any(axis=1)]


def cash_position(data: StockData, fundamentals: AlignedFundamentals, as_of: datetime.date) -> CashPositionResult:
    """Cash Position: two latest annual balance sheets compared, plus the latest quarter (design §5.2.7)."""
    del fundamentals
    annual = _reported(data.balance_annual, as_of)
    quarterly = _reported(data.balance_quarterly, as_of)
    columns = {}
    warnings = []
    for key, stamp in zip(("latest", "prior"), reversed(annual.index[-2:])):
        label = f"FY{stamp.year}"
        columns[key] = (label, *_sheet_values(annual.loc[stamp], label))
    if not quarterly.empty and (annual.empty or quarterly.index[-1] > annual.index[-1]):
        label = f"Q {quarterly.index[-1].date().isoformat()}"
        columns["quarter"] = (label, *_sheet_values(quarterly.loc[quarterly.index[-1]], label))
    for _, _, column_warnings in columns.values():
        warnings += column_warnings
    if len(annual) < 2:
        warnings.append(_unavailable("cash_position", "prior_year", 2, len(annual), "annual balance sheets"))
    rows = []
    for group, metrics in CASH_LAYOUT:
        for metric in metrics:
            latest, prior, quarter = (
                columns[k][1][metric] if k in columns else None for k in ("latest", "prior", "quarter")
            )
            difference = None if latest is None or prior is None else latest - prior
            pct = None if difference is None or not prior else difference / abs(prior)
            rows.append(CashRow(metric, group, latest, prior, difference, pct, quarter))
    return CashPositionResult(
        latest_label=columns["latest"][0] if "latest" in columns else None,
        prior_label=columns["prior"][0] if "prior" in columns else None,
        quarter_label=columns["quarter"][0] if "quarter" in columns else None,
        rows=tuple(rows),
        warnings=tuple(warnings),
    )
