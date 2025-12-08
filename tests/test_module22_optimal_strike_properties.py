#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Property-based tests for Module 22 Optimal Strike Calculator
使用 Hypothesis 進行屬性測試
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
import sys
import os

# 添加項目根目錄到路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from calculation_layer.module22_optimal_strike import OptimalStrikeCalculator, StrikeAnalysis


def generate_option_chain(current_price: float, num_strikes: int = 10):
    """生成模擬期權鏈數據"""
    calls = []
    puts = []
    
    # 生成 ATM ± 範圍內的行使價
    strike_step = current_price * 0.025  # 2.5% 間隔
    
    for i in range(-num_strikes // 2, num_strikes // 2 + 1):
        strike = round(current_price + i * strike_step, 2)
        
        # 計算模擬的期權數據
        moneyness = (strike - current_price) / current_price
        
        call_data = {
            'strike': strike,
            'bid': max(0.1, current_price * 0.05 - moneyness * current_price * 0.5),
            'ask': max(0.2, current_price * 0.06 - moneyness * current_price * 0.5),
            'lastPrice': max(0.15, current_price * 0.055 - moneyness * current_price * 0.5),
            'volume': 100 + abs(i) * 50,
            'openInterest': 500 + abs(i) * 100,
            'impliedVolatility': 0.25 + abs(moneyness) * 0.1,
            'delta': max(0.05, min(0.95, 0.5 - moneyness * 2)),
            'gamma': 0.05,
            'theta': -0.05,
            'vega': 0.1
        }
        
        put_data = {
            'strike': strike,
            'bid': max(0.1, current_price * 0.05 + moneyness * current_price * 0.5),
            'ask': max(0.2, current_price * 0.06 + moneyness * current_price * 0.5),
            'lastPrice': max(0.15, current_price * 0.055 + moneyness * current_price * 0.5),
            'volume': 100 + abs(i) * 50,
            'openInterest': 500 + abs(i) * 100,
            'impliedVolatility': 0.25 + abs(moneyness) * 0.1,
            'delta': -max(0.05, min(0.95, 0.5 + moneyness * 2)),
            'gamma': 0.05,
            'theta': -0.05,
            'vega': 0.1
        }
        
        calls.append(call_data)
        puts.append(put_data)
    
    return {'calls': calls, 'puts': puts}


class TestStrikeRangeFiltering:
    """
    **Feature: jin-cao-option-enhancements, Property 3: Strike Range Filtering**
    
    測試行使價範圍過濾的正確性
    """
    
    def setup_method(self):
        self.calculator = OptimalStrikeCalculator()
    
    @given(
        current_price=st.floats(min_value=10.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
        strategy_type=st.sampled_from(['long_call', 'long_put', 'short_call', 'short_put'])
    )
    @settings(max_examples=100, deadline=None)
    def test_strikes_within_range(self, current_price, strategy_type):
        """
        **Feature: jin-cao-option-enhancements, Property 3: Strike Range Filtering**
        **Validates: Requirements 12.1**
        
        Property: All analyzed strikes should be within ATM ± 15% range.
        """
        option_chain = generate_option_chain(current_price)
        result = self.calculator.analyze_strikes(
            current_price=current_price,
            option_chain=option_chain,
            strategy_type=strategy_type
        )
        
        min_strike = current_price * 0.85
        max_strike = current_price * 1.15
        
        for strike_data in result['analyzed_strikes']:
            strike = strike_data['strike']
            assert min_strike <= strike <= max_strike, \
                f"Strike {strike} outside range [{min_strike:.2f}, {max_strike:.2f}]"
    
    @given(
        current_price=st.floats(min_value=50.0, max_value=500.0, allow_nan=False, allow_infinity=False),
        strategy_type=st.sampled_from(['long_call', 'long_put', 'short_call', 'short_put'])
    )
    @settings(max_examples=100, deadline=None)
    def test_liquidity_filtering(self, current_price, strategy_type):
        """
        **Feature: jin-cao-option-enhancements, Property 3: Strike Range Filtering**
        **Validates: Requirements 12.1**
        
        Property: All analyzed strikes should have Volume > 10 and OI > 100.
        """
        option_chain = generate_option_chain(current_price)
        result = self.calculator.analyze_strikes(
            current_price=current_price,
            option_chain=option_chain,
            strategy_type=strategy_type
        )
        
        for strike_data in result['analyzed_strikes']:
            assert strike_data['volume'] >= 10, \
                f"Volume {strike_data['volume']} < 10 for strike {strike_data['strike']}"
            assert strike_data['open_interest'] >= 100, \
                f"OI {strike_data['open_interest']} < 100 for strike {strike_data['strike']}"


class TestCompositeScoreCalculation:
    """
    **Feature: jin-cao-option-enhancements, Property 2: Composite Score Weight Sum**
    
    測試綜合評分計算的正確性
    """
    
    def setup_method(self):
        self.calculator = OptimalStrikeCalculator()
    
    @given(
        liquidity_score=st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False),
        greeks_score=st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False),
        iv_score=st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False),
        risk_reward_score=st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False),
        strategy_type=st.sampled_from(['long_call', 'long_put', 'short_call', 'short_put'])
    )
    @settings(max_examples=100)
    def test_composite_score_weights(self, liquidity_score, greeks_score, iv_score, risk_reward_score, strategy_type):
        """
        **Feature: jin-cao-option-enhancements, Property 2: Composite Score Weight Sum**
        **Validates: Requirements 12.2**
        
        Property: Composite score should equal weighted sum of component scores.
        """
        analysis = StrikeAnalysis(
            strike=100.0,
            option_type='call',
            liquidity_score=liquidity_score,
            greeks_score=greeks_score,
            iv_score=iv_score,
            risk_reward_score=risk_reward_score
        )
        
        composite = self.calculator.calculate_composite_score(analysis, strategy_type)
        
        expected = (
            liquidity_score * 0.30 +
            greeks_score * 0.30 +
            iv_score * 0.20 +
            risk_reward_score * 0.20
        )
        expected = min(100.0, max(0.0, expected))
        
        assert abs(composite - expected) < 0.01, \
            f"Composite {composite} != expected {expected}"


class TestComponentScoreBounds:
    """
    **Feature: jin-cao-option-enhancements, Property 10: Component Score Bounds**
    
    測試所有評分組件的邊界
    """
    
    def setup_method(self):
        self.calculator = OptimalStrikeCalculator()
    
    @given(
        current_price=st.floats(min_value=50.0, max_value=500.0, allow_nan=False, allow_infinity=False),
        strategy_type=st.sampled_from(['long_call', 'long_put', 'short_call', 'short_put'])
    )
    @settings(max_examples=100, deadline=None)
    def test_all_scores_within_bounds(self, current_price, strategy_type):
        """
        **Feature: jin-cao-option-enhancements, Property 10: Component Score Bounds**
        **Validates: Requirements 12.2, 12.3, 12.4, 12.5, 12.6**
        
        Property: All component scores and composite score should be between 0 and 100.
        """
        option_chain = generate_option_chain(current_price)
        result = self.calculator.analyze_strikes(
            current_price=current_price,
            option_chain=option_chain,
            strategy_type=strategy_type
        )
        
        for strike_data in result['analyzed_strikes']:
            assert 0 <= strike_data['liquidity_score'] <= 100, \
                f"Liquidity score {strike_data['liquidity_score']} out of bounds"
            assert 0 <= strike_data['greeks_score'] <= 100, \
                f"Greeks score {strike_data['greeks_score']} out of bounds"
            assert 0 <= strike_data['iv_score'] <= 100, \
                f"IV score {strike_data['iv_score']} out of bounds"
            assert 0 <= strike_data['risk_reward_score'] <= 100, \
                f"Risk-reward score {strike_data['risk_reward_score']} out of bounds"
            assert 0 <= strike_data['composite_score'] <= 100, \
                f"Composite score {strike_data['composite_score']} out of bounds"


