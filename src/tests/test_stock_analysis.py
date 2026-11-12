# -*- coding: utf-8 -*-
# pylint: disable=C0116, W0511
"""Test stock_report module for stock analysis."""
import asyncio
import datetime
import types
import unittest
import warnings
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from tests import fixture_loader
# under test
from stockyard import stock_analysis


class _SnapshotClock(datetime.datetime):
    """datetime whose now() is the fixture's capture date."""

    @classmethod
    def now(cls, tz=None):
        return fixture_loader.anchor()


@pytest.fixture(autouse=True)
def _freeze_legacy_clock(monkeypatch):
    """Legacy stock_analysis reads datetime.now(); pin it to the snapshot until Phase 4 replaces it."""
    monkeypatch.setattr(stock_analysis, "datetime", types.SimpleNamespace(datetime=_SnapshotClock))


# pylint: disable=E1136
def _load_reports(dataset):
    """Load a statement snapshot in the {'annualReports', 'quarterlyReports'} contract."""
    return fixture_loader.load(dataset)


def _load_earnings():
    """Load the earnings snapshot in the {'annualEarnings', 'quarterlyEarnings'} contract."""
    return fixture_loader.load("earnings")


def _load_prices(dataset):
    """Load a price snapshot as a date-indexed DataFrame."""
    return fixture_loader.load(dataset)


