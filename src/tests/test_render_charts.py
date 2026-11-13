# -*- coding: utf-8 -*-
"""Chart rendering: OO Figure API only, files only where asked, safe from threads (design §6)."""
import concurrent.futures
import sys

from stockyard.render import charts
from stockyard.research.models import RiskRewardResult, TrendResult

PNG = b"\x89PNG\r\n\x1a\n"

TREND = TrendResult(
    quarterly_revenue=(("2026-03-31", 5.0), ("2026-06-30", 6.0)),
    quarterly_eps=(("2026-04-20", 1.0), ("2026-07-20", 1.1)),
    monthly_prices=(("2026-07", 10.0, 5.0, None, None), ("2026-08", 12.0, 6.0, None, None)),
    warnings=(),
)


def test_trend_charts_are_pngs_in_the_given_directory_only(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    out = tmp_path / "charts"
    out.mkdir()

    paths = charts.trend(TREND, out)

    assert sorted(p.name for p in paths) == ["trend_high_low.png", "trend_revenue_eps.png"]
    assert all(p.parent == out and p.read_bytes().startswith(PNG) for p in paths)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["charts"]


def test_a_chart_without_data_is_skipped(tmp_path):
    empty = TrendResult(quarterly_revenue=(), quarterly_eps=(), monthly_prices=TREND.monthly_prices, warnings=())
    assert [p.name for p in charts.trend(empty, tmp_path)] == ["trend_high_low.png"]


def test_rendering_from_many_threads_is_safe_and_leaves_no_pyplot_figures(tmp_path):
    def render(index):
        directory = tmp_path / str(index)
        directory.mkdir()
        return charts.trend(TREND, directory)

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(render, range(16)))

    assert all(len(paths) == 2 and all(p.stat().st_size > 1000 for p in paths) for paths in results)
    if "matplotlib.pyplot" in sys.modules:
        assert sys.modules["matplotlib.pyplot"].get_fignums() == []


RISK = RiskRewardResult(
    present_price=35.0,
    average_pe_high=12.5,
    projected_eps=4.0,
    forecast_high=50.0,
    price_target_appreciation=0.43,
    lows=(),
    eps_points=(("2025-01-25", 4.0), ("2026-10-25", 4.2)),
    eps_forecast_line=(("2025-01-25", 4.0), ("2031-11-11", 5.0)),
    monthly_lows=(("2026-09", 30.0), ("2026-10", 31.0)),
    low_forecast_line=(("2021-11-15", 20.0), ("2031-11-11", 40.0)),
    warnings=(),
)


def test_risk_reward_charts(tmp_path):
    paths = charts.risk_reward(RISK, tmp_path)
    assert sorted(p.name for p in paths) == ["risk_eps_forecast.png", "risk_low_forecast.png"]
    assert all(p.read_bytes().startswith(PNG) for p in paths)
