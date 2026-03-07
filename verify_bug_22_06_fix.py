"""驗證 BUG-22-06 修復: Short Put win_probability 計算"""
import sys
sys.path.insert(0, '.')

from calculation_layer.module22_optimal_strike import OptimalStrikeCalculator, StrikeAnalysis

print("="*60)
print("驗證 BUG-22-06 修復: Short Put win_probability")
print("="*60)

calc = OptimalStrikeCalculator()

# 創建測試場景
# Short Put: strike=95, current_price=100, delta=0.30
# 預期: win_probability = 1 - 0.30 = 0.70 (70% 勝率)

# 創建 StrikeAnalysis 物件
analysis = StrikeAnalysis(
    strike=95.0,
    option_type='put',
    bid=2.0,
    ask=2.2,
    last_price=2.1,
    volume=1000,
    open_interest=5000,
    delta=0.30,  # Put delta (正值表示被行使概率)
    gamma=0.05,
    theta=-0.05,
    vega=0.25,
    iv=0.25,
    liquidity_score=80.0,
    greeks_score=70.0,
    iv_score=60.0,
    risk_reward_score=0.0,  # 待計算
    composite_score=0.0
)

# 調用 _calculate_risk_reward_score_v2
current_price = 100.0
strategy_type = 'short_put'
target_price = None
holding_days = 30

print(f"\n測試場景:")
print(f"  策略: {strategy_type}")
print(f"  行使價: {analysis.strike}")
print(f"  當前股價: {current_price}")
print(f"  Delta: {analysis.delta}")

score = calc._calculate_risk_reward_score_v2(
    analysis=analysis,
    current_price=current_price,
    strategy_type=strategy_type,
    target_price=target_price,
    holding_days=holding_days
)

print(f"\n計算結果:")
print(f"  勝率 (win_probability): {analysis.win_probability:.4f}")
print(f"  預期收益 (expected_return): {analysis.expected_return:.2f}")
print(f"  風險回報評分: {score:.2f}")

# 驗證
expected_win_prob = 1.0 - analysis.delta  # 0.70
actual_win_prob = analysis.win_probability

print(f"\n驗證:")
print(f"  預期勝率: {expected_win_prob:.4f} (1 - delta)")
print(f"  實際勝率: {actual_win_prob:.4f}")

if abs(actual_win_prob - expected_win_prob) < 0.0001:
    print(f"  ✓ PASS - Short Put 勝率計算正確")
    print("\n" + "="*60)
    print("✅ BUG-22-06 已修復")
    print("="*60)
else:
    print(f"  ❌ FAIL - Short Put 勝率計算錯誤")
    print("\n" + "="*60)
    print("❌ BUG-22-06 仍存在")
    print("="*60)
