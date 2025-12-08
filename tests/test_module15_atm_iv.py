#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Module 15 ATM IV 準確性屬性測試

測試使用 ATM IV 計算的期權理論價格準確性
**Feature: option-calculation-fixes, Property 3: ATM IV 理論價格準確性**
**Validates: Requirements 3.4**
"""

import sys
import os
import math

# 添加項目根目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hypothesis import given, strategies as st, settings, assume
from calculation_layer.module15_black_scholes import BlackScholesCalculator, BSPricingResult
from calculation_layer.module17_implied_volatility import ImpliedVolatilityCalculator


class TestATMIVAccuracy:
    """ATM IV 理論價格準確性屬性測試類"""
    
    def setup_method(self):
        """測試前準備"""
        self.bs_calculator = BlackScholesCalculator()
        self.iv_calculator = ImpliedVolatilityCalculator()
    
    @settings(max_examples=100)
    @given(
        stock_price=st.floats(min_value=50.0, max_value=500.0, allow_nan=False, allow_infinity=False),
        strike_ratio=st.floats(min_value=0.85, max_value=1.15, allow_nan=False, allow_infinity=False),
        atm_iv=st.floats(min_value=0.10, max_value=0.80, allow_nan=False, allow_infinity=False),
        time_to_expiration=st.floats(min_value=0.02, max_value=1.0, allow_nan=False, allow_infinity=False),
        risk_free_rate=st.floats(min_value=0.01, max_value=0.10, allow_nan=False, allow_infinity=False),
        option_type=st.sampled_from(['call', 'put'])
    )
    def test_atm_iv_theoretical_price_accuracy(
        self,
        stock_price: float,
        strike_ratio: float,
        atm_iv: float,
        time_to_expiration: float,
        risk_free_rate: float,
        option_type: str
    ):
        """
        **Feature: option-calculation-fixes, Property 3: ATM IV 理論價格準確性**
        **Validates: Requirements 3.4**
        
        For any valid option parameters, when using ATM IV to calculate the theoretical
        price, the result should be within 15% of the market price (which was used to
        derive the ATM IV in the first place).
        
        This is a round-trip property:
        1. Generate a "market price" using BS model with known ATM IV
        2. Use calculate_option_price_with_atm_iv with the same ATM IV
        3. The theoretical price should match the market price closely
        """
        strike_price = stock_price * strike_ratio
        
        # Step 1: Generate a "market price" using the ATM IV
        # This simulates what we would observe in the market
        market_result = self.bs_calculator.calculate_option_price(
            stock_price=stock_price,
            strike_price=strike_price,
            risk_free_rate=risk_free_rate,
            time_to_expiration=time_to_expiration,
            volatility=atm_iv,
            option_type=option_type
        )
        market_price = market_result.option_price
        
        # Skip if market price is too small (numerical instability)
        assume(market_price > 0.01)
        
        # Step 2: Use calculate_option_price_with_atm_iv with the ATM IV
        # Use a different market_iv to ensure ATM IV is being used
        market_iv = atm_iv * 1.2  # 20% higher than ATM IV
        
        theoretical_result = self.bs_calculator.calculate_option_price_with_atm_iv(
            stock_price=stock_price,
            strike_price=strike_price,
            risk_free_rate=risk_free_rate,
            time_to_expiration=time_to_expiration,
            market_iv=market_iv,
            atm_iv=atm_iv,
            option_type=option_type
        )
        
        # Step 3: Verify the theoretical price matches the market price
        # Since we used the same IV, they should be essentially identical
        price_diff = abs(theoretical_result.option_price - market_price)
        price_diff_pct = (price_diff / market_price) * 100
        
        # The prices should be nearly identical (within floating point precision)
        # Using 0.01% tolerance for numerical precision
        assert price_diff_pct < 0.01, (
            f"理論價格與市場價格偏差過大: {price_diff_pct:.4f}%, "
            f"理論價格: ${theoretical_result.option_price:.4f}, "
            f"市場價格: ${market_price:.4f}, "
            f"ATM IV: {atm_iv*100:.2f}%"
        )
        
        # Verify IV source is correctly set
        assert theoretical_result.iv_source == 'ATM IV (Module 17)', (
            f"IV 來源應該是 'ATM IV (Module 17)', 但得到 '{theoretical_result.iv_source}'"
        )
    
    @settings(max_examples=100)
    @given(
        stock_price=st.floats(min_value=50.0, max_value=500.0, allow_nan=False, allow_infinity=False),
        strike_ratio=st.floats(min_value=0.85, max_value=1.15, allow_nan=False, allow_infinity=False),
        market_iv=st.floats(min_value=0.10, max_value=0.80, allow_nan=False, allow_infinity=False),
        time_to_expiration=st.floats(min_value=0.02, max_value=1.0, allow_nan=False, allow_infinity=False),
        risk_free_rate=st.floats(min_value=0.01, max_value=0.10, allow_nan=False, allow_infinity=False),
        option_type=st.sampled_from(['call', 'put'])
    )
    def test_fallback_to_market_iv_when_atm_iv_unavailable(
        self,
        stock_price: float,
        strike_ratio: float,
        market_iv: float,
        time_to_expiration: float,
        risk_free_rate: float,
        option_type: str
    ):
        """
        **Feature: option-calculation-fixes, Property 3: ATM IV 理論價格準確性**
        **Validates: Requirements 3.2**
        
        When ATM IV is not available (None), the method should fall back to market_iv
        and correctly label the IV source.
        """
        strike_price = stock_price * strike_ratio
        
        # Calculate with atm_iv=None (should fall back to market_iv)
        result = self.bs_calculator.calculate_option_price_with_atm_iv(
            stock_price=stock_price,
            strike_price=strike_price,
            risk_free_rate=risk_free_rate,
            time_to_expiration=time_to_expiration,
            market_iv=market_iv,
            atm_iv=None,  # Not available
            option_type=option_type
        )
        
        # Verify IV source indicates fallback
        assert result.iv_source == 'Market IV (fallback)', (
            f"IV 來源應該是 'Market IV (fallback)', 但得到 '{result.iv_source}'"
        )
        
        # Verify the volatility used is market_iv
        assert abs(result.volatility - market_iv) < 1e-10, (
            f"使用的波動率應該是 market_iv ({market_iv}), 但得到 {result.volatility}"
        )

    
    @settings(max_examples=100)
    @given(
        stock_price=st.floats(min_value=50.0, max_value=500.0, allow_nan=False, allow_infinity=False),
        strike_ratio=st.floats(min_value=0.85, max_value=1.15, allow_nan=False, allow_infinity=False),
        market_iv=st.floats(min_value=0.10, max_value=0.80, allow_nan=False, allow_infinity=False),
        time_to_expiration=st.floats(min_value=0.02, max_value=1.0, allow_nan=False, allow_infinity=False),
        risk_free_rate=st.floats(min_value=0.01, max_value=0.10, allow_nan=False, allow_infinity=False),
        option_type=st.sampled_from(['call', 'put'])
    )
    def test_fallback_to_market_iv_when_atm_iv_zero(
        self,
        stock_price: float,
        strike_ratio: float,
        market_iv: float,
        time_to_expiration: float,
        risk_free_rate: float,
        option_type: str
    ):
        """
        **Feature: option-calculation-fixes, Property 3: ATM IV 理論價格準確性**
        **Validates: Requirements 3.2**
        
        When ATM IV is zero or negative, the method should fall back to market_iv.
        """
        strike_price = stock_price * strike_ratio
        
        # Calculate with atm_iv=0 (should fall back to market_iv)
        result = self.bs_calculator.calculate_option_price_with_atm_iv(
            stock_price=stock_price,
            strike_price=strike_price,
            risk_free_rate=risk_free_rate,
            time_to_expiration=time_to_expiration,
            market_iv=market_iv,
            atm_iv=0.0,  # Zero IV
            option_type=option_type
        )
        
        # Verify IV source indicates fallback
        assert result.iv_source == 'Market IV (fallback)', (
            f"IV 來源應該是 'Market IV (fallback)', 但得到 '{result.iv_source}'"
        )
    
    @settings(max_examples=100)
    @given(
        stock_price=st.floats(min_value=50.0, max_value=500.0, allow_nan=False, allow_infinity=False),
        strike_ratio=st.floats(min_value=0.85, max_value=1.15, allow_nan=False, allow_infinity=False),
        atm_iv=st.floats(min_value=0.10, max_value=0.80, allow_nan=False, allow_infinity=False),
        market_iv=st.floats(min_value=0.10, max_value=0.80, allow_nan=False, allow_infinity=False),
        time_to_expiration=st.floats(min_value=0.02, max_value=1.0, allow_nan=False, allow_infinity=False),
        risk_free_rate=st.floats(min_value=0.01, max_value=0.10, allow_nan=False, allow_infinity=False),
        option_type=st.sampled_from(['call', 'put'])
    )
    def test_atm_iv_takes_priority_over_market_iv(
        self,
        stock_price: float,
        strike_ratio: float,
        atm_iv: float,
        market_iv: float,
        time_to_expiration: float,
        risk_free_rate: float,
        option_type: str
    ):
        """
        **Feature: option-calculation-fixes, Property 3: ATM IV 理論價格準確性**
        **Validates: Requirements 3.1**
        
        When both ATM IV and market IV are provided, ATM IV should take priority.
        """
        # Ensure ATM IV and market IV are different
        assume(abs(atm_iv - market_iv) > 0.05)
        
        strike_price = stock_price * strike_ratio
        
        # Calculate with both IVs provided
        result = self.bs_calculator.calculate_option_price_with_atm_iv(
            stock_price=stock_price,
            strike_price=strike_price,
            risk_free_rate=risk_free_rate,
            time_to_expiration=time_to_expiration,
            market_iv=market_iv,
            atm_iv=atm_iv,
            option_type=option_type
        )
        
        # Verify ATM IV was used (not market IV)
        assert abs(result.volatility - atm_iv) < 1e-10, (
            f"應該使用 ATM IV ({atm_iv}), 但使用了 {result.volatility}"
        )
        
        # Verify IV source
        assert result.iv_source == 'ATM IV (Module 17)', (
            f"IV 來源應該是 'ATM IV (Module 17)', 但得到 '{result.iv_source}'"
        )
    
    @settings(max_examples=50)
    @given(
        stock_price=st.floats(min_value=100.0, max_value=300.0, allow_nan=False, allow_infinity=False),
        atm_iv=st.floats(min_value=0.15, max_value=0.50, allow_nan=False, allow_infinity=False),
        time_to_expiration=st.floats(min_value=0.05, max_value=0.5, allow_nan=False, allow_infinity=False),
        risk_free_rate=st.floats(min_value=0.02, max_value=0.08, allow_nan=False, allow_infinity=False),
        option_type=st.sampled_from(['call', 'put'])
    )
    def test_atm_iv_round_trip_accuracy(
        self,
        stock_price: float,
        atm_iv: float,
        time_to_expiration: float,
        risk_free_rate: float,
        option_type: str
    ):
        """
        **Feature: option-calculation-fixes, Property 3: ATM IV 理論價格準確性**
        **Validates: Requirements 3.4**
        
        Round-trip test: Generate market price with ATM IV, extract IV from that price,
        then verify the extracted IV matches the original ATM IV.
        
        This validates that using ATM IV produces prices consistent with market pricing.
        """
        # ATM option (strike = stock price)
        strike_price = stock_price
        
        # Step 1: Generate market price using ATM IV
        market_result = self.bs_calculator.calculate_option_price_with_atm_iv(
            stock_price=stock_price,
            strike_price=strike_price,
            risk_free_rate=risk_free_rate,
            time_to_expiration=time_to_expiration,
            market_iv=atm_iv,  # Use same IV as fallback
            atm_iv=atm_iv,
            option_type=option_type
        )
        market_price = market_result.option_price
        
        # Skip if market price is too small
        assume(market_price > 0.10)
        
        # Step 2: Extract IV from the market price
        iv_result = self.iv_calculator.calculate_implied_volatility(
            market_price=market_price,
            stock_price=stock_price,
            strike_price=strike_price,
            risk_free_rate=risk_free_rate,
            time_to_expiration=time_to_expiration,
            option_type=option_type
        )
        
        # Step 3: Verify the extracted IV matches the original ATM IV
        # Allow 1% relative error for numerical precision
        if iv_result.converged:
            iv_diff_pct = abs(iv_result.implied_volatility - atm_iv) / atm_iv * 100
            assert iv_diff_pct < 1.0, (
                f"Round-trip IV 偏差過大: {iv_diff_pct:.4f}%, "
                f"原始 ATM IV: {atm_iv*100:.2f}%, "
                f"提取的 IV: {iv_result.implied_volatility*100:.2f}%"
            )


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