class StockAnalysisTestCase(unittest.TestCase):
    """Test Stock Analysis methods."""

    def test_risk_reward(self):
        """Test cash position risk_reward module."""
        # GIVEN
        income_statement = _load_reports("income_statement")
        daily_prices = _load_prices("daily_prices")
        monthly_prices = _load_prices("monthly_prices")
        earnings = _load_earnings()

        # WHEN
        with warnings.catch_warnings():
            warnings.simplefilter("error", FutureWarning)
            msg, charts = stock_analysis.risk_reward(
                daily_prices,
                earnings,
                monthly_prices,
                income_statement,
                earnings["quarterlyEarnings"]["reportedEPS"].iloc[-1],  # stand in for highest EPS
            )
        # THEN
        self.assertIsInstance(msg, str)
        self.assertIsInstance(charts, list)
        for fig in charts:
            self.assertIsInstance(fig, str)

    @pytest.mark.usefixtures("core_stub")
    def test_run_calls_risk_reward_with_matching_signature(self):
        """run() must call risk_reward with an argument list its signature accepts.

        Regression: run() passed a 6th (shares-outstanding) argument to risk_reward(),
        which accepts only 5 parameters. Patching risk_reward with autospec=True enforces
        the real signature, so a mismatched call raises TypeError.
        """
        # GIVEN a message and every collaborator run() touches mocked out (no network).
        # yfinance getters are synchronous. get_yfinance_earnings returns non-empty earnings
        # frames so the .empty guard passes and risk_reward is reached (MagicMock subscripts
        # keep the earnings['quarterlyEarnings']['reportedEPS'][-1] access from touching pandas).
        message = MagicMock()
        message.channel.send = AsyncMock()

        yf_mock = MagicMock()
        for getter in (
            "get_yfinance_income_statement",
            "get_yfinance_balance_sheet",
            "get_yfinance_cash_flow",
            "get_monthly_yfinance_company_prices",
            "get_daily_yfinance_company_prices",
        ):
            setattr(yf_mock, getter, MagicMock(return_value=MagicMock()))
        non_empty_annual = MagicMock()
        non_empty_annual.empty = False
        non_empty_quarterly = MagicMock()
        non_empty_quarterly.empty = False
        yf_mock.get_yfinance_earnings = MagicMock(
            return_value={"annualEarnings": non_empty_annual, "quarterlyEarnings": non_empty_quarterly}
        )

        utils_mock = MagicMock()
        utils_mock.send_message_in_chunks = AsyncMock()

        # WHEN / THEN run() completes without a signature TypeError
        with patch.object(stock_analysis, "yf_api", yf_mock), patch.object(
            stock_analysis, "utils", utils_mock





        ), patch.object(
            stock_analysis, "risk_reward", autospec=True
        ) as risk_reward_mock:
            risk_reward_mock.return_value = ("risk_reward", [])
            asyncio.run(stock_analysis.run(message, "IBM"))

        risk_reward_mock.assert_called_once()

    @pytest.mark.usefixtures("core_stub")
    def test_run_bails_out_when_quarterly_earnings_missing(self):
        """run() warns and returns early when earnings data is incomplete.

        Regression: earnings['quarterlyEarnings'] can be empty (yfinance returns an empty
        DataFrame when there is no quarterly data), and building the report off it would crash
        on earnings['quarterlyEarnings']['reportedEPS'][-1]. run() must bail out first.
        """
        # GIVEN earnings present annually but an empty quarterly frame (the missing-data case)
        message = MagicMock()
        message.channel.send = AsyncMock()

        yf_mock = MagicMock()
        for getter in (
            "get_yfinance_income_statement",
            "get_yfinance_balance_sheet",
            "get_yfinance_cash_flow",
            "get_monthly_yfinance_company_prices",
            "get_daily_yfinance_company_prices",
        ):
            setattr(yf_mock, getter, MagicMock(return_value=MagicMock()))
        yf_mock.get_yfinance_earnings = MagicMock(
            return_value={
                "annualEarnings": pd.DataFrame({"reportedEPS": [1.0]}),
                "quarterlyEarnings": pd.DataFrame(),  # empty -> triggers the guard
            }
        )

        utils_mock = MagicMock()
        utils_mock.send_message_in_chunks = AsyncMock()

        # WHEN
        with patch.object(stock_analysis, "yf_api", yf_mock), patch.object(
            stock_analysis, "utils", utils_mock
        ), patch.object(stock_analysis, "risk_reward") as risk_reward_mock:
            asyncio.run(stock_analysis.run(message, "AAPL"))

        # THEN it warned the channel and never reached the earnings-dependent report sections
        message.channel.send.assert_awaited_once()
        self.assertIn("AAPL", str(message.channel.send.await_args))
        risk_reward_mock.assert_not_called()

    def test_epoch_seconds(self):
        """_epoch_seconds converts each datetime to its UNIX epoch seconds."""
        # GIVEN
        times = [datetime.datetime(2020, 1, 1), datetime.datetime(2021, 6, 15, 12, 30)]

        # WHEN
        result = stock_analysis._epoch_seconds(times)

        # THEN
        self.assertEqual(result, [moment.timestamp() for moment in times])

    def test_epoch_seconds_empty(self):
        """_epoch_seconds returns an empty list for empty input."""
        self.assertEqual(stock_analysis._epoch_seconds([]), [])

    def test_predict_values(self):
        """_predict_values evaluates the prediction at each time's epoch seconds."""
        # GIVEN a prediction that marks its input so we can prove it saw epoch seconds
        def prediction(seconds):
            return seconds + 1

        times = [datetime.datetime(2020, 1, 1), datetime.datetime(2022, 3, 10)]

        # WHEN
        result = stock_analysis._predict_values(prediction, times)

        # THEN
        self.assertEqual(result, [moment.timestamp() + 1 for moment in times])

    def test_zone_analysis_success(self):
        """_zone_analysis returns the predict_low fragment and the up/down ratio."""
        # WHEN high > low and prices are numeric
        fragment, ratio = stock_analysis._zone_analysis(100.0, 40.0, 60.0)

        # THEN
        self.assertIsInstance(fragment, str)
        self.assertTrue(fragment.startswith("```Lower"))
        self.assertAlmostEqual(ratio, (100.0 - 60.0) / (60.0 - 40.0))

    def test_zone_analysis_type_error_returns_zero_ratio(self):
        """A None projected_low makes predict_low raise TypeError -> error fragment, 0 ratio."""
        # WHEN
        fragment, ratio = stock_analysis._zone_analysis(100.0, None, 60.0)

        # THEN
        self.assertIsInstance(fragment, str)
        self.assertTrue(fragment.startswith("```"))
        self.assertEqual(ratio, 0)

    def test_zone_analysis_assertion_error_returns_nan(self):
        """When high <= low predict_low asserts -> NaN fragment, 0 ratio."""
        # WHEN forcast high is below the projected low
        fragment, ratio = stock_analysis._zone_analysis(40.0, 100.0, 60.0)

        # THEN
        self.assertEqual(fragment, "```NaN```")
        self.assertEqual(ratio, 0)


if __name__ == "__main__":
    unittest.main()
