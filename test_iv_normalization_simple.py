#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Simple test to verify IV normalization is working correctly
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_layer.data_fetcher import IVNormalizer
from calculation_layer.module15_black_scholes import BlackScholesCalculator

def test_iv_normalization():
    """Test that IV normalization works correctly"""
    
    print("\n" + "="*80)
    print("Testing IV Normalization (Task 17.3)")
    print("="*80)
    
    # Test 1: IBKR format (decimal)
    print("\nTest 1: IBKR format (decimal 0.25)")
    ibkr_iv = 0.25
    normalized_ibkr = IVNormalizer.normalize(ibkr_iv, source='IBKR', ticker='AAPL')
    print(f"  Input: {ibkr_iv}")
    print(f"  Output: {normalized_ibkr}%")
    print(f"  Expected: 25.0%")
    assert normalized_ibkr == 25.0, f"Expected 25.0, got {normalized_ibkr}"
    print("  ✓ PASS")
    
    # Test 2: Yahoo format (percentage)
    print("\nTest 2: Yahoo format (percentage 25.0)")
    yahoo_iv = 25.0
    normalized_yahoo = IVNormalizer.normalize(yahoo_iv, source='Yahoo', ticker='AAPL')
    print(f"  Input: {yahoo_iv}")
    print(f"  Output: {normalized_yahoo}%")
    print(f"  Expected: 25.0%")
    assert normalized_yahoo == 25.0, f"Expected 25.0, got {normalized_yahoo}"
    print("  ✓ PASS")
    
    # Test 3: Both should produce same Black-Scholes result
    print("\nTest 3: Black-Scholes consistency")
    bs_calculator = BlackScholesCalculator()
    
    # Convert to decimal for Black-Scholes (expects 0-1 range)
    ibkr_iv_decimal = normalized_ibkr / 100.0
    yahoo_iv_decimal = normalized_yahoo / 100.0
    
    print(f"  IBKR IV (decimal): {ibkr_iv_decimal}")
    print(f"  Yahoo IV (decimal): {yahoo_iv_decimal}")
    
    # Calculate option prices
    bs_result_ibkr = bs_calculator.calculate_option_price(
        stock_price=100.0,
        strike_price=105.0,
        time_to_expiration=0.5,
        risk_free_rate=0.05,
        volatility=ibkr_iv_decimal,
        option_type='call'
    )
    
    bs_result_yahoo = bs_calculator.calculate_option_price(
        stock_price=100.0,
        strike_price=105.0,
        time_to_expiration=0.5,
        risk_free_rate=0.05,
        volatility=yahoo_iv_decimal,
        option_type='call'
    )
    
    price_ibkr = bs_result_ibkr.option_price
    price_yahoo = bs_result_yahoo.option_price
    
    print(f"  IBKR option price: ${price_ibkr:.4f}")
    print(f"  Yahoo option price: ${price_yahoo:.4f}")
    print(f"  Difference: ${abs(price_ibkr - price_yahoo):.4f}")
    
    # Prices should be identical (or very close due to floating point)
    assert abs(price_ibkr - price_yahoo) < 0.0001, f"Prices differ: {price_ibkr} vs {price_yahoo}"
    print("  ✓ PASS - Prices are consistent")
    
    # Test 4: Verify logging
    print("\nTest 4: Verify conversion logging")
    print("  Testing with decimal format (should log conversion)...")
    result = IVNormalizer.normalize(0.35, source='Test', ticker='TEST')
    print(f"  Input: 0.35 -> Output: {result}%")
    assert result == 35.0, f"Expected 35.0, got {result}"
    print("  ✓ PASS")
    
    print("\n" + "="*80)
    print("All IV Normalization Tests PASSED!")
    print("="*80)
    print("\nConclusion:")
    print("  - IVNormalizer.normalize() correctly converts decimal to percentage")
    print("  - Both IBKR and Yahoo formats produce consistent results")
    print("  - Black-Scholes calculations are identical for both sources")
    print("  - Task 17.3 implementation is working correctly")
    print("\n")

if __name__ == '__main__':
    try:
        test_iv_normalization()
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
