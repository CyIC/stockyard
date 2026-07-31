# -*- coding: utf-8 -*-
# pylint: disable=C0116, W0212
"""Tests for the drift-proofing behaviour of the yfinance snapshot loader."""
import datetime

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


@pytest.mark.parametrize("elapsed_years", [0, 1, 4, 9])
def test_shift_tracks_whole_years_since_the_anchor(elapsed_years):
    anchor = (datetime.datetime.now() - relativedelta(years=elapsed_years, days=3)).isoformat()

    assert fixture_loader._shift_years(anchor) == elapsed_years


def test_no_shift_applied_for_a_future_anchor():
    """A freshly regenerated snapshot must be used exactly as captured."""
    anchor = (datetime.datetime.now() + relativedelta(months=6)).isoformat()

    assert fixture_loader._shift_years(anchor) == 0


def test_rebasing_preserves_month_and_day():
    """Shifting by whole years keeps fiscal year ends on their own calendar date."""
    payload = {
        "index_name": "fiscalDateEnding",
        "index": ["2021-12-31T00:00:00", "2022-06-30T00:00:00"],
        "columns": ["reportedEPS"],
        "dtypes": {"reportedEPS": "float64"},
        "data": [[9.97], [2.31]],
    }

    frame = fixture_loader._payload_to_frame(payload, shift=3)

    assert [stamp.date() for stamp in frame.index] == [datetime.date(2024, 12, 31), datetime.date(2025, 6, 30)]
    assert frame["reportedEPS"].tolist() == [9.97, 2.31]


def test_snapshot_stays_inside_the_five_year_lookback():
    """The guarantee that makes these fixtures drift-proof.

    stock_analysis filters every input to the last five years. If the snapshot ages past that
    window the filters silently trim it down and the reports get computed from a handful of
    rows, which is exactly how the stale Alphavantage fixtures distorted the analysis.
    """
    cutoff = datetime.datetime.now() - relativedelta(years=5)

    daily = fixture_loader.load("daily_prices")
    assert daily.index.max() >= cutoff
    assert (daily.index >= cutoff).sum() > 1000, "a full five years of daily prices must survive"

    annual = fixture_loader.load("earnings")["annualEarnings"]
    assert (annual.index >= cutoff).sum() >= 5, "all five fiscal years must survive the filter"


def test_price_and_earnings_datasets_stay_aligned():
    """record_of_stock looks up price rows by an earnings row's fiscal year.

    Both datasets get the same shift, so every annual earnings year must still have monthly
    price rows to match against.
    """
    monthly = fixture_loader.load("monthly_prices")
    annual = fixture_loader.load("earnings")["annualEarnings"]
    cutoff = datetime.datetime.now() - relativedelta(years=5)

    price_years = {stamp.year for stamp in monthly.index}
    for stamp in annual.index[annual.index >= cutoff]:
        assert stamp.year in price_years, f"no monthly prices for fiscal year {stamp.year}"
