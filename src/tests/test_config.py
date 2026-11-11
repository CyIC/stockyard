# -*- coding: utf-8 -*-
"""Tests for stockyard.config.Settings."""
from pathlib import Path

import pytest

from stockyard.config import Settings


def test_data_dir_defaults_to_current_directory():
    assert Settings.from_env({}).data_dir == Path(".")


def test_data_dir_from_stockyard_data_dir():
    assert Settings.from_env({"STOCKYARD_DATA_DIR": "/srv/stockyard"}).data_dir == Path("/srv/stockyard")


def test_legacy_warren_data_dir_is_not_read():
    """Design §15.6: renamed without a fallback."""
    assert Settings.from_env({"WARREN_DATA_DIR": "/old"}).data_dir == Path(".")


def test_settings_are_immutable():
    settings = Settings.from_env({})
    with pytest.raises(AttributeError):
        settings.data_dir = Path("/elsewhere")
