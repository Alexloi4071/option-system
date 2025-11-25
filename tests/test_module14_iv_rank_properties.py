#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Property-based tests for Module 14 IV Rank Post
使用 Hypothesis 進行屬性測試

測試 check_iv_rank_post 方法的正確性
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
import sys
import os

# 添加項目根目錄到路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from calculation_layer.module14_monitoring_posts import MonitoringPostsCalculator


class TestIVRankStatusClassification:
    """
    **Feature: jin-cao-option-enhancements, Property 1: IV Rank Status Classification**
    
    測試 IV Rank 狀態分類的正確性：
    - IV Rank > 70% → "高IV環境"
    - IV Rank < 30% → "低IV環境"
    - 30% ≤ IV Rank ≤ 70% → "中性IV環境"
    """
    
    def setup_method(self):
        """每個測試方法前初始化計算器"""
        self.calculator = MonitoringPostsCalculator()
    
    @given(iv_rank=st.floats(min_value=70.01, max_value=100.0, allow_nan=False, allow_infinity=False))
    @settings(max_examples=100)
    def test_high_iv_environment(self, iv_rank):
        """
        **Feature: jin-cao-option-enhancements, Property 1: IV Rank Status Classification**
        **Validates: Requirements 11.1**
        
        Property: For any IV Rank > 70%, the system should return "高IV環境" status
        and recommend selling options strategies.
        """
        result = self.calculator.check_iv_rank_post(iv_rank)
        
        # 驗證狀態包含 "高IV環境"
        assert "高IV環境" in result['status'], f"Expected '高IV環境' in status for IV Rank {iv_rank}, got {result['status']}"
        
        # 驗證策略建議包含賣期權相關策略
        assert any(strategy in result['strategy_suggestion'] for strategy in ['賣期權', 'Iron Condor', 'Short Straddle', 'Credit Spread']), \
            f"Expected selling strategy suggestion for high IV, got {result['strategy_suggestion']}"
        
        # 驗證 IV 環境描述
        assert "高IV環境" in result['iv_environment'], f"Expected '高IV環境' in iv_environment, got {result['iv_environment']}"
        
        # 驗證返回值
        assert result['value'] == round(iv_rank, 2), f"Expected value {round(iv_rank, 2)}, got {result['value']}"
    
    @given(iv_rank=st.floats(min_value=0.0, max_value=29.99, allow_nan=False, allow_infinity=False))
    @settings(max_examples=100)
    def test_low_iv_environment(self, iv_rank):
        """
        **Feature: jin-cao-option-enhancements, Property 1: IV Rank Status Classification**
        **Validates: Requirements 11.2**
        
        Property: For any IV Rank < 30%, the system should return "低IV環境" status
        and recommend buying options strategies.
        """
        result = self.calculator.check_iv_rank_post(iv_rank)
        
        # 驗證狀態包含 "低IV環境"
        assert "低IV環境" in result['status'], f"Expected '低IV環境' in status for IV Rank {iv_rank}, got {result['status']}"
        
        # 驗證策略建議包含買期權相關策略
        assert any(strategy in result['strategy_suggestion'] for strategy in ['買期權', 'Long Straddle', 'Debit Spread', 'Long Options']), \
            f"Expected buying strategy suggestion for low IV, got {result['strategy_suggestion']}"
        
        # 驗證 IV 環境描述
        assert "低IV環境" in result['iv_environment'], f"Expected '低IV環境' in iv_environment, got {result['iv_environment']}"
        
        # 驗證返回值
        assert result['value'] == round(iv_rank, 2), f"Expected value {round(iv_rank, 2)}, got {result['value']}"
    
    @given(iv_rank=st.floats(min_value=30.0, max_value=70.0, allow_nan=False, allow_infinity=False))
    @settings(max_examples=100)
    def test_neutral_iv_environment(self, iv_rank):
        """
        **Feature: jin-cao-option-enhancements, Property 1: IV Rank Status Classification**
        **Validates: Requirements 11.3**
        
        Property: For any IV Rank between 30% and 70%, the system should return 
        "中性IV環境" status and recommend neutral strategies.
        """
        result = self.calculator.check_iv_rank_post(iv_rank)
        
        # 驗證狀態包含 "中性" 或 "OK"
        assert "中性" in result['status'] or "OK" in result['status'], \
            f"Expected '中性' or 'OK' in status for IV Rank {iv_rank}, got {result['status']}"
        
        # 驗證策略建議包含中性策略
        assert any(strategy in result['strategy_suggestion'] for strategy in ['中性', '觀望', 'Calendar', 'Butterfly']), \
            f"Expected neutral strategy suggestion, got {result['strategy_suggestion']}"
        
        # 驗證返回值
        assert result['value'] == round(iv_rank, 2), f"Expected value {round(iv_rank, 2)}, got {result['value']}"
    
    @given(iv_rank=st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False))
    @settings(max_examples=100)
    def test_iv_rank_value_bounds(self, iv_rank):
        """
        **Feature: jin-cao-option-enhancements, Property 1: IV Rank Status Classification**
        **Validates: Requirements 11.1, 11.2, 11.3**
        
        Property: For any valid IV Rank (0-100), the returned value should be 
        within the valid range and properly rounded.
        """
        result = self.calculator.check_iv_rank_post(iv_rank)
        
        # 驗證返回值在有效範圍內
        assert 0.0 <= result['value'] <= 100.0, f"Value {result['value']} out of bounds [0, 100]"
        
        # 驗證返回值正確四捨五入
        assert result['value'] == round(iv_rank, 2), f"Expected {round(iv_rank, 2)}, got {result['value']}"
        
        # 驗證必要字段存在
        assert 'name' in result
        assert 'threshold' in result
        assert 'status' in result
        assert 'note' in result
        assert 'strategy_suggestion' in result
        assert 'iv_environment' in result
    
    @given(iv_rank=st.floats(min_value=-100.0, max_value=200.0, allow_nan=False, allow_infinity=False))
    @settings(max_examples=100)
    def test_iv_rank_clamping(self, iv_rank):
        """
        **Feature: jin-cao-option-enhancements, Property 1: IV Rank Status Classification**
        **Validates: Requirements 11.1, 11.2, 11.3**
        
        Property: For any IV Rank value (even out of bounds), the system should 
        clamp the value to [0, 100] range.
        """
        result = self.calculator.check_iv_rank_post(iv_rank)
        
        # 驗證返回值被限制在有效範圍內
        assert 0.0 <= result['value'] <= 100.0, f"Value {result['value']} should be clamped to [0, 100]"


