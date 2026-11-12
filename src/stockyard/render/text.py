# -*- coding: utf-8 -*-
"""Plain-text rendering of section results, shared by the CLI and (wrapped) Discord (design §6)."""
from dataclasses import dataclass

from stockyard.research.models import PastSalesResult

NA = "n/a"


@dataclass(frozen=True)
class RenderedSection:
    """A section ready to print: a title and a plain-text body."""

    title: str
    body: str


def _money(value: float | None) -> str:
    return NA if value is None else f"${value:,.0f}"


def _pct(value: float | None) -> str:
    return NA if value is None else f"{value:.2%}"


def _rows(rows) -> list[str]:
    width = max(len(label) for label, _ in rows)
    return [f"{label:<{width}}  {value:>20}" for label, value in rows]


def _warnings(warnings) -> list[str]:
    return [f"⚠ {warning.message}" for warning in warnings]


def past_sales(result: PastSalesResult) -> RenderedSection:
    """Past Sales Records: revenue by fiscal year, then the growth figures and the years they span."""
    labels = [fiscal_year for fiscal_year, _ in result.years]
    lines = _rows([(fiscal_year, _money(revenue)) for fiscal_year, revenue in result.years])
    if labels:
        lines.append("")
        span = f"{labels[0]}→{labels[-1]}"
        recent = f"{labels[-2]}–{labels[-1]}" if len(labels) >= 2 else NA
        oldest = f"{labels[0]}–{labels[1]}" if len(labels) >= 2 else NA
        lines += _rows(
            [
                (f"Recent two-year average ({recent})", _money(result.recent_pair_average)),
                (f"Oldest two-year average ({oldest})", _money(result.oldest_pair_average)),
                ("% increase in sales", _pct(result.pair_increase)),
                (f"Compound annual growth ({span})", _pct(result.cagr)),
            ]
        )
    lines += _warnings(result.warnings)
    return RenderedSection("Past Sales Records", "\n".join(lines))
