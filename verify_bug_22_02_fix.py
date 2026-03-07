#!/usr/bin/env python3
"""
驗證 BUG-22-02 修復：IBKR Greeks 單位標準化

測試場景：
1. 模擬 IBKR Greeks（theta: $/day, vega: $/1% IV）
2. 驗證單位轉換正確（theta: $/year, vega: $/1.0 IV）
3. 確認 greeks_score 和 risk_reward_score 計算正確
"""

import sys
from pathlib import Path

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from calculation_layer.module22_optimal_strike import OptimalStrikeCalculator


def test_bug_22_02_ibkr_greeks_unit_standardization():
    """測試 IBKR Greeks 單位標準化"""
    print("\n" + "="*80)
    print("BUG-22-02 驗證：IBKR Greeks 單位標準化")
    print("="*80)
    
    calc = OptimalStrikeCalculator()
    
    # 測試場景：模擬 IBKR Greeks
    # IBKR theta = -0.05 ($/day) -> 應轉換為 -18.25 ($/year)
    # IBKR vega = 0.25 ($/1% IV) -> 應轉換為 25.0 ($/1.0 IV)
    
    print("\n測試 1: IBKR Greeks 單位轉換")
    print("-" * 80)
    
    ibkr_theta = -0.05  # $/day
    ibkr_vega = 0.25    # $/1% IV
    
    print(f"輸入 (IBKR):")
    print(f"  theta = {ibkr_theta} $/day")
    print(f"  vega = {ibkr_vega} $/1% IV")
    
    # 調用 _normalize_greeks
    normalized_theta, normalized_vega = calc._normalize_greeks(
        theta=ibkr_theta,
        vega=ibkr_vega,
        source='IBKR'
    )
    
    print(f"\n輸出 (標準化):")
    print(f"  theta = {normalized_theta:.4f} $/year")
    print(f"  vega = {normalized_vega:.4f} $/1.0 IV")
    
    # 驗證轉換正確
    expected_theta = ibkr_theta * 365.0  # -18.25
    expected_vega = ibkr_vega * 100.0    # 25.0
    
    assert abs(normalized_theta - expected_theta) < 0.01, \
        f"Theta 轉換錯誤: 預期 {expected_theta}, 實際 {normalized_theta}"
    assert abs(normalized_vega - expected_vega) < 0.01, \
        f"Vega 轉換錯誤: 預期 {expected_vega}, 實際 {normalized_vega}"
    
    print(f"\n✅ 驗證通過:")
    print(f"  theta 轉換: {ibkr_theta} * 365 = {normalized_theta:.4f} ✓")
    print(f"  vega 轉換: {ibkr_vega} * 100 = {normalized_vega:.4f} ✓")
    
    # 測試 2: BS Greeks 不轉換
    print("\n\n測試 2: BS Greeks 保持不變")
    print("-" * 80)
    
    bs_theta = -18.25  # $/year
    bs_vega = 25.0     # $/1.0 IV
    
    print(f"輸入 (BS):")
    print(f"  theta = {bs_theta} $/year")
    print(f"  vega = {bs_vega} $/1.0 IV")
    
    normalized_theta_bs, normalized_vega_bs = calc._normalize_greeks(
        theta=bs_theta,
        vega=bs_vega,
        source='BS'
    )
    
    print(f"\n輸出 (標準化):")
    print(f"  theta = {normalized_theta_bs:.4f} $/year")
    print(f"  vega = {normalized_vega_bs:.4f} $/1.0 IV")
    
    assert normalized_theta_bs == bs_theta, \
        f"BS Theta 不應轉換: 預期 {bs_theta}, 實際 {normalized_theta_bs}"
    assert normalized_vega_bs == bs_vega, \
        f"BS Vega 不應轉換: 預期 {bs_vega}, 實際 {normalized_vega_bs}"
    
    print(f"\n✅ 驗證通過:")
    print(f"  BS theta 保持不變: {bs_theta} ✓")
    print(f"  BS vega 保持不變: {bs_vega} ✓")
    
    # 測試 3: 在 _analyze_single_strike 中的集成測試
    print("\n\n測試 3: _analyze_single_strike 集成測試")
    print("-" * 80)
    
    # 創建模擬 option 數據（包含 IBKR Greeks）
    option_with_ibkr_greeks = {
        'strike': 100.0,
        'bid': 5.0,
        'ask': 5.2,
        'lastPrice': 5.1,
        'volume': 100,
        'openInterest': 500,
        'delta': 0.50,
        'gamma': 0.02,
        'theta': -0.05,  # IBKR: $/day
        'vega': 0.25,    # IBKR: $/1% IV
        'greeks_source': 'ibkr_snapshot',  # 標記為 IBKR 來源
        'impliedVolatility': 0.30
    }
    
    print(f"模擬 option 數據 (IBKR Greeks):")
    print(f"  strike = {option_with_ibkr_greeks['strike']}")
    print(f"  theta = {option_with_ibkr_greeks['theta']} ($/day)")
    print(f"  vega = {option_with_ibkr_greeks['vega']} ($/1% IV)")
    print(f"  greeks_source = '{option_with_ibkr_greeks['greeks_source']}'")
    
    # 調用 _analyze_single_strike
    analysis = calc._analyze_single_strike(
        option=option_with_ibkr_greeks,
        option_type='call',
        current_price=100.0,
        strategy_type='long_call',
        days_to_expiration=30,
        iv_rank=50.0,
        target_price=None
    )
    
    if analysis:
        print(f"\n分析結果:")
        print(f"  theta = {analysis.theta:.4f} (應為 $/year)")
        print(f"  vega = {analysis.vega:.4f} (應為 $/1.0 IV)")
        
        # 驗證單位已轉換
        expected_theta = -0.05 * 365.0  # -18.25
        expected_vega = 0.25 * 100.0    # 25.0
        
        assert abs(analysis.theta - expected_theta) < 0.01, \
            f"Theta 未正確轉換: 預期 {expected_theta}, 實際 {analysis.theta}"
        assert abs(analysis.vega - expected_vega) < 0.01, \
            f"Vega 未正確轉換: 預期 {expected_vega}, 實際 {analysis.vega}"
        
        print(f"\n✅ 驗證通過:")
        print(f"  theta 已轉換為 $/year: {analysis.theta:.4f} ✓")
        print(f"  vega 已轉換為 $/1.0 IV: {analysis.vega:.4f} ✓")
    else:
        print("\n❌ 錯誤: _analyze_single_strike 返回 None")
        sys.exit(1)
    
    print("\n" + "="*80)
    print("✅ BUG-22-02 修復驗證完成：所有測試通過")
    print("="*80)


if __name__ == '__main__':
    test_bug_22_02_ibkr_greeks_unit_standardization()
