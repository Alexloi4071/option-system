#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Property-based tests for IV Comparison Analysis

**Feature: report-improvements, Property 5: IV 比較分析**
**Validates: Requirements 6.1, 6.2**
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from output_layer.report_generator import ReportGenerator


# Strategy for valid IV values (0.01 to 2.0, i.e., 1% to 200%)
iv_strategy = st.floats(min_value=0.01, max_value=2.0, allow_nan=False, allow_infinity=False)


class TestIVComparisonAnalysis:
    """
    Test IV Comparison Analysis
    
    **Feature: report-improvements, Property 5: IV 比較分析**
    **Validates: Requirements 6.1, 6.2**
    """
    
    def setup_method(self):
        self.generator = ReportGenerator()
    
    @given(call_iv=iv_strategy, put_iv=iv_strategy)
    @settings(max_examples=100)
    def test_iv_comparison_returns_valid_structure(self, call_iv, put_iv):
        """
        Property 5: For any valid Call IV and Put IV, comparison should return valid structure.
        
        **Feature: report-improvements, Property 5: IV 比較分析**
        **Validates: Requirements 6.1, 6.2**
        """
        result = self.generator._get_iv_comparison_analysis(call_iv, put_iv)
        
        # Should return a dict with required keys
        assert result is not None
        assert 'call_iv' in result
        assert 'put_iv' in result
        assert 'diff_pct' in result
        assert 'has_skew' in result
        assert 'comparison_text' in result
    
    @given(call_iv=iv_strategy, put_iv=iv_strategy)
    @settings(max_examples=100)
    def test_iv_skew_warning_when_diff_exceeds_5_percent(self, call_iv, put_iv):
        """
        Property 5: When Call IV and Put IV differ by more than 5%, output should contain skew warning.
        
        **Feature: report-improvements, Property 5: IV 比較分析**
        **Validates: Requirements 6.1, 6.2**
        """
        result = self.generator._get_iv_comparison_analysis(call_iv, put_iv)
        
        # Calculate expected diff percentage
        max_iv = max(call_iv, put_iv)
        expected_diff_pct = abs(call_iv - put_iv) / max_iv * 100
        
        # Verify skew detection
        if expected_diff_pct > 5.0:
            assert result['has_skew'] is True
            assert result['skew_warning'] is not None
            assert result['skew_reason'] is not None
            # Verify warning contains "偏斜" or percentage info
            assert '高於' in result['skew_warning'] or 'IV' in result['skew_warning']
        else:
            assert result['has_skew'] is False
    
    @given(call_iv=iv_strategy, put_iv=iv_strategy)
    @settings(max_examples=100)
    def test_iv_skew_direction_correctness(self, call_iv, put_iv):
        """
        Property 5: Skew direction should correctly identify which IV is higher.
        
        **Feature: report-improvements, Property 5: IV 比較分析**
        **Validates: Requirements 6.1, 6.2**
        """
        result = self.generator._get_iv_comparison_analysis(call_iv, put_iv)
        
        max_iv = max(call_iv, put_iv)
        diff_pct = abs(call_iv - put_iv) / max_iv * 100
        
        if diff_pct > 5.0:
            if put_iv > call_iv:
                assert result['skew_direction'] == 'put_premium'
                assert 'Put IV 高於' in result['skew_warning']
            else:
                assert result['skew_direction'] == 'call_premium'
                assert 'Call IV 高於' in result['skew_warning']
        else:
            assert result['skew_direction'] == 'neutral'
    
    @given(call_iv=iv_strategy, put_iv=iv_strategy)
    @settings(max_examples=100)
    def test_diff_percentage_calculation_accuracy(self, call_iv, put_iv):
        """
        Property 5: Difference percentage should be calculated correctly.
        
        **Feature: report-improvements, Property 5: IV 比較分析**
        **Validates: Requirements 6.1, 6.2**
        """
        result = self.generator._get_iv_comparison_analysis(call_iv, put_iv)
        
        # Calculate expected diff percentage
        max_iv = max(call_iv, put_iv)
        expected_diff_pct = abs(call_iv - put_iv) / max_iv * 100
        
        # Allow small floating point tolerance
        assert abs(result['diff_pct'] - expected_diff_pct) < 0.01


