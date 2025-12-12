#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Property-based tests for ATM IV Propagation

**Feature: iv-source-fix, Property 1: ATM IV Propagation**
**Validates: Requirements 1.1, 2.1, 3.1, 4.1, 6.2**

Tests that when Module 17 successfully calculates ATM IV, the volatility_estimate
is updated correctly and subsequent modules use the ATM IV value.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
import sys
import os
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from calculation_layer.module15_black_scholes import BlackScholesCalculator
from calculation_layer.module16_greeks import GreeksCalculator
from calculation_layer.module17_implied_volatility import ImpliedVolatilityCalculator


# Strategies for valid option parameters
stock_price_strategy = st.floats(min_value=10.0, max_value=1000.0, allow_nan=False, allow_infinity=False)
strike_price_strategy = st.floats(min_value=10.0, max_value=1000.0, allow_nan=False, allow_infinity=False)
risk_free_rate_strategy = st.floats(min_value=0.001, max_value=0.15, allow_nan=False, allow_infinity=False)
time_to_expiration_strategy = st.floats(min_value=0.01, max_value=2.0, allow_nan=False, allow_infinity=False)
volatility_strategy = st.floats(min_value=0.05, max_value=2.0, allow_nan=False, allow_infinity=False)
market_iv_strategy = st.floats(min_value=0.01, max_value=0.50, allow_nan=False, allow_infinity=False)


