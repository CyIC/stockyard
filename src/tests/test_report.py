# -*- coding: utf-8 -*-
"""build_report: sections, metadata and warnings gathered into one Report (design §5.4, §5.5)."""
import datetime

import pytest

from stockyard.research import report as report_module
from stockyard.research.report import SECTION_IDS, build_report
from tests.fixture_replay import load_stock_data

EXPECTED_IDS = (
    "fundamentals",
    "past_sales",
    "past_eps",
    "record_of_stock",
    "trend",
    "cash_position",
    "revenue_growth",
    "earnings_growth",
    "risk_reward",
)


@pytest.fixture(name="ibm")
def _ibm():
    return load_stock_data("IBM")


def test_all_sections_by_default_in_report_order(ibm):
    data, as_of = ibm
    report = build_report(data, as_of)

    assert SECTION_IDS == EXPECTED_IDS
    assert tuple(report.sections) == EXPECTED_IDS
    assert all(result is not None for result in report.sections.values())


def test_metadata(ibm):
    data, as_of = ibm
    report = build_report(data, as_of)

    assert (report.ticker, report.as_of, report.source) == ("IBM", as_of, "yfinance")
    assert report.history["complete_fiscal_years"] == 5


def test_a_subset_of_sections_keeps_report_order(ibm):
    data, as_of = ibm
    report = build_report(data, as_of, sections=["risk_reward", "past_eps"])
    assert tuple(report.sections) == ("past_eps", "risk_reward")


def test_an_unknown_section_is_rejected_naming_the_valid_ids(ibm):
    data, as_of = ibm
    with pytest.raises(ValueError, match="past_sales"):
        build_report(data, as_of, sections=["nope"])


def test_warnings_are_gathered_once_with_their_section():
    data, as_of = load_stock_data("RDDT")
    report = build_report(data, as_of)

    keys = [(w.code, w.section, w.figure, w.message) for w in report.warnings]
    assert len(keys) == len(set(keys)), "no duplicates (alignment warnings also live in the fundamentals section)"
    assert ("insufficient_history", None) in {(w.code, w.section) for w in report.warnings}
    assert ("figure_unavailable", "risk_reward", "forecast_high") in {
        (w.code, w.section, w.figure) for w in report.warnings
    }


def test_a_failing_section_becomes_null_with_a_warning_and_the_rest_survive(ibm, monkeypatch):
    def boom(data, fundamentals, as_of):
        raise RuntimeError("kaboom")

    monkeypatch.setitem(report_module.SECTIONS, "past_eps", boom)
    data, as_of = ibm
    report = build_report(data, as_of)

    assert report.sections["past_eps"] is None
    assert report.sections["past_sales"] is not None
    (warning,) = [w for w in report.warnings if w.code == "section_failed"]
    assert warning.section == "past_eps" and "kaboom" in warning.message


def test_as_of_is_a_date(ibm):
    data, as_of = ibm
    assert isinstance(build_report(data, as_of).as_of, datetime.date)
