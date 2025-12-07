#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RapidAPIClient 單元測試

測試 RapidAPI 客戶端的核心功能：
- API 請求構建
- 速率限制邏輯
- 響應解析

Requirements: 8.3
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import logging
import sys
import os

# 添加項目路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_layer.rapidapi_client import RapidAPIClient, RateLimitTracker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestRateLimitTracker(unittest.TestCase):
    """速率限制追蹤器測試"""
    
    def setUp(self):
        """測試初始化"""
        self.tracker = RateLimitTracker(limit=500, period='month')
    
    def test_initial_state(self):
        """測試初始狀態"""
        self.assertEqual(self.tracker.usage_count, 0)
        self.assertEqual(self.tracker.limit, 500)
        self.assertTrue(self.tracker.can_make_request())
        self.assertEqual(self.tracker.get_remaining(), 500)
    
    def test_record_request(self):
        """測試記錄請求"""
        self.tracker.record_request()
        self.assertEqual(self.tracker.usage_count, 1)
        self.assertEqual(self.tracker.get_remaining(), 499)
    
    def test_can_make_request_under_limit(self):
        """測試未達限制時可以請求"""
        for _ in range(499):
            self.tracker.record_request()
        
        self.assertTrue(self.tracker.can_make_request())
        self.assertEqual(self.tracker.get_remaining(), 1)
    
    def test_cannot_make_request_at_limit(self):
        """測試達到限制時不能請求"""
        for _ in range(500):
            self.tracker.record_request()
        
        self.assertFalse(self.tracker.can_make_request())
        self.assertEqual(self.tracker.get_remaining(), 0)
    
    def test_reset_date_calculation(self):
        """測試重置日期計算"""
        reset_date = self.tracker.reset_date
        now = datetime.now()
        
        # 重置日期應該是下個月1號
        if now.month == 12:
            expected_month = 1
            expected_year = now.year + 1
        else:
            expected_month = now.month + 1
            expected_year = now.year
        
        self.assertEqual(reset_date.month, expected_month)
        self.assertEqual(reset_date.year, expected_year)
        self.assertEqual(reset_date.day, 1)
    
    def test_reset_on_new_month(self):
        """測試新月份重置"""
        # 模擬已使用 100 次
        for _ in range(100):
            self.tracker.record_request()
        
        self.assertEqual(self.tracker.usage_count, 100)
        
        # 模擬重置日期已過
        self.tracker.reset_date = datetime.now() - timedelta(days=1)
        
        # 調用 can_make_request 應該觸發重置
        self.assertTrue(self.tracker.can_make_request())
        self.assertEqual(self.tracker.usage_count, 0)


