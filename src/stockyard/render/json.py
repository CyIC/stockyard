# -*- coding: utf-8 -*-
"""JSON documents for agents: ``stockyard.report/1`` and ``stockyard.error/1`` (ADR-0003, design §8.2).

Every row is an object with named fields, never a positional tuple. Missing, NaN and infinite values are
``null``. Adding fields is non-breaking; renaming, removing or changing a field's meaning bumps the
schema version (pinned by tests/test_render_json.py).
"""
import dataclasses
import datetime
import json
import math

from stockyard.research.definitions import Zones
from stockyard.research.report import Report

REPORT_SCHEMA = "stockyard.report/1"
ERROR_SCHEMA = "stockyard.error/1"

ROW_FIELDS = {
    ("fundamentals", "years"): ("fiscal_year", "period_end", "revenue", "net_income", "reported_eps"),
    ("past_sales", "years"): ("fiscal_year", "revenue"),
    ("past_eps", "years"): ("fiscal_year", "reported_eps"),
    ("trend", "quarterly_revenue"): ("quarter_end", "revenue"),
    ("trend", "quarterly_eps"): ("announced", "reported_eps"),
    ("trend", "monthly_prices"): ("month", "high", "low", "average_high_4m", "average_low_4m"),
    ("revenue_growth", "years"): ("fiscal_year", "revenue", "change", "pct_change"),
    ("earnings_growth", "years"): ("fiscal_year", "net_income", "change", "pct_change"),
    ("risk_reward", "eps_points"): ("announced", "ttm_eps"),
    ("risk_reward", "eps_forecast_line"): ("date", "value"),
    ("risk_reward", "monthly_lows"): ("month", "low"),
    ("risk_reward", "low_forecast_line"): ("date", "value"),
}


def _plain(value):  # pylint: disable=too-many-return-statements  # a flat type dispatch
    """Convert a result value to JSON-safe primitives."""
    if isinstance(value, Zones):
        return {"buy": list(value.buy), "maybe": list(value.maybe), "sell": list(value.sell)}
    if dataclasses.is_dataclass(value):
        return {field.name: _plain(getattr(value, field.name)) for field in dataclasses.fields(value)}
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _section(name: str, result) -> dict | None:
    if result is None:
        return None
    document = {}
    for field in dataclasses.fields(result):
        if field.name == "warnings":  # gathered once, at report level
            continue
        value = getattr(result, field.name)
        names = ROW_FIELDS.get((name, field.name))
        document[field.name] = [dict(zip(names, _plain(row))) for row in value] if names is not None else _plain(value)
    return document


def report_document(report: Report) -> dict:
    """The ``stockyard.report/1`` document for a report."""
    return {
        "schema": REPORT_SCHEMA,
        "ticker": report.ticker,
        "as_of": report.as_of.isoformat(),
        "source": report.source,
        "history": _plain(report.history),
        "warnings": [_plain(warning) for warning in report.warnings],
        "sections": {name: _section(name, result) for name, result in report.sections.items()},
    }


def dumps(report: Report) -> str:
    """Serialise a report; NaN and infinities never reach the output."""
    return json.dumps(report_document(report), allow_nan=False)


def dumps_error(code: str, message: str) -> str:
    """The ``stockyard.error/1`` document."""
    return json.dumps({"schema": ERROR_SCHEMA, "code": code, "message": message})
