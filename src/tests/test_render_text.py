# -*- coding: utf-8 -*-
"""Terminal/text rendering of section results (design §6)."""
import datetime
import re

from stockyard.render import text
from stockyard.report_warning import ReportWarning
from stockyard.research.models import (
    CashPositionResult,
    CashRow,
    EarningsGrowthResult,
    FundamentalsResult,
    LowEstimate,
    PastEpsResult,
    PastSalesResult,
    RecordOfStockResult,
    RevenueGrowthResult,
    RiskRewardResult,
    TrendResult,
)
from stockyard.research.definitions import Zones
from stockyard.research.price_stats import PriceStatsRow


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
    assert "FY2022" in rendered.body and "$60,530M" in rendered.body
    assert "FY2025" in rendered.body and "$67,536M" in rendered.body


def test_past_sales_shows_growth_figures_with_the_years_they_span():
    body = text.past_sales(_past_sales()).body

    assert "Recent two-year average (FY2024–FY2025)" in body and "$65,145M" in body
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
    assert "FY2024" in lines[1] and "-$50M" in lines[1] and "n/a" in lines[1]
    assert "FY2025" in lines[2] and "$250M" in lines[2] and "500.00%" in lines[2]


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
    headers = [line for line in body.splitlines() if line.startswith("LINE ITEM")]
    assert len(headers) == 2  # one per table; the group name never doubles as a header (it is also a row name)
    assert body.splitlines()[0].split() == [
        "LINE",
        "ITEM",
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


def test_revenue_growth_shows_lynch_ratio_with_its_reading():
    result = RevenueGrowthResult(
        years=(("FY2024", 100.0, None, None), ("FY2025", 125.0, 25.0, 0.25)),
        average_growth=0.25,
        ttm_dividends_per_share=2.0,
        dividend_yield=0.02,
        present_price=100.0,
        ttm_eps=5.0,
        current_pe=20.0,
        eps_cagr=0.25,
        lynch_ratio=1.35,
        warnings=(),
    )
    body = text.revenue_growth(result).body

    assert text.revenue_growth(result).title == "Revenue Growth"
    assert "FY2025" in body and "25.00%" in body
    assert "Average growth" in body
    assert "Dividends per share (TTM)" in body and "$2.00" in body
    assert "Dividend yield" in body and "2.00%" in body
    assert "Current P/E" in body and "20.00" in body
    assert "Lynch dividend-adjusted ratio" in body and "1.35" in body
    assert "below 1 poor, 1.5 okay, 2 or more what you're looking for" in body


def test_record_of_stock_table_and_comparisons():
    rows = (
        PriceStatsRow("FY2024", datetime.date(2024, 12, 31), 4.0, None, None, None, None, None, None, None),
        PriceStatsRow("FY2025", datetime.date(2025, 12, 31), 4.0, 60.0, 30.0, 1.0, 15.0, 7.5, 0.25, 1 / 30),
    )
    result = RecordOfStockResult(rows, 60.0, 30.0, 15.0, 7.5, 11.25, 0.25, 50.0, 4.0, 12.5, "FY2025", -1 / 6, ())
    body = text.record_of_stock(result).body
    lines = body.splitlines()

    assert text.record_of_stock(result).title == "Record of Stock"
    assert lines[0].split()[:4] == ["Fiscal", "year", "High", "Low"]
    assert "FY2024" in lines[1] and "n/a" in lines[1]
    assert (
        "FY2025" in lines[2]
        and "$60.00" in lines[2]
        and "15.00" in lines[2]
        and "25.00%" in lines[2]
        and "3.33%" in lines[2]
    )
    assert lines[3].startswith("Averages")
    assert "Average P/E" in body and "11.25" in body
    assert "Current P/E (price / TTM EPS)" in body and "12.50" in body
    assert "Present price vs FY2025 high" in body and "-16.67%" in body


def test_trend_summarises_the_chart_data():
    result = TrendResult(
        quarterly_revenue=(("2026-06-30", 5e9), ("2026-09-30", 6e9)),
        quarterly_eps=(("2026-10-20", 1.1),),
        monthly_prices=(),
        warnings=(ReportWarning("figure_unavailable", "no monthly prices in the five years to 2026-11-11"),),
    )
    rendered = text.trend(result)

    assert rendered.title == "Trends"
    assert "Quarterly revenue" in rendered.body and "2 quarters" in rendered.body and "$6,000M" in rendered.body
    assert "Quarterly EPS" in rendered.body and "$1.10" in rendered.body
    assert "⚠ no monthly prices" in rendered.body


def test_risk_reward_summary_and_low_estimate_table():
    zones = Zones(buy=(25.0, 31.25), maybe=(31.25, 43.75), sell=(43.75, 50.0))
    lows = (
        LowEstimate("linear_regression", 60.0, None, None, None),
        LowEstimate("average_low", 25.0, zones, "maybe", 1.5),
    )
    result = RiskRewardResult(35.0, 12.5, 4.0, 50.0, 50 / 35 - 1, lows, (), (), (), (), ())
    rendered = text.risk_reward(result)
    body = rendered.body

    assert rendered.title == "Evaluating Risk & Reward"
    assert "Forecast high (avg P/E × projected EPS)" in body and "$50.00" in body
    assert "Price target appreciation" in body and "42.86%" in body
    assert "Linear regression of lows" in body
    average_line = next(line for line in body.splitlines() if line.startswith("Average of fiscal-year lows"))
    assert "$25.00–$31.25" in average_line and "maybe" in average_line and "1.50 to 1" in average_line


def test_fundamentals_table_current_year_and_history():
    result = FundamentalsResult(
        years=(("FY2024", "2024-12-31", 62.753e9, 6.023e9, 10.33), ("FY2025", "2025-12-31", 67.536e9, 10.593e9, None)),
        current={
            "fiscal_year": "FY2026",
            "quarters_reported": 3,
            "eps_to_date": 7.79,
            "awaiting_annual_statement": False,
        },
        history={
            "complete_fiscal_years": 1,
            "quarters_reported": 3,
            "price_history_start": "2021-01-04",
            "sufficient_history": False,
        },
        warnings=(),
    )
    body = text.fundamentals(result).body

    assert text.fundamentals(result).title == "Fundamentals"
    assert "FY2024" in body and "2024-12-31" in body and "$62,753M" in body and "$10.33" in body
    assert "Current FY2026: 3 of 4 quarters reported, EPS to date $7.79" in body
    assert "1 complete fiscal year(s); history insufficient (4 needed)" in body


def test_negative_per_share_figures_put_the_sign_before_the_dollar():
    rows = (CashRow("net_cash_per_share", "cash", -43.14, -38.1, -5.04, -0.1322, -48.4),)
    body = text.cash_position(CashPositionResult("FY2025", "FY2024", "Q 2026-09-30", rows, ())).body
    line = next(line for line in body.splitlines() if line.startswith("Net cash per share"))
    assert line.split()[4:7] == ["-$43.14", "-$38.10", "-$5.04"] and "$-" not in body


def test_large_dollar_amounts_are_shown_in_millions():
    rows = (
        CashRow("total_cash", "cash", 14_417_000_000.0, 14_591_000_000.0, -174_000_000.0, -0.0119, 11_058_000_000.0),
        CashRow("net_cash", "cash", -40_419_000_000.0, None, None, None, None),
        CashRow("other_current_liabilities", "working_capital", -1_000_000.0, 250_000.0, None, None, None),
        CashRow("shares_outstanding", "cash", 936_952_129.0, None, None, None, None),
    )
    body = text.cash_position(CashPositionResult("FY2025", "FY2024", None, rows, ())).body
    split = [re.split(r"\s{2,}", line.strip()) for line in body.splitlines() if line.strip()]
    cells = {parts[0]: parts[1:] for parts in split}

    assert cells["Total cash"][:3] == ["$14,417M", "$14,591M", "-$174M"]
    assert cells["Net cash"][0] == "-$40,419M"
    assert cells["Other current liabilities"][:2] == ["-$1M", "$250,000"]  # under a million keeps whole dollars
    assert cells["Shares outstanding"][0] == "936,952,129"  # counts are not money


def test_half_a_million_rounds_up():
    rows = (CashRow("total_cash", "cash", 65_144_500_000.0, -2_500_000.0, None, None, None),)
    body = text.cash_position(CashPositionResult("FY2025", "FY2024", None, rows, ())).body
    assert "$65,145M" in body and "-$3M" in body  # half up, as financial readers expect; not Python's half-to-even
