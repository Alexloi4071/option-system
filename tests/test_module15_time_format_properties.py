#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Property-based tests for Module 15 Black-Scholes Time Format
使用 Hypothesis 進行屬性測試

**Feature: report-improvements, Property 3: 到期時間格式完整性**
**Validates: Requirements 4.1, 4.2**

測試 _format_module15_black_scholes 方法的到期時間格式：
- 應同時包含天數格式和年化格式
- 短期期權（< 7 天）應顯示警告
"""

import pytest
from hypothesis import given, strategies as st, settings
import sys
import os
import re

# 添加項目根目錄到路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from output_layer.report_generator import ReportGenerator


class TestBlackScholesTimeFormatCompleteness:
    """
    **Feature: report-improvements, Property 3: 到期時間格式完整性**
    **Validates: Requirements 4.1, 4.2**
    
    測試 Black-Scholes 到期時間格式的完整性：
    - 應以天數格式顯示到期時間
    - 應同時顯示天數和年化數值
    """
    
    def setup_method(self):
        """每個測試方法前初始化報告生成器"""
        self.generator = ReportGenerator()
    
    def _create_bs_results(self, time_to_expiry_years: float) -> dict:
        """創建 Black-Scholes 測試數據"""
        return {
            'parameters': {
                'stock_price': 100.0,
                'strike_price': 100.0,
                'risk_free_rate': 0.05,
                'time_to_expiration': time_to_expiry_years,
                'volatility': 0.25
            },
            'call': {
                'option_price': 5.0,
                'd1': 0.25,
                'd2': 0.15
            },
            'put': {
                'option_price': 4.5,
                'd1': 0.25,
                'd2': 0.15
            }
        }
    
    @given(time_years=st.floats(min_value=0.001, max_value=2.0, allow_nan=False, allow_infinity=False))
    @settings(max_examples=100)
    def test_time_format_contains_days_and_years(self, time_years):
        """
        **Feature: report-improvements, Property 3: 到期時間格式完整性**
        **Validates: Requirements 4.1, 4.2**
        
        Property: For any valid time to expiration, the output should contain
        both days format and annualized format.
        """
        results = self._create_bs_results(time_years)
        output = self.generator._format_module15_black_scholes(results)
        
        # 計算預期的天數
        expected_days = time_years * 365
        
        # 驗證輸出包含「天」字樣
        assert '天' in output, \
            f"Output should contain '天' for time {time_years} years"
        
        # 驗證輸出包含「年」字樣
        assert '年' in output, \
            f"Output should contain '年' for time {time_years} years"
        
        # 驗證到期時間行同時包含天數和年化格式
        # 格式應為: "到期時間: X 天 (Y.YYYY 年)"
        time_pattern = r'到期時間:\s*\d+\s*天\s*\(\d+\.\d+\s*年\)'
        assert re.search(time_pattern, output), \
            f"Output should match pattern 'X 天 (Y.YYYY 年)', got: {output}"
    
    @given(time_years=st.floats(min_value=0.001, max_value=2.0, allow_nan=False, allow_infinity=False))
    @settings(max_examples=100)
    def test_days_calculation_accuracy(self, time_years):
        """
        **Feature: report-improvements, Property 3: 到期時間格式完整性**
        **Validates: Requirements 4.1**
        
        Property: The displayed days should be approximately equal to 
        time_years * 365.
        """
        results = self._create_bs_results(time_years)
        output = self.generator._format_module15_black_scholes(results)
        
        # 提取顯示的天數
        days_match = re.search(r'到期時間:\s*(\d+)\s*天', output)
        assert days_match, f"Could not find days in output: {output}"
        
        displayed_days = int(days_match.group(1))
        expected_days = round(time_years * 365)
        
        # 允許四捨五入誤差
        assert abs(displayed_days - expected_days) <= 1, \
            f"Expected ~{expected_days} days, got {displayed_days} days"


class TestBlackScholesShortTermWarning:
    """
    **Feature: report-improvements, Property 3: 到期時間格式完整性**
    **Validates: Requirements 4.3**
    
    測試短期期權警告功能：
    - 到期時間少於 7 天時應顯示警告
    """
    
    def setup_method(self):
        """每個測試方法前初始化報告生成器"""
        self.generator = ReportGenerator()
    
    def _create_bs_results(self, time_to_expiry_years: float) -> dict:
        """創建 Black-Scholes 測試數據"""
        return {
            'parameters': {
                'stock_price': 100.0,
                'strike_price': 100.0,
                'risk_free_rate': 0.05,
                'time_to_expiration': time_to_expiry_years,
                'volatility': 0.25
            },
            'call': {
                'option_price': 5.0,
                'd1': 0.25,
                'd2': 0.15
            },
            'put': {
                'option_price': 4.5,
                'd1': 0.25,
                'd2': 0.15
            }
        }
    
    @given(days=st.integers(min_value=1, max_value=6))
    @settings(max_examples=50)
    def test_short_term_warning_displayed(self, days):
        """
        **Feature: report-improvements, Property 3: 到期時間格式完整性**
        **Validates: Requirements 4.3**
        
        Property: For any time to expiration less than 7 days, the output
        should contain a short-term option warning.
        """
        time_years = days / 365.0
        results = self._create_bs_results(time_years)
        output = self.generator._format_module15_black_scholes(results)
        
        # 驗證輸出包含短期期權警告
        assert '短期期權警告' in output, \
            f"Output should contain '短期期權警告' for {days} days"
        
        # 驗證警告提及時間衰減
        assert 'Theta' in output or '時間價值衰減' in output, \
            f"Warning should mention time decay for {days} days"
    
    @given(days=st.integers(min_value=7, max_value=365))
    @settings(max_examples=50)
    def test_no_warning_for_longer_term(self, days):
        """
        **Feature: report-improvements, Property 3: 到期時間格式完整性**
        **Validates: Requirements 4.3**
        
        Property: For any time to expiration >= 7 days, the output
        should NOT contain a short-term option warning.
        """
        time_years = days / 365.0
        results = self._create_bs_results(time_years)
        output = self.generator._format_module15_black_scholes(results)
        
        # 驗證輸出不包含短期期權警告
        assert '短期期權警告' not in output, \
            f"Output should NOT contain '短期期權警告' for {days} days"


class TestBlackScholesTimeFormatBoundaries:
    """
    測試到期時間格式的邊界條件
    """
    
    def setup_method(self):
        """每個測試方法前初始化報告生成器"""
        self.generator = ReportGenerator()
    
    def _create_bs_results(self, time_to_expiry_years: float) -> dict:
        """創建 Black-Scholes 測試數據"""
        return {
            'parameters': {
                'stock_price': 100.0,
                'strike_price': 100.0,
                'risk_free_rate': 0.05,
                'time_to_expiration': time_to_expiry_years,
                'volatility': 0.25
            },
            'call': {
                'option_price': 5.0,
                'd1': 0.25,
                'd2': 0.15
            },
            'put': {
                'option_price': 4.5,
                'd1': 0.25,
                'd2': 0.15
            }
        }
    
    def test_exactly_7_days_no_warning(self):
        """
        Test exactly 7 days - should NOT show warning
        """
        time_years = 7 / 365.0
        results = self._create_bs_results(time_years)
        output = self.generator._format_module15_black_scholes(results)
        
        # 7 天剛好不應該顯示警告
        assert '短期期權警告' not in output, \
            "7 days should NOT trigger short-term warning"
    
    def test_6_days_shows_warning(self):
        """
        Test 6 days - should show warning
        """
        time_years = 6 / 365.0
        results = self._create_bs_results(time_years)
        output = self.generator._format_module15_black_scholes(results)
        
        # 6 天應該顯示警告
        assert '短期期權警告' in output, \
            "6 days should trigger short-term warning"
    
    def test_1_day_shows_warning(self):
        """
        Test 1 day - should show warning
        """
        time_years = 1 / 365.0
        results = self._create_bs_results(time_years)
        output = self.generator._format_module15_black_scholes(results)
        
        # 1 天應該顯示警告
        assert '短期期權警告' in output, \
            "1 day should trigger short-term warning"
    
    def test_missing_parameters_handled(self):
        """
        Test handling of missing parameters
        """
        results = {
            'call': {
                'option_price': 5.0,
                'd1': 0.25,
                'd2': 0.15
            }
        }
        output = self.generator._format_module15_black_scholes(results)
        
        # 應該不會崩潰，仍然生成報告
        assert 'Module 15' in output, \
            "Should still generate report without parameters"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
