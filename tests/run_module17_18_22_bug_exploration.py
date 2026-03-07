"""
直接運行 Module17-18-22 Bug Exploration Tests
不使用 pytest，直接執行測試邏輯
"""

import sys
import os
import numpy as np
import pandas as pd
from typing import Dict, List, Optional

# 添加項目根目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import modules to test
from calculation_layer.module17_implied_volatility import ImpliedVolatilityCalculator
from calculation_layer.module18_historical_volatility import HistoricalVolatilityCalculator
from calculation_layer.module22_optimal_strike import OptimalStrikeCalculator


def test_bug_22_04_normalize_iv_3_to_5_range():
    """
    BUG-22-04 (CRITICAL): _normalize_iv 在 3.0-5.0 範圍返回默認值
    
    預期失敗：未修復代碼會返回 DEFAULT_IV = 0.30
    """
    print("\n" + "="*80)
    print("測試 BUG-22-04: _normalize_iv 3.0-5.0 範圍處理")
    print("="*80)
    
    analyzer = OptimalStrikeCalculator()
    test_values = [3.0, 3.5, 4.0, 4.5, 5.0]
    
    failures = []
    for raw_iv in test_values:
        result = analyzer._normalize_iv(raw_iv)
        expected = raw_iv
        
        print(f"\n測試 raw_iv = {raw_iv}:")
        print(f"  預期結果: {expected}")
        print(f"  實際結果: {result}")
        
        if result != expected:
            print(f"  ❌ 失敗: 應該返回 {expected}，但返回了 {result}")
            failures.append((raw_iv, expected, result))
        else:
            print(f"  ✓ 通過")
    
    if failures:
        print(f"\n總結: {len(failures)}/{len(test_values)} 個測試失敗")
        print("Bug 確認: 3.0-5.0 範圍的 IV 被錯誤處理")
        return False
    else:
        print(f"\n總結: 所有測試通過")
        return True


def test_bug_17_03_fixed_tolerance_convergence():
    """
    BUG-17-03 (HIGH): Newton-Raphson 收斂條件使用固定絕對誤差
    
    預期失敗：高價期權迭代次數過多
    """
    print("\n" + "="*80)
    print("測試 BUG-17-03: 固定 tolerance 收斂問題")
    print("="*80)
    
    calculator = ImpliedVolatilityCalculator()
    
    # 測試高價期權
    print("\n測試 1: 高價期權 ($50)")
    market_price = 50.0
    stock_price = 100.0
    strike = 100.0
    time_to_expiry = 1.0
    risk_free_rate = 0.05
    option_type = 'call'
    
    try:
        result = calculator.calculate_implied_volatility(
            market_price=market_price,
            stock_price=stock_price,
            strike=strike,
            time_to_expiry=time_to_expiry,
            risk_free_rate=risk_free_rate,
            option_type=option_type
        )
        
        print(f"  迭代次數: {result.iterations}")
        print(f"  是否收斂: {result.converged}")
        print(f"  隱含波動率: {result.implied_volatility:.4f}")
        
        if result.iterations > 30:
            print(f"  ❌ 失敗: 迭代次數 {result.iterations} > 30")
            print(f"  Bug 確認: 固定絕對誤差對高價期權過於嚴格")
            return False
        else:
            print(f"  ✓ 通過: 迭代次數合理")
            return True
            
    except Exception as e:
        print(f"  ❌ 異常: {e}")
        return False


def test_bug_18_03_nan_in_price_series():
    """
    BUG-18-03 (MEDIUM): calculate_hv 不過濾 NaN 中間值
    
    預期失敗：返回 NaN 或 inf
    """
    print("\n" + "="*80)
    print("測試 BUG-18-03: price_series 中的 NaN 處理")
    print("="*80)
    
    calculator = HistoricalVolatilityCalculator()
    
    # 測試 1: 中間有 NaN
    print("\n測試 1: price_series 中間有 NaN")
    prices = [100.0, 101.0, np.nan, 103.0, 104.0]
    price_series = pd.Series(prices)
    
    try:
        result = calculator.calculate_hv(
            price_series=price_series,
            window=252
        )
        
        print(f"  HV 結果: {result.hv}")
        
        if np.isnan(result.hv):
            print(f"  ❌ 失敗: 返回 NaN")
            print(f"  Bug 確認: NaN 未被過濾")
            return False
        elif np.isinf(result.hv):
            print(f"  ❌ 失敗: 返回 inf")
            print(f"  Bug 確認: NaN 導致 log_returns 包含 inf")
            return False
        else:
            print(f"  ✓ 通過: 返回有效的 HV")
            return True
            
    except Exception as e:
        print(f"  ❌ 異常: {e}")
        print(f"  Bug 確認: NaN 導致計算失敗")
        return False


