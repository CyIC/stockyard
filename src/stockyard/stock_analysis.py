# -*- coding: utf-8 -*-
# pylint: disable=C0116, W0511, E1121, E1137
"""Stock Analysis functions for chatbot."""
import datetime
import logging

import discord
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from dateutil.relativedelta import relativedelta
from prettytable import PrettyTable

from stockyard import utilities as utils
from stockyard.clock import new_york_today
from stockyard.data.fundamentals import aligned_annual_fundamentals
from stockyard.data.snapshot import fetch_stock_data
from stockyard.render import text
from stockyard.research import sections
from stockyard import yfinance_integration as yf_api

YRS_LOOKBACK = 5
logger = logging.getLogger("discord")
logger.setLevel(logging.DEBUG)

float_formatter = "{:0.2f}".format
np.set_printoptions(formatter={"float_kind": float_formatter})


def _ttm_eps(quarterly_earnings):
    """Trailing twelve month EPS, the annual earnings basis for a P/E ratio.

    :param quarterly_earnings: <pd.DataFrame> quarterly earnings, oldest row first
    :return: <float> sum of the four most recent reported quarters
    """
    return quarterly_earnings["reportedEPS"].iloc[-4:].sum()


def record_of_stock(eps, income_statement, daily_prices, monthly_prices):
    """Build record of stock section of analysis.

    :param eps:
    :param income_statement:
    :param stock_price_json:
    :param monthly_prices:
    :return: <tuple> (<list> a list of message chunks to print, <float> max high_yield)
    """
    # pylint: disable=R0915, R0914, W0212
    msg = []
    msg.append("\n__**Record of Stock**__\n")

    # Get only last 5 years of yearly earnings
    eps_per_year = eps["annualEarnings"]
    eps_per_year = eps_per_year[eps_per_year.index >= datetime.datetime.now() - relativedelta(years=5)]
    # Get only last 5 years of quarterly earnings
    quarterly_eps = eps["quarterlyEarnings"]
    quarterly_eps = quarterly_eps[quarterly_eps.index >= datetime.datetime.now() - relativedelta(years=5)]

    # get current stock prices
    present_price = daily_prices["close"].iloc[-1]
    # get current eps on an annual basis, to match the annual EPS the PE columns use
    present_eps = _ttm_eps(quarterly_eps)
    # get monthly prices
    msg.append(f"*Present Price*:\t**{present_price:.3f}**\t*Present EPS*:\t**{present_eps:.3f}**")
    # Display
    high_prices = []
    low_prices = []
    pe_high = []
    pe_low = []
    percent_payout = []
    high_yield = []
    eps_table = PrettyTable(
        [
            "List Last 5 Years",
            "High Price",
            "Low Price",
            "EPS",
            "PE Ratio at High",
            "PE Ratio at Low",
            "Dividend per Share",
            "% Payout",
            "% High Yield",
        ],
        float_format=".3",
    )
    # x.float_format = '.4'
    eps_table.align = "r"
    eps_table.align["PE Ratio at High"] = "c"
    eps_table.align["PE Ratio at Low"] = "c"
    for yr in eps_per_year.index:
        high = float(monthly_prices.loc[yr.strftime("%Y")]["high"].max())
        high_prices.append(high)
        low = float(monthly_prices.loc[yr.strftime("%Y")]["low"].min())
        low_prices.append(low)
        eps = eps_per_year.loc[yr].iloc[-1]
        pe_high.append(high / eps)
        pe_low.append(low / eps)
        div_per_share = monthly_prices.loc[yr.strftime("%Y")]["dividend_amt"].sum()
        pct_payout = (div_per_share / eps) * 100
        percent_payout.append(pct_payout)
        h_yield = (div_per_share / low) * 100
        high_yield.append(h_yield)
        eps_table.add_row(
            [
                yr,
                f"${high:15,.2f}",
                f"${low:15,.2f}",
                eps,
                f"{high / eps:15,.4f}",
                f"{low / eps:15,.4f}",
                f"{div_per_share:15,.2f}",
                f"{pct_payout:15,.2f}",
                f"{h_yield:15,.2f}",
            ]
        )
    high_prices = pd.Series(high_prices)
    low_prices = pd.Series(low_prices)
    pe_high = pd.Series(pe_high)
    pe_low = pd.Series(pe_low)
    percent_payout = pd.Series(percent_payout)
    high_yield = pd.Series(high_yield)
    eps_table.add_row(
        [
            "Averages",
            f"${high_prices.mean():15,.2f}",
            f"${low_prices.mean():15,.2f}",
            "",
            f"{pe_high.mean():15,.4f}",
            f"{pe_low.mean():15,.4f}",
            "",
            f"{percent_payout.mean():15,.2f}",
            "",
        ]
    )
    msg.append(f"```{eps_table}```")
    y = PrettyTable([], float_format=".4")
    y.header = False
    # y.border = False
    y._max_width = {
        "Field 1": 15,
        "Field 2": 20,
        "Field 3": 15,
        "Field 4": 20,
        "Field 5": 20,
        "Field 6": 20,
    }
    # Past Sales Records  ********** get sales_percent_increase  ****************
    sales_per_year = income_statement["annualReports"]["totalRevenue"]
    # Last year and year before sales
    recent_sales_trend = (sales_per_year.iloc[-1] + sales_per_year.iloc[-2]) / 2
    # Years 5 and 6 sales
    past_sales_trend = (sales_per_year.iloc[0] + sales_per_year.iloc[1]) / 2
    sales_increase = recent_sales_trend - past_sales_trend
    sales_percent_increase = sales_increase / past_sales_trend

    # Last year and year before EPS  ************** GET eps_percent_increase *************
    recent_eps_mean = (eps_per_year.iloc[-1] + eps_per_year.iloc[-2]) / 2
    # Years 4 and 5 EPS
    past_eps_mean = (eps_per_year.iloc[1] + eps_per_year.iloc[0]) / 2
    eps_increase = recent_eps_mean - past_eps_mean
    eps_percent_increase = eps_increase.iloc[0] / past_eps_mean.iloc[0]

    y.add_row(
        [
            f"Present Price % difference then high price {YRS_LOOKBACK} years ago",
            f"{((present_price - high_prices.values[0]) / high_prices.values[0]):.4%}",
            "% Increase in Sales",
            f"{sales_percent_increase:.4%}",
            "% Increase in Earnings",
            f"{eps_percent_increase:.4%}",
        ]
    )
    # pylint: disable-next=consider-using-f-string
    msg.append(
        "*Average PE Ratio*:\t{:20.4f}\t*Current PE Ratio*\t{:20.4f}".format(
            pd.concat([pe_high, pe_low]).mean(),
            present_price / present_eps,
        )
    )
    msg.append(f"```{y}```")
    msg.append("**% Payout** is `Dividend per share / EPS` \t**% High Yield** is `Dividend per share / Low Price`")
    return msg, high_yield.max()


