"""驗證 BUG-17-03 修復: Newton-Raphson 相對誤差收斂"""
import sys
sys.path.insert(0, '.')

from calculation_layer.module17_implied_volatility import ImpliedVolatilityCalculator

print("="*60)
print("驗證 BUG-17-03 修復: 相對誤差收斂條件")
print("="*60)

calc = ImpliedVolatilityCalculator()

# 測試 1: 高價期權
print("\n測試 1: 高價期權 ($50)")
print("-"*60)

result_high = calc.calculate_implied_volatility(
    market_price=50.0,
    stock_price=100.0,
    strike_price=100.0,
    time_to_expiration=1.0,
    risk_free_rate=0.05,
    option_type='call'
)

print(f"迭代次數: {result_high.iterations}")
print(f"是否收斂: {result_high.converged}")
print(f"隱含波動率: {result_high.implied_volatility*100:.2f}%")
print(f"價格差異: ${abs(result_high.price_difference):.6f}")

if result_high.iterations < 30:
    print(f"✓ PASS - 迭代次數 {result_high.iterations} < 30（高效收斂）")
    test1_pass = True
else:
    print(f"❌ FAIL - 迭代次數 {result_high.iterations} >= 30（收斂過慢）")
    test1_pass = False

# 測試 2: 低價期權（更合理的場景）
print("\n測試 2: 低價期權 ($0.50)")
print("-"*60)

result_low = calc.calculate_implied_volatility(
    market_price=0.50,
    stock_price=100.0,
    strike_price=105.0,  # 稍微價外
    time_to_expiration=0.25,  # 3 個月
    risk_free_rate=0.05,
    option_type='call'
)

print(f"迭代次數: {result_low.iterations}")
print(f"是否收斂: {result_low.converged}")
print(f"隱含波動率: {result_low.implied_volatility*100:.2f}%")
print(f"價格差異: ${abs(result_low.price_difference):.6f}")

if result_low.converged:
    print(f"✓ PASS - 成功收斂")
    test2_pass = True
else:
    print(f"❌ FAIL - 未收斂")
    test2_pass = False

# 測試 3: 正常價格期權（確保不影響）
print("\n測試 3: 正常價格期權 ($5)")
print("-"*60)

result_normal = calc.calculate_implied_volatility(
    market_price=5.0,
    stock_price=100.0,
    strike_price=100.0,
    time_to_expiration=0.5,
    risk_free_rate=0.05,
    option_type='call'
)

print(f"迭代次數: {result_normal.iterations}")
print(f"是否收斂: {result_normal.converged}")
print(f"隱含波動率: {result_normal.implied_volatility*100:.2f}%")

if result_normal.converged:
    print(f"✓ PASS - 正常價格範圍不受影響")
    test3_pass = True
else:
    print(f"❌ FAIL - 正常價格範圍受影響")
    test3_pass = False

# 總結
print("\n" + "="*60)
print("測試總結")
print("="*60)

all_passed = test1_pass and test2_pass and test3_pass

if all_passed:
    print("✅ 所有測試通過 - BUG-17-03 已修復")
    print("\n修復效果:")
    print("  - 高價期權收斂效率提升")
    print("  - 低價期權收斂可靠性提升")
    print("  - 正常價格範圍不受影響")
else:
    print("❌ 部分測試失敗 - BUG-17-03 仍存在問題")
    if not test1_pass:
        print("  - 高價期權收斂仍然過慢")
    if not test2_pass:
        print("  - 低價期權收斂仍有問題")
    if not test3_pass:
        print("  - 正常價格範圍受到影響")

print("="*60)
