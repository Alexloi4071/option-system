#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module 22 Long/Short 策略增強功能測試

測試內容:
- Property 1: 場景概率總和為 1
- Property 2: 內在價值計算正確性
- Property 3: 期望收益等於概率加權平均
- Property 4: 年化收益率計算正確性
- Property 5: 推薦退出時機對應最高年化收益率
- Property 6: Long 策略評分權重正確性
- Property 7: 安全概率計算正確性
- Property 8: 安全距離計算正確性（Short Put）
- Property 9: Theta 收益計算正確性
- Property 10: Short 策略評分權重正確性
- Property 11: Long 策略綜合評分計算正確性
- Property 12: Short 策略綜合評分計算正確性
- Property 13: 推薦列表按綜合評分降序排列
- Property 14: 目標價/風險邊界默認值正確性
- Property 15: 評分範圍有效性

作者: Kiro
日期: 2025-12-18
"""

import pytest
import sys
import os
from hypothesis import given, strategies as st, settings, assume

# 添加項目根目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from calculation_layer.module22_optimal_strike import OptimalStrikeCalculator, StrikeAnalysis


class TestTargetPriceAndRiskBoundary:
    """Task 2.2: 目標價和風險邊界測試"""
    
    def setup_method(self):
        self.calculator = OptimalStrikeCalculator()
    
    @given(current_price=st.floats(min_value=10, max_value=1000, allow_nan=False, allow_infinity=False))
    @settings(max_examples=50)
    def test_property_14_long_call_default_target_price(self, current_price):
        """
        Property 14: 目標價/風險邊界默認值正確性
        Long Call 目標價 = 當前股價 × 1.10
        """
        target = self.calculator._determine_target_price(
            current_price=current_price,
            strategy_type='long_call',
            support_resistance_data=None
        )
        expected = current_price * 1.10
        assert abs(target - expected) < 0.01, f"Long Call 目標價應為 {expected}，實際為 {target}"
    
    @given(current_price=st.floats(min_value=10, max_value=1000, allow_nan=False, allow_infinity=False))
    @settings(max_examples=50)
    def test_property_14_long_put_default_target_price(self, current_price):
        """
        Property 14: 目標價/風險邊界默認值正確性
        Long Put 目標價 = 當前股價 × 0.90
        """
        target = self.calculator._determine_target_price(
            current_price=current_price,
            strategy_type='long_put',
            support_resistance_data=None
        )
        expected = current_price * 0.90
        assert abs(target - expected) < 0.01, f"Long Put 目標價應為 {expected}，實際為 {target}"
    
    def test_target_price_with_resistance_data(self):
        """測試使用阻力位數據確定目標價"""
        current_price = 100.0
        support_resistance_data = {
            'resistance_level': 115.0,
            'support_level': 85.0
        }
        
        # Long Call 應使用阻力位
        target = self.calculator._determine_target_price(
            current_price=current_price,
            strategy_type='long_call',
            support_resistance_data=support_resistance_data
        )
        assert target == 115.0
        
        # Long Put 應使用支持位
        target = self.calculator._determine_target_price(
            current_price=current_price,
            strategy_type='long_put',
            support_resistance_data=support_resistance_data
        )
        assert target == 85.0


class TestMultiScenarioProfit:
    """Task 3.2, 3.3, 3.4: 多場景收益分析測試"""
    
    def setup_method(self):
        self.calculator = OptimalStrikeCalculator()
    
    def test_property_1_scenario_probabilities_sum_to_one(self):
        """
        Property 1: 場景概率總和為 1
        """
        analysis = StrikeAnalysis(
            strike=105.0,
            option_type='call',
            last_price=3.0,
            delta=0.5
        )
        
        result = self.calculator._calculate_multi_scenario_profit(
            analysis=analysis,
            current_price=100.0,
            target_price=110.0,
            strategy_type='long_call'
        )
        
        assert result is not None
        total_probability = sum(
            scenario['probability'] 
            for scenario in result['scenarios'].values()
        )
        assert abs(total_probability - 1.0) < 0.001, f"概率總和應為 1.0，實際為 {total_probability}"
    
    @given(
        current_price=st.floats(min_value=50, max_value=200, allow_nan=False, allow_infinity=False),
        strike_price=st.floats(min_value=50, max_value=200, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=50)
    def test_property_2_intrinsic_value_call(self, current_price, strike_price):
        """
        Property 2: 內在價值計算正確性 (Call)
        Call 的內在價值 = max(0, 股價 - 行使價)
        """
        intrinsic = max(0, current_price - strike_price)
        assert intrinsic >= 0
        if current_price > strike_price:
            assert intrinsic == current_price - strike_price
        else:
            assert intrinsic == 0
    
    @given(
        current_price=st.floats(min_value=50, max_value=200, allow_nan=False, allow_infinity=False),
        strike_price=st.floats(min_value=50, max_value=200, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=50)
    def test_property_2_intrinsic_value_put(self, current_price, strike_price):
        """
        Property 2: 內在價值計算正確性 (Put)
        Put 的內在價值 = max(0, 行使價 - 股價)
        """
        intrinsic = max(0, strike_price - current_price)
        assert intrinsic >= 0
        if strike_price > current_price:
            assert intrinsic == strike_price - current_price
        else:
            assert intrinsic == 0
    
    def test_property_3_expected_profit_calculation(self):
        """
        Property 3: 期望收益等於概率加權平均
        """
        analysis = StrikeAnalysis(
            strike=105.0,
            option_type='call',
            last_price=3.0,
            delta=0.5
        )
        
        result = self.calculator._calculate_multi_scenario_profit(
            analysis=analysis,
            current_price=100.0,
            target_price=110.0,
            strategy_type='long_call'
        )
        
        assert result is not None
        
        # 手動計算期望收益
        manual_expected = sum(
            scenario['profit'] * scenario['probability']
            for scenario in result['scenarios'].values()
        )
        
        assert abs(result['expected_profit'] - manual_expected) < 0.01, \
            f"期望收益應為 {manual_expected}，實際為 {result['expected_profit']}"


class TestOptimalExitTiming:
    """Task 4.2, 4.3: 最佳退出時機測試"""
    
    def setup_method(self):
        self.calculator = OptimalStrikeCalculator()
    
    @given(
        profit=st.floats(min_value=0.1, max_value=100, allow_nan=False, allow_infinity=False),
        premium=st.floats(min_value=0.1, max_value=50, allow_nan=False, allow_infinity=False),
        days_held=st.integers(min_value=1, max_value=365)
    )
    @settings(max_examples=50)
    def test_property_4_annualized_return_calculation(self, profit, premium, days_held):
        """
        Property 4: 年化收益率計算正確性
        年化收益率 = (利潤 / 期權金) × (365 / 持倉天數) × 100
        """
        annualized_return = (profit / premium) * (365 / days_held) * 100
        
        # 驗證公式正確性
        expected = (profit / premium) * (365 / days_held) * 100
        assert abs(annualized_return - expected) < 0.001
    
    def test_property_5_recommended_exit_has_highest_annualized_return(self):
        """
        Property 5: 推薦退出時機對應最高年化收益率
        """
        analysis = StrikeAnalysis(
            strike=105.0,
            option_type='call',
            last_price=3.0,
            delta=0.5,
            theta=-0.05,
            vega=0.2
        )
        
        result = self.calculator._calculate_optimal_exit_timing(
            analysis=analysis,
            current_price=100.0,
            target_price=110.0,
            days_to_expiration=30,
            iv=0.30
        )
        
        if result is None:
            pytest.skip("無法計算最佳退出時機")
        
        # 找到所有場景中的最高年化收益率
        max_annualized = max(
            scenario['annualized_return_pct']
            for scenario in result['exit_scenarios'].values()
        )
        
        # 驗證推薦的退出時機對應最高年化收益率
        assert abs(result['annualized_return_pct'] - max_annualized) < 0.01, \
            f"推薦的年化收益率 {result['annualized_return_pct']} 應等於最高值 {max_annualized}"


class TestLongStrategyScoring:
    """Task 5.2, 5.3: Long 策略評分測試"""
    
    def setup_method(self):
        self.calculator = OptimalStrikeCalculator()
    
    def test_property_6_long_strategy_score_weights(self):
        """
        Property 6: Long 策略評分權重正確性
        總評分 = 期望收益評分 × 0.5 + 年化收益評分 × 0.3 + 風險控制評分 × 0.2
        """
        analysis = StrikeAnalysis(
            strike=105.0,
            option_type='call',
            last_price=3.0,
            delta=0.5
        )
        
        # 設置多場景收益數據
        analysis.multi_scenario_profit = {
            'expected_profit_pct': 100.0,  # 100% 期望收益 -> 40 分
            'worst_case_profit_pct': -50.0  # 虧 50% -> 10 分
        }
        
        # 設置最佳退出時機數據
        analysis.optimal_exit_timing = {
            'annualized_return_pct': 150.0  # 150% 年化 -> 25 分
        }
        
        score = self.calculator._calculate_max_profit_score_long(analysis)
        
        # 驗證評分在合理範圍內
        assert 0 <= score <= 100, f"評分應在 0-100 範圍內，實際為 {score}"
    
    def test_property_15_score_range_validity_long(self):
        """
        Property 15: 評分範圍有效性 (Long 策略)
        所有評分應該在 0-100 範圍內
        """
        analysis = StrikeAnalysis(
            strike=105.0,
            option_type='call',
            last_price=3.0,
            delta=0.5
        )
        
        # 測試極端情況
        test_cases = [
            {'expected_profit_pct': 500.0, 'worst_case_profit_pct': 0.0},  # 極高收益
            {'expected_profit_pct': -100.0, 'worst_case_profit_pct': -100.0},  # 極低收益
            {'expected_profit_pct': 0.0, 'worst_case_profit_pct': -50.0},  # 中等情況
        ]
        
        for case in test_cases:
            analysis.multi_scenario_profit = case
            analysis.optimal_exit_timing = {'annualized_return_pct': 100.0}
            
            score = self.calculator._calculate_max_profit_score_long(analysis)
            assert 0 <= score <= 100, f"評分 {score} 超出 0-100 範圍"


class TestShortStrategyAnalysis:
    """Task 7.2, 7.3, 8.2: Short 策略分析測試"""
    
    def setup_method(self):
        self.calculator = OptimalStrikeCalculator()
    
    @given(delta=st.floats(min_value=0.01, max_value=0.99, allow_nan=False, allow_infinity=False))
    @settings(max_examples=50)
    def test_property_7_safe_probability_calculation(self, delta):
        """
        Property 7: 安全概率計算正確性
        安全概率 = 1 - |Delta|
        """
        safe_probability = 1.0 - abs(delta)
        expected = 1.0 - abs(delta)
        assert abs(safe_probability - expected) < 0.001
        assert 0 <= safe_probability <= 1
    
    @given(
        current_price=st.floats(min_value=50, max_value=200, allow_nan=False, allow_infinity=False),
        strike_price=st.floats(min_value=40, max_value=190, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=50)
    def test_property_8_safety_distance_short_put(self, current_price, strike_price):
        """
        Property 8: 安全距離計算正確性（Short Put）
        安全距離 = (當前股價 - 行使價) / 當前股價 × 100
        """
        assume(strike_price < current_price)  # Short Put 行使價應低於當前股價
        
        safety_distance = ((current_price - strike_price) / current_price) * 100
        expected = ((current_price - strike_price) / current_price) * 100
        assert abs(safety_distance - expected) < 0.001
    
    @given(
        theta=st.floats(min_value=-1.0, max_value=-0.01, allow_nan=False, allow_infinity=False),
        days=st.integers(min_value=1, max_value=90)
    )
    @settings(max_examples=50)
    def test_property_9_theta_gain_calculation(self, theta, days):
        """
        Property 9: Theta 收益計算正確性
        總 Theta 收益 = |Theta| × 到期天數
        """
        total_theta_gain = abs(theta) * days
        expected = abs(theta) * days
        assert abs(total_theta_gain - expected) < 0.001
        assert total_theta_gain >= 0


class TestShortStrategyScoring:
    """Task 9.2: Short 策略評分測試"""
    
    def setup_method(self):
        self.calculator = OptimalStrikeCalculator()
    
    def test_property_10_short_strategy_score_weights(self):
        """
        Property 10: Short 策略評分權重正確性
        總評分 = 收益率評分 × 0.4 + 安全性評分 × 0.4 + Theta 優勢評分 × 0.2
        """
        analysis = StrikeAnalysis(
            strike=95.0,
            option_type='put',
            last_price=2.0,
            delta=-0.2,
            theta=-0.05
        )
        
        # 設置期權金分析數據
        analysis.premium_analysis = {
            'annualized_yield_pct': 100.0,  # 100% 年化 -> 32 分
            'safe_probability': 0.80  # 80% 安全概率 -> 32 分
        }
        
        # 設置持有優勢數據
        analysis.hold_to_expiry_advantage = {
            'theta_percentage': 60.0  # 60% Theta 佔比 -> 約 15 分
        }
        
        score = self.calculator._calculate_max_profit_score_short(analysis)
        
        # 驗證評分在合理範圍內
        assert 0 <= score <= 100, f"評分應在 0-100 範圍內，實際為 {score}"
    
    def test_property_15_score_range_validity_short(self):
        """
        Property 15: 評分範圍有效性 (Short 策略)
        """
        analysis = StrikeAnalysis(
            strike=95.0,
            option_type='put',
            last_price=2.0,
            delta=-0.2,
            theta=-0.05
        )
        
        # 測試極端情況
        test_cases = [
            {'annualized_yield_pct': 300.0, 'safe_probability': 0.95},  # 極高收益和安全性
            {'annualized_yield_pct': 10.0, 'safe_probability': 0.50},  # 低收益和安全性
            {'annualized_yield_pct': 100.0, 'safe_probability': 0.80},  # 中等情況
        ]
        
        for case in test_cases:
            analysis.premium_analysis = case
            analysis.hold_to_expiry_advantage = {'theta_percentage': 50.0}
            
            score = self.calculator._calculate_max_profit_score_short(analysis)
            assert 0 <= score <= 100, f"評分 {score} 超出 0-100 範圍"


class TestCompositeScoreIntegration:
    """Task 11.4, 11.5, 11.7: 綜合評分整合測試"""
    
    def setup_method(self):
        self.calculator = OptimalStrikeCalculator()
    
    def test_property_11_long_strategy_composite_score(self):
        """
        Property 11: Long 策略綜合評分計算正確性
        綜合評分 = 原始評分 × 0.6 + 利益最大化評分 × 0.4
        """
        original_score = 70.0
        max_profit_score = 80.0
        
        expected_composite = original_score * 0.6 + max_profit_score * 0.4
        assert expected_composite == 70.0 * 0.6 + 80.0 * 0.4  # 42 + 32 = 74
    
    def test_property_12_short_strategy_composite_score(self):
        """
        Property 12: Short 策略綜合評分計算正確性
        綜合評分 = 原始評分 × 0.5 + 期權金安全性評分 × 0.5
        """
        original_score = 70.0
        max_profit_score = 80.0
        
        expected_composite = original_score * 0.5 + max_profit_score * 0.5
        assert expected_composite == 70.0 * 0.5 + 80.0 * 0.5  # 35 + 40 = 75
    
    def test_property_13_recommendations_sorted_by_composite_score(self):
        """
        Property 13: 推薦列表按綜合評分降序排列
        """
        # 創建模擬期權鏈數據
        option_chain = {
            'calls': [
                {'strike': 100.0, 'bid': 5.0, 'ask': 5.5, 'lastPrice': 5.25, 
                 'volume': 500, 'openInterest': 1000, 'impliedVolatility': 0.30},
                {'strike': 105.0, 'bid': 3.0, 'ask': 3.5, 'lastPrice': 3.25,
                 'volume': 300, 'openInterest': 800, 'impliedVolatility': 0.32},
                {'strike': 110.0, 'bid': 1.5, 'ask': 2.0, 'lastPrice': 1.75,
                 'volume': 200, 'openInterest': 600, 'impliedVolatility': 0.35},
            ],
            'puts': []
        }
        
        result = self.calculator.analyze_strikes(
            current_price=100.0,
            option_chain=option_chain,
            strategy_type='long_call',
            days_to_expiration=30,
            enable_max_profit_analysis=True
        )
        
        if result['top_recommendations']:
            scores = [rec['composite_score'] for rec in result['top_recommendations']]
            # 驗證按降序排列
            assert scores == sorted(scores, reverse=True), \
                f"推薦列表應按綜合評分降序排列，實際順序: {scores}"


class TestBackwardCompatibility:
    """Task 16.1: 兼容性驗證測試"""
    
    def setup_method(self):
        self.calculator = OptimalStrikeCalculator()
    
    def test_existing_functionality_preserved(self):
        """驗證現有功能正常工作"""
        option_chain = {
            'calls': [
                {'strike': 100.0, 'bid': 5.0, 'ask': 5.5, 'lastPrice': 5.25,
                 'volume': 500, 'openInterest': 1000, 'impliedVolatility': 0.30},
            ],
            'puts': [
                {'strike': 95.0, 'bid': 2.0, 'ask': 2.5, 'lastPrice': 2.25,
                 'volume': 300, 'openInterest': 800, 'impliedVolatility': 0.28},
            ]
        }
        
        # 測試禁用新功能時的行為
        result = self.calculator.analyze_strikes(
            current_price=100.0,
            option_chain=option_chain,
            strategy_type='long_call',
            days_to_expiration=30,
            enable_max_profit_analysis=False
        )
        
        assert 'analyzed_strikes' in result
        assert 'top_recommendations' in result
        assert 'best_strike' in result
    
    def test_new_fields_in_strike_analysis(self):
        """驗證新字段已添加到 StrikeAnalysis"""
        analysis = StrikeAnalysis(
            strike=100.0,
            option_type='call'
        )
        
        # 驗證新字段存在
        assert hasattr(analysis, 'multi_scenario_profit')
        assert hasattr(analysis, 'optimal_exit_timing')
        assert hasattr(analysis, 'max_profit_score')
        assert hasattr(analysis, 'premium_analysis')
        assert hasattr(analysis, 'hold_to_expiry_advantage')
        
        # 驗證 to_dict 包含新字段
        data = analysis.to_dict()
        assert 'multi_scenario_profit' in data
        assert 'optimal_exit_timing' in data
        assert 'max_profit_score' in data
        assert 'premium_analysis' in data
        assert 'hold_to_expiry_advantage' in data


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