def trend(
    income_statement: pd.DataFrame,
    eps: pd.DataFrame,
    monthly_company_prices: pd.DataFrame,
):
    """Build Trend section of analysis.

    :param income_statement: <pandas.DatFrame>
    :param eps: <pandas.DatFrame>
    :param monthly_company_prices: <pandas.DatFrame>
    :return: <tuple> (<str> a message of the section to print, <list> of chart figure file names)
    """
    msg = "\n__**Trends**__"
    files = []
    quarterly_revenue = income_statement["quarterlyReports"]
    quarterly_revenue = quarterly_revenue["totalRevenue"]
    quarterly_revenue = quarterly_revenue[quarterly_revenue.index >= datetime.datetime.now() - relativedelta(years=5)]
    quarterly_eps = eps["quarterlyEarnings"]
    quarterly_eps = quarterly_eps[quarterly_eps.index >= datetime.datetime.now() - relativedelta(years=5)]
    # Quarterly Revenue
    fig1, revenue_fig = plt.subplots()  # pylint: disable=W0612
    revenue_fig.set_xlabel("Date")
    revenue_fig.set_ylabel("Revenue", color="tab:red")
    revenue_fig.plot(quarterly_revenue, color="tab:red")
    revenue_fig.set_title("Revenue & EPS")
    # Quarterly EPS
    eps_fig = revenue_fig.twinx()
    eps_fig.set_ylabel("EPS", color="tab:blue")
    eps_fig.plot(quarterly_eps["reportedEPS"])
    # Price high/low
    eps_fig_path = utils.data_path("eps_fig.jpg")
    plt.savefig(eps_fig_path)
    files.append(eps_fig_path)

    # Plot Stock Highs and Lows
    monthly_company_prices["avg_high"] = monthly_company_prices["high"].rolling(4).mean()
    monthly_company_prices["avg_low"] = monthly_company_prices["low"].rolling(4).mean()
    monthly_company_prices.plot(
        y=["high", "low", "avg_high", "avg_low"],
        title="Stock High & Low",
        xlabel="Date",
        ylabel="USD",
    )
    stock_high_low_path = utils.data_path("stock_high_low.jpg")
    plt.savefig(stock_high_low_path)
    files.append(stock_high_low_path)
    return msg, files


