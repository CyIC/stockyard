# -*- coding: utf-8 -*-
# pylint: disable=C0116, W0212
"""Tests for the yfinance snapshot loader."""
import datetime
import types

import pandas as pd
import pytest
from dateutil.relativedelta import relativedelta

# under test
from tests import fixture_loader


def test_every_dataset_loads_with_the_getter_contract():
    """Each dataset must match the shape of the get_yfinance_* helper it stands in for."""
    for name in ("income_statement", "balance_sheet", "cash_flow"):
        reports = fixture_loader.load(name)
        assert set(reports) == {"annualReports", "quarterlyReports"}
        for frame in reports.values():
            assert not frame.empty
            assert isinstance(frame.index, pd.DatetimeIndex)

    earnings = fixture_loader.load("earnings")
    assert set(earnings) == {"annualEarnings", "quarterlyEarnings"}
    assert "reportedEPS" in earnings["annualEarnings"].columns
    assert "reportedEPS" in earnings["quarterlyEarnings"].columns

    for name in ("monthly_prices", "daily_prices"):
        prices = fixture_loader.load(name)
        assert {"open", "high", "low", "close", "dividend_amt"} <= set(prices.columns)
        assert prices.index.is_monotonic_increasing


def test_unknown_dataset_names_report_what_is_available():
    with pytest.raises(KeyError, match="daily_prices"):
        fixture_loader.load("no_such_dataset")


class _YearsLater(datetime.datetime):
    """A clock three years after the snapshot was captured."""

    @classmethod
    def now(cls, tz=None):
        return datetime.datetime.fromisoformat(fixture_loader._snapshot()["anchor"]) + relativedelta(years=3)


@pytest.fixture
def clock_three_years_later(monkeypatch):
    monkeypatch.setattr(fixture_loader, "datetime", types.SimpleNamespace(datetime=_YearsLater))


def test_dates_are_used_exactly_as_captured_even_years_later(clock_three_years_later):
    """Design §5.3: tests pin as_of to the snapshot date instead of rebasing data to the clock."""
    raw = fixture_loader._snapshot()["datasets"]["income_statement"]["annualReports"]["index"]

    frame = fixture_loader.load("income_statement")["annualReports"]

    assert [stamp.isoformat() for stamp in frame.index] == raw


def test_anchor_is_the_capture_date_even_years_later(clock_three_years_later):
    captured = datetime.datetime.fromisoformat(fixture_loader._snapshot()["anchor"])

    assert fixture_loader.anchor() == captured


def test_price_and_earnings_datasets_stay_aligned():
    """record_of_stock looks up price rows by an earnings row's fiscal year.

    Every annual earnings year inside the five-year window before the snapshot must have
    monthly price rows to match against.
    """
    monthly = fixture_loader.load("monthly_prices")
    annual = fixture_loader.load("earnings")["annualEarnings"]
    cutoff = fixture_loader.anchor() - relativedelta(years=5)

    price_years = {stamp.year for stamp in monthly.index}
    for stamp in annual.index[annual.index >= cutoff]:
        assert stamp.year in price_years, f"no monthly prices for fiscal year {stamp.year}"
