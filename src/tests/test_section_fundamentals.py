# -*- coding: utf-8 -*-
"""Fundamentals section: the aligned fiscal-year table for the CLI and JSON (design §5.4)."""
import datetime

import pytest

from stockyard.data.fundamentals import aligned_annual_fundamentals
from stockyard.research.sections import fundamentals_table as fundamentals_section
from tests.fixture_replay import load_stock_data


def test_ibm_recorded_years_current_year_history_and_alignment_warnings():
    data, as_of = load_stock_data("IBM")
    aligned = aligned_annual_fundamentals(data, as_of)

    result = fundamentals_section(data, aligned, as_of)

    fy2025 = result.years[-1]
    assert fy2025 == ("FY2025", "2025-12-31", 67_536_000_000.0, 10_593_000_000.0, pytest.approx(11.57))
    assert result.years[0][2] is None  # IBM's oldest statement has no revenue
    assert result.current == {
        "fiscal_year": "FY2026",
        "quarters_reported": 3,
        "eps_to_date": pytest.approx(7.79),
        "awaiting_annual_statement": False,
    }
    assert result.history == aligned.history
    assert result.warnings == aligned.warnings


def test_no_statements_has_no_years_and_no_current_year():
    data, as_of = load_stock_data("RDDT")
    aligned = aligned_annual_fundamentals(data, datetime.date(2021, 1, 1))
    result = fundamentals_section(data, aligned, datetime.date(2021, 1, 1))
    assert result.years == () and result.current is None
