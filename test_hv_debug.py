# test_hv_debug.py
"""
診斷 Module 18 歷史波動率為 0 的問題
"""

import sys
import logging
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from data_layer.data_fetcher import DataFetcher
from calculation_layer.module18_historical_volatility import HistoricalVolatilityCalculator

def test_hv_calculation():
    print("="*60)
    print("診斷 Module 18 歷史波動率問題")
    print("="*60)
    
    # 1. 測試數據獲取
    print("\n[1] 測試歷史數據獲取...")
    fetcher = DataFetcher(use_ibkr=False)
    
    ticker = "META"
    historical_data = fetcher.get_historical_data(ticker, period='1y', interval='1d')
    
    if historical_data is None:
        print("❌ 無法獲取歷史數據!")
        return
    
    print(f"✅ 獲取了 {len(historical_data)} 條歷史記錄")
    print(f"   列名: {list(historical_data.columns)}")
    print(f"   數據類型:\n{historical_data.dtypes}")
    
    # 2. 檢查 Close 列
    print("\n[2] 檢查 Close 列...")
    if 'Close' not in historical_data.columns:
        print("❌ 沒有 'Close' 列!")
        print(f"   可用列: {list(historical_data.columns)}")
        return
    
    close_prices = historical_data['Close']
    print(f"   Close 列類型: {type(close_prices)}")
    print(f"   Close 列數據類型: {close_prices.dtype}")
    print(f"   Close 列長度: {len(close_prices)}")
    print(f"   Close 列前5個值:\n{close_prices.head()}")
    print(f"   Close 列後5個值:\n{close_prices.tail()}")
    
    # 檢查是否有 NaN 或 0 值
    nan_count = close_prices.isna().sum()
    zero_count = (close_prices == 0).sum()
    print(f"   NaN 值數量: {nan_count}")
    print(f"   零值數量: {zero_count}")
    
    # 3. 測試 HV 計算
    print("\n[3] 測試 HV 計算...")
    hv_calc = HistoricalVolatilityCalculator()
    
    # 確保數據是 pandas Series
    if isinstance(close_prices, pd.DataFrame):
        close_prices = close_prices.squeeze()
    
    # 移除 NaN
    close_prices_clean = close_prices.dropna()
    print(f"   清理後數據點數: {len(close_prices_clean)}")
    
    if len(close_prices_clean) < 30:
        print("❌ 數據點不足 30 個!")
        return
    
    try:
        # 計算對數收益率
        log_returns = np.log(close_prices_clean / close_prices_clean.shift(1)).dropna()
        print(f"\n   對數收益率統計:")
        print(f"   - 數據點數: {len(log_returns)}")
        print(f"   - 平均值: {log_returns.mean():.8f}")
        print(f"   - 標準差: {log_returns.std():.8f}")
        print(f"   - 最小值: {log_returns.min():.8f}")
        print(f"   - 最大值: {log_returns.max():.8f}")
        
        # 計算 HV
        result = hv_calc.calculate_hv(close_prices_clean, window=30)
        print(f"\n   ✅ HV 計算結果:")
        print(f"   - 歷史波動率: {result.historical_volatility*100:.2f}%")
        print(f"   - 窗口期: {result.window_days} 天")
        print(f"   - 數據點數: {result.data_points}")
        
    except Exception as e:
        print(f"❌ HV 計算失敗: {e}")
        import traceback
        traceback.print_exc()
    
    # 4. 測試多窗口期
    print("\n[4] 測試多窗口期 HV...")
    try:
        results = hv_calc.calculate_multiple_windows(close_prices_clean, windows=[10, 20, 30])
        for window, result in results.items():
            print(f"   {window}天 HV: {result.historical_volatility*100:.2f}%")
    except Exception as e:
        print(f"❌ 多窗口期計算失敗: {e}")
    
    print("\n" + "="*60)
    print("診斷完成")
    print("="*60)


if __name__ == "__main__":
    test_hv_calculation()