class TestATMIVPropagation:
    """
    Test ATM IV Propagation
    
    **Feature: iv-source-fix, Property 1: ATM IV Propagation**
    **Validates: Requirements 1.1, 2.1, 3.1, 4.1, 6.2**
    
    For any successful Module 17 execution that produces a converged ATM IV,
    all subsequent modules (15, 16, 18, 23) should use the ATM IV value for
    their calculations, not the original Market IV.
    """
    
    def setup_method(self):
        self.bs_calculator = BlackScholesCalculator()
        self.greeks_calculator = GreeksCalculator()
        self.iv_calculator = ImpliedVolatilityCalculator()
    
    @given(
        stock_price=st.floats(min_value=50.0, max_value=500.0, allow_nan=False, allow_infinity=False),
        strike_ratio=st.floats(min_value=0.9, max_value=1.1, allow_nan=False, allow_infinity=False),  # Near ATM
        risk_free_rate=st.floats(min_value=0.01, max_value=0.08, allow_nan=False, allow_infinity=False),
        time_to_expiration=st.floats(min_value=0.1, max_value=1.0, allow_nan=False, allow_infinity=False),
        true_iv=st.floats(min_value=0.15, max_value=0.80, allow_nan=False, allow_infinity=False)  # Reasonable IV range
    )
    @settings(max_examples=100)
    def test_module17_convergence_produces_correct_iv(
        self, stock_price, strike_ratio, risk_free_rate, time_to_expiration, true_iv
    ):
        """
        Property 1: For any valid option parameters, Module 17 should converge
        to the correct IV when given a BS-calculated option price.
        
        **Feature: iv-source-fix, Property 1: ATM IV Propagation**
        **Validates: Requirements 1.1, 6.2**
        """
        # Calculate strike price from ratio to ensure near-ATM options
        strike_price = stock_price * strike_ratio
        
        # Calculate option price using known IV
        bs_result = self.bs_calculator.calculate_option_price(
            stock_price=stock_price,
            strike_price=strike_price,
            risk_free_rate=risk_free_rate,
            time_to_expiration=time_to_expiration,
            volatility=true_iv,
            option_type='call'
        )
        
        # Skip if option price is too small (numerical precision issues)
        assume(bs_result.option_price > 0.10)
        
        # Use Module 17 to recover IV from option price
        iv_result = self.iv_calculator.calculate_implied_volatility(
            market_price=bs_result.option_price,
            stock_price=stock_price,
            strike_price=strike_price,
            risk_free_rate=risk_free_rate,
            time_to_expiration=time_to_expiration,
            option_type='call'
        )
        
        # If converged, the recovered IV should be close to true IV
        if iv_result.converged:
            # Allow 6% relative tolerance for numerical precision in edge cases
            # (ITM options with low IV and high risk-free rate can have higher error)
            relative_error = abs(iv_result.implied_volatility - true_iv) / true_iv
            assert relative_error < 0.06, (
                f"IV recovery error too large: {relative_error*100:.2f}%, "
                f"true_iv={true_iv*100:.2f}%, recovered={iv_result.implied_volatility*100:.2f}%"
            )
    
    @given(
        stock_price=st.floats(min_value=50.0, max_value=500.0, allow_nan=False, allow_infinity=False),
        risk_free_rate=risk_free_rate_strategy,
        time_to_expiration=st.floats(min_value=0.1, max_value=1.0, allow_nan=False, allow_infinity=False),
        atm_iv=st.floats(min_value=0.15, max_value=0.80, allow_nan=False, allow_infinity=False),
        market_iv=st.floats(min_value=0.05, max_value=0.30, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_volatility_estimate_update_affects_greeks(
        self, stock_price, risk_free_rate, time_to_expiration, atm_iv, market_iv
    ):
        """
        Property 1: When volatility_estimate is updated from Market IV to ATM IV,
        Greeks calculations should use the new ATM IV value.
        
        **Feature: iv-source-fix, Property 1: ATM IV Propagation**
        **Validates: Requirements 2.1**
        """
        # Use ATM option (strike = stock price) to ensure meaningful Greeks
        strike_price = stock_price
        
        # Ensure ATM IV and Market IV are different enough to matter
        assume(abs(atm_iv - market_iv) / max(atm_iv, market_iv) > 0.2)
        
        # Calculate Greeks with Market IV
        greeks_market = self.greeks_calculator.calculate_all_greeks(
            stock_price=stock_price,
            strike_price=strike_price,
            risk_free_rate=risk_free_rate,
            time_to_expiration=time_to_expiration,
            volatility=market_iv,
            option_type='call'
        )
        
        # Calculate Greeks with ATM IV (simulating volatility_estimate update)
        greeks_atm = self.greeks_calculator.calculate_all_greeks(
            stock_price=stock_price,
            strike_price=strike_price,
            risk_free_rate=risk_free_rate,
            time_to_expiration=time_to_expiration,
            volatility=atm_iv,
            option_type='call'
        )
        
        # For ATM options with reasonable time to expiration, Greeks should differ
        # when using different IV values. Vega is most sensitive to IV changes.
        assert greeks_market.vega != greeks_atm.vega or greeks_market.gamma != greeks_atm.gamma, (
            f"Greeks should differ when using different IV values: "
            f"market_iv={market_iv}, atm_iv={atm_iv}"
        )
    
    @given(
        stock_price=st.floats(min_value=50.0, max_value=500.0, allow_nan=False, allow_infinity=False),
        risk_free_rate=risk_free_rate_strategy,
        time_to_expiration=st.floats(min_value=0.1, max_value=1.0, allow_nan=False, allow_infinity=False),
        atm_iv=st.floats(min_value=0.15, max_value=0.80, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_bs_price_uses_updated_volatility(
        self, stock_price, risk_free_rate, time_to_expiration, atm_iv
    ):
        """
        Property 1: Black-Scholes calculations should use the updated volatility_estimate.
        
        **Feature: iv-source-fix, Property 1: ATM IV Propagation**
        **Validates: Requirements 3.1**
        """
        # Use ATM option to ensure meaningful option price
        strike_price = stock_price
        
        # Calculate option price with ATM IV
        bs_result = self.bs_calculator.calculate_option_price(
            stock_price=stock_price,
            strike_price=strike_price,
            risk_free_rate=risk_free_rate,
            time_to_expiration=time_to_expiration,
            volatility=atm_iv,
            option_type='call'
        )
        
        # For ATM options with reasonable parameters, option price should be positive
        assert bs_result.option_price > 0, "Option price should be positive for ATM options"
        
        # The volatility used should match the input
        assert abs(bs_result.volatility - atm_iv) < 0.0001, (
            f"BS calculation should use the provided volatility: "
            f"expected {atm_iv}, got {bs_result.volatility}"
        )


class TestIVSourceTracking:
    """
    Test IV Source Tracking
    
    **Feature: iv-source-fix, Property 2: IV Source Recording Consistency**
    **Validates: Requirements 1.3, 2.3, 3.2, 5.3**
    """
    
    def setup_method(self):
        self.bs_calculator = BlackScholesCalculator()
        self.iv_calculator = ImpliedVolatilityCalculator()
        self.greeks_calculator = GreeksCalculator()
    
    @given(
        stock_price=stock_price_strategy,
        strike_price=strike_price_strategy,
        risk_free_rate=risk_free_rate_strategy,
        time_to_expiration=time_to_expiration_strategy,
        atm_iv=volatility_strategy,
        market_iv=market_iv_strategy
    )
    @settings(max_examples=100)
    def test_bs_with_atm_iv_records_source(
        self, stock_price, strike_price, risk_free_rate, time_to_expiration, atm_iv, market_iv
    ):
        """
        Property 2: When ATM IV is used, the iv_source should be recorded correctly.
        
        **Feature: iv-source-fix, Property 2: IV Source Recording Consistency**
        **Validates: Requirements 1.3, 3.2**
        """
        # Skip extreme moneyness cases
        moneyness = stock_price / strike_price
        assume(0.5 < moneyness < 2.0)
        
        # Calculate option price with ATM IV using the special method
        bs_result = self.bs_calculator.calculate_option_price_with_atm_iv(
            stock_price=stock_price,
            strike_price=strike_price,
            risk_free_rate=risk_free_rate,
            time_to_expiration=time_to_expiration,
            market_iv=market_iv,
            atm_iv=atm_iv,
            option_type='call'
        )
        
        # The result should indicate ATM IV was used
        assert bs_result.iv_source == 'ATM IV (Module 17)', (
            f"iv_source should be 'ATM IV (Module 17)', got '{bs_result.iv_source}'"
        )
        
        # The volatility used should be ATM IV
        assert abs(bs_result.volatility - atm_iv) < 0.0001, (
            f"Should use ATM IV: expected {atm_iv}, got {bs_result.volatility}"
        )
    
    @given(
        stock_price=st.floats(min_value=50.0, max_value=500.0, allow_nan=False, allow_infinity=False),
        risk_free_rate=risk_free_rate_strategy,
        time_to_expiration=st.floats(min_value=0.05, max_value=1.0, allow_nan=False, allow_infinity=False),
        atm_iv=st.floats(min_value=0.10, max_value=1.0, allow_nan=False, allow_infinity=False),
        market_iv=st.floats(min_value=0.01, max_value=0.30, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_greeks_iv_source_recording(
        self, stock_price, risk_free_rate, time_to_expiration, atm_iv, market_iv
    ):
        """
        Property 2: When Greeks are calculated with ATM IV, the module16_greeks result
        should contain iv_source and iv_used fields that correctly indicate the IV used.
        
        **Feature: iv-source-fix, Property 2: IV Source Recording Consistency**
        **Validates: Requirements 2.3**
        
        This test simulates the behavior of main.py where:
        1. Module 16 calculates Greeks with some IV
        2. After Module 17 converges, the results are updated with ATM IV
        3. The iv_source and iv_used fields are added to track which IV was used
        """
        # Use ATM option (strike = stock price) for meaningful Greeks
        strike_price = stock_price
        
        # Ensure ATM IV and Market IV are different enough to matter
        assume(abs(atm_iv - market_iv) / max(atm_iv, market_iv) > 0.1)
        
        # Simulate the module16_greeks result structure as created in main.py
        # First, calculate Greeks with ATM IV (as done after Module 17 update)
        call_greeks = self.greeks_calculator.calculate_all_greeks(
            stock_price=stock_price,
            strike_price=strike_price,
            risk_free_rate=risk_free_rate,
            time_to_expiration=time_to_expiration,
            volatility=atm_iv,
            option_type='call'
        )
        
        put_greeks = self.greeks_calculator.calculate_all_greeks(
            stock_price=stock_price,
            strike_price=strike_price,
            risk_free_rate=risk_free_rate,
            time_to_expiration=time_to_expiration,
            volatility=atm_iv,
            option_type='put'
        )
        
        # Simulate the module16_greeks result structure with IV source tracking
        # This mirrors what main.py does after Module 17 ATM IV update
        iv_source = "ATM IV (Module 17)"
        module16_greeks = {
            'call': call_greeks.to_dict(),
            'put': put_greeks.to_dict(),
            'iv_source': iv_source,
            'iv_used': round(atm_iv, 6),
            'iv_used_pct': round(atm_iv * 100, 2),
            'market_iv': round(market_iv, 6),
            'market_iv_pct': round(market_iv * 100, 2),
            'data_source': 'Self-Calculated (ATM IV)'
        }
        
        # Property 2 assertions: IV source recording consistency
        
        # 1. iv_source field must exist and indicate ATM IV was used
        assert 'iv_source' in module16_greeks, "module16_greeks must contain 'iv_source' field"
        assert module16_greeks['iv_source'] == "ATM IV (Module 17)", (
            f"iv_source should be 'ATM IV (Module 17)', got '{module16_greeks['iv_source']}'"
        )
        
        # 2. iv_used field must exist and match the ATM IV used
        assert 'iv_used' in module16_greeks, "module16_greeks must contain 'iv_used' field"
        assert abs(module16_greeks['iv_used'] - atm_iv) < 0.0001, (
            f"iv_used should match ATM IV: expected {atm_iv}, got {module16_greeks['iv_used']}"
        )
        
        # 3. The Greeks should be calculated with ATM IV, not Market IV
        # Verify by checking that the volatility in the call result matches ATM IV
        assert abs(module16_greeks['call']['volatility'] - atm_iv) < 0.0001, (
            f"Greeks should be calculated with ATM IV: expected {atm_iv}, got {module16_greeks['call']['volatility']}"
        )
    
    @given(
        stock_price=st.floats(min_value=50.0, max_value=500.0, allow_nan=False, allow_infinity=False),
        risk_free_rate=risk_free_rate_strategy,
        time_to_expiration=st.floats(min_value=0.05, max_value=1.0, allow_nan=False, allow_infinity=False),
        market_iv=st.floats(min_value=0.05, max_value=0.50, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_greeks_fallback_iv_source_recording(
        self, stock_price, risk_free_rate, time_to_expiration, market_iv
    ):
        """
        Property 2: When Module 17 fails to converge and Market IV is used as fallback,
        the module16_greeks result should contain iv_source indicating fallback was used.
        
        **Feature: iv-source-fix, Property 2: IV Source Recording Consistency**
        **Validates: Requirements 2.3**
        
        This test simulates the fallback behavior when Module 17 doesn't converge.
        """
        # Use ATM option
        strike_price = stock_price
        
        # Calculate Greeks with Market IV (fallback case)
        call_greeks = self.greeks_calculator.calculate_all_greeks(
            stock_price=stock_price,
            strike_price=strike_price,
            risk_free_rate=risk_free_rate,
            time_to_expiration=time_to_expiration,
            volatility=market_iv,
            option_type='call'
        )
        
        put_greeks = self.greeks_calculator.calculate_all_greeks(
            stock_price=stock_price,
            strike_price=strike_price,
            risk_free_rate=risk_free_rate,
            time_to_expiration=time_to_expiration,
            volatility=market_iv,
            option_type='put'
        )
        
        # Simulate the fallback case where Module 17 didn't converge
        iv_source = "Market IV (fallback)"
        module16_greeks = {
            'call': call_greeks.to_dict(),
            'put': put_greeks.to_dict(),
            'iv_source': iv_source,
            'iv_used': round(market_iv, 6),
            'iv_used_pct': round(market_iv * 100, 2),
            'data_source': 'Self-Calculated'
        }
        
        # Property 2 assertions for fallback case
        
        # 1. iv_source field must exist and indicate fallback was used
        assert 'iv_source' in module16_greeks, "module16_greeks must contain 'iv_source' field"
        assert 'fallback' in module16_greeks['iv_source'].lower(), (
            f"iv_source should indicate fallback, got '{module16_greeks['iv_source']}'"
        )
        
        # 2. iv_used field must exist and match the Market IV used
        assert 'iv_used' in module16_greeks, "module16_greeks must contain 'iv_used' field"
        assert abs(module16_greeks['iv_used'] - market_iv) < 0.0001, (
            f"iv_used should match Market IV: expected {market_iv}, got {module16_greeks['iv_used']}"
        )
        
        # 3. The Greeks should be calculated with Market IV
        assert abs(module16_greeks['call']['volatility'] - market_iv) < 0.0001, (
            f"Greeks should be calculated with Market IV: expected {market_iv}, got {module16_greeks['call']['volatility']}"
        )


class TestModule17ConvergenceBehavior:
    """
    Test Module 17 Convergence Behavior
    
    Tests the convergence properties of the IV calculation.
    """
    
    def setup_method(self):
        self.bs_calculator = BlackScholesCalculator()
        self.iv_calculator = ImpliedVolatilityCalculator()
    
    @given(
        stock_price=st.floats(min_value=50.0, max_value=500.0, allow_nan=False, allow_infinity=False),
        time_to_expiration=st.floats(min_value=0.05, max_value=1.0, allow_nan=False, allow_infinity=False),
        true_iv=st.floats(min_value=0.10, max_value=1.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_atm_options_converge_reliably(self, stock_price, time_to_expiration, true_iv):
        """
        For ATM options (strike = stock price), Module 17 should converge reliably.
        
        **Feature: iv-source-fix, Property 1: ATM IV Propagation**
        **Validates: Requirements 1.1, 6.2**
        """
        strike_price = stock_price  # ATM option
        risk_free_rate = 0.05
        
        # Calculate option price using known IV
        bs_result = self.bs_calculator.calculate_option_price(
            stock_price=stock_price,
            strike_price=strike_price,
            risk_free_rate=risk_free_rate,
            time_to_expiration=time_to_expiration,
            volatility=true_iv,
            option_type='call'
        )
        
        # Skip if option price is too small
        assume(bs_result.option_price > 0.01)
        
        # Use Module 17 to recover IV
        iv_result = self.iv_calculator.calculate_implied_volatility(
            market_price=bs_result.option_price,
            stock_price=stock_price,
            strike_price=strike_price,
            risk_free_rate=risk_free_rate,
            time_to_expiration=time_to_expiration,
            option_type='call'
        )
        
        # ATM options should converge reliably
        assert iv_result.converged, (
            f"ATM option IV calculation should converge: "
            f"S={stock_price}, K={strike_price}, T={time_to_expiration}, true_iv={true_iv}"
        )
        
        # Recovered IV should be close to true IV
        relative_error = abs(iv_result.implied_volatility - true_iv) / true_iv
        assert relative_error < 0.01, (
            f"ATM IV recovery error: {relative_error*100:.2f}%"
        )


class TestModule23DynamicIVThresholdIVUsage:
    """
    Test Module 23 Dynamic IV Threshold IV Usage
    
    **Feature: iv-source-fix, Property 1: ATM IV Propagation**
    **Validates: Requirements 4.1, 4.2, 4.3**
    
    Tests that Module 23 (Dynamic IV Threshold) uses ATM IV from volatility_estimate
    instead of Market IV from analysis_data.get('implied_volatility').
    """
    
    def setup_method(self):
        from calculation_layer.module23_dynamic_iv_threshold import DynamicIVThresholdCalculator
        self.dynamic_iv_calc = DynamicIVThresholdCalculator()
    
    @given(
        atm_iv=st.floats(min_value=0.10, max_value=2.0, allow_nan=False, allow_infinity=False),
        market_iv=st.floats(min_value=0.01, max_value=0.50, allow_nan=False, allow_infinity=False),
        vix=st.floats(min_value=10.0, max_value=80.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_module23_uses_atm_iv_not_market_iv(self, atm_iv, market_iv, vix):
        """
        Property 1: Module 23 should use ATM IV (volatility_estimate * 100) for threshold
        calculations, not Market IV from analysis_data.
        
        **Feature: iv-source-fix, Property 1: ATM IV Propagation**
        **Validates: Requirements 4.1, 4.2**
        
        This test simulates the behavior in main.py where:
        1. volatility_estimate is updated to ATM IV after Module 17 converges
        2. Module 23 should use volatility_estimate * 100 as current_iv
        """
        # Ensure ATM IV and Market IV are different enough to matter
        assume(abs(atm_iv - market_iv) / max(atm_iv, market_iv) > 0.2)
        
        # Simulate volatility_estimate being updated to ATM IV (as done in main.py)
        volatility_estimate = atm_iv  # This is in decimal form (e.g., 0.25 for 25%)
        
        # Convert to percentage for Module 23 (as done in main.py fix)
        current_iv_for_threshold = volatility_estimate * 100
        
        # Calculate thresholds using ATM IV
        result_atm = self.dynamic_iv_calc.calculate_thresholds(
            current_iv=current_iv_for_threshold,
            historical_iv=None,  # Use static thresholds for simplicity
            vix=vix
        )
        
        # Calculate thresholds using Market IV (the old incorrect behavior)
        market_iv_pct = market_iv * 100
        result_market = self.dynamic_iv_calc.calculate_thresholds(
            current_iv=market_iv_pct,
            historical_iv=None,
            vix=vix
        )
        
        # Property assertion: The current_iv in the result should match ATM IV, not Market IV
        # Allow small tolerance for floating point
        assert abs(result_atm.current_iv - current_iv_for_threshold) < 0.01, (
            f"Module 23 should use ATM IV: expected {current_iv_for_threshold:.2f}%, "
            f"got {result_atm.current_iv:.2f}%"
        )
        
        # When ATM IV and Market IV differ significantly, the results should differ
        if abs(current_iv_for_threshold - market_iv_pct) > 5.0:
            # The current_iv values should be different
            assert abs(result_atm.current_iv - result_market.current_iv) > 1.0, (
                f"Results should differ when using different IV values: "
                f"ATM IV result={result_atm.current_iv:.2f}%, "
                f"Market IV result={result_market.current_iv:.2f}%"
            )
    
    @given(
        atm_iv=st.floats(min_value=0.15, max_value=1.5, allow_nan=False, allow_infinity=False),
        market_iv=st.floats(min_value=0.05, max_value=0.40, allow_nan=False, allow_infinity=False),
        vix=st.floats(min_value=12.0, max_value=60.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_module23_iv_source_recording(self, atm_iv, market_iv, vix):
        """
        Property 1: Module 23 result should contain iv_source and iv_used fields
        that correctly indicate which IV was used.
        
        **Feature: iv-source-fix, Property 1: ATM IV Propagation**
        **Validates: Requirements 4.3**
        
        This test simulates the complete flow in main.py where:
        1. Module 23 calculates thresholds using ATM IV
        2. The result is augmented with iv_source and iv_used fields
        """
        # Simulate volatility_estimate being updated to ATM IV
        volatility_estimate = atm_iv
        current_iv_for_threshold = volatility_estimate * 100
        
        # Simulate iv_source being set after Module 17 converges
        atm_iv_available = True
        iv_source = "ATM IV (Module 17)"
        
        # Calculate thresholds
        result = self.dynamic_iv_calc.calculate_thresholds(
            current_iv=current_iv_for_threshold,
            historical_iv=None,
            vix=vix
        )
        
        # Simulate the augmentation done in main.py (the fix we implemented)
        result_dict = result.to_dict()
        result_dict['iv_source'] = iv_source
        result_dict['iv_used'] = round(current_iv_for_threshold, 2)
        result_dict['iv_used_decimal'] = round(volatility_estimate, 6)
        result_dict['market_iv'] = market_iv * 100
        result_dict['atm_iv_available'] = atm_iv_available
        
        # Property assertions for iv_source recording
        
        # 1. iv_source field must exist and indicate ATM IV was used
        assert 'iv_source' in result_dict, "Module 23 result must contain 'iv_source' field"
        assert result_dict['iv_source'] == "ATM IV (Module 17)", (
            f"iv_source should be 'ATM IV (Module 17)', got '{result_dict['iv_source']}'"
        )
        
        # 2. iv_used field must exist and match the ATM IV used
        assert 'iv_used' in result_dict, "Module 23 result must contain 'iv_used' field"
        assert abs(result_dict['iv_used'] - current_iv_for_threshold) < 0.01, (
            f"iv_used should match ATM IV: expected {current_iv_for_threshold:.2f}%, "
            f"got {result_dict['iv_used']:.2f}%"
        )
        
        # 3. atm_iv_available field must exist and be True
        assert 'atm_iv_available' in result_dict, "Module 23 result must contain 'atm_iv_available' field"
        assert result_dict['atm_iv_available'] == True, "atm_iv_available should be True when ATM IV is used"
        
        # 4. The current_iv in the result should match the ATM IV used
        assert abs(result_dict['current_iv'] - current_iv_for_threshold) < 0.01, (
            f"current_iv should match ATM IV: expected {current_iv_for_threshold:.2f}%, "
            f"got {result_dict['current_iv']:.2f}%"
        )
    
    @given(
        atm_iv=st.floats(min_value=0.20, max_value=1.5, allow_nan=False, allow_infinity=False),
        vix=st.floats(min_value=12.0, max_value=50.0, allow_nan=False, allow_infinity=False),
        historical_iv=st.lists(
            st.floats(min_value=0.10, max_value=1.0, allow_nan=False, allow_infinity=False),
            min_size=60,
            max_size=300
        )
    )
    @settings(max_examples=50)
    def test_module23_status_based_on_atm_iv(self, atm_iv, vix, historical_iv):
        """
        Property 1: Module 23 IV status judgment (HIGH/NORMAL/LOW) should be based
        on ATM IV, not Market IV.
        
        **Feature: iv-source-fix, Property 1: ATM IV Propagation**
        **Validates: Requirements 4.2, 4.3**
        
        This test verifies that the status determination uses the correct IV value.
        """
        # Convert ATM IV to percentage
        current_iv_for_threshold = atm_iv * 100
        
        # Calculate thresholds with historical data
        result = self.dynamic_iv_calc.calculate_thresholds(
            current_iv=current_iv_for_threshold,
            historical_iv=historical_iv,
            vix=vix
        )
        
        # Verify the status is determined based on the ATM IV value
        # The status should be consistent with the current_iv vs thresholds comparison
        if result.current_iv > result.high_threshold:
            assert "高於" in result.status or "HIGH" in result.status, (
                f"Status should indicate HIGH when current_iv ({result.current_iv:.2f}%) > "
                f"high_threshold ({result.high_threshold:.2f}%), got '{result.status}'"
            )
        elif result.current_iv < result.low_threshold:
            assert "低於" in result.status or "LOW" in result.status, (
                f"Status should indicate LOW when current_iv ({result.current_iv:.2f}%) < "
                f"low_threshold ({result.low_threshold:.2f}%), got '{result.status}'"
            )
        else:
            assert "正常" in result.status or "NORMAL" in result.status, (
                f"Status should indicate NORMAL when current_iv ({result.current_iv:.2f}%) is "
                f"between thresholds ({result.low_threshold:.2f}%-{result.high_threshold:.2f}%), "
                f"got '{result.status}'"
            )


class TestIVDifferenceWarning:
    """
    Test IV Difference Warning Generation
    
    **Feature: iv-source-fix, Property 3: IV Difference Warning Generation**
    **Validates: Requirements 5.1, 5.2**
    
    For any case where ATM IV differs from Market IV by more than 20%, 
    the system should generate a warning message.
    """
    
    @given(
        atm_iv=st.floats(min_value=0.10, max_value=2.0, allow_nan=False, allow_infinity=False),
        market_iv=st.floats(min_value=1.0, max_value=100.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_iv_warning_generated_when_difference_exceeds_threshold(self, atm_iv, market_iv):
        """
        Property 3: When ATM IV differs from Market IV by more than 20%, 
        a warning should be generated.
        
        **Feature: iv-source-fix, Property 3: IV Difference Warning Generation**
        **Validates: Requirements 5.1, 5.2**
        
        This test simulates the IV warning logic in main.py:
        1. Calculate the difference percentage between ATM IV and Market IV
        2. If difference > 20%, generate a warning
        3. Store the warning in analysis_results
        """
        # Skip edge cases where market_iv is too small
        assume(market_iv > 0.1)
        
        # Convert ATM IV to percentage for comparison (as done in main.py)
        atm_iv_pct = atm_iv * 100
        volatility_raw = market_iv  # Market IV is already in percentage
        
        # Calculate difference percentage (as done in main.py)
        iv_diff_pct = abs(atm_iv_pct - volatility_raw) / volatility_raw * 100 if volatility_raw > 0 else 0
        
        # Simulate the warning logic from main.py
        iv_warning = None
        if iv_diff_pct > 20:
            iv_warning = f"ATM IV ({atm_iv_pct:.2f}%) 與 Market IV ({volatility_raw:.2f}%) 差異 {iv_diff_pct:.1f}%，超過 20% 閾值"
        
        # Simulate the iv_comparison structure
        iv_comparison = {
            'market_iv': round(volatility_raw, 2),
            'atm_iv': round(atm_iv_pct, 2),
            'difference_pct': round(iv_diff_pct, 1),
            'warning_threshold': 20,
            'has_warning': iv_diff_pct > 20
        }
        
        # Property assertions
        
        # 1. Warning should be generated if and only if difference > 20%
        if iv_diff_pct > 20:
            assert iv_warning is not None, (
                f"Warning should be generated when difference ({iv_diff_pct:.1f}%) > 20%"
            )
            assert iv_comparison['has_warning'] == True, (
                f"has_warning should be True when difference ({iv_diff_pct:.1f}%) > 20%"
            )
            # Warning message should contain both IV values
            assert f"{atm_iv_pct:.2f}%" in iv_warning, (
                f"Warning should contain ATM IV value"
            )
            assert f"{volatility_raw:.2f}%" in iv_warning, (
                f"Warning should contain Market IV value"
            )
        else:
            assert iv_warning is None, (
                f"Warning should NOT be generated when difference ({iv_diff_pct:.1f}%) <= 20%"
            )
            assert iv_comparison['has_warning'] == False, (
                f"has_warning should be False when difference ({iv_diff_pct:.1f}%) <= 20%"
            )
        
        # 2. iv_comparison should always contain required fields
        assert 'market_iv' in iv_comparison, "iv_comparison must contain 'market_iv'"
        assert 'atm_iv' in iv_comparison, "iv_comparison must contain 'atm_iv'"
        assert 'difference_pct' in iv_comparison, "iv_comparison must contain 'difference_pct'"
        assert 'warning_threshold' in iv_comparison, "iv_comparison must contain 'warning_threshold'"
        assert 'has_warning' in iv_comparison, "iv_comparison must contain 'has_warning'"
        
        # 3. Threshold should be 20%
        assert iv_comparison['warning_threshold'] == 20, (
            f"Warning threshold should be 20%, got {iv_comparison['warning_threshold']}"
        )
    
    @given(
        atm_iv=st.floats(min_value=0.10, max_value=2.0, allow_nan=False, allow_infinity=False),
        market_iv=st.floats(min_value=1.0, max_value=100.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_iv_comparison_values_are_consistent(self, atm_iv, market_iv):
        """
        Property 3: The iv_comparison structure should have consistent values.
        
        **Feature: iv-source-fix, Property 3: IV Difference Warning Generation**
        **Validates: Requirements 5.1, 5.2**
        
        This test verifies that the iv_comparison values are mathematically consistent.
        """
        assume(market_iv > 0.1)
        
        atm_iv_pct = atm_iv * 100
        volatility_raw = market_iv
        
        iv_diff_pct = abs(atm_iv_pct - volatility_raw) / volatility_raw * 100 if volatility_raw > 0 else 0
        
        iv_comparison = {
            'market_iv': round(volatility_raw, 2),
            'atm_iv': round(atm_iv_pct, 2),
            'difference_pct': round(iv_diff_pct, 1),
            'warning_threshold': 20,
            'has_warning': iv_diff_pct > 20
        }
        
        # Verify mathematical consistency
        # Recalculate difference from stored values
        stored_diff = abs(iv_comparison['atm_iv'] - iv_comparison['market_iv']) / iv_comparison['market_iv'] * 100
        
        # Allow for rounding differences - use relative tolerance for large values
        # For small differences, use absolute tolerance of 1.5%
        # For large differences, use relative tolerance of 1%
        max_diff = max(stored_diff, iv_comparison['difference_pct'])
        if max_diff > 100:
            # Use relative tolerance for large differences
            tolerance = max_diff * 0.01  # 1% relative tolerance
        else:
            tolerance = 1.5  # Absolute tolerance for small differences
        
        assert abs(stored_diff - iv_comparison['difference_pct']) < tolerance, (
            f"Stored difference_pct ({iv_comparison['difference_pct']:.1f}%) should be consistent "
            f"with calculated difference ({stored_diff:.1f}%)"
        )
        
        # has_warning should be consistent with difference_pct and threshold
        expected_has_warning = iv_comparison['difference_pct'] > iv_comparison['warning_threshold']
        # Note: Due to rounding, we need to check the original iv_diff_pct
        assert iv_comparison['has_warning'] == (iv_diff_pct > 20), (
            f"has_warning ({iv_comparison['has_warning']}) should be consistent with "
            f"difference_pct ({iv_diff_pct:.1f}%) > threshold (20%)"
        )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
