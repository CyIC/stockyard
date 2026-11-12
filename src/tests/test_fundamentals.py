# -*- coding: utf-8 -*-
"""Aligned Annual Fundamentals (design §5.2, ADR-0001 as amended)."""
import datetime

import pytest

from stockyard.data.fundamentals import aligned_annual_fundamentals
from tests.builders import quarterly_eps, stock_data
from tests.fixture_replay import load_stock_data

AS_OF = datetime.date(2026, 11, 11)
DEC_QUARTERS_2025 = ["2025-03-31", "2025-06-30", "2025-09-30", "2025-12-31"]


def _align(**kwargs):
    return aligned_annual_fundamentals(stock_data(**kwargs), AS_OF)


# --- fiscal-year rows ------------------------------------------------------------------------


def test_fiscal_years_are_annual_period_ends_on_or_before_as_of_oldest_first():
    result = _align(annual={"2024-12-31": (100, 10), "2025-12-31": (110, 11), "2026-12-31": (120, 12)})

    assert [fy.fiscal_year for fy in result.years] == ["FY2024", "FY2025"]
    assert [fy.period_end for fy in result.years] == [datetime.date(2024, 12, 31), datetime.date(2025, 12, 31)]
    assert [(fy.revenue, fy.net_income) for fy in result.years] == [(100, 10), (110, 11)]


def test_four_attributed_quarters_make_a_complete_year_whose_eps_is_their_sum():
    result = _align(
        annual={"2025-12-31": (100, 10)},
        eps=[("2025-04-20", 1.0), ("2025-07-20", 1.25), ("2025-10-20", 1.5), ("2026-01-25", 2.0)],
    )

    year = result.years[0]
    assert year.quarter_eps == (1.0, 1.25, 1.5, 2.0)
    assert year.reported_eps == pytest.approx(5.75)
    assert year.complete


def test_q4_announced_after_the_new_year_belongs_to_the_old_fiscal_year():
    """The ADR-0001 reproduction: Q4-FY2025 EPS announced in late January 2026."""
    result = _align(annual={"2025-12-31": (100, 10)}, eps=quarterly_eps(DEC_QUARTERS_2025, lag_days=28))

    assert result.years[0].fiscal_year == "FY2025"
    assert result.years[0].complete


@pytest.mark.parametrize(
    ("year_end", "quarter_ends"),
    [
        ("2025-06-30", ["2024-09-30", "2024-12-31", "2025-03-31", "2025-06-30"]),  # MSFT-style
        ("2025-09-30", ["2024-12-31", "2025-03-31", "2025-06-30", "2025-09-30"]),
        ("2025-09-27", ["2024-12-28", "2025-03-29", "2025-06-28", "2025-09-27"]),  # 52/53-week filer
    ],
)
def test_non_december_and_52_53_week_year_ends_bucket_correctly(year_end, quarter_ends):
    result = _align(annual={year_end: (100, 10)}, eps=quarterly_eps(quarter_ends, lag_days=30))

    year = result.years[0]
    assert year.fiscal_year == f"FY{year_end[:4]}"
    assert year.complete


def test_a_missing_quarter_keeps_the_year_with_revenue_but_no_eps():
    """Pre-IPO S-1 years have statements but no earnings announcements (design §5.2.4)."""
    result = _align(annual={"2025-12-31": (100, 10)}, eps=quarterly_eps(DEC_QUARTERS_2025[1:]))

    year = result.years[0]
    assert (year.revenue, year.net_income) == (100, 10)
    assert year.reported_eps is None
    assert not year.complete
    assert year.quarter_eps == (None, 1.0, 1.0, 1.0)


def test_announcements_after_as_of_are_ignored():
    """Q4 is announced 25 Jan, inside the 120-day window, but after an as_of of 20 Jan."""
    late = [("2025-04-20", 1.0), ("2025-07-20", 1.0), ("2025-10-20", 1.0), ("2026-01-25", 1.0)]
    result = aligned_annual_fundamentals(
        stock_data(annual={"2025-12-31": (100, 10)}, eps=late), datetime.date(2026, 1, 20)
    )

    assert result.years[0].quarter_eps == (1.0, 1.0, 1.0, None)


# --- attribution warnings --------------------------------------------------------------------


def _codes(result):
    return [warning.code for warning in result.warnings]


def _eps_codes(result):
    return [code for code in _codes(result) if code.startswith("eps_")]


def test_two_announcements_for_one_quarter_keep_the_earliest_and_warn():
    eps = quarterly_eps(DEC_QUARTERS_2025) + [("2025-05-02", 9.0)]  # second release for Q1
    result = _align(annual={"2025-12-31": (100, 10)}, eps=eps)

    assert result.years[0].quarter_eps[0] == 1.0
    assert _eps_codes(result) == ["eps_duplicate"]


def test_an_announcement_more_than_120_days_after_its_quarter_end_is_dropped_with_a_warning():
    """Quarter-ends are three months apart, so this only happens past the in-progress year (stale statements)."""
    eps = quarterly_eps(DEC_QUARTERS_2025) + [("2027-06-15", 1.0)]  # 166 days after the last derived quarter-end
    result = aligned_annual_fundamentals(
        stock_data(annual={"2025-12-31": (100, 10)}, eps=eps), datetime.date(2027, 7, 1)
    )

    assert result.years[0].quarter_eps == (1.0, 1.0, 1.0, 1.0)
    assert result.current.quarters_reported == 0
    assert _eps_codes(result) == ["eps_unattributed"]


