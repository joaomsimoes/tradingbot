import logging
from binance.spot import Spot as Client
from binance.lib.utils import config_logging
from datetime import datetime
import numpy as np
import pandas as pd
import pandas_ta as pta
import pickle
import json
from main import COIN, COIN_PAIR
import warnings

THRESHOLD = .5

warnings.filterwarnings('ignore')


with open('keys.json', 'r') as fIn:
    keys = json.load(fIn)

config_logging(logging, logging.DEBUG, log_file='logs.txt')

client = Client(keys['api'], keys['secret'])

model = pickle.load(open(f'./model/models/{COIN_PAIR}.sav', 'rb'))


def model_prediction():
    data, _ = data_prepared()
    data_proba = model.predict_proba(data)
    result = [i[1] for i in data_proba]

    return result


def signal_indicator(type=None, prediction=None):
    # MA = {'ETH': [30, 100], 'LUNA': [10, 200], 'SOL': [40, 80]}
    #
    # for k, v in MA.items():
    #     if COIN == k:
    #         _, df = data_prepared(ma_fast=v[0], ma_slow=v[1])
    #
    # slope_fast = df.iloc[-1, 11]
    # slope_slow = df.iloc[-1, 12]

    if type == 'BUY':
        return 1 if (prediction[-1] > .55) else 0

    elif type == 'SELL':
        return 1 if (prediction[-1] < .5) else 0


def binance_klines_data(limit=100):
    # get the data
    data = client.klines(COIN_PAIR, "30m", limit=limit)
    columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close time', 'quote asset volume',
               'numberoftrades', 'taker buy base asset volume', 'taker', 'ignore']
    klines = pd.DataFrame(data, columns=columns)
    klines['timestamp'] = pd.to_datetime(klines.timestamp, unit='ms')
    # to merge with greed index it needs to match by day time
    klines['time'] = pd.to_datetime(klines['timestamp'].dt.strftime('%Y-%m-%d'))

    return klines


def data_prepared(ma_fast=10, ma_slow=40):
    # get the data
    df = binance_klines_data(limit=100)

    # merge with greed index data
    # df = data_klines.merge(greed_df, left_on='time', right_on='time')
    df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume', 'numberoftrades']]
    df = df.astype({"open": float, "high": float, "low": float, "close": float,
                    "volume": float, "numberoftrades": float})

    # feature eng.
    df['candle_hight'] = 100 * (df.high - df.low)/((df.high + df.low)/2)
    df['price_change'] = df['close'].pct_change()*100
    df['FASTMA'] = df.close.rolling(ma_fast).mean()
    df['SLOWMA'] = df.close.rolling(ma_slow).mean()
    df['FASTSlope'] = np.degrees(np.arctan(df['FASTMA'].diff()/ma_fast))
    df['SLOWSlope'] = np.degrees(np.arctan(df['SLOWMA'].diff()/ma_slow))
    df['RSI'] = pta.rsi(df.close)
    df['Slope'] = pta.slope(df.close, length=5)
    df['AROON'] = pta.aroon(df['high'], df['low'])['AROONU_14']
    df['BBAND'] = pta.bbands(df['close'], length=14, std=2, talib=False)['BBP_14_2.0']
    df['OBV'] = pta.bbands(close=df['close'], volume=df['volume'])['BBP_5_2.0']
    df['MACD'] = pta.macd(close=df['close'])['MACD_12_26_9']
    df = df.sort_values('timestamp')

    # final dataset
    reframed = df[['volume', 'candle_hight', 'price_change', 'RSI', 'Slope',
                    'AROON', 'BBAND', 'OBV', 'MACD']]

    reframed = reframed.astype('float32')
    total_columns = len(reframed.columns)
    # prepare for timeseries
    reframed = series_to_supervised(reframed, 28, 1)
    columns_to_remove = reframed.iloc[:, :total_columns].columns
    reframed = reframed.drop(columns_to_remove, axis=1)

    return reframed, df


def series_to_supervised(data, n_in=1, n_out=1, dropnan=True):
    """
    Frame a time series as a supervised learning dataset.
    Arguments:
        data: Sequence of observations as a list or NumPy array.
        n_in: Number of lag observations as input (X).
        n_out: Number of observations as output (y).
        dropnan: Boolean whether or not to drop rows with NaN values.
    Returns:
        Pandas DataFrame of series framed for supervised learning.
    """
    n_vars = 1 if type(data) is list else data.shape[1]
    df = pd.DataFrame(data)
    cols, names = list(), list()
    # input sequence (t-n, ... t-1)
    for i in range(n_in, 0, -1):
        cols.append(df.shift(i))
        names += [('var%d(t-%d)' % (j+1, i+1)) for j in range(n_vars)]
    # forecast sequence (t, t+1, ... t+n)
    for i in range(0, n_out):
        cols.append(df.shift(-i))
        if i == 0:
            names += [('var%d(t)' % (j+1)) for j in range(n_vars)]
        else:
            names += [('var%d(t+%d)' % (j+1, i+1)) for j in range(n_vars)]
    # put it all together
    agg = pd.concat(cols, axis=1)
    agg.columns = names
    # drop rows with NaN values
    if dropnan:
        agg.dropna(inplace=True)
    return agg


def get_price():
    # get the actual price from the coin
    coin_price = client.book_ticker(COIN_PAIR)
    coin_price = float(coin_price['bidPrice'])

    return coin_price


def stoploss(timestamp=None, price_bought=None):
    # Calculate how many 5min periods between current time and bought time
    date = datetime.fromtimestamp(timestamp / 1000.0)
    now = datetime.now()
    limit = int((now - date).total_seconds() / 1800) # 30 min
    # because of price volatility, it can fire the stop loss on the first minutes
    # better to wait to see if the price is really going up or down
    if limit < 1:
        return price_bought * .985

    else:
        # set stop_loss 1% from the highest price since we bought
        # this threshold can be changed
        klines_price = binance_klines_data(limit=limit)
        max_price = float(klines_price.close.max())
        stop_loss = max_price * .985

        return stop_loss



def place_buy_order(quantity=None):
    response = client.new_margin_order(
        symbol=COIN_PAIR,
        side="BUY",
        type="MARKET",
        recvWindow=6000,
        quantity=round(quantity, lot_size())
    )
    logging.info(response)

    return response


def place_sell_order(quantity=None):
    try:
        response = client.new_margin_order(
            symbol=COIN_PAIR,
            side="SELL",
            type="MARKET",
            recvWindow=6000,
            sideEffectType='AUTO_REPAY',
            quantity=quantity)
        logging.info(response)
        return response

    except:
        response = client.new_margin_order(
            symbol=COIN_PAIR,
            side="SELL",
            type="MARKET",
            recvWindow=50000,
            sideEffectType='AUTO_REPAY',
            quantity=quantity)
        logging.info(response)
        return response


def lot_size():
    lotsize = {'BTCBUSD': 4, 'ETHBUSD': 4, 'SOLBUSD': 2, 'LUNABUSD': 2, 'AVAXBUSD': 2,
           'ADABUSD': 1, 'XRPBUSD': 0}

    for key, value in lotsize.items():
        if key == COIN_PAIR:
            return value


def get_margin_available_amount():
    data = client.margin_account()['userAssets']

    for item in data:
        if item['asset'] == COIN:
            lotsize = 1 / (10 ** lot_size())
            available_amount = float(item['free']) // lotsize * lotsize

            return available_amount


# def get_busd_amount():
#     data = client.account()['balances']
#
#     for item in data:
#         if item['asset'] == 'BUSD':
#             return float(item['free'])


def percentage_calculator(old_price=None, new_price=None):
    return round(((new_price - old_price) / old_price)*100, 2)