def revenue_growth(
    daily_prices: pd.DataFrame,
    cash_flow: pd.DataFrame,
    income_statement: pd.DataFrame,
    current_eps: float,
    current_shares_outstanding: int,
):
    # pylint: disable=C0209
    """Build Revenue Growth section of report.

    :param daily_prices: <pd.DataFrame> Current Daily Prices for company
    :param cash_flow: <pd.DataFrame> Current Cash Flow Statement
    :param income_statement: <pd.DataFrame> Current Income Statement
    :param current_eps: <float>
    :param current_shares_outstanding: <int>
    :return: <str> a message of the section to print
    """
    msg = "\n__**Revenue Growth**__"
    cash_flow = cash_flow["annualReports"]
    try:
        dividend_yield = cash_flow["dividendPayout"].iloc[-1] / current_shares_outstanding
    except TypeError as e:
        logger.error(e)
        dividend_yield = 0
    revenue = income_statement["annualReports"]
    revenue = pd.DataFrame(revenue["totalRevenue"])
    revenue_diff = revenue.diff()
    revenue["change"] = revenue_diff
    revenue["%_change"] = revenue["totalRevenue"].pct_change()

    pd.options.display.float_format = "{:,.3f}".format
    msg += f"```{revenue}```"
    msg += f"```Average Growth: {revenue['%_change'].mean():.3%}```"
    msg += f"```div yield: {dividend_yield:.3f}```"
    current_price = daily_prices["close"].iloc[-1]
    current_pe = current_price / current_eps
    msg += f"```Current P/E: {current_pe:.4f}```"
    msg += "```Growth Rate w/ Dividends: {:.3f}```".format(
        ((revenue["%_change"].mean() * 10) + dividend_yield) / current_pe
    )
    return msg


def predict_low(high: float, low: float, current_price: float):
    """Build out the table for buy/maybe/sell options.

    :param high: <float> Predicted stock high
    :param low: <float> Predicted stock low
    :param current_price: <float> Current price of a stock
    :return: <str> a message of the prediction to print
    """
    # pylint: disable=C0209
    assert high > low
    quarter_range = (high - low) / 3
    if current_price < (low + quarter_range):
        decision = "BUY"
    elif current_price > (high - quarter_range):
        decision = "SELL"
    else:
        decision = "Maybe"
    msg = """```Lower 1/3 = {low_low:,.2f} to {low_high:,.2f} (Buy)
Middle 1/3 = {mid_low:,.2f} to {mid_high:,.2f} (Maybe)
Upper 1/3 = {high_low:,.2f} to {high_high:,.2f} (Sell)```
*Present Market Price of {present_price:,.2f} is in the **{decision}** range*
""".format(
        low_low=low,
        low_high=low + quarter_range,
        mid_low=low + quarter_range,
        mid_high=low + quarter_range * 2,
        high_low=high - quarter_range,
        high_high=high,
        present_price=current_price,
        decision=decision,
    )
    return msg


def _epoch_seconds(times) -> list[float]:
    """Convert an iterable of datetimes to UNIX epoch seconds."""
    return [moment.timestamp() for moment in times]


def _predict_values(prediction, times) -> list[float]:
    """Evaluate a fitted prediction at each time, returning a list of predicted values."""
    return [prediction(moment.timestamp()) for moment in times]


def _zone_analysis(forcast_high: float, projected_low: float | None, present_price: float) -> tuple[str, float]:
    """Build the zoning message fragment and up-side/down-side ratio for one low estimate.

    Mirrors the original inline handling: predict_low and the ratio share a try block, so a
    failure in either yields an error fragment paired with a 0 ratio.

    :param forcast_high: predicted 5-year high price
    :param projected_low: candidate low price for this zone
    :param present_price: current market price
    :return: tuple of (message fragment, up-side/down-side ratio)
    """
    try:
        fragment = predict_low(forcast_high, projected_low, present_price)
        ratio = (forcast_high - present_price) / (present_price - projected_low)
    except TypeError as e:
        return f"```{e}```", 0
    except (AssertionError, ZeroDivisionError):
        return "```NaN```", 0
    return fragment, ratio


