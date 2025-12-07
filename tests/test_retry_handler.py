# tests/test_retry_handler.py
"""
重試處理器屬性測試

使用 Hypothesis 進行屬性測試，驗證退避策略的正確性。
"""

import pytest
from hypothesis import given, strategies as st, settings, assume

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_layer.utils.retry_handler import RetryHandler, RetryConfig


class TestRetryHandler:
    """重試處理器測試"""
    
    def test_initialization(self):
        """測試初始化"""
        handler = RetryHandler()
        assert handler.config.max_retries == 3
        assert handler.config.initial_delay == 1.0
    
    def test_custom_config(self):
        """測試自定義配置"""
        config = RetryConfig(max_retries=5, initial_delay=2.0)
        handler = RetryHandler(config)
        assert handler.config.max_retries == 5
        assert handler.config.initial_delay == 2.0
    
    @settings(max_examples=100)
    @given(st.integers(min_value=1, max_value=10))
    def test_exponential_backoff_increases(self, attempt):
        """
        **Feature: data-sources-optimization, Property 2: 指數退避正確性**
        
        *For any* sequence of retry attempts with exponential backoff, 
        the delay for attempt N should be approximately base^(N-1) * initial_delay.
        
        **Validates: Requirements 3.1**
        """
        # 使用無抖動配置以便精確測試
        config = RetryConfig(
            initial_delay=1.0,
            exponential_base=2.0,
            jitter=False
        )
        handler = RetryHandler(config)
        
        delay = handler.calculate_delay(attempt, 'exponential')
        expected = config.initial_delay * (config.exponential_base ** (attempt - 1))
        expected = min(expected, config.max_delay)
        
        # 允許小誤差
        assert abs(delay - expected) < 0.01, \
            f"Expected {expected}, got {delay} for attempt {attempt}"
    
    @settings(max_examples=100)
    @given(st.integers(min_value=1, max_value=10))
    def test_exponential_delay_increases_with_attempt(self, attempt):
        """測試指數退避延遲隨重試次數增加"""
        config = RetryConfig(jitter=False, max_delay=1000.0)
        handler = RetryHandler(config)
        
        if attempt > 1:
            delay_current = handler.calculate_delay(attempt, 'exponential')
            delay_previous = handler.calculate_delay(attempt - 1, 'exponential')
            
            # 當前延遲應該大於前一次（除非達到最大值）
            assert delay_current >= delay_previous, \
                f"Delay should increase: {delay_previous} -> {delay_current}"
    
    @settings(max_examples=100)
    @given(st.integers(min_value=1, max_value=10))
    def test_linear_backoff_correctness(self, attempt):
        """
        **Feature: data-sources-optimization, Property 3: 線性退避正確性**
        
        *For any* sequence of retry attempts with linear backoff, 
        the delay should increase linearly with each attempt.
        
        **Validates: Requirements 3.3**
        """
        config = RetryConfig(
            initial_delay=10.0,
            jitter=False
        )
        handler = RetryHandler(config)
        
        delay = handler.calculate_delay(attempt, 'linear')
        expected = config.initial_delay * attempt
        expected = min(expected, config.max_delay)
        
        assert abs(delay - expected) < 0.01, \
            f"Expected {expected}, got {delay} for attempt {attempt}"
    
    @settings(max_examples=100)
    @given(st.integers(min_value=1, max_value=10))
    def test_linear_delay_increases_linearly(self, attempt):
        """測試線性退避延遲線性增加"""
        config = RetryConfig(jitter=False, initial_delay=10.0, max_delay=1000.0)
        handler = RetryHandler(config)
        
        if attempt > 1:
            delay_current = handler.calculate_delay(attempt, 'linear')
            delay_previous = handler.calculate_delay(attempt - 1, 'linear')
            
            # 差值應該等於 initial_delay
            diff = delay_current - delay_previous
            assert abs(diff - config.initial_delay) < 0.01, \
                f"Linear increment should be {config.initial_delay}, got {diff}"
    
    def test_constant_delay(self):
        """測試固定延遲"""
        config = RetryConfig(initial_delay=5.0, jitter=False)
        handler = RetryHandler(config)
        
        for attempt in range(1, 6):
            delay = handler.calculate_delay(attempt, 'constant')
            assert abs(delay - 5.0) < 0.01
    
    def test_max_delay_cap(self):
        """測試最大延遲限制"""
        config = RetryConfig(
            initial_delay=100.0,
            max_delay=50.0,
            jitter=False
        )
        handler = RetryHandler(config)
        
        delay = handler.calculate_delay(5, 'exponential')
        assert delay <= config.max_delay
    
    def test_jitter_adds_variation(self):
        """測試抖動添加變化"""
        config = RetryConfig(initial_delay=10.0, jitter=True, jitter_factor=0.1)
        handler = RetryHandler(config)
        
        delays = [handler.calculate_delay(1, 'constant') for _ in range(20)]
        
        # 應該有一些變化
        assert len(set(delays)) > 1, "Jitter should add variation"
    
    def test_should_retry_respects_max_retries(self):
        """測試重試次數限制"""
        config = RetryConfig(max_retries=3)
        handler = RetryHandler(config)
        
        assert handler.should_retry(429, 1) == True
        assert handler.should_retry(429, 2) == True
        assert handler.should_retry(429, 3) == False  # 達到最大次數
    
    def test_should_retry_checks_status_code(self):
        """測試狀態碼檢查"""
        handler = RetryHandler()
        
        # 可重試的狀態碼
        assert handler.should_retry(429, 1) == True
        assert handler.should_retry(500, 1) == True
        assert handler.should_retry(503, 1) == True
        
        # 不可重試的狀態碼
        assert handler.should_retry(200, 1) == False
        assert handler.should_retry(400, 1) == False
        assert handler.should_retry(404, 1) == False
    
    def test_strategy_for_status(self):
        """測試狀態碼對應的策略"""
        handler = RetryHandler()
        
        assert handler.get_strategy_for_status(429) == 'exponential'
        assert handler.get_strategy_for_status(500) == 'linear'
        assert handler.get_strategy_for_status(401) == 'constant'
    
    def test_initial_delay_for_status(self):
        """測試狀態碼對應的初始延遲"""
        handler = RetryHandler()
        
        assert handler.get_initial_delay_for_status(429) == 30.0
        assert handler.get_initial_delay_for_status(500) == 10.0
        assert handler.get_initial_delay_for_status(401) == 2.0
    
    def test_record_and_stats(self):
        """測試記錄和統計"""
        handler = RetryHandler()
        
        handler.record_attempt(1, 429, 1.0, False)
        handler.record_attempt(2, 429, 2.0, True)
        
        stats = handler.get_stats()
        assert stats['total_attempts'] == 2
        assert stats['success_rate'] == 0.5
        assert stats['avg_delay'] == 1.5
    
    def test_delay_always_positive(self):
        """測試延遲始終為正數"""
        handler = RetryHandler()
        
        for attempt in range(1, 20):
            for strategy in ['exponential', 'linear', 'constant']:
                delay = handler.calculate_delay(attempt, strategy)
                assert delay > 0, f"Delay should be positive: {delay}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
