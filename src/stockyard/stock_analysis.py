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
    earnings = yf_api.get_yfinance_earnings(ticker)
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
    record = sections.record_of_stock(data, fundamentals, as_of)
    await utils.send_message_in_chunks(message.channel, _discord(text.record_of_stock(record)))
    # Bridge until risk_reward migrates: legacy risk_reward wants the peak high yield in percent units
    high_yield = max((row.high_yield for row in record.rows if row.high_yield is not None), default=0.0) * 100
    msg, charts = trend(income_statement, earnings, monthly_company_prices)
    await message.channel.send(msg)
    for fig in charts:
        with open(fig, "rb") as fh:
            f = discord.File(fh, filename=fig)
            await message.channel.send(file=f)
    await utils.send_message_in_chunks(
        message.channel, _discord(text.cash_position(sections.cash_position(data, fundamentals, as_of)))
    )
    await message.channel.send(_discord(text.revenue_growth(sections.revenue_growth(data, fundamentals, as_of))))
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