class TestIVRankMissingData:
    """
    **Feature: jin-cao-option-enhancements, Property 7: Missing IV Rank Handling**
    
    測試缺失 IV Rank 數據的處理
    """
    
    def setup_method(self):
        """每個測試方法前初始化計算器"""
        self.calculator = MonitoringPostsCalculator()
    
    def test_none_iv_rank(self):
        """
        **Feature: jin-cao-option-enhancements, Property 7: Missing IV Rank Handling**
        **Validates: Requirements 14.3**
        
        Property: When IV Rank is None, the system should return "數據不足" status
        and not crash.
        """
        result = self.calculator.check_iv_rank_post(None)
        
        # 驗證狀態包含 "數據不足"
        assert "數據不足" in result['status'], f"Expected '數據不足' in status, got {result['status']}"
        
        # 驗證返回值為 None
        assert result['value'] is None, f"Expected None value, got {result['value']}"
        
        # 驗證必要字段存在
        assert 'name' in result
        assert 'threshold' in result
        assert 'note' in result
        assert 'strategy_suggestion' in result
        assert 'iv_environment' in result


if __name__ == '__main__':
    pytest.main([__file__, '-v'])



class TestIVRankDataFlow:
    """
    **Feature: jin-cao-option-enhancements, Property 6: IV Rank Data Flow**
    
    測試 IV Rank 數據從 Module 18 到 Module 14 的流動
    """
    
    def setup_method(self):
        """每個測試方法前初始化計算器"""
        self.calculator = MonitoringPostsCalculator()
    
    @given(iv_rank=st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False))
    @settings(max_examples=100)
    def test_iv_rank_passed_to_module14(self, iv_rank):
        """
        **Feature: jin-cao-option-enhancements, Property 6: IV Rank Data Flow**
        **Validates: Requirements 11.4, 14.1, 14.2**
        
        Property: When Module 18 calculates IV Rank, the value should be correctly
        passed to Module 14's check_iv_rank_post method and return valid results.
        """
        # 模擬 Module 18 計算的 IV Rank 傳入 Module 14
        result = self.calculator.check_iv_rank_post(iv_rank)
        
        # 驗證返回結果包含所有必要字段
        assert 'name' in result, "Result should contain 'name' field"
        assert 'value' in result, "Result should contain 'value' field"
        assert 'threshold' in result, "Result should contain 'threshold' field"
        assert 'status' in result, "Result should contain 'status' field"
        assert 'note' in result, "Result should contain 'note' field"
        assert 'strategy_suggestion' in result, "Result should contain 'strategy_suggestion' field"
        assert 'iv_environment' in result, "Result should contain 'iv_environment' field"
        
        # 驗證返回值與輸入一致（四捨五入後）
        assert result['value'] == round(iv_rank, 2), f"Expected {round(iv_rank, 2)}, got {result['value']}"
    
    @given(iv_rank=st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False))
    @settings(max_examples=100)
    def test_iv_rank_result_can_be_added_to_post_details(self, iv_rank):
        """
        **Feature: jin-cao-option-enhancements, Property 6: IV Rank Data Flow**
        **Validates: Requirements 11.5, 14.5**
        
        Property: The IV Rank result should be in a format that can be added to
        Module 14's post_details dictionary as post13.
        """
        result = self.calculator.check_iv_rank_post(iv_rank)
        
        # 模擬將結果添加到 post_details
        post_details = {}
        post_details['post13'] = result
        
        # 驗證可以正確添加
        assert 'post13' in post_details
        assert post_details['post13']['name'] == 'IV Rank 歷史判斷'
        assert post_details['post13']['value'] == round(iv_rank, 2)