def test_announcements_older_than_the_statement_history_are_ignored_silently():
    """The earnings fetch reaches back past the oldest annual statement; those rows are not errors."""
    eps = [("2024-10-20", 7.0)] + quarterly_eps(DEC_QUARTERS_2025)
    result = _align(annual={"2025-12-31": (100, 10)}, eps=eps)

    assert result.years[0].quarter_eps == (1.0, 1.0, 1.0, 1.0)
    assert _eps_codes(result) == []


# --- current year ----------------------------------------------------------------------------


def test_quarters_after_the_last_annual_statement_form_the_current_year():
    eps = quarterly_eps(DEC_QUARTERS_2025) + quarterly_eps(["2026-03-31", "2026-06-30"], value=2.0)
    result = _align(annual={"2025-12-31": (100, 10)}, eps=eps)

    current = result.current
    assert current.fiscal_year == "FY2026"
    assert current.quarters_reported == 2
    assert current.eps_to_date == pytest.approx(4.0)
    assert not current.awaiting_annual_statement
    assert [fy.fiscal_year for fy in result.years] == ["FY2025"]


def test_four_quarters_without_an_annual_statement_are_awaiting_it_and_excluded_from_comparisons():
    eps = quarterly_eps(DEC_QUARTERS_2025, lag_days=20)
    result = aligned_annual_fundamentals(
        stock_data(annual={"2024-12-31": (90, 9)}, eps=eps), datetime.date(2026, 1, 30)
    )

    assert result.current.quarters_reported == 4
    assert result.current.awaiting_annual_statement
    assert [fy.fiscal_year for fy in result.years] == ["FY2024"]
    assert "awaiting_annual_statement" in _codes(result)


def test_no_annual_statements_means_no_years_and_no_current_year():
    result = _align(eps=quarterly_eps(DEC_QUARTERS_2025))

    assert result.years == ()
    assert result.current is None


# --- sufficiency and history -----------------------------------------------------------------


def _complete_years(count):
    ends = [f"{year}-12-31" for year in range(2025 - count + 1, 2026)]
    annual = {end: (100, 10) for end in ends}
    quarters = [q.replace("2025", end[:4]) for end in ends for q in DEC_QUARTERS_2025]
    return annual, quarterly_eps(quarters)


def test_four_complete_years_are_sufficient():
    """D17: yfinance reliably supplies about four annual statements."""
    annual, eps = _complete_years(4)
    result = _align(annual=annual, eps=eps)

    assert result.sufficient_history
    assert "insufficient_history" not in _codes(result)


def test_three_complete_years_are_insufficient_and_say_what_was_needed():
    annual, eps = _complete_years(3)
    result = _align(annual=annual, eps=eps)

    assert not result.sufficient_history
    (warning,) = [w for w in result.warnings if w.code == "insufficient_history"]
    assert (warning.needed, warning.available) == (4, 3)


def test_price_windows_are_covered_only_when_prices_span_the_whole_fiscal_year():
    """An IPO in mid-2024 leaves FY2024's window partly untraded (design §5.2.8)."""
    annual = {"2023-12-31": (80, 8), "2024-12-31": (90, 9), "2025-12-31": (100, 10)}
    result = _align(annual=annual, prices=("2024-06-14", "2026-11-10"))

    assert [fy.prices_covered for fy in result.years] == [False, False, True]
    assert [fy.window_start for fy in result.years] == [
        datetime.date(2022, 12, 31),
        datetime.date(2023, 12, 31),
        datetime.date(2024, 12, 31),
    ]


def test_history_block_summarises_the_depth_of_data():
    annual, eps = _complete_years(5)
    eps += quarterly_eps(["2026-03-31"], value=2.0)
    result = _align(annual=annual, eps=eps, prices=("2020-01-02", "2026-11-10"))

    assert result.history == {
        "complete_fiscal_years": 5,
        "quarters_reported": 1,
        "price_history_start": "2020-01-02",
        "sufficient_history": True,
    }


# --- recorded fixtures (captured 2026-11-11) -------------------------------------------------


def _recorded(ticker):
    data, as_of = load_stock_data(ticker)
    return aligned_annual_fundamentals(data, as_of)


def test_ibm_fiscal_year_eps_is_the_sum_of_its_four_reported_quarters():
    fy2025 = next(year for year in _recorded("IBM").years if year.fiscal_year == "FY2025")

    assert fy2025.quarter_eps == (1.6, 2.8, 2.65, 4.52)
    assert fy2025.reported_eps == pytest.approx(11.57)


def test_msft_june_year_end_has_four_complete_years_which_is_sufficient():
    result = _recorded("MSFT")

    assert [year.fiscal_year for year in result.years] == ["FY2023", "FY2024", "FY2025", "FY2026"]
    assert all(year.complete for year in result.years)
    assert result.sufficient_history
    assert result.current.fiscal_year == "FY2027"


def test_rddt_keeps_pre_ipo_revenue_years_and_flags_its_partly_traded_ipo_year():
    result = _recorded("RDDT")
    by_year = {year.fiscal_year: year for year in result.years}

    assert by_year["FY2022"].revenue is not None and not by_year["FY2022"].complete
    assert by_year["FY2024"].complete and not by_year["FY2024"].prices_covered
    assert by_year["FY2025"].prices_covered
    assert result.history["complete_fiscal_years"] == 2
    assert not result.sufficient_history