def risk_reward(
    daily_prices: pd.DataFrame,
    eps: pd.DataFrame,
    monthly_company_prices: pd.DataFrame,
    income_statement: pd.DataFrame,
    high_yield: float,
):
    # pylint: disable=R0915, R0914, C0209
    """Build Risk/Reward analysis of stock report.

    :param company_data:
    :param stock_price_json:
    :param cash_flow_json:
    :param monthly_company_price_json:
    :param income_statement_json:
    :param high_yield:
    :return:
    """
    msg = "\n__**Evaluating Risk & Reward**__"
    present_price = float(daily_prices["close"].iloc[-1])
    files = []
    # Build PE High
    yearly_eps = eps["annualEarnings"]
    yearly_eps = yearly_eps[yearly_eps.index >= datetime.datetime.now() - relativedelta(years=5)]
    quarterly_eps = eps["quarterlyEarnings"]
    quarterly_eps = quarterly_eps[quarterly_eps.index >= datetime.datetime.now() - relativedelta(years=5)]
    pe_high = []
    div_per_share = []
    for yr in yearly_eps.index:
        high = float(monthly_company_prices.loc[yr.strftime("%Y")]["high"].max())
        newest_eps = yearly_eps.loc[yr.strftime("%Y")]["reportedEPS"].iloc[-1]
        div_per_share.append(monthly_company_prices.loc[yr.strftime("%Y")]["dividend_amt"].sum())
        pe_high.append(high / newest_eps)
    pe_high = pd.Series(pe_high, index=yearly_eps.index)
    div_per_share = pd.Series(div_per_share, index=yearly_eps.index)
    # filter daily_prices to last 5 years
    daily_prices = daily_prices[daily_prices.index >= datetime.datetime.now() - relativedelta(years=5)]
    future_five_years = datetime.datetime.now() + relativedelta(years=5)

    # Build EPS prediction from trailing twelve month earnings. Quarterly EPS is strongly
    # seasonal, so fitting it raw reads the seasonal swing as a trend; TTM removes that and is
    # already on the annual basis pe_high is built from. Needs 4 quarters per TTM point.
    ttm_eps = quarterly_eps["reportedEPS"].rolling(4).sum().dropna()
    est_high_eps = 0
    if len(ttm_eps) >= 2:
        time = ttm_eps.index.tolist()
        # convert time to UNIX Epoch time for x values
        eps_prediction = np.polynomial.polynomial.Polynomial.fit(_epoch_seconds(time), ttm_eps, 1)
        est_high_eps = eps_prediction(future_five_years.timestamp())
        eps_pred = pd.Series(pd.to_numeric(_predict_values(eps_prediction, time)), index=pd.to_datetime(time))
        # convert arrays to DataFrame for plotting
        tmp_info = {"ttm_eps": ttm_eps, "eps_pred": eps_pred}
        ttm_frame = pd.DataFrame(tmp_info, index=time)
        ttm_frame.index.name = "date"
        ttm_frame.index = pd.to_datetime(time)
        ttm_frame.sort_index(ascending=True, inplace=True)
        ttm_frame.plot()
        eps_pred_fig_path = utils.data_path("eps_pred_fig.jpg")
        plt.savefig(eps_pred_fig_path)
        files.append(eps_pred_fig_path)
    # Extrapolating any declining series five years out eventually crosses zero, and a
    # negative projection is not a price. Report the gap instead of quoting one.
    has_forecast = est_high_eps > 0
    forcast_high = pe_high.mean() * est_high_eps

    # Build High Revenue Prediction
    revenue = income_statement["quarterlyReports"]
    revenue = revenue["totalRevenue"].tolist()
    time = income_statement["quarterlyReports"].index.tolist()
    # Build prediction
    revenue_prediction = np.polynomial.polynomial.Polynomial.fit(_epoch_seconds(time), revenue, 1)
    # Build revenue & prediction DataFrame
    revenue = pd.Series(revenue, index=time)
    revenue_pred = pd.Series(_predict_values(revenue_prediction, time), index=time)
    tmp_info = {"revenue": revenue, "revenue_pred": revenue_pred}
    quarterly_revenue = pd.DataFrame(tmp_info, index=time)
    quarterly_revenue.index.name = "date"
    quarterly_revenue.index = pd.to_datetime(time)
    quarterly_revenue.sort_index(ascending=True, inplace=True)
    # Plot revenue and prediction
    quarterly_revenue.plot()
    revenue_pred_fig_path = utils.data_path("revenue_pred_fig.jpg")
    plt.savefig(revenue_pred_fig_path)
    files.append(revenue_pred_fig_path)

    # Sales to EPS Prediction
    # print('PE High Mean: {}'.format(pe_high.mean()))
    # print('Predicted Revenue: {}'.format(revenue_prediction(future_five_years.timestamp())))
    # print('shares_outstanding: {}'.format(current_stocks_outstanding))
    # print('forcast_pe_high: {}'.format(est_high_eps))
    # forcast_high = pe_high.mean() * (revenue_prediction(future_five_years.timestamp()) /
    #                                  pd.to_numeric(company_data['shares_outstanding'].iloc[-1]))

    # Build High Price Prediction
    if has_forecast:
        msg += f"""\n**HIGH PRICE - NEXT 5 YEARS**
```Linear Regression of Highs: {forcast_high}```\n"""
    else:
        msg += """\n**HIGH PRICE - NEXT 5 YEARS**
```The earnings trend does not support a five-year price projection.```\n"""

    # Build Low Price Predictions
    # Calculate linear regression low
    low_prices = daily_prices["low"].values.tolist()
    time = daily_prices.index.tolist()
    low_price_prediction = np.polynomial.polynomial.Polynomial.fit(_epoch_seconds(time), low_prices, 1)
    lr_low = low_price_prediction(future_five_years.timestamp())

    # Plot Low Prices and Prediction
    low_prices = pd.Series(low_prices, index=time)
    low_price_pred = pd.Series(_predict_values(low_price_prediction, time), index=time)
    tmp_info = {"low": low_prices, "low_price_pred": low_price_pred}
    low_prices = pd.DataFrame(tmp_info, index=time)
    low_prices.index.name = "date"
    low_prices.index = pd.to_datetime(time)
    low_prices.sort_index(ascending=True, inplace=True)
    low_prices.plot()
    low_price_pred_fig_path = utils.data_path("low_price_pred_fig.jpg")
    plt.savefig(low_price_pred_fig_path)
    files.append(low_price_pred_fig_path)

    # Build High Price Predictions
    # Calculate linear regression high
    high_prices = daily_prices["high"].values.tolist()
    time = daily_prices.index.tolist()
    high_price_prediction = np.polynomial.polynomial.Polynomial.fit(_epoch_seconds(time), high_prices, 1)

    # Plot Low Prices and Prediction
    high_prices = pd.Series(high_prices, index=time)
    high_price_pred = pd.Series(_predict_values(high_price_prediction, time), index=time)
    tmp_info = {"high": high_prices, "high_price_pred": high_price_pred}
    high_prices = pd.DataFrame(tmp_info, index=time)
    high_prices.index.name = "date"
    high_prices.index = pd.to_datetime(time)
    high_prices.sort_index(ascending=True, inplace=True)
    high_prices.plot()
    high_price_pred_fig_path = utils.data_path("high_price_pred_fig.jpg")
    plt.savefig(high_price_pred_fig_path)
    files.append(high_price_pred_fig_path)

    # Calculate severe low
    severe_low = daily_prices["low"].min()
    # Calculate avg low
    avg_low = daily_prices["low"].mean()
    # Calculate Dividend low
    try:
        price_dividend = pd.to_numeric(div_per_share.iloc[-1]) / (high_yield / 100)
    except ValueError as e:
        logger.error(e)
        price_dividend = None
    msg += """**LOW PRICE - NEXT 5 YEARS**
```(a) Linear Regression of Lows: {a}
(b) Avg Low Price of Last 5 Years: {b}
(c) Recent Severe Market Low Price: {c}
(d) Price Dividend will Support: {d}```
""".format(
        a=lr_low, b=avg_low, c=severe_low, d=price_dividend
    )
    # Zoning and the price target are all measured against forcast_high, so they only mean
    # anything when the earnings trend produced one.
    if has_forecast:
        # Build Zoning
        msg += "**ZONING**"
        # Predict A
        msg += "\n(a - Linear Regression)"
        fragment, lr_low = _zone_analysis(forcast_high, lr_low, present_price)
        msg += fragment
        # Predict B
        msg += "\n(b - Avg Low Price of Last 5 Years)"
        fragment, avg_low = _zone_analysis(forcast_high, avg_low, present_price)
        msg += fragment
        # Predict C
        msg += "\n(c - Recent Severe Market Low)"
        fragment, severe_low = _zone_analysis(forcast_high, severe_low, present_price)
        msg += fragment
        # Predict D
        msg += "\n(d - Price Dividend Support)"
        fragment, dividend_low = _zone_analysis(forcast_high, price_dividend, present_price)
        msg += fragment
        # Build UP-SIDE DOWN-SIDE Ration
        msg += """\n**UP-SIDE / DOWN-SIDE RATIO (Potential Gain vs Risk of Loss)**"""
        msg += """```a) {lr_low:.4f} to 1
b) {avg_low:.4f} to 1
c) {severe_low:.4f} to 1
d) {dividend_low:.4f} to 1```""".format(
            lr_low=lr_low, avg_low=avg_low, severe_low=severe_low, dividend_low=dividend_low
        )
        # TODO Build Price Targe
        msg += """\n**PRICE TARGET**
```${:,.2f} 5yr predicted stock price drives {:,.4f}% appreciation```""".format(
            forcast_high, (forcast_high / present_price) * 100 - 100
        )
    return msg, files


