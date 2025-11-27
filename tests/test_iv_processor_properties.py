#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Property-based tests for IV Processor Enhancement
使用 Hypothesis 進行屬性測試

Feature: iv-processing-enhancement
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
import sys
import os
import math

# 添加項目根目錄到路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from calculation_layer.module22_optimal_strike import OptimalStrikeCalculator, StrikeAnalysis
from calculation_layer.module15_black_scholes import BlackScholesCalculator
from calculation_layer.module17_implied_volatility import ImpliedVolatilityCalculator


class TestIVRoundTrip:
    """
    **Feature: iv-processing-enhancement, Property 1: IV Calculation Round Trip**
    
    測試 IV 計算的往返一致性
    """
    
    def setup_method(self):
        self.calculator = OptimalStrikeCalculator()
        self.bs_calculator = BlackScholesCalculator()
        self.iv_calculator = ImpliedVolatilityCalculator()
    
    @given(
        stock_price=st.floats(min_value=10.0, max_value=500.0, allow_nan=False, allow_infinity=False),
        strike_ratio=st.floats(min_value=0.8, max_value=1.2, allow_nan=False, allow_infinity=False),
        known_iv=st.floats(min_value=0.10, max_value=1.0, allow_nan=False, allow_infinity=False),
        time_to_expiration=st.floats(min_value=0.05, max_value=2.0, allow_nan=False, allow_infinity=False),
        risk_free_rate=st.floats(min_value=0.01, max_value=0.10, allow_nan=False, allow_infinity=False),
        option_type=st.sampled_from(['call', 'put'])
    )
    @settings(max_examples=100)
    def test_iv_round_trip(self, stock_price, strike_ratio, known_iv, time_to_expiration, risk_free_rate, option_type):
        """
        **Feature: iv-processing-enhancement, Property 1: IV Calculation Round Trip**
        **Validates: Requirements 1.1, 1.2**
        
        Property: For any valid option with positive market price, if Module 17 calculates 
        an IV that converges, then using that IV in Black-Scholes should produce a price 
        within tolerance of the original market price.
        """
        strike_price = stock_price * strike_ratio
        
        # 使用已知 IV 計算期權價格
        bs_result = self.bs_calculator.calculate_option_price(
            stock_price=stock_price,
            strike_price=strike_price,
            risk_free_rate=risk_free_rate,
            time_to_expiration=time_to_expiration,
            volatility=known_iv,
            option_type=option_type
        )
        
        market_price = bs_result.option_price
        
        # 跳過價格太低的情況（數值不穩定）
        assume(market_price > 0.01)
        
        # 從市場價格反推 IV
        iv_result = self.iv_calculator.calculate_implied_volatility(
            market_price=market_price,
            stock_price=stock_price,
            strike_price=strike_price,
            risk_free_rate=risk_free_rate,
            time_to_expiration=time_to_expiration,
            option_type=option_type
        )
        
        # 如果收斂，驗證往返一致性
        if iv_result.converged:
            # 使用反推的 IV 重新計算價格
            bs_result_verify = self.bs_calculator.calculate_option_price(
                stock_price=stock_price,
                strike_price=strike_price,
                risk_free_rate=risk_free_rate,
                time_to_expiration=time_to_expiration,
                volatility=iv_result.implied_volatility,
                option_type=option_type
            )
            
            # 價格應該在容差範圍內
            price_diff = abs(bs_result_verify.option_price - market_price)
            tolerance = max(0.01, market_price * 0.01)  # 1% 或 $0.01
            
            assert price_diff < tolerance, \
                f"Round trip price difference {price_diff:.4f} exceeds tolerance {tolerance:.4f}"