class TestTopRecommendationsRanking:
    """
    **Feature: jin-cao-option-enhancements, Property 9: Top Recommendations Ranking**
    
    測試推薦排名的正確性
    """
    
    def setup_method(self):
        self.calculator = OptimalStrikeCalculator()
    
    @given(
        current_price=st.floats(min_value=50.0, max_value=500.0, allow_nan=False, allow_infinity=False),
        strategy_type=st.sampled_from(['long_call', 'long_put', 'short_call', 'short_put'])
    )
    @settings(max_examples=100, deadline=None)
    def test_top_3_sorted_descending(self, current_price, strategy_type):
        """
        **Feature: jin-cao-option-enhancements, Property 9: Top Recommendations Ranking**
        **Validates: Requirements 12.7**
        
        Property: Top 3 recommendations should be sorted by composite score descending.
        """
        option_chain = generate_option_chain(current_price)
        result = self.calculator.analyze_strikes(
            current_price=current_price,
            option_chain=option_chain,
            strategy_type=strategy_type
        )
        
        top_recs = result['top_recommendations']
        
        if len(top_recs) >= 2:
            for i in range(len(top_recs) - 1):
                assert top_recs[i]['composite_score'] >= top_recs[i + 1]['composite_score'], \
                    f"Recommendations not sorted: {top_recs[i]['composite_score']} < {top_recs[i + 1]['composite_score']}"
    
    @given(
        current_price=st.floats(min_value=50.0, max_value=500.0, allow_nan=False, allow_infinity=False),
        strategy_type=st.sampled_from(['long_call', 'long_put', 'short_call', 'short_put'])
    )
    @settings(max_examples=100, deadline=None)
    def test_best_strike_is_top_recommendation(self, current_price, strategy_type):
        """
        **Feature: jin-cao-option-enhancements, Property 9: Top Recommendations Ranking**
        **Validates: Requirements 12.7**
        
        Property: Best strike should match the first recommendation.
        """
        option_chain = generate_option_chain(current_price)
        result = self.calculator.analyze_strikes(
            current_price=current_price,
            option_chain=option_chain,
            strategy_type=strategy_type
        )
        
        if result['top_recommendations']:
            # Use approximate comparison for floating point values
            assert abs(result['best_strike'] - result['top_recommendations'][0]['strike']) < 0.01, \
                f"Best strike {result['best_strike']} != top recommendation {result['top_recommendations'][0]['strike']}"


def generate_short_put_option_chain(current_price: float, num_strikes: int = 20):
    """
    生成包含各種 Short Put 場景的期權鏈數據
    
    包括:
    - ITM Put（行使價 >= 當前股價）
    - 高 Delta Put（|Delta| > 0.35）
    - 距離過近的 Put（距離 < 3%）
    - 安全的 OTM Put（應該通過過濾）
    """
    calls = []
    puts = []
    
    # 生成更寬範圍的行使價（ATM ± 25%）
    strike_step = current_price * 0.02  # 2% 間隔
    
    for i in range(-12, 13):  # -24% 到 +24%
        strike = round(current_price + i * strike_step, 2)
        
        # 計算 moneyness
        moneyness = (strike - current_price) / current_price
        
        # 計算 Put Delta（負值，ITM 時絕對值更大）
        # 對於 Put: ITM (strike > price) -> Delta 接近 -1
        #          ATM (strike ≈ price) -> Delta 接近 -0.5
        #          OTM (strike < price) -> Delta 接近 0
        if strike >= current_price:
            # ITM Put: Delta 接近 -1
            put_delta = -min(0.95, 0.5 + moneyness * 2)
        else:
            # OTM Put: Delta 接近 0
            distance_pct = (current_price - strike) / current_price
            # 距離越遠，Delta 絕對值越小
            put_delta = -max(0.05, 0.5 - distance_pct * 3)
        
        call_data = {
            'strike': strike,
            'bid': max(0.1, current_price * 0.05 - moneyness * current_price * 0.5),
            'ask': max(0.2, current_price * 0.06 - moneyness * current_price * 0.5),
            'lastPrice': max(0.15, current_price * 0.055 - moneyness * current_price * 0.5),
            'volume': 100 + abs(i) * 50,
            'openInterest': 500 + abs(i) * 100,
            'impliedVolatility': 0.25 + abs(moneyness) * 0.1,
            'delta': max(0.05, min(0.95, 0.5 - moneyness * 2)),
            'gamma': 0.05,
            'theta': -0.05,
            'vega': 0.1
        }
        
        put_data = {
            'strike': strike,
            'bid': max(0.1, current_price * 0.05 + moneyness * current_price * 0.5),
            'ask': max(0.2, current_price * 0.06 + moneyness * current_price * 0.5),
            'lastPrice': max(0.15, current_price * 0.055 + moneyness * current_price * 0.5),
            'volume': 100 + abs(i) * 50,
            'openInterest': 500 + abs(i) * 100,
            'impliedVolatility': 0.25 + abs(moneyness) * 0.1,
            'delta': put_delta,
            'gamma': 0.05,
            'theta': -0.05,
            'vega': 0.1
        }
        
        calls.append(call_data)
        puts.append(put_data)
    
    return {'calls': calls, 'puts': puts}


