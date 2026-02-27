import math
from scipy.stats import norm

def black_scholes(S, K, T, r, sigma, option_type='call'):
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    if option_type == 'call':
        return S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
    else:
        return K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)

# Parameters
S = 6.18
r = 0.0418
T = 14 / 365.0  # ~2 weeks (2026-02-27)
sigma = 1.30  # 130% HV as proxy for IV

strikes = [6.0, 7.0, 8.0, 9.0, 10.0, 11.0]

print(f"UVIX Repair Analysis (Price: ${S}, Cost: $11, Expiry: 14 days, IV: 130%)")
print("-" * 60)
print(f"{'Strike':<10} {'Premium':<10} {'Lower Cost To':<15} {'Assignment Loss':<15}")

for K in strikes:
    premium = black_scholes(S, K, T, r, sigma)
    new_cost = 11.0 - premium
    loss_if_assigned = 11.0 - K - premium
    print(f"{K:<10.1f} ${premium:<9.2f} ${new_cost:<14.2f} ${loss_if_assigned:<14.2f}")

print("-" * 60)
# Stock Repair Calculation (1:2 Ratio Spread)
# Buy 1 $7 Call, Sell 2 $9 Calls
p_buy_7 = black_scholes(S, 7, T, r, sigma)
p_sell_9 = black_scholes(S, 9, T, r, sigma)
net_cost = p_buy_7 - 2 * p_sell_9
print(f"Stock Repair Strategy (1x $7 Call / 2x $9 Calls):")
print(f"  Net Cost: ${net_cost:.2f}")
print(f"  Max Recovery at $9: ${2.0 - net_cost:.2f} per share")
print(f"  Effective Breakeven: ${11.0 - (2.0 - net_cost):.2f}")
