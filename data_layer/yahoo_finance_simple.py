# -*- coding: utf-8 -*-
"""
Yahoo Finance 簡化客戶端 - 專門解決 429 錯誤
"""

import time
import logging
import requests
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class YahooFinanceSimpleClient:
    """
    簡化版 Yahoo Finance 客戶端
    專注於解決 429 錯誤問題
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.last_request_time = 0
        self.request_delay = 8.0  # 8秒間隔
        
        # 設置基本的 headers
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
        logger.info("* Yahoo Finance 簡化客戶端已初始化（8秒間隔）")
    
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
        """如果需要，清除 session"""
        try:
            # 每 5 次請求刷新一次 session
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
                
        except Exception as e:
            logger.warning(f"Session 刷新失敗: {e}")
    
    def get_chart_data(self, symbol: str) -> Optional[Dict]:
        """
        獲取股票圖表數據
        """
        try:
            # 應用速率限制
            self._rate_limit()
            
            # 定期清除 session
            self._clear_session_if_needed()
            
            url = f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}"
            params = {
                'period1': '0',
                'period2': str(int(time.time())),
                'interval': '1d',
                'includePrePost': 'true'
            }
            
            logger.info(f"Requesting chart data for {symbol}...")
            
            response = self.session.get(url, params=params, timeout=15)
            
            if response.status_code == 429:
                logger.error("x 429 錯誤 - 強制清除 session")
                # 強制清除 session
                self.session.close()
                time.sleep(20)  # 等待更長時間
                self.session = requests.Session()
                
                # 重試一次
                response = self.session.get(url, params=params, timeout=15)
            
            response.raise_for_status()
            
            data = response.json()
            
            if 'chart' in data and data['chart']['result']:
                return data
            
            logger.warning(f"No chart data for {symbol}")
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {symbol}: {e}")
            # 如果是 429，清除 session
            if "429" in str(e):
                logger.info("  檢測到 429，清除 session")
                self.session.close()
                time.sleep(20)
                self.session = requests.Session()
            return None
        except Exception as e:
            logger.error(f"Unexpected error for {symbol}: {e}")
            return None
    
    def get_option_chain(self, symbol: str) -> Optional[Dict]:
        """
        獲取期權鏈數據
        """
        try:
            # 應用速率限制
            self._rate_limit()
            
            # 定期清除 session  
            self._clear_session_if_needed()
            
            url = f"https://query1.finance.yahoo.com/v7/finance/options/{symbol}"
            params = {
                'date': None,  # 獲取所有到期日
                'strike': None,
                'optionType': 'ALL'
            }
            
            logger.info(f"Requesting option chain for {symbol}...")
            
            response = self.session.get(url, params=params, timeout=15)
            
            if response.status_code == 429:
                logger.error("x 429 錯誤 - 強制清除 session")
                self.session.close()
                time.sleep(20)
                self.session = requests.Session()
                
                response = self.session.get(url, params=params, timeout=15)
            
            response.raise_for_status()
            
            data = response.json()
            
            if 'optionChain' in data and data['optionChain']['result']:
                return data
            
            logger.warning(f"No option data for {symbol}")
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {symbol}: {e}")
            if "429" in str(e):
                self.session.close()
                time.sleep(20)
                self.session = requests.Session()
            return None
        except Exception as e:
            logger.error(f"Unexpected error for {symbol}: {e}")
            return None
    
    def get_quote_summary(self, symbol: str) -> Optional[Dict]:
        """
        獲取股票報價摘要
        """
        try:
            # 應用速率限制
            self._rate_limit()
            
            url = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{symbol}"
            params = {
                'modules': 'summaryDetail,defaultKeyStatistics,financialData,calendarEvents'
            }
            
            logger.info(f"Requesting quote summary for {symbol}...")
            
            response = self.session.get(url, params=params, timeout=15)
            
            if response.status_code == 429:
                logger.error("x 429 錯誤 - 強制清除 session")
                self.session.close()
                time.sleep(20)
                self.session = requests.Session()
                
                response = self.session.get(url, params=params, timeout=15)
            
            response.raise_for_status()
            
            data = response.json()
            
            if 'quoteSummary' in data and data['quoteSummary']['result']:
                return data
            
            logger.warning(f"No quote data for {symbol}")
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {symbol}: {e}")
            if "429" in str(e):
                self.session.close()
                time.sleep(20)
                self.session = requests.Session()
            return None
        except Exception as e:
            logger.error(f"Unexpected error for {symbol}: {e}")
            return None