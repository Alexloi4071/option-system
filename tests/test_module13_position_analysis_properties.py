#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Property-based tests for Module 13 Position Analysis
使用 Hypothesis 進行屬性測試

Feature: report-improvements
Property 7: 數據不可用標示
Property 8: Put/Call 比率計算
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
import sys
import os

# 添加項目根目錄到路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from calculation_layer.module13_position_analysis import PositionAnalysisCalculator, PositionAnalysisResult
from output_layer.report_generator import ReportGenerator


class TestDataUnavailableDisplay:
    """
    **Feature: report-improvements, Property 7: 數據不可用標示**
    
    測試當未平倉量為 None 時，輸出應顯示「數據不可用」而非 0
    **Validates: Requirements 2.4**
    """
    
    def test_none_call_volume_shows_unavailable(self):
        """
        **Feature: report-improvements, Property 7: 數據不可用標示**
        **Validates: Requirements 2.4**
        
        Property: 當 call_volume 為 None 時，應顯示「數據不可用」
        """
        report_gen = ReportGenerator()
        
        # 測試 None 值
        result = report_gen._format_position_value(None)
        assert result == "數據不可用", f"Expected '數據不可用', got '{result}'"
    
    def test_none_put_volume_shows_unavailable(self):
        """
        **Feature: report-improvements, Property 7: 數據不可用標示**
        **Validates: Requirements 2.4**
        
        Property: 當 put_volume 為 None 時，應顯示「數據不可用」
        """
        report_gen = ReportGenerator()
        
        result = report_gen._format_position_value(None)
        assert result == "數據不可用"
    
    def test_none_open_interest_shows_unavailable(self):
        """
        **Feature: report-improvements, Property 7: 數據不可用標示**
        **Validates: Requirements 2.4**
        
        Property: 當 open_interest 為 None 時，應顯示「數據不可用」
        """
        report_gen = ReportGenerator()
        
        result = report_gen._format_position_value(None)
        assert result == "數據不可用"
    
    @given(
        value=st.integers(min_value=0, max_value=10000000)
    )
    @settings(max_examples=100)
    def test_valid_values_show_formatted_number(self, value):
        """
        **Feature: report-improvements, Property 7: 數據不可用標示**
        **Validates: Requirements 2.4**
        
        Property: 有效數值應顯示格式化的數字（帶千位分隔符）
        """
        report_gen = ReportGenerator()
        
        result = report_gen._format_position_value(value)
        expected = f"{value:,}"
        assert result == expected, f"Expected '{expected}', got '{result}'"
    
    def test_module13_report_shows_unavailable_for_none_values(self):
        """
        **Feature: report-improvements, Property 7: 數據不可用標示**
        **Validates: Requirements 2.4**
        
        Property: Module 13 報告中，None 值應顯示「數據不可用」
        """
        report_gen = ReportGenerator()
        
        # 模擬部分數據不可用的情況
        results = {
            'volume': 1000,
            'open_interest': 5000,
            'volume_oi_ratio': 0.2,
            'call_volume': None,  # 數據不可用
            'call_open_interest': 500,
            'put_volume': 300,
            'put_open_interest': None,  # 數據不可用
            'put_call_ratio': None
        }
        
        report = report_gen._format_module13_position_analysis(results)
        
        # 驗證報告中包含「數據不可用」
        assert "數據不可用" in report, "Report should show '數據不可用' for None values"


class TestPutCallRatioCalculation:
    """
    **Feature: report-improvements, Property 8: Put/Call 比率計算**
    
    測試 Put/Call 比率計算的正確性
    **Validates: Requirements 2.3**
    """
    
    @given(
        call_oi=st.integers(min_value=1, max_value=10000000),
        put_oi=st.integers(min_value=0, max_value=10000000)
    )
    @settings(max_examples=100)
    def test_put_call_ratio_calculation_correct(self, call_oi, put_oi):
        """
        **Feature: report-improvements, Property 8: Put/Call 比率計算**
        **Validates: Requirements 2.3**
        
        Property: *For any* 有效的 Put 和 Call 未平倉量，
                  計算的 Put/Call 比率應等於 Put OI / Call OI
        """
        calculator = PositionAnalysisCalculator()
        
        # 計算 Put/Call 比率
        ratio = calculator._calculate_put_call_ratio(call_oi, put_oi)
        
        # 驗證計算正確
        expected_ratio = put_oi / call_oi
        assert ratio is not None, "Ratio should not be None for valid inputs"
        assert abs(ratio - expected_ratio) < 0.0001, \
            f"Expected ratio {expected_ratio}, got {ratio}"
    
    def test_put_call_ratio_none_when_call_oi_is_none(self):
        """
        **Feature: report-improvements, Property 8: Put/Call 比率計算**
        **Validates: Requirements 2.3**
        
        Property: 當 Call OI 為 None 時，比率應為 None
        """
        calculator = PositionAnalysisCalculator()
        
        ratio = calculator._calculate_put_call_ratio(None, 1000)
        assert ratio is None, "Ratio should be None when call_oi is None"
    
    def test_put_call_ratio_none_when_put_oi_is_none(self):
        """
        **Feature: report-improvements, Property 8: Put/Call 比率計算**
        **Validates: Requirements 2.3**
        
        Property: 當 Put OI 為 None 時，比率應為 None
        """
        calculator = PositionAnalysisCalculator()
        
        ratio = calculator._calculate_put_call_ratio(1000, None)
        assert ratio is None, "Ratio should be None when put_oi is None"
    
    def test_put_call_ratio_none_when_call_oi_is_zero(self):
        """
        **Feature: report-improvements, Property 8: Put/Call 比率計算**
        **Validates: Requirements 2.3**
        
        Property: 當 Call OI 為 0 時，比率應為 None（避免除以零）
        """
        calculator = PositionAnalysisCalculator()
        
        ratio = calculator._calculate_put_call_ratio(0, 1000)
        assert ratio is None, "Ratio should be None when call_oi is 0"
    
    @given(
        call_oi=st.integers(min_value=1, max_value=10000000),
        put_oi=st.integers(min_value=0, max_value=10000000)
    )
    @settings(max_examples=100)
    def test_put_call_ratio_in_result_dict(self, call_oi, put_oi):
        """
        **Feature: report-improvements, Property 8: Put/Call 比率計算**
        **Validates: Requirements 2.3**
        
        Property: PositionAnalysisResult.to_dict() 應包含正確的 put_call_ratio
        """
        calculator = PositionAnalysisCalculator()
        
        result = calculator.calculate(
            volume=1000,
            open_interest=5000,
            price_change=1.5,
            call_volume=500,
            call_open_interest=call_oi,
            put_volume=300,
            put_open_interest=put_oi
        )
        
        result_dict = result.to_dict()
        
        # 驗證 put_call_ratio 存在且正確
        assert 'put_call_ratio' in result_dict
        expected_ratio = put_oi / call_oi
        assert result_dict['put_call_ratio'] is not None
        assert abs(result_dict['put_call_ratio'] - expected_ratio) < 0.0001