class TestRapidAPIClient(unittest.TestCase):
    """RapidAPI 客戶端測試"""
    
    def setUp(self):
        """測試初始化"""
        self.api_key = "test_api_key"
        self.host = "yahoo-finance127.p.rapidapi.com"
        self.client = RapidAPIClient(
            api_key=self.api_key,
            host=self.host,
            request_delay=0.1,  # 測試時使用較短延遲
            monthly_limit=500
        )
    
    def test_initialization(self):
        """測試客戶端初始化"""
        self.assertEqual(self.client.api_key, self.api_key)
        self.assertEqual(self.client.host, self.host)
        self.assertEqual(self.client.request_delay, 0.1)
        self.assertIsNotNone(self.client.rate_limiter)
        self.assertEqual(self.client.rate_limiter.limit, 500)
    
    def test_headers_setup(self):
        """測試請求頭設置"""
        self.assertIn('X-RapidAPI-Key', self.client.headers)
        self.assertIn('X-RapidAPI-Host', self.client.headers)
        self.assertEqual(self.client.headers['X-RapidAPI-Key'], self.api_key)
        self.assertEqual(self.client.headers['X-RapidAPI-Host'], self.host)
    
    @patch('data_layer.rapidapi_client.requests.get')
    def test_make_request_success(self, mock_get):
        """測試成功的 API 請求"""
        # 模擬成功響應
        mock_response = Mock()
        mock_response.json.return_value = {'chart': {'result': [{'meta': {'symbol': 'AAPL'}}]}}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = self.client._make_request('/v8/finance/chart', {'symbol': 'AAPL'})
        
        self.assertIsNotNone(result)
        self.assertIn('chart', result)
        mock_get.assert_called_once()
    
    @patch('data_layer.rapidapi_client.requests.get')
    def test_make_request_http_error(self, mock_get):
        """測試 HTTP 錯誤處理"""
        import requests
        mock_get.side_effect = requests.exceptions.HTTPError("404 Not Found")
        
        result = self.client._make_request('/v8/finance/chart', {'symbol': 'INVALID'})
        
        self.assertIsNone(result)
    
    @patch('data_layer.rapidapi_client.requests.get')
    def test_make_request_timeout(self, mock_get):
        """測試超時處理"""
        import requests
        mock_get.side_effect = requests.exceptions.Timeout()
        
        result = self.client._make_request('/v8/finance/chart', {'symbol': 'AAPL'})
        
        self.assertIsNone(result)
    
    @patch('data_layer.rapidapi_client.requests.get')
    def test_make_request_rate_limit_exceeded(self, mock_get):
        """測試超過速率限制"""
        # 模擬已達到限制
        for _ in range(500):
            self.client.rate_limiter.record_request()
        
        result = self.client._make_request('/v8/finance/chart', {'symbol': 'AAPL'})
        
        self.assertIsNone(result)
        # 不應該發送請求
        mock_get.assert_not_called()
    
    @patch('data_layer.rapidapi_client.requests.get')
    def test_get_quote_success(self, mock_get):
        """測試獲取報價成功"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'chart': {
                'result': [{
                    'meta': {
                        'symbol': 'AAPL',
                        'regularMarketPrice': 150.25
                    },
                    'indicators': {
                        'quote': [{
                            'open': [149.0],
                            'high': [151.0],
                            'low': [148.5],
                            'close': [150.25],
                            'volume': [50000000]
                        }]
                    }
                }]
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = self.client.get_quote('AAPL')
        
        self.assertIsNotNone(result)
        self.assertIn('chart', result)
    
    @patch('data_layer.rapidapi_client.requests.get')
    def test_get_quote_failure(self, mock_get):
        """測試獲取報價失敗"""
        import requests
        mock_get.side_effect = requests.exceptions.HTTPError("500 Server Error")
        
        result = self.client.get_quote('AAPL')
        
        self.assertIsNone(result)
    
    @patch('data_layer.rapidapi_client.requests.get')
    def test_get_historical_data_success(self, mock_get):
        """測試獲取歷史數據成功"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'chart': {
                'result': [{
                    'meta': {'symbol': 'AAPL'},
                    'timestamp': [1699920000, 1700006400, 1700092800],
                    'indicators': {
                        'quote': [{
                            'open': [149.0, 150.0, 151.0],
                            'high': [151.0, 152.0, 153.0],
                            'low': [148.5, 149.5, 150.5],
                            'close': [150.25, 151.25, 152.25],
                            'volume': [50000000, 45000000, 48000000]
                        }]
                    }
                }]
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = self.client.get_historical_data('AAPL', period='1mo')
        
        self.assertIsNotNone(result)
        self.assertIn('chart', result)
    
    @patch('data_layer.rapidapi_client.requests.get')
    def test_get_historical_data_different_periods(self, mock_get):
        """測試不同時間週期的歷史數據"""
        mock_response = Mock()
        mock_response.json.return_value = {'chart': {'result': [{}]}}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        periods = ['1d', '5d', '1mo', '3mo', '1y']
        
        for period in periods:
            result = self.client.get_historical_data('AAPL', period=period)
            self.assertIsNotNone(result)
    
    @patch('data_layer.rapidapi_client.requests.get')
    def test_request_url_construction(self, mock_get):
        """測試請求 URL 構建"""
        mock_response = Mock()
        mock_response.json.return_value = {}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        self.client._make_request('/v8/finance/chart', {'symbol': 'AAPL'})
        
        # 驗證 URL 構建正確
        call_args = mock_get.call_args
        expected_url = f"https://{self.host}/v8/finance/chart"
        self.assertEqual(call_args[0][0], expected_url)
        self.assertEqual(call_args[1]['params'], {'symbol': 'AAPL'})
    
    @patch('data_layer.rapidapi_client.requests.get')
    def test_rate_limiter_increments_on_success(self, mock_get):
        """測試成功請求後速率限制計數增加"""
        mock_response = Mock()
        mock_response.json.return_value = {}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        initial_count = self.client.rate_limiter.usage_count
        
        self.client._make_request('/v8/finance/chart', {'symbol': 'AAPL'})
        
        self.assertEqual(self.client.rate_limiter.usage_count, initial_count + 1)
    
    @patch('data_layer.rapidapi_client.requests.get')
    def test_rate_limiter_not_incremented_on_failure(self, mock_get):
        """測試失敗請求不增加速率限制計數"""
        import requests
        mock_get.side_effect = requests.exceptions.HTTPError("500 Server Error")
        
        initial_count = self.client.rate_limiter.usage_count
        
        self.client._make_request('/v8/finance/chart', {'symbol': 'AAPL'})
        
        # 失敗時不應該增加計數
        self.assertEqual(self.client.rate_limiter.usage_count, initial_count)


class TestRapidAPIClientIntegration(unittest.TestCase):
    """RapidAPI 客戶端集成測試（模擬）"""
    
    def setUp(self):
        """測試初始化"""
        self.client = RapidAPIClient(
            api_key="test_key",
            host="yahoo-finance127.p.rapidapi.com",
            request_delay=0.1,
            monthly_limit=500
        )
    
    @patch('data_layer.rapidapi_client.requests.get')
    def test_multiple_requests_rate_limiting(self, mock_get):
        """測試多次請求的速率限制"""
        mock_response = Mock()
        mock_response.json.return_value = {'chart': {'result': [{}]}}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # 發送多次請求
        for i in range(5):
            result = self.client.get_quote('AAPL')
            self.assertIsNotNone(result)
        
        # 驗證計數正確
        self.assertEqual(self.client.rate_limiter.usage_count, 5)
        self.assertEqual(self.client.rate_limiter.get_remaining(), 495)


if __name__ == '__main__':
    unittest.main()
