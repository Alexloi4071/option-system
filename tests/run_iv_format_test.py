# -*- coding: utf-8 -*-
"""
Simple test runner for IV format consistency test (without pytest)
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from data_layer.data_fetcher import IVNormalizer
from calculation_layer.module15_black_scholes import BlackScholesCalculator


def test_iv_format_consistency():
    """
    Test IV format consistency between IBKR (decimal) and Yahoo (percentage)
    """
    bs_calculator = BlackScholesCalculator()
    
    # Standard option parameters for testing
    stock_price = 100.0
    strike_price = 105.0
    time_to_expiration = 0.5  # 6 months
    risk_free_rate = 0.05  # 5%
    option_type = 'call'
    
    # Simulate IBKR data source (decimal format)
    ibkr_iv = 0.25  # 25% in decimal format
    
    # Simulate Yahoo Finance data source (percentage format)
    yahoo_iv = 25.0  # 25% in percentage format
    
    print("\n" + "="*80)
    print("BUG EXPLORATION: Multi-Source IV Format Inconsistency")
    print("="*80)
    print(f"\nScenario: Same volatility (25%) from different sources")
    print(f"  IBKR format:  {ibkr_iv} (decimal)")
    print(f"  Yahoo format: {yahoo_iv} (percentage)")
    
    # Step 1: Normalize both IVs
    ibkr_normalized = IVNormalizer.normalize_iv(ibkr_iv, source='ibkr')
    yahoo_normalized = IVNormalizer.normalize_iv(yahoo_iv, source='yahoo')
    
    print(f"\nAfter IVNormalizer:")
    print(f"  IBKR:  {ibkr_normalized['normalized_iv']}% (was_decimal: {ibkr_normalized['was_decimal']})")
    print(f"  Yahoo: {yahoo_normalized['normalized_iv']}% (was_decimal: {yahoo_normalized['was_decimal']})")
    
    # Step 2: Calculate Black-Scholes with normalized IVs (what the fix should do)
    ibkr_iv_normalized_decimal = ibkr_normalized['normalized_iv'] / 100.0
    yahoo_iv_normalized_decimal = yahoo_normalized['normalized_iv'] / 100.0
    
    bs_result_ibkr = bs_calculator.calculate_option_price(
        stock_price=stock_price,
        strike_price=strike_price,
        time_to_expiration=time_to_expiration,
        risk_free_rate=risk_free_rate,
        volatility=ibkr_iv_normalized_decimal,
        option_type=option_type
    )
    
    bs_result_yahoo = bs_calculator.calculate_option_price(
        stock_price=stock_price,
        strike_price=strike_price,
        time_to_expiration=time_to_expiration,
        risk_free_rate=risk_free_rate,
        volatility=yahoo_iv_normalized_decimal,
        option_type=option_type
    )
    
    price_ibkr = bs_result_ibkr.option_price
    price_yahoo = bs_result_yahoo.option_price
    
    print(f"\nBlack-Scholes Results (WITH normalization):")
    print(f"  IBKR IV=0.25 -> 25% -> 0.25:  Option Price = ${price_ibkr:.4f}")
    print(f"  Yahoo IV=25.0 -> 25% -> 0.25: Option Price = ${price_yahoo:.4f}")
    
    price_diff = abs(price_ibkr - price_yahoo)
    print(f"  Difference: ${price_diff:.4f}")
    
    # Check if prices are consistent (within 0.01)
    print("\n" + "="*80)
    print("TEST RESULT:")
    print("="*80)
    
    if price_diff < 0.01:
        print(f"\n✅ TEST PASSED: Prices are consistent (difference: ${price_diff:.4f})")
        print(f"   IBKR IV=0.25 -> ${price_ibkr:.4f}")
        print(f"   Yahoo IV=25.0 -> ${price_yahoo:.4f}")
        print(f"\n   This confirms Bug 1.12 is FIXED:")
        print(f"   - IVNormalizer correctly unifies both formats to percentage")
        print(f"   - Black-Scholes produces consistent results")
        print(f"   - No 100x calculation errors")
        return True
    else:
        print(f"\n❌ TEST FAILED: Prices differ by ${price_diff:.4f}")
        print(f"   IBKR IV=0.25 -> ${price_ibkr:.4f}")
        print(f"   Yahoo IV=25.0 -> ${price_yahoo:.4f}")
        print(f"\n   Bug 1.12 still exists: IV format inconsistency causes calculation errors")
        return False


if __name__ == '__main__':
    print("\n" + "="*80)
    print("Bug Exploration Test - IV Format Consistency")
    print("="*80)
    
    try:
        success = test_iv_format_consistency()
        print("\n" + "="*80 + "\n")
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
        print("\n" + "="*80 + "\n")
        sys.exit(1)
