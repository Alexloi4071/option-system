# data_layer/utils/__init__.py
"""
數據層工具模塊

包含:
- UserAgentRotator: User-Agent 輪換器
- RetryHandler: 重試處理器
- ConnectionConfig: 連接配置
"""

from dataclasses import dataclass
from typing import Tuple

from .user_agent_rotator import UserAgentRotator
from .retry_handler import RetryHandler, RetryConfig


@dataclass
class ConnectionConfig:
    """
    連接配置
    
    統一管理 HTTP 連接的超時和會話設置。
    
    Requirements: 6.1, 6.2, 6.3
    """
    # 超時設置（秒）
    connect_timeout: float = 5.0   # 連接超時
    read_timeout: float = 15.0     # 讀取超時
    
    # 會話設置
    max_retries: int = 3           # 最大重試次數
    pool_connections: int = 10     # 連接池大小
    pool_maxsize: int = 10         # 連接池最大大小
    
    # 會話過期設置
    session_ttl_minutes: int = 30  # 會話有效期（分鐘）
    
    @property
    def timeout(self) -> Tuple[float, float]:
        """返回 requests 格式的超時元組 (connect, read)"""
        return (self.connect_timeout, self.read_timeout)


# 預配置的連接配置
DEFAULT_CONNECTION_CONFIG = ConnectionConfig()

# Yahoo Finance 專用配置（較長超時）
YAHOO_CONNECTION_CONFIG = ConnectionConfig(
    connect_timeout=5.0,
    read_timeout=20.0,
    max_retries=3
)

# Finviz 專用配置
FINVIZ_CONNECTION_CONFIG = ConnectionConfig(
    connect_timeout=5.0,
    read_timeout=15.0,
    max_retries=3
)


__all__ = [
    'UserAgentRotator', 
    'RetryHandler', 
    'RetryConfig',
    'ConnectionConfig',
    'DEFAULT_CONNECTION_CONFIG',
    'YAHOO_CONNECTION_CONFIG',
    'FINVIZ_CONNECTION_CONFIG',
]
