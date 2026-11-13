# -*- coding: utf-8 -*-
"""Front ends compute as_of as the New York calendar date (design §5.3, §7)."""
import datetime

from stockyard.clock import new_york_today


def test_late_evening_utc_is_still_the_previous_day_in_new_york():
    utc = datetime.datetime(2026, 11, 12, 3, 0, tzinfo=datetime.timezone.utc)  # 22:00 on the 11th in New York
    assert new_york_today(utc) == datetime.date(2026, 11, 11)


def test_daylight_saving_offset_is_respected():
    utc = datetime.datetime(2026, 7, 1, 3, 30, tzinfo=datetime.timezone.utc)  # 23:30 on 30 June (EDT, UTC-4)
    assert new_york_today(utc) == datetime.date(2026, 6, 30)


def test_defaults_to_now():
    assert isinstance(new_york_today(), datetime.date)
