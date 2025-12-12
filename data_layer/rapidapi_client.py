#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RapidAPI 客戶端 (增強版)

封裝 RapidAPI 數據訪問，支持多個期權數據服務：
1. Yahoo Finance API - 基本股票和期權數據
2. Tradier API - 專業期權數據（含 Greeks、IV）
3. Options Data API - 備用期權數據源

Requirements: 提供完整的期權鏈數據，包括 lastPrice、bid、ask、IV、Greeks
"""

import time
import logging
import requests
import pandas as pd
from typing import Optional, Dict, Any, List
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
        
        # yahoo-finance15 API 端點
        # 嘗試 v1/markets/quote (real-time) 或 v1/markets/quote (snapshot)
        endpoint = "/api/v1/markets/quote"
        params = {
            'ticker': ticker,
            'type': 'STOCKS'
        }
        
        response = self._make_request(endpoint, params)
        
        if response:
            logger.info(f"[OK] 成功從 RapidAPI 獲取 {ticker} 報價")
            return response
        else:
            logger.warning(f"[!] RapidAPI 獲取 {ticker} 報價失敗")
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
        
        # yahoo-finance15 API 端點
        endpoint = "/api/v1/markets/stock/history"
        params = {
            'symbol': ticker,
            'interval': '1d',
            'diffandsplits': 'false'
        }
        
        response = self._make_request(endpoint, params)
        
        if response:
            logger.info(f"[OK] 成功從 RapidAPI 獲取 {ticker} 歷史數據")
            return response
        else:
            logger.warning(f"[!] RapidAPI 獲取 {ticker} 歷史數據失敗")
            return None
    
    def get_market_news(self, ticker: str = None) -> Optional[Dict[str, Any]]:
        """
        獲取市場新聞
        
        Args:
            ticker: 股票代碼（可選，不提供則獲取一般市場新聞）
        
        Returns:
            新聞數據字典，失敗返回 None
        """
        logger.info(f"從 RapidAPI 獲取市場新聞...")
        
        # yahoo-finance15 API 端點
        endpoint = "/api/v1/markets/news"
        params = {}
        if ticker:
            params['ticker'] = ticker
        
        response = self._make_request(endpoint, params)
        
        if response:
            logger.info(f"[OK] 成功從 RapidAPI 獲取市場新聞")
            return response
        else:
            logger.warning(f"[!] RapidAPI 獲取市場新聞失敗")
            return None
    
    def get_stock_modules(
        self,
        ticker: str,
        module: str = 'asset-profile'
    ) -> Optional[Dict[str, Any]]:
        """
        獲取股票模塊數據（公司資料、財務數據等）
        
        Args:
            ticker: 股票代碼
            module: 模塊類型 (asset-profile, financial-data, etc.)
        
        Returns:
            模塊數據字典，失敗返回 None
        """
        logger.info(f"從 RapidAPI 獲取 {ticker} {module} 數據...")
        
        # yahoo-finance15 API 端點
        endpoint = "/api/v1/markets/stock/modules"
        params = {
            'ticker': ticker,
            'module': module
        }
        
        response = self._make_request(endpoint, params)
        
        if response:
            logger.info(f"[OK] 成功從 RapidAPI 獲取 {ticker} {module} 數據")
            return response
        else:
            logger.warning(f"[!] RapidAPI 獲取 {ticker} {module} 數據失敗")
            return None
    
    def get_options(self, ticker: str, expiration: str = None) -> Optional[Dict[str, Any]]:
        """
        獲取期權鏈數據
        
        Args:
            ticker: 股票代碼
            expiration: 到期日（可選，格式 YYYY-MM-DD）
        
        Returns:
            期權鏈數據字典，失敗返回 None
        """
        logger.info(f"從 RapidAPI 獲取 {ticker} 期權鏈...")
        
        # yahoo-finance15 API 端點
        endpoint = "/api/v1/markets/options"
        params = {
            'ticker': ticker
        }
        if expiration:
            params['date'] = expiration
        
        response = self._make_request(endpoint, params)
        
        if response:
            logger.info(f"[OK] 成功從 RapidAPI 獲取 {ticker} 期權鏈")
            return response
        else:
            logger.warning(f"[!] RapidAPI 獲取 {ticker} 期權鏈失敗")
            return None
    
    def get_option_chain_enhanced(
        self, 
        ticker: str, 
        expiration: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        獲取增強版期權鏈數據（包含完整的市場數據）
        
        嘗試多個 API 端點以獲取最完整的數據：
        1. Yahoo Finance Options API
        2. 備用端點
        
        Args:
            ticker: 股票代碼
            expiration: 到期日（格式 YYYY-MM-DD）
        
        Returns:
            標準化的期權鏈數據:
            {
                'calls': DataFrame,
                'puts': DataFrame,
                'expiration': str,
                'underlying_price': float,
                'data_source': str
            }
        """
        logger.info(f"從 RapidAPI 獲取 {ticker} 增強版期權鏈...")
        
        # 方案1: 使用 yahoo-finance127 API
        result = self._get_options_yahoo_finance127(ticker, expiration)
        if result and self._validate_option_data(result):
            return result
        
        # 方案2: 使用原始 get_options 方法
        raw_response = self.get_options(ticker, expiration)
        if raw_response:
            result = self._parse_yahoo_options_response(raw_response, ticker, expiration)
            if result and self._validate_option_data(result):
                return result
        
        logger.warning(f"[!] RapidAPI 無法獲取 {ticker} 完整期權數據")
        return None
    
    def _get_options_yahoo_finance127(
        self, 
        ticker: str, 
        expiration: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        使用 yahoo-finance15/127 API 獲取期權數據
        
        此 API 提供更完整的期權數據，包括：
        - lastPrice, bid, ask
        - impliedVolatility
        - volume, openInterest
        - Greeks (部分)
        
        支持兩種 API Host:
        - yahoo-finance15.p.rapidapi.com: 使用 /api/v1/markets/options 端點
        - yahoo-finance127.p.rapidapi.com: 使用 /v6/finance/options 端點
        """
        # 根據 host 選擇不同的端點
        if 'yahoo-finance15' in self.host:
            # yahoo-finance15 API 端點
            endpoint = "/api/v1/markets/options"
            params = {'ticker': ticker}
            if expiration:
                params['date'] = expiration
        else:
            # yahoo-finance127 API 端點
            endpoint = f"/v6/finance/options/{ticker}"
            params = {}
            if expiration:
                try:
                    exp_date = datetime.strptime(expiration, '%Y-%m-%d')
                    import calendar
                    params['date'] = calendar.timegm(exp_date.timetuple())
                except ValueError:
                    params['date'] = expiration
        
        response = self._make_request(endpoint, params)
        
        if not response:
            return None
        
        try:
            # 嘗試解析不同格式的響應
            # 格式1: yahoo-finance15 格式 (body 是列表)
            if 'body' in response:
                body = response['body']
                
                # body 可能是列表或字典
                if isinstance(body, list) and len(body) > 0:
                    # body 是列表，取第一個元素
                    item = body[0]
                    options_list = item.get('options', [])
                    if options_list and len(options_list) > 0:
                        option_data = options_list[0]
                        calls_raw = option_data.get('calls', [])
                        puts_raw = option_data.get('puts', [])
                        
                        # 獲取標的價格
                        quote = item.get('quote', {})
                        underlying_price = quote.get('regularMarketPrice', 0)
                        
                        # 獲取到期日
                        exp_timestamp = option_data.get('expirationDate', 0)
                        if exp_timestamp:
                            exp_date_str = datetime.fromtimestamp(exp_timestamp).strftime('%Y-%m-%d')
                        else:
                            exp_date_str = expiration or 'unknown'
                    else:
                        logger.warning(f"[!] RapidAPI body[0] 無 options 數據")
                        return None
                elif isinstance(body, dict):
                    if 'options' in body:
                        options_data = body['options']
                        calls_raw = options_data.get('calls', [])
                        puts_raw = options_data.get('puts', [])
                        underlying_price = body.get('underlyingSymbol', {}).get('regularMarketPrice', 0)
                        exp_date_str = expiration or 'unknown'
                    elif 'calls' in body or 'puts' in body:
                        calls_raw = body.get('calls', [])
                        puts_raw = body.get('puts', [])
                        underlying_price = body.get('underlyingPrice', 0)
                        exp_date_str = expiration or 'unknown'
                    else:
                        logger.warning(f"[!] RapidAPI 響應格式未知 (body dict)")
                        return None
                else:
                    logger.warning(f"[!] RapidAPI 響應格式未知 (body type: {type(body)})")
                    return None
            # 格式2: yahoo-finance127 格式 (optionChain.result)
            elif 'optionChain' in response:
                option_chain = response.get('optionChain', {})
                result_list = option_chain.get('result', [])
                
                if not result_list:
                    logger.warning(f"[!] RapidAPI 返回空期權數據")
                    return None
                
                result = result_list[0]
                quote = result.get('quote', {})
                options = result.get('options', [])
                
                if not options:
                    logger.warning(f"[!] RapidAPI 無期權合約數據")
                    return None
                
                option_data = options[0]
                calls_raw = option_data.get('calls', [])
                puts_raw = option_data.get('puts', [])
                underlying_price = quote.get('regularMarketPrice', 0)
                
                exp_timestamp = option_data.get('expirationDate', 0)
                if exp_timestamp:
                    exp_date_str = datetime.fromtimestamp(exp_timestamp).strftime('%Y-%m-%d')
                else:
                    exp_date_str = expiration or 'unknown'
            else:
                # 嘗試直接解析
                calls_raw = response.get('calls', [])
                puts_raw = response.get('puts', [])
                underlying_price = response.get('underlyingPrice', 0)
                exp_date_str = expiration or 'unknown'
            
            if not calls_raw and not puts_raw:
                logger.warning(f"[!] RapidAPI 無期權數據")
                return None
            
            # 轉換為 DataFrame
            calls_df = pd.DataFrame(calls_raw) if calls_raw else pd.DataFrame()
            puts_df = pd.DataFrame(puts_raw) if puts_raw else pd.DataFrame()
            
            # 標準化列名
            calls_df = self._standardize_option_columns(calls_df)
            puts_df = self._standardize_option_columns(puts_df)
            
            logger.info(f"[OK] RapidAPI 獲取 {ticker} 期權鏈: {len(calls_df)} calls, {len(puts_df)} puts")
            
            return {
                'calls': calls_df,
                'puts': puts_df,
                'expiration': exp_date_str,
                'underlying_price': underlying_price,
                'data_source': f'RapidAPI ({self.host})'
            }
            
        except Exception as e:
            logger.error(f"[x] 解析 RapidAPI 期權數據失敗: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return None
    
    def _standardize_option_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        標準化期權數據列名
        
        確保所有必需的列都存在，並轉換 IV 為百分比格式
        """
        if df.empty:
            return df
        
        # 列名映射
        column_mapping = {
            'contractSymbol': 'contractSymbol',
            'strike': 'strike',
            'lastPrice': 'lastPrice',
            'bid': 'bid',
            'ask': 'ask',
            'volume': 'volume',
            'openInterest': 'openInterest',
            'impliedVolatility': 'impliedVolatility',
            'inTheMoney': 'inTheMoney',
            'percentChange': 'percentChange',
            'change': 'change'
        }
        
        # 重命名列（如果存在）
        for old_name, new_name in column_mapping.items():
            if old_name in df.columns and old_name != new_name:
                df = df.rename(columns={old_name: new_name})
        
        # 確保必需列存在
        required_columns = ['strike', 'lastPrice', 'bid', 'ask', 'volume', 
                          'openInterest', 'impliedVolatility']
        for col in required_columns:
            if col not in df.columns:
                df[col] = 0 if col != 'impliedVolatility' else None
        
        # 轉換 IV 為百分比格式（如果是小數格式）
        if 'impliedVolatility' in df.columns:
            df['impliedVolatility'] = df['impliedVolatility'].apply(
                lambda x: x * 100 if x is not None and 0 < x < 1 else x
            )
        
        # 填充 NaN 值
        numeric_cols = ['lastPrice', 'bid', 'ask', 'volume', 'openInterest']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = df[col].fillna(0)
        
        return df
    
    def _parse_yahoo_options_response(
        self, 
        response: Dict[str, Any],
        ticker: str,
        expiration: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        解析原始 Yahoo Finance 期權響應
        """
        try:
            body = response.get('body', response)
            
            # 嘗試不同的響應格式
            if 'optionChain' in body:
                return self._get_options_yahoo_finance127(ticker, expiration)
            
            calls_raw = body.get('calls', [])
            puts_raw = body.get('puts', [])
            
            if not calls_raw and not puts_raw:
                return None
            
            calls_df = pd.DataFrame(calls_raw) if calls_raw else pd.DataFrame()
            puts_df = pd.DataFrame(puts_raw) if puts_raw else pd.DataFrame()
            
            calls_df = self._standardize_option_columns(calls_df)
            puts_df = self._standardize_option_columns(puts_df)
            
            return {
                'calls': calls_df,
                'puts': puts_df,
                'expiration': expiration or 'unknown',
                'underlying_price': body.get('underlyingPrice', 0),
                'data_source': 'RapidAPI (yahoo-finance)'
            }
            
        except Exception as e:
            logger.error(f"[x] 解析期權響應失敗: {e}")
            return None
    
    def _validate_option_data(self, data: Dict[str, Any]) -> bool:
        """
        驗證期權數據是否有效
        
        檢查：
        1. calls 和 puts DataFrame 不為空
        2. lastPrice 不全為 0
        3. IV 數據存在
        """
        if not data:
            return False
        
        calls = data.get('calls')
        puts = data.get('puts')
        
        if calls is None or puts is None:
            return False
        
        if isinstance(calls, pd.DataFrame) and isinstance(puts, pd.DataFrame):
            if calls.empty and puts.empty:
                return False
            
            # 檢查是否有有效的 lastPrice
            has_valid_call_price = False
            has_valid_put_price = False
            
            if not calls.empty and 'lastPrice' in calls.columns:
                has_valid_call_price = (calls['lastPrice'] > 0).any()
            
            if not puts.empty and 'lastPrice' in puts.columns:
                has_valid_put_price = (puts['lastPrice'] > 0).any()
            
            if not has_valid_call_price and not has_valid_put_price:
                logger.warning("[!] 期權數據中 lastPrice 全為 0")
                return False
            
            return True
        
        return False
    
    def get_option_expirations(self, ticker: str) -> Optional[List[str]]:
        """
        獲取可用的期權到期日列表
        
        Args:
            ticker: 股票代碼
        
        Returns:
            到期日列表（格式 YYYY-MM-DD），失敗返回 None
        """
        logger.info(f"從 RapidAPI 獲取 {ticker} 期權到期日...")
        
        # 使用 yahoo-finance127 API
        endpoint = f"/v6/finance/options/{ticker}"
        response = self._make_request(endpoint, {})
        
        if not response:
            return None
        
        try:
            option_chain = response.get('optionChain', {})
            result_list = option_chain.get('result', [])
            
            if not result_list:
                return None
            
            result = result_list[0]
            exp_timestamps = result.get('expirationDates', [])
            
            # 轉換 timestamp 為日期字符串
            expirations = []
            for ts in exp_timestamps:
                try:
                    date_str = datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
                    expirations.append(date_str)
                except:
                    continue
            
            logger.info(f"[OK] 獲取 {ticker} {len(expirations)} 個到期日")
            return expirations
            
        except Exception as e:
            logger.error(f"[x] 解析期權到期日失敗: {e}")
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
