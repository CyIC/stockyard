<!-- Improved compatibility of back to top link: See: https://github.com/othneildrew/Best-README-Template/pull/73 -->
<a name="readme-top"></a>

<!-- PROJECT SHIELDS -->
<!--
*** I'm using markdown "reference style" links for readability.
*** Reference links are enclosed in brackets [ ] instead of parentheses ( ).
*** See the bottom of this document for the declaration of the reference variables
*** for contributors-url, forks-url, etc. This is an optional, concise syntax you may use.
*** https://www.markdownguide.org/basic-syntax/#reference-style-links
-->
[![Linting: flake8][lint-flake8-shield]][flake8-url]
[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![Apache License][license-shield]][license-url]
[![Python: 3.13][python-shield]][python-url]
[![OSS Lifecycle][oss-shield]][oss-url]

<!-- PROJECT LOGO -->
<br />
<div align="center">
    <a href="https://github.com/CyIC/stockyard">
        <img src="images/logo.png" alt="Logo" width="80" height="80">
    </a>

<h3 align="center">Stockyard v1.0.0</h3>

  <p align="center">
    Stock Selection Guide research for the Cypress Investment Club, from the command line or Discord
    <br />
    <a href="docs/design/v1.md"><strong>Explore the docs »</strong></a>
    <br />
    <br />
    <a href="https://github.com/CyIC/stockyard/issues">Report Bug</a>
    ·
    <a href="https://github.com/CyIC/stockyard/issues">Request Feature</a>
  </p>
</div>

<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
      <ul>
        <li><a href="#built-with">Built With</a></li>
        <li><a href="#folder-structure">Folder Structure</a></li>
      </ul>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Installation</a></li>
      </ul>
    </li>
    <li>
      <a href="#usage">Usage</a>
      <ul>
        <li><a href="#command-line">Command line</a></li>
        <li><a href="#discord-warren">Discord (Warren)</a></li>
      </ul>
    </li>
    <li><a href="#calculation-notes">Calculation Notes</a></li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#acknowledgments">Acknowledgments</a></li>
  </ol>
</details>




<!-- ABOUT THE PROJECT -->
## About The Project

Stockyard builds the sections of a BetterInvesting-style **Stock Selection Guide** (SSG) for any ticker
from Yahoo Finance data: past sales and EPS, the record of stock prices, P/E, payout and yield, trends,
cash position, revenue and earnings growth, and the risk/reward evaluation with buy/maybe/sell zones.

One core library, two front ends:
* **`stockyard`**, a command-line tool for quick lookups in a terminal and for automation. `--json` gives
  AI agents and scripts a versioned, machine-readable report without spending LLM tokens on scraping.
  See [docs/agents.md](docs/agents.md).
* **Warren**, the club's Discord bot, which posts the same report and charts in a channel.

Every figure is computed for fiscal years aligned on the company's own period-ends, as of a stated New York
date. Missing data never becomes a silent zero or a crash: the figure is `null` (`n/a` in text) with a
warning saying what was needed.

Stockyard is research and education for the club, not investment advice.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

### Built With

* [Python 3.13](https://www.python.org/)
* [yfinance](https://github.com/ranaroussi/yfinance)
* [pandas](https://pandas.pydata.org/) and [NumPy](https://numpy.org/)
* [matplotlib](https://matplotlib.org/)
* [discord.py][discordpy-url]

<p align="right">(<a href="#readme-top">back to top</a>)</p>

### Folder Structure
```
.
├-- .do/                          # DigitalOcean deployment config
├-- .github/workflows/            # GitHub Actions
├-- docs/
|   ├-- adr/                      # architecture decision records
|   └-- design/                   # v1 design and implementation plan
├-- scripts/
|   ├-- record_raw_fixtures.py    # record raw yfinance responses as test fixtures
|   └-- build-*.sh / .bat         # Docker build helpers
├-- src/
|   ├-- stockyard/
|   |   ├-- data/                 # fetch (yfinance), same-day cache, ticker validation, fiscal-year alignment
|   |   ├-- research/             # Stock Selection Guide definitions, sections and build_report
|   |   ├-- render/               # text, Discord, JSON and chart renderers
|   |   ├-- bot/                  # Warren, the Discord bot (console script `warren`)
|   |   ├-- cli.py                # the command line (console script `stockyard`)
|   |   ├-- clock.py              # the single wall-clock read (New York date)
|   |   ├-- config.py             # settings from environment variables
|   |   ├-- logging_config.py     # logging to stderr
|   |   ├-- report_warning.py     # structured warnings
|   |   └-- utilities.py          # data-directory path, Discord token
|   └-- tests/                    # pytest suite; fixtures/ holds recorded yfinance responses
├-- .env.template                 # environment variables (copy to .env)
├-- CHANGELOG.md                  # human-readable record of version changes
├-- CONTEXT.md                    # glossary of domain terms
├-- CONTRIBUTING.md               # contribution guidelines
├-- DOCKER.md                     # container build and deployment
├-- Dockerfile, docker-compose*.yml
├-- pyproject.toml / poetry.lock  # package metadata and locked dependencies
└-- tox.ini                       # test, lint and type-check environments
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- GETTING STARTED -->
## Getting Started

To build a development version of this software, refer to the [CONTRIBUTING.md](./CONTRIBUTING.md) file for development
instructions.

### Prerequisites 

You need [Python][python-url] 3.13 and [Poetry][poetry-url]; Poetry installs everything else. The CLI needs nothing
more. Warren also needs a Discord bot token. In production Warren runs in a container, self-hosted with Docker
Compose or on DigitalOcean App Platform (`.do/`); see [DOCKER.md](./DOCKER.md).

### Installation

1. Clone the repo
   ```sh
   git clone https://github.com/CyIC/stockyard.git
   cd stockyard
   ```
2. Install Python dependencies
   ```sh
   poetry install
   ```
3. Create your configuration from the template and fill in your values (see [Configuration](#configuration))
   ```sh
   cp .env.template .env
   ```

Market data comes from Yahoo Finance via yfinance, which needs no API key.

### Configuration

Stockyard is configured with environment variables. [`.env.template`](./.env.template) lists them all;
copy it to `.env`. Docker Compose reads `.env` automatically. For local runs, set the variables in your
shell, e.g. `export LOGGING_LEVEL=DEBUG` (bash) or `$env:LOGGING_LEVEL = "DEBUG"` (PowerShell).

| Variable | Used by | Default | Purpose |
|---|---|---|---|
| `STOCKYARD_DATA_DIR` | bot, CLI | current directory (`/app/data` in Docker) | Writable directory for the same-day market-data cache (`cache/<TICKER>.json`). Charts go to a per-request temporary directory (bot) or `--charts DIR` (CLI). |
| `LOGGING_LEVEL` | bot, CLI | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` or `CRITICAL`. Logs go to stderr, so CLI output on stdout stays clean. |
| `DISCORD_TOKEN` | bot | — | The Discord bot token. |
| `DISCORD_TOKEN_FILE` | bot | — | Path to a file holding the token (e.g. a Docker/Swarm secret at `/run/secrets/discord_token`). Used when `DISCORD_TOKEN` is not set. |

The bot resolves its token from `DISCORD_TOKEN`, then `DISCORD_TOKEN_FILE`, then a `[discord] token` entry in
a local `bot_config.ini`; if none is found it exits with a message saying so. The CLI needs no token.

**Upgrading from Warren Bot 0.1:** `WARREN_DATA_DIR` is now `STOCKYARD_DATA_DIR`, and `LOGGING` is now
`LOGGING_LEVEL`. The old names are not read. `DEBUG_MODE`, `DISCORD_APP_ID`, `DISCORD_PUBLIC_KEY` and
`FRED_KEY` remain in the template for deployment tooling but are not read by stockyard v1.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- USAGE EXAMPLES -->

## Usage

### Command line

```sh
stockyard report MSFT                 # every section, as text
stockyard past-eps MSFT               # one section
stockyard report MSFT --json          # stockyard.report/1 JSON for scripts and agents
stockyard trend MSFT --charts charts/ # also write PNG charts into charts/
stockyard --help
```

Run it as `poetry run stockyard ...` or `python -m stockyard ...` if the script isn't on your PATH.

| Command | Section |
|---|---|
| `report` | all of the below |
| `fundamentals` | aligned fiscal years: revenue, net income, reported EPS; current-year progress |
| `past-sales` | past sales records, growth and CAGR |
| `past-eps` | past EPS, growth and CAGR |
| `record` | record of stock: fiscal-year high/low, P/E at high and low, payout, high yield |
| `trend` | quarterly revenue and EPS, monthly high/low prices |
| `cash` | cash position: cash, debt and working capital, two fiscal years and the latest quarter |
| `revenue-growth` | revenue growth, dividends, current P/E and Lynch's dividend-adjusted ratio |
| `earnings-growth` | net income year over year |
| `risk-reward` | forecast high, low estimates, zones, up/down ratios and price target |

Options for every command: `--json`, `--charts DIR` (writes `trend_*.png` / `risk_*.png` for the sections that
have charts), `--no-cache` (skip the same-day cache), `-v` (debug logging on stderr).

Only the result is written to stdout; logs and errors go to stderr. Exit codes: `0` success (warnings may be
present), `1` internal error, `2` usage error or invalid ticker, `3` no data for the ticker, `4` Yahoo Finance
failed. The JSON contract is described in [docs/agents.md](docs/agents.md).

Example (`stockyard past-eps IBM`, recorded data):

```
IBM — Stock Selection Guide as of 2026-11-11 (yfinance)

== Past EPS ==
FY2021                 $9.97
FY2022                 $9.12
FY2023                 $9.61
FY2024                $10.33
FY2025                $11.57

Recent two-year average (FY2024–FY2025)                $10.95
Oldest two-year average (FY2021–FY2022)                 $9.55
% increase in earnings                                 14.72%
Compound annual growth (FY2021→FY2025)                  3.79%
```

### Discord (Warren)

```sh
poetry run warren        # or: python -m stockyard.bot
```

| Command | What it does |
|---|---|
| `!stock_report TICKER` (or `!sr TICKER`) | posts the full report with trend and risk/reward charts |
| `!help` | lists the commands |

Warren builds the report off Discord's event loop, so one slow lookup doesn't stall the bot.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Calculation Notes

The full definitions, minimums and edge cases are in [design §5.2, §5.6 and §5.7](docs/design/v1.md); terms
are in [CONTEXT.md](./CONTEXT.md). In brief:

**Fiscal years.** Rows are the company's annual statement period-ends, labelled `FY####`. Quarterly EPS
announcements are attributed to the quarter they report, and a year whose four quarters are all present is
a *Complete Fiscal Year*. EPS-based figures use complete years only; revenue and income use every annual
statement. Each year's prices come from its own window, the trading days after the prior period-end up to
its own. With fewer than 4 complete fiscal years (recent IPOs) the history is *insufficient*: the EPS
growth figures that need more years and the risk/reward forecast are `n/a`, with warnings saying why.

| Figure | How it is calculated |
|---|---|
| CAGR | `(last / first)^(1/(n−1)) − 1` over n years; `n/a` if the first year is ≤ 0 or the last is < 0 |
| % increase (pair) | average of the two most recent years versus the two oldest years |
| TTM EPS | sum of the last four reported quarterly EPS |
| Current P/E | present price ÷ TTM EPS; `n/a` if TTM EPS ≤ 0 |
| P/E at high / low | fiscal-year high ÷ that year's EPS, fiscal-year low ÷ EPS; years with EPS ≤ 0 are left out of the averages |
| % payout, high yield | dividends per share ÷ EPS; dividends per share ÷ fiscal-year low |
| Dividends per share | the dividends actually paid per share in the period, from the price history (fiscal-year window, or the last 365 days for TTM) |
| Dividend yield | TTM dividends per share ÷ present price |
| Forecast high | average P/E at high × TTM EPS projected five years ahead by a straight-line fit. Labelled "Forecast high (avg PE × projected EPS)". |
| Low estimates | four, each shown on its own: the five-year straight-line trend of daily lows; the average of fiscal-year lows; the lowest daily low in five years; and dividend support (TTM dividends ÷ highest fiscal-year high yield) |
| Zones | the range from a low estimate to the forecast high, split **25 % buy / 50 % maybe / 25 % sell**; the present price is placed in one of them |
| Up/down ratio | `(forecast high − price) ÷ (price − low)`; the top of the buy zone is 3 to 1 |
| Price target | forecast high ÷ present price − 1 |
| Cash position | total cash = cash + short-term investments; net cash = total cash − long-term debt; working capital = current assets − current liabilities. Items Yahoo omits (often a company with no debt) count as zero, with a warning. |

**Lynch's dividend-adjusted ratio.** The Revenue Growth section reports **Peter Lynch's dividend-adjusted
PEG ratio**, from *One Up on Wall Street* (1989):

```
(EPS growth % + dividend yield %) ÷ current P/E
```

with both percentages as whole numbers and EPS growth taken as the EPS CAGR. For example, 12 % growth, a 2 %
yield and a P/E of 20 give (12 + 2) ÷ 20 = 0.7. Lynch's reading: below 1 is poor, 1.5 is okay, and 2 or more is
what you're looking for. It appears in the Revenue Growth section of the text and Discord reports (labelled
"Lynch dividend-adjusted ratio") and as `lynch_ratio` in the JSON. It replaces the 0.1 formula, which mixed
units.

All prices are split-adjusted but not dividend-adjusted, so historical highs and lows match what was quoted
at the time, apart from splits.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- CONTRIBUTING -->
## Contributing

Please read [CONTRIBUTING.md](./CONTRIBUTING.md) for details on our code of conduct, installing, developing, and the 
process for submitting pull requests to us.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## License

This project uses libraries and software listed in the [Built With](README.md#built-with) and 
[Acknowledgements](README.md#acknowledgments) sections. See the [LICENSE.md](LICENSE.md) file for details.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Acknowledgments

* [Lance James](https://github.com/lancejames221b) and his Hal DiscordBot for the idea and initial structure.
* [bump-my-version](https://github.com/callowayproject/bump-my-version)
* [Poetry][poetry-url]
* [GitHub Pages](https://pages.github.com)
* [Font Awesome](https://fontawesome.com)
* [Img Shields](https://shields.io)
* [Best README](https://github.com/othneildrew/Best-README-Template/tree/master)

<p align="right">(<a href="#readme-top">back to top</a>)</p>


<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->
[contributors-shield]: https://img.shields.io/github/contributors/CyIC/stockyard.svg?style=for-the-badge
[contributors-url]: https://github.com/CyIC/stockyard/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/CyIC/stockyard.svg?style=for-the-badge
[forks-url]: https://github.com/CyIC/stockyard/network/members
[stars-shield]: https://img.shields.io/github/stars/CyIC/stockyard.svg?style=for-the-badge
[stars-url]: https://github.com/CyIC/stockyard/stargazers
[issues-shield]: https://img.shields.io/github/issues/CyIC/stockyard.svg?style=for-the-badge
[issues-url]: https://github.com/CyIC/stockyard/issues
[license-shield]: https://img.shields.io/github/license/CyIC/stockyard.svg?style=for-the-badge
[license-url]: https://github.com/CyIC/stockyard/blob/main/LICENSE.md
[lint-flake8-shield]: https://img.shields.io/badge/linting-flake8-yellowgreen?style=for-the-badge
[flake8-url]: https://flake8.pycqa.org/en/latest/
[discordpy-url]: https://discordpy.readthedocs.io/en/stable/
[python-shield]: https://img.shields.io/python/required-version-toml?style=for-the-badge&tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2FCyIC%2Fstockyard%2Fblob%2Fmain%2Fpyproject.toml
[python-url]: https://www.python.org/
[poetry-url]: https://python-poetry.org
[oss-shield]: https://img.shields.io/osslifecycle/CyIC/stockyard?style=for-the-badge
[oss-url]: https://github.com/Netflix/osstracker/tree/master