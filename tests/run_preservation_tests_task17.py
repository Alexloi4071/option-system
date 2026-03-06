# -*- coding: utf-8 -*-
"""
Run preservation tests relevant to Task 17.5
- IVNormalizer logic preservation (Requirement 3.11)
- Autonomous calculation modules preservation (Requirement 3.3)
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from data_layer.data_fetcher import IVNormalizer
from calculation_layer.module15_black_scholes import BlackScholesCalculator


def test_iv_normalizer_decimal_to_percentage():
    """
    Test that IVNormalizer converts decimal format (0-1) to percentage (0-100)
    Requirement 3.11
    """
    print("\n" + "="*80)
    print("PRESERVATION TEST 1: IVNormalizer Decimal to Percentage Conversion")
    print("="*80)
    
    test_cases = [
        (0.25, 25.0),
        (0.35, 35.0),
        (0.50, 50.0),
        (0.15, 15.0),
        (0.75, 75.0),
    ]
    
    all_passed = True
    
    for iv_decimal, expected_percentage in test_cases:
        result = IVNormalizer.normalize_iv(iv_decimal, source='test')
        
        print(f"\nTest: {iv_decimal} (decimal) -> {expected_percentage}% (percentage)")
        print(f"  Result: {result['normalized_iv']}%")
        print(f"  Was decimal: {result.get('was_decimal')}")
        
        # Check conversion
        if abs(result['normalized_iv'] - expected_percentage) < 0.01:
            print(f"  ✅ PASS: Conversion correct")
        else:
            print(f"  ❌ FAIL: Expected {expected_percentage}%, got {result['normalized_iv']}%")
            all_passed = False
        
        # Check format detection
        if result.get('was_decimal') == True:
            print(f"  ✅ PASS: Format detected as decimal")
        else:
            print(f"  ❌ FAIL: Format should be detected as decimal")
            all_passed = False
    
    print("\n" + "="*80)
    if all_passed:
        print("✅ PRESERVATION TEST 1 PASSED: IVNormalizer decimal conversion preserved")
    else:
        print("❌ PRESERVATION TEST 1 FAILED: IVNormalizer logic changed")
    print("="*80)
    
    return all_passed


def test_iv_normalizer_percentage_unchanged():
    """
    Test that IVNormalizer keeps percentage format (1-100) unchanged
    Requirement 3.11
    """
    print("\n" + "="*80)
    print("PRESERVATION TEST 2: IVNormalizer Percentage Format Unchanged")
    print("="*80)
    
    test_cases = [25.0, 35.0, 50.0, 15.0, 75.0]
    
    all_passed = True
    
    for iv_percentage in test_cases:
        result = IVNormalizer.normalize_iv(iv_percentage, source='test')
        
        print(f"\nTest: {iv_percentage}% (percentage) -> {iv_percentage}% (unchanged)")
        print(f"  Result: {result['normalized_iv']}%")
        print(f"  Was decimal: {result.get('was_decimal')}")
        
        # Check unchanged
        if abs(result['normalized_iv'] - iv_percentage) < 0.01:
            print(f"  ✅ PASS: Value unchanged")
        else:
            print(f"  ❌ FAIL: Expected {iv_percentage}%, got {result['normalized_iv']}%")
            all_passed = False
        
        # Check format detection
        if result.get('was_decimal') == False:
            print(f"  ✅ PASS: Format detected as percentage")
        else:
            print(f"  ❌ FAIL: Format should be detected as percentage")
            all_passed = False
    
    print("\n" + "="*80)
    if all_passed:
        print("✅ PRESERVATION TEST 2 PASSED: IVNormalizer percentage format preserved")
    else:
        print("❌ PRESERVATION TEST 2 FAILED: IVNormalizer logic changed")
    print("="*80)
    
    return all_passed


def test_autonomous_black_scholes_consistency():
    """
    Test that Black-Scholes calculator produces consistent results
    Requirement 3.3
    """
    print("\n" + "="*80)
    print("PRESERVATION TEST 3: Autonomous Black-Scholes Consistency")
    print("="*80)
    
    bs_calculator = BlackScholesCalculator()
    
    # Standard test parameters
    stock_price = 100.0
    strike_price = 105.0
    time_to_expiration = 0.5
    risk_free_rate = 0.05
    volatility = 0.25
    
    print(f"\nTest Parameters:")
    print(f"  Stock Price: ${stock_price}")
    print(f"  Strike Price: ${strike_price}")
    print(f"  Time to Expiration: {time_to_expiration} years")
    print(f"  Risk-Free Rate: {risk_free_rate * 100}%")
    print(f"  Volatility: {volatility * 100}%")
    
    # Calculate call option price twice
    result1 = bs_calculator.calculate_option_price(
        stock_price=stock_price,
        strike_price=strike_price,
        time_to_expiration=time_to_expiration,
        risk_free_rate=risk_free_rate,
        volatility=volatility,
        option_type='call'
    )
    
    result2 = bs_calculator.calculate_option_price(
        stock_price=stock_price,
        strike_price=strike_price,
        time_to_expiration=time_to_expiration,
        risk_free_rate=risk_free_rate,
        volatility=volatility,
        option_type='call'
    )
    
    price1 = result1.option_price
    price2 = result2.option_price
    
    print(f"\nResults:")
    print(f"  First calculation: ${price1:.4f}")
    print(f"  Second calculation: ${price2:.4f}")
    print(f"  Difference: ${abs(price1 - price2):.6f}")
    
    # Check consistency (should be identical)
    if abs(price1 - price2) < 0.0001:
        print(f"\n✅ PRESERVATION TEST 3 PASSED: Black-Scholes produces consistent results")
        print("="*80)
        return True
    else:
        print(f"\n❌ PRESERVATION TEST 3 FAILED: Black-Scholes results inconsistent")
        print("="*80)
        return False


def main():
    """Run all preservation tests for Task 17.5"""
    print("\n" + "="*80)
    print("TASK 17.5: Preservation Tests Verification")
    print("="*80)
    print("\nRunning preservation tests to ensure no regressions...")
    
    results = []
    
    # Test 1: IVNormalizer decimal to percentage
    results.append(("IVNormalizer Decimal Conversion", test_iv_normalizer_decimal_to_percentage()))
    
    # Test 2: IVNormalizer percentage unchanged
    results.append(("IVNormalizer Percentage Format", test_iv_normalizer_percentage_unchanged()))
    
    # Test 3: Black-Scholes consistency
    results.append(("Black-Scholes Consistency", test_autonomous_black_scholes_consistency()))
    
    # Summary
    print("\n" + "="*80)
    print("PRESERVATION TESTS SUMMARY")
    print("="*80)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
        if not passed:
            all_passed = False
    
    print("\n" + "="*80)
    if all_passed:
        print("✅ ALL PRESERVATION TESTS PASSED")
        print("\nConclusion:")
        print("  - IVNormalizer logic is preserved (decimal 0-1 → percentage 0-100)")
        print("  - Autonomous calculation modules produce consistent results")
        print("  - No regressions detected in Task 17 implementation")
    else:
        print("❌ SOME PRESERVATION TESTS FAILED")
        print("\nAction Required:")
        print("  - Review failed tests and investigate regressions")
        print("  - Ensure Task 17 implementation preserves existing behavior")
    print("="*80 + "\n")
    
    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
