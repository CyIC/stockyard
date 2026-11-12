# -*- coding: utf-8 -*-
"""Plain-text rendering of section results, shared by the CLI and (wrapped) Discord (design §6)."""
from dataclasses import dataclass

from stockyard.research.models import PastEpsResult, PastSalesResult

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


def _per_share(value: float | None) -> str:
    return NA if value is None else f"${value:,.2f}"


def _growth(title: str, result, value_format, increase_label: str) -> RenderedSection:
    """A per-fiscal-year series followed by its growth figures and the years they span."""
    labels = [fiscal_year for fiscal_year, _ in result.years]
    lines = _rows([(fiscal_year, value_format(value)) for fiscal_year, value in result.years]) if labels else []
    if labels:
        lines.append("")
        span = f"{labels[0]}→{labels[-1]}"
        recent = f"{labels[-2]}–{labels[-1]}" if len(labels) >= 2 else NA
        oldest = f"{labels[0]}–{labels[1]}" if len(labels) >= 2 else NA
        lines += _rows(
            [
                (f"Recent two-year average ({recent})", value_format(result.recent_pair_average)),
                (f"Oldest two-year average ({oldest})", value_format(result.oldest_pair_average)),
                (increase_label, _pct(result.pair_increase)),
                (f"Compound annual growth ({span})", _pct(result.cagr)),
            ]
        )
    lines += _warnings(result.warnings)
    return RenderedSection(title, "\n".join(lines))


def past_sales(result: PastSalesResult) -> RenderedSection:
    """Past Sales Records: revenue by fiscal year and its growth."""
    return _growth("Past Sales Records", result, _money, "% increase in sales")


def past_eps(result: PastEpsResult) -> RenderedSection:
    """Past EPS: reported EPS per share by Complete Fiscal Year and its growth."""
    return _growth("Past EPS", result, _per_share, "% increase in earnings")
