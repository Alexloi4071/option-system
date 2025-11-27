#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Property-based tests for Put-Call Parity Integration
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
from calculation_layer.module19_put_call_parity import PutCallParityValidator


class TestParityDeviationDetection:
    """
    **Feature: iv-processing-enhancement, Property 8: Put-Call Parity Deviation Detection**
    
    測試 Put-Call Parity 偏離檢測
    """
    
    def setup_method(self):
        self.calculator = OptimalStrikeCalculator()
        self.bs_calculator = BlackScholesCalculator()
        self.parity_validator = PutCallParityValidator()
    
    @given(
        stock_price=st.floats(min_value=50.0, max_value=300.0, allow_nan=False, allow_infinity=False),
        strike_ratio=st.floats(min_value=0.95, max_value=1.05, allow_nan=False, allow_infinity=False),
        volatility=st.floats(min_value=0.15, max_value=0.60, allow_nan=False, allow_infinity=False),
        time_to_expiration=st.floats(min_value=0.05, max_value=1.0, allow_nan=False, allow_infinity=False),
        risk_free_rate=st.floats(min_value=0.01, max_value=0.10, allow_nan=False, allow_infinity=False),
        call_deviation_pct=st.floats(min_value=-0.10, max_value=0.10, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_parity_deviation_detection(
        self, stock_price, strike_ratio, volatility, time_to_expiration, 
        risk_free_rate, call_deviation_pct
    ):
        """
        **Feature: iv-processing-enhancement, Property 8: Put-Call Parity Deviation Detection**
        **Validates: Requirements 4.1, 4.2**
        
        Property: For any option pair (Call and Put at same strike), if the deviation 
        from Put-Call Parity exceeds 2%, the system should flag it as potentially mispriced.
        """
        strike_price = stock_price * strike_ratio
        
        # 使用 Black-Scholes 計算理論價格
        call_result = self.bs_calculator.calculate_option_price(
            stock_price=stock_price,
            strike_price=strike_price,
            risk_free_rate=risk_free_rate,
            time_to_expiration=time_to_expiration,
            volatility=volatility,
            option_type='call'
        )
        
        put_result = self.bs_calculator.calculate_option_price(
            stock_price=stock_price,
            strike_price=strike_price,
            risk_free_rate=risk_free_rate,
            time_to_expiration=time_to_expiration,
            volatility=volatility,
            option_type='put'
        )
        
        theoretical_call_price = call_result.option_price
        theoretical_put_price = put_result.option_price
        
        # 跳過價格太低的情況
        assume(theoretical_call_price > 0.1)
        assume(theoretical_put_price > 0.1)
        
        # 添加偏離到 Call 價格
        deviated_call_price = theoretical_call_price * (1 + call_deviation_pct)
        assume(deviated_call_price > 0)
        
        # 構建期權鏈數據
        option_chain = {
            'calls': [{
                'strike': strike_price,
                'lastPrice': deviated_call_price,
                'bid': deviated_call_price * 0.98,
                'ask': deviated_call_price * 1.02,
                'volume': 100,
                'openInterest': 500
            }],
            'puts': [{
                'strike': strike_price,
                'lastPrice': theoretical_put_price,
                'bid': theoretical_put_price * 0.98,
                'ask': theoretical_put_price * 1.02,
                'volume': 100,
                'openInterest': 500
            }]
        }
        
        # 調用 _validate_parity_for_atm
        result = self.calculator._validate_parity_for_atm(
            option_chain=option_chain,
            current_price=stock_price,
            time_to_expiration=time_to_expiration,
            risk_free_rate=risk_free_rate
        )
        
        # 驗證結果不為 None
        assert result is not None, "Parity validation should return a result"
        
        # 驗證結果包含必要字段
        assert 'valid' in result, "Result should contain 'valid' field"
        assert 'deviation_pct' in result, "Result should contain 'deviation_pct' field"
        assert 'arbitrage_opportunity' in result, "Result should contain 'arbitrage_opportunity' field"
        
        # 計算預期的偏離
        # 理論差異: S - K×e^(-r×T)
        discount_factor = math.exp(-risk_free_rate * time_to_expiration)
        theoretical_difference = stock_price - strike_price * discount_factor
        
        # 實際差異: C - P
        actual_difference = deviated_call_price - theoretical_put_price
        
        # 偏離
        deviation = actual_difference - theoretical_difference
        
        # 計算偏離百分比
        if abs(theoretical_difference) > 0.01:
            expected_deviation_pct = abs((deviation / abs(theoretical_difference)) * 100)
        else:
            expected_deviation_pct = 0.0
        
        # 驗證: 如果偏離超過 2%，valid 應該為 False
        # Requirements 4.2: 偏離超過 2% 時標記為可能定價錯誤
        if expected_deviation_pct > 2.0:
            assert result['valid'] == False, \
                f"Deviation {expected_deviation_pct:.2f}% > 2%, should be flagged as invalid"
        else:
            assert result['valid'] == True, \
                f"Deviation {expected_deviation_pct:.2f}% <= 2%, should be valid"
    
    @given(
        stock_price=st.floats(min_value=50.0, max_value=300.0, allow_nan=False, allow_infinity=False),
        volatility=st.floats(min_value=0.15, max_value=0.60, allow_nan=False, allow_infinity=False),
        time_to_expiration=st.floats(min_value=0.1, max_value=1.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_theoretical_prices_pass_parity(self, stock_price, volatility, time_to_expiration):
        """
        **Feature: iv-processing-enhancement, Property 8: Put-Call Parity Deviation Detection**
        **Validates: Requirements 4.1, 4.2**
        
        Property: Option pairs with theoretical Black-Scholes prices should always 
        pass the Put-Call Parity validation (deviation < 2%).
        """
        strike_price = stock_price  # ATM
        risk_free_rate = 0.045
        
        # 使用 Black-Scholes 計算理論價格
        call_result = self.bs_calculator.calculate_option_price(
            stock_price=stock_price,
            strike_price=strike_price,
            risk_free_rate=risk_free_rate,
            time_to_expiration=time_to_expiration,
            volatility=volatility,
            option_type='call'
        )
        
        put_result = self.bs_calculator.calculate_option_price(
            stock_price=stock_price,
            strike_price=strike_price,
            risk_free_rate=risk_free_rate,
            time_to_expiration=time_to_expiration,
            volatility=volatility,
            option_type='put'
        )
        
        theoretical_call_price = call_result.option_price
        theoretical_put_price = put_result.option_price
        
        # 跳過價格太低的情況
        assume(theoretical_call_price > 0.1)
        assume(theoretical_put_price > 0.1)
        
        # 構建期權鏈數據（使用理論價格）
        option_chain = {
            'calls': [{
                'strike': strike_price,
                'lastPrice': theoretical_call_price,
                'bid': theoretical_call_price * 0.99,
                'ask': theoretical_call_price * 1.01,
                'volume': 100,
                'openInterest': 500
            }],
            'puts': [{
                'strike': strike_price,
                'lastPrice': theoretical_put_price,
                'bid': theoretical_put_price * 0.99,
                'ask': theoretical_put_price * 1.01,
                'volume': 100,
                'openInterest': 500
            }]
        }
        
        # 調用 _validate_parity_for_atm
        result = self.calculator._validate_parity_for_atm(
            option_chain=option_chain,
            current_price=stock_price,
            time_to_expiration=time_to_expiration,
            risk_free_rate=risk_free_rate
        )
        
        # 理論價格應該完美滿足 Parity
        assert result is not None, "Parity validation should return a result"
        assert result['valid'] == True, \
            f"Theoretical prices should pass parity, got deviation {result['deviation_pct']:.2f}%"
        assert abs(result['deviation_pct']) < 1.0, \
            f"Theoretical prices should have minimal deviation, got {result['deviation_pct']:.2f}%"
    
    def test_missing_option_data_returns_none(self):
        """
        **Feature: iv-processing-enhancement, Property 8: Put-Call Parity Deviation Detection**
        **Validates: Requirements 4.5**
        
        Property: When option data is missing, the validation should return None 
        and log a warning.
        """
        # 空期權鏈
        empty_chain = {'calls': [], 'puts': []}
        result = self.calculator._validate_parity_for_atm(
            option_chain=empty_chain,
            current_price=100.0,
            time_to_expiration=0.25
        )
        assert result is None, "Empty option chain should return None"
        
        # 只有 calls
        calls_only = {
            'calls': [{'strike': 100, 'lastPrice': 5.0, 'bid': 4.9, 'ask': 5.1}],
            'puts': []
        }
        result = self.calculator._validate_parity_for_atm(
            option_chain=calls_only,
            current_price=100.0,
            time_to_expiration=0.25
        )
        assert result is None, "Calls-only chain should return None"
        
        # 只有 puts
        puts_only = {
            'calls': [],
            'puts': [{'strike': 100, 'lastPrice': 5.0, 'bid': 4.9, 'ask': 5.1}]
        }
        result = self.calculator._validate_parity_for_atm(
            option_chain=puts_only,
            current_price=100.0,
            time_to_expiration=0.25
        )
        assert result is None, "Puts-only chain should return None"
    
    def test_no_common_strikes_returns_none(self):
        """
        **Feature: iv-processing-enhancement, Property 8: Put-Call Parity Deviation Detection**
        **Validates: Requirements 4.5**
        
        Property: When there are no common strikes between calls and puts, 
        the validation should return None.
        """
        # 不同行使價的 calls 和 puts
        no_common = {
            'calls': [{'strike': 100, 'lastPrice': 5.0, 'bid': 4.9, 'ask': 5.1}],
            'puts': [{'strike': 110, 'lastPrice': 5.0, 'bid': 4.9, 'ask': 5.1}]
        }
        result = self.calculator._validate_parity_for_atm(
            option_chain=no_common,
            current_price=105.0,
            time_to_expiration=0.25
        )
        assert result is None, "No common strikes should return None"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
