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
from hypothesis import given, strategies as st, settings, assume

# 添加項目根目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_layer.data_fetcher import DataFetcher


# ==================== Hypothesis 策略定義 ====================

# 有效的股票代碼策略（1-5個大寫字母）
ticker_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('Lu',)),
    min_size=1,
    max_size=5
).filter(lambda x: x.isalpha())

# 業績日期策略（未來 1-90 天）
future_date_strategy = st.integers(min_value=1, max_value=90).map(
    lambda days: (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')
)

# 業績時間策略
earnings_time_strategy = st.sampled_from(['bmo', 'amc', 'dmh', 'unknown'])

# EPS 估計策略
eps_estimate_strategy = st.floats(min_value=-10.0, max_value=50.0, allow_nan=False, allow_infinity=False)

# 收入估計策略
revenue_estimate_strategy = st.integers(min_value=0, max_value=500000000000)

# 降級場景策略
fallback_scenario_strategy = st.sampled_from([
    'finnhub_success',
    'finnhub_fail_yfinance_success',
    'finnhub_fail_yfinance_fail_estimation_success',
    'all_fail'
])


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


class TestEarningsCalendarFallbackProperties:
    """
    業績日曆降級策略的屬性測試
    
    **Feature: data-sources-enhancement, Property 1: Earnings Calendar Fallback Chain Completeness**
    **Validates: Requirements 1.1, 1.3, 1.5**
    
    Property 1: 對於任何股票代碼，當 Finnhub 無法提供業績日曆數據時，
    系統應該嘗試 yfinance，然後嘗試歷史推測，確保至少一種方法返回結果或 None
    （永不拋出未處理的異常）。
    """
    
    @pytest.fixture
    def fetcher(self):
        """創建 DataFetcher 實例（不使用 IBKR）"""
        return DataFetcher(use_ibkr=False)
    
    @given(
        ticker=ticker_strategy,
        earnings_date=future_date_strategy,
        earnings_time=earnings_time_strategy,
        eps_estimate=eps_estimate_strategy,
        revenue_estimate=revenue_estimate_strategy
    )
    @settings(max_examples=20, deadline=30000)
    def test_property_finnhub_success_returns_valid_result(
        self, ticker, earnings_date, earnings_time, eps_estimate, revenue_estimate
    ):
        """
        Property 1.1: 當 Finnhub 成功時，返回有效的業績日曆結果
        
        *For any* valid ticker and Finnhub response, the system should return
        a result with all required fields and correct data source attribution.
        
        **Feature: data-sources-enhancement, Property 1: Earnings Calendar Fallback Chain Completeness**
        **Validates: Requirements 1.1**
        """
        fetcher = DataFetcher(use_ibkr=False)
        
        # 模擬 Finnhub 成功響應
        mock_response = {
            'earningsCalendar': [{
                'date': earnings_date,
                'hour': earnings_time,
                'epsEstimate': eps_estimate,
                'revenueEstimate': revenue_estimate
            }]
        }
        
        with mock.patch.object(
            fetcher.finnhub_client,
            'earnings_calendar',
            return_value=mock_response
        ):
            result = fetcher.get_earnings_calendar(ticker)
        
        # 驗證結果結構
        assert result is not None, "Finnhub 成功時應返回結果"
        assert 'next_earnings_date' in result
        assert 'earnings_call_time' in result
        assert 'data_source' in result
        assert 'is_estimated' in result
        assert 'confidence' in result
        
        # 驗證數據源標記
        assert result['data_source'] == 'finnhub'
        assert result['is_estimated'] is False
        assert result['confidence'] == 'high'
        
        # 驗證日期格式
        assert len(result['next_earnings_date']) == 10
        assert result['next_earnings_date'].count('-') == 2
    
    @given(
        ticker=ticker_strategy,
        scenario=fallback_scenario_strategy
    )
    @settings(max_examples=20, deadline=60000)
    def test_property_fallback_chain_never_throws_exception(self, ticker, scenario):
        """
        Property 1.2: 降級鏈永不拋出未處理異常
        
        *For any* ticker and any failure scenario, the system should either
        return a valid result or None, but never throw an unhandled exception.
        
        **Feature: data-sources-enhancement, Property 1: Earnings Calendar Fallback Chain Completeness**
        **Validates: Requirements 1.5**
        """
        fetcher = DataFetcher(use_ibkr=False)
        
        # 根據場景設置 mock
        if scenario == 'finnhub_success':
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
                result = fetcher.get_earnings_calendar(ticker)
        
        elif scenario == 'finnhub_fail_yfinance_success':
            with mock.patch.object(
                fetcher.finnhub_client,
                'earnings_calendar',
                side_effect=Exception("API Error")
            ):
                mock_calendar = pd.DataFrame({
                    'Earnings Date': [pd.Timestamp('2025-01-20')]
                }).T
                
                with mock.patch('yfinance.Ticker') as mock_ticker:
                    mock_ticker.return_value.calendar = mock_calendar
                    result = fetcher.get_earnings_calendar(ticker)
        
        elif scenario == 'finnhub_fail_yfinance_fail_estimation_success':
            with mock.patch.object(
                fetcher.finnhub_client,
                'earnings_calendar',
                side_effect=Exception("API Error")
            ):
                with mock.patch('yfinance.Ticker') as mock_ticker:
                    mock_ticker.return_value.calendar = None
                    mock_earnings_dates = pd.DatetimeIndex([
                        pd.Timestamp('2024-10-15')
                    ])
                    mock_ticker.return_value.earnings_dates = pd.DataFrame(
                        index=mock_earnings_dates
                    )
                    result = fetcher.get_earnings_calendar(ticker)
        
        else:  # all_fail
            with mock.patch.object(
                fetcher.finnhub_client,
                'earnings_calendar',
                side_effect=Exception("API Error")
            ):
                with mock.patch('yfinance.Ticker', side_effect=Exception("Network Error")):
                    result = fetcher.get_earnings_calendar(ticker)
        
        # 核心屬性：永不拋出異常，結果要麼是有效字典，要麼是 None
        assert result is None or isinstance(result, dict), \
            f"結果應該是 dict 或 None，但得到 {type(result)}"
        
        # 如果有結果，驗證必要字段
        if result is not None:
            required_fields = ['next_earnings_date', 'data_source', 'is_estimated']
            for field in required_fields:
                assert field in result, f"結果缺少必要字段: {field}"
    
    @given(
        ticker=ticker_strategy,
        days_ago=st.integers(min_value=1, max_value=365)
    )
    @settings(max_examples=20, deadline=30000)
    def test_property_estimation_produces_future_date(self, ticker, days_ago):
        """
        Property 1.3: 歷史推測總是產生未來日期
        
        *For any* ticker with historical earnings data, the estimated next
        earnings date should always be in the future.
        
        **Feature: data-sources-enhancement, Property 1: Earnings Calendar Fallback Chain Completeness**
        **Validates: Requirements 1.3, 1.4**
        """
        fetcher = DataFetcher(use_ibkr=False)
        
        # 模擬所有 API 失敗，只有歷史數據可用
        with mock.patch.object(
            fetcher.finnhub_client,
            'earnings_calendar',
            side_effect=Exception("API Error")
        ):
            with mock.patch('yfinance.Ticker') as mock_ticker:
                mock_ticker.return_value.calendar = None
                
                # 提供歷史業績日期
                historical_date = datetime.now() - timedelta(days=days_ago)
                mock_earnings_dates = pd.DatetimeIndex([historical_date])
                mock_ticker.return_value.earnings_dates = pd.DataFrame(
                    index=mock_earnings_dates
                )
                
                result = fetcher.get_earnings_calendar(ticker)
        
        # 如果推測成功，日期應該在未來
        if result is not None and result.get('is_estimated'):
            estimated_date = datetime.strptime(
                result['next_earnings_date'], '%Y-%m-%d'
            )
            days_until = (estimated_date - datetime.now()).days
            
            # 推測日期應該在未來（允許當天）
            assert days_until >= 0, \
                f"推測日期應該在未來，但得到 {days_until} 天後"
            
            # 推測日期不應該太遠（最多 120 天）
            assert days_until <= 120, \
                f"推測日期不應超過 120 天，但得到 {days_until} 天後"
    
    def test_property_data_source_attribution(self):
        """
        Property 1.4: 數據源歸屬正確
        
        *For any* successful result, the data_source field should correctly
        indicate which source provided the data.
        
        **Feature: data-sources-enhancement, Property 1: Earnings Calendar Fallback Chain Completeness**
        **Validates: Requirements 1.1, 1.3**
        """
        fetcher = DataFetcher(use_ibkr=False)
        
        # 測試各數據源的歸屬
        test_cases = [
            ('finnhub', 'high', False),
            ('yfinance', 'medium', False),
            ('estimated', 'low', True)
        ]
        
        for data_source, expected_confidence, expected_estimated in test_cases:
            if data_source == 'finnhub':
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
            
            elif data_source == 'yfinance':
                with mock.patch.object(
                    fetcher.finnhub_client,
                    'earnings_calendar',
                    side_effect=Exception("API Error")
                ):
                    mock_calendar = pd.DataFrame({
                        'Earnings Date': [pd.Timestamp('2025-01-20')]
                    }).T
                    with mock.patch('yfinance.Ticker') as mock_ticker:
                        mock_ticker.return_value.calendar = mock_calendar
                        result = fetcher.get_earnings_calendar('AAPL')
            
            else:  # estimated
                with mock.patch.object(
                    fetcher.finnhub_client,
                    'earnings_calendar',
                    side_effect=Exception("API Error")
                ):
                    with mock.patch('yfinance.Ticker') as mock_ticker:
                        mock_ticker.return_value.calendar = None
                        mock_earnings_dates = pd.DatetimeIndex([pd.Timestamp('2024-10-15')])
                        mock_ticker.return_value.earnings_dates = pd.DataFrame(index=mock_earnings_dates)
                        result = fetcher.get_earnings_calendar('AAPL')
            
            assert result is not None, f"{data_source} 應返回結果"
            assert result['data_source'] == data_source, f"數據源應為 {data_source}"
            assert result['confidence'] == expected_confidence, f"信心度應為 {expected_confidence}"
            assert result['is_estimated'] == expected_estimated, f"is_estimated 應為 {expected_estimated}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
