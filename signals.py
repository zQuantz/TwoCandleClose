from mpl_finance import candlestick_ohlc as ohlc
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from bs4 import BeautifulSoup
from report import report_

import pandas as pd
import requests
import sys, os
import pickle
import shutil
import time

with open('data/tickers.pickle', 'rb') as file:
	tickers = pickle.load(file)

headers_mobile = { 'User-Agent' : 'Mozilla/5.0 (iPhone; CPU iPhone OS 9_1 like Mac OS X) AppleWebKit/601.1.46 (KHTML, like Gecko) Version/9.0 Mobile/13B137 Safari/601.1'}
HISTORY = "https://ca.finance.yahoo.com/quote/{ticker}/history?p={ticker}"
PARSER = "lxml"

upper_band_length = 10
lower_band_length = 8
ma_length = 50

results = []

def analyze(df):

	df['UpperBand'] = df.High.rolling(upper_band_length, min_periods=1).mean()
	df['LowerBand'] = df.Low.rolling(lower_band_length, min_periods=1).mean()

	df['BandRange'] = (df.UpperBand - df.LowerBand)
	df['BandRangeAvg'] = df.BandRange.rolling(20, min_periods=1).mean()

	df['MA50'] = df.Close.rolling(50, min_periods=1).mean()
	df['MA200'] = df.Close.rolling(200, min_periods=1).mean()

	df['BodyProportion'] = abs((df.Close - df.Open) / (df.High - df.Low))
	df['AvgBodyProportion'] = df.BodyProportion.rolling(20, min_periods=1).mean()

	df['Change'] = abs((df.Close - df.Open) / df.Open)
	df['AvgChange'] = df.Change.rolling(20, min_periods=1).mean()

	df['UpperClose'] = ((df.Close > df.UpperBand) & (df.Open < df.UpperBand) & (df.Open > df.LowerBand)).astype(int)
	df['LowerClose'] = ((df.Close < df.LowerBand) & (df.Open > df.LowerBand) & (df.Open < df.UpperBand)).astype(int)

	df['SecondUpperClose'] = ((df.Close > df.Open) & (df.UpperClose.shift().fillna(0) == 1)).astype(int)
	df['SecondLowerClose'] = ((df.Close < df.Open) & (df.LowerClose.shift().fillna(0) == 1)).astype(int)

	df['AvgVolume'] = df.Volume.rolling(20, min_periods=1).mean()

	return df

def fetch(ticker):	

	page = requests.get(HISTORY.format(ticker = ticker), headers=headers_mobile).content
	page = BeautifulSoup(page, PARSER)

	table = page.find("table", {"data-test" : "historical-prices"})
	df = pd.read_html(str(table))[0]
	df = df.reset_index(drop=True).iloc[:-1, :]
	df = df.drop_duplicates(subset=["Date"])	
	dates = pd.date_range(start=df.Date.values[-1], end=df.Date.values[0])
	dates = dates[::-1][:len(df)]
	df.Date = dates

	df['Date'] = pd.to_datetime(df.Date.values, format="%b. %d, %Y")
	df['Date'] = df['Date'].map(mdates.date2num)

	df.columns = ['Date', 'Open', 'High', 'Low', 'Close', 'AdjClose', 'Volume']
	df = df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
	df.columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']

	df['Open'] = df.Open.astype(float)
	df['High'] = df.High.astype(float)
	df['Low'] = df.Low.astype(float)
	df['Close'] = df.Close.astype(float)
	df['Volume'] = df.Volume.astype(int)

	df = df.sort_values('Date').reset_index(drop=True)

	return df

def plot(df, ticker):

	font_size = 9
	data = df.values[:, :6]

	## Plot
	f, ax = plt.subplots(6, 1, figsize=(14, 8), sharex=True,
						 gridspec_kw={"height_ratios" : [2, 1, 1, 1, 1, 1]})
	
	ohlc(ax[0], data[:, :-1], width=0.5)

	ax[0].plot(data[:, 0], df.UpperBand.values, color='orange')
	ax[0].plot(data[:, 0], df.LowerBand.values, color='orange')
	ax[0].plot(data[:, 0], df.MA50.values, color="blue")
	
	ax[1].bar(data[:, 0], df.Change.values)
	ax[1].plot(data[:, 0], df.AvgChange.values, color='r')
	ax[1].set_title("Candle Change", loc="right", fontsize=font_size)

	ax[2].bar(data[:, 0], df.BodyProportion.values)
	ax[2].plot(data[:, 0], df.AvgBodyProportion.values, color='r')
	ax[2].set_title("Body/Wick Proportion", loc="right", fontsize=font_size)

	ax[3].bar(data[:, 0], df.Change.values)
	ax[3].plot(data[:, 0], df.AvgChange.values, color='r')
	ax[3].set_title("Band Width", loc="right", fontsize=font_size)

	ax[4].bar(data[:, 0], data[:, 5])
	ax[4].plot(data[:, 0], df.AvgVolume, color='r')
	ax[4].set_title("Volume", loc="right", fontsize=font_size)

	ax[5].bar(data[:, 0], df.SecondUpperClose.values, color='g')
	ax[5].bar(data[:, 0], df.SecondLowerClose.values * -1, color='r')
	ax[5].set_title("Signal", loc="right", fontsize=font_size)

	for ax_ in ax: ax_.grid(True); ax_.xaxis_date(); 

	f.suptitle(f'{ticker} - {tickers[ticker][0]} - {tickers[ticker][1]}')

	plt.savefig(f'plots/{ticker}.png')
	plt.close()

def main(ticker):

	try:
		df = analyze(fetch(ticker))
	except Exception as e:
		return

	is_long = df.SecondUpperClose.values[-1]
	is_short = df.SecondLowerClose.values[-1]

	assert (is_long + is_short) != 2

	if is_long:
		direction = "Long"
	elif is_short:
		direction = "Short"
	else:
		return

	plot(df, ticker)
	results.append([
		ticker,
		direction,
		(df.BodyProportion.values[-1] + df.BodyProportion.values[-2]) / 2
	])

if __name__ == '__main__':

	try:
		shutil.rmtree("plots")
	except:
		pass

	try:
		os.mkdir("plots")
	except:
		pass

	for ticker in tickers:
		print("Processing:", ticker) ; main(ticker) ; 
		time.sleep(1)

	df = pd.DataFrame(results, columns = ['Ticker', 'Direction', 'BPAvg'])
	df = df.sort_values(['Direction', 'BPAvg'], ascending=[True, False])
	report_(df)