def test_bug_18_04_iv_rank_failure_returns_50():
    """
    BUG-18-04 (MEDIUM): iv_rank/iv_percentile 靜默返回 50.0
    
    預期失敗：返回 50.0 而非 None
    """
    print("\n" + "="*80)
    print("測試 BUG-18-04: iv_rank 失敗時返回 50.0")
    print("="*80)
    
    calculator = HistoricalVolatilityCalculator()
    
    # 測試 calculate_iv_rank
    print("\n測試 1: calculate_iv_rank 空 history")
    current_iv = 0.25
    iv_history = []  # 空列表應該導致失敗
    
    result = calculator.calculate_iv_rank(
        current_iv=current_iv,
        iv_history=iv_history
    )
    
    print(f"  返回值: {result}")
    
    if result == 50.0:
        print(f"  ❌ 失敗: 返回 50.0 而非 None")
        print(f"  Bug 確認: 計算失敗時靜默返回假中性值")
        return False
    elif result is None:
        print(f"  ✓ 通過: 正確返回 None")
        return True
    else:
        print(f"  ⚠ 意外: 返回了 {result}")
        return False


def test_bug_18_05_conflicting_iv_signals():
    """
    BUG-18-05 (MEDIUM): get_iv_recommendation OR 邏輯產生矛盾信號
    
    預期失敗：矛盾信號仍給出高信心建議
    """
    print("\n" + "="*80)
    print("測試 BUG-18-05: 矛盾 IV 信號檢測")
    print("="*80)
    
    calculator = HistoricalVolatilityCalculator()
    
    # 矛盾信號：rank 高但 percentile 低
    print("\n測試: iv_rank=85%, iv_percentile=10%")
    iv_rank = 85.0
    iv_percentile = 10.0
    
    result = calculator.get_iv_recommendation(
        iv_rank=iv_rank,
        iv_percentile=iv_percentile
    )
    
    print(f"  推薦: {result.recommendation}")
    print(f"  信心度: {result.confidence}")
    
    is_conflicting_detected = (
        result.confidence == "低" or
        "矛盾" in result.recommendation or
        "Conflicting" in result.recommendation
    )
    
    if not is_conflicting_detected:
        print(f"  ❌ 失敗: 矛盾信號未被檢測")
        print(f"  Bug 確認: OR 邏輯無法檢測矛盾")
        return False
    else:
        print(f"  ✓ 通過: 矛盾信號被正確檢測")
        return True


def main():
    """運行所有探索性測試"""
    print("\n" + "="*80)
    print("Module17-18-22 Bug Condition Exploration Tests")
    print("這些測試在未修復的代碼上運行，預期會失敗")
    print("="*80)
    
    results = {}
    
    # 運行測試
    results['BUG-22-04'] = test_bug_22_04_normalize_iv_3_to_5_range()
    results['BUG-17-03'] = test_bug_17_03_fixed_tolerance_convergence()
    results['BUG-18-03'] = test_bug_18_03_nan_in_price_series()
    results['BUG-18-04'] = test_bug_18_04_iv_rank_failure_returns_50()
    results['BUG-18-05'] = test_bug_18_05_conflicting_iv_signals()
    
    # 總結
    print("\n" + "="*80)
    print("測試總結")
    print("="*80)
    
    passed = sum(1 for v in results.values() if v)
    failed = sum(1 for v in results.values() if not v)
    
    for bug_id, passed_test in results.items():
        status = "✓ 通過" if passed_test else "❌ 失敗"
        print(f"{bug_id}: {status}")
    
    print(f"\n總計: {passed} 通過, {failed} 失敗")
    
    if failed > 0:
        print("\n✓ 探索性測試完成：發現 bug 存在（預期結果）")
        print("下一步：實施修復")
    else:
        print("\n⚠ 警告：所有測試都通過了")
        print("這可能意味著 bug 已經被修復，或測試邏輯需要調整")
    
    return failed > 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
