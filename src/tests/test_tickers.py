# -*- coding: utf-8 -*-
"""Tests for ticker validation, the trust boundary for user-supplied symbols (design §5.1, §7)."""
import pytest

from stockyard.data.tickers import InvalidTicker, validate_ticker


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("MSFT", "MSFT"),
        ("msft", "MSFT"),
        ("  ibm ", "IBM"),
        ("BRK.B", "BRK.B"),
        ("BRK-B", "BRK-B"),
        ("^GSPC", "^GSPC"),
        ("EURUSD=X", "EURUSD=X"),
        ("RY.TO", "RY.TO"),
        ("A" * 15, "A" * 15),
    ],
)
def test_accepts_and_normalises_real_symbols(raw, expected):
    assert validate_ticker(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        "../etc",
        "..",
        "MS FT",
        "MSFT/../x",
        "C:\\x",
        "A" * 16,
        ".MSFT",
        "-MSFT",
        "MSFT;rm",
        "MSF\x00T",
    ],
)
def test_rejects_anything_else(raw):
    with pytest.raises(InvalidTicker):
        validate_ticker(raw)


def test_invalid_ticker_is_a_value_error_naming_the_input():
    with pytest.raises(ValueError, match="not a valid ticker"):
        validate_ticker("../etc")