class TestIVComparisonEdgeCases:
    """Test edge cases for IV comparison"""
    
    def setup_method(self):
        self.generator = ReportGenerator()
    
    def test_none_call_iv_returns_none(self):
        """When call_iv is None, should return None"""
        result = self.generator._get_iv_comparison_analysis(None, 0.25)
        assert result is None
    
    def test_none_put_iv_returns_none(self):
        """When put_iv is None, should return None"""
        result = self.generator._get_iv_comparison_analysis(0.25, None)
        assert result is None
    
    def test_zero_call_iv_returns_none(self):
        """When call_iv is 0, should return None"""
        result = self.generator._get_iv_comparison_analysis(0, 0.25)
        assert result is None
    
    def test_zero_put_iv_returns_none(self):
        """When put_iv is 0, should return None"""
        result = self.generator._get_iv_comparison_analysis(0.25, 0)
        assert result is None
    
    def test_equal_ivs_no_skew(self):
        """When Call IV equals Put IV, there should be no skew"""
        result = self.generator._get_iv_comparison_analysis(0.30, 0.30)
        assert result['has_skew'] is False
        assert result['diff_pct'] == 0.0


class TestHistoricalIVComparison:
    """Test historical IV comparison functionality"""
    
    def setup_method(self):
        self.generator = ReportGenerator()
    
    @given(
        current_iv=iv_strategy,
        historical_iv=iv_strategy
    )
    @settings(max_examples=100)
    def test_historical_comparison_returns_valid_structure(self, current_iv, historical_iv):
        """Historical IV comparison should return valid structure"""
        result = self.generator._get_historical_iv_comparison(current_iv, historical_iv)
        
        assert result is not None
        assert 'status' in result
        assert 'level' in result
    
    @given(
        current_iv=st.floats(min_value=0.25, max_value=2.0, allow_nan=False, allow_infinity=False),
        historical_iv=st.floats(min_value=0.01, max_value=0.20, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=50)
    def test_high_iv_detection(self, current_iv, historical_iv):
        """When current IV is significantly higher than historical, should detect as high"""
        assume(current_iv / historical_iv > 1.2)
        result = self.generator._get_historical_iv_comparison(current_iv, historical_iv)
        assert result['level'] == 'high'
        assert '高於歷史' in result['status']
    
    @given(
        current_iv=st.floats(min_value=0.01, max_value=0.15, allow_nan=False, allow_infinity=False),
        historical_iv=st.floats(min_value=0.20, max_value=2.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=50)
    def test_low_iv_detection(self, current_iv, historical_iv):
        """When current IV is significantly lower than historical, should detect as low"""
        assume(current_iv / historical_iv < 0.8)
        result = self.generator._get_historical_iv_comparison(current_iv, historical_iv)
        assert result['level'] == 'low'
        assert '低於歷史' in result['status']


class TestIVStrategySuggestion:
    """Test IV strategy suggestion functionality"""
    
    def setup_method(self):
        self.generator = ReportGenerator()
    
    @given(call_iv=iv_strategy, put_iv=iv_strategy)
    @settings(max_examples=100)
    def test_strategy_suggestion_returns_valid_structure(self, call_iv, put_iv):
        """Strategy suggestion should return valid structure"""
        result = self.generator._get_iv_strategy_suggestion(call_iv, put_iv)
        
        assert result is not None
        assert 'recommendation' in result
        assert 'reason' in result
    
    def test_high_iv_suggests_selling(self):
        """High IV (>50%) should suggest selling options"""
        result = self.generator._get_iv_strategy_suggestion(0.55, 0.55)
        assert '賣出' in result['recommendation']
    
    def test_low_iv_suggests_buying(self):
        """Low IV (<20%) should suggest buying options"""
        result = self.generator._get_iv_strategy_suggestion(0.15, 0.15)
        assert '買入' in result['recommendation']
    
    def test_none_iv_returns_none(self):
        """When both IVs are None, should return None"""
        result = self.generator._get_iv_strategy_suggestion(None, None)
        assert result is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
