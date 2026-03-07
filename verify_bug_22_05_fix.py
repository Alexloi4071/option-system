#!/usr/bin/env python3
"""
驗證 BUG-22-05 修復：composite_score 上限

測試場景：
1. weighted_score + bonus_score > 100
2. 驗證總分被限制在 100
3. 正常情況（總分 <= 100）- Preservation
"""

import sys
from pathlib import Path

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from calculation_layer.module22_optimal_strike import OptimalStrikeCalculator, StrikeAnalysis


def test_bug_22_05_composite_score_cap():
    """測試 composite_score 上限"""
    print("\n" + "="*80)
    print("BUG-22-05 驗證：composite_score 上限")
    print("="*80)
    
    calc = OptimalStrikeCalculator()
    
    # 測試 1: 總分超過 100
    print("\n測試 1: weighted_score=90, bonus_score=15 (總分=105)")
    print("-" * 80)
    
    # 創建 StrikeAnalysis，設置各項評分使 weighted_score = 90
    # weighted_score = liquidity * 0.3 + greeks * 0.3 + iv * 0.2 + risk_reward * 0.2
    # 設置所有評分為 90，則 weighted_score = 90
    analysis = StrikeAnalysis(
        strike=100.0,
        option_type='call',
        bid=5.0,
        ask=5.2,
        last_price=5.1,
        delta=0.50,
        gamma=0.02,
        theta=-0.05,
        vega=0.25,
        volume=1000,
        open_interest=5000,
        bid_ask_spread_pct=4.0,
        iv=30.0,
        iv_rank=50.0,
        liquidity_score=90.0,
        greeks_score=90.0,
        iv_score=90.0,
        risk_reward_score=90.0,
        bonus_score=15.0  # 異動加分
    )
    
    print(f"輸入:")
    print(f"  liquidity_score = {analysis.liquidity_score}")
    print(f"  greeks_score = {analysis.greeks_score}")
    print(f"  iv_score = {analysis.iv_score}")
    print(f"  risk_reward_score = {analysis.risk_reward_score}")
    print(f"  bonus_score = {analysis.bonus_score}")
    
    # 計算 weighted_score
    weighted_score = (
        analysis.liquidity_score * 0.3 +
        analysis.greeks_score * 0.3 +
        analysis.iv_score * 0.2 +
        analysis.risk_reward_score * 0.2
    )
    print(f"  weighted_score = {weighted_score:.2f}")
    print(f"  未限制的總分 = {weighted_score + analysis.bonus_score:.2f}")
    
    composite_score = calc.calculate_composite_score(analysis, 'long_call')
    
    print(f"\n輸出:")
    print(f"  composite_score = {composite_score}")
    
    # 驗證總分被限制在 100
    assert composite_score == 100.0, f"應為 100.0，實際: {composite_score}"
    
    print(f"\n✅ 驗證通過: 總分被限制在 100")
    
    # 測試 2: 總分剛好 100
    print("\n\n測試 2: weighted_score=85, bonus_score=15 (總分=100)")
    print("-" * 80)
    
    analysis.liquidity_score = 85.0
    analysis.greeks_score = 85.0
    analysis.iv_score = 85.0
    analysis.risk_reward_score = 85.0
    analysis.bonus_score = 15.0
    
    weighted_score = (
        analysis.liquidity_score * 0.3 +
        analysis.greeks_score * 0.3 +
        analysis.iv_score * 0.2 +
        analysis.risk_reward_score * 0.2
    )
    print(f"  weighted_score = {weighted_score:.2f}")
    print(f"  bonus_score = {analysis.bonus_score}")
    print(f"  總分 = {weighted_score + analysis.bonus_score:.2f}")
    
    composite_score = calc.calculate_composite_score(analysis, 'long_call')
    
    print(f"\n輸出:")
    print(f"  composite_score = {composite_score}")
    
    # 驗證總分為 100
    assert composite_score == 100.0, f"應為 100.0，實際: {composite_score}"
    
    print(f"\n✅ 驗證通過: 總分為 100（邊界值）")
    
    # 測試 3: 總分小於 100 - Preservation
    print("\n\n測試 3: weighted_score=70, bonus_score=10 (總分=80) - Preservation")
    print("-" * 80)
    
    analysis.liquidity_score = 70.0
    analysis.greeks_score = 70.0
    analysis.iv_score = 70.0
    analysis.risk_reward_score = 70.0
    analysis.bonus_score = 10.0
    
    weighted_score = (
        analysis.liquidity_score * 0.3 +
        analysis.greeks_score * 0.3 +
        analysis.iv_score * 0.2 +
        analysis.risk_reward_score * 0.2
    )
    print(f"  weighted_score = {weighted_score:.2f}")
    print(f"  bonus_score = {analysis.bonus_score}")
    print(f"  總分 = {weighted_score + analysis.bonus_score:.2f}")
    
    composite_score = calc.calculate_composite_score(analysis, 'long_call')
    
    print(f"\n輸出:")
    print(f"  composite_score = {composite_score}")
    
    expected_score = weighted_score + analysis.bonus_score
    
    # 驗證總分未被限制
    assert composite_score == round(expected_score, 2), \
        f"應為 {expected_score:.2f}，實際: {composite_score}"
    
    print(f"\n✅ 驗證通過: 總分 < 100 時不受影響")
    
    # 測試 4: 無 bonus_score - Preservation
    print("\n\n測試 4: weighted_score=75, bonus_score=0 - Preservation")
    print("-" * 80)
    
    analysis.liquidity_score = 75.0
    analysis.greeks_score = 75.0
    analysis.iv_score = 75.0
    analysis.risk_reward_score = 75.0
    analysis.bonus_score = 0.0
    
    weighted_score = (
        analysis.liquidity_score * 0.3 +
        analysis.greeks_score * 0.3 +
        analysis.iv_score * 0.2 +
        analysis.risk_reward_score * 0.2
    )
    print(f"  weighted_score = {weighted_score:.2f}")
    print(f"  bonus_score = {analysis.bonus_score}")
    
    composite_score = calc.calculate_composite_score(analysis, 'long_call')
    
    print(f"\n輸出:")
    print(f"  composite_score = {composite_score}")
    
    # 驗證總分等於 weighted_score
    assert composite_score == round(weighted_score, 2), \
        f"應為 {weighted_score:.2f}，實際: {composite_score}"
    
    print(f"\n✅ 驗證通過: 無 bonus_score 時計算正確")
    
    print("\n" + "="*80)
    print("✅ BUG-22-05 修復驗證完成：所有測試通過")
    print("="*80)


if __name__ == '__main__':
    test_bug_22_05_composite_score_cap()
