#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Property-based tests for Volatility Smile Market Sentiment (Report Improvements)
使用 Hypothesis 進行屬性測試

**Feature: report-improvements, Property 9: 波動率微笑市場情緒**
**Validates: Requirements 13.2, 13.3**

測試波動率微笑分析的市場情緒判斷:
- Skew < 0 時應解釋為看漲傾向
- Skew > 0 時應解釋為看跌傾向
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
import sys
import os

# 添加項目根目錄到路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from output_layer.report_generator import ReportGenerator


class TestVolatilitySmileSentiment:
    """
    **Feature: report-improvements, Property 9: 波動率微笑市場情緒**
    **Validates: Requirements 13.2, 13.3**
    
    測試波動率微笑的市場情緒判斷
    """
    
    def setup_method(self):
        self.report_generator = ReportGenerator()
    
    @given(
        skew=st.floats(min_value=-20.0, max_value=-1.1, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_negative_skew_indicates_bullish_sentiment(self, skew):
        """
        **Feature: report-improvements, Property 9: 波動率微笑市場情緒**
        **Validates: Requirements 13.3**
        
        Property: For any Skew < -1%, the market sentiment should indicate bullish tendency
        (看漲傾向), because OTM Call IV > OTM Put IV means market expects upside risk.
        """
        # 使用任意有效的 smile_shape
        smile_shape = 'call_skew'
        
        sentiment = self.report_generator._get_volatility_smile_sentiment(skew, smile_shape)
        
        # 驗證情緒判斷為看漲
        assert sentiment['sentiment'] == '看漲', \
            f"Expected '看漲' for negative skew {skew}, got '{sentiment['sentiment']}'"
    
    @given(
        skew=st.floats(min_value=1.1, max_value=20.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_positive_skew_indicates_bearish_sentiment(self, skew):
        """
        **Feature: report-improvements, Property 9: 波動率微笑市場情緒**
        **Validates: Requirements 13.2**
        
        Property: For any Skew > 1%, the market sentiment should indicate bearish tendency
        (看跌傾向), because OTM Put IV > OTM Call IV means market expects downside risk.
        """
        # 使用任意有效的 smile_shape
        smile_shape = 'put_skew'
        
        sentiment = self.report_generator._get_volatility_smile_sentiment(skew, smile_shape)
        
        # 驗證情緒判斷為看跌
        assert sentiment['sentiment'] == '看跌', \
            f"Expected '看跌' for positive skew {skew}, got '{sentiment['sentiment']}'"
    
    @given(
        skew=st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_near_zero_skew_indicates_neutral_sentiment(self, skew):
        """
        **Feature: report-improvements, Property 9: 波動率微笑市場情緒**
        **Validates: Requirements 13.2, 13.3**
        
        Property: For any Skew between -1% and 1%, the market sentiment should be neutral
        (中性), indicating no clear directional bias.
        """
        smile_shape = 'symmetric'
        
        sentiment = self.report_generator._get_volatility_smile_sentiment(skew, smile_shape)
        
        # 驗證情緒判斷為中性
        assert sentiment['sentiment'] == '中性', \
            f"Expected '中性' for near-zero skew {skew}, got '{sentiment['sentiment']}'"
    
    def test_unknown_shape_returns_neutral_with_low_confidence(self):
        """
        **Feature: report-improvements, Property 9: 波動率微笑市場情緒**
        **Validates: Requirements 13.1**
        
        Property: When smile shape is 'unknown', sentiment should be neutral with low confidence.
        """
        sentiment = self.report_generator._get_volatility_smile_sentiment(0.0, 'unknown')
        
        assert '中性' in sentiment['sentiment'], \
            f"Expected '中性' for unknown shape, got '{sentiment['sentiment']}'"
        assert sentiment['confidence'] == '低', \
            f"Expected '低' confidence for unknown shape, got '{sentiment['confidence']}'"


class TestSkewInterpretation:
    """
    **Feature: report-improvements, Property 9: 波動率微笑市場情緒**
    **Validates: Requirements 13.2, 13.3**
    
    測試 Skew 值的解釋
    """
    
    def setup_method(self):
        self.report_generator = ReportGenerator()
    
    @given(
        skew=st.floats(min_value=1.1, max_value=20.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_positive_skew_interpretation_mentions_downside_risk(self, skew):
        """
        **Feature: report-improvements, Property 9: 波動率微笑市場情緒**
        **Validates: Requirements 13.2**
        
        Property: For any positive Skew > 1%, the interpretation should mention
        that market expects downside risk (下跌風險).
        """
        interpretation = self.report_generator._get_skew_interpretation(skew)
        
        # 將解釋列表合併為字符串進行檢查
        interpretation_text = ' '.join(interpretation)
        
        # 驗證解釋中包含下跌風險相關內容
        assert '下跌' in interpretation_text or '正值' in interpretation_text, \
            f"Expected interpretation to mention downside risk for positive skew {skew}, got: {interpretation_text}"
    
    @given(
        skew=st.floats(min_value=-20.0, max_value=-1.1, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_negative_skew_interpretation_mentions_upside_risk(self, skew):
        """
        **Feature: report-improvements, Property 9: 波動率微笑市場情緒**
        **Validates: Requirements 13.3**
        
        Property: For any negative Skew < -1%, the interpretation should mention
        that market expects upside risk (上漲風險).
        """
        interpretation = self.report_generator._get_skew_interpretation(skew)
        
        # 將解釋列表合併為字符串進行檢查
        interpretation_text = ' '.join(interpretation)
        
        # 驗證解釋中包含上漲風險相關內容
        assert '上漲' in interpretation_text or '負值' in interpretation_text, \
            f"Expected interpretation to mention upside risk for negative skew {skew}, got: {interpretation_text}"


class TestSmileTradingImplications:
    """
    **Feature: report-improvements, Property 9: 波動率微笑市場情緒**
    **Validates: Requirements 13.4**
    
    測試微笑形狀的交易含義
    """
    
    def setup_method(self):
        self.report_generator = ReportGenerator()
    
    @given(
        skew=st.floats(min_value=-10.0, max_value=10.0, allow_nan=False, allow_infinity=False),
        atm_iv=st.floats(min_value=10.0, max_value=100.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_trading_implications_returns_non_empty_list(self, skew, atm_iv):
        """
        **Feature: report-improvements, Property 9: 波動率微笑市場情緒**
        **Validates: Requirements 13.4**
        
        Property: For any valid smile shape, skew, and ATM IV, the trading implications
        should return a non-empty list of suggestions.
        """
        for smile_shape in ['put_skew', 'call_skew', 'symmetric', 'unknown']:
            implications = self.report_generator._get_smile_trading_implications(
                smile_shape, skew, atm_iv
            )
            
            assert isinstance(implications, list), \
                f"Expected list, got {type(implications)}"
            assert len(implications) > 0, \
                f"Expected non-empty list for shape '{smile_shape}'"
    
    def test_put_skew_suggests_put_strategies(self):
        """
        **Feature: report-improvements, Property 9: 波動率微笑市場情緒**
        **Validates: Requirements 13.4**
        
        Property: For put_skew shape, trading implications should mention Put strategies.
        """
        implications = self.report_generator._get_smile_trading_implications(
            'put_skew', 5.0, 30.0
        )
        
        implications_text = ' '.join(implications)
        
        assert 'Put' in implications_text, \
            f"Expected Put strategies for put_skew, got: {implications_text}"
    
    def test_call_skew_suggests_call_strategies(self):
        """
        **Feature: report-improvements, Property 9: 波動率微笑市場情緒**
        **Validates: Requirements 13.4**
        
        Property: For call_skew shape, trading implications should mention Call strategies.
        """
        implications = self.report_generator._get_smile_trading_implications(
            'call_skew', -5.0, 30.0
        )
        
        implications_text = ' '.join(implications)
        
        assert 'Call' in implications_text, \
            f"Expected Call strategies for call_skew, got: {implications_text}"


class TestVolatilitySmileFormatOutput:
    """
    **Feature: report-improvements, Property 9: 波動率微笑市場情緒**
    **Validates: Requirements 13.1, 13.2, 13.3, 13.4**
    
    測試完整的波動率微笑格式化輸出
    """
    
    def setup_method(self):
        self.report_generator = ReportGenerator()
    
    @given(
        skew=st.floats(min_value=-15.0, max_value=15.0, allow_nan=False, allow_infinity=False),
        atm_iv=st.floats(min_value=10.0, max_value=80.0, allow_nan=False, allow_infinity=False),
        current_price=st.floats(min_value=20.0, max_value=500.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_format_volatility_smile_contains_all_sections(self, skew, atm_iv, current_price):
        """
        **Feature: report-improvements, Property 9: 波動率微笑市場情緒**
        **Validates: Requirements 13.1, 13.2, 13.3, 13.4**
        
        Property: For any valid smile data, the formatted output should contain:
        - Market sentiment summary (市場情緒總結)
        - Skew interpretation (Skew 解讀)
        - Trading implications (交易含義)
        """
        # 根據 skew 決定 smile_shape
        if skew > 2.0:
            smile_shape = 'put_skew'
        elif skew < -2.0:
            smile_shape = 'call_skew'
        else:
            smile_shape = 'symmetric'
        
        smile_data = {
            'atm_iv': atm_iv,
            'atm_strike': current_price,
            'skew': skew,
            'smile_shape': smile_shape,
            'skew_25delta': skew * 0.8,  # 模擬 25-delta skew
            'current_price': current_price
        }
        
        output = self.report_generator._format_volatility_smile(smile_data)
        
        # 驗證輸出包含市場情緒總結
        assert '市場情緒總結' in output, \
            f"Expected '市場情緒總結' in output, got: {output[:200]}..."
        
        # 驗證輸出包含 Skew 解讀
        assert 'Skew 解讀' in output, \
            f"Expected 'Skew 解讀' in output, got: {output[:200]}..."
        
        # 驗證輸出包含交易含義
        assert '交易含義' in output, \
            f"Expected '交易含義' in output, got: {output[:200]}..."
        
        # 驗證輸出包含情緒判斷（看漲/看跌/中性）
        assert any(sentiment in output for sentiment in ['看漲', '看跌', '中性']), \
            f"Expected sentiment indicator in output, got: {output[:200]}..."


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
