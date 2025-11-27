#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Property-based tests for Risk-Reward Scoring Enhancement
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


class TestExpectedReturnFormula:
    """
    **Feature: iv-processing-enhancement, Property 5: Expected Return Formula**
    
    測試預期收益公式的正確性
    """
    
    def setup_method(self):
        self.calculator = OptimalStrikeCalculator()
    
    @given(
        delta=st.floats(min_value=0.1, max_value=0.9, allow_nan=False, allow_infinity=False),
        max_loss=st.floats(min_value=1.0, max_value=100.0, allow_nan=False, allow_infinity=False),
        potential_profit=st.floats(min_value=0.0, max_value=500.0, allow_nan=False, allow_infinity=False),
        current_price=st.floats(min_value=50.0, max_value=500.0, allow_nan=False, allow_infinity=False),
        strategy_type=st.sampled_from(['long_call', 'long_put', 'short_call', 'short_put'])
    )
    @settings(max_examples=100)
    def test_expected_return_formula(self, delta, max_loss, potential_profit, current_price, strategy_type):
        """
        **Feature: iv-processing-enhancement, Property 5: Expected Return Formula**
        **Validates: Requirements 3.1, 3.3**
        
        Property: For any strike analysis with valid Delta, max_loss, and potential_profit,
        the expected return should equal: potential_profit × Delta - max_loss × (1 - Delta).
        """
        # 創建一個 StrikeAnalysis 對象
        strike = current_price
        analysis = StrikeAnalysis(
            strike=strike,
            option_type='call' if strategy_type in ['long_call', 'short_call'] else 'put',
            delta=delta,
            theta=-0.05,  # 典型的 Theta 值
            last_price=max_loss if strategy_type in ['long_call', 'long_put'] else potential_profit
        )
        
        # 設置目標價格以產生預期的 potential_profit
        if strategy_type == 'long_call':
            target_price = strike + max_loss + potential_profit
        elif strategy_type == 'long_put':
            target_price = strike - max_loss - potential_profit
        elif strategy_type == 'short_call':
            target_price = strike  # Short call 的 potential_profit 就是權金
        else:  # short_put
            target_price = strike  # Short put 的 potential_profit 就是權金
        
        # 調用 v2 方法
        self.calculator._calculate_risk_reward_score_v2(
            analysis=analysis,
            current_price=current_price,
            strategy_type=strategy_type,
            target_price=target_price,
            holding_days=30
        )
        
        # 驗證勝率被正確設置（基於 Delta）
        assert 0.0 <= analysis.win_probability <= 1.0, \
            f"Win probability {analysis.win_probability} outside valid range [0, 1]"
        
        # 驗證預期收益公式
        # expected_return = potential_profit × win_probability - max_loss × (1 - win_probability)
        win_prob = analysis.win_probability
        actual_max_loss = analysis.max_loss
        actual_potential_profit = analysis.potential_profit
        
        # 對於 Short Call，max_loss 是無限的，使用估計值
        if actual_max_loss == float('inf'):
            actual_max_loss = current_price * 2
        
        expected_return_calculated = (
            actual_potential_profit * win_prob - 
            actual_max_loss * (1 - win_prob)
        )
        
        # 驗證計算的預期收益與公式一致
        assert abs(analysis.expected_return - expected_return_calculated) < 0.01, \
            f"Expected return {analysis.expected_return} differs from formula result {expected_return_calculated}"


class TestThetaAdjustment:
    """
    **Feature: iv-processing-enhancement, Property 6: Theta Adjustment for Long Strategies**
    
    測試 Long 策略的 Theta 調整
    """
    
    def setup_method(self):
        self.calculator = OptimalStrikeCalculator()
    
    @given(
        delta=st.floats(min_value=0.3, max_value=0.7, allow_nan=False, allow_infinity=False),
        theta=st.floats(min_value=-0.5, max_value=-0.01, allow_nan=False, allow_infinity=False),
        current_price=st.floats(min_value=50.0, max_value=300.0, allow_nan=False, allow_infinity=False),
        premium=st.floats(min_value=1.0, max_value=20.0, allow_nan=False, allow_infinity=False),
        holding_days=st.integers(min_value=1, max_value=90),
        strategy_type=st.sampled_from(['long_call', 'long_put'])
    )
    @settings(max_examples=100)
    def test_theta_adjustment_for_long_strategies(self, delta, theta, current_price, premium, holding_days, strategy_type):
        """
        **Feature: iv-processing-enhancement, Property 6: Theta Adjustment for Long Strategies**
        **Validates: Requirements 3.2, 3.6**
        
        Property: For any Long strategy (long_call or long_put), the theta-adjusted return 
        should be less than or equal to the unadjusted expected return (since Theta is 
        negative for Long positions).
        """
        strike = current_price
        analysis = StrikeAnalysis(
            strike=strike,
            option_type='call' if strategy_type == 'long_call' else 'put',
            delta=delta,
            theta=theta,  # Theta 是負的
            last_price=premium
        )
        
        # 設置目標價格
        if strategy_type == 'long_call':
            target_price = current_price * 1.15
        else:
            target_price = current_price * 0.85
        
        # 調用 v2 方法
        self.calculator._calculate_risk_reward_score_v2(
            analysis=analysis,
            current_price=current_price,
            strategy_type=strategy_type,
            target_price=target_price,
            holding_days=holding_days
        )
        
        # 對於 Long 策略，theta_adjusted_return 應該 <= expected_return
        # 因為 Theta 損失會被扣除
        assert analysis.theta_adjusted_return <= analysis.expected_return + 0.001, \
            f"Theta adjusted return {analysis.theta_adjusted_return} should be <= " \
            f"expected return {analysis.expected_return} for Long strategy"
        
        # 驗證 Theta 損失計算
        expected_theta_loss = abs(theta) * holding_days
        actual_theta_loss = analysis.expected_return - analysis.theta_adjusted_return
        
        assert abs(actual_theta_loss - expected_theta_loss) < 0.01, \
            f"Theta loss {actual_theta_loss} differs from expected {expected_theta_loss}"
    
    @given(
        delta=st.floats(min_value=0.1, max_value=0.3, allow_nan=False, allow_infinity=False),
        theta=st.floats(min_value=-0.5, max_value=-0.01, allow_nan=False, allow_infinity=False),
        current_price=st.floats(min_value=50.0, max_value=300.0, allow_nan=False, allow_infinity=False),
        premium=st.floats(min_value=1.0, max_value=20.0, allow_nan=False, allow_infinity=False),
        holding_days=st.integers(min_value=1, max_value=90),
        strategy_type=st.sampled_from(['short_call', 'short_put'])
    )
    @settings(max_examples=100)
    def test_no_theta_deduction_for_short_strategies(self, delta, theta, current_price, premium, holding_days, strategy_type):
        """
        **Feature: iv-processing-enhancement, Property 6: Theta Adjustment for Long Strategies**
        **Validates: Requirements 3.6**
        
        Property: For Short strategies, Theta should NOT be deducted from expected return
        (since Theta benefits Short strategies).
        """
        strike = current_price
        analysis = StrikeAnalysis(
            strike=strike,
            option_type='call' if strategy_type == 'short_call' else 'put',
            delta=delta,
            theta=theta,
            last_price=premium
        )
        
        # 設置目標價格
        target_price = current_price
        
        # 調用 v2 方法
        self.calculator._calculate_risk_reward_score_v2(
            analysis=analysis,
            current_price=current_price,
            strategy_type=strategy_type,
            target_price=target_price,
            holding_days=holding_days
        )
        
        # 對於 Short 策略，theta_adjusted_return 應該等於 expected_return
        # 因為 Theta 對 Short 有利，不扣除
        assert abs(analysis.theta_adjusted_return - analysis.expected_return) < 0.001, \
            f"For Short strategy, theta_adjusted_return {analysis.theta_adjusted_return} " \
            f"should equal expected_return {analysis.expected_return}"


