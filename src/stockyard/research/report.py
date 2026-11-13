# -*- coding: utf-8 -*-
"""build_report: run the requested sections and gather their warnings (design §5.4, §5.5)."""
import datetime
from dataclasses import dataclass

from stockyard.data.fundamentals import aligned_annual_fundamentals
from stockyard.data.snapshot import StockData
from stockyard.report_warning import ReportWarning
from stockyard.research import sections as section_functions

SECTIONS = {
    "fundamentals": section_functions.fundamentals_table,
    "past_sales": section_functions.past_sales,
    "past_eps": section_functions.past_eps,
    "record_of_stock": section_functions.record_of_stock,
    "trend": section_functions.trend,
    "cash_position": section_functions.cash_position,
    "revenue_growth": section_functions.revenue_growth,
    "earnings_growth": section_functions.earnings_growth,
    "risk_reward": section_functions.risk_reward,
}
SECTION_IDS = tuple(SECTIONS)


@dataclass(frozen=True)
class Report:
    """Section results for one ticker as of one date, with every warning gathered once."""

    ticker: str
    as_of: datetime.date
    source: str
    history: dict
    sections: dict  # section id -> result, or None if the section failed
    warnings: tuple


def build_report(data: StockData, as_of: datetime.date, sections=None) -> Report:
    """Run ``sections`` (default: all) in report order.

    A section that raises becomes ``None`` with a ``section_failed`` warning; the others are unaffected.

    :raises ValueError: for an unknown section id
    """
    requested = SECTION_IDS if sections is None else tuple(sections)
    unknown = [name for name in requested if name not in SECTIONS]
    if unknown:
        raise ValueError(f"unknown section(s) {unknown}; valid ids: {', '.join(SECTION_IDS)}")
    fundamentals = aligned_annual_fundamentals(data, as_of)
    warnings = list(fundamentals.warnings)
    results = {}
    for name in SECTION_IDS:
        if name not in requested:
            continue
        try:
            results[name] = SECTIONS[name](data, fundamentals, as_of)
        except Exception as exc:  # pylint: disable=broad-exception-caught  # one section must not sink the report
            results[name] = None
            warnings.append(ReportWarning("section_failed", f"{name} failed: {exc}", section=name))
            continue
        if name != "fundamentals":  # its warnings are the alignment warnings, already gathered
            warnings.extend(results[name].warnings)
    return Report(
        ticker=data.ticker,
        as_of=as_of,
        source="yfinance",
        history=fundamentals.history,
        sections=results,
        warnings=tuple(warnings),
    )
