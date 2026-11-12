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
[![Python: 3.11][python-shield]][python-url]
[![OSS Lifecycle][oss-shield]][oss-url]

<!-- PROJECT LOGO -->
<br />
<div align="center">
    <a href="https://github.com/CyIC/warren_bot">
        <img src="images/logo.png" alt="Logo" width="80" height="80">
    </a>

<h3 align="center">Warren Chatbot</h3>

  <p align="center">
    An Investment Club chatbot
    <br />
    <a href="https://github.com/github_username/repo_name"><strong>Explore the docs »</strong></a>
    <br />
    <br />
    <a href="https://github.com/github_username/repo_name">View Demo</a>
    ·
    <a href="https://github.com/CyIC/warren_bot/issues">Report Bug</a>
    ·
    <a href="https://github.com/CyIC/warren_bot/issues">Request Feature</a>
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
    <li><a href="#usage">Usage</a></li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#acknowledgments">Acknowledgments</a></li>
  </ol>
</details>




<!-- ABOUT THE PROJECT -->
## About The Project

[![Product Name Screen Shot][product-screenshot]](https://example.com)

Warren is a chatbot for investment clubs to analyze stocks, report on club fundamentals and more.

With Warren, you can:
* Conduct 5 year stock return analysis on publically traded companies.
* Track and report on club portfolio performance.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

### Built With

* [Python3.11](https://www.python.org/downloads/release/python-3110/)
* [Pandas](https://pandas.pydata.org/)
* [NumPy](https://numpy.org/)
* [PrettyTables](https://github.com/jazzband/prettytable)
* [requests](https://docs.python-requests.org/en/latest/index.html)
* [matplotlib](https://matplotlib.org/)
* [mplfinance](https://github.com/matplotlib/mplfinance)
* [Discord.py][discordpy-url]

<p align="right">(<a href="#readme-top">back to top</a>)</p>

### Folder Structure
```
.
├-- .do                                     # Digital Ocean Actions folder
├-- .github                                 # Github Actions folder
├-- src/                                
|   ├-- tests/                              # unit tests        
|   └-- warren_bot/                         # main module for application
|       ├-- resources/
|       ├-- __init__.py                     # module init
|       ├-- __main__.py                     # module main
|       ├-- alphavantage.py                 # file for alphavantage transactions
|       ├-- analysis.py                     # file for quant analysis methods
|       ├-- logging_config.py               # central module for controlling logging
|       ├-- portfolio_analysis.py           # file for portfolio analysis function
|       ├-- stock_analysis.py               # file for stock analysis function
|       └-- utilites.py                     # file for general utility functions
├-- .bumpversion.cfg                        # bumpversion configuration for version incrementation
├-- .gitignore                              # Typical gitignore file
├-- bot_config.template.info                # INI template for bot_config (remove .template for function)
├-- CHANGELOG.md                            # running record (human readable) of version changes
├-- club_info_template.json                 # JSON template for club/portfolio info
├-- club_stocks.csv                         # CSV template for club/portfolio buy and sell of stocks
├-- CONTRIBUTING.md                         # Directions and standards for contributing to this application
├-- dchat.py                                # Discord chatbot entrypoint
├-- humans.txt                              # Running list of all contributors
├-- LICENSE                                 # Source of truth for required LICENSE
├-- pyproject.toml                          # Python toml setup configurations
├-- README.md                               # This file
├-- setup.py                                # Backwards compatable python setup script
├-- stocks.pkl                              # Pickle file of latest stocks download (prevent extra calls to 
|                                           # apvantage API)
└-- tox.ini                                 # configuration file for testing via tox
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- GETTING STARTED -->
## Getting Started

To build a development version of this software, refer to the [CONTRIBUTING.md](./CONTRIBUTING.md) file for development
instructions.

### Prerequisites 

This bot is run off of a Digital Ocean droplet and constantly monitors a single Discord server. In order to run this bot
locally, you will need [Python][python-url] and [Poetry][poetry-url] installed. All other dependencies are installed 
using poetry.

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

Use this space to show useful examples of how a project can be used. Additional screenshots, code examples and demos work well in this space. You may also link to more resources.

_For more examples, please refer to the [Documentation](https://example.com)_

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
[contributors-shield]: https://img.shields.io/github/contributors/CyIC/warren_bot.svg?style=for-the-badge
[contributors-url]: https://github.com/CyIC/warren_bot/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/CyIC/warren_bot.svg?style=for-the-badge
[forks-url]: https://github.com/CyIC/warren_bot/network/members
[stars-shield]: https://img.shields.io/github/stars/CyIC/warren_bot.svg?style=for-the-badge
[stars-url]: https://github.com/CyIC/warren_bot/stargazers
[issues-shield]: https://img.shields.io/github/issues/CyIC/warren_bot.svg?style=for-the-badge
[issues-url]: https://github.com/CyIC/warren_bot/issues
[license-shield]: https://img.shields.io/github/license/CyIC/warren_bot.svg?style=for-the-badge
[license-url]: https://github.com/CyIC/warren_bot/blob/master/LICENSE.md
[product-screenshot]: images/screenshot.png
[lint-flake8-shield]: https://img.shields.io/badge/linting-flake8-yellowgreen?style=for-the-badge
[flake8-url]: https://flake8.pycqa.org/en/latest/
[discordpy-url]: https://discordpy.readthedocs.io/en/stable/
[python-shield]: https://img.shields.io/python/required-version-toml?style=for-the-badge&tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2FCyIC%2Fwarren_bot%2Fblob%2Fmain%2Fpyproject.toml
[python-url]: https://www.python.org/
[poetry-url]: https://python-poetry.org
[oss-shield]: https://img.shields.io/osslifecycle/CyIC/warren_bot?style=for-the-badge
[oss-url]: https://github.com/Netflix/osstracker/tree/master