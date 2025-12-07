# data_layer/utils/retry_handler.py
"""
重試處理器

提供統一的重試邏輯，支持多種退避策略（指數、線性、固定）。

使用示例:
    >>> handler = RetryHandler()
    >>> delay = handler.calculate_delay(attempt=1, strategy='exponential')
    >>> print(f"等待 {delay} 秒後重試")
"""

import random
import logging
from dataclasses import dataclass, field
from typing import Optional, List, Callable, Any
from enum import Enum

logger = logging.getLogger(__name__)


class RetryStrategy(Enum):
    """重試策略枚舉"""
    EXPONENTIAL = 'exponential'  # 指數退避
    LINEAR = 'linear'            # 線性退避
    CONSTANT = 'constant'        # 固定延遲


@dataclass
class RetryConfig:
    """
    重試配置
    
    屬性:
        max_retries: 最大重試次數（默認 3）
        initial_delay: 初始延遲秒數（默認 1.0）
        max_delay: 最大延遲秒數（默認 120.0）
        exponential_base: 指數退避的基數（默認 2.0）
        jitter: 是否添加隨機抖動（默認 True）
        jitter_factor: 抖動因子，0-1 之間（默認 0.1）
        retryable_status_codes: 可重試的 HTTP 狀態碼
    """
    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 120.0
    exponential_base: float = 2.0
    jitter: bool = True
    jitter_factor: float = 0.1
    retryable_status_codes: List[int] = field(default_factory=lambda: [429, 500, 502, 503, 504])


class RetryHandler:
    """
    統一的重試處理器
    
    支持多種退避策略:
    - exponential: 指數退避 (initial * base^attempt)
    - linear: 線性退避 (initial * attempt)
    - constant: 固定延遲 (initial)
    
    Requirements: 3.1, 3.3
    """
    
    def __init__(self, config: Optional[RetryConfig] = None):
        """
        初始化重試處理器
        
        參數:
            config: 重試配置（可選，使用默認配置）
        """
        self.config = config or RetryConfig()
        self._attempt_history: List[dict] = []
        
        logger.debug(f"RetryHandler 初始化: max_retries={self.config.max_retries}, "
                    f"initial_delay={self.config.initial_delay}s")
    
    def calculate_delay(
        self, 
        attempt: int, 
        strategy: str = 'exponential'
    ) -> float:
        """
        計算重試延遲
        
        參數:
            attempt: 當前重試次數（從 1 開始）
            strategy: 退避策略 ('exponential', 'linear', 'constant')
        
        返回:
            float: 延遲秒數
        
        Requirements: 3.1, 3.3
        """
        if attempt < 1:
            attempt = 1
        
        # 計算基礎延遲
        if strategy == 'exponential':
            # 指數退避: initial * base^(attempt-1)
            # attempt=1: initial * 2^0 = initial
            # attempt=2: initial * 2^1 = initial * 2
            # attempt=3: initial * 2^2 = initial * 4
            delay = self.config.initial_delay * (self.config.exponential_base ** (attempt - 1))
        elif strategy == 'linear':
            # 線性退避: initial * attempt
            delay = self.config.initial_delay * attempt
        elif strategy == 'constant':
            # 固定延遲
            delay = self.config.initial_delay
        else:
            logger.warning(f"未知策略 '{strategy}'，使用指數退避")
            delay = self.config.initial_delay * (self.config.exponential_base ** (attempt - 1))
        
        # 添加抖動（避免多個客戶端同時重試）
        if self.config.jitter:
            jitter_range = delay * self.config.jitter_factor
            delay += random.uniform(-jitter_range, jitter_range)
        
        # 限制最大延遲
        delay = min(delay, self.config.max_delay)
        
        # 確保延遲為正數
        delay = max(0.1, delay)
        
        logger.debug(f"計算延遲: attempt={attempt}, strategy={strategy}, delay={delay:.2f}s")
        
        return delay
    
    def should_retry(self, status_code: int, attempt: int) -> bool:
        """
        判斷是否應該重試
        
        參數:
            status_code: HTTP 狀態碼
            attempt: 當前重試次數
        
        返回:
            bool: 是否應該重試
        """
        # 檢查是否超過最大重試次數
        if attempt >= self.config.max_retries:
            logger.debug(f"已達最大重試次數 {self.config.max_retries}")
            return False
        
        # 檢查狀態碼是否可重試
        if status_code in self.config.retryable_status_codes:
            logger.debug(f"狀態碼 {status_code} 可重試")
            return True
        
        logger.debug(f"狀態碼 {status_code} 不可重試")
        return False
    
    def get_strategy_for_status(self, status_code: int) -> str:
        """
        根據狀態碼獲取推薦的退避策略
        
        參數:
            status_code: HTTP 狀態碼
        
        返回:
            str: 推薦的策略名稱
        """
        if status_code == 429:
            # 速率限制：使用較長的指數退避
            return 'exponential'
        elif status_code in [500, 502, 503, 504]:
            # 服務器錯誤：使用線性退避
            return 'linear'
        elif status_code == 401:
            # 認證錯誤：使用固定短延遲
            return 'constant'
        else:
            return 'exponential'
    
    def get_initial_delay_for_status(self, status_code: int) -> float:
        """
        根據狀態碼獲取推薦的初始延遲
        
        參數:
            status_code: HTTP 狀態碼
        
        返回:
            float: 推薦的初始延遲秒數
        """
        if status_code == 429:
            # 速率限制：較長初始延遲
            return 30.0
        elif status_code in [500, 502, 503, 504]:
            # 服務器錯誤：中等延遲
            return 10.0
        elif status_code == 401:
            # 認證錯誤：短延遲
            return 2.0
        else:
            return self.config.initial_delay
    
    def record_attempt(
        self, 
        attempt: int, 
        status_code: int, 
        delay: float,
        success: bool
    ) -> None:
        """
        記錄重試嘗試
        
        參數:
            attempt: 重試次數
            status_code: HTTP 狀態碼
            delay: 使用的延遲
            success: 是否成功
        """
        record = {
            'attempt': attempt,
            'status_code': status_code,
            'delay': delay,
            'success': success
        }
        self._attempt_history.append(record)
        
        if len(self._attempt_history) > 100:
            self._attempt_history = self._attempt_history[-100:]
    
    def get_stats(self) -> dict:
        """
        獲取重試統計
        
        返回:
            dict: 統計信息
        """
        if not self._attempt_history:
            return {
                'total_attempts': 0,
                'success_rate': 0.0,
                'avg_delay': 0.0
            }
        
        total = len(self._attempt_history)
        successes = sum(1 for r in self._attempt_history if r['success'])
        total_delay = sum(r['delay'] for r in self._attempt_history)
        
        return {
            'total_attempts': total,
            'success_rate': successes / total if total > 0 else 0.0,
            'avg_delay': total_delay / total if total > 0 else 0.0
        }
    
    def reset_stats(self) -> None:
        """重置統計"""
        self._attempt_history.clear()


