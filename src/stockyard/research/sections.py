# -*- coding: utf-8 -*-
"""Stock Selection Guide sections: ``section(data, fundamentals, as_of) -> Result`` (design §5.4).

Sections are pure: they read StockData and Aligned Fundamentals, never another section's result, and
explain every missing figure with a warning (design §5.6).
"""
import datetime
import math
from statistics import mean

import pandas as pd

from stockyard.data.fundamentals import AlignedFundamentals
from stockyard.data.snapshot import StockData
from stockyard.report_warning import ReportWarning
from stockyard.research import definitions
from stockyard.research import price_stats
from stockyard.research.models import (
    CashPositionResult,
    CashRow,
    EarningsGrowthResult,
    PastEpsResult,
    PastSalesResult,
    RecordOfStockResult,
    RevenueGrowthResult,
    TrendResult,
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
    rows = _year_over_year([(y.fiscal_year, y.net_income) for y in fundamentals.years if y.net_income is not None])
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


def _year_over_year(series) -> list:
    """((fiscal_year, value, change, pct_change), ...) with pct_change relative to the prior value."""
    rows = []
    for index, (fiscal_year, value) in enumerate(series):
        if index == 0:
            rows.append((fiscal_year, value, None, None))
            continue
        prior = series[index - 1][1]
        rows.append((fiscal_year, value, value - prior, (value - prior) / abs(prior) if prior else None))
    return rows


def revenue_growth(data: StockData, fundamentals: AlignedFundamentals, as_of: datetime.date) -> RevenueGrowthResult:
    """Revenue Growth: year-over-year revenue, dividends, current P/E and Lynch's dividend-adjusted ratio."""
    section = "revenue_growth"
    warnings = []
    rows = _year_over_year([(y.fiscal_year, y.revenue) for y in fundamentals.years if y.revenue is not None])
    changes = [row[3] for row in rows[1:] if row[3] is not None]
    if not changes:
        warnings.append(_unavailable(section, "average_growth", 2, len(rows), "fiscal years with revenue"))
    price = price_stats.present_price(data, as_of)
    dividends = price_stats.ttm_dividends_per_share(data, as_of)
    dividend_yield = None if dividends is None or price is None else definitions.dividend_yield(dividends, price)
    if dividend_yield is None:
        warnings.append(
            ReportWarning("figure_unavailable", "dividend_yield needs a year of prices", section, "dividend_yield")
        )
    ttm = price_stats.trailing_eps(data, as_of)
    current_pe = definitions.pe(price, ttm)
    if current_pe is None:
        code = "non_positive_eps" if ttm is not None and ttm <= 0 else "figure_unavailable"
        warnings.append(
            ReportWarning(
                code, f"current_pe needs a price and positive TTM EPS (TTM EPS: {ttm})", section, "current_pe"
            )
        )
    complete = [y.reported_eps for y in fundamentals.years if y.complete]
    eps_cagr = definitions.cagr(complete[0], complete[-1], len(complete) - 1) if len(complete) >= 2 else None
    if len(complete) < 2:
        warnings.append(_unavailable(section, "eps_cagr", 2, len(complete), "complete fiscal years"))
    elif eps_cagr is None:
        warnings.append(
            ReportWarning(
                "non_positive_eps", f"eps_cagr undefined: base year EPS {complete[0]:,.2f}", section, "eps_cagr"
            )
        )
    lynch = definitions.lynch_ratio(eps_cagr, dividend_yield, current_pe)
    if lynch is None:
        missing = [
            name
            for name, value in (("eps_cagr", eps_cagr), ("dividend_yield", dividend_yield), ("current_pe", current_pe))
            if value is None
        ]
        warnings.append(
            ReportWarning("figure_unavailable", f"lynch_ratio needs {', '.join(missing)}", section, "lynch_ratio")
        )
    return RevenueGrowthResult(
        years=tuple(rows),
        average_growth=mean(changes) if changes else None,
        ttm_dividends_per_share=dividends,
        dividend_yield=dividend_yield,
        present_price=price,
        ttm_eps=ttm,
        current_pe=current_pe,
        eps_cagr=eps_cagr,
        lynch_ratio=lynch,
        warnings=tuple(warnings),
    )


def _mean_of(values) -> float | None:
    present = [value for value in values if value is not None]
    return mean(present) if present else None


def record_of_stock(data: StockData, fundamentals: AlignedFundamentals, as_of: datetime.date) -> RecordOfStockResult:
    """Record of Stock: per fiscal year high, low, EPS, P/E, dividends; averages; present price vs history."""
    section = "record_of_stock"
    rows = price_stats.fiscal_year_price_stats(data, fundamentals, as_of)
    warnings = []
    for row in rows:
        if row.high is None:
            warnings.append(
                ReportWarning(
                    "figure_unavailable", f"{row.fiscal_year}: not fully traded; no price figures", section, "prices"
                )
            )
        elif row.eps <= 0:
            warnings.append(
                ReportWarning(
                    "non_positive_eps",
                    f"{row.fiscal_year}: EPS {row.eps:,.2f}; left out of P/E averages",
                    section,
                    "pe",
                )
            )
    if not rows:
        warnings.append(_unavailable(section, "rows", 1, 0, "complete fiscal years"))
    price = price_stats.present_price(data, as_of)
    ttm = price_stats.trailing_eps(data, as_of)
    oldest = next((row for row in rows if row.high is not None), None)
    return RecordOfStockResult(
        rows=rows,
        average_high=_mean_of(row.high for row in rows),
        average_low=_mean_of(row.low for row in rows),
        average_pe_high=_mean_of(row.pe_high for row in rows),
        average_pe_low=_mean_of(row.pe_low for row in rows),
        average_pe=_mean_of([row.pe_high for row in rows] + [row.pe_low for row in rows]),
        average_payout=_mean_of(row.payout for row in rows),
        present_price=price,
        ttm_eps=ttm,
        current_pe=definitions.pe(price, ttm),
        oldest_fiscal_year=oldest.fiscal_year if oldest else None,
        change_from_oldest_high=definitions.appreciation(price, oldest.high) if oldest and price is not None else None,
        warnings=tuple(warnings),
    )


TREND_YEARS = 5


def _within(frame, as_of: datetime.date):
    """Rows in the five years up to and including as_of."""
    if frame.empty:
        return frame
    start = as_of - pd.DateOffset(years=TREND_YEARS)
    return frame[(frame.index > start) & (frame.index.date <= as_of)]


def _column(frame, name: str) -> pd.Series:
    """One column without missing values; an empty Series when the frame is empty."""
    return frame[name].dropna() if not frame.empty else pd.Series(dtype=float)


def trend(data: StockData, fundamentals: AlignedFundamentals, as_of: datetime.date) -> TrendResult:
    """Trend: quarterly revenue and EPS, monthly highs and lows with 4-month averages (chart data)."""
    del fundamentals
    revenue = _column(_within(data.income_quarterly, as_of), "totalRevenue")
    eps = _column(_within(data.earnings, as_of), "reported_eps")
    prices = _within(data.daily_prices, as_of)
    monthly = []
    if not prices.empty:
        grouped = prices.groupby(prices.index.to_period("M")).agg({"high": "max", "low": "min"})
        avg_high, avg_low = grouped["high"].rolling(4).mean(), grouped["low"].rolling(4).mean()
        for month, row in grouped.iterrows():
            monthly.append(
                (
                    str(month),
                    float(row["high"]),
                    float(row["low"]),
                    None if pd.isna(avg_high[month]) else float(avg_high[month]),
                    None if pd.isna(avg_low[month]) else float(avg_low[month]),
                )
            )
    series = {
        "quarterly_revenue": tuple((day.date().isoformat(), float(value)) for day, value in revenue.items()),
        "quarterly_eps": tuple((day.date().isoformat(), float(value)) for day, value in eps.items()),
        "monthly_prices": tuple(monthly),
    }
    warnings = tuple(
        ReportWarning("figure_unavailable", f"no {name.replace('_', ' ')} in the five years to {as_of}", "trend", name)
        for name, values in series.items()
        if not values
    )
    return TrendResult(**series, warnings=warnings)