class TestScoreAssignment:
    """
    **Feature: iv-processing-enhancement, Property 7: Score Assignment Consistency**
    
    測試評分分配的一致性
    """
    
    def setup_method(self):
        self.calculator = OptimalStrikeCalculator()
    
    @given(
        delta=st.floats(min_value=0.3, max_value=0.7, allow_nan=False, allow_infinity=False),
        theta=st.floats(min_value=-0.1, max_value=-0.01, allow_nan=False, allow_infinity=False),
        current_price=st.floats(min_value=50.0, max_value=300.0, allow_nan=False, allow_infinity=False),
        premium=st.floats(min_value=1.0, max_value=10.0, allow_nan=False, allow_infinity=False),
        profit_multiplier=st.floats(min_value=0.5, max_value=5.0, allow_nan=False, allow_infinity=False),
        strategy_type=st.sampled_from(['long_call', 'long_put'])
    )
    @settings(max_examples=100)
    def test_score_range_for_positive_return(self, delta, theta, current_price, premium, profit_multiplier, strategy_type):
        """
        **Feature: iv-processing-enhancement, Property 7: Score Assignment Consistency**
        **Validates: Requirements 3.4, 3.5**
        
        Property: For any adjusted expected return, if positive the score should be 
        in range [40, 100] based on return rate.
        """
        strike = current_price
        analysis = StrikeAnalysis(
            strike=strike,
            option_type='call' if strategy_type == 'long_call' else 'put',
            delta=delta,
            theta=theta,
            last_price=premium
        )
        
        # 設置目標價格以產生正的預期收益
        if strategy_type == 'long_call':
            target_price = current_price * (1 + 0.1 * profit_multiplier)
        else:
            target_price = current_price * (1 - 0.1 * profit_multiplier)
        
        # 調用 v2 方法
        score = self.calculator._calculate_risk_reward_score_v2(
            analysis=analysis,
            current_price=current_price,
            strategy_type=strategy_type,
            target_price=target_price,
            holding_days=10  # 較短的持有期以減少 Theta 損失
        )
        
        # 如果調整後預期收益為正，評分應該在 [40, 100]
        if analysis.theta_adjusted_return > 0:
            assert 40.0 <= score <= 100.0, \
                f"Score {score} outside range [40, 100] for positive adjusted return {analysis.theta_adjusted_return}"
        else:
            # 如果調整後預期收益為負或零，評分應該是 20.0
            assert score == 20.0, \
                f"Score {score} should be 20.0 for non-positive adjusted return {analysis.theta_adjusted_return}"
    
    @given(
        delta=st.floats(min_value=0.05, max_value=0.15, allow_nan=False, allow_infinity=False),
        theta=st.floats(min_value=-0.5, max_value=-0.1, allow_nan=False, allow_infinity=False),
        current_price=st.floats(min_value=50.0, max_value=300.0, allow_nan=False, allow_infinity=False),
        premium=st.floats(min_value=0.5, max_value=3.0, allow_nan=False, allow_infinity=False),
        strategy_type=st.sampled_from(['long_call', 'long_put'])
    )
    @settings(max_examples=100)
    def test_score_for_negative_return(self, delta, theta, current_price, premium, strategy_type):
        """
        **Feature: iv-processing-enhancement, Property 7: Score Assignment Consistency**
        **Validates: Requirements 3.5**
        
        Property: If adjusted expected return is negative, the score should be exactly 20.0.
        """
        strike = current_price
        analysis = StrikeAnalysis(
            strike=strike,
            option_type='call' if strategy_type == 'long_call' else 'put',
            delta=delta,  # 低 Delta = 低勝率
            theta=theta,  # 高 Theta 損失
            last_price=premium
        )
        
        # 設置目標價格接近當前價格（低收益潛力）
        target_price = current_price * 1.01 if strategy_type == 'long_call' else current_price * 0.99
        
        # 調用 v2 方法，使用較長的持有期以增加 Theta 損失
        score = self.calculator._calculate_risk_reward_score_v2(
            analysis=analysis,
            current_price=current_price,
            strategy_type=strategy_type,
            target_price=target_price,
            holding_days=60  # 較長的持有期
        )
        
        # 如果調整後預期收益為負，評分應該是 20.0
        if analysis.theta_adjusted_return <= 0:
            assert score == 20.0, \
                f"Score {score} should be exactly 20.0 for negative adjusted return {analysis.theta_adjusted_return}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
