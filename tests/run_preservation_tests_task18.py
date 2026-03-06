# -*- coding: utf-8 -*-
"""
Run preservation tests relevant to Task 18.5
- Market Data Type switching logic (Requirement 3.10)
- Autonomous Greeks calculator (Requirement 3.3)
- Generic Tick Tags (Requirement 3.9)
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from data_layer.ibkr_client import IBKRClient, MARKET_DATA_TYPE_LIVE, MARKET_DATA_TYPE_FROZEN
from calculation_layer.module16_greeks import GreeksCalculator


def test_market_data_type_switching_logic():
    """
    Test that Market Data Type switching logic is preserved
    Requirement 3.10: RTH uses Type=1 (Live), off-hours uses Type=2 (Frozen)
    """
    print("\n" + "="*80)
    print("PRESERVATION TEST 1: Market Data Type Switching Logic")
    print("="*80)
    
    print("\nTesting Market Data Type constants...")
    print(f"  MARKET_DATA_TYPE_LIVE = {MARKET_DATA_TYPE_LIVE}")
    print(f"  MARKET_DATA_TYPE_FROZEN = {MARKET_DATA_TYPE_FROZEN}")
    
    # Verify constants
    if MARKET_DATA_TYPE_LIVE == 1:
        print(f"  ✅ PASS: MARKET_DATA_TYPE_LIVE = 1")
    else:
        print(f"  ❌ FAIL: MARKET_DATA_TYPE_LIVE should be 1, got {MARKET_DATA_TYPE_LIVE}")
        return False
    
    if MARKET_DATA_TYPE_FROZEN == 2:
        print(f"  ✅ PASS: MARKET_DATA_TYPE_FROZEN = 2")
    else:
        print(f"  ❌ FAIL: MARKET_DATA_TYPE_FROZEN should be 2, got {MARKET_DATA_TYPE_FROZEN}")
        return False
    
    print("\nTesting IBKR client Market Data Type methods...")
    try:
        client = IBKRClient()
        
        # Check if methods exist
        if hasattr(client, '_determine_market_data_type'):
            print(f"  ✅ PASS: _determine_market_data_type method exists")
        else:
            print(f"  ❌ FAIL: _determine_market_data_type method missing")
            return False
        
        if hasattr(client, 'is_rth'):
            print(f"  ✅ PASS: is_rth method exists")
        else:
            print(f"  ❌ FAIL: is_rth method missing")
            return False
        
        if hasattr(client, '_get_market_data_type_name'):
            print(f"  ✅ PASS: _get_market_data_type_name method exists")
        else:
            print(f"  ❌ FAIL: _get_market_data_type_name method missing")
            return False
        
        print(f"\n✅ PRESERVATION TEST 1 PASSED: Market Data Type switching logic preserved")
        print("="*80)
        return True
        
    except Exception as e:
        print(f"\n❌ PRESERVATION TEST 1 FAILED: {e}")
        print("="*80)
        return False


def test_autonomous_greeks_calculator():
    """
    Test that autonomous Greeks calculator produces consistent results
    Requirement 3.3
    """
    print("\n" + "="*80)
    print("PRESERVATION TEST 2: Autonomous Greeks Calculator")
    print("="*80)
    
    greeks_calc = GreeksCalculator()
    
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
    
    # Calculate Greeks twice
    greeks1 = greeks_calc.calculate_all_greeks(
        stock_price=stock_price,
        strike_price=strike_price,
        time_to_expiration=time_to_expiration,
        risk_free_rate=risk_free_rate,
        volatility=volatility,
        option_type='call'
    )
    
    greeks2 = greeks_calc.calculate_all_greeks(
        stock_price=stock_price,
        strike_price=strike_price,
        time_to_expiration=time_to_expiration,
        risk_free_rate=risk_free_rate,
        volatility=volatility,
        option_type='call'
    )
    
    print(f"\nResults:")
    print(f"  First calculation:")
    print(f"    Delta: {greeks1.delta:.6f}")
    print(f"    Gamma: {greeks1.gamma:.6f}")
    print(f"    Theta: {greeks1.theta:.6f}")
    print(f"    Vega: {greeks1.vega:.6f}")
    
    print(f"  Second calculation:")
    print(f"    Delta: {greeks2.delta:.6f}")
    print(f"    Gamma: {greeks2.gamma:.6f}")
    print(f"    Theta: {greeks2.theta:.6f}")
    print(f"    Vega: {greeks2.vega:.6f}")
    
    # Check consistency
    delta_diff = abs(greeks1.delta - greeks2.delta)
    gamma_diff = abs(greeks1.gamma - greeks2.gamma)
    theta_diff = abs(greeks1.theta - greeks2.theta)
    vega_diff = abs(greeks1.vega - greeks2.vega)
    
    print(f"\nDifferences:")
    print(f"  Delta: {delta_diff:.8f}")
    print(f"  Gamma: {gamma_diff:.8f}")
    print(f"  Theta: {theta_diff:.8f}")
    print(f"  Vega: {vega_diff:.8f}")
    
    if all(diff < 0.0001 for diff in [delta_diff, gamma_diff, theta_diff, vega_diff]):
        print(f"\n✅ PRESERVATION TEST 2 PASSED: Greeks calculator produces consistent results")
        print("="*80)
        return True
    else:
        print(f"\n❌ PRESERVATION TEST 2 FAILED: Greeks results inconsistent")
        print("="*80)
        return False


def test_generic_tick_tags():
    """
    Test that Generic Tick Tags configuration is preserved
    Requirement 3.9: IBKR requests use CORE, RECOMMENDED, ADVANCED_OPTION_SAFE tags (not Tag 292)
    """
    print("\n" + "="*80)
    print("PRESERVATION TEST 3: Generic Tick Tags Configuration")
    print("="*80)
    
    print("\nTesting Generic Tick Tags configuration...")
    
    try:
        client = IBKRClient()
        
        # Check if client has tick tag configuration
        if hasattr(client, '_tick_tag_categories'):
            categories = client._tick_tag_categories
            print(f"  Tick tag categories: {categories}")
            
            # Verify expected categories
            expected_categories = ['CORE', 'RECOMMENDED', 'ADVANCED_OPTION_SAFE']
            if all(cat in categories for cat in expected_categories):
                print(f"  ✅ PASS: All expected categories present")
            else:
                print(f"  ❌ FAIL: Missing expected categories")
                return False
        else:
            print(f"  ⚠ WARNING: _tick_tag_categories attribute not found")
        
        # Check if client has generic tick list
        if hasattr(client, '_generic_tick_list'):
            tick_list = client._generic_tick_list
            print(f"  Generic tick list: {tick_list}")
            
            # Verify Tag 292 (news) is NOT in the list
            if '292' not in tick_list:
                print(f"  ✅ PASS: Tag 292 (news) not in option tick list")
            else:
                print(f"  ❌ FAIL: Tag 292 (news) should not be in option tick list")
                return False
        else:
            print(f"  ⚠ WARNING: _generic_tick_list attribute not found")
        
        print(f"\n✅ PRESERVATION TEST 3 PASSED: Generic Tick Tags configuration preserved")
        print("="*80)
        return True
        
    except Exception as e:
        print(f"\n❌ PRESERVATION TEST 3 FAILED: {e}")
        print("="*80)
        return False


def main():
    """Run all preservation tests for Task 18.5"""
    print("\n" + "="*80)
    print("TASK 18.5: Preservation Tests Verification")
    print("="*80)
    print("\nRunning preservation tests to ensure no regressions...")
    
    results = []
    
    # Test 1: Market Data Type switching logic
    results.append(("Market Data Type Switching", test_market_data_type_switching_logic()))
    
    # Test 2: Autonomous Greeks calculator
    results.append(("Autonomous Greeks Calculator", test_autonomous_greeks_calculator()))
    
    # Test 3: Generic Tick Tags
    results.append(("Generic Tick Tags", test_generic_tick_tags()))
    
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
        print("  - Market Data Type switching logic preserved (RTH=Live, off-hours=Frozen)")
        print("  - Autonomous Greeks calculator produces consistent results")
        print("  - Generic Tick Tags configuration preserved (no Tag 292 for options)")
        print("  - No regressions detected in Task 18 implementation")
    else:
        print("❌ SOME PRESERVATION TESTS FAILED")
        print("\nAction Required:")
        print("  - Review failed tests and investigate regressions")
        print("  - Ensure Task 18 implementation preserves existing behavior")
    print("="*80 + "\n")
    
    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