class TestCallPutSeparation:
    """
    測試 Call/Put 數據分離功能
    **Validates: Requirements 2.1, 2.2**
    """
    
    @given(
        call_vol=st.integers(min_value=0, max_value=10000000),
        call_oi=st.integers(min_value=0, max_value=10000000),
        put_vol=st.integers(min_value=0, max_value=10000000),
        put_oi=st.integers(min_value=0, max_value=10000000)
    )
    @settings(max_examples=100)
    def test_call_put_data_preserved_in_result(self, call_vol, call_oi, put_vol, put_oi):
        """
        **Feature: report-improvements**
        **Validates: Requirements 2.1, 2.2**
        
        Property: Call/Put 數據應正確保存在結果中
        """
        calculator = PositionAnalysisCalculator()
        
        # 使用 None 表示數據不可用（0 值時）
        call_vol_input = call_vol if call_vol > 0 else None
        call_oi_input = call_oi if call_oi > 0 else None
        put_vol_input = put_vol if put_vol > 0 else None
        put_oi_input = put_oi if put_oi > 0 else None
        
        result = calculator.calculate(
            volume=call_vol + put_vol,
            open_interest=call_oi + put_oi,
            price_change=0.0,
            call_volume=call_vol_input,
            call_open_interest=call_oi_input,
            put_volume=put_vol_input,
            put_open_interest=put_oi_input
        )
        
        result_dict = result.to_dict()
        
        # 驗證 Call/Put 數據正確保存
        assert result_dict['call_volume'] == call_vol_input
        assert result_dict['call_open_interest'] == call_oi_input
        assert result_dict['put_volume'] == put_vol_input
        assert result_dict['put_open_interest'] == put_oi_input
    
    def test_report_shows_call_put_sections(self):
        """
        **Feature: report-improvements**
        **Validates: Requirements 2.1, 2.2**
        
        Property: 報告應包含 Call 和 Put 的獨立區塊
        """
        report_gen = ReportGenerator()
        
        results = {
            'volume': 1000,
            'open_interest': 5000,
            'volume_oi_ratio': 0.2,
            'call_volume': 600,
            'call_open_interest': 3000,
            'put_volume': 400,
            'put_open_interest': 2000,
            'put_call_ratio': 0.6667
        }
        
        report = report_gen._format_module13_position_analysis(results)
        
        # 驗證報告包含 Call 和 Put 區塊
        assert "Call 期權" in report, "Report should contain Call section"
        assert "Put 期權" in report, "Report should contain Put section"
        assert "Put/Call 比率" in report, "Report should contain Put/Call ratio"


class TestPutCallRatioInterpretation:
    """
    測試 Put/Call 比率解讀
    """
    
    def test_high_put_call_ratio_shows_bearish(self):
        """
        Property: Put/Call 比率 > 1.0 應顯示看跌傾向
        """
        report_gen = ReportGenerator()
        
        results = {
            'volume': 1000,
            'open_interest': 5000,
            'volume_oi_ratio': 0.2,
            'call_volume': 300,
            'call_open_interest': 2000,
            'put_volume': 700,
            'put_open_interest': 3000,
            'put_call_ratio': 1.5  # > 1.0
        }
        
        report = report_gen._format_module13_position_analysis(results)
        
        assert "看跌傾向" in report, "High Put/Call ratio should show bearish indication"
    
    def test_low_put_call_ratio_shows_bullish(self):
        """
        Property: Put/Call 比率 < 0.7 應顯示看漲傾向
        """
        report_gen = ReportGenerator()
        
        results = {
            'volume': 1000,
            'open_interest': 5000,
            'volume_oi_ratio': 0.2,
            'call_volume': 700,
            'call_open_interest': 3000,
            'put_volume': 300,
            'put_open_interest': 1500,
            'put_call_ratio': 0.5  # < 0.7
        }
        
        report = report_gen._format_module13_position_analysis(results)
        
        assert "看漲傾向" in report, "Low Put/Call ratio should show bullish indication"
    
    def test_neutral_put_call_ratio(self):
        """
        Property: Put/Call 比率在 0.7-1.0 之間應顯示中性
        """
        report_gen = ReportGenerator()
        
        results = {
            'volume': 1000,
            'open_interest': 5000,
            'volume_oi_ratio': 0.2,
            'call_volume': 500,
            'call_open_interest': 2500,
            'put_volume': 500,
            'put_open_interest': 2000,
            'put_call_ratio': 0.8  # 0.7 <= ratio <= 1.0
        }
        
        report = report_gen._format_module13_position_analysis(results)
        
        assert "中性" in report, "Neutral Put/Call ratio should show neutral indication"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
