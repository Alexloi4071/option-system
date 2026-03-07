#!/usr/bin/env python3
"""
驗證 BUG-18-03 修復：calculate_hv NaN 過濾

測試場景：
1. price_series 包含中間 NaN 值
2. 驗證 NaN 被正確過濾
3. 確認 HV 計算成功返回有效值
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from calculation_layer.module18_historical_volatility import HistoricalVolatilityCalculator


def test_bug_18_03_nan_filtering():
    """測試 NaN 過濾"""
    print("\n" + "="*80)
    print("BUG-18-03 驗證：calculate_hv NaN 過濾")
    print("="*80)
    
    calc = HistoricalVolatilityCalculator()
    
    # 測試 1: 單個中間 NaN
    print("\n測試 1: price_series 包含單個中間 NaN")
    print("-" * 80)
    
    dates = pd.date_range('2024-01-01', periods=10)
    prices_with_nan = pd.Series([100, 101, np.nan, 103, 104, 105, 106, 107, 108, 109], index=dates)
    
    print(f"輸入 price_series:")
    print(f"  長度: {len(prices_with_nan)}")
    print(f"  NaN 數量: {prices_with_nan.isna().sum()}")
    print(f"  數據: {prices_with_nan.tolist()}")
    
    try:
        result = calc.calculate_hv(prices_with_nan, window=10)
        print(f"\n輸出:")
        print(f"  HV = {result.historical_volatility * 100:.2f}%")
        print(f"  有效數據點: {result.data_points}")
        
        # 驗證 HV 是有效值
        assert not np.isnan(result.historical_volatility), "HV 不應為 NaN"
        assert not np.isinf(result.historical_volatility), "HV 不應為 inf"
        assert result.historical_volatility > 0, "HV 應為正值"
        
        print(f"\n✅ 驗證通過: HV 計算成功，返回有效值")
        
    except Exception as e:
        print(f"\n❌ 錯誤: {e}")
        sys.exit(1)
    
    # 測試 2: 多個 NaN
    print("\n\n測試 2: price_series 包含多個 NaN")
    print("-" * 80)
    
    prices_with_multiple_nan = pd.Series([100, np.nan, np.nan, 103, 104, 105, 106, 107, 108, 109], index=dates)
    
    print(f"輸入 price_series:")
    print(f"  長度: {len(prices_with_multiple_nan)}")
    print(f"  NaN 數量: {prices_with_multiple_nan.isna().sum()}")
    print(f"  數據: {prices_with_multiple_nan.tolist()}")
    
    try:
        result = calc.calculate_hv(prices_with_multiple_nan, window=10)
        print(f"\n輸出:")
        print(f"  HV = {result.historical_volatility * 100:.2f}%")
        print(f"  有效數據點: {result.data_points}")
        
        # 驗證 HV 是有效值
        assert not np.isnan(result.historical_volatility), "HV 不應為 NaN"
        assert not np.isinf(result.historical_volatility), "HV 不應為 inf"
        assert result.historical_volatility > 0, "HV 應為正值"
        
        print(f"\n✅ 驗證通過: HV 計算成功，返回有效值")
        
    except Exception as e:
        print(f"\n❌ 錯誤: {e}")
        sys.exit(1)
    
    # 測試 3: 不包含 NaN 的正常數據（Preservation）
    print("\n\n測試 3: 正常數據（無 NaN）- Preservation")
    print("-" * 80)
    
    clean_prices = pd.Series([100, 101, 102, 103, 104, 105, 106, 107, 108, 109], index=dates)
    
    print(f"輸入 price_series:")
    print(f"  長度: {len(clean_prices)}")
    print(f"  NaN 數量: {clean_prices.isna().sum()}")
    
    try:
        result = calc.calculate_hv(clean_prices, window=10)
        print(f"\n輸出:")
        print(f"  HV = {result.historical_volatility * 100:.2f}%")
        print(f"  有效數據點: {result.data_points}")
        
        # 驗證 HV 是有效值
        assert not np.isnan(result.historical_volatility), "HV 不應為 NaN"
        assert not np.isinf(result.historical_volatility), "HV 不應為 inf"
        assert result.historical_volatility > 0, "HV 應為正值"
        assert result.data_points == 9, f"應有 9 個有效數據點（10-1），實際: {result.data_points}"
        
        print(f"\n✅ 驗證通過: 正常數據處理不受影響")
        
    except Exception as e:
        print(f"\n❌ 錯誤: {e}")
        sys.exit(1)
    
    # 測試 4: 過濾後數據點不足
    print("\n\n測試 4: 過濾後數據點不足")
    print("-" * 80)
    
    prices_mostly_nan = pd.Series([100, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan], index=dates)
    
    print(f"輸入 price_series:")
    print(f"  長度: {len(prices_mostly_nan)}")
    print(f"  NaN 數量: {prices_mostly_nan.isna().sum()}")
    
    try:
        result = calc.calculate_hv(prices_mostly_nan, window=10)
        print(f"\n❌ 錯誤: 應該拋出 ValueError，但計算成功了")
        sys.exit(1)
    except ValueError as e:
        print(f"\n✅ 驗證通過: 正確拋出 ValueError")
        print(f"  錯誤訊息: {e}")
    
    print("\n" + "="*80)
    print("✅ BUG-18-03 修復驗證完成：所有測試通過")
    print("="*80)


if __name__ == '__main__':
    test_bug_18_03_nan_filtering()
