#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
重試策略模組
處理不同類型的 HTTP 錯誤的重試邏輯
"""

from typing import Tuple


class RetryStrategy:
    """重試策略類"""
    
    @staticmethod
    def should_retry(status_code: int, retry_count: int, max_retries: int) -> bool:
        """
        判斷是否應該重試
        
        Args:
            status_code: HTTP 狀態碼
            retry_count: 當前重試次數
            max_retries: 最大重試次數
            
        Returns:
            是否應該重試
        """
        # 已達到最大重試次數
        if retry_count >= max_retries:
            return False
        
        # 429: 速率限制 - 應該重試
        if status_code == 429:
            return True
        
        # 5xx: 服務器錯誤 - 應該重試
        if 500 <= status_code < 600:
            return True
        
        # 4xx: 客戶端錯誤（除 429）- 不重試
        if 400 <= status_code < 500:
            return False
        
        # 其他錯誤 - 不重試
        return False
    
    @staticmethod
    def get_wait_time(status_code: int, retry_count: int) -> float:
        """
        計算等待時間
        
        Args:
            status_code: HTTP 狀態碼
            retry_count: 當前重試次數（從 0 開始）
            
        Returns:
            等待時間（秒）
        """
        # 429: 指數退避（30, 60, 120, ...）
        if status_code == 429:
            return 30 * (2 ** retry_count)
        
        # 5xx: 線性退避（固定 10 秒）
        if 500 <= status_code < 600:
            return 10.0
        
        # 其他情況不應該重試，返回 0
        return 0.0
    
    @staticmethod
    def get_retry_info(status_code: int, retry_count: int, max_retries: int) -> Tuple[bool, float]:
        """
        獲取重試信息（便捷方法）
        
        Args:
            status_code: HTTP 狀態碼
            retry_count: 當前重試次數
            max_retries: 最大重試次數
            
        Returns:
            (是否應該重試, 等待時間)
        """
        should_retry = RetryStrategy.should_retry(status_code, retry_count, max_retries)
        wait_time = RetryStrategy.get_wait_time(status_code, retry_count) if should_retry else 0.0
        return should_retry, wait_time
