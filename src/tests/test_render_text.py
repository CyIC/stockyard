# -*- coding: utf-8 -*-
"""Terminal/text rendering of section results (design §6)."""
from stockyard.render import text
from stockyard.report_warning import ReportWarning
from stockyard.research.models import (
    CashPositionResult,
    CashRow,
    EarningsGrowthResult,
    PastEpsResult,
    PastSalesResult,
)


def _past_sales(**overrides):
    values = {
        "years": (
            ("FY2022", 60_530_000_000.0),
            ("FY2023", 61_860_000_000.0),
            ("FY2024", 62_753_000_000.0),
            ("FY2025", 67_536_000_000.0),
        ),
        "recent_pair_average": 65_144_500_000.0,
        "oldest_pair_average": 61_195_000_000.0,
        "pair_increase": 0.064531,
        "cagr": 0.037175,
        "warnings": (),
    }
    values.update(overrides)
    return PastSalesResult(**values)


def test_past_sales_shows_each_fiscal_year_with_its_label():
    rendered = text.past_sales(_past_sales())

    assert rendered.title == "Past Sales Records"
    assert "FY2022" in rendered.body and "$60,530,000,000" in rendered.body
    assert "FY2025" in rendered.body and "$67,536,000,000" in rendered.body


def test_past_sales_shows_growth_figures_with_the_years_they_span():
    body = text.past_sales(_past_sales()).body

    assert "Recent two-year average (FY2024–FY2025)" in body and "$65,144,500,000" in body
    assert "Oldest two-year average (FY2022–FY2023)" in body
    assert "% increase in sales" in body and "6.45%" in body
    assert "Compound annual growth (FY2022→FY2025)" in body and "3.72%" in body


def test_missing_figures_read_n_a_and_warnings_are_listed():
    result = _past_sales(
        years=(("FY2024", 100.0), ("FY2025", 110.0)),
        recent_pair_average=None,
        oldest_pair_average=None,
        pair_increase=None,
        warnings=(ReportWarning("figure_unavailable", "pair_increase needs 4 fiscal years with revenue; 2 available"),),
    )
    body = text.past_sales(result).body

    assert "% increase in sales" in body and "n/a" in body
    assert "⚠ pair_increase needs 4 fiscal years with revenue; 2 available" in body


def test_past_eps_shows_eps_per_share_with_cents():
    result = PastEpsResult(
        years=(("FY2024", 10.33), ("FY2025", 11.57)),
        recent_pair_average=None,
        oldest_pair_average=None,
        pair_increase=None,
        cagr=0.12,
        warnings=(),
    )
    rendered = text.past_eps(result)

    assert rendered.title == "Past EPS"
    assert "FY2025" in rendered.body and "$11.57" in rendered.body
    assert "% increase in earnings" in rendered.body
    assert "Compound annual growth (FY2024→FY2025)" in rendered.body and "12.00%" in rendered.body


def test_earnings_growth_table():
    result = EarningsGrowthResult(
        years=(("FY2024", -50_000_000.0, None, None), ("FY2025", 200_000_000.0, 250_000_000.0, 5.0)), warnings=()
    )
    rendered = text.earnings_growth(result)

    assert rendered.title == "Earnings Growth"
    lines = rendered.body.splitlines()
    assert lines[0].split() == ["Fiscal", "year", "Net", "income", "Change", "%", "change"]
    assert "FY2024" in lines[1] and "-$50,000,000" in lines[1] and "n/a" in lines[1]
    assert "FY2025" in lines[2] and "$250,000,000" in lines[2] and "500.00%" in lines[2]


def test_cash_position_tables():
    rows = (
        CashRow("total_cash", "cash", 150.0, 130.0, 20.0, 20 / 130, 155.0),
        CashRow("shares_outstanding", "cash", 10.0, 10.0, 0.0, 0.0, 10.0),
        CashRow("net_cash_per_share", "cash", 12.0, 10.0, 2.0, 0.2, None),
        CashRow("inventory", "working_capital", None, 15.0, None, None, None),
        CashRow("working_capital_per_share", "working_capital", 15.0, 14.0, 1.0, 1 / 14, None),
    )
    result = CashPositionResult(
        "FY2025",
        "FY2024",
        "Q 2026-09-30",
        rows,
        (ReportWarning("figure_unavailable", "FY2025: inventory not reported"),),
    )
    rendered = text.cash_position(result)

    assert rendered.title == "Cash Position"
    body = rendered.body
    assert body.splitlines()[0].split() == [
        "Cash",
        "FY2025",
        "FY2024",
        "Difference",
        "%",
        "Difference",
        "Q",
        "2026-09-30",
    ]
    assert "Total cash" in body and "$150" in body and "15.38%" in body
    shares_line = next(line for line in body.splitlines() if line.startswith("Shares outstanding"))
    assert "$" not in shares_line
    assert "Net cash per share" in body and "$12.00" in body
    assert "Working capital per share" in body
    inventory_line = next(line for line in body.splitlines() if line.startswith("Inventory"))
    assert "n/a" in inventory_line
    assert "⚠ FY2025: inventory not reported" in body
