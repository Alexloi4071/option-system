#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Property-based tests for RetryStrategy
使用 Hypothesis 進行屬性測試
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from data_layer.retry_strategy import RetryStrategy


class TestRetryStrategyProperties:
    """RetryStrategy 屬性測試"""
    
    @given(
        retry_count=st.integers(min_value=0, max_value=10),
        max_retries=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=100)
    def test_exponential_backoff_for_429_errors(self, retry_count, max_retries):
        """
        **Feature: yahoo-api-rate-limit-handling, Property 4: Exponential backoff for 429 errors**
        **Validates: Requirements 4.3, 5.1**
        
        Property: For any sequence of consecutive 429 errors, the wait time before 
        each retry should increase exponentially (30s, 60s, 120s, ...).
        """
        status_code = 429
        
        # 只測試在重試限制內的情況
        if retry_count < max_retries:
            # 驗證應該重試
            should_retry = RetryStrategy.should_retry(status_code, retry_count, max_retries)
            assert should_retry, f"Should retry for 429 error when retry_count ({retry_count}) < max_retries ({max_retries})"
            
            # 驗證等待時間符合指數增長：30 * (2 ** retry_count)
            wait_time = RetryStrategy.get_wait_time(status_code, retry_count)
            expected_wait_time = 30 * (2 ** retry_count)
            
            assert wait_time == expected_wait_time, \
                f"Wait time should be {expected_wait_time}s for retry {retry_count}, got {wait_time}s"
            
            # 驗證指數增長特性：每次重試等待時間翻倍
            if retry_count > 0:
                previous_wait_time = RetryStrategy.get_wait_time(status_code, retry_count - 1)
                assert wait_time == previous_wait_time * 2, \
                    f"Wait time should double: {previous_wait_time}s -> {wait_time}s"
        else:
            # 達到最大重試次數，不應該重試
            should_retry = RetryStrategy.should_retry(status_code, retry_count, max_retries)
            assert not should_retry, \
                f"Should not retry when retry_count ({retry_count}) >= max_retries ({max_retries})"
    
    @given(
        retry_count=st.integers(min_value=0, max_value=10),
        max_retries=st.integers(min_value=1, max_value=10),
        status_code=st.integers(min_value=500, max_value=599)
    )
    @settings(max_examples=100)
    def test_linear_backoff_for_5xx_errors(self, retry_count, max_retries, status_code):
        """
        **Feature: yahoo-api-rate-limit-handling, Property 5: Linear backoff for 5xx errors**
        **Validates: Requirements 5.2**
        
        Property: For any sequence of 5xx errors, the wait time before each retry 
        should remain constant at 10 seconds.
        """
        # 只測試在重試限制內的情況
        if retry_count < max_retries:
            # 驗證應該重試
            should_retry = RetryStrategy.should_retry(status_code, retry_count, max_retries)
            assert should_retry, \
                f"Should retry for {status_code} error when retry_count ({retry_count}) < max_retries ({max_retries})"
            
            # 驗證等待時間固定為 10 秒（線性退避）
            wait_time = RetryStrategy.get_wait_time(status_code, retry_count)
            expected_wait_time = 10.0
            
            assert wait_time == expected_wait_time, \
                f"Wait time should be {expected_wait_time}s for 5xx error, got {wait_time}s"
            
            # 驗證線性特性：無論重試次數如何，等待時間保持不變
            if retry_count > 0:
                previous_wait_time = RetryStrategy.get_wait_time(status_code, retry_count - 1)
                assert wait_time == previous_wait_time, \
                    f"Wait time should remain constant: {previous_wait_time}s == {wait_time}s"
        else:
            # 達到最大重試次數，不應該重試
            should_retry = RetryStrategy.should_retry(status_code, retry_count, max_retries)
            assert not should_retry, \
                f"Should not retry when retry_count ({retry_count}) >= max_retries ({max_retries})"
    
    @given(
        retry_count=st.integers(min_value=0, max_value=10),
        max_retries=st.integers(min_value=1, max_value=10),
        status_code=st.integers(min_value=400, max_value=499).filter(lambda x: x != 429)
    )
    @settings(max_examples=100)
    def test_no_retry_for_4xx_errors_except_429(self, retry_count, max_retries, status_code):
        """
        **Feature: yahoo-api-rate-limit-handling, Property 6: No retry for 4xx errors (except 429)**
        **Validates: Requirements 5.5**
        
        Property: For any 4xx error response (excluding 429), the system should not 
        attempt any retries and should fail immediately.
        """
        # 驗證不應該重試 4xx 錯誤（除了 429）
        should_retry = RetryStrategy.should_retry(status_code, retry_count, max_retries)
        assert not should_retry, \
            f"Should not retry for {status_code} error (4xx except 429)"
        
        # 驗證等待時間為 0（因為不重試）
        wait_time = RetryStrategy.get_wait_time(status_code, retry_count)
        assert wait_time == 0.0, \
            f"Wait time should be 0 for non-retryable {status_code} error, got {wait_time}s"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
