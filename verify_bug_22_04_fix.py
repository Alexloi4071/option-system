"""驗證 BUG-22-04 修復"""
import sys
sys.path.insert(0, '.')

from calculation_layer.module22_optimal_strike import OptimalStrikeCalculator

print("="*60)
print("驗證 BUG-22-04 修復: _normalize_iv 3.0-5.0 範圍處理")
print("="*60)

calc = OptimalStrikeCalculator()
test_values = [3.0, 3.5, 4.0, 4.5, 5.0]

all_passed = True
for v in test_values:
    result = calc._normalize_iv(v)
    expected = v
    passed = (result == expected)
    status = "✓ PASS" if passed else "❌ FAIL"
    print(f"raw_iv={v}: result={result} (expected={expected}) - {status}")
    if not passed:
        all_passed = False

print("\n" + "="*60)
if all_passed:
    print("✅ 所有測試通過 - BUG-22-04 已修復")
else:
    print("❌ 部分測試失敗 - BUG-22-04 仍存在")
print("="*60)
