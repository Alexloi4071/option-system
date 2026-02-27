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
S = 16.49
r = 0.0418
T = 13 / 365.0  # ~2 weeks (2026-02-27)
sigma = 0.50  # Estimated 50% IV for HIMS

strikes = [16.5, 17.0, 17.5, 18.0, 18.5, 19.0, 19.5, 20.0]

print(f"HIMS Short Call Theoretical Analysis (Price: ${S}, Expiry: 13 days, Est. IV: 50%)")
print("-" * 65)
print(f"{'Strike':<10} {'Premium':<10} {'ROI (2w)':<12} {'Annualized ROI':<15} {'Delta (Est)':<10}")

for K in strikes:
    premium = black_scholes(S, K, T, r, sigma)
    # Delta approximation
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    delta = norm.cdf(d1)
    
    roi = (premium / S) * 100
    ann_roi = roi * (365 / 13)
    
    print(f"{K:<10.1f} ${premium:<9.2f} {roi:<11.2f}% {ann_roi:<14.2f}% {delta:<10.2f}")

print("-" * 65)
print("Recommendation: Strike $18.0 - $19.0 balance safety and yield.")
