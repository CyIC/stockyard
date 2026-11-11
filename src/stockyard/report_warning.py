# -*- coding: utf-8 -*-
"""A structured, non-fatal notice attached to a report or one of its figures (design §5.5)."""
from dataclasses import dataclass


@dataclass(frozen=True)
class ReportWarning:
    """``code`` is one of the documented warning codes; ``needed``/``available`` quantify history gaps."""

    code: str
    message: str
    section: str | None = None
    figure: str | None = None
    needed: int | None = None
    available: int | None = None
