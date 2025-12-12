#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Property-based tests for StrategyScenarioGenerator
使用 Hypothesis 進行屬性測試

Feature: report-improvements, Property 1: 策略場景多樣性
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
import sys
import os

# 添加項目根目錄到路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from output_layer.strategy_scenario_generator import StrategyScenarioGenerator, StrategyScenario


class TestStrategyScenarioDiversity:
    """
    **Feature: report-improvements, Property 1: 策略場景多樣性**
    
    測試不同策略生成不同的場景配置
    **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5**
    """
    
    # 預期的場景配置
    EXPECTED_LONG_CALL = [-0.10, 0.00, 0.10, 0.20]
    EXPECTED_LONG_PUT = [-0.20, -0.10, 0.00, 0.10]
    EXPECTED_SHORT_CALL = [0.00, 0.05, 0.10, 0.20]
    EXPECTED_SHORT_PUT = [-0.20, -0.10, -0.05, 0.00]
    
    @given(
        stock_price=st.floats(min_value=1.0, max_value=10000.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_long_call_scenarios_match_requirements(self, stock_price):
        """
        **Feature: report-improvements, Property 1: 策略場景多樣性**
        **Validates: Requirements 1.2**
        
        Property: Long Call 策略應包含股價下跌 10%、維持不變、上漲 10%、上漲 20% 四個場景
        """
        scenarios = StrategyScenarioGenerator.get_scenarios('long_call', stock_price)
        
        # 驗證場景數量
        assert len(scenarios) == 4, f"Expected 4 scenarios, got {len(scenarios)}"
        
        # 驗證場景百分比
        actual_pcts = [s.price_change_pct for s in scenarios]
        assert actual_pcts == self.EXPECTED_LONG_CALL, \
            f"Long Call scenarios mismatch: expected {self.EXPECTED_LONG_CALL}, got {actual_pcts}"
        
        # 驗證到期股價計算正確
        for scenario in scenarios:
            expected_price = stock_price * (1 + scenario.price_change_pct)
            assert abs(scenario.stock_price_at_expiry - expected_price) < 0.01, \
                f"Price calculation error: expected {expected_price}, got {scenario.stock_price_at_expiry}"
    
    @given(
        stock_price=st.floats(min_value=1.0, max_value=10000.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_long_put_scenarios_match_requirements(self, stock_price):
        """
        **Feature: report-improvements, Property 1: 策略場景多樣性**
        **Validates: Requirements 1.3**
        
        Property: Long Put 策略應包含股價下跌 20%、下跌 10%、維持不變、上漲 10% 四個場景
        """
        scenarios = StrategyScenarioGenerator.get_scenarios('long_put', stock_price)
        
        # 驗證場景數量
        assert len(scenarios) == 4, f"Expected 4 scenarios, got {len(scenarios)}"
        
        # 驗證場景百分比
        actual_pcts = [s.price_change_pct for s in scenarios]
        assert actual_pcts == self.EXPECTED_LONG_PUT, \
            f"Long Put scenarios mismatch: expected {self.EXPECTED_LONG_PUT}, got {actual_pcts}"
    
    @given(
        stock_price=st.floats(min_value=1.0, max_value=10000.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_short_call_scenarios_match_requirements(self, stock_price):
        """
        **Feature: report-improvements, Property 1: 策略場景多樣性**
        **Validates: Requirements 1.4**
        
        Property: Short Call 策略應包含股價維持不變、上漲 5%、上漲 10%、上漲 20% 四個場景
        """
        scenarios = StrategyScenarioGenerator.get_scenarios('short_call', stock_price)
        
        # 驗證場景數量
        assert len(scenarios) == 4, f"Expected 4 scenarios, got {len(scenarios)}"
        
        # 驗證場景百分比
        actual_pcts = [s.price_change_pct for s in scenarios]
        assert actual_pcts == self.EXPECTED_SHORT_CALL, \
            f"Short Call scenarios mismatch: expected {self.EXPECTED_SHORT_CALL}, got {actual_pcts}"
    
    @given(
        stock_price=st.floats(min_value=1.0, max_value=10000.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_short_put_scenarios_match_requirements(self, stock_price):
        """
        **Feature: report-improvements, Property 1: 策略場景多樣性**
        **Validates: Requirements 1.5**
        
        Property: Short Put 策略應包含股價下跌 20%、下跌 10%、下跌 5%、維持不變 四個場景
        """
        scenarios = StrategyScenarioGenerator.get_scenarios('short_put', stock_price)
        
        # 驗證場景數量
        assert len(scenarios) == 4, f"Expected 4 scenarios, got {len(scenarios)}"
        
        # 驗證場景百分比
        actual_pcts = [s.price_change_pct for s in scenarios]
        assert actual_pcts == self.EXPECTED_SHORT_PUT, \
            f"Short Put scenarios mismatch: expected {self.EXPECTED_SHORT_PUT}, got {actual_pcts}"
    
    @given(
        stock_price=st.floats(min_value=1.0, max_value=10000.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_different_strategies_have_different_scenarios(self, stock_price):
        """
        **Feature: report-improvements, Property 1: 策略場景多樣性**
        **Validates: Requirements 1.1**
        
        Property: 不同策略應有不同的場景配置
        """
        strategies = ['long_call', 'long_put', 'short_call', 'short_put']
        scenario_sets = {}
        
        for strategy in strategies:
            scenarios = StrategyScenarioGenerator.get_scenarios(strategy, stock_price)
            pcts = tuple(s.price_change_pct for s in scenarios)
            scenario_sets[strategy] = pcts
        
        # 驗證每個策略的場景配置都不同
        unique_configs = set(scenario_sets.values())
        assert len(unique_configs) == 4, \
            f"Expected 4 unique scenario configurations, got {len(unique_configs)}"
    
    @given(
        stock_price=st.floats(min_value=1.0, max_value=10000.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_scenario_labels_are_descriptive(self, stock_price):
        """
        **Feature: report-improvements, Property 1: 策略場景多樣性**
        **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5**
        
        Property: 每個場景應有描述性的標籤
        """
        for strategy in ['long_call', 'long_put', 'short_call', 'short_put']:
            scenarios = StrategyScenarioGenerator.get_scenarios(strategy, stock_price)
            
            for scenario in scenarios:
                # 標籤不應為空
                assert scenario.scenario_label, f"Scenario label should not be empty"
                
                # 標籤應包含描述性文字
                if scenario.price_change_pct == 0:
                    assert "維持不變" in scenario.scenario_label or "不變" in scenario.scenario_label
                elif scenario.price_change_pct < 0:
                    assert "下跌" in scenario.scenario_label
                else:
                    assert "上漲" in scenario.scenario_label
    
    @given(
        stock_price=st.floats(min_value=1.0, max_value=10000.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_module_name_aliases_work(self, stock_price):
        """
        **Feature: report-improvements, Property 1: 策略場景多樣性**
        **Validates: Requirements 1.1**
        
        Property: 模塊名稱別名應返回相同的場景配置
        """
        # 測試模塊名稱別名
        aliases = [
            ('long_call', 'module7_long_call'),
            ('long_put', 'module8_long_put'),
            ('short_call', 'module9_short_call'),
            ('short_put', 'module10_short_put'),
        ]
        
        for base_name, module_name in aliases:
            base_scenarios = StrategyScenarioGenerator.get_scenarios(base_name, stock_price)
            module_scenarios = StrategyScenarioGenerator.get_scenarios(module_name, stock_price)
            
            base_pcts = [s.price_change_pct for s in base_scenarios]
            module_pcts = [s.price_change_pct for s in module_scenarios]
            
            assert base_pcts == module_pcts, \
                f"Alias mismatch: {base_name} != {module_name}"


class TestStrategyScenarioEdgeCases:
    """
    測試邊界情況
    """
    
    def test_invalid_strategy_type_raises_error(self):
        """測試無效策略類型應拋出錯誤"""
        with pytest.raises(ValueError) as exc_info:
            StrategyScenarioGenerator.get_scenarios('invalid_strategy', 100.0)
        
        assert "無效的策略類型" in str(exc_info.value)
    
    def test_invalid_stock_price_raises_error(self):
        """測試無效股價應拋出錯誤"""
        with pytest.raises(ValueError) as exc_info:
            StrategyScenarioGenerator.get_scenarios('long_call', -100.0)
        
        assert "股價必須為正數" in str(exc_info.value)
        
        with pytest.raises(ValueError):
            StrategyScenarioGenerator.get_scenarios('long_call', 0)
        
        with pytest.raises(ValueError):
            StrategyScenarioGenerator.get_scenarios('long_call', None)
    
    def test_get_scenario_prices_returns_correct_values(self):
        """測試 get_scenario_prices 方法"""
        stock_price = 100.0
        prices = StrategyScenarioGenerator.get_scenario_prices('long_call', stock_price)
        
        assert len(prices) == 4
        assert prices == [90.0, 100.0, 110.0, 120.0]
    
    def test_get_scenario_labels_returns_correct_values(self):
        """測試 get_scenario_labels 方法"""
        labels = StrategyScenarioGenerator.get_scenario_labels('long_call')
        
        assert len(labels) == 4
        assert labels == ["下跌10%", "維持不變", "上漲10%", "上漲20%"]
    
    def test_get_scenario_percentages_returns_correct_values(self):
        """測試 get_scenario_percentages 方法"""
        pcts = StrategyScenarioGenerator.get_scenario_percentages('short_put')
        
        assert len(pcts) == 4
        assert pcts == [-0.20, -0.10, -0.05, 0.00]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
