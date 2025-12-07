# data_layer/utils/user_agent_rotator.py
"""
User-Agent 輪換器

用於避免被網站識別為爬蟲，通過輪換不同的瀏覽器 User-Agent 字符串。

使用示例:
    >>> rotator = UserAgentRotator()
    >>> ua = rotator.get_next()
    >>> headers = {'User-Agent': ua}
"""

import random
import logging
from typing import List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class UserAgentRotator:
    """
    User-Agent 輪換器
    
    提供多種瀏覽器的 User-Agent 字符串，支持輪換和隨機選擇。
    
    特點:
    - 包含 Chrome, Firefox, Safari, Edge 等主流瀏覽器
    - 支持 Windows, macOS, Linux 等操作系統
    - 定期更新版本號以保持真實性
    
    Requirements: 2.4, 4.1
    """
    
    # 常見瀏覽器 User-Agent 列表（2024-2025 最新版本）
    # 更新日期: 2025-12-07
    # 注意: 使用最新的瀏覽器版本號可以減少被識別為爬蟲的風險
    USER_AGENTS: List[str] = [
        # Chrome 131 on Windows (2024年12月最新)
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
        
        # Chrome on macOS (最新版本)
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        
        # Firefox 133 on Windows (2024年12月最新)
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0',
        
        # Firefox on macOS
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:133.0) Gecko/20100101 Firefox/133.0',
        
        # Safari 17.2 on macOS (最新)
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
        
        # Edge 131 on Windows (最新)
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0',
        
        # Chrome on Linux
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        
        # Chrome on Windows 11
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    ]
    
    def __init__(self, custom_agents: Optional[List[str]] = None):
        """
        初始化 User-Agent 輪換器
        
        參數:
            custom_agents: 自定義 User-Agent 列表（可選）
        """
        self._agents = custom_agents if custom_agents else self.USER_AGENTS.copy()
        self._index = 0
        self._last_used: Optional[str] = None
        self._usage_count = 0
        
        logger.debug(f"UserAgentRotator 初始化，共 {len(self._agents)} 個 User-Agent")
    
    def get_next(self) -> str:
        """
        獲取下一個 User-Agent（輪換）
        
        按順序輪換 User-Agent，到達末尾後從頭開始。
        
        返回:
            str: User-Agent 字符串
        """
        ua = self._agents[self._index]
        self._index = (self._index + 1) % len(self._agents)
        self._last_used = ua
        self._usage_count += 1
        
        logger.debug(f"輪換 User-Agent: {ua[:50]}...")
        return ua
    
    def get_random(self) -> str:
        """
        獲取隨機 User-Agent
        
        隨機選擇一個 User-Agent，避免連續使用相同的。
        
        返回:
            str: User-Agent 字符串
        """
        # 如果只有一個，直接返回
        if len(self._agents) == 1:
            self._last_used = self._agents[0]
            self._usage_count += 1
            return self._agents[0]
        
        # 避免連續使用相同的 User-Agent
        available = [ua for ua in self._agents if ua != self._last_used]
        ua = random.choice(available)
        self._last_used = ua
        self._usage_count += 1
        
        logger.debug(f"隨機 User-Agent: {ua[:50]}...")
        return ua
    
    def get_current(self) -> Optional[str]:
        """
        獲取當前（最後使用的）User-Agent
        
        返回:
            str: 最後使用的 User-Agent，如果從未使用過則返回 None
        """
        return self._last_used
    
    def reset(self) -> None:
        """重置輪換索引到開始位置"""
        self._index = 0
        logger.debug("UserAgentRotator 已重置")
    
    def add_agent(self, user_agent: str) -> None:
        """
        添加新的 User-Agent
        
        參數:
            user_agent: 要添加的 User-Agent 字符串
        """
        if user_agent not in self._agents:
            self._agents.append(user_agent)
            logger.debug(f"添加 User-Agent: {user_agent[:50]}...")
    
    def get_stats(self) -> dict:
        """
        獲取使用統計
        
        返回:
            dict: 包含統計信息的字典
        """
        return {
            'total_agents': len(self._agents),
            'current_index': self._index,
            'usage_count': self._usage_count,
            'last_used': self._last_used[:50] + '...' if self._last_used else None
        }
    
    def __len__(self) -> int:
        """返回 User-Agent 數量"""
        return len(self._agents)
    
    def __iter__(self):
        """迭代所有 User-Agent"""
        return iter(self._agents)


# 全局單例（可選使用）
_default_rotator: Optional[UserAgentRotator] = None


def get_default_rotator() -> UserAgentRotator:
    """
    獲取默認的 User-Agent 輪換器（單例）
    
    返回:
        UserAgentRotator: 默認輪換器實例
    """
    global _default_rotator
    if _default_rotator is None:
        _default_rotator = UserAgentRotator()
    return _default_rotator


# 測試代碼
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    print("=" * 60)
    print("User-Agent 輪換器測試")
    print("=" * 60)
    
    rotator = UserAgentRotator()
    
    print(f"\n總共 {len(rotator)} 個 User-Agent")
    
    print("\n測試輪換 (get_next):")
    for i in range(5):
        ua = rotator.get_next()
        print(f"  {i+1}. {ua[:60]}...")
    
    print("\n測試隨機 (get_random):")
    for i in range(5):
        ua = rotator.get_random()
        print(f"  {i+1}. {ua[:60]}...")
    
    print(f"\n統計: {rotator.get_stats()}")