class TestShortPutFiltering:
    """
    **Feature: option-calculation-fixes, Property 2: Short Put 過濾完整性**
    
    測試 Short Put 策略的安全過濾功能
    
    Requirements: 2.1, 2.2, 2.3
    """
    
    def setup_method(self):
        self.calculator = OptimalStrikeCalculator()
    
    @given(
        current_price=st.floats(min_value=50.0, max_value=500.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100, deadline=None)
    def test_short_put_filter_completeness(self, current_price):
        """
        **Feature: option-calculation-fixes, Property 2: Short Put 過濾完整性**
        **Validates: Requirements 2.1, 2.2, 2.3**
        
        Property: For any Short Put strategy analysis result, all recommended strikes should satisfy:
        1. Strike < Current Price (OTM only)
        2. |Delta| <= 0.35
        3. (Current Price - Strike) / Current Price >= 0.03 (at least 3% distance)
        """
        option_chain = generate_short_put_option_chain(current_price)
        result = self.calculator.analyze_strikes(
            current_price=current_price,
            option_chain=option_chain,
            strategy_type='short_put'
        )
        
        for strike_data in result['analyzed_strikes']:
            strike = strike_data['strike']
            delta = strike_data['delta']
            
            # Requirement 2.1: 過濾 ITM Put（行使價 >= 當前股價）
            assert strike < current_price, \
                f"ITM Put not filtered: strike ${strike:.2f} >= current price ${current_price:.2f}"
            
            # Requirement 2.2: 過濾高 Delta Put（|Delta| > 0.35）
            assert abs(delta) <= 0.35, \
                f"High Delta Put not filtered: |Delta|={abs(delta):.4f} > 0.35 for strike ${strike:.2f}"
            
            # Requirement 2.3: 確保距離 >= 3%
            distance_pct = (current_price - strike) / current_price
            assert distance_pct >= 0.03, \
                f"Too close Put not filtered: distance {distance_pct*100:.1f}% < 3% for strike ${strike:.2f}"
    
    @given(
        current_price=st.floats(min_value=50.0, max_value=500.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100, deadline=None)
    def test_short_put_safety_probability(self, current_price):
        """
        **Feature: option-calculation-fixes, Property 2: Short Put 過濾完整性**
        **Validates: Requirements 2.5**
        
        Property: For any Short Put recommendation, safety_probability should equal (1 - |Delta|).
        """
        option_chain = generate_short_put_option_chain(current_price)
        result = self.calculator.analyze_strikes(
            current_price=current_price,
            option_chain=option_chain,
            strategy_type='short_put'
        )
        
        for strike_data in result['analyzed_strikes']:
            delta = strike_data['delta']
            safety_prob = strike_data['safety_probability']
            expected_safety = 1.0 - abs(delta)
            
            assert abs(safety_prob - expected_safety) < 0.0001, \
                f"Safety probability {safety_prob:.4f} != expected {expected_safety:.4f} (1 - |{delta:.4f}|)"
    
    @given(
        current_price=st.floats(min_value=50.0, max_value=500.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100, deadline=None)
    def test_short_put_vs_other_strategies(self, current_price):
        """
        **Feature: option-calculation-fixes, Property 2: Short Put 過濾完整性**
        **Validates: Requirements 2.1, 2.2, 2.3**
        
        Property: Short Put filtering should be more restrictive than other strategies.
        The number of analyzed strikes for short_put should be <= other put strategies.
        """
        option_chain = generate_short_put_option_chain(current_price)
        
        # Analyze with short_put strategy
        short_put_result = self.calculator.analyze_strikes(
            current_price=current_price,
            option_chain=option_chain,
            strategy_type='short_put'
        )
        
        # Analyze with long_put strategy (no special filtering)
        long_put_result = self.calculator.analyze_strikes(
            current_price=current_price,
            option_chain=option_chain,
            strategy_type='long_put'
        )
        
        # Short Put should have fewer or equal analyzed strikes due to filtering
        assert len(short_put_result['analyzed_strikes']) <= len(long_put_result['analyzed_strikes']), \
            f"Short Put ({len(short_put_result['analyzed_strikes'])}) has more strikes than Long Put ({len(long_put_result['analyzed_strikes'])})"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
