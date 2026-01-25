# -*- coding: utf-8 -*-
"""
Yahoo Finance 快速修復客戶端
專門修復 URL 和 429 錯誤問題
"""

import time
import logging
import requests
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class YahooFinanceQuickClient:
    """快速修復版 Yahoo Finance 客戶端"""
    
    def __init__(self):
        self.session = requests.Session()
        self.last_request_time = 0
        self.request_delay = 8.0  # 8秒間隔
        
        # 基礎 URLs
        self.API_BASE_URL = 'https://query1.finance.yahoo.com'
        self.API_BASE_URL_V2 = 'https://query2.finance.yahoo.com'
        self.CHART_ENDPOINT = '/v8/finance/chart'
        self.OPTIONS_ENDPOINT = '/v7/finance/options'
        
        # 設置 headers
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
        logger.info("* Yahoo 快速修復客戶端已初始化")
    
    def _rate_limit(self):
        """確保請求間隔"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.request_delay:
            wait_time = self.request_delay - time_since_last
            logger.info(f"  等待 {wait_time:.1f} 秒避免 429 錯誤...")
            time.sleep(wait_time)
        
        self.last_request_time = time.time()
    
    def _clear_session_if_needed(self):
        """定期清除 session"""
        if not hasattr(self, '_request_count'):
            self._request_count = 0
        
        self._request_count += 1
        
        if self._request_count % 5 == 0:
            logger.info("  定期刷新 session...")
            self.session.close()
            self.session = requests.Session()
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            })
    
    def get_option_expirations(self, symbol: str) -> list:
        """獲取期權到期日列表"""
        try:
            self._rate_limit()
            self._clear_session_if_needed()
            
            url = f"{self.API_BASE_URL}{self.OPTIONS_ENDPOINT}/{symbol}"
            logger.info(f"獲取 {symbol} 到期日...")
            
            response = self.session.get(url, timeout=15)
            
            if response.status_code == 429:
                logger.error("x 429 錯誤，清除 session 並重試")
                self.session.close()
                time.sleep(20)
                self.session = requests.Session()
                response = self.session.get(url, timeout=15)
            
            response.raise_for_status()
            data = response.json()
            
            if 'optionChain' in data and data['optionChain']['result']:
                expirations = data['optionChain']['result'][0]['expirationDates']
                logger.info(f"✓ 獲取到 {len(expirations)} 個到期日")
                return expirations
            
            logger.warning(f"沒有找到 {symbol} 的期權數據")
            return []
            
        except Exception as e:
            logger.error(f"獲取 {symbol} 到期日失敗: {e}")
            return []
    
    def get_option_chain(self, symbol: str, expiration: str = None) -> Optional[Dict]:
        """獲取期權鏈數據"""
        try:
            self._rate_limit()
            self._clear_session_if_needed()
            
            url = f"{self.API_BASE_URL}{self.OPTIONS_ENDPOINT}/{symbol}"
            params = {}
            if expiration:
                params['date'] = expiration
            
            logger.info(f"獲取 {symbol} 期權鏈...")
            
            response = self.session.get(url, params=params, timeout=15)
            
            if response.status_code == 429:
                logger.error("x 429 錯誤，清除 session 並重試")
                self.session.close()
                time.sleep(20)
                self.session = requests.Session()
                response = self.session.get(url, params=params, timeout=15)
            
            response.raise_for_status()
            data = response.json()
            
            if 'optionChain' in data and data['optionChain']['result']:
                logger.info(f"✓ 獲取 {symbol} 期權鏈成功")
                return data
            
            logger.warning(f"沒有找到 {symbol} 的期權鏈數據")
            return None
            
        except Exception as e:
            logger.error(f"獲取 {symbol} 期權鏈失敗: {e}")
            return None
    
    def get_quote_data(self, symbol: str) -> Optional[Dict]:
        """獲取股價數據"""
        try:
            self._rate_limit()
            self._clear_session_if_needed()
            
            url = f"{self.API_BASE_URL_V2}{self.CHART_ENDPOINT}/{symbol}"
            params = {
                'interval': '1d',
                'range': '1d'
            }
            
            logger.info(f"獲取 {symbol} 股價數據...")
            
            response = self.session.get(url, params=params, timeout=15)
            
            if response.status_code == 429:
                logger.error("x 429 錯誤，清除 session 並重試")
                self.session.close()
                time.sleep(20)
                self.session = requests.Session()
                response = self.session.get(url, params=params, timeout=15)
            
            response.raise_for_status()
            data = response.json()
            
            if 'chart' in data and data['chart']['result']:
                result = data['chart']['result'][0]
                meta = result.get('meta', {})
                
                return {
                    'symbol': symbol,
                    'current_price': meta.get('regularMarketPrice', 0),
                    'previous_close': meta.get('previousClose', 0),
                    'currency': meta.get('currency', 'USD'),
                    'market_state': meta.get('marketState', 'CLOSED'),
                    'exchange': meta.get('exchangeName', 'NASDAQ'),
                    'quote_type': meta.get('quoteType', 'EQUITY')
                }
            
            logger.warning(f"沒有找到 {symbol} 的股價數據")
            return None
            
        except Exception as e:
            logger.error(f"獲取 {symbol} 股價數據失敗: {e}")
            return None