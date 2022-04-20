import dload
import pandas as pd
import os
import zipfile
import argparse
import warnings
warnings.filterwarnings('ignore')

parser = argparse.ArgumentParser()
parser.add_argument("--coin", required=True)
parser.add_argument("--time", required=True)
args = parser.parse_args()

START = "2021-03-01"
END = "2022-04-08"
COIN = args.coin
TIME = args.time

date_list = pd.date_range(start=START, end=END)
url = []
path = './temp/'

for date in date_list:
    file = f"https://data.binance.vision/data/spot/daily/klines/{COIN}/{TIME}/{COIN}-{TIME}-{date.strftime('%Y-%m-%d')}.zip"
    url.append(file)

dload.save_multi(url_list=url, dir=path)

columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'closetime', 'quoteassetvolume', 'numberoftrades', 'takerbuybaseassetvolume']

klines = pd.DataFrame(columns=columns)

for file in os.listdir(path):
    if file.endswith('.zip'):
        try:
            with zipfile.ZipFile(path + file, 'r') as zip_ref:
                zip_ref.extractall(path)
            os.remove(path + file)
        except:
            pass

for file in os.listdir(path):
    if file.endswith('.csv'):
        csv = pd.read_csv(path + file, header=None, names=columns, index_col=False)
        klines = pd.concat([klines, csv], ignore_index=True, names=columns)
        os.remove(path + file)


klines['timestamp'] = pd.to_datetime(klines.timestamp, unit='ms')
klines['time'] = pd.to_datetime(klines['timestamp'].dt.strftime('%Y-%m-%d'))
klines.to_csv(f'./klines/{COIN}_{TIME}.csv')

klines_to_label = klines[['timestamp', 'close']].set_index('timestamp')
klines_to_label.to_csv(f'./to_label/{COIN}_{TIME}_to_label.csv')

