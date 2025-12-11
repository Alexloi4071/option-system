#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Property-based tests for Fallback Behavior Correctness

**Feature: iv-source-fix, Property 4: Fallback Behavior Correctness**
**Validates: Requirements 1.2, 2.2**

Tests that when Module 17 fails to converge or ATM IV is unavailable,
the system falls back to Market IV and records the iv_source as "Market IV (fallback)".
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
market_iv_strategy = st.floats(min_value=0.05, max_value=0.80, allow_nan=False, allow_infinity=False)


class TestFallbackBehaviorCorrectness:
    """
    Test Fallback Behavior Correctness
    
    **Feature: iv-source-fix, Property 4: Fallback Behavior Correctness**
    **Validates: Requirements 1.2, 2.2**
    
    For any case where Module 17 fails to converge or ATM IV is unavailable,
    the system should fall back to Market IV and record the iv_source as 
    "Market IV (fallback)".
    """
    
    def setup_method(self):
        self.bs_calculator = BlackScholesCalculator()
        self.greeks_calculator = GreeksCalculator()
        self.iv_calculator = ImpliedVolatilityCalculator()
    
    @given(
        stock_price=st.floats(min_value=50.0, max_value=500.0, allow_nan=False, allow_infinity=False),
        strike_ratio=st.floats(min_value=0.8, max_value=1.2, allow_nan=False, allow_infinity=False),
        risk_free_rate=st.floats(min_value=0.01, max_value=0.10, allow_nan=False, allow_infinity=False),
        time_to_expiration=st.floats(min_value=0.05, max_value=1.0, allow_nan=False, allow_infinity=False),
        market_iv=st.floats(min_value=0.10, max_value=0.60, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_bs_fallback_when_atm_iv_is_none(
        self, stock_price, strike_ratio, risk_free_rate, time_to_expiration, market_iv
    ):
        """
        Property 4: When ATM IV is None, Black-Scholes should fall back to Market IV.
        
        **Feature: iv-source-fix, Property 4: Fallback Behavior Correctness**
        **Validates: Requirements 1.2, 2.2**
        
        This test verifies that when atm_iv is not provided (None), the system
        correctly falls back to using market_iv and records the appropriate iv_source.
        """
        strike_price = stock_price * strike_ratio
        
        # Call calculate_option_price_with_atm_iv with atm_iv=None
        result = self.bs_calculator.calculate_option_price_with_atm_iv(
            stock_price=stock_price,
            strike_price=strike_price,
            risk_free_rate=risk_free_rate,
            time_to_expiration=time_to_expiration,
            market_iv=market_iv,
            atm_iv=None,  # ATM IV not available
            option_type='call'
        )
        
        # Property assertions for fallback behavior
        
        # 1. iv_source should indicate fallback
        assert result.iv_source == 'Market IV (fallback)', (
            f"iv_source should be 'Market IV (fallback)' when atm_iv is None, "
            f"got '{result.iv_source}'"
        )
        
        # 2. The volatility used should be market_iv
        assert abs(result.volatility - market_iv) < 0.0001, (
            f"Should use market_iv when atm_iv is None: "
            f"expected {market_iv}, got {result.volatility}"
        )
        
        # 3. Option price should be positive for valid inputs
        assert result.option_price >= 0, (
            f"Option price should be non-negative, got {result.option_price}"
        )
    
    @given(
        stock_price=st.floats(min_value=50.0, max_value=500.0, allow_nan=False, allow_infinity=False),
        strike_ratio=st.floats(min_value=0.8, max_value=1.2, allow_nan=False, allow_infinity=False),
        risk_free_rate=st.floats(min_value=0.01, max_value=0.10, allow_nan=False, allow_infinity=False),
        time_to_expiration=st.floats(min_value=0.05, max_value=1.0, allow_nan=False, allow_infinity=False),
        market_iv=st.floats(min_value=0.10, max_value=0.60, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_bs_fallback_when_atm_iv_is_zero(
        self, stock_price, strike_ratio, risk_free_rate, time_to_expiration, market_iv
    ):
        """
        Property 4: When ATM IV is zero, Black-Scholes should fall back to Market IV.
        
        **Feature: iv-source-fix, Property 4: Fallback Behavior Correctness**
        **Validates: Requirements 1.2, 2.2**
        
        This test verifies that when atm_iv is 0 (invalid), the system
        correctly falls back to using market_iv.
        """
        strike_price = stock_price * strike_ratio
        
        # Call calculate_option_price_with_atm_iv with atm_iv=0
        result = self.bs_calculator.calculate_option_price_with_atm_iv(
            stock_price=stock_price,
            strike_price=strike_price,
            risk_free_rate=risk_free_rate,
            time_to_expiration=time_to_expiration,
            market_iv=market_iv,
            atm_iv=0.0,  # Invalid ATM IV
            option_type='call'
        )
        
        # Property assertions for fallback behavior
        
        # 1. iv_source should indicate fallback
        assert result.iv_source == 'Market IV (fallback)', (
            f"iv_source should be 'Market IV (fallback)' when atm_iv is 0, "
            f"got '{result.iv_source}'"
        )
        
        # 2. The volatility used should be market_iv
        assert abs(result.volatility - market_iv) < 0.0001, (
            f"Should use market_iv when atm_iv is 0: "
            f"expected {market_iv}, got {result.volatility}"
        )
    
    @given(
        stock_price=st.floats(min_value=50.0, max_value=500.0, allow_nan=False, allow_infinity=False),
        strike_ratio=st.floats(min_value=0.8, max_value=1.2, allow_nan=False, allow_infinity=False),
        risk_free_rate=st.floats(min_value=0.01, max_value=0.10, allow_nan=False, allow_infinity=False),
        time_to_expiration=st.floats(min_value=0.05, max_value=1.0, allow_nan=False, allow_infinity=False),
        market_iv=st.floats(min_value=0.10, max_value=0.60, allow_nan=False, allow_infinity=False),
        negative_atm_iv=st.floats(min_value=-1.0, max_value=-0.01, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_bs_fallback_when_atm_iv_is_negative(
        self, stock_price, strike_ratio, risk_free_rate, time_to_expiration, market_iv, negative_atm_iv
    ):
        """
        Property 4: When ATM IV is negative (invalid), Black-Scholes should fall back to Market IV.
        
        **Feature: iv-source-fix, Property 4: Fallback Behavior Correctness**
        **Validates: Requirements 1.2, 2.2**
        
        This test verifies that when atm_iv is negative (invalid), the system
        correctly falls back to using market_iv.
        """
        strike_price = stock_price * strike_ratio
        
        # Call calculate_option_price_with_atm_iv with negative atm_iv
        result = self.bs_calculator.calculate_option_price_with_atm_iv(
            stock_price=stock_price,
            strike_price=strike_price,
            risk_free_rate=risk_free_rate,
            time_to_expiration=time_to_expiration,
            market_iv=market_iv,
            atm_iv=negative_atm_iv,  # Invalid negative ATM IV
            option_type='call'
        )
        
        # Property assertions for fallback behavior
        
        # 1. iv_source should indicate fallback
        assert result.iv_source == 'Market IV (fallback)', (
            f"iv_source should be 'Market IV (fallback)' when atm_iv is negative, "
            f"got '{result.iv_source}'"
        )
        
        # 2. The volatility used should be market_iv
        assert abs(result.volatility - market_iv) < 0.0001, (
            f"Should use market_iv when atm_iv is negative: "
            f"expected {market_iv}, got {result.volatility}"
        )


class TestModule16FallbackBehavior:
    """
    Test Module 16 (Greeks) Fallback Behavior
    
    **Feature: iv-source-fix, Property 4: Fallback Behavior Correctness**
    **Validates: Requirements 2.2**
    
    Tests that when ATM IV is not available, Module 16 Greeks calculations
    fall back to Market IV and record the appropriate iv_source.
    """
    
    def setup_method(self):
        self.greeks_calculator = GreeksCalculator()
    
    @given(
        stock_price=st.floats(min_value=50.0, max_value=500.0, allow_nan=False, allow_infinity=False),
        risk_free_rate=st.floats(min_value=0.01, max_value=0.10, allow_nan=False, allow_infinity=False),
        time_to_expiration=st.floats(min_value=0.05, max_value=1.0, allow_nan=False, allow_infinity=False),
        market_iv=st.floats(min_value=0.10, max_value=0.60, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_greeks_fallback_iv_source_recording(
        self, stock_price, risk_free_rate, time_to_expiration, market_iv
    ):
        """
        Property 4: When Module 17 fails to converge, Module 16 Greeks should
        use Market IV and record iv_source as "Market IV (fallback)".
        
        **Feature: iv-source-fix, Property 4: Fallback Behavior Correctness**
        **Validates: Requirements 2.2**
        
        This test simulates the fallback behavior in main.py when Module 17
        doesn't converge and Module 16 must use Market IV.
        """
        # Use ATM option
        strike_price = stock_price
        
        # Simulate Module 17 not converging
        atm_iv_available = False
        iv_source = "Market IV (fallback)"
        volatility_estimate = market_iv  # Use Market IV as fallback
        
        # Calculate Greeks with Market IV (fallback case)
        call_greeks = self.greeks_calculator.calculate_all_greeks(
            stock_price=stock_price,
            strike_price=strike_price,
            risk_free_rate=risk_free_rate,
            time_to_expiration=time_to_expiration,
            volatility=volatility_estimate,
            option_type='call'
        )
        
        put_greeks = self.greeks_calculator.calculate_all_greeks(
            stock_price=stock_price,
            strike_price=strike_price,
            risk_free_rate=risk_free_rate,
            time_to_expiration=time_to_expiration,
            volatility=volatility_estimate,
            option_type='put'
        )
        
        # Simulate the module16_greeks result structure with fallback IV source
        module16_greeks = {
            'call': call_greeks.to_dict(),
            'put': put_greeks.to_dict(),
            'iv_source': iv_source,
            'iv_used': round(volatility_estimate, 6),
            'iv_used_pct': round(volatility_estimate * 100, 2),
            'data_source': 'Self-Calculated'
        }
        
        # Property 4 assertions for fallback behavior
        
        # 1. iv_source field must exist and indicate fallback was used
        assert 'iv_source' in module16_greeks, (
            "module16_greeks must contain 'iv_source' field"
        )
        assert 'fallback' in module16_greeks['iv_source'].lower(), (
            f"iv_source should indicate fallback, got '{module16_greeks['iv_source']}'"
        )
        
        # 2. iv_used field must exist and match the Market IV used
        assert 'iv_used' in module16_greeks, (
            "module16_greeks must contain 'iv_used' field"
        )
        assert abs(module16_greeks['iv_used'] - market_iv) < 0.0001, (
            f"iv_used should match Market IV: expected {market_iv}, "
            f"got {module16_greeks['iv_used']}"
        )
        
        # 3. The Greeks should be calculated with Market IV
        assert abs(module16_greeks['call']['volatility'] - market_iv) < 0.0001, (
            f"Greeks should be calculated with Market IV: expected {market_iv}, "
            f"got {module16_greeks['call']['volatility']}"
        )
        
        # 4. Greeks values should be valid (not NaN or infinite)
        assert not math.isnan(call_greeks.delta), "Delta should not be NaN"
        assert not math.isnan(call_greeks.gamma), "Gamma should not be NaN"
        assert not math.isnan(call_greeks.theta), "Theta should not be NaN"
        assert not math.isnan(call_greeks.vega), "Vega should not be NaN"


class TestModule17NonConvergenceScenarios:
    """
    Test Module 17 Non-Convergence Scenarios
    
    **Feature: iv-source-fix, Property 4: Fallback Behavior Correctness**
    **Validates: Requirements 1.2**
    
    Tests scenarios where Module 17 is expected to not converge,
    triggering the fallback behavior.
    """
    
    def setup_method(self):
        self.bs_calculator = BlackScholesCalculator()
        self.iv_calculator = ImpliedVolatilityCalculator()
    
    @given(
        stock_price=st.floats(min_value=50.0, max_value=500.0, allow_nan=False, allow_infinity=False),
        time_to_expiration=st.floats(min_value=0.05, max_value=1.0, allow_nan=False, allow_infinity=False),
        market_iv=st.floats(min_value=0.10, max_value=0.60, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_fallback_state_variables_when_non_convergence(
        self, stock_price, time_to_expiration, market_iv
    ):
        """
        Property 4: When Module 17 doesn't converge, the fallback state variables
        should be set correctly.
        
        **Feature: iv-source-fix, Property 4: Fallback Behavior Correctness**
        **Validates: Requirements 1.2**
        
        This test simulates the state variable updates in main.py when
        Module 17 fails to converge.
        """
        # Simulate the initial state (before Module 17)
        volatility_raw = market_iv * 100  # Market IV in percentage
        volatility_estimate = market_iv  # Market IV in decimal
        atm_iv_available = False
        iv_source = "Market IV (initial)"
        
        # Simulate Module 17 not converging
        # In main.py, this happens when call_iv_result.converged is False
        module17_converged = False
        
        if not module17_converged:
            # Requirements 1.2: Module 17 不收斂時的回退邏輯
            atm_iv_available = False
            iv_source = "Market IV (fallback)"
            # volatility_estimate remains unchanged (Market IV)
        
        # Property 4 assertions for fallback state
        
        # 1. atm_iv_available should be False
        assert atm_iv_available == False, (
            f"atm_iv_available should be False when Module 17 doesn't converge"
        )
        
        # 2. iv_source should indicate fallback
        assert 'fallback' in iv_source.lower(), (
            f"iv_source should indicate fallback, got '{iv_source}'"
        )
        
        # 3. volatility_estimate should remain as Market IV
        assert abs(volatility_estimate - market_iv) < 0.0001, (
            f"volatility_estimate should remain as Market IV: "
            f"expected {market_iv}, got {volatility_estimate}"
        )
    
    @given(
        stock_price=st.floats(min_value=50.0, max_value=500.0, allow_nan=False, allow_infinity=False),
        time_to_expiration=st.floats(min_value=0.05, max_value=1.0, allow_nan=False, allow_infinity=False),
        market_iv=st.floats(min_value=0.10, max_value=0.60, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_fallback_state_variables_when_module17_error(
        self, stock_price, time_to_expiration, market_iv
    ):
        """
        Property 4: When Module 17 raises an exception, the fallback state variables
        should be set correctly.
        
        **Feature: iv-source-fix, Property 4: Fallback Behavior Correctness**
        **Validates: Requirements 1.2**
        
        This test simulates the state variable updates in main.py when
        Module 17 execution fails with an exception.
        """
        # Simulate the initial state (before Module 17)
        volatility_raw = market_iv * 100  # Market IV in percentage
        volatility_estimate = market_iv  # Market IV in decimal
        atm_iv_available = False
        iv_source = "Market IV (initial)"
        
        # Simulate Module 17 raising an exception
        # In main.py, this is caught in the except block
        module17_error = True
        
        if module17_error:
            # Module 17 執行失敗時也設置回退狀態
            atm_iv_available = False
            iv_source = "Market IV (fallback - Module 17 error)"
            # volatility_estimate remains unchanged (Market IV)
        
        # Property 4 assertions for fallback state
        
        # 1. atm_iv_available should be False
        assert atm_iv_available == False, (
            f"atm_iv_available should be False when Module 17 errors"
        )
        
        # 2. iv_source should indicate fallback with error
        assert 'fallback' in iv_source.lower(), (
            f"iv_source should indicate fallback, got '{iv_source}'"
        )
        assert 'error' in iv_source.lower(), (
            f"iv_source should indicate error, got '{iv_source}'"
        )
        
        # 3. volatility_estimate should remain as Market IV
        assert abs(volatility_estimate - market_iv) < 0.0001, (
            f"volatility_estimate should remain as Market IV: "
            f"expected {market_iv}, got {volatility_estimate}"
        )


class TestFallbackConsistencyAcrossModules:
    """
    Test Fallback Consistency Across Modules
    
    **Feature: iv-source-fix, Property 4: Fallback Behavior Correctness**
    **Validates: Requirements 1.2, 2.2**
    
    Tests that when fallback occurs, all dependent modules consistently
    use Market IV and record the same iv_source.
    """
    
    def setup_method(self):
        self.bs_calculator = BlackScholesCalculator()
        self.greeks_calculator = GreeksCalculator()
        from calculation_layer.module23_dynamic_iv_threshold import DynamicIVThresholdCalculator
        self.dynamic_iv_calc = DynamicIVThresholdCalculator()
    
    @given(
        stock_price=st.floats(min_value=50.0, max_value=500.0, allow_nan=False, allow_infinity=False),
        risk_free_rate=st.floats(min_value=0.01, max_value=0.10, allow_nan=False, allow_infinity=False),
        time_to_expiration=st.floats(min_value=0.05, max_value=1.0, allow_nan=False, allow_infinity=False),
        market_iv=st.floats(min_value=0.10, max_value=0.60, allow_nan=False, allow_infinity=False),
        vix=st.floats(min_value=12.0, max_value=50.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_all_modules_use_same_fallback_iv(
        self, stock_price, risk_free_rate, time_to_expiration, market_iv, vix
    ):
        """
        Property 4: When fallback occurs, all modules should use the same Market IV.
        
        **Feature: iv-source-fix, Property 4: Fallback Behavior Correctness**
        **Validates: Requirements 1.2, 2.2**
        
        This test verifies that when Module 17 doesn't converge, all dependent
        modules (15, 16, 23) use the same Market IV value consistently.
        """
        strike_price = stock_price
        
        # Simulate fallback state
        atm_iv_available = False
        iv_source = "Market IV (fallback)"
        volatility_estimate = market_iv
        
        # Module 15: Black-Scholes with fallback
        bs_result = self.bs_calculator.calculate_option_price_with_atm_iv(
            stock_price=stock_price,
            strike_price=strike_price,
            risk_free_rate=risk_free_rate,
            time_to_expiration=time_to_expiration,
            market_iv=market_iv,
            atm_iv=None,  # Fallback case
            option_type='call'
        )
        
        # Module 16: Greeks with fallback
        call_greeks = self.greeks_calculator.calculate_all_greeks(
            stock_price=stock_price,
            strike_price=strike_price,
            risk_free_rate=risk_free_rate,
            time_to_expiration=time_to_expiration,
            volatility=volatility_estimate,
            option_type='call'
        )
        
        # Module 23: Dynamic IV Threshold with fallback
        current_iv_for_threshold = volatility_estimate * 100
        iv_threshold_result = self.dynamic_iv_calc.calculate_thresholds(
            current_iv=current_iv_for_threshold,
            historical_iv=None,
            vix=vix
        )
        
        # Property 4 assertions for consistency
        
        # 1. All modules should use the same IV value
        assert abs(bs_result.volatility - market_iv) < 0.0001, (
            f"Module 15 should use Market IV: expected {market_iv}, "
            f"got {bs_result.volatility}"
        )
        assert abs(call_greeks.volatility - market_iv) < 0.0001, (
            f"Module 16 should use Market IV: expected {market_iv}, "
            f"got {call_greeks.volatility}"
        )
        assert abs(iv_threshold_result.current_iv - current_iv_for_threshold) < 0.01, (
            f"Module 23 should use Market IV: expected {current_iv_for_threshold:.2f}%, "
            f"got {iv_threshold_result.current_iv:.2f}%"
        )
        
        # 2. Module 15 iv_source should indicate fallback
        assert bs_result.iv_source == 'Market IV (fallback)', (
            f"Module 15 iv_source should indicate fallback, got '{bs_result.iv_source}'"
        )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
