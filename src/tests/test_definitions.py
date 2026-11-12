# -*- coding: utf-8 -*-
"""Financial definitions (design §5.7). Expected values are computed by hand from the definition."""
import pytest

from stockyard.research import definitions as d

# --- growth ----------------------------------------------------------------------------------


def test_cagr_spans_one_fewer_period_than_values():
    # four fiscal years span three periods: 100 * 1.1^3 = 133.1
    assert d.cagr(100, 133.1, periods=3) == pytest.approx(0.10)


@pytest.mark.parametrize(("first", "last", "periods"), [(0, 10, 3), (-5, 10, 3), (10, -1, 3), (10, 20, 0)])
def test_cagr_is_undefined_for_non_positive_base_negative_end_or_no_periods(first, last, periods):
    assert d.cagr(first, last, periods) is None


def test_cagr_of_a_total_loss_is_minus_one():
    assert d.cagr(10, 0, periods=2) == pytest.approx(-1.0)


def test_pair_increase_compares_the_mean_of_the_last_two_with_the_first_two():
    # first pair mean 10, last pair mean 15 -> +50 %
    assert d.pair_increase([9, 11, 13, 14, 16]) == pytest.approx(0.5)


def test_pair_increase_needs_four_values_and_a_positive_base():
    assert d.pair_increase([1, 2, 3]) is None
    assert d.pair_increase([-1, 0, 3, 4]) is None


# --- earnings and valuation ------------------------------------------------------------------


def test_ttm_eps_sums_the_last_four_quarters():
    assert d.ttm_eps([0.5, 1.0, 1.1, 1.2, 1.3]) == pytest.approx(4.6)


def test_ttm_eps_needs_four_quarters():
    assert d.ttm_eps([1.0, 1.0, 1.0]) is None


def test_pe_is_price_over_eps_and_undefined_for_non_positive_eps():
    assert d.pe(150, 7.5) == pytest.approx(20)
    assert d.pe(150, 0) is None
    assert d.pe(150, -2) is None


def test_payout_and_high_yield():
    assert d.payout(dividends_per_share=2.0, eps=5.0) == pytest.approx(0.4)
    assert d.payout(2.0, 0) is None
    assert d.payout(2.0, None) is None
    assert d.high_yield(dividends_per_share=2.0, low=40.0) == pytest.approx(0.05)
    assert d.high_yield(2.0, 0) is None


def test_dividend_yield_is_ttm_dividends_over_price():
    assert d.dividend_yield(ttm_dividends_per_share=3.0, price=150.0) == pytest.approx(0.02)
    assert d.dividend_yield(0.0, 150.0) == 0.0
    assert d.dividend_yield(3.0, 0) is None


def test_appreciation_is_relative_to_present_price_and_negative_above_target():
    assert d.appreciation(target=150, price=100) == pytest.approx(0.5)
    assert d.appreciation(target=90, price=100) == pytest.approx(-0.1)


# --- Lynch ratio (D15) -----------------------------------------------------------------------


def test_lynch_ratio_matches_lynchs_worked_example():
    """12 % EPS growth, 2 % yield, P/E 20 -> (12 + 2) / 20 = 0.7."""
    assert d.lynch_ratio(eps_growth=0.12, dividend_yield=0.02, pe=20) == pytest.approx(0.7)


def test_lynch_ratio_uses_whole_number_percentages_not_fractions():
    """The units trap: (0.12 + 0.02) / 20 = 0.007 would be off by 100x."""
    assert d.lynch_ratio(0.12, 0.02, 20) != pytest.approx(0.007)


@pytest.mark.parametrize(
    ("growth", "dividend", "pe"), [(None, 0.02, 20), (0.12, None, 20), (0.12, 0.02, None), (0.12, 0.02, 0)]
)
def test_lynch_ratio_is_undefined_when_an_input_is_missing(growth, dividend, pe):
    assert d.lynch_ratio(growth, dividend, pe) is None


# --- risk & reward ---------------------------------------------------------------------------


def test_up_down_ratio():
    # high 160, price 100, low 80: (160 - 100) / (100 - 80) = 3
    assert d.up_down_ratio(high=160, price=100, low=80) == pytest.approx(3.0)


@pytest.mark.parametrize("price", [80, 70, 160, 170])
def test_up_down_ratio_is_undefined_at_or_beyond_the_range(price):
    assert d.up_down_ratio(high=160, price=price, low=80) is None


def test_zones_split_the_range_25_50_25():
    zones = d.zones(low=80, high=160)
    assert zones.buy == (80, 100)
    assert zones.maybe == (100, 140)
    assert zones.sell == (140, 160)


def test_zones_are_undefined_when_the_low_is_not_below_the_high():
    assert d.zones(low=160, high=160) is None
    assert d.zones(low=170, high=160) is None


@pytest.mark.parametrize(
    ("price", "position"),
    [
        (79, "below_range"),
        (80, "buy"),
        (100, "buy"),
        (101, "maybe"),
        (139, "maybe"),
        (140, "sell"),
        (160, "sell"),
        (161, "above_range"),
    ],
)
def test_zone_position(price, position):
    assert d.zones(low=80, high=160).position(price) == position


def test_top_of_the_buy_zone_is_exactly_three_to_one():
    """D14: the zones and the 3-to-1 rule never contradict each other."""
    zones = d.zones(low=80, high=160)
    assert d.up_down_ratio(high=160, price=zones.buy[1], low=80) == pytest.approx(3.0)
