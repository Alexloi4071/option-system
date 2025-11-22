#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RapidAPI 客戶端

封裝 RapidAPI Yahoo Finance 數據訪問，作為最終降級方案。
"""

import time
import logging
import requests
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class RateLimitTracker:
    """追蹤 API 使用量以避免超限"""
    
    def __init__(self, limit: int = 500, period: str = 'month'):
        """
        初始化速率限制追蹤器
        
        Args:
            limit: 使用限制（默認 500 次/月）
            period: 時間週期（默認 'month'）
        """
        self.limit = limit
        self.period = period
        self.usage_count = 0
        self.reset_date = self._calculate_reset_date()
    
    def _calculate_reset_date(self) -> datetime:
        """計算重置日期（下個月1號）"""
        now = datetime.now()
        if now.month == 12:
            return datetime(now.year + 1, 1, 1)
        else:
            return datetime(now.year, now.month + 1, 1)
    
    def can_make_request(self) -> bool:
        """檢查是否可以發送請求"""
        # 檢查是否需要重置
        if datetime.now() >= self.reset_date:
            self._reset()
        
        return self.usage_count < self.limit
    
    def record_request(self) -> None:
        """記錄一次請求"""
        self.usage_count += 1
        logger.debug(f"RapidAPI usage: {self.usage_count}/{self.limit}")
    
    def _reset(self) -> None:
        """重置計數器"""
        logger.info("RapidAPI 使用量已重置")
        self.usage_count = 0
        self.reset_date = self._calculate_reset_date()
    
    def get_remaining(self) -> int:
        """獲取剩餘請求數"""
        return max(0, self.limit - self.usage_count)


class RapidAPIClient:
    """
    RapidAPI 客戶端
    
    提供 Yahoo Finance 數據的備用訪問方式。
    """
    
    def __init__(
        self,
        api_key: str,
        host: str,
        request_delay: float = 1.0,
        monthly_limit: int = 500
    ):
        """
        初始化 RapidAPI 客戶端
        
        Args:
            api_key: RapidAPI Key
            host: RapidAPI Host
            request_delay: 請求間隔（秒）
            monthly_limit: 月度請求限制
        """
        self.api_key = api_key
        self.host = host
        self.request_delay = request_delay
        self.last_request_time = 0
        
        # 初始化速率限制追蹤器
        self.rate_limiter = RateLimitTracker(limit=monthly_limit)
        
        # 設置請求頭
        self.headers = {
            'X-RapidAPI-Key': self.api_key,
            'X-RapidAPI-Host': self.host
        }
        
        logger.info(f"* RapidAPI 客戶端已初始化 (限制: {monthly_limit}/月)")
    
    def _rate_limit_delay(self) -> None:
        """請求速率限制"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.request_delay:
            time.sleep(self.request_delay - elapsed)
        self.last_request_time = time.time()
    
    def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        發送 API 請求
        
        Args:
            endpoint: API 端點
            params: 查詢參數
        
        Returns:
            API 響應（JSON），失敗返回 None
        """
        # 檢查速率限制
        if not self.rate_limiter.can_make_request():
            logger.error(
                f"x RapidAPI 月度限制已達 "
                f"({self.rate_limiter.usage_count}/{self.rate_limiter.limit})"
            )
            return None
        
        self._rate_limit_delay()
        
        url = f"https://{self.host}{endpoint}"
        
        try:
            logger.debug(f"RapidAPI request: {url}")
            response = requests.get(
                url,
                headers=self.headers,
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            # 記錄請求
            self.rate_limiter.record_request()
            
            logger.debug(
                f"* RapidAPI request succeeded "
                f"(remaining: {self.rate_limiter.get_remaining()})"
            )
            
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"x RapidAPI HTTP error: {e}")
            return None
        except requests.exceptions.Timeout:
            logger.error("x RapidAPI request timeout")
            return None
        except Exception as e:
            logger.error(f"x RapidAPI request failed: {e}")
            return None
    
    def get_quote(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        獲取股票報價
        
        Args:
            ticker: 股票代碼
        
        Returns:
            報價數據字典，失敗返回 None
        """
        logger.info(f"從 RapidAPI 獲取 {ticker} 報價...")
        
        endpoint = "/v8/finance/chart"
        params = {
            'symbol': ticker,
            'interval': '1d',
            'range': '1d'
        }
        
        response = self._make_request(endpoint, params)
        
        if response:
            logger.info(f"* 成功從 RapidAPI 獲取 {ticker} 報價")
            return response
        else:
            logger.warning(f"! RapidAPI 獲取 {ticker} 報價失敗")
            return None
    
    def get_historical_data(
        self,
        ticker: str,
        period: str = '1mo'
    ) -> Optional[Dict[str, Any]]:
        """
        獲取歷史數據
        
        Args:
            ticker: 股票代碼
            period: 時間範圍（1d, 5d, 1mo, 3mo, 1y）
        
        Returns:
            歷史數據字典，失敗返回 None
        """
        logger.info(f"從 RapidAPI 獲取 {ticker} 歷史數據 ({period})...")
        
        endpoint = "/v8/finance/chart"
        params = {
            'symbol': ticker,
            'interval': '1d',
            'range': period
        }
        
        response = self._make_request(endpoint, params)
        
        if response:
            logger.info(f"* 成功從 RapidAPI 獲取 {ticker} 歷史數據")
            return response
        else:
            logger.warning(f"! RapidAPI 獲取 {ticker} 歷史數據失敗")
            return None


# 使用示例
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    logging.basicConfig(level=logging.INFO)
    load_dotenv()
    
    api_key = os.getenv('RAPIDAPI_KEY')
    host = os.getenv('RAPIDAPI_HOST')
    
    if api_key and host:
        client = RapidAPIClient(api_key, host)
        
        # 測試獲取報價
        quote = client.get_quote('AAPL')
        if quote:
            print("* RapidAPI 測試成功")
        else:
            print("x RapidAPI 測試失敗")
    else:
        print("! 請配置 RAPIDAPI_KEY 和 RAPIDAPI_HOST")
