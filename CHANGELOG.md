# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project 
adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).


## [Unreleased]

### Added
    * Release pipeline: publishing a GitHub release tests, builds `ghcr.io/cyic/stockyard:<tag>` and deploys
      that image to DigitalOcean App Platform as the `warren` worker

### Changed
    * `.do/app.yml` runs the CI-built image by digest instead of building on DigitalOcean on every push to `main`

## [1.0.0] - 2026-11-13

Version 1.0 renames the project to **Stockyard** (the Discord bot keeps the name Warren) and rebuilds it as a
library with two front ends. See `docs/design/v1.md` for the design and decision log.

### Added
    * `stockyard` command line: `report` plus one command per Stock Selection Guide section, text by default,
      `--json` (`stockyard.report/1`), `--charts DIR`, `--no-cache`, exit codes 0-4 (ADR-0003)
    * `docs/agents.md`: how AI agents and scripts call the CLI and read its JSON
    * Fundamentals section: aligned fiscal years with revenue, net income and reported EPS
    * Lynch's dividend-adjusted ratio in Revenue Growth (D15)
    * Structured warnings on every report; missing figures are `null`/`n/a` with a reason instead of errors
    * Same-day JSON cache of Yahoo Finance responses in `$STOCKYARD_DATA_DIR/cache/`
    * Recorded IBM, MSFT and RDDT fixtures; tests never touch the network
    * Architecture decision records in `docs/adr/` and a glossary in `CONTEXT.md`
    * Add [OSS metadata](https://github.com/Netflix/osstracker/tree/master)

### Changed
    * Package renamed `warren_bot` -> `stockyard`; the bot runs with `warren` or `python -m stockyard.bot`,
      and `python -m stockyard` runs the CLI (ADR-0005)
    * Market data from yfinance instead of Alpha Vantage; no API key needed
    * Dependencies refreshed for Python 3.13: numpy 2.5, pandas 2.3, matplotlib 3.11, discord.py 2.7
    * Text and Discord reports show dollar amounts of $1M or more in whole millions (`$13,587M`, halves rounded
      up); smaller amounts, per-share figures and share counts are unchanged, and JSON keeps full values
    * Negative per-share figures read `-$43.14`; Cash Position tables head their label column `LINE ITEM`
    * Figures are aligned on each company's fiscal-year period-ends (ADR-0001); rows are labelled `FY####`
    * History threshold is 4 complete fiscal years (D17); recent IPOs get partial reports instead of errors
    * Zones are 25 / 50 / 25 (D14)
    * Dividends per share come from the dividends actually paid, not cash flow / shares outstanding
    * "Linear Regression of Highs" is relabelled "Forecast high (avg PE × projected EPS)", which is what it computes
    * Environment variables: `WARREN_DATA_DIR` -> `STOCKYARD_DATA_DIR`, `LOGGING` -> `LOGGING_LEVEL`
    * Logs are JSON on stderr
    * CI runs tox on GitHub Actions; CodeQL scans Python (D21)
    * DigitalOcean App Platform runs Warren as a worker from the Dockerfile (D22)
    * Moved Logging control to seperate file
    * Fix linting formatting errors
    * Move bumpversion rules to pyproject.toml
    * Updated README.md

### Fixed
    (0.1 defects, design §16)
    * "Div yield" showed dividends per share; it is now TTM dividends per share / price
    * The Revenue Growth ratio mixed units (replaced by Lynch's ratio)
    * Price figures used calendar years instead of each company's fiscal-year windows
    * Prices were dividend-adjusted, understating historical highs, lows and P/Es
    * The average low averaged ~1,250 daily lows instead of fiscal-year lows
    * The latest quarter was promoted to a fake `YYYY-12-31` annual row
    * A fallback reported net income as EPS
    * Undefined CAGR, P/E and up/down ratios for non-positive inputs are now `null` with a warning
    * The second "Net cash per share" in Cash Position is relabelled "Working capital per share"
    * Concurrent `!sr` requests overwrote each other's charts
    * Reports blocked the Discord event loop
    * The compose healthcheck called a function that did not exist
    * CI linted a non-existent `setup.py` and did not run tox
    * Quarter attribution no longer depends on the ~5 quarters yfinance returns
    * Ticker input is validated before it reaches file paths or Yahoo Finance
    * `poetry install` failed on Python 3.13: the lock pinned numpy, pandas, matplotlib and seven other
      packages to versions with no 3.13 wheels
    * Every lookup failed with "Missing optional dependency 'lxml'": yfinance needs lxml for earnings dates but
      does not declare it, and v1 had removed the package that used to pull it in; it is now a direct dependency

### Removed
    * Club portfolio tracking and `!club_report` / `!cr` (to be rebuilt in a separate `stockyard.club`)
    * `!graham_value` (returns in v1.1), `!bug` and `!terms_of_use`
    * Alpha Vantage integration, PDF/HTML report generation, `prettytable`, `scipy`, `jinja2`, `mplfinance`,
      `xhtml2pdf`
    * GitLab CI

### Security
    * The Discord token is read at start-up from `DISCORD_TOKEN` or `DISCORD_TOKEN_FILE`, never at import
    * Cache files are JSON written atomically, never pickle

## [0.1.0] - 2023-07-19

### Added
    * Add Python build to Github actions
    * Add Digital Ocean App deployment scripts

### Changed
    * Updated README
    * Rename LICENSE to LICENSE.md for clarity
    * Update bumpversion to remove tag signing for Github actions automation
    * Update Requirements to remove unneeded packages
    * Fix CHANGELOG
    * Move bumpversion from build.yml to own action


### Fixed
    * Setup pyproject.toml to allow Python 3.10

### Deprecated

### Removed

### Security

## [0.0.2] - 2023-07-19

### Added
    * Add initial Stock analysis function
    * Add initial portfolio analysis function
    * Add initial Alphavantage functionality
    * Add Quant analysis utilities
    * Add general utilities
    * Add CodeQL check to Github Actions

### Changed

### Fixed

### Deprecated

### Removed

### Security
