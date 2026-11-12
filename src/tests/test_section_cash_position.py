# -*- coding: utf-8 -*-
"""Cash Position section (design §5.2.7, §5.6; D18 missing line items count as zero in totals)."""
import datetime

import pytest

from stockyard.data.fundamentals import aligned_annual_fundamentals
from stockyard.research.sections import cash_position
from tests.builders import stock_data
from tests.fixture_replay import load_stock_data

AS_OF = datetime.date(2026, 11, 11)
FULL = {
    "cash": 100.0,
    "short_term_investments": 50.0,
    "long_term_debt": 30.0,
    "shares_outstanding": 10.0,
    "receivables": 20.0,
    "inventory": 15.0,
    "other_current_assets": 5.0,
    "current_assets": 190.0,
    "payables": 25.0,
    "short_term_debt": 10.0,
    "other_current_liabilities": 5.0,
    "current_liabilities": 40.0,
}


def _section(balance, balance_quarterly=None):
    data = stock_data(balance=balance, balance_quarterly=balance_quarterly)
    return cash_position(data, aligned_annual_fundamentals(data, AS_OF), AS_OF)


def _row(result, metric):
    (row,) = [row for row in result.rows if row.metric == metric]
    return row


def test_compares_the_two_latest_fiscal_years_with_derived_totals():
    prior = {**FULL, "cash": 80.0}
    result = _section({"2024-12-31": prior, "2025-12-31": FULL})

    assert (result.latest_label, result.prior_label) == ("FY2025", "FY2024")
    total_cash = _row(result, "total_cash")
    assert (total_cash.latest, total_cash.prior, total_cash.difference) == (150.0, 130.0, 20.0)
    assert total_cash.pct_difference == pytest.approx(20 / 130)
    assert _row(result, "net_cash").latest == 120.0  # 150 - 30
    assert _row(result, "net_cash_per_share").latest == pytest.approx(12.0)
    assert _row(result, "working_capital").latest == 150.0  # 190 - 40
    assert _row(result, "working_capital_per_share").latest == pytest.approx(15.0)
    assert result.warnings == ()


def test_missing_line_items_count_as_zero_in_totals_and_are_named_in_warnings():
    """D18: yfinance omits zero items (a company with no debt and no inventory)."""
    sheet = {k: v for k, v in FULL.items() if k not in ("long_term_debt", "inventory")}
    result = _section({"2024-12-31": sheet, "2025-12-31": sheet})

    assert _row(result, "long_term_debt").latest is None
    assert _row(result, "net_cash").latest == 150.0
    noted = {(w.code, w.figure, w.message.split(":")[0]) for w in result.warnings}
    assert ("assumed_zero", "long_term_debt", "FY2025") in noted  # summed into net cash
    assert ("figure_unavailable", "inventory", "FY2024") in noted  # listed, never summed


def test_a_total_with_every_component_missing_stays_unavailable():
    sheet = {k: v for k, v in FULL.items() if k not in ("cash", "short_term_investments")}
    result = _section({"2025-12-31": sheet, "2024-12-31": sheet})
    assert _row(result, "total_cash").latest is None


def test_missing_shares_leave_per_share_figures_unavailable_not_divided_by_zero():
    sheet = {k: v for k, v in FULL.items() if k != "shares_outstanding"}
    result = _section({"2025-12-31": sheet, "2024-12-31": sheet})
    assert _row(result, "net_cash_per_share").latest is None
    assert "shares_outstanding" not in {w.figure for w in result.warnings}


def test_empty_sheets_and_sheets_after_as_of_are_ignored():
    empty = {key: float("nan") for key in FULL}
    result = _section({"2023-12-31": empty, "2024-12-31": FULL, "2025-12-31": FULL, "2026-12-31": FULL})
    assert (result.latest_label, result.prior_label) == ("FY2025", "FY2024")


def test_the_latest_quarter_is_a_separate_labelled_column():
    result = _section(
        {"2024-12-31": FULL, "2025-12-31": FULL}, balance_quarterly={"2026-09-30": FULL, "2025-12-31": FULL}
    )
    assert result.quarter_label == "Q 2026-09-30"
    assert _row(result, "total_cash").quarter == 150.0


def test_one_annual_sheet_has_no_prior_year_and_says_so():
    result = _section({"2025-12-31": FULL})
    assert result.prior_label is None and _row(result, "total_cash").difference is None
    assert ("figure_unavailable", "prior_year") in {(w.code, w.figure) for w in result.warnings}


def test_ibm_recorded_names_its_missing_fy2025_other_current_liabilities():
    data, as_of = load_stock_data("IBM")
    result = cash_position(data, aligned_annual_fundamentals(data, as_of), as_of)

    assert (result.latest_label, result.prior_label) == ("FY2025", "FY2024")
    assert any(
        (w.code, w.figure) == ("figure_unavailable", "other_current_liabilities") and w.message.startswith("FY2025")
        for w in result.warnings
    )
