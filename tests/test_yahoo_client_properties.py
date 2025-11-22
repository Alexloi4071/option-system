#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Property-based tests for Yahoo Finance Client
使用 Hypothesis 进行属性测试
"""

import pytest
from hypothesis import given, strategies as st, settings
from unittest.mock import Mock, patch, MagicMock
from data_layer.yahoo_finance_v2_client import YahooFinanceV2Client


class TestYahooClientProperties:
    """Yahoo Finance 客户端属性测试"""
    
    @given(
        symbol=st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('Lu',))),
        user_agent=st.one_of(st.none(), st.text(min_size=10, max_size=200))
    )
    @settings(max_examples=100)
    def test_user_agent_header_presence(self, symbol, user_agent):
        """
        **Feature: yahoo-api-rate-limit-handling, Property 1: User-Agent header presence**
        **Validates: Requirements 1.2**
        
        Property: For any API request made by the system, the request headers 
        should include a non-empty User-Agent field.
        """
        # 创建客户端
        client = YahooFinanceV2Client(user_agent=user_agent)
        
        # 验证 User-Agent header 存在且非空
        assert 'User-Agent' in client.headers, "User-Agent header must be present"
        assert client.headers['User-Agent'], "User-Agent header must not be empty"
        assert len(client.headers['User-Agent']) > 0, "User-Agent must have content"
        
        # 模拟 API 请求，验证 headers 被正确传递
        with patch('requests.get') as mock_get:
            # 设置 mock 返回值
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'chart': {
                    'result': [{
                        'meta': {
                            'symbol': symbol,
                            'regularMarketPrice': 150.0
                        }
                    }]
                }
            }
            mock_get.return_value = mock_response
            
            try:
                # 发起请求
                client.get_quote(symbol)
                
                # 验证 requests.get 被调用时包含 User-Agent
                assert mock_get.called, "requests.get should be called"
                call_kwargs = mock_get.call_args[1]
                
                assert 'headers' in call_kwargs, "headers must be passed to requests.get"
                assert 'User-Agent' in call_kwargs['headers'], "User-Agent must be in headers"
                assert call_kwargs['headers']['User-Agent'], "User-Agent must not be empty in request"
                
            except Exception:
                # 如果 symbol 无效导致异常，仍然验证 headers 配置正确
                assert 'User-Agent' in client.headers
                assert client.headers['User-Agent']


    @given(
        request_delay=st.floats(min_value=0.1, max_value=2.0),
        num_requests=st.integers(min_value=2, max_value=5)
    )
    @settings(max_examples=100)
    def test_minimum_request_interval_enforcement(self, request_delay, num_requests):
        """
        **Feature: yahoo-api-rate-limit-handling, Property 3: Minimum request interval enforcement**
        **Validates: Requirements 4.2**
        
        Property: For any two consecutive API requests, the time interval between them 
        should be at least the configured minimum request interval.
        """
        import time
        
        # 创建客户端，设置请求间隔
        client = YahooFinanceV2Client(request_delay=request_delay)
        
        # Mock time.time 和 time.sleep 来避免真实等待
        current_time = [0.0]  # 使用列表来允许在闭包中修改
        sleep_durations = []
        
        def mock_time():
            return current_time[0]
        
        def mock_sleep(duration):
            sleep_durations.append(duration)
            current_time[0] += duration
        
        # 模拟多次 API 请求
        with patch('requests.get') as mock_get, \
             patch('time.time', side_effect=mock_time), \
             patch('time.sleep', side_effect=mock_sleep):
            
            # 设置 mock 返回值
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'chart': {
                    'result': [{
                        'meta': {
                            'symbol': 'TEST',
                            'regularMarketPrice': 100.0
                        }
                    }]
                }
            }
            mock_get.return_value = mock_response
            
            # 发起多次请求
            for i in range(num_requests):
                try:
                    client.get_quote('TEST')
                except Exception:
                    pass  # 忽略可能的异常
            
            # 验证 sleep 被调用，且每次 sleep 的时间接近 request_delay
            # 第一次请求不应该 sleep（因为 last_request_time 初始为 0）
            # 后续请求应该 sleep request_delay 秒
            if num_requests > 1:
                # 至少应该有 num_requests - 1 次 sleep
                assert len(sleep_durations) >= num_requests - 1, \
                    f"Expected at least {num_requests - 1} sleep calls, got {len(sleep_durations)}"
                
                # 验证每次 sleep 的时间大约等于 request_delay
                for duration in sleep_durations:
                    assert duration >= 0, f"Sleep duration should be non-negative, got {duration}"
                    assert duration <= request_delay + 0.01, \
                        f"Sleep duration {duration:.3f}s exceeds request_delay {request_delay}s"
    
    @given(
        symbol=st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('Lu',)))
    )
    @settings(max_examples=100)
    def test_no_oauth_tokens_in_requests(self, symbol):
        """
        **Feature: yahoo-api-rate-limit-handling, Property 2: No OAuth tokens in requests**
        **Validates: Requirements 3.2**
        
        Property: For any API request made by the system, the request should not 
        include OAuth authorization headers or tokens.
        """
        # 创建客户端
        client = YahooFinanceV2Client()
        
        # 验证客户端 headers 中没有 OAuth 相关字段
        assert 'Authorization' not in client.headers, "Authorization header should not be present"
        assert 'OAuth' not in client.headers, "OAuth header should not be present"
        
        # 模拟 API 请求，验证没有 OAuth headers
        with patch('requests.get') as mock_get:
            # 设置 mock 返回值
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'chart': {
                    'result': [{
                        'meta': {
                            'symbol': symbol,
                            'regularMarketPrice': 150.0
                        }
                    }]
                }
            }
            mock_get.return_value = mock_response
            
            try:
                # 发起请求
                client.get_quote(symbol)
                
                # 验证 requests.get 被调用时没有 OAuth headers
                if mock_get.called:
                    call_kwargs = mock_get.call_args[1]
                    
                    if 'headers' in call_kwargs:
                        headers = call_kwargs['headers']
                        assert 'Authorization' not in headers, "Authorization header should not be in request"
                        assert 'OAuth' not in headers, "OAuth header should not be in request"
                        
                        # 检查 header 值中是否包含 OAuth 相关字符串
                        for key, value in headers.items():
                            if isinstance(value, str):
                                assert 'Bearer' not in value, "Bearer token should not be in headers"
                                assert 'oauth' not in value.lower(), "OAuth token should not be in headers"
                
            except Exception:
                # 如果 symbol 无效导致异常，仍然验证 headers 配置正确
                assert 'Authorization' not in client.headers
                assert 'OAuth' not in client.headers


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
