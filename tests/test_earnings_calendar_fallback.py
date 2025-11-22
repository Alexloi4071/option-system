#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
業績日曆降級策略測試

測試 Finnhub → yfinance → 歷史推測的完整降級鏈。

**Feature: data-sources-enhancement, Property 1: Earnings Calendar Fallback Chain Completeness**
**Validates: Requirements 1.1, 1.3, 1.5**
"""

import pytest
import sys
import os
from unittest import mock
from datetime import datetime, timedelta
import pandas as pd

# 添加項目根目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_layer.data_fetcher import DataFetcher


class TestEarningsCalendarFallback:
    """測試業績日曆降級策略"""
    
    @pytest.fixture
    def fetcher(self):
        """創建 DataFetcher 實例（不使用 IBKR）"""
        return DataFetcher(use_ibkr=False)
    
    def test_finnhub_success(self, fetcher):
        """測試 Finnhub 成功獲取業績日期"""
        # 模擬 Finnhub 成功響應
        mock_response = {
            'earningsCalendar': [{
                'date': '2025-01-15',
                'hour': 'amc',
                'epsEstimate': 1.25,
                'revenueEstimate': 50000000000
            }]
        }
        
        with mock.patch.object(
            fetcher.finnhub_client,
            'earnings_calendar',
            return_value=mock_response
        ):
            result = fetcher.get_earnings_calendar('AAPL')
        
        assert result is not None
        assert result['next_earnings_date'] == '2025-01-15'
        assert result['earnings_call_time'] == 'amc'
        assert result['data_source'] == 'finnhub'
        assert result['is_estimated'] is False
        assert result['confidence'] == 'high'
    
    def test_finnhub_failure_yfinance_success(self, fetcher):
        """
        測試 Finnhub 失敗時降級到 yfinance
        
        **Property 1: Earnings Calendar Fallback Chain Completeness**
        """
        # 模擬 Finnhub 失敗
        with mock.patch.object(
            fetcher.finnhub_client,
            'earnings_calendar',
            side_effect=Exception("API Error")
        ):
            # 模擬 yfinance 成功
            mock_calendar = pd.DataFrame({
                'Earnings Date': [pd.Timestamp('2025-01-20')]
            }).T
            
            with mock.patch('yfinance.Ticker') as mock_ticker:
                mock_ticker.return_value.calendar = mock_calendar
                
                result = fetcher.get_earnings_calendar('AAPL')
        
        assert result is not None
        assert result['next_earnings_date'] == '2025-01-20'
        assert result['data_source'] == 'yfinance'
        assert result['is_estimated'] is False
        assert result['confidence'] == 'medium'

    def test_finnhub_and_yfinance_failure_estimation_success(self, fetcher):
        """
        測試 Finnhub 和 yfinance 都失敗時使用歷史推測
        
        **Property 1: Earnings Calendar Fallback Chain Completeness**
        """
        # 模擬 Finnhub 失敗
        with mock.patch.object(
            fetcher.finnhub_client,
            'earnings_calendar',
            side_effect=Exception("API Error")
        ):
            # 模擬 yfinance calendar 失敗
            with mock.patch('yfinance.Ticker') as mock_ticker:
                mock_ticker.return_value.calendar = None
                
                # 模擬 yfinance earnings_dates 成功（用於推測）
                mock_earnings_dates = pd.DatetimeIndex([
                    pd.Timestamp('2024-10-15'),
                    pd.Timestamp('2024-07-15')
                ])
                mock_ticker.return_value.earnings_dates = pd.DataFrame(
                    index=mock_earnings_dates
                )
                
                result = fetcher.get_earnings_calendar('AAPL')
        
        assert result is not None
        assert result['data_source'] == 'estimated'
        assert result['is_estimated'] is True
        assert result['confidence'] == 'low'
        # 驗證日期格式
        assert len(result['next_earnings_date']) == 10  # YYYY-MM-DD
        assert result['next_earnings_date'].count('-') == 2
    
    def test_all_sources_fail_returns_none(self, fetcher):
        """
        測試所有數據源都失敗時返回 None（而非拋出異常）
        
        **Property 1: Earnings Calendar Fallback Chain Completeness**
        """
        # 模擬 Finnhub 失敗
        with mock.patch.object(
            fetcher.finnhub_client,
            'earnings_calendar',
            side_effect=Exception("API Error")
        ):
            # 模擬 yfinance 完全失敗
            with mock.patch('yfinance.Ticker', side_effect=Exception("Network Error")):
                # 不應該拋出異常，應該返回 None
                result = fetcher.get_earnings_calendar('AAPL')
        
        assert result is None
    
    def test_finnhub_empty_calendar(self, fetcher):
        """測試 Finnhub 返回空日曆時的降級"""
        # 模擬 Finnhub 返回空日曆
        mock_response = {
            'earningsCalendar': []
        }
        
        with mock.patch.object(
            fetcher.finnhub_client,
            'earnings_calendar',
            return_value=mock_response
        ):
            # 模擬 yfinance 成功
            mock_calendar = pd.DataFrame({
                'Earnings Date': [pd.Timestamp('2025-01-25')]
            }).T
            
            with mock.patch('yfinance.Ticker') as mock_ticker:
                mock_ticker.return_value.calendar = mock_calendar
                
                result = fetcher.get_earnings_calendar('AAPL')
        
        # 應該降級到 yfinance
        assert result is not None
        assert result['data_source'] == 'yfinance'
    
    def test_estimation_with_recent_earnings(self, fetcher):
        """測試基於最近業績日期的推測"""
        # 模擬所有 API 失敗，只有歷史數據可用
        with mock.patch.object(
            fetcher.finnhub_client,
            'earnings_calendar',
            side_effect=Exception("API Error")
        ):
            with mock.patch('yfinance.Ticker') as mock_ticker:
                # calendar 不可用
                mock_ticker.return_value.calendar = None
                
                # 提供最近的業績日期（30天前）
                recent_date = datetime.now() - timedelta(days=30)
                mock_earnings_dates = pd.DatetimeIndex([recent_date])
                mock_ticker.return_value.earnings_dates = pd.DataFrame(
                    index=mock_earnings_dates
                )
                
                result = fetcher.get_earnings_calendar('AAPL')
        
        assert result is not None
        assert result['is_estimated'] is True
        
        # 驗證推測日期在合理範圍內（應該在未來 60-90 天）
        estimated_date = datetime.strptime(result['next_earnings_date'], '%Y-%m-%d')
        days_until = (estimated_date - datetime.now()).days
        assert 0 < days_until <= 90
    
    def test_estimation_with_old_earnings(self, fetcher):
        """測試基於較舊業績日期的推測"""
        # 模擬所有 API 失敗
        with mock.patch.object(
            fetcher.finnhub_client,
            'earnings_calendar',
            side_effect=Exception("API Error")
        ):
            with mock.patch('yfinance.Ticker') as mock_ticker:
                mock_ticker.return_value.calendar = None
                
                # 提供較舊的業績日期（120天前）
                old_date = datetime.now() - timedelta(days=120)
                mock_earnings_dates = pd.DatetimeIndex([old_date])
                mock_ticker.return_value.earnings_dates = pd.DataFrame(
                    index=mock_earnings_dates
                )
                
                result = fetcher.get_earnings_calendar('AAPL')
        
        assert result is not None
        assert result['is_estimated'] is True
        
        # 應該推測下一個季度（從最後業績日期+90天的倍數）
        # 120天前 + 90天 = 30天前，再+90天 = 60天後
        estimated_date = datetime.strptime(result['next_earnings_date'], '%Y-%m-%d')
        days_until = (estimated_date - datetime.now()).days
        # 應該在未來 30-90 天內
        assert 0 < days_until <= 100
    
    def test_fallback_recording(self, fetcher):
        """測試降級使用記錄"""
        # 清空記錄
        fetcher.fallback_used = {}
        
        # 模擬 Finnhub 失敗，yfinance 成功
        with mock.patch.object(
            fetcher.finnhub_client,
            'earnings_calendar',
            side_effect=Exception("API Error")
        ):
            mock_calendar = pd.DataFrame({
                'Earnings Date': [pd.Timestamp('2025-01-30')]
            }).T
            
            with mock.patch('yfinance.Ticker') as mock_ticker:
                mock_ticker.return_value.calendar = mock_calendar
                
                result = fetcher.get_earnings_calendar('AAPL')
        
        # 驗證降級記錄
        assert 'earnings_calendar' in fetcher.fallback_used
        assert 'yfinance' in fetcher.fallback_used['earnings_calendar']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
