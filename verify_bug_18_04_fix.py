#!/usr/bin/env python3
"""
驗證 BUG-18-04 修復：iv_rank/iv_percentile 返回 None 而非 50.0

測試場景：
1. 數據不足導致計算失敗
2. 驗證返回 None 而非 50.0
3. 確認調用方能區分錯誤和真實中性值
"""

import sys
from pathlib import Path
import pandas as pd

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from calculation_layer.module18_historical_volatility import HistoricalVolatilityCalculator


def test_bug_18_04_none_return_on_failure():
    """測試失敗時返回 None"""
    print("\n" + "="*80)
    print("BUG-18-04 驗證：iv_rank/iv_percentile 返回 None 而非 50.0")
    print("="*80)
    
    calc = HistoricalVolatilityCalculator()
    
    # 測試 1: calculate_iv_rank 數據不足
    print("\n測試 1: calculate_iv_rank 數據不足")
    print("-" * 80)
    
    current_iv = 0.30
    insufficient_data = pd.Series([0.25])  # 只有 1 個數據點
    
    print(f"輸入:")
    print(f"  current_iv = {current_iv}")
    print(f"  historical_iv_series 長度 = {len(insufficient_data)}")
    
    result = calc.calculate_iv_rank(current_iv, insufficient_data)
    
    print(f"\n輸出:")
    print(f"  iv_rank = {result}")
    
    # 驗證返回 None
    assert result is None, f"應返回 None，實際返回: {result}"
    
    print(f"\n✅ 驗證通過: 返回 None（而非 50.0）")
    
    # 測試 2: calculate_iv_rank IV 範圍為 0
    print("\n\n測試 2: calculate_iv_rank IV 範圍為 0")
    print("-" * 80)
    
    zero_range_data = pd.Series([0.30, 0.30, 0.30, 0.30])  # 所有值相同
    
    print(f"輸入:")
    print(f"  current_iv = {current_iv}")
    print(f"  historical_iv_series = {zero_range_data.tolist()}")
    
    result = calc.calculate_iv_rank(current_iv, zero_range_data)
    
    print(f"\n輸出:")
    print(f"  iv_rank = {result}")
    
    # 驗證返回 None
    assert result is None, f"應返回 None，實際返回: {result}"
    
    print(f"\n✅ 驗證通過: 返回 None（而非 50.0）")
    
    # 測試 3: calculate_iv_percentile 數據不足
    print("\n\n測試 3: calculate_iv_percentile 數據不足")
    print("-" * 80)
    
    result = calc.calculate_iv_percentile(current_iv, insufficient_data)
    
    print(f"\n輸出:")
    print(f"  iv_percentile = {result}")
    
    # 驗證返回 None
    assert result is None, f"應返回 None，實際返回: {result}"
    
    print(f"\n✅ 驗證通過: 返回 None（而非 50.0）")
    
    # 測試 4: 正常計算（Preservation）
    print("\n\n測試 4: 正常計算 - Preservation")
    print("-" * 80)
    
    normal_data = pd.Series([0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50])
    current_iv = 0.35
    
    print(f"輸入:")
    print(f"  current_iv = {current_iv}")
    print(f"  historical_iv_series 長度 = {len(normal_data)}")
    print(f"  範圍: {normal_data.min():.2f} - {normal_data.max():.2f}")
    
    iv_rank = calc.calculate_iv_rank(current_iv, normal_data)
    iv_percentile = calc.calculate_iv_percentile(current_iv, normal_data)
    
    print(f"\n輸出:")
    print(f"  iv_rank = {iv_rank}")
    print(f"  iv_percentile = {iv_percentile}")
    
    # 驗證返回有效值
    assert iv_rank is not None, "正常計算應返回有效值"
    assert iv_percentile is not None, "正常計算應返回有效值"
    assert 0 <= iv_rank <= 100, f"iv_rank 應在 0-100 範圍，實際: {iv_rank}"
    assert 0 <= iv_percentile <= 100, f"iv_percentile 應在 0-100 範圍，實際: {iv_percentile}"
    
    print(f"\n✅ 驗證通過: 正常計算返回有效值")
    
    # 測試 5: 真實的 50% 值（與錯誤的 50.0 區分）
    print("\n\n測試 5: 真實的 50% 值")
    print("-" * 80)
    
    # 構造數據使 iv_rank 接近 50%
    mid_range_data = pd.Series([0.20, 0.25, 0.30, 0.35, 0.40])
    current_iv = 0.30  # 中間值
    
    print(f"輸入:")
    print(f"  current_iv = {current_iv}")
    print(f"  範圍: {mid_range_data.min():.2f} - {mid_range_data.max():.2f}")
    
    iv_rank = calc.calculate_iv_rank(current_iv, mid_range_data)
    
    print(f"\n輸出:")
    print(f"  iv_rank = {iv_rank}")
    
    # 驗證這是真實的 50%，不是錯誤值
    assert iv_rank is not None, "應返回有效值"
    assert 45 <= iv_rank <= 55, f"應接近 50%，實際: {iv_rank}"
    
    print(f"\n✅ 驗證通過: 真實的 50% 值可以與錯誤區分（None vs 50.0）")
    
    print("\n" + "="*80)
    print("✅ BUG-18-04 修復驗證完成：所有測試通過")
    print("="*80)


if __name__ == '__main__':
    test_bug_18_04_none_return_on_failure()
