# tests/test_user_agent_rotator.py
"""
User-Agent 輪換器屬性測試

使用 Hypothesis 進行屬性測試，驗證 User-Agent 輪換的正確性。
"""

import pytest
from hypothesis import given, strategies as st, settings

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_layer.utils.user_agent_rotator import UserAgentRotator


class TestUserAgentRotator:
    """User-Agent 輪換器測試"""
    
    def test_initialization(self):
        """測試初始化"""
        rotator = UserAgentRotator()
        assert len(rotator) > 0
        assert rotator.get_current() is None
    
    def test_get_next_returns_string(self):
        """測試 get_next 返回字符串"""
        rotator = UserAgentRotator()
        ua = rotator.get_next()
        assert isinstance(ua, str)
        assert len(ua) > 0
    
    def test_get_random_returns_string(self):
        """測試 get_random 返回字符串"""
        rotator = UserAgentRotator()
        ua = rotator.get_random()
        assert isinstance(ua, str)
        assert len(ua) > 0
    
    @settings(max_examples=100)
    @given(st.integers(min_value=2, max_value=20))
    def test_rotation_not_all_identical(self, n_requests):
        """
        **Feature: data-sources-optimization, Property 1: User-Agent 輪換正確性**
        
        *For any* sequence of N requests (N > 1), the User-Agent strings used 
        should not all be identical, ensuring rotation is working.
        
        **Validates: Requirements 2.4**
        """
        rotator = UserAgentRotator()
        
        # 獲取 N 個 User-Agent
        user_agents = [rotator.get_next() for _ in range(n_requests)]
        
        # 驗證不是所有都相同（除非只有一個 UA）
        if len(rotator) > 1:
            unique_agents = set(user_agents)
            assert len(unique_agents) > 1, \
                f"All {n_requests} User-Agents are identical: {user_agents[0][:50]}..."
    
    def test_rotation_cycles_through_all(self):
        """測試輪換會遍歷所有 User-Agent"""
        rotator = UserAgentRotator()
        n = len(rotator)
        
        # 獲取 n 個 User-Agent
        user_agents = [rotator.get_next() for _ in range(n)]
        
        # 應該包含所有不同的 User-Agent
        assert len(set(user_agents)) == n
    
    def test_rotation_wraps_around(self):
        """測試輪換會循環"""
        rotator = UserAgentRotator()
        n = len(rotator)
        
        # 獲取第一個
        first = rotator.get_next()
        
        # 跳過 n-1 個
        for _ in range(n - 1):
            rotator.get_next()
        
        # 下一個應該是第一個
        wrapped = rotator.get_next()
        assert wrapped == first
    
    def test_random_avoids_consecutive_duplicates(self):
        """測試隨機選擇避免連續重複"""
        rotator = UserAgentRotator()
        
        # 獲取 20 個隨機 User-Agent
        user_agents = [rotator.get_random() for _ in range(20)]
        
        # 檢查沒有連續重複
        for i in range(1, len(user_agents)):
            assert user_agents[i] != user_agents[i-1], \
                f"Consecutive duplicates at index {i}"
    
    def test_custom_agents(self):
        """測試自定義 User-Agent 列表"""
        custom = ['UA1', 'UA2', 'UA3']
        rotator = UserAgentRotator(custom_agents=custom)
        
        assert len(rotator) == 3
        assert rotator.get_next() == 'UA1'
        assert rotator.get_next() == 'UA2'
        assert rotator.get_next() == 'UA3'
    
    def test_reset(self):
        """測試重置功能"""
        rotator = UserAgentRotator()
        
        first = rotator.get_next()
        rotator.get_next()
        rotator.get_next()
        
        rotator.reset()
        
        assert rotator.get_next() == first
    
    def test_add_agent(self):
        """測試添加新 User-Agent"""
        rotator = UserAgentRotator()
        initial_count = len(rotator)
        
        rotator.add_agent('New Custom UA')
        
        assert len(rotator) == initial_count + 1
    
    def test_stats(self):
        """測試統計功能"""
        rotator = UserAgentRotator()
        
        rotator.get_next()
        rotator.get_next()
        
        stats = rotator.get_stats()
        
        assert stats['usage_count'] == 2
        assert stats['current_index'] == 2
        assert stats['total_agents'] == len(rotator)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
