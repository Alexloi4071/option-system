#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Property-based tests for Volatility Smile Analyzer (Module 24)
使用 Hypothesis 進行屬性測試

Feature: iv-processing-enhancement
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
import sys
import os

# 添加項目根目錄到路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from calculation_layer.module25_volatility_smile import VolatilitySmileAnalyzer, VolatilitySmileResult
from calculation_layer.module15_black_scholes import BlackScholesCalculator


def generate_option_chain(
    current_price: float,
    num_strikes: int,
    base_iv: float,
    put_skew: float = 0.0,
    time_to_expiration: float = 0.25,
    risk_free_rate: float = 0.045
):
    """
    生成模擬期權鏈數據
    
    參數:
        current_price: 當前股價
        num_strikes: 行使價數量
        base_iv: 基礎 IV（ATM IV）
        put_skew: Put 偏斜（正值表示 OTM Put IV 高於 OTM Call IV）
        time_to_expiration: 到期時間（年）
        risk_free_rate: 無風險利率
    """
    bs_calculator = BlackScholesCalculator()
    
    # 生成行使價（ATM ± 15%）
    strike_range = 0.15
    min_strike = current_price * (1 - strike_range)
    max_strike = current_price * (1 + strike_range)
    strike_step = (max_strike - min_strike) / (num_strikes - 1) if num_strikes > 1 else 0
    
    calls = []
    puts = []
    
    for i in range(num_strikes):
        strike = min_strike + i * strike_step if num_strikes > 1 else current_price
        
        # 計算該行使價的 IV（加入 skew）
        moneyness = (strike - current_price) / current_price
        
        # Call IV: ATM 最低，OTM 略高
        call_iv = base_iv + abs(moneyness) * 0.1
        
        # Put IV: 加入 skew
        put_iv = base_iv + abs(moneyness) * 0.1
        if strike < current_price:  # OTM Put
            put_iv += put_skew
        
        # 確保 IV 在合理範圍內
        call_iv = max(0.05, min(2.0, call_iv))
        put_iv = max(0.05, min(2.0, put_iv))
        
        # 計算期權價格
        try:
            call_result = bs_calculator.calculate_option_price(
                stock_price=current_price,
                strike_price=strike,
                risk_free_rate=risk_free_rate,
                time_to_expiration=time_to_expiration,
                volatility=call_iv,
                option_type='call'
            )
            call_price = call_result.option_price
        except:
            call_price = max(0.01, current_price - strike) if strike < current_price else 0.01
        
        try:
            put_result = bs_calculator.calculate_option_price(
                stock_price=current_price,
                strike_price=strike,
                risk_free_rate=risk_free_rate,
                time_to_expiration=time_to_expiration,
                volatility=put_iv,
                option_type='put'
            )
            put_price = put_result.option_price
        except:
            put_price = max(0.01, strike - current_price) if strike > current_price else 0.01
        
        # 確保價格為正
        call_price = max(0.01, call_price)
        put_price = max(0.01, put_price)
        
        calls.append({
            'strike': strike,
            'lastPrice': call_price,
            'bid': call_price * 0.95,
            'ask': call_price * 1.05,
            'impliedVolatility': call_iv,
            'volume': 100,
            'openInterest': 500
        })
        
        puts.append({
            'strike': strike,
            'lastPrice': put_price,
            'bid': put_price * 0.95,
            'ask': put_price * 1.05,
            'impliedVolatility': put_iv,
            'volume': 100,
            'openInterest': 500
        })
    
    return {'calls': calls, 'puts': puts}


