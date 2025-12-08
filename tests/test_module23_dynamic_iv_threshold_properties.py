#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Property-based tests for Module 23 Dynamic IV Threshold Calculator
使用 Hypothesis 進行屬性測試
"""

import pytest
import numpy as np
from hypothesis import given, strategies as st, settings, assume
import sys
import os

# 添加項目根目錄到路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from calculation_layer.module23_dynamic_iv_threshold import DynamicIVThresholdCalculator


class TestIVThresholdFlagging:
    """
    **Feature: jin-cao-option-enhancements, Property 4: IV Threshold Flagging**
    
    測試IV閾值標記的正確性
    """
    
    def setup_method(self):
        self.calculator = DynamicIVThresholdCalculator()
    
    @given(
        current_iv=st.floats(min_value=10.0, max_value=100.0, allow_nan=False, allow_infinity=False),
        iv_mean=st.floats(min_value=15.0, max_value=50.0, allow_nan=False, allow_infinity=False),
        iv_std=st.floats(min_value=2.0, max_value=15.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_high_iv_flagging(self, current_iv, iv_mean, iv_std):
        """
        **Feature: jin-cao-option-enhancements, Property 4: IV Threshold Flagging**
        **Validates: Requirements 13.2**
        
        Property: When current IV exceeds 75th percentile, status should be "高於歷史水平".
        """
        # 生成歷史IV數據
        np.random.seed(42)
        historical_iv = np.random.normal(iv_mean, iv_std, 252)
        historical_iv = np.clip(historical_iv, 5, 150)  # 限制在合理範圍
        
        # 計算75th percentile
        percentile_75 = np.percentile(historical_iv, 75)
        
        # 設定當前IV高於75th percentile
        high_iv = percentile_75 + 5.0
        
        result = self.calculator.calculate_thresholds(
            current_iv=high_iv,
            historical_iv=historical_iv
        )
        
        assert result.status == "高於歷史水平", \
            f"Expected '高於歷史水平' for IV {high_iv:.2f} > 75th {percentile_75:.2f}, got {result.status}"
    
    @given(
        iv_mean=st.floats(min_value=20.0, max_value=50.0, allow_nan=False, allow_infinity=False),
        iv_std=st.floats(min_value=3.0, max_value=10.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_low_iv_flagging(self, iv_mean, iv_std):
        """
        **Feature: jin-cao-option-enhancements, Property 4: IV Threshold Flagging**
        **Validates: Requirements 13.3**
        
        Property: When current IV is below 25th percentile, status should be "低於歷史水平".
        """
        # 生成歷史IV數據
        np.random.seed(42)
        historical_iv = np.random.normal(iv_mean, iv_std, 252)
        historical_iv = np.clip(historical_iv, 5, 150)
        
        # 計算25th percentile
        percentile_25 = np.percentile(historical_iv, 25)
        
        # 設定當前IV低於25th percentile
        low_iv = max(5.0, percentile_25 - 5.0)
        
        result = self.calculator.calculate_thresholds(
            current_iv=low_iv,
            historical_iv=historical_iv
        )
        
        assert result.status == "低於歷史水平", \
            f"Expected '低於歷史水平' for IV {low_iv:.2f} < 25th {percentile_25:.2f}, got {result.status}"
    
    @given(
        iv_mean=st.floats(min_value=20.0, max_value=50.0, allow_nan=False, allow_infinity=False),
        iv_std=st.floats(min_value=3.0, max_value=10.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_normal_iv_flagging(self, iv_mean, iv_std):
        """
        **Feature: jin-cao-option-enhancements, Property 4: IV Threshold Flagging**
        **Validates: Requirements 13.2, 13.3**
        
        Property: When current IV is between 25th and 75th percentile, status should be "正常範圍".
        """
        # 生成歷史IV數據
        np.random.seed(42)
        historical_iv = np.random.normal(iv_mean, iv_std, 252)
        historical_iv = np.clip(historical_iv, 5, 150)
        
        # 計算百分位數
        percentile_25 = np.percentile(historical_iv, 25)
        percentile_75 = np.percentile(historical_iv, 75)
        
        # 設定當前IV在正常範圍內
        normal_iv = (percentile_25 + percentile_75) / 2
        
        result = self.calculator.calculate_thresholds(
            current_iv=normal_iv,
            historical_iv=historical_iv
        )
        
        assert result.status == "正常範圍", \
            f"Expected '正常範圍' for IV {normal_iv:.2f} in [{percentile_25:.2f}, {percentile_75:.2f}], got {result.status}"


class TestDynamicThresholdFallback:
    """
    **Feature: jin-cao-option-enhancements, Property 5: Dynamic Threshold Fallback**
    
    測試動態閾值降級到靜態閾值的正確性
    """
    
    def setup_method(self):
        self.calculator = DynamicIVThresholdCalculator()
    
    @given(
        current_iv=st.floats(min_value=10.0, max_value=80.0, allow_nan=False, allow_infinity=False),
        vix=st.floats(min_value=10.0, max_value=50.0, allow_nan=False, allow_infinity=False),
        data_points=st.integers(min_value=0, max_value=59)
    )
    @settings(max_examples=100)
    def test_insufficient_data_uses_static(self, current_iv, vix, data_points):
        """
        **Feature: jin-cao-option-enhancements, Property 5: Dynamic Threshold Fallback**
        **Validates: Requirements 13.4, 5.4**
        
        Property: When historical data has fewer than 60 points, use static thresholds.
        (Updated: threshold changed from 200 to 60 per Requirements 5.4)
        """
        # 生成不足的歷史數據
        if data_points > 0:
            historical_iv = np.random.normal(30, 5, data_points)
        else:
            historical_iv = None
        
        result = self.calculator.calculate_thresholds(
            current_iv=current_iv,
            historical_iv=historical_iv,
            vix=vix
        )
        
        # 驗證使用靜態閾值
        assert result.data_quality == 'insufficient', \
            f"Expected 'insufficient' data quality for {data_points} points, got {result.data_quality}"
        
        # 驗證可靠性為 unreliable
        assert result.reliability == 'unreliable', \
            f"Expected 'unreliable' reliability for {data_points} points, got {result.reliability}"
        
        # 驗證靜態閾值計算正確 (使用新的計算邏輯)
        # 新邏輯: base_iv = max(vix, current_iv * 0.8)
        # high_threshold = base_iv * 1.25
        # low_threshold = max(5.0, base_iv * 0.75)
        base_iv = max(vix, current_iv * 0.8)
        expected_high = base_iv * 1.25
        expected_low = max(5.0, base_iv * 0.75)
        
        assert abs(result.high_threshold - expected_high) < 0.01, \
            f"Expected high threshold {expected_high}, got {result.high_threshold}"
        assert abs(result.low_threshold - expected_low) < 0.01, \
            f"Expected low threshold {expected_low}, got {result.low_threshold}"
    
    @given(
        current_iv=st.floats(min_value=10.0, max_value=80.0, allow_nan=False, allow_infinity=False),
        iv_mean=st.floats(min_value=20.0, max_value=50.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_sufficient_data_uses_dynamic(self, current_iv, iv_mean):
        """
        **Feature: jin-cao-option-enhancements, Property 5: Dynamic Threshold Fallback**
        **Validates: Requirements 13.4**
        
        Property: When historical data has 200+ points, use dynamic thresholds.
        """
        # 生成足夠的歷史數據
        np.random.seed(42)
        historical_iv = np.random.normal(iv_mean, 5, 252)
        historical_iv = np.clip(historical_iv, 5, 150)
        
        result = self.calculator.calculate_thresholds(
            current_iv=current_iv,
            historical_iv=historical_iv
        )
        
        # 驗證使用動態閾值
        assert result.data_quality == 'sufficient', \
            f"Expected 'sufficient' data quality for 252 points, got {result.data_quality}"
        
        # 驗證動態閾值基於百分位數
        expected_high = np.percentile(historical_iv, 75)
        expected_low = np.percentile(historical_iv, 25)
        
        assert abs(result.high_threshold - expected_high) < 0.1, \
            f"Expected high threshold ~{expected_high:.2f}, got {result.high_threshold}"
        assert abs(result.low_threshold - expected_low) < 0.1, \
            f"Expected low threshold ~{expected_low:.2f}, got {result.low_threshold}"


class TestThresholdBounds:
    """
    測試閾值邊界的正確性
    """
    
    def setup_method(self):
        self.calculator = DynamicIVThresholdCalculator()
    
    @given(
        current_iv=st.floats(min_value=5.0, max_value=100.0, allow_nan=False, allow_infinity=False),
        vix=st.floats(min_value=10.0, max_value=50.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_threshold_ordering(self, current_iv, vix):
        """
        Property: Low threshold should always be less than high threshold.
        """
        result = self.calculator.calculate_thresholds(
            current_iv=current_iv,
            historical_iv=None,
            vix=vix
        )
        
        assert result.low_threshold < result.high_threshold, \
            f"Low threshold {result.low_threshold} >= high threshold {result.high_threshold}"
    
    @given(
        current_iv=st.floats(min_value=5.0, max_value=100.0, allow_nan=False, allow_infinity=False),
        vix=st.floats(min_value=10.0, max_value=50.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_low_threshold_minimum(self, current_iv, vix):
        """
        Property: Low threshold should never be below 5%.
        """
        result = self.calculator.calculate_thresholds(
            current_iv=current_iv,
            historical_iv=None,
            vix=vix
        )
        
        assert result.low_threshold >= 5.0, \
            f"Low threshold {result.low_threshold} < 5%"


class TestIVRankDataQualityMarking:
    """
    **Feature: option-calculation-fixes, Property 4: IV Rank 數據質量標記**
    
    測試 IV Rank 數據質量標記的正確性
    **Validates: Requirements 5.2, 5.4**
    """
    
    def setup_method(self):
        self.calculator = DynamicIVThresholdCalculator()
    
    @given(
        current_iv=st.floats(min_value=10.0, max_value=80.0, allow_nan=False, allow_infinity=False),
        data_days=st.integers(min_value=60, max_value=251)
    )
    @settings(max_examples=100)
    def test_limited_data_has_warning(self, current_iv, data_days):
        """
        **Feature: option-calculation-fixes, Property 4: IV Rank 數據質量標記**
        **Validates: Requirements 5.2, 5.4**
        
        Property: When historical data has 60-251 days (less than 252), 
        result should include a data insufficiency warning.
        """
        # 生成指定天數的歷史數據
        np.random.seed(42)
        historical_iv = np.random.normal(30, 5, data_days)
        historical_iv = np.clip(historical_iv, 5, 150)
        
        result = self.calculator.calculate_thresholds(
            current_iv=current_iv,
            historical_iv=historical_iv
        )
        
        # 驗證數據質量為 'limited'
        assert result.data_quality == 'limited', \
            f"Expected 'limited' data quality for {data_days} days, got {result.data_quality}"
        
        # 驗證可靠性為 'moderate'
        assert result.reliability == 'moderate', \
            f"Expected 'moderate' reliability for {data_days} days, got {result.reliability}"
        
        # 驗證包含警告
        assert result.warning is not None, \
            f"Expected warning for {data_days} days (< 252), but warning is None"
        
        # 驗證警告包含天數信息
        assert str(data_days) in result.warning, \
            f"Expected warning to contain '{data_days}', got: {result.warning}"
    
    @given(
        current_iv=st.floats(min_value=10.0, max_value=80.0, allow_nan=False, allow_infinity=False),
        data_days=st.integers(min_value=252, max_value=500)
    )
    @settings(max_examples=100)
    def test_sufficient_data_no_warning(self, current_iv, data_days):
        """
        **Feature: option-calculation-fixes, Property 4: IV Rank 數據質量標記**
        **Validates: Requirements 5.2, 5.4**
        
        Property: When historical data has 252+ days, 
        result should NOT include a data insufficiency warning.
        """
        # 生成指定天數的歷史數據
        np.random.seed(42)
        historical_iv = np.random.normal(30, 5, data_days)
        historical_iv = np.clip(historical_iv, 5, 150)
        
        result = self.calculator.calculate_thresholds(
            current_iv=current_iv,
            historical_iv=historical_iv
        )
        
        # 驗證數據質量為 'sufficient'
        assert result.data_quality == 'sufficient', \
            f"Expected 'sufficient' data quality for {data_days} days, got {result.data_quality}"
        
        # 驗證可靠性為 'reliable'
        assert result.reliability == 'reliable', \
            f"Expected 'reliable' reliability for {data_days} days, got {result.reliability}"
        
        # 驗證沒有警告
        assert result.warning is None, \
            f"Expected no warning for {data_days} days (>= 252), but got: {result.warning}"
    
    @given(
        current_iv=st.floats(min_value=10.0, max_value=80.0, allow_nan=False, allow_infinity=False),
        data_days=st.integers(min_value=0, max_value=59)
    )
    @settings(max_examples=100)
    def test_insufficient_data_unreliable(self, current_iv, data_days):
        """
        **Feature: option-calculation-fixes, Property 4: IV Rank 數據質量標記**
        **Validates: Requirements 5.4**
        
        Property: When historical data has fewer than 60 days, 
        result should be marked as 'unreliable'.
        """
        # 生成指定天數的歷史數據
        if data_days > 0:
            np.random.seed(42)
            historical_iv = np.random.normal(30, 5, data_days)
            historical_iv = np.clip(historical_iv, 5, 150)
        else:
            historical_iv = None
        
        result = self.calculator.calculate_thresholds(
            current_iv=current_iv,
            historical_iv=historical_iv,
            vix=20.0
        )
        
        # 驗證數據質量為 'insufficient'
        assert result.data_quality == 'insufficient', \
            f"Expected 'insufficient' data quality for {data_days} days, got {result.data_quality}"
        
        # 驗證可靠性為 'unreliable'
        assert result.reliability == 'unreliable', \
            f"Expected 'unreliable' reliability for {data_days} days, got {result.reliability}"
        
        # 驗證包含警告
        assert result.warning is not None, \
            f"Expected warning for {data_days} days (< 60), but warning is None"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
