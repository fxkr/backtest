import itertools
import sys, os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import pandas_datareader as web
import requests_cache
import datetime

session = requests_cache.CachedSession(cache_name='cache', backend='sqlite', expire_after=datetime.timedelta(days=3))

one_day = datetime.timedelta(days=1)
one_week = datetime.timedelta(days=7)

stock = web.get_data_yahoo("VTSAX",
                            start = "2009-01-01",
                            end = "2019-04-30",
                            session=session)


test_start = datetime.datetime(2009, 1, 5)
test_end = datetime.datetime(2019, 1, 7)

assert test_start.weekday() == 0   # Monday
assert test_end.weekday() == test_start.weekday()


# Strategy: invest on 1st day each month (or whatever next possible day is)
def strategy1(is_valid_day, *args, **kwargs):
    """1st"""
    investments = []
    for i in range(2009, 2019):
        for j in range(1, 13):
            for k in range(1, 28):
                dt = datetime.date(i, j,  k)
                if not is_valid_day(dt):
                    continue
                investments.append([dt, 1000])
                break
    return investments

# Strategy: invest on 1st and 15th day each month (or whatever next possible day is)
def strategy2(is_valid_day, *args, **kwargs):
    """1st/15th"""
    investments = []
    for i in range(2009, 2019):
        for j in range(1, 13):
            for k in range(1, 28):
                dt = datetime.date(i, j,  k)
                if not is_valid_day(dt):
                    continue
                investments.append([dt, 500])
                break
            for k in range(15, 28):
                dt = datetime.date(i, j,  k)
                if not is_valid_day(dt):
                    continue
                investments.append([dt, 500])
                break
    return investments

# Strategy: invest on lastish day each month (or whatever next possible day is)
def strategy3(is_valid_day, *args, **kwargs):
    """Lastish"""
    investments = []
    for i in range(2009, 2019):
        for j in range(1, 13):
            for k in range(28):
                dt = datetime.date(i, j, 28) + k * one_day
                if not is_valid_day(dt):
                    continue
                investments.append([dt, 1000])
                break
    return investments

# Strategy: invest on worst (highest) day each month (or whatever next possible day is)
def strategy4(is_valid_day, get_price, *args, **kwargs):
    """Highest"""
    investments = []
    for i in range(2009, 2019):
        for j in range(1, 13):
            best_dt = None
            best_price = None
            for k in range(1, 31+1):
                try:
                    dt = datetime.date(i, j, k)
                except ValueError:
                    continue
                if not is_valid_day(dt):
                    continue
                price = get_price(dt)
                if best_dt is None or best_price is None:
                    best_dt = dt
                    best_price = price
                elif price > best_price:
                    best_dt = dt
                    best_price = price
            investments.append([best_dt, 1000])
    return investments

# Strategy: invest on best (lowest) day each month (or whatever next possible day is)
def strategy5(is_valid_day, get_price, *args, **kwargs):
    """Lowest"""
    investments = []
    for i in range(2009, 2019):
        for j in range(1, 13):
            best_dt = None
            best_price = None
            for k in range(1, 31+1):
                try:
                    dt = datetime.date(i, j, k)
                except ValueError:
                    continue
                if not is_valid_day(dt):
                    continue
                price = get_price(dt)
                if best_dt is None or best_price is None:
                    best_dt = dt
                    best_price = price
                elif price < best_price:
                    best_dt = dt
                    best_price = price
            investments.append([best_dt, 1000])
    return investments



all_days = stock.filter(items=[])

report = all_days

strategies = [strategy1, strategy2, strategy3, strategy4, strategy5]
#strategies = [strategy4]

for i, strategy in enumerate(strategies):
    strategy_name = strategy.__doc__
    investments = strategy(lambda dt: dt in stock.index, lambda dt: stock.loc[dt]['Adj Close'])

    # Convert to data frame
    investments_dollar = pd.DataFrame(investments, columns=['Date', 'Value']).set_index(['Date']).astype(float)

    # Join list of all days with list of investment days. On days without investment, fill in a 0.0 investment.
    investments_dollar = all_days.merge(investments_dollar, left_index=True, right_index=True, sort=True, how='outer').fillna(0)

    # Costbasis is just the total amount invested (without any gains).
    costbasis = investments_dollar.cumsum().rename(columns={'Date': 'Date', 'Value': 'Costbasis <%s>' % strategy_name})

    # Include costbasis in report
    report = report.merge(costbasis, left_index=True, right_index=True, sort=True)

    # Number of shares bought on any certain day (money invested that day divded by adjusted closing price that day).
    investments_stock = investments_dollar.apply(lambda x: float(x['Value']) / float(stock.loc[x.name]['Adj Close']), axis=1, result_type='broadcast')

    # Total stock is cumulative sum of stock bought on all previous days (Bogle says never sell).
    portfolio_stock = investments_stock.cumsum()

    # Portfolio worth is total stock times stock price on any given day.
    portfolio_worth = portfolio_stock.apply(lambda x: x['Value'] * stock.loc[x.name]['Adj Close'], axis=1, result_type='broadcast')

    # Show cost basis and total worth for all days.
    report = report.merge(portfolio_worth.rename(columns={'Value': 'Value <%s>' % strategy_name}), left_index=True, right_index=True, sort=True)

# Raw (non-normalized) values
print(report)

# Normalize all columns by dividing by value in first column
report = report.filter(regex='^Value')
normalize = 1  # Change this, either 0 or 1
if normalize:
    for i in range(1, len(strategies)): # all except zeroeth
        report.iloc[:, i] = report.iloc[:, i].div(report.iloc[:, 0], axis=0)
    report.iloc[:, 0] = report.iloc[:, 0].div(report.iloc[:, 0], axis=0) # must be last! as other columns need to use it's orig value

report.plot(kind='line')
plt.show()
