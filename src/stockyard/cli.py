# -*- coding: utf-8 -*-
"""The stockyard command line (ADR-0003, design §8.1).

The result goes to stdout and nothing else does: text by default, ``--json`` for agents. Logs and plain-text
errors go to stderr. Exit codes: 0 ok, 1 internal error, 2 usage or invalid ticker, 3 no data, 4 upstream error.
"""
import argparse
import logging
import sys
from pathlib import Path

from stockyard import logging_config
from stockyard.clock import new_york_today
from stockyard.config import Settings
from stockyard.data.cache import Cache
from stockyard.data.errors import DataUnavailable, UpstreamError
from stockyard.data.snapshot import fetch_stock_data
from stockyard.data.tickers import InvalidTicker, validate_ticker
from stockyard.render import charts, text
from stockyard.render import json as json_render
from stockyard.research.report import SECTION_IDS, build_report

LOGGER = logging.getLogger(__name__)

COMMANDS = {  # command -> (section id, help)
    "fundamentals": ("fundamentals", "Fundamentals table"),
    "past-sales": ("past_sales", "Past sales records"),
    "past-eps": ("past_eps", "Past EPS"),
    "record": ("record_of_stock", "Record of stock prices, P/E, payout and yield"),
    "trend": ("trend", "Revenue, EPS and price trend"),
    "cash": ("cash_position", "Cash position"),
    "revenue-growth": ("revenue_growth", "Revenue growth (Lynch ratio)"),
    "earnings-growth": ("earnings_growth", "Earnings growth"),
    "risk-reward": ("risk_reward", "Evaluating risk and reward"),
}
TEXT = {name: getattr(text, name) for name in SECTION_IDS}
CHARTS = {"trend": charts.trend, "risk_reward": charts.risk_reward}
EXIT_CODES = {DataUnavailable: (3, "data_unavailable"), UpstreamError: (4, "upstream_error")}


def _parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("ticker", help="ticker symbol, e.g. MSFT")
    common.add_argument("--json", action="store_true", help="emit a stockyard.report/1 JSON document")
    common.add_argument("--charts", metavar="DIR", type=Path, help="write PNG charts into DIR")
    common.add_argument("--no-cache", action="store_true", help="always fetch fresh data")
    common.add_argument("-v", "--verbose", action="store_true", help="debug logging on stderr")

    parser = argparse.ArgumentParser(
        prog="stockyard",
        description="Stock Selection Guide research from yfinance.",
        epilog="Warren, the Discord bot, runs separately: set DISCORD_TOKEN, then run `warren` "
        "(or `python -m stockyard.bot`).",
    )
    commands = parser.add_subparsers(dest="command", required=True, metavar="command")
    commands.add_parser("report", parents=[common], help="every section")
    for command, (_, description) in COMMANDS.items():
        commands.add_parser(command, parents=[common], help=description)
    return parser


def _text(report, chart_paths) -> str:
    lines = [f"{report.ticker} — Stock Selection Guide as of {report.as_of.isoformat()} ({report.source})"]
    for name, result in report.sections.items():
        if result is None:
            lines += ["", f"== {name} =="] + [f"⚠ {w.message}" for w in report.warnings if w.section == name]
            continue
        rendered = TEXT[name](result)
        lines += ["", f"== {rendered.title} ==", rendered.body]
    general = [warning for warning in report.warnings if warning.section is None]
    if general:
        lines += ["", "== Warnings =="] + [f"⚠ {warning.message}" for warning in general]
    if chart_paths:
        lines += ["", "== Charts =="] + [str(path) for path in chart_paths]
    return "\n".join(lines)


def _fail(args, code: int, name: str, message: str) -> int:
    if args.json:
        print(json_render.dumps_error(name, message))
    else:
        print(f"stockyard: {message}", file=sys.stderr)
    return code


def _run(args) -> int:
    try:
        ticker = validate_ticker(args.ticker)
    except InvalidTicker as error:  # exit 2 is plain text even with --json (ADR-0003)
        print(f"stockyard: {error}", file=sys.stderr)
        return 2
    sections = list(SECTION_IDS) if args.command == "report" else [COMMANDS[args.command][0]]
    try:
        as_of = new_york_today()
        cache = None if args.no_cache else Cache(Settings.from_env().data_dir, today=as_of)
        report = build_report(fetch_stock_data(ticker, cache=cache), as_of, sections=sections)
        chart_paths = []
        if args.charts:
            args.charts.mkdir(parents=True, exist_ok=True)
            for name, draw in CHARTS.items():
                if report.sections.get(name) is not None:
                    chart_paths += draw(report.sections[name], args.charts)
    except (DataUnavailable, UpstreamError) as error:
        code, name = EXIT_CODES[type(error)]
        return _fail(args, code, name, str(error))
    except Exception as error:  # pylint: disable=broad-exception-caught  # exit 1, no traceback on stdout
        LOGGER.exception("internal error for %s", ticker)
        return _fail(args, 1, "internal_error", f"internal error: {error}")
    print(json_render.dumps(report) if args.json else _text(report, chart_paths))
    return 0


def main(argv=None) -> int:
    """Entry point for the ``stockyard`` command; returns the exit code."""
    try:
        args = _parser().parse_args(argv)
    except SystemExit as exit_:
        return exit_.code if isinstance(exit_.code, int) else 2
    logging_config.configure_logging()
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    return _run(args)
