#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Alpha Vantage API 客戶端

功能:
- 獲取股票歷史價格數據
- 獲取技術指標 (ATR, RSI, SMA, EMA 等)
- 獲取基本面數據

速率限制: 5次/分鐘, 500次/天 (免費版)

作者: Kiro
日期: 2025-11-25
版本: 1.0.0
"""

import requests
import pandas as pd
import logging
import time
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List

logger = logging.getLogger(__name__)

# 計數器持久化文件路徑
ALPHA_VANTAGE_COUNT_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'cache',
    'alpha_vantage_count.json'
)


class AlphaVantageClient:
    """
    Alpha Vantage API 客戶端
    
    提供:
    - 歷史價格數據 (日線、週線、月線)
    - 技術指標 (ATR, RSI, SMA, EMA, MACD, Bollinger Bands)
    - 基本面數據 (公司概況、財務報表)
    
    速率限制:
    - 免費版: 5次/分鐘, 500次/天
    - 建議請求間隔: 12秒以上
    """
    
    BASE_URL = "https://www.alphavantage.co/query"
    
    # 速率限制設置
    REQUESTS_PER_MINUTE = 5
    MIN_REQUEST_INTERVAL = 12.0  # 秒 (60/5 = 12)
    
    def __init__(self, api_key: str, request_delay: float = 12.0):
        """
        初始化 Alpha Vantage 客戶端
        
        參數:
            api_key: Alpha Vantage API Key
            request_delay: 請求間隔（秒），默認 12 秒
        """
        self.api_key = api_key
        self.request_delay = max(request_delay, self.MIN_REQUEST_INTERVAL)
        self.last_request_time = 0
        
        # 從持久化文件加載每日計數
        self.daily_request_count, self.daily_request_reset = self._load_daily_count()
        
        if not api_key:
            logger.warning("! Alpha Vantage API Key 未設置")
        else:
            logger.info(f"* Alpha Vantage 客戶端已初始化")
            logger.info(f"  請求間隔: {self.request_delay}秒")
            logger.info(f"  今日已用請求: {self.daily_request_count}/500")
    
    def _load_daily_count(self) -> tuple:
        """
        從持久化文件加載每日請求計數
        
        返回:
            tuple: (daily_count, reset_date)
        """
        try:
            if os.path.exists(ALPHA_VANTAGE_COUNT_FILE):
                with open(ALPHA_VANTAGE_COUNT_FILE, 'r') as f:
                    data = json.load(f)
                    saved_date = datetime.strptime(data.get('date', ''), '%Y-%m-%d').date()
                    today = datetime.now().date()
                    
                    # 如果是同一天，使用保存的計數
                    if saved_date == today:
                        count = data.get('count', 0)
                        logger.debug(f"  從緩存加載 Alpha Vantage 計數: {count}")
                        return count, today
                    else:
                        # 新的一天，重置計數
                        logger.debug(f"  新的一天，重置 Alpha Vantage 計數")
                        return 0, today
        except Exception as e:
            logger.debug(f"  加載 Alpha Vantage 計數失敗: {e}")
        
        return 0, datetime.now().date()
    
    def _save_daily_count(self):
        """
        保存每日請求計數到持久化文件
        """
        try:
            # 確保 cache 目錄存在
            cache_dir = os.path.dirname(ALPHA_VANTAGE_COUNT_FILE)
            if not os.path.exists(cache_dir):
                os.makedirs(cache_dir)
            
            data = {
                'date': self.daily_request_reset.strftime('%Y-%m-%d'),
                'count': self.daily_request_count,
                'updated_at': datetime.now().isoformat()
            }
            
            with open(ALPHA_VANTAGE_COUNT_FILE, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.debug(f"  保存 Alpha Vantage 計數: {self.daily_request_count}")
        except Exception as e:
            logger.warning(f"! 保存 Alpha Vantage 計數失敗: {e}")
    
    def _rate_limit(self):
        """速率限制"""
        # 檢查是否需要重置每日計數
        today = datetime.now().date()
        if today > self.daily_request_reset:
            self.daily_request_count = 0
            self.daily_request_reset = today
            self._save_daily_count()  # 保存重置後的計數
        
        # 檢查每日限制
        if self.daily_request_count >= 500:
            logger.error("x Alpha Vantage 每日請求限制已達 (500次/天)")
            raise Exception("Alpha Vantage daily limit exceeded")
        
        # 請求間隔控制
        elapsed = time.time() - self.last_request_time
        if elapsed < self.request_delay:
            sleep_time = self.request_delay - elapsed
            logger.debug(f"  速率限制延遲: {sleep_time:.2f}秒")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
        self.daily_request_count += 1
        
        # 每次請求後保存計數（確保持久化）
        self._save_daily_count()
    
    def _make_request(self, params: Dict[str, str]) -> Optional[Dict]:
        """
        發送 API 請求
        
        參數:
            params: 請求參數
        
        返回:
            dict: API 響應數據
        """
        try:
            self._rate_limit()
            
            params['apikey'] = self.api_key
            
            logger.debug(f"  請求 Alpha Vantage: {params.get('function', 'unknown')}")
            
            response = requests.get(
                self.BASE_URL,
                params=params,
                timeout=30
            )
            
            response.raise_for_status()
            data = response.json()
            
            # 檢查錯誤響應
            if 'Error Message' in data:
                logger.error(f"x Alpha Vantage 錯誤: {data['Error Message']}")
                return None
            
            if 'Note' in data:
                # API 限制警告
                logger.warning(f"! Alpha Vantage 警告: {data['Note']}")
                return None
            
            if 'Information' in data:
                logger.warning(f"! Alpha Vantage 信息: {data['Information']}")
                return None
            
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"x Alpha Vantage 請求失敗: {e}")
            return None
        except Exception as e:
            logger.error(f"x Alpha Vantage 錯誤: {e}")
            return None

    # ==================== 股票價格數據 ====================
    
    def get_daily_prices(
        self,
        ticker: str,
        outputsize: str = 'compact'
    ) -> Optional[pd.DataFrame]:
        """
        獲取每日股票價格數據
        
        參數:
            ticker: 股票代碼
            outputsize: 'compact' (最近100天) 或 'full' (20年+)
        
        返回:
            DataFrame: 包含 Open, High, Low, Close, Volume 的數據
        """
        try:
            logger.info(f"開始獲取 {ticker} 每日價格數據 (Alpha Vantage)...")
            
            params = {
                'function': 'TIME_SERIES_DAILY',
                'symbol': ticker,
                'outputsize': outputsize
            }
            
            data = self._make_request(params)
            
            if not data or 'Time Series (Daily)' not in data:
                logger.warning(f"! 未獲取到 {ticker} 的價格數據")
                return None
            
            # 轉換為 DataFrame
            time_series = data['Time Series (Daily)']
            df = pd.DataFrame.from_dict(time_series, orient='index')
            
            # 重命名列
            df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            
            # 轉換數據類型
            for col in ['Open', 'High', 'Low', 'Close']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            df['Volume'] = pd.to_numeric(df['Volume'], errors='coerce').astype(int)
            
            # 設置索引為日期
            df.index = pd.to_datetime(df.index)
            df = df.sort_index()
            
            logger.info(f"* 成功獲取 {ticker} 的 {len(df)} 條價格記錄")
            
            return df
            
        except Exception as e:
            logger.error(f"x 獲取 {ticker} 價格數據失敗: {e}")
            return None
    
    def get_quote(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        獲取股票即時報價
        
        參數:
            ticker: 股票代碼
        
        返回:
            dict: 包含價格、成交量等信息
        """
        try:
            logger.info(f"開始獲取 {ticker} 即時報價 (Alpha Vantage)...")
            
            params = {
                'function': 'GLOBAL_QUOTE',
                'symbol': ticker
            }
            
            data = self._make_request(params)
            
            if not data or 'Global Quote' not in data:
                logger.warning(f"! 未獲取到 {ticker} 的報價")
                return None
            
            quote = data['Global Quote']
            
            result = {
                'ticker': ticker,
                'current_price': float(quote.get('05. price', 0)),
                'open': float(quote.get('02. open', 0)),
                'high': float(quote.get('03. high', 0)),
                'low': float(quote.get('04. low', 0)),
                'volume': int(quote.get('06. volume', 0)),
                'previous_close': float(quote.get('08. previous close', 0)),
                'change': float(quote.get('09. change', 0)),
                'change_percent': quote.get('10. change percent', '0%').replace('%', ''),
                'latest_trading_day': quote.get('07. latest trading day', ''),
                'data_source': 'Alpha Vantage'
            }
            
            logger.info(f"* 成功獲取 {ticker} 報價: ${result['current_price']:.2f}")
            
            return result
            
        except Exception as e:
            logger.error(f"x 獲取 {ticker} 報價失敗: {e}")
            return None
    
    # ==================== 技術指標 ====================
    
    def get_atr(
        self,
        ticker: str,
        interval: str = 'daily',
        time_period: int = 14
    ) -> Optional[Dict[str, Any]]:
        """
        獲取 ATR (Average True Range) 指標
        
        參數:
            ticker: 股票代碼
            interval: 時間間隔 ('daily', 'weekly', 'monthly')
            time_period: 計算週期（默認 14）
        
        返回:
            dict: 包含最新 ATR 值和歷史數據
        """
        try:
            logger.info(f"開始獲取 {ticker} ATR 指標 (Alpha Vantage)...")
            
            params = {
                'function': 'ATR',
                'symbol': ticker,
                'interval': interval,
                'time_period': str(time_period)
            }
            
            data = self._make_request(params)
            
            if not data or 'Technical Analysis: ATR' not in data:
                logger.warning(f"! 未獲取到 {ticker} 的 ATR 數據")
                return None
            
            atr_data = data['Technical Analysis: ATR']
            
            # 獲取最新值
            latest_date = list(atr_data.keys())[0]
            latest_atr = float(atr_data[latest_date]['ATR'])
            
            # 獲取歷史數據（最近30天）
            history = []
            for date, values in list(atr_data.items())[:30]:
                history.append({
                    'date': date,
                    'atr': float(values['ATR'])
                })
            
            result = {
                'ticker': ticker,
                'atr': latest_atr,
                'date': latest_date,
                'time_period': time_period,
                'interval': interval,
                'history': history,
                'data_source': 'Alpha Vantage'
            }
            
            logger.info(f"* 成功獲取 {ticker} ATR: ${latest_atr:.2f}")
            
            return result
            
        except Exception as e:
            logger.error(f"x 獲取 {ticker} ATR 失敗: {e}")
            return None
    
    def get_rsi(
        self,
        ticker: str,
        interval: str = 'daily',
        time_period: int = 14,
        series_type: str = 'close'
    ) -> Optional[Dict[str, Any]]:
        """
        獲取 RSI (Relative Strength Index) 指標
        
        參數:
            ticker: 股票代碼
            interval: 時間間隔 ('daily', 'weekly', 'monthly')
            time_period: 計算週期（默認 14）
            series_type: 價格類型 ('close', 'open', 'high', 'low')
        
        返回:
            dict: 包含最新 RSI 值和歷史數據
        """
        try:
            logger.info(f"開始獲取 {ticker} RSI 指標 (Alpha Vantage)...")
            
            params = {
                'function': 'RSI',
                'symbol': ticker,
                'interval': interval,
                'time_period': str(time_period),
                'series_type': series_type
            }
            
            data = self._make_request(params)
            
            if not data or 'Technical Analysis: RSI' not in data:
                logger.warning(f"! 未獲取到 {ticker} 的 RSI 數據")
                return None
            
            rsi_data = data['Technical Analysis: RSI']
            
            # 獲取最新值
            latest_date = list(rsi_data.keys())[0]
            latest_rsi = float(rsi_data[latest_date]['RSI'])
            
            # 判斷超買超賣
            if latest_rsi >= 70:
                signal = 'overbought'
                signal_cn = '超買'
            elif latest_rsi <= 30:
                signal = 'oversold'
                signal_cn = '超賣'
            else:
                signal = 'neutral'
                signal_cn = '中性'
            
            # 獲取歷史數據（最近30天）
            history = []
            for date, values in list(rsi_data.items())[:30]:
                history.append({
                    'date': date,
                    'rsi': float(values['RSI'])
                })
            
            result = {
                'ticker': ticker,
                'rsi': latest_rsi,
                'signal': signal,
                'signal_cn': signal_cn,
                'date': latest_date,
                'time_period': time_period,
                'interval': interval,
                'history': history,
                'data_source': 'Alpha Vantage'
            }
            
            logger.info(f"* 成功獲取 {ticker} RSI: {latest_rsi:.2f} ({signal_cn})")
            
            return result
            
        except Exception as e:
            logger.error(f"x 獲取 {ticker} RSI 失敗: {e}")
            return None

    def get_sma(
        self,
        ticker: str,
        interval: str = 'daily',
        time_period: int = 20,
        series_type: str = 'close'
    ) -> Optional[Dict[str, Any]]:
        """
        獲取 SMA (Simple Moving Average) 指標
        
        參數:
            ticker: 股票代碼
            interval: 時間間隔
            time_period: 計算週期
            series_type: 價格類型
        
        返回:
            dict: 包含最新 SMA 值
        """
        try:
            logger.info(f"開始獲取 {ticker} SMA{time_period} (Alpha Vantage)...")
            
            params = {
                'function': 'SMA',
                'symbol': ticker,
                'interval': interval,
                'time_period': str(time_period),
                'series_type': series_type
            }
            
            data = self._make_request(params)
            
            if not data or 'Technical Analysis: SMA' not in data:
                logger.warning(f"! 未獲取到 {ticker} 的 SMA 數據")
                return None
            
            sma_data = data['Technical Analysis: SMA']
            latest_date = list(sma_data.keys())[0]
            latest_sma = float(sma_data[latest_date]['SMA'])
            
            result = {
                'ticker': ticker,
                'sma': latest_sma,
                'time_period': time_period,
                'date': latest_date,
                'data_source': 'Alpha Vantage'
            }
            
            logger.info(f"* 成功獲取 {ticker} SMA{time_period}: ${latest_sma:.2f}")
            
            return result
            
        except Exception as e:
            logger.error(f"x 獲取 {ticker} SMA 失敗: {e}")
            return None
    
    def get_ema(
        self,
        ticker: str,
        interval: str = 'daily',
        time_period: int = 20,
        series_type: str = 'close'
    ) -> Optional[Dict[str, Any]]:
        """
        獲取 EMA (Exponential Moving Average) 指標
        """
        try:
            logger.info(f"開始獲取 {ticker} EMA{time_period} (Alpha Vantage)...")
            
            params = {
                'function': 'EMA',
                'symbol': ticker,
                'interval': interval,
                'time_period': str(time_period),
                'series_type': series_type
            }
            
            data = self._make_request(params)
            
            if not data or 'Technical Analysis: EMA' not in data:
                return None
            
            ema_data = data['Technical Analysis: EMA']
            latest_date = list(ema_data.keys())[0]
            latest_ema = float(ema_data[latest_date]['EMA'])
            
            result = {
                'ticker': ticker,
                'ema': latest_ema,
                'time_period': time_period,
                'date': latest_date,
                'data_source': 'Alpha Vantage'
            }
            
            logger.info(f"* 成功獲取 {ticker} EMA{time_period}: ${latest_ema:.2f}")
            
            return result
            
        except Exception as e:
            logger.error(f"x 獲取 {ticker} EMA 失敗: {e}")
            return None
    
    # ==================== 基本面數據 ====================
    
    def get_company_overview(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        獲取公司概況和基本面數據
        
        參數:
            ticker: 股票代碼
        
        返回:
            dict: 包含 PE, EPS, Beta, 市值等信息
        """
        try:
            logger.info(f"開始獲取 {ticker} 公司概況 (Alpha Vantage)...")
            
            params = {
                'function': 'OVERVIEW',
                'symbol': ticker
            }
            
            data = self._make_request(params)
            
            if not data or 'Symbol' not in data:
                logger.warning(f"! 未獲取到 {ticker} 的公司概況")
                return None
            
            # 安全轉換函數
            def safe_float(value, default=0.0):
                try:
                    if value in ['None', '-', '', None]:
                        return default
                    return float(value)
                except (ValueError, TypeError):
                    return default
            
            def safe_int(value, default=0):
                try:
                    if value in ['None', '-', '', None]:
                        return default
                    return int(value)
                except (ValueError, TypeError):
                    return default
            
            result = {
                'ticker': ticker,
                'company_name': data.get('Name', ''),
                'description': data.get('Description', ''),
                'sector': data.get('Sector', ''),
                'industry': data.get('Industry', ''),
                'market_cap': safe_int(data.get('MarketCapitalization')),
                'pe_ratio': safe_float(data.get('PERatio')),
                'forward_pe': safe_float(data.get('ForwardPE')),
                'peg_ratio': safe_float(data.get('PEGRatio')),
                'eps': safe_float(data.get('EPS')),
                'beta': safe_float(data.get('Beta')),
                'dividend_yield': safe_float(data.get('DividendYield')),
                'dividend_per_share': safe_float(data.get('DividendPerShare')),
                'profit_margin': safe_float(data.get('ProfitMargin')),
                'operating_margin': safe_float(data.get('OperatingMarginTTM')),
                'roe': safe_float(data.get('ReturnOnEquityTTM')),
                'roa': safe_float(data.get('ReturnOnAssetsTTM')),
                'revenue': safe_int(data.get('RevenueTTM')),
                'gross_profit': safe_int(data.get('GrossProfitTTM')),
                'book_value': safe_float(data.get('BookValue')),
                'price_to_book': safe_float(data.get('PriceToBookRatio')),
                '52_week_high': safe_float(data.get('52WeekHigh')),
                '52_week_low': safe_float(data.get('52WeekLow')),
                '50_day_ma': safe_float(data.get('50DayMovingAverage')),
                '200_day_ma': safe_float(data.get('200DayMovingAverage')),
                'shares_outstanding': safe_int(data.get('SharesOutstanding')),
                'ex_dividend_date': data.get('ExDividendDate', ''),
                'data_source': 'Alpha Vantage'
            }
            
            logger.info(f"* 成功獲取 {ticker} 公司概況")
            logger.info(f"  公司: {result['company_name']}")
            logger.info(f"  PE: {result['pe_ratio']:.2f}")
            logger.info(f"  EPS: ${result['eps']:.2f}")
            
            return result
            
        except Exception as e:
            logger.error(f"x 獲取 {ticker} 公司概況失敗: {e}")
            return None
    
    # ==================== 批量獲取 ====================
    
    def get_technical_indicators(
        self,
        ticker: str,
        indicators: List[str] = None
    ) -> Dict[str, Any]:
        """
        批量獲取多個技術指標
        
        參數:
            ticker: 股票代碼
            indicators: 指標列表 ['atr', 'rsi', 'sma', 'ema']
        
        返回:
            dict: 包含所有請求的指標
        """
        if indicators is None:
            indicators = ['atr', 'rsi']
        
        logger.info(f"開始批量獲取 {ticker} 技術指標: {indicators}")
        
        results = {
            'ticker': ticker,
            'data_source': 'Alpha Vantage',
            'timestamp': datetime.now().isoformat()
        }
        
        for indicator in indicators:
            try:
                if indicator.lower() == 'atr':
                    data = self.get_atr(ticker)
                    if data:
                        results['atr'] = data['atr']
                        results['atr_data'] = data
                
                elif indicator.lower() == 'rsi':
                    data = self.get_rsi(ticker)
                    if data:
                        results['rsi'] = data['rsi']
                        results['rsi_signal'] = data['signal_cn']
                        results['rsi_data'] = data
                
                elif indicator.lower() == 'sma':
                    data = self.get_sma(ticker)
                    if data:
                        results['sma'] = data['sma']
                        results['sma_data'] = data
                
                elif indicator.lower() == 'ema':
                    data = self.get_ema(ticker)
                    if data:
                        results['ema'] = data['ema']
                        results['ema_data'] = data
                
            except Exception as e:
                logger.warning(f"! 獲取 {indicator} 失敗: {e}")
                results[indicator] = None
        
        logger.info(f"* 批量獲取完成: {len([k for k in results if k not in ['ticker', 'data_source', 'timestamp']])} 個指標")
        
        return results


# 使用示例
if __name__ == "__main__":
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    from config.settings import settings
    
    logging.basicConfig(level=logging.INFO)
    
    # 創建客戶端
    client = AlphaVantageClient(api_key=settings.ALPHA_VANTAGE_API_KEY)
    
    # 測試獲取報價
    print("\n" + "=" * 60)
    print("測試 Alpha Vantage API")
    print("=" * 60)
    
    ticker = "AAPL"
    
    # 獲取報價
    quote = client.get_quote(ticker)
    if quote:
        print(f"\n{ticker} 報價:")
        print(f"  價格: ${quote['current_price']:.2f}")
        print(f"  變化: {quote['change_percent']}%")
    
    # 獲取 ATR
    atr = client.get_atr(ticker)
    if atr:
        print(f"\n{ticker} ATR:")
        print(f"  ATR(14): ${atr['atr']:.2f}")
    
    # 獲取 RSI
    rsi = client.get_rsi(ticker)
    if rsi:
        print(f"\n{ticker} RSI:")
        print(f"  RSI(14): {rsi['rsi']:.2f} ({rsi['signal_cn']})")
    
    print("\n" + "=" * 60)
