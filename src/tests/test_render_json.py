# -*- coding: utf-8 -*-
"""JSON contract stockyard.report/1 (ADR-0003, design §8.2). Key sets are pinned: a rename must bump the schema."""
import datetime
import json

import pytest

from stockyard.render import json as render_json
from stockyard.research import report as report_module
from stockyard.research.report import build_report
from tests.builders import stock_data
from tests.fixture_replay import load_stock_data

ENVELOPE_KEYS = {"schema", "ticker", "as_of", "source", "history", "warnings", "sections"}
WARNING_KEYS = {"code", "section", "figure", "message", "needed", "available"}
GROWTH_KEYS = {"years", "recent_pair_average", "oldest_pair_average", "pair_increase", "cagr"}
PRICE_ROW_KEYS = {
    "fiscal_year",
    "period_end",
    "eps",
    "high",
    "low",
    "dividends_per_share",
    "pe_high",
    "pe_low",
    "payout",
    "high_yield",
}

SECTION_KEYS = {
    "fundamentals": {"years", "current", "history"},
    "past_sales": GROWTH_KEYS,
    "past_eps": GROWTH_KEYS,
    "record_of_stock": {
        "rows",
        "average_high",
        "average_low",
        "average_pe_high",
        "average_pe_low",
        "average_pe",
        "average_payout",
        "present_price",
        "ttm_eps",
        "current_pe",
        "oldest_fiscal_year",
        "change_from_oldest_high",
    },
    "trend": {"quarterly_revenue", "quarterly_eps", "monthly_prices"},
    "cash_position": {"latest_label", "prior_label", "quarter_label", "rows"},
    "revenue_growth": {
        "years",
        "average_growth",
        "ttm_dividends_per_share",
        "dividend_yield",
        "present_price",
        "ttm_eps",
        "current_pe",
        "eps_cagr",
        "lynch_ratio",
    },
    "earnings_growth": {"years"},
    "risk_reward": {
        "present_price",
        "average_pe_high",
        "projected_eps",
        "forecast_high",
        "price_target_appreciation",
        "lows",
        "eps_points",
        "eps_forecast_line",
        "monthly_lows",
        "low_forecast_line",
    },
}
ROW_KEYS = {
    ("fundamentals", "years"): {"fiscal_year", "period_end", "revenue", "net_income", "reported_eps"},
    ("past_sales", "years"): {"fiscal_year", "revenue"},
    ("past_eps", "years"): {"fiscal_year", "reported_eps"},
    ("record_of_stock", "rows"): PRICE_ROW_KEYS,
    ("trend", "quarterly_revenue"): {"quarter_end", "revenue"},
    ("trend", "quarterly_eps"): {"announced", "reported_eps"},
    ("trend", "monthly_prices"): {"month", "high", "low", "average_high_4m", "average_low_4m"},
    ("cash_position", "rows"): {"metric", "group", "latest", "prior", "difference", "pct_difference", "quarter"},
    ("revenue_growth", "years"): {"fiscal_year", "revenue", "change", "pct_change"},
    ("earnings_growth", "years"): {"fiscal_year", "net_income", "change", "pct_change"},
    ("risk_reward", "lows"): {"name", "value", "zones", "position", "up_down_ratio"},
    ("risk_reward", "eps_points"): {"announced", "ttm_eps"},
    ("risk_reward", "eps_forecast_line"): {"date", "value"},
    ("risk_reward", "monthly_lows"): {"month", "low"},
    ("risk_reward", "low_forecast_line"): {"date", "value"},
}


@pytest.fixture(name="document", scope="module")
def _document():
    data, as_of = load_stock_data("IBM")
    return json.loads(render_json.dumps(build_report(data, as_of)))


def test_envelope(document):
    assert set(document) == ENVELOPE_KEYS
    assert document["schema"] == "stockyard.report/1"
    assert (document["ticker"], document["as_of"], document["source"]) == ("IBM", "2026-11-11", "yfinance")
    assert all(set(warning) == WARNING_KEYS for warning in document["warnings"])


def test_every_section_has_exactly_its_pinned_keys(document):
    assert {name: set(section) for name, section in document["sections"].items()} == SECTION_KEYS


def test_every_row_has_named_fields_not_positions(document):
    for (section, field), keys in ROW_KEYS.items():
        rows = document["sections"][section][field]
        assert rows, f"{section}.{field} is empty in the IBM fixture"
        assert all(set(row) == keys for row in rows), f"{section}.{field}"


def test_zones_are_low_high_pairs(document):
    average = next(low for low in document["sections"]["risk_reward"]["lows"] if low["name"] == "average_low")
    assert set(average["zones"]) == {"buy", "maybe", "sell"}
    assert len(average["zones"]["buy"]) == 2


def test_values_are_plain_json_with_null_for_missing():
    data, as_of = load_stock_data("RDDT")
    text = render_json.dumps(build_report(data, as_of))

    assert "NaN" not in text and "Infinity" not in text
    document = json.loads(text)
    assert document["sections"]["risk_reward"]["forecast_high"] is None
    assert document["sections"]["fundamentals"]["years"][0]["reported_eps"] is None


def test_a_subset_has_only_its_sections():
    data = stock_data(annual={"2025-12-31": (100.0, 10.0)}, prices=("2024-01-02", "2026-11-10"))
    document = json.loads(render_json.dumps(build_report(data, datetime.date(2026, 11, 11), sections=["past_sales"])))
    assert set(document["sections"]) == {"past_sales"}


def test_a_failed_section_is_null(monkeypatch):
    def boom(data, fundamentals, as_of):
        raise RuntimeError("kaboom")

    monkeypatch.setitem(report_module.SECTIONS, "past_eps", boom)
    data, as_of = load_stock_data("IBM")
    document = json.loads(render_json.dumps(build_report(data, as_of)))
    assert document["sections"]["past_eps"] is None
    assert any(w["code"] == "section_failed" and w["section"] == "past_eps" for w in document["warnings"])


def test_error_envelope():
    document = json.loads(render_json.dumps_error("data_unavailable", "no statements or prices for ZZZZ"))
    assert document == {
        "schema": "stockyard.error/1",
        "code": "data_unavailable",
        "message": "no statements or prices for ZZZZ",
    }
