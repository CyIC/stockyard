# -*- coding: utf-8 -*-
"""Chart images from section results (design §6).

Uses matplotlib's object-oriented Figure API with the Agg canvas, never the global pyplot state, so charts
can be drawn concurrently from worker threads. Files are written only into the directory the caller passes
(a per-request temporary directory in the bot, ``--charts DIR`` in the CLI).
"""
from pathlib import Path

import pandas as pd
from matplotlib.figure import Figure

from stockyard.research.models import RiskRewardResult, TrendResult


def _series(points) -> pd.Series:
    return pd.Series([value for _, value in points], index=pd.to_datetime([day for day, _ in points]))


def trend(result: TrendResult, directory: Path) -> list[Path]:
    """Revenue & EPS by quarter, and monthly highs and lows; a chart with no data is skipped."""
    directory = Path(directory)
    paths = []
    if result.quarterly_revenue or result.quarterly_eps:
        figure = Figure(figsize=(8, 4.5))
        revenue_axis = figure.add_subplot()
        revenue_axis.set_title("Revenue & EPS")
        revenue_axis.set_xlabel("Date")
        revenue_axis.set_ylabel("Revenue", color="tab:red")
        if result.quarterly_revenue:
            revenue_axis.plot(_series(result.quarterly_revenue), color="tab:red")
        eps_axis = revenue_axis.twinx()
        eps_axis.set_ylabel("EPS", color="tab:blue")
        if result.quarterly_eps:
            eps_axis.plot(_series(result.quarterly_eps), color="tab:blue")
        paths.append(_save(figure, directory / "trend_revenue_eps.png"))
    if result.monthly_prices:
        months = pd.PeriodIndex([row[0] for row in result.monthly_prices], freq="M").to_timestamp()
        figure = Figure(figsize=(8, 4.5))
        axis = figure.add_subplot()
        axis.set_title("Stock High & Low")
        axis.set_xlabel("Date")
        axis.set_ylabel("USD")
        for column, label in ((1, "high"), (2, "low"), (3, "avg high (4m)"), (4, "avg low (4m)")):
            axis.plot(months, [row[column] for row in result.monthly_prices], label=label)
        axis.legend()
        paths.append(_save(figure, directory / "trend_high_low.png"))
    return paths


def risk_reward(result: RiskRewardResult, directory: Path) -> list[Path]:
    """TTM EPS with its five-year projection, and monthly lows with their regression line."""
    directory = Path(directory)
    paths = []
    for points, line, name, title, label in (
        (result.eps_points, result.eps_forecast_line, "risk_eps_forecast.png", "TTM EPS projection", "TTM EPS"),
        (result.monthly_lows, result.low_forecast_line, "risk_low_forecast.png", "Low price projection", "USD"),
    ):
        if not points:
            continue
        figure = Figure(figsize=(8, 4.5))
        axis = figure.add_subplot()
        axis.set_title(title)
        axis.set_ylabel(label)
        series = _series(points) if len(points[0][0]) > 7 else _monthly(points)
        axis.plot(series, label="actual")
        if line:
            axis.plot(_series(line), linestyle="--", label="projection")
        axis.legend()
        paths.append(_save(figure, directory / name))
    return paths


def _monthly(points) -> pd.Series:
    return pd.Series(
        [value for _, value in points], index=pd.PeriodIndex([month for month, _ in points], freq="M").to_timestamp()
    )


def _save(figure: Figure, path: Path) -> Path:
    figure.savefig(path, format="png")
    return path