# 預配置的重試處理器
def create_rate_limit_handler() -> RetryHandler:
    """創建針對速率限制優化的重試處理器"""
    config = RetryConfig(
        max_retries=3,
        initial_delay=30.0,
        max_delay=120.0,
        exponential_base=2.0,
        jitter=True
    )
    return RetryHandler(config)


def create_server_error_handler() -> RetryHandler:
    """創建針對服務器錯誤優化的重試處理器"""
    config = RetryConfig(
        max_retries=3,
        initial_delay=10.0,
        max_delay=60.0,
        exponential_base=1.0,  # 線性
        jitter=True
    )
    return RetryHandler(config)


# 測試代碼
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    print("=" * 60)
    print("重試處理器測試")
    print("=" * 60)
    
    handler = RetryHandler()
    
    print("\n指數退避測試:")
    for i in range(1, 6):
        delay = handler.calculate_delay(i, 'exponential')
        print(f"  attempt {i}: {delay:.2f}s")
    
    print("\n線性退避測試:")
    for i in range(1, 6):
        delay = handler.calculate_delay(i, 'linear')
        print(f"  attempt {i}: {delay:.2f}s")
    
    print("\n固定延遲測試:")
    for i in range(1, 6):
        delay = handler.calculate_delay(i, 'constant')
        print(f"  attempt {i}: {delay:.2f}s")
    
    print("\n狀態碼測試:")
    for code in [429, 500, 401, 200]:
        should = handler.should_retry(code, 1)
        strategy = handler.get_strategy_for_status(code)
        print(f"  {code}: should_retry={should}, strategy={strategy}")
