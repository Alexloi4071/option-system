"""測試歷史數據獲取和 HV 計算"""
import yfinance as yf
import pandas as pd
import numpy as np
import math

# 測試獲取 META 歷史數據
ticker = 'META'
stock = yf.Ticker(ticker)
hist = stock.history(period='3mo', interval='1d')

print(f'獲取到 {len(hist)} 條歷史記錄')
print(f'日期範圍: {hist.index[0].date()} 到 {hist.index[-1].date()}')
print(f'收盤價範圍: ${hist["Close"].min():.2f} - ${hist["Close"].max():.2f}')
print()
print('最近5天數據:')
print(hist.tail())
print()

# 測試 HV 計算
price_series = hist['Close']
window = 30

# 選取窗口期數據
if len(price_series) > window:
    price_series = price_series.iloc[-window:]
    print(f'使用最近 {window} 天數據')

# 計算對數收益率
log_returns = np.log(price_series / price_series.shift(1))
log_returns = log_returns.dropna()

print(f'有效對數收益率數據點: {len(log_returns)}')
print(f'對數收益率範圍: {log_returns.min():.6f} 到 {log_returns.max():.6f}')

# 計算統計量
mean_return = log_returns.mean()
std_return = log_returns.std(ddof=1)

print(f'平均收益率: {mean_return:.8f}')
print(f'收益率標準差: {std_return:.8f}')

# 年化波動率
annualization_factor = math.sqrt(252)
historical_volatility = std_return * annualization_factor

print(f'年化因子: {annualization_factor:.4f}')
print(f'歷史波動率 (HV): {historical_volatility*100:.2f}%')
