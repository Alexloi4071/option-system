#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Finviz 錯誤處理測試

測試 Finviz 部分數據可用時的優雅處理和關鍵字段補充。

**Feature: data-sources-enhancement**
**Property 4: Finviz Partial Data Handling**
**Property 6: Critical Field Supplementation**
**Validates: Requirements 4.1, 4.2, 4.3**
"""

import pytest
import sys
import os
from unittest import mock

# 添加項目根目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_layer.data_fetcher import DataFetcher


class TestFinvizErrorHandling:
    """測試 Finviz 錯誤處理"""
    
    @pytest.fixture
    def fetcher(self):
        """創建 DataFetcher 實例"""
        return DataFetcher(use_ibkr=False)
    
    def test_complete_finviz_data(self, fetcher):
        """測試完整的 Finviz 數據"""
        complete_data = {
            'price': 150.25,
            'eps_ttm': 6.15,
            'pe': 24.43,
            'forward_pe': 22.5,
            'peg': 2.1,
            'market_cap': 2500000000000,
            'volume': 50000000,
            'dividend_yield': 0.5,
            'beta': 1.2,
            'atr': 3.5,
            'rsi': 55.0,
            'company_name': 'Apple Inc.',
            'sector': 'Technology',
            'industry': 'Consumer Electronics',
            'target_price': 180.0,
            'profit_margin': 25.0,
            'operating_margin': 30.0,
            'roe': 150.0,
            'roa': 20.0,
            'debt_eq': 1.5,
            'insider_own': 0.1,
            'inst_own': 60.0,
            'short_float': 1.0,
            'avg_volume': 55000000,
            'eps_next_y': 7.0
        }
        
        result = fetcher._validate_and_supplement_finviz_data(complete_data, 'AAPL')
        
        assert result is not None
        assert result['data_quality'] == 'complete'
        assert len(result['supplemented_fields']) == 0

    def test_partial_finviz_data(self, fetcher):
        """
        測試部分數據可用時的優雅處理
        
        **Property 4: Finviz Partial Data Handling**
        """
        partial_data = {
            'price': 150.25,
            'eps_ttm': 6.15,
            'pe': 24.43,
            # 缺少很多非關鍵字段
            'company_name': 'Apple Inc.',
            'sector': 'Technology'
        }
        
        result = fetcher._validate_and_supplement_finviz_data(partial_data, 'AAPL')
        
        assert result is not None
        assert result['data_quality'] in ['partial', 'minimal']
        assert len(result['missing_fields']) > 0
        # 關鍵字段都存在，不需要補充
        assert len(result['supplemented_fields']) == 0
    
    def test_missing_critical_fields_supplementation(self, fetcher):
        """
        測試關鍵字段缺失時的補充邏輯
        
        **Property 6: Critical Field Supplementation**
        """
        # 缺少關鍵字段的數據
        incomplete_data = {
            # 缺少 price, eps_ttm, pe
            'company_name': 'Apple Inc.',
            'sector': 'Technology'
        }
        
        # 模擬 yfinance 補充數據
        mock_info = {
            'currentPrice': 150.25,
            'trailingEps': 6.15,
            'trailingPE': 24.43
        }
        
        with mock.patch('yfinance.Ticker') as mock_ticker:
            mock_ticker.return_value.info = mock_info
            
            result = fetcher._validate_and_supplement_finviz_data(incomplete_data, 'AAPL')
        
        assert result is not None
        assert result['price'] == 150.25
        assert result['eps_ttm'] == 6.15
        assert result['pe'] == 24.43
        assert 'price' in result['supplemented_fields']
        assert 'eps_ttm' in result['supplemented_fields']
        assert 'pe' in result['supplemented_fields']
        assert result['data_source'] == 'Finviz+yfinance'
    
    def test_missing_critical_fields_no_supplement(self, fetcher):
        """測試關鍵字段缺失且無法補充時返回 None"""
        incomplete_data = {
            'company_name': 'Apple Inc.'
        }
        
        # 模擬 yfinance 也無法提供數據
        with mock.patch('yfinance.Ticker', side_effect=Exception("Network Error")):
            result = fetcher._validate_and_supplement_finviz_data(incomplete_data, 'AAPL')
        
        # 應該返回 None（驗證失敗）
        assert result is None
    
    def test_data_quality_assessment(self, fetcher):
        """測試數據質量評估"""
        # 測試 minimal 質量
        minimal_data = {
            'price': 150.25,
            'eps_ttm': 6.15,
            'pe': 24.43
        }
        result = fetcher._validate_and_supplement_finviz_data(minimal_data, 'AAPL')
        assert result is not None
        assert result['data_quality'] == 'minimal'
        
        # 測試 partial 質量（60-90% 字段）
        partial_data = {
            'price': 150.25,
            'eps_ttm': 6.15,
            'pe': 24.43,
            'forward_pe': 22.5,
            'peg': 2.1,
            'market_cap': 2500000000000,
            'volume': 50000000,
            'dividend_yield': 0.5,
            'beta': 1.2,
            'atr': 3.5,
            'rsi': 55.0,
            'company_name': 'Apple Inc.',
            'sector': 'Technology',
            'industry': 'Consumer Electronics',
            'target_price': 180.0,
            'profit_margin': 25.0,
            'operating_margin': 30.0,
            'roe': 150.0
            # 缺少一些字段
        }
        result = fetcher._validate_and_supplement_finviz_data(partial_data, 'AAPL')
        assert result is not None
        assert result['data_quality'] in ['partial', 'complete']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