class TestIVFormatDetection:
    """
    **Feature: iv-processing-enhancement, Property 2: IV Format Detection and Conversion**
    
    測試 IV 格式檢測和轉換
    """
    
    def setup_method(self):
        self.calculator = OptimalStrikeCalculator()
    
    @given(
        decimal_iv=st.floats(min_value=0.05, max_value=3.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_decimal_format_detection(self, decimal_iv):
        """
        **Feature: iv-processing-enhancement, Property 2: IV Format Detection and Conversion**
        **Validates: Requirements 1.4, 1.5, 2.1**
        
        Property: IV values in decimal form (0.05-3.0) should be recognized and returned 
        in decimal form within [0.01, 5.0].
        """
        result = self.calculator._normalize_iv(decimal_iv)
        
        # 結果應該在 [0.01, 5.0] 範圍內
        assert 0.01 <= result <= 5.0, \
            f"Normalized IV {result} outside valid range [0.01, 5.0]"
        
        # 對於有效的小數形式，結果應該接近原值（除非被限制）
        expected = max(0.01, min(5.0, decimal_iv))
        assert abs(result - expected) < 0.001, \
            f"Decimal IV {decimal_iv} normalized to {result}, expected {expected}"
    
    @given(
        percentage_iv=st.floats(min_value=5.0, max_value=300.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_percentage_format_detection(self, percentage_iv):
        """
        **Feature: iv-processing-enhancement, Property 2: IV Format Detection and Conversion**
        **Validates: Requirements 1.4, 1.5, 2.1**
        
        Property: IV values in percentage form (5-300) should be converted to decimal 
        form by dividing by 100.
        """
        result = self.calculator._normalize_iv(percentage_iv)
        
        # 結果應該在 [0.01, 5.0] 範圍內
        assert 0.01 <= result <= 5.0, \
            f"Normalized IV {result} outside valid range [0.01, 5.0]"
        
        # 百分比形式應該被除以 100
        expected_decimal = percentage_iv / 100.0
        expected = max(0.01, min(5.0, expected_decimal))
        assert abs(result - expected) < 0.001, \
            f"Percentage IV {percentage_iv}% normalized to {result}, expected {expected}"


class TestIVClamping:
    """
    **Feature: iv-processing-enhancement, Property 3: IV Clamping Bounds**
    
    測試 IV 限制邊界
    """
    
    def setup_method(self):
        self.calculator = OptimalStrikeCalculator()
    
    @given(
        raw_iv=st.floats(min_value=-10.0, max_value=1000.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_iv_clamping_bounds(self, raw_iv):
        """
        **Feature: iv-processing-enhancement, Property 3: IV Clamping Bounds**
        **Validates: Requirements 2.2, 2.3**
        
        Property: For any IV value after normalization, the result should be clamped 
        to the range [0.01, 5.0].
        """
        result = self.calculator._normalize_iv(raw_iv)
        
        # 結果必須在 [0.01, 5.0] 範圍內
        assert 0.01 <= result <= 5.0, \
            f"Normalized IV {result} outside clamped range [0.01, 5.0] for input {raw_iv}"
    
    def test_iv_below_minimum_clamped(self):
        """
        **Feature: iv-processing-enhancement, Property 3: IV Clamping Bounds**
        **Validates: Requirements 2.2**
        
        Property: Values below 0.01 should be clamped to exactly 0.01.
        """
        # 測試非常小的正值
        result = self.calculator._normalize_iv(0.001)
        assert result == 0.01, f"IV 0.001 should be clamped to 0.01, got {result}"
    
    def test_iv_above_maximum_clamped(self):
        """
        **Feature: iv-processing-enhancement, Property 3: IV Clamping Bounds**
        **Validates: Requirements 2.3**
        
        Property: Values above 5.0 should be clamped to exactly 5.0.
        """
        # 測試非常大的值（會被視為百分比並轉換）
        # 600% -> 6.0 -> clamped to 5.0
        result = self.calculator._normalize_iv(600.0)
        assert result == 5.0, f"IV 600% should be clamped to 5.0, got {result}"


class TestIVFallbackChain:
    """
    **Feature: iv-processing-enhancement, Property 4: IV Fallback Chain**
    
    測試 IV 回退鏈
    """
    
    def setup_method(self):
        self.calculator = OptimalStrikeCalculator()
    
    @given(
        current_price=st.floats(min_value=10.0, max_value=500.0, allow_nan=False, allow_infinity=False),
        strike_ratio=st.floats(min_value=0.8, max_value=1.2, allow_nan=False, allow_infinity=False),
        time_to_expiration=st.floats(min_value=0.05, max_value=1.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_fallback_always_returns_valid_iv(self, current_price, strike_ratio, time_to_expiration):
        """
        **Feature: iv-processing-enhancement, Property 4: IV Fallback Chain**
        **Validates: Requirements 1.3, 1.6**
        
        Property: For any option data, the IV processor should return a valid IV 
        (in range [0.01, 5.0]) regardless of whether Module 17 converges, Yahoo data 
        is valid, or both fail.
        """
        strike = current_price * strike_ratio
        
        # 測試場景 1: 完全空的期權數據
        empty_option = {}
        iv, source = self.calculator._get_corrected_iv(
            option=empty_option,
            current_price=current_price,
            strike=strike,
            option_type='call',
            time_to_expiration=time_to_expiration
        )
        
        assert 0.01 <= iv <= 5.0, f"IV {iv} outside valid range for empty option"
        assert source == 'default', f"Expected 'default' source for empty option, got '{source}'"
    
    @given(
        current_price=st.floats(min_value=50.0, max_value=200.0, allow_nan=False, allow_infinity=False),
        yahoo_iv=st.floats(min_value=0.1, max_value=1.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_fallback_to_yahoo_iv(self, current_price, yahoo_iv):
        """
        **Feature: iv-processing-enhancement, Property 4: IV Fallback Chain**
        **Validates: Requirements 1.3, 1.6**
        
        Property: When Module 17 cannot calculate IV (no market price), 
        the system should fall back to Yahoo Finance IV.
        """
        strike = current_price
        
        # 期權數據只有 Yahoo IV，沒有市場價格
        option_with_yahoo_iv = {
            'strike': strike,
            'impliedVolatility': yahoo_iv,
            'lastPrice': 0,  # 無市場價格
            'bid': 0,
            'ask': 0
        }
        
        iv, source = self.calculator._get_corrected_iv(
            option=option_with_yahoo_iv,
            current_price=current_price,
            strike=strike,
            option_type='call',
            time_to_expiration=0.25
        )
        
        assert 0.01 <= iv <= 5.0, f"IV {iv} outside valid range"
        assert source == 'yahoo', f"Expected 'yahoo' source, got '{source}'"
        
        # 驗證 Yahoo IV 被正確標準化
        expected_iv = max(0.01, min(5.0, yahoo_iv))
        assert abs(iv - expected_iv) < 0.001, \
            f"Yahoo IV {yahoo_iv} not correctly normalized to {expected_iv}, got {iv}"
    
    @given(
        current_price=st.floats(min_value=50.0, max_value=200.0, allow_nan=False, allow_infinity=False),
        known_iv=st.floats(min_value=0.15, max_value=0.50, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_module17_preferred_over_yahoo(self, current_price, known_iv):
        """
        **Feature: iv-processing-enhancement, Property 4: IV Fallback Chain**
        **Validates: Requirements 1.1, 1.2**
        
        Property: When Module 17 can calculate IV successfully, it should be 
        preferred over Yahoo Finance IV.
        """
        strike = current_price
        bs_calculator = BlackScholesCalculator()
        
        # 使用已知 IV 計算期權價格
        bs_result = bs_calculator.calculate_option_price(
            stock_price=current_price,
            strike_price=strike,
            risk_free_rate=0.045,
            time_to_expiration=0.25,
            volatility=known_iv,
            option_type='call'
        )
        
        market_price = bs_result.option_price
        assume(market_price > 0.1)  # 確保價格足夠高
        
        # 期權數據有市場價格和不同的 Yahoo IV
        different_yahoo_iv = known_iv + 0.1  # 故意設置不同的 Yahoo IV
        option_with_both = {
            'strike': strike,
            'impliedVolatility': different_yahoo_iv,
            'lastPrice': market_price,
            'bid': market_price * 0.95,
            'ask': market_price * 1.05
        }
        
        iv, source = self.calculator._get_corrected_iv(
            option=option_with_both,
            current_price=current_price,
            strike=strike,
            option_type='call',
            time_to_expiration=0.25
        )
        
        # 應該使用 Module 17 計算的 IV
        assert source == 'module17', f"Expected 'module17' source, got '{source}'"
        
        # 計算的 IV 應該接近已知 IV
        assert abs(iv - known_iv) < 0.05, \
            f"Module 17 IV {iv} differs significantly from known IV {known_iv}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
