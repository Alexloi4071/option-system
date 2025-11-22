# 測試策略計算器的輸出
from calculation_layer.module8_long_put import LongPutCalculator
from calculation_layer.module9_short_call import ShortCallCalculator
from calculation_layer.module10_short_put import ShortPutCalculator

# 測試參數
strike_price = 265.0
put_premium = 6.59
call_premium = 10.95
current_price = 267.44

# 價格場景
price_scenarios = [
    round(current_price * 0.9, 2),  # 240.70
    round(current_price, 2),         # 267.44
    round(current_price * 1.1, 2)    # 294.18
]

print("=" * 70)
print("測試 Long Put 計算器")
print("=" * 70)

long_put_calc = LongPutCalculator()
for i, price in enumerate(price_scenarios, 1):
    result = long_put_calc.calculate(
        strike_price=strike_price,
        option_premium=put_premium,
        stock_price_at_expiry=price,
        calculation_date="2025-11-19"
    )
    result_dict = result.to_dict()
    print(f"\n場景 {i}: 到期股價 = ${price:.2f}")
    print(f"  stock_price_at_expiry: {result_dict.get('stock_price_at_expiry')}")
    print(f"  profit_loss: {result_dict.get('profit_loss')}")
    print(f"  完整字典: {result_dict}")

print("\n" + "=" * 70)
print("測試 Short Call 計算器")
print("=" * 70)

short_call_calc = ShortCallCalculator()
for i, price in enumerate(price_scenarios, 1):
    result = short_call_calc.calculate(
        strike_price=strike_price,
        option_premium=call_premium,
        stock_price_at_expiry=price,
        calculation_date="2025-11-19"
    )
    result_dict = result.to_dict()
    print(f"\n場景 {i}: 到期股價 = ${price:.2f}")
    print(f"  stock_price_at_expiry: {result_dict.get('stock_price_at_expiry')}")
    print(f"  profit_loss: {result_dict.get('profit_loss')}")

print("\n" + "=" * 70)
print("測試 Short Put 計算器")
print("=" * 70)

short_put_calc = ShortPutCalculator()
for i, price in enumerate(price_scenarios, 1):
    result = short_put_calc.calculate(
        strike_price=strike_price,
        option_premium=put_premium,
        stock_price_at_expiry=price,
        calculation_date="2025-11-19"
    )
    result_dict = result.to_dict()
    print(f"\n場景 {i}: 到期股價 = ${price:.2f}")
    print(f"  stock_price_at_expiry: {result_dict.get('stock_price_at_expiry')}")
    print(f"  profit_loss: {result_dict.get('profit_loss')}")
