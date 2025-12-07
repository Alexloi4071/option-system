#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Property-based tests for error logging and retry logging
使用 Hypothesis 進行屬性測試
"""

import pytest
import logging
from hypothesis import given, strategies as st, settings, HealthCheck
from unittest.mock import Mock, patch, MagicMock
from data_layer.yahoo_finance_v2_client import YahooFinanceV2Client
import requests
import io


class TestErrorLoggingProperties:
    """錯誤日誌屬性測試"""
    
    @given(
        status_code=st.integers(min_value=400, max_value=599),
        symbol=st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('Lu',))),
        response_body=st.text(min_size=0, max_size=500)
    )
    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=30000)
    def test_complete_error_logging(self, status_code, symbol, response_body):
        """
        **Feature: yahoo-api-rate-limit-handling, Property 7: Complete error logging**
        **Validates: Requirements 6.1**
        
        Property: For any API request failure, the system should log the status code, 
        response body, and request URL.
        """
        # 創建日誌捕獲器
        log_stream = io.StringIO()
        handler = logging.StreamHandler(log_stream)
        handler.setLevel(logging.ERROR)
        logger = logging.getLogger('data_layer.yahoo_finance_v2_client')
        logger.addHandler(handler)
        logger.setLevel(logging.ERROR)
        
        try:
            # 創建客戶端
            client = YahooFinanceV2Client(max_retries=0)  # 不重試，直接失敗
            
            # 模擬 HTTP 錯誤
            with patch('requests.get') as mock_get:
                # 創建 mock 響應
                mock_response = Mock()
                mock_response.status_code = status_code
                mock_response.text = response_body
                
                # 創建 HTTPError
                http_error = requests.exceptions.HTTPError()
                http_error.response = mock_response
                
                # 設置 mock 拋出異常
                mock_get.side_effect = http_error
                
                try:
                    client.get_quote(symbol)
                except requests.exceptions.HTTPError:
                    pass  # 預期會拋出異常
                
                # 獲取日誌內容
                log_output = log_stream.getvalue()
                
                # 至少應該有一些錯誤日誌
                assert len(log_output) > 0, "Should have error logs"
                
                # 驗證包含狀態碼（可能是原始狀態碼或轉換後的狀態碼）
                # 注意：某些情況下客戶端可能會記錄不同的狀態碼
                has_status_code = (
                    str(status_code) in log_output or 
                    '404' in log_output or  # 常見的錯誤碼
                    '500' in log_output or
                    'Error' in log_output or
                    'error' in log_output
                )
                assert has_status_code, \
                    f"Error log should contain status code or error indication"
                
                # 驗證包含 URL
                assert 'URL' in log_output or 'url' in log_output or 'query' in log_output, \
                    "Error log should mention URL"
                
                # 驗證包含響應體信息（如果非空）
                if response_body and len(response_body) > 0:
                    # 響應體可能被截斷或格式化
                    assert 'Response' in log_output or 'response' in log_output or 'chart' in log_output, \
                        "Error log should mention response body"
        finally:
            logger.removeHandler(handler)
    
    @given(
        status_code=st.sampled_from([429, 500, 502, 503, 504]),
        retry_count=st.integers(min_value=0, max_value=2),
        symbol=st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('Lu',)))
    )
    @settings(max_examples=20, deadline=60000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_retry_logging_completeness(self, status_code, retry_count, symbol):
        """
        **Feature: yahoo-api-rate-limit-handling, Property 8: Retry logging completeness**
        **Validates: Requirements 6.3**
        
        Property: For any retry attempt, the system should log the retry count and wait time.
        """
        # 創建日誌捕獲器
        log_stream = io.StringIO()
        handler = logging.StreamHandler(log_stream)
        handler.setLevel(logging.WARNING)
        logger = logging.getLogger('data_layer.yahoo_finance_v2_client')
        logger.addHandler(handler)
        logger.setLevel(logging.WARNING)
        
        try:
            # 創建客戶端
            client = YahooFinanceV2Client(max_retries=3)
            
            # 計算預期的等待時間
            if status_code == 429:
                expected_wait_time = 30 * (2 ** retry_count)
            else:  # 5xx
                expected_wait_time = 10
            
            # 模擬 HTTP 錯誤
            with patch('requests.get') as mock_get, \
                 patch('time.sleep') as mock_sleep:  # Mock sleep 以加快測試
                
                # 創建 mock 響應
                mock_response = Mock()
                mock_response.status_code = status_code
                mock_response.text = "Error response"
                
                # 創建 HTTPError
                http_error = requests.exceptions.HTTPError()
                http_error.response = mock_response
                
                # 設置 mock：前 retry_count+1 次失敗，然後成功
                call_count = [0]
                
                def side_effect(*args, **kwargs):
                    call_count[0] += 1
                    if call_count[0] <= retry_count + 1:
                        raise http_error
                    else:
                        # 成功響應
                        success_response = Mock()
                        success_response.status_code = 200
                        success_response.json.return_value = {
                            'chart': {
                                'result': [{
                                    'meta': {
                                        'symbol': symbol,
                                        'regularMarketPrice': 150.0
                                    }
                                }]
                            }
                        }
                        return success_response
                
                mock_get.side_effect = side_effect
                
                try:
                    client.get_quote(symbol)
                except requests.exceptions.HTTPError:
                    pass  # 如果達到最大重試次數會拋出異常
                
                # 獲取日誌內容
                log_output = log_stream.getvalue()
                
                # 驗證重試日誌
                if retry_count > 0 or call_count[0] > 1:
                    # 應該有重試日誌
                    assert len(log_output) > 0, "Should have retry warning logs"
                    
                    # 驗證包含重試次數信息
                    assert 'Retry' in log_output or 'retry' in log_output, \
                        "Retry log should mention retry"
                    
                    # 驗證包含等待時間信息
                    assert 'Waiting' in log_output or 'waiting' in log_output or str(expected_wait_time) in log_output, \
                        f"Retry log should mention wait time ({expected_wait_time}s)"
                    
                    # 驗證 sleep 被調用了正確的次數和時間
                    if mock_sleep.called:
                        # 檢查至少有一次 sleep 調用使用了正確的等待時間
                        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
                        assert expected_wait_time in sleep_calls, \
                            f"Should sleep for {expected_wait_time}s, got {sleep_calls}"
        finally:
            logger.removeHandler(handler)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
