#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Massive API 客戶端

功能:
- 獲取股票即時報價
- 獲取歷史價格數據
- 作為備用數據源

作者: Kiro
日期: 2025-11-25
版本: 1.0.0
"""

import requests
import pandas as pd
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List

logger = logging.getLogger(__name__)


class MassiveAPIClient:
    """
    Massive API 客戶端
    
    提供:
    - 股票即時報價
    - 歷史價格數據
    - 基本面數據
    
    作為 Yahoo Finance 和 Alpha Vantage 的備用數據源
    """
    
    # Massive API 基礎 URL (需要根據實際 API 文檔調整)
    BASE_URL = "https://api.massive.io"
    
    # 速率限制設置 (根據實際限制調整)
    MIN_REQUEST_INTERVAL = 1.0  # 秒
    
    def __init__(self, api_key: str, request_delay: float = 1.0):
        """
        初始化 Massive API 客戶端
        
        參數:
            api_key: Massive API Key
            request_delay: 請求間隔（秒）
        """
        self.api_key = api_key
        self.request_delay = max(request_delay, self.MIN_REQUEST_INTERVAL)
        self.last_request_time = 0
        self.request_count = 0
        
        if not api_key:
            logger.warning("! Massive API Key 未設置")
        else:
            logger.info(f"* Massive API 客戶端已初始化")
            logger.info(f"  請求間隔: {self.request_delay}秒")
    
    def _rate_limit(self):
        """速率限制"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.request_delay:
            sleep_time = self.request_delay - elapsed
            logger.debug(f"  速率限制延遲: {sleep_time:.2f}秒")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
        self.request_count += 1
    
    def _make_request(
        self, 
        endpoint: str, 
        params: Dict[str, str] = None,
        method: str = 'GET'
    ) -> Optional[Dict]:
        """
        發送 API 請求
        
        參數:
            endpoint: API 端點
            params: 請求參數
            method: HTTP 方法
        
        返回:
            dict: API 響應數據
        """
        try:
            self._rate_limit()
            
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            url = f"{self.BASE_URL}/{endpoint}"
            
            logger.debug(f"  請求 Massive API: {endpoint}")
            
            if method == 'GET':
                response = requests.get(
                    url,
                    headers=headers,
                    params=params,
                    timeout=30
                )
            else:
                response = requests.post(
                    url,
                    headers=headers,
                    json=params,
                    timeout=30
                )
            
            response.raise_for_status()
            data = response.json()
            
            # 檢查錯誤響應
            if 'error' in data:
                logger.error(f"x Massive API 錯誤: {data['error']}")
                return None
            
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"x Massive API 請求失敗: {e}")
            return None
        except Exception as e:
            logger.error(f"x Massive API 錯誤: {e}")
            return None

    # ==================== 股票價格數據 ====================
    
    def get_quote(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        獲取股票即時報價
        
        參數:
            ticker: 股票代碼
        
        返回:
            dict: 包含價格、成交量等信息
        """
        try:
            logger.info(f"開始獲取 {ticker} 即時報價 (Massive API)...")
            
            # 嘗試不同的 API 端點格式
            endpoints_to_try = [
                f"v1/stocks/{ticker}/quote",
                f"stocks/{ticker}/quote",
                f"quote/{ticker}",
                f"v1/quote/{ticker}"
            ]
            
            data = None
            for endpoint in endpoints_to_try:
                try:
                    data = self._make_request(endpoint)
                    if data:
                        break
                except:
                    continue
            
            if not data:
                logger.warning(f"! Massive API 未獲取到 {ticker} 的報價")
                return None
            
            # 解析響應 (根據實際 API 響應格式調整)
            result = {
                'ticker': ticker,
                'current_price': float(data.get('price', data.get('lastPrice', data.get('close', 0)))),
                'open': float(data.get('open', 0)),
                'high': float(data.get('high', 0)),
                'low': float(data.get('low', 0)),
                'volume': int(data.get('volume', 0)),
                'previous_close': float(data.get('previousClose', data.get('prevClose', 0))),
                'change': float(data.get('change', 0)),
                'change_percent': float(data.get('changePercent', data.get('percentChange', 0))),
                'data_source': 'Massive API'
            }
            
            if result['current_price'] > 0:
                logger.info(f"* 成功獲取 {ticker} 報價: ${result['current_price']:.2f}")
                return result
            else:
                logger.warning(f"! Massive API 返回無效價格")
                return None
            
        except Exception as e:
            logger.error(f"x 獲取 {ticker} 報價失敗 (Massive API): {e}")
            return None
    
    def get_daily_prices(
        self,
        ticker: str,
        days: int = 100
    ) -> Optional[pd.DataFrame]:
        """
        獲取每日股票價格數據
        
        參數:
            ticker: 股票代碼
            days: 獲取天數
        
        返回:
            DataFrame: 包含 Open, High, Low, Close, Volume 的數據
        """
        try:
            logger.info(f"開始獲取 {ticker} 歷史價格數據 (Massive API)...")
            
            # 計算日期範圍
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            params = {
                'from': start_date.strftime('%Y-%m-%d'),
                'to': end_date.strftime('%Y-%m-%d')
            }
            
            # 嘗試不同的端點
            endpoints_to_try = [
                f"v1/stocks/{ticker}/history",
                f"stocks/{ticker}/historical",
                f"history/{ticker}",
                f"v1/historical/{ticker}"
            ]
            
            data = None
            for endpoint in endpoints_to_try:
                try:
                    data = self._make_request(endpoint, params)
                    if data:
                        break
                except:
                    continue
            
            if not data:
                logger.warning(f"! Massive API 未獲取到 {ticker} 的歷史數據")
                return None
            
            # 解析響應 (根據實際 API 響應格式調整)
            if isinstance(data, list):
                prices = data
            elif 'data' in data:
                prices = data['data']
            elif 'prices' in data:
                prices = data['prices']
            elif 'history' in data:
                prices = data['history']
            else:
                prices = []
            
            if not prices:
                logger.warning(f"! Massive API 返回空的歷史數據")
                return None
            
            # 轉換為 DataFrame
            df = pd.DataFrame(prices)
            
            # 標準化列名
            column_mapping = {
                'date': 'Date',
                'timestamp': 'Date',
                'open': 'Open',
                'high': 'High',
                'low': 'Low',
                'close': 'Close',
                'volume': 'Volume',
                'adj_close': 'Adj Close',
                'adjClose': 'Adj Close'
            }
            
            df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
            
            # 設置日期索引
            if 'Date' in df.columns:
                df['Date'] = pd.to_datetime(df['Date'])
                df = df.set_index('Date')
            
            # 確保數據類型正確
            for col in ['Open', 'High', 'Low', 'Close']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            if 'Volume' in df.columns:
                df['Volume'] = pd.to_numeric(df['Volume'], errors='coerce').fillna(0).astype(int)
            
            df = df.sort_index()
            
            logger.info(f"* 成功獲取 {ticker} 的 {len(df)} 條歷史記錄 (Massive API)")
            
            return df
            
        except Exception as e:
            logger.error(f"x 獲取 {ticker} 歷史數據失敗 (Massive API): {e}")
            return None
    
    def get_company_info(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        獲取公司基本信息
        
        參數:
            ticker: 股票代碼
        
        返回:
            dict: 公司信息
        """
        try:
            logger.info(f"開始獲取 {ticker} 公司信息 (Massive API)...")
            
            endpoints_to_try = [
                f"v1/stocks/{ticker}/profile",
                f"stocks/{ticker}/company",
                f"company/{ticker}",
                f"v1/company/{ticker}"
            ]
            
            data = None
            for endpoint in endpoints_to_try:
                try:
                    data = self._make_request(endpoint)
                    if data:
                        break
                except:
                    continue
            
            if not data:
                logger.warning(f"! Massive API 未獲取到 {ticker} 的公司信息")
                return None
            
            result = {
                'ticker': ticker,
                'company_name': data.get('name', data.get('companyName', '')),
                'sector': data.get('sector', ''),
                'industry': data.get('industry', ''),
                'market_cap': data.get('marketCap', 0),
                'pe_ratio': data.get('peRatio', data.get('pe', 0)),
                'eps': data.get('eps', 0),
                'beta': data.get('beta', 0),
                'dividend_yield': data.get('dividendYield', 0),
                'data_source': 'Massive API'
            }
            
            logger.info(f"* 成功獲取 {ticker} 公司信息 (Massive API)")
            
            return result
            
        except Exception as e:
            logger.error(f"x 獲取 {ticker} 公司信息失敗 (Massive API): {e}")
            return None
    
    def test_connection(self) -> bool:
        """
        測試 API 連接
        
        返回:
            bool: 連接是否成功
        """
        try:
            # 嘗試獲取一個常見股票的報價來測試連接
            result = self.get_quote('AAPL')
            return result is not None
        except Exception as e:
            logger.error(f"x Massive API 連接測試失敗: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """
        獲取客戶端狀態
        
        返回:
            dict: 狀態信息
        """
        return {
            'name': 'Massive API',
            'api_key_set': bool(self.api_key),
            'request_count': self.request_count,
            'request_delay': self.request_delay,
            'last_request_time': datetime.fromtimestamp(self.last_request_time).isoformat() if self.last_request_time > 0 else None
        }


# 使用示例
if __name__ == "__main__":
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    from config.settings import settings
    
    logging.basicConfig(level=logging.INFO)
    
    # 創建客戶端
    api_key = getattr(settings, 'MASSIVE_API_KEY', None)
    
    if api_key:
        client = MassiveAPIClient(api_key=api_key)
        
        print("\n" + "=" * 60)
        print("測試 Massive API")
        print("=" * 60)
        
        # 測試連接
        if client.test_connection():
            print("✓ 連接成功")
        else:
            print("✗ 連接失敗")
        
        print("\n" + "=" * 60)
    else:
        print("! MASSIVE_API_KEY 未設置")
