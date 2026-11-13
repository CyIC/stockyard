# -*- coding: utf-8 -*-
"""The one place the wall clock is read: front ends turn it into an as_of date (design §5.3)."""
import datetime
from zoneinfo import ZoneInfo

NEW_YORK = ZoneInfo("America/New_York")


def new_york_today(now: datetime.datetime | None = None) -> datetime.date:
    """Today's calendar date on the US equity market's clock."""
    return (now or datetime.datetime.now(datetime.timezone.utc)).astimezone(NEW_YORK).date()
