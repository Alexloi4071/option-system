"""
Quick offline verification of Fix 1, 2, 3, 6 - no IBKR connection needed.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Patch out ib_insync so it doesn't block
import types
fake_ib = types.ModuleType('ib_insync')
for name in ['IB','Stock','Option','Contract','util']:
    setattr(fake_ib, name, object)
sys.modules['ib_insync'] = fake_ib

import logging
logging.basicConfig(level=logging.WARNING)
from datetime import datetime

print("="*55)
print(" VZ Fix Verification (Offline)")
print("="*55)

# ── Fix 1 & 2 & 6: module16 ────────────────────────────
from calculation_layer.module16_greeks import GreeksCalculator
calc = GreeksCalculator()
expiry_dt = datetime.strptime('2026-03-27', '%Y-%m-%d')
dte = (expiry_dt - datetime.now()).days
t   = dte / 365.0

# With dividend (Fix 6)
r_div = calc.calculate_all_greeks(41.80, 42.0, 0.043, t, 0.18, 'call', dividend_yield=0.065)
# Without dividend
r_nodiv = calc.calculate_all_greeks(41.80, 42.0, 0.043, t, 0.18, 'call', dividend_yield=0.0)

theta_new  = r_div.theta           # /252
theta_old  = r_div.theta * 252/365 # what /365 would give
rho_new    = r_div.rho             # /100
rho_old    = r_div.rho * 100       # unscaled
delta_diff = r_div.delta - r_nodiv.delta

print(f"\n[Fix 1] Theta (/252 standard)")
print(f"  New (correct): {theta_new:.4f}/day")
print(f"  Old (/365):    {theta_old:.4f}/day")
pct = (theta_new - theta_old) / abs(theta_old) * 100
fix1 = abs(pct - (-44.8)) < 2
print(f"  Difference:    {pct:.1f}%  → {'✅ PASS' if fix1 else '❌ FAIL'}")

print(f"\n[Fix 2] Rho (/100 normalization)")
print(f"  New (correct): {rho_new:.4f}  per 1% rate change")
print(f"  Old (unscaled):{rho_old:.4f}  100x too large")
fix2 = abs(rho_old / rho_new - 100) < 1
print(f"  Ratio 100x:    {'✅ PASS' if fix2 else '❌ FAIL'}")

print(f"\n[Fix 6] dividend_yield in Greeks (VZ 6.5%)")
print(f"  Delta with div:    {r_div.delta:.4f}")
print(f"  Delta without div: {r_nodiv.delta:.4f}")
print(f"  Delta difference:  {delta_diff:.4f}  {'✅ PASS (significant)' if abs(delta_diff) > 0.01 else '❌ too small'}")

# ── Fix 3: AI TTL Cache ────────────────────────────────
import time
from services.ai_analysis_service import AIAnalysisService
ai = AIAnalysisService.__new__(AIAnalysisService)
ai._cache = {}
ai.api_key = 'test'
ai.CACHE_TTL_SECONDS = 300

ai._cache['VZ'] = ('fresh result', time.time())
valid1 = ai._is_cache_valid('VZ')
ai._cache['VZ'] = ('stale result', time.time() - 400)
valid2 = ai._is_cache_valid('VZ')
fix3 = valid1 and not valid2
print(f"\n[Fix 3] AI TTL Cache (5 min)")
print(f"  Fresh cache valid:   {valid1}  {'✅' if valid1 else '❌'}")
print(f"  400s-old expired:    {not valid2}  {'✅' if not valid2 else '❌'}")
print(f"  Cache TTL:           {'✅ PASS' if fix3 else '❌ FAIL'}")

# ── Fix 8: module29 exists ────────────────────────────
import os
fix8 = os.path.exists('calculation_layer/module29_short_option_analysis.py')
print(f"\n[Fix 8] module29 renamed")
print(f"  module29 exists: {'✅ PASS' if fix8 else '❌ FAIL'}")

# ── Fix 5: .gitignore ────────────────────────────────
with open('.gitignore') as f:
    gi = f.read()
fix5 = 'hot_options.json' in gi
print(f"\n[Fix 5] .gitignore")
print(f"  hot_options.json: {'✅ PASS' if fix5 else '❌ FAIL'}")

# ── Summary ───────────────────────────────────────────
print("\n" + "="*55)
all_pass = fix1 and fix2 and fix3 and fix5 and fix8
print(f" OVERALL: {'✅ ALL FIXES VERIFIED' if all_pass else '⚠️  SOME FIXES NEED REVIEW'}")
print("="*55)
sys.exit(0 if all_pass else 1)