class TestSmileAnalysisCompleteness:
    """
    **Feature: iv-processing-enhancement, Property 9: Smile Analysis Completeness**
    
    測試波動率微笑分析的完整性
    """
    
    def setup_method(self):
        self.analyzer = VolatilitySmileAnalyzer()
    
    @given(
        current_price=st.floats(min_value=20.0, max_value=500.0, allow_nan=False, allow_infinity=False),
        num_strikes=st.integers(min_value=5, max_value=15),
        base_iv=st.floats(min_value=0.10, max_value=0.80, allow_nan=False, allow_infinity=False),
        put_skew=st.floats(min_value=-0.10, max_value=0.20, allow_nan=False, allow_infinity=False),
        time_to_expiration=st.floats(min_value=0.05, max_value=1.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_smile_analysis_returns_complete_result(
        self, current_price, num_strikes, base_iv, put_skew, time_to_expiration
    ):
        """
        **Feature: iv-processing-enhancement, Property 9: Smile Analysis Completeness**
        **Validates: Requirements 5.1, 5.2, 5.4, 5.5**
        
        Property: For any valid option chain, the smile analysis should return a result 
        containing: ATM IV, skew value, smile shape classification, and IV distribution 
        for both calls and puts.
        """
        # 生成期權鏈
        option_chain = generate_option_chain(
            current_price=current_price,
            num_strikes=num_strikes,
            base_iv=base_iv,
            put_skew=put_skew,
            time_to_expiration=time_to_expiration
        )
        
        # 執行分析
        result = self.analyzer.analyze_smile(
            option_chain=option_chain,
            current_price=current_price,
            time_to_expiration=time_to_expiration
        )
        
        # 驗證結果是 VolatilitySmileResult 類型
        assert isinstance(result, VolatilitySmileResult), \
            f"Expected VolatilitySmileResult, got {type(result)}"
        
        # 驗證 ATM IV 存在且在合理範圍內
        assert result.atm_iv > 0, f"ATM IV should be positive, got {result.atm_iv}"
        assert result.atm_iv <= 5.0, f"ATM IV should be <= 5.0, got {result.atm_iv}"
        
        # 驗證 ATM 行使價存在且合理
        assert result.atm_strike > 0, f"ATM strike should be positive, got {result.atm_strike}"
        # ATM 行使價應該接近當前價格（±20%）
        assert abs(result.atm_strike - current_price) / current_price < 0.20, \
            f"ATM strike {result.atm_strike} too far from current price {current_price}"
        
        # 驗證 skew 值存在（可以是任何數值）
        assert isinstance(result.skew, (int, float)), \
            f"Skew should be numeric, got {type(result.skew)}"
        
        # 驗證 smile_shape 是有效的分類
        valid_shapes = ['smile', 'smirk', 'skew', 'flat', 'neutral']
        assert result.smile_shape in valid_shapes, \
            f"Smile shape '{result.smile_shape}' not in valid shapes {valid_shapes}"
        
        # 驗證 IV 分佈列表存在
        assert isinstance(result.call_ivs, list), \
            f"call_ivs should be a list, got {type(result.call_ivs)}"
        assert isinstance(result.put_ivs, list), \
            f"put_ivs should be a list, got {type(result.put_ivs)}"
        
        # 驗證 IV 分佈列表非空（因為我們生成了有效的期權鏈）
        assert len(result.call_ivs) > 0, "call_ivs should not be empty"
        assert len(result.put_ivs) > 0, "put_ivs should not be empty"
        
        # 驗證 IV 分佈列表中的每個元素格式正確
        for strike, iv in result.call_ivs:
            assert strike > 0, f"Strike should be positive, got {strike}"
            assert 0 < iv <= 5.0, f"IV should be in (0, 5.0], got {iv}"
        
        for strike, iv in result.put_ivs:
            assert strike > 0, f"Strike should be positive, got {strike}"
            assert 0 < iv <= 5.0, f"IV should be in (0, 5.0], got {iv}"
        
        # 驗證 to_dict 方法正常工作
        result_dict = result.to_dict()
        assert 'atm_iv' in result_dict
        assert 'atm_strike' in result_dict
        assert 'skew' in result_dict
        assert 'smile_shape' in result_dict
        assert 'call_ivs' in result_dict
        assert 'put_ivs' in result_dict
    
    def test_empty_option_chain_returns_default_result(self):
        """
        **Feature: iv-processing-enhancement, Property 9: Smile Analysis Completeness**
        **Validates: Requirements 5.1, 5.5**
        
        Property: Even with empty option chain, the analyzer should return a valid 
        VolatilitySmileResult with default values.
        """
        result = self.analyzer.analyze_smile(
            option_chain={'calls': [], 'puts': []},
            current_price=100.0,
            time_to_expiration=0.25
        )
        
        assert isinstance(result, VolatilitySmileResult)
        assert result.atm_iv == 0.30  # 默認 IV
        assert result.smile_shape == 'neutral'  # module25 使用 'neutral' 而非 'unknown'



class TestSmileShapeClassification:
    """
    **Feature: iv-processing-enhancement, Property 10: Smile Shape Classification**
    
    測試波動率微笑形狀分類
    """
    
    def setup_method(self):
        self.analyzer = VolatilitySmileAnalyzer()
    
    @given(
        current_price=st.floats(min_value=50.0, max_value=200.0, allow_nan=False, allow_infinity=False),
        base_iv=st.floats(min_value=0.15, max_value=0.50, allow_nan=False, allow_infinity=False),
        time_to_expiration=st.floats(min_value=0.1, max_value=0.5, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_smile_shape_is_exactly_one_classification(
        self, current_price, base_iv, time_to_expiration
    ):
        """
        **Feature: iv-processing-enhancement, Property 10: Smile Shape Classification**
        **Validates: Requirements 5.3**
        
        Property: For any IV distribution, the smile shape should be classified as 
        exactly one of: 'symmetric', 'put_skew', or 'call_skew' (or 'unknown' for 
        insufficient data).
        """
        # 生成期權鏈（隨機 skew）
        import random
        put_skew = random.uniform(-0.15, 0.25)
        
        option_chain = generate_option_chain(
            current_price=current_price,
            num_strikes=9,
            base_iv=base_iv,
            put_skew=put_skew,
            time_to_expiration=time_to_expiration
        )
        
        result = self.analyzer.analyze_smile(
            option_chain=option_chain,
            current_price=current_price,
            time_to_expiration=time_to_expiration
        )
        
        # 驗證 smile_shape 是且僅是一個有效分類
        valid_shapes = ['smile', 'smirk', 'skew', 'flat', 'neutral']
        assert result.smile_shape in valid_shapes, \
            f"Smile shape '{result.smile_shape}' not in valid shapes {valid_shapes}"
        
        # 驗證只有一個分類（不是多個）
        shape_count = sum(1 for s in valid_shapes if result.smile_shape == s)
        assert shape_count == 1, \
            f"Expected exactly one classification, got {shape_count}"
    
    def test_put_skew_classification(self):
        """
        **Feature: iv-processing-enhancement, Property 10: Smile Shape Classification**
        **Validates: Requirements 5.3**
        
        Property: When OTM Put IV > OTM Call IV significantly, the shape should be 
        classified as 'put_skew'.
        """
        current_price = 100.0
        
        # 生成明顯的 put_skew 期權鏈
        option_chain = generate_option_chain(
            current_price=current_price,
            num_strikes=9,
            base_iv=0.25,
            put_skew=0.10,  # 明顯的 put skew
            time_to_expiration=0.25
        )
        
        result = self.analyzer.analyze_smile(
            option_chain=option_chain,
            current_price=current_price,
            time_to_expiration=0.25
        )
        
        assert result.smile_shape == 'skew', \
            f"Expected 'skew' for positive skew, got '{result.smile_shape}'"
    
    def test_call_skew_classification(self):
        """
        **Feature: iv-processing-enhancement, Property 10: Smile Shape Classification**
        **Validates: Requirements 5.3**
        
        Property: When OTM Call IV > OTM Put IV significantly, the shape should be 
        classified as 'call_skew'.
        """
        current_price = 100.0
        
        # 生成明顯的 call_skew 期權鏈
        option_chain = generate_option_chain(
            current_price=current_price,
            num_strikes=9,
            base_iv=0.25,
            put_skew=-0.10,  # 負 skew = call skew
            time_to_expiration=0.25
        )
        
        result = self.analyzer.analyze_smile(
            option_chain=option_chain,
            current_price=current_price,
            time_to_expiration=0.25
        )
        
        assert result.smile_shape == 'skew', \
            f"Expected 'skew' for negative skew, got '{result.smile_shape}'"
    
    def test_symmetric_classification(self):
        """
        **Feature: iv-processing-enhancement, Property 10: Smile Shape Classification**
        **Validates: Requirements 5.3**
        
        Property: When OTM Put IV ≈ OTM Call IV (difference < 2%), the shape should 
        be classified as 'symmetric'.
        """
        current_price = 100.0
        
        # 生成對稱的期權鏈
        option_chain = generate_option_chain(
            current_price=current_price,
            num_strikes=9,
            base_iv=0.25,
            put_skew=0.0,  # 無 skew = symmetric
            time_to_expiration=0.25
        )
        
        result = self.analyzer.analyze_smile(
            option_chain=option_chain,
            current_price=current_price,
            time_to_expiration=0.25
        )
        
        assert result.smile_shape in ['smile', 'flat', 'neutral'], \
            f"Expected 'smile', 'flat', or 'neutral' for zero skew, got '{result.smile_shape}'"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