def _discord(rendered) -> str:
    """Wrap a rendered section the way the 0.1 report looked (replaced by render.discord in phase 6)."""
    return f"__**{rendered.title}**__\n```{rendered.body}```"


async def run(message, ticker):
    """Run stock analysis.

    :param message: <discord.message> Discord message object to make replys to
    :param ticker: Company stock ticker
    :return:
    """
    # New core (v1): fetched once; sections move onto it one at a time (plan phase 4)
    data = fetch_stock_data(ticker)
    as_of = new_york_today()
    fundamentals = aligned_annual_fundamentals(data, as_of)
    # Get Company Data
    income_statement = yf_api.get_yfinance_income_statement(ticker)
    balance_sheet = yf_api.get_yfinance_balance_sheet(ticker)
    earnings = yf_api.get_yfinance_earnings(ticker)
    cash_flow = yf_api.get_yfinance_cash_flow(ticker)
    # Get company stock prices
    monthly_company_prices = yf_api.get_monthly_yfinance_company_prices(ticker)
    daily_company_prices = yf_api.get_daily_yfinance_company_prices(ticker)

    # Guard: the report requires earnings history. get_yfinance_earnings returns empty
    # DataFrames when a series is unavailable (unknown ticker or no reported EPS);
    # building the report off empty frames would crash downstream, so bail out early.
    if earnings["annualEarnings"].empty or earnings["quarterlyEarnings"].empty:
        await message.channel.send(f"No earnings data available for {ticker}.")
        return

    # Build and send report components
    await utils.send_message_in_chunks(
        message.channel, _discord(text.past_sales(sections.past_sales(data, fundamentals, as_of)))
    )
    await message.channel.send(_discord(text.past_eps(sections.past_eps(data, fundamentals, as_of))))
    msg, high_yield = record_of_stock(earnings, income_statement, daily_company_prices, monthly_company_prices)
    await utils.send_message_in_chunks(message.channel, msg)
    msg, charts = trend(income_statement, earnings, monthly_company_prices)
    await message.channel.send(msg)
    for fig in charts:
        with open(fig, "rb") as fh:
            f = discord.File(fh, filename=fig)
            await message.channel.send(file=f)
    await utils.send_message_in_chunks(
        message.channel, _discord(text.cash_position(sections.cash_position(data, fundamentals, as_of)))
    )
    await message.channel.send(
        revenue_growth(
            daily_company_prices,
            cash_flow,
            income_statement,
            _ttm_eps(earnings["quarterlyEarnings"]),
            balance_sheet["annualReports"]["commonStockSharesOutstanding"].iloc[-1],
        )
    )
    await message.channel.send(_discord(text.earnings_growth(sections.earnings_growth(data, fundamentals, as_of))))
    # TODO management
    # Risk Reward
    msg, charts = risk_reward(
        daily_company_prices,
        earnings,
        monthly_company_prices,
        income_statement,
        high_yield,  # high yield from EPS chart
    )
    await message.channel.send(msg)
    for fig in charts:
        with open(fig, "rb") as fh:
            f = discord.File(fh, filename=fig)
            await message.channel.send(file=f)