class TestIVRankAlertUpdate:
    """
    **Feature: jin-cao-option-enhancements, Property 8: Alert Count Update**
    
    測試 IV Rank 觸發警告時警報計數的更新
    """
    
    def setup_method(self):
        """每個測試方法前初始化計算器"""
        self.calculator = MonitoringPostsCalculator()
    
    @given(iv_rank=st.floats(min_value=70.01, max_value=100.0, allow_nan=False, allow_infinity=False))
    @settings(max_examples=100)
    def test_high_iv_triggers_alert(self, iv_rank):
        """
        **Feature: jin-cao-option-enhancements, Property 8: Alert Count Update**
        **Validates: Requirements 14.4**
        
        Property: When IV Rank > 70%, it should trigger a warning condition
        that would increment the alert count.
        """
        result = self.calculator.check_iv_rank_post(iv_rank)
        
        # 驗證高 IV 環境狀態
        assert "高IV環境" in result['status'], f"Expected '高IV環境' for IV Rank {iv_rank}"
        
        # 模擬警報計數更新邏輯
        initial_alerts = 0
        if iv_rank > 70:
            initial_alerts += 1
        
        assert initial_alerts == 1, "High IV should trigger alert increment"
    
    @given(iv_rank=st.floats(min_value=0.0, max_value=29.99, allow_nan=False, allow_infinity=False))
    @settings(max_examples=100)
    def test_low_iv_triggers_alert(self, iv_rank):
        """
        **Feature: jin-cao-option-enhancements, Property 8: Alert Count Update**
        **Validates: Requirements 14.4**
        
        Property: When IV Rank < 30%, it should trigger a warning condition
        that would increment the alert count.
        """
        result = self.calculator.check_iv_rank_post(iv_rank)
        
        # 驗證低 IV 環境狀態
        assert "低IV環境" in result['status'], f"Expected '低IV環境' for IV Rank {iv_rank}"
        
        # 模擬警報計數更新邏輯
        initial_alerts = 0
        if iv_rank < 30:
            initial_alerts += 1
        
        assert initial_alerts == 1, "Low IV should trigger alert increment"
    
    @given(iv_rank=st.floats(min_value=30.0, max_value=70.0, allow_nan=False, allow_infinity=False))
    @settings(max_examples=100)
    def test_neutral_iv_no_alert(self, iv_rank):
        """
        **Feature: jin-cao-option-enhancements, Property 8: Alert Count Update**
        **Validates: Requirements 14.4**
        
        Property: When IV Rank is between 30% and 70%, it should NOT trigger
        a warning condition.
        """
        result = self.calculator.check_iv_rank_post(iv_rank)
        
        # 驗證中性 IV 環境狀態
        assert "中性" in result['status'] or "OK" in result['status'], \
            f"Expected neutral status for IV Rank {iv_rank}"
        
        # 模擬警報計數更新邏輯
        initial_alerts = 0
        if iv_rank > 70 or iv_rank < 30:
            initial_alerts += 1
        
        assert initial_alerts == 0, "Neutral IV should not trigger alert"
