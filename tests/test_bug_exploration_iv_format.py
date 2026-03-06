# -*- coding: utf-8 -*-
"""
Bug Exploration Test - IV Format Consistency (Task 6)

Validates: Requirements 1.12, 2.12

CRITICAL: This test MUST FAIL on unfixed code - failure confirms the bug exists.

Bug Condition 1.12: Multi-source IV format inconsistency causing calculation errors
Expected Behavior 2.12: System should unify data formats (IV unified to percentage format)

Test Goal: Surface counterexamples showing IV format inconsistency causes calculation errors

Expected Outcome: Test FAILS (calculation results differ by 100x)
"""

import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from data_layer.data_fetcher import IVNormalizer
from calculation_layer.module15_black_scholes import BlackScholesCalculator


class TestBugExplorationIVFormatConsistency:
    """
    Bug Exploration Test for IV Format Consistency
    
    EXPECTED TO FAIL on unfixed code - failure confirms the bug exists.
    """
    
    def setup_method(self):
        """Setup test fixtures"""
        self.bs_calculator = BlackScholesCalculator()
        
        # Standard option parameters for testing
        self.stock_price = 100.0
        self.strike_price = 105.0
        self.time_to_expiration = 0.5  # 6 months
        self.risk_free_rate = 0.05  # 5%
        self.option_type = 'call'
    
    def test_bug_condition_iv_format_inconsistency(self):
        """
        Property 1: Bug Condition - Multi-Source IV Format Inconsistency
        
        Validates: Requirements 1.12, 2.12
        
        CRITICAL: This test MUST FAIL on unfixed code - failure confirms the bug exists.
        
        GOAL: Surface counterexamples showing IV format inconsistency causes calculation errors.
        """
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
        
        # Step 2: Calculate Black-Scholes with IBKR IV (decimal format)
        bs_result_ibkr = self.bs_calculator.calculate_option_price(
            stock_price=self.stock_price,
            strike_price=self.strike_price,
            time_to_expiration=self.time_to_expiration,
            risk_free_rate=self.risk_free_rate,
            volatility=ibkr_iv,
            option_type=self.option_type
        )
        
        price_ibkr = bs_result_ibkr.option_price
        
        # Step 3: Calculate Black-Scholes with Yahoo IV (percentage format)
        # BUG: If system doesn't normalize, this will treat 25 as 2500% volatility!
        try:
            bs_result_yahoo = self.bs_calculator.calculate_option_price(
                stock_price=self.stock_price,
                strike_price=self.strike_price,
                time_to_expiration=self.time_to_expiration,
                risk_free_rate=self.risk_free_rate,
                volatility=yahoo_iv,  # Using raw Yahoo format (25.0) - THIS IS THE BUG!
                option_type=self.option_type
            )
            price_yahoo = bs_result_yahoo.option_price
        except ValueError as e:
            # BUG CONFIRMED: Black-Scholes rejects Yahoo IV=25 as invalid (2500% volatility)
            print(f"\nBlack-Scholes REJECTED Yahoo IV=25.0:")
            print(f"  Error: {str(e)}")
            print(f"  Reason: Yahoo IV=25.0 is treated as 2500% volatility (outside valid range [0%, 500%])")
            
            # This is the bug! The system should normalize Yahoo IV=25 to 0.25 before passing to Black-Scholes
            print(f"\nBUG CONFIRMED: Yahoo IV format inconsistency causes calculation failure")
            print(f"   Counterexample:")
            print(f"   - IBKR IV=0.25 (decimal) -> Price = ${price_ibkr:.4f}")
            print(f"   - Yahoo IV=25.0 (percentage) -> REJECTED (treated as 2500% volatility)")
            print(f"\n   Root cause: Yahoo IV=25 is not normalized to decimal format before Black-Scholes calculation")
            
            pytest.fail(
                f"BUG DETECTED: Yahoo IV=25.0 is rejected by Black-Scholes (treated as 2500% volatility). "
                f"IBKR IV=0.25 works fine (${price_ibkr:.4f}). "
                f"This confirms Bug 1.12: IV format inconsistency causes calculation errors."
            )
            return  # Exit early since we can't continue
        
        price_ibkr = bs_result_ibkr.option_price
        price_yahoo = bs_result_yahoo.option_price
        
        print(f"\nBlack-Scholes Results (WITHOUT normalization):")
        print(f"  IBKR IV=0.25:  Option Price = ${price_ibkr:.4f}")
        print(f"  Yahoo IV=25.0: Option Price = ${price_yahoo:.4f}")
        
        # Calculate the difference
        price_diff = abs(price_ibkr - price_yahoo)
        price_ratio = max(price_ibkr, price_yahoo) / min(price_ibkr, price_yahoo) if min(price_ibkr, price_yahoo) > 0 else float('inf')
        
        print(f"\nDifference Analysis:")
        print(f"  Absolute difference: ${price_diff:.4f}")
        print(f"  Ratio: {price_ratio:.2f}x")
        
        # Step 4: Calculate with NORMALIZED IVs (what the fix should do)
        ibkr_iv_normalized_decimal = ibkr_normalized['normalized_iv'] / 100.0
        yahoo_iv_normalized_decimal = yahoo_normalized['normalized_iv'] / 100.0
        
        bs_result_ibkr_fixed = self.bs_calculator.calculate_option_price(
            stock_price=self.stock_price,
            strike_price=self.strike_price,
            time_to_expiration=self.time_to_expiration,
            risk_free_rate=self.risk_free_rate,
            volatility=ibkr_iv_normalized_decimal,
            option_type=self.option_type
        )
        
        bs_result_yahoo_fixed = self.bs_calculator.calculate_option_price(
            stock_price=self.stock_price,
            strike_price=self.strike_price,
            time_to_expiration=self.time_to_expiration,
            risk_free_rate=self.risk_free_rate,
            volatility=yahoo_iv_normalized_decimal,
            option_type=self.option_type
        )
        
        price_ibkr_fixed = bs_result_ibkr_fixed.option_price
        price_yahoo_fixed = bs_result_yahoo_fixed.option_price
        
        print(f"\nBlack-Scholes Results (WITH normalization - expected after fix):")
        print(f"  IBKR IV=0.25 -> 25% -> 0.25:  Option Price = ${price_ibkr_fixed:.4f}")
        print(f"  Yahoo IV=25.0 -> 25% -> 0.25: Option Price = ${price_yahoo_fixed:.4f}")
        
        fixed_diff = abs(price_ibkr_fixed - price_yahoo_fixed)
        print(f"  Difference: ${fixed_diff:.4f}")
        
        # CRITICAL ASSERTION: This should FAIL on unfixed code
        print("\n" + "="*80)
        print("CRITICAL TEST: Checking for format inconsistency bug...")
        print("="*80)
        
        # On unfixed code, the prices should differ significantly (by ~100x or more)
        if price_ratio > 10.0:
            print(f"\nBUG CONFIRMED: Prices differ by {price_ratio:.2f}x")
            print(f"   This confirms Bug 1.12: IV format inconsistency causes calculation errors")
            print(f"\n   Counterexample:")
            print(f"   - IBKR IV=0.25 (decimal) -> Price = ${price_ibkr:.4f}")
            print(f"   - Yahoo IV=25.0 (percentage) -> Price = ${price_yahoo:.4f}")
            print(f"   - Difference: ${price_diff:.4f} ({price_ratio:.2f}x)")
            print(f"\n   Root cause: Yahoo IV=25 is treated as 2500% volatility instead of 25%")
            
            # This assertion SHOULD FAIL on unfixed code
            pytest.fail(
                f"BUG DETECTED: IV format inconsistency causes {price_ratio:.2f}x price difference. "
                f"IBKR IV=0.25 -> ${price_ibkr:.4f}, Yahoo IV=25.0 -> ${price_yahoo:.4f}. "
                f"This confirms Bug 1.12 exists."
            )
        else:
            print(f"\nBUG NOT DETECTED: Prices are consistent (ratio: {price_ratio:.2f}x)")
            print(f"   This suggests IVNormalizer is already being applied correctly")
            print(f"   OR the bug has already been fixed")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
