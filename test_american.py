import sys
import os
sys.path.append(os.getcwd())

from calculation_layer.module32_american_pricing import AmericanOptionPricer

pricer = AmericanOptionPricer()
res = pricer.calculate_american_price(
    stock_price=100.0,
    strike_price=100.0,
    risk_free_rate=0.05,
    time_to_expiration=1.0,
    volatility=0.2,
    option_type='put',
    dividend_yield=0.0,
    steps=200
)

print(f"Euro: {res.european_price}, American: {res.american_price}, Premium: {res.early_exercise_premium}")
