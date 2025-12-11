#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Property-based tests for RSI Interpretation
使用 Hypothesis 進行屬性測試

**Feature: report-improvements, Property 2: RSI 解讀一致性**
**Validates: Requirements 3.2, 3.3, 3.4**

測試 _get_rsi_interpretation 方法的正確性：
- RSI > 70 → "超買"
- RSI < 30 → "超賣"
- 30 ≤ RSI ≤ 70 → "中性"
"""

import pytest
from hypothesis import given, strategies as st, settings
import sys
import os

# 添加項目根目錄到路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from output_layer.report_generator import ReportGenerator


class TestRSIInterpretationConsistency:
    """
    **Feature: report-improvements, Property 2: RSI 解讀一致性**
    **Validates: Requirements 3.2, 3.3, 3.4**
    
    測試 RSI 解讀的一致性：
    - RSI > 70 時輸出應包含「超買」
    - RSI < 30 時輸出應包含「超賣」
    - 30 ≤ RSI ≤ 70 時輸出應包含「中性」
    """
    
    def setup_method(self):
        """每個測試方法前初始化報告生成器"""
        self.generator = ReportGenerator()
    
    @given(rsi=st.floats(min_value=70.01, max_value=100.0, allow_nan=False, allow_infinity=False))
    @settings(max_examples=100)
    def test_rsi_overbought_interpretation(self, rsi):
        """
        **Feature: report-improvements, Property 2: RSI 解讀一致性**
        **Validates: Requirements 3.2**
        
        Property: For any RSI > 70, the interpretation should contain "超買"
        and suggest possible pullback.
        """
        result = self.generator._get_rsi_interpretation(rsi)
        
        # 驗證狀態為「超買」
        assert result['status'] == '超買', \
            f"Expected '超買' for RSI {rsi}, got {result['status']}"
        
        # 驗證描述包含「超買」
        assert '超買' in result['description'], \
            f"Expected '超買' in description for RSI {rsi}, got {result['description']}"
        
        # 驗證建議包含回調相關提示
        assert '回調' in result['action_hint'] or '謹慎' in result['action_hint'], \
            f"Expected pullback warning for RSI {rsi}, got {result['action_hint']}"
    
    @given(rsi=st.floats(min_value=0.0, max_value=29.99, allow_nan=False, allow_infinity=False))
    @settings(max_examples=100)
    def test_rsi_oversold_interpretation(self, rsi):
        """
        **Feature: report-improvements, Property 2: RSI 解讀一致性**
        **Validates: Requirements 3.3**
        
        Property: For any RSI < 30, the interpretation should contain "超賣"
        and suggest possible rebound.
        """
        result = self.generator._get_rsi_interpretation(rsi)
        
        # 驗證狀態為「超賣」
        assert result['status'] == '超賣', \
            f"Expected '超賣' for RSI {rsi}, got {result['status']}"
        
        # 驗證描述包含「超賣」
        assert '超賣' in result['description'], \
            f"Expected '超賣' in description for RSI {rsi}, got {result['description']}"
        
        # 驗證建議包含反彈相關提示
        assert '反彈' in result['action_hint'] or '買入' in result['action_hint'], \
            f"Expected rebound hint for RSI {rsi}, got {result['action_hint']}"
    
    @given(rsi=st.floats(min_value=30.0, max_value=70.0, allow_nan=False, allow_infinity=False))
    @settings(max_examples=100)
    def test_rsi_neutral_interpretation(self, rsi):
        """
        **Feature: report-improvements, Property 2: RSI 解讀一致性**
        **Validates: Requirements 3.4**
        
        Property: For any RSI between 30 and 70, the interpretation should 
        contain "中性".
        """
        result = self.generator._get_rsi_interpretation(rsi)
        
        # 驗證狀態為「中性」
        assert result['status'] == '中性', \
            f"Expected '中性' for RSI {rsi}, got {result['status']}"
        
        # 驗證描述包含正常範圍說明
        assert '30-70' in result['description'] or '正常' in result['description'], \
            f"Expected normal range description for RSI {rsi}, got {result['description']}"
    
    @given(rsi=st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False))
    @settings(max_examples=100)
    def test_rsi_interpretation_completeness(self, rsi):
        """
        **Feature: report-improvements, Property 2: RSI 解讀一致性**
        **Validates: Requirements 3.2, 3.3, 3.4**
        
        Property: For any valid RSI value, the interpretation should contain
        all required fields: status, description, and action_hint.
        """
        result = self.generator._get_rsi_interpretation(rsi)
        
        # 驗證所有必要字段存在
        assert 'status' in result, "Result should contain 'status' field"
        assert 'description' in result, "Result should contain 'description' field"
        assert 'action_hint' in result, "Result should contain 'action_hint' field"
        
        # 驗證字段不為空
        assert result['status'], "Status should not be empty"
        assert result['description'], "Description should not be empty"
        assert result['action_hint'], "Action hint should not be empty"
        
        # 驗證狀態是三種之一
        assert result['status'] in ['超買', '超賣', '中性'], \
            f"Status should be one of ['超買', '超賣', '中性'], got {result['status']}"
    
    def test_rsi_none_handling(self):
        """
        **Feature: report-improvements, Property 2: RSI 解讀一致性**
        **Validates: Requirements 3.2, 3.3, 3.4**
        
        Property: When RSI is None, the interpretation should indicate
        data unavailability.
        """
        result = self.generator._get_rsi_interpretation(None)
        
        # 驗證狀態表示數據不可用
        assert '數據不可用' in result['status'], \
            f"Expected '數據不可用' for None RSI, got {result['status']}"
        
        # 驗證所有字段存在
        assert 'status' in result
        assert 'description' in result
        assert 'action_hint' in result


class TestRSIInterpretationBoundaries:
    """
    測試 RSI 解讀的邊界條件
    """
    
    def setup_method(self):
        """每個測試方法前初始化報告生成器"""
        self.generator = ReportGenerator()
    
    def test_rsi_exactly_70(self):
        """
        Test RSI exactly at 70 (boundary between neutral and overbought)
        """
        result = self.generator._get_rsi_interpretation(70.0)
        
        # RSI = 70 應該是中性（不超過70）
        assert result['status'] == '中性', \
            f"Expected '中性' for RSI 70, got {result['status']}"
    
    def test_rsi_exactly_30(self):
        """
        Test RSI exactly at 30 (boundary between oversold and neutral)
        """
        result = self.generator._get_rsi_interpretation(30.0)
        
        # RSI = 30 應該是中性（不低於30）
        assert result['status'] == '中性', \
            f"Expected '中性' for RSI 30, got {result['status']}"
    
    def test_rsi_just_above_70(self):
        """
        Test RSI just above 70
        """
        result = self.generator._get_rsi_interpretation(70.01)
        
        assert result['status'] == '超買', \
            f"Expected '超買' for RSI 70.01, got {result['status']}"
    
    def test_rsi_just_below_30(self):
        """
        Test RSI just below 30
        """
        result = self.generator._get_rsi_interpretation(29.99)
        
        assert result['status'] == '超賣', \
            f"Expected '超賣' for RSI 29.99, got {result['status']}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
