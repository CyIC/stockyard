# -*- coding: utf-8 -*-
"""The stockyard CLI (ADR-0003, design §8.1). In-process, recorded data, no network."""
import json
import logging
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

from stockyard import cli
from stockyard.data.cache import Cache
from stockyard.data.errors import DataUnavailable, UpstreamError
from stockyard.research import report as report_module
from tests.fixture_replay import load_stock_data

COMMANDS = {
    "fundamentals": "fundamentals",
    "past-sales": "past_sales",
    "past-eps": "past_eps",
    "record": "record_of_stock",
    "trend": "trend",
    "cash": "cash_position",
    "revenue-growth": "revenue_growth",
    "earnings-growth": "earnings_growth",
    "risk-reward": "risk_reward",
}


@pytest.fixture(name="calls")
def _ibm(monkeypatch):
    data, as_of = load_stock_data("IBM")
    calls = []

    def fetch(ticker, cache=None):
        calls.append((ticker, cache))
        return data

    monkeypatch.setattr(cli, "fetch_stock_data", fetch)
    monkeypatch.setattr(cli, "new_york_today", lambda: as_of)
    monkeypatch.setattr(cli.logging_config, "configure_logging", lambda: None)
    return calls


def _run(capsys, *argv):
    code = cli.main(list(argv))
    out, err = capsys.readouterr()
    return code, out, err


@pytest.mark.usefixtures("calls")
def test_report_json_is_the_only_thing_on_stdout(capsys):
    code, out, _ = _run(capsys, "report", "ibm", "--json")

    document = json.loads(out)
    assert code == 0
    assert document["schema"] == "stockyard.report/1" and document["ticker"] == "IBM"
    assert tuple(document["sections"]) == tuple(COMMANDS.values())


@pytest.mark.usefixtures("calls")
@pytest.mark.parametrize(("command", "section"), COMMANDS.items())
def test_each_command_emits_exactly_its_section(capsys, command, section):
    code, out, _ = _run(capsys, command, "IBM", "--json")
    assert code == 0 and set(json.loads(out)["sections"]) == {section}


@pytest.mark.usefixtures("calls")
def test_text_is_the_default(capsys):
    code, out, _ = _run(capsys, "past-eps", "IBM")

    assert code == 0
    assert out.startswith("IBM — Stock Selection Guide as of 2026-11-11 (yfinance)")
    assert "== Past EPS ==" in out and "FY2025" in out and "== Past Sales Records ==" not in out


@pytest.mark.usefixtures("calls")
def test_report_text_has_every_section(capsys):
    _, out, _ = _run(capsys, "report", "IBM")
    for title in ("Fundamentals", "Past Sales Records", "Record of Stock", "Evaluating Risk & Reward"):
        assert f"== {title} ==" in out


@pytest.mark.usefixtures("calls")
def test_charts_are_written_to_the_given_directory_and_listed_in_text(capsys, tmp_path):
    code, out, _ = _run(capsys, "report", "IBM", "--charts", str(tmp_path))

    written = sorted(p.name for p in tmp_path.iterdir())
    assert code == 0
    assert written == ["risk_eps_forecast.png", "risk_low_forecast.png", "trend_high_low.png", "trend_revenue_eps.png"]
    assert all(str(tmp_path / name) in out for name in written)


@pytest.mark.usefixtures("calls")
def test_charts_follow_the_command(capsys, tmp_path):
    _run(capsys, "trend", "IBM", "--charts", str(tmp_path), "--json")
    assert sorted(p.name for p in tmp_path.iterdir()) == ["trend_high_low.png", "trend_revenue_eps.png"]


def test_cache_is_used_by_default_and_disabled_by_no_cache(capsys, calls, monkeypatch, tmp_path):
    monkeypatch.setenv("STOCKYARD_DATA_DIR", str(tmp_path))
    _run(capsys, "past-eps", "IBM")
    _run(capsys, "past-eps", "IBM", "--no-cache")

    (_, default_cache), (_, no_cache) = calls
    assert isinstance(default_cache, Cache) and no_cache is None


@pytest.mark.usefixtures("calls")
def test_an_invalid_ticker_exits_2(capsys):
    code, out, err = _run(capsys, "report", "../etc")
    assert code == 2 and out == "" and "not a valid ticker" in err

    code, out, err = _run(capsys, "report", "../etc", "--json")  # exit 2 is always plain text (ADR-0003)
    assert code == 2 and out == "" and "not a valid ticker" in err


@pytest.mark.parametrize(
    ("error", "code", "name"),
    [
        (DataUnavailable("none"), 3, "data_unavailable"),
        (UpstreamError("down"), 4, "upstream_error"),
        (RuntimeError("bug"), 1, "internal_error"),
    ],
)
def test_failures_map_to_exit_codes_and_json_errors(capsys, monkeypatch, error, code, name):
    def fetch(ticker, cache=None):
        raise error

    monkeypatch.setattr(cli, "fetch_stock_data", fetch)
    monkeypatch.setattr(cli.logging_config, "configure_logging", lambda: None)

    exit_code, out, _ = _run(capsys, "report", "IBM", "--json")
    assert exit_code == code
    assert json.loads(out) == {"schema": "stockyard.error/1", "code": name, "message": json.loads(out)["message"]}

    exit_code, out, err = _run(capsys, "report", "IBM")
    assert exit_code == code and out == "" and err


def test_usage_errors_exit_2_with_plain_text_on_stderr(capsys):
    code, out, err = _run(capsys, "report")
    assert code == 2 and out == "" and "usage:" in err


def test_python_m_stockyard_runs_the_cli():
    result = subprocess.run([sys.executable, "-m", "stockyard", "--help"], capture_output=True, text=True)
    assert result.returncode == 0 and "risk-reward" in result.stdout


def test_stockyard_console_script():
    root = Path(__file__).resolve().parents[2]
    scripts = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["tool"]["poetry"]["scripts"]
    assert scripts["stockyard"] == "stockyard.cli:main"


@pytest.mark.usefixtures("calls")
def test_verbose_turns_on_debug_logging(capsys, monkeypatch):
    root = logging.getLogger()
    monkeypatch.setattr(root, "level", logging.INFO)
    _run(capsys, "past-eps", "IBM", "-v")
    assert root.level == logging.DEBUG


@pytest.mark.usefixtures("calls")
def test_a_failed_section_shows_why_in_text(capsys, monkeypatch):
    def broken(*_):
        raise ValueError("boom")

    monkeypatch.setitem(report_module.SECTIONS, "past_eps", broken)
    code, out, _ = _run(capsys, "past-eps", "IBM")
    assert code == 0 and "== past_eps ==\n⚠ " in out and "boom" in out


@pytest.mark.usefixtures("calls")
def test_the_charts_directory_is_created(capsys, tmp_path):
    target = tmp_path / "new" / "dir"
    _run(capsys, "trend", "IBM", "--charts", str(target))
    assert (target / "trend_high_low.png").exists()


def test_report_level_warnings_are_listed_in_text(capsys, monkeypatch):
    data, as_of = load_stock_data("RDDT")
    monkeypatch.setattr(cli, "fetch_stock_data", lambda ticker, cache=None: data)
    monkeypatch.setattr(cli, "new_york_today", lambda: as_of)
    monkeypatch.setattr(cli.logging_config, "configure_logging", lambda: None)

    _, out, _ = _run(capsys, "past-eps", "RDDT")
    warnings = out.split("== Warnings ==\n", 1)[1]
    assert warnings.startswith("⚠ 2 complete fiscal years; 4 needed")
