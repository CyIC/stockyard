# -*- coding: utf-8 -*-
"""Past EPS section: reported EPS per Complete Fiscal Year (design §5.4, §5.6, §5.7)."""
import datetime

import pytest

from stockyard.data.fundamentals import aligned_annual_fundamentals
from stockyard.research.sections import past_eps
from tests.builders import quarterly_eps, stock_data
from tests.fixture_replay import load_stock_data

AS_OF = datetime.date(2026, 11, 11)


def _quarters(year):
    return [f"{year}-03-31", f"{year}-06-30", f"{year}-09-30", f"{year}-12-31"]


def _section(eps_by_year, extra_years=()):
    annual = {f"{year}-12-31": (100, 10) for year in list(eps_by_year) + list(extra_years)}
    eps = [
        item for year, quarter_value in eps_by_year.items() for item in quarterly_eps(_quarters(year), quarter_value)
    ]
    data = stock_data(annual=annual, eps=eps)
    return past_eps(data, aligned_annual_fundamentals(data, AS_OF), AS_OF)


def test_lists_reported_eps_of_complete_years_and_computes_growth():
    result = _section({2022: 0.25, 2023: 0.30, 2024: 0.35, 2025: 0.40})  # annual 1.00, 1.20, 1.40, 1.60

    assert [fy for fy, _ in result.years] == ["FY2022", "FY2023", "FY2024", "FY2025"]
    assert [eps for _, eps in result.years] == pytest.approx([1.0, 1.2, 1.4, 1.6])
    assert result.pair_increase == pytest.approx((1.5 - 1.1) / 1.1)
    assert result.cagr == pytest.approx(1.6 ** (1 / 3) - 1)
    assert result.warnings == ()


def test_years_without_four_reported_quarters_are_excluded():
    result = _section({2024: 0.25, 2025: 0.30}, extra_years=[2023])
    assert [fy for fy, _ in result.years] == ["FY2024", "FY2025"]


def test_a_loss_in_the_base_year_leaves_cagr_undefined_with_a_warning():
    result = _section({2024: -0.5, 2025: 0.5})

    assert result.cagr is None
    assert ("non_positive_eps", "past_eps", "cagr") in {(w.code, w.section, w.figure) for w in result.warnings}


def test_rddt_recorded_loss_year_and_short_history():
    data, as_of = load_stock_data("RDDT")
    result = past_eps(data, aligned_annual_fundamentals(data, as_of), as_of)

    assert [fy for fy, _ in result.years] == ["FY2024", "FY2025"]
    assert result.cagr is None and result.pair_increase is None
    assert {(w.code, w.figure) for w in result.warnings} == {
        ("non_positive_eps", "cagr"),
        ("figure_unavailable", "pair_increase"),
    }
