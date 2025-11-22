#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Yahoo Finance API 客户端（简化版，无需 OAuth）
使用公开的 Yahoo Finance API
"""

import time
import logging
from typing import Optional, Dict, Any
import requests

# 配置日志
logger = logging.getLogger(__name__)


class YahooFinanceV2Client:
    """Yahoo Finance API 客户端（简化版，无需 OAuth）"""
    
    # Yahoo Finance API 端点
    API_BASE_URL = 'https://query1.finance.yahoo.com'
    CHART_ENDPOINT = '/v8/finance/chart'
    OPTIONS_ENDPOINT = '/v7/finance/options'
    
    def __init__(
        self, 
        request_delay: float = 1.0,
        max_retries: int = 3,
        user_agent: Optional[str] = None
    ):
        """
        初始化客户端
        
        Args:
            request_delay: 请求间隔（秒），默认 1.0
            max_retries: 最大重试次数，默认 3
            user_agent: 自定义 User-Agent，默认使用浏览器 UA
        """
        self.request_delay = request_delay
        self.max_retries = max_retries
        self.last_request_time = 0
        
        # 设置 User-Agent（关键！）
        self.headers = {
            'User-Agent': user_agent or self._get_default_user_agent()
        }
        
        logger.info(f"Yahoo Finance 客户端已初始化 (User-Agent: {self.headers['User-Agent'][:50]}...)")
    
    def _get_default_user_agent(self) -> str:
        """获取默认 User-Agent"""
        return 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    
    def _rate_limit_delay(self) -> None:
        """请求速率限制"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.request_delay:
            time.sleep(self.request_delay - elapsed)
        self.last_request_time = time.time()
    
    def _make_request(
        self, 
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None,
        retry_count: int = 0
    ) -> Dict[str, Any]:
        """
        发送 API 请求（包含重试逻辑）
        
        Args:
            endpoint: API 端点路径
            params: 查询参数
            retry_count: 当前重试次数
            
        Returns:
            API 响应（JSON）
            
        Raises:
            requests.exceptions.RequestException: API 错误
        """
        self._rate_limit_delay()
        
        url = f"{self.API_BASE_URL}{endpoint}"
        start_time = time.time()
        
        try:
            logger.info(f"Requesting {url} with params {params}")
            logger.debug(f"User-Agent: {self.headers.get('User-Agent', 'MISSING')}")
            
            response = requests.get(url, params=params, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            elapsed_time = time.time() - start_time
            if retry_count > 0:
                logger.info(
                    f"* Request succeeded after {retry_count} retries. "
                    f"Response time: {elapsed_time:.2f}s"
                )
            else:
                logger.info(f"* Request succeeded. Response time: {elapsed_time:.2f}s")
            
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code
            response_body = e.response.text[:500] if hasattr(e.response, 'text') else 'N/A'
            
            # 完整的錯誤日誌（狀態碼、響應體、URL）
            logger.error(
                f"x HTTP Error {status_code} - URL: {url} - "
                f"Response: {response_body}"
            )
            
            # 429: 速率限制 - 指数退避
            if status_code == 429:
                if retry_count < self.max_retries:
                    wait_time = 30 * (2 ** retry_count)  # 30, 60, 120
                    
                    # 重試日誌（重試次數、等待時間）
                    logger.warning(
                        f"Rate limit (429) - Retry {retry_count + 1}/{self.max_retries}. "
                        f"Waiting {wait_time}s (exponential backoff)..."
                    )
                    
                    # User-Agent 檢查日誌
                    logger.warning(f"User-Agent check: {self.headers.get('User-Agent', 'MISSING')}")
                    
                    time.sleep(wait_time)
                    return self._make_request(endpoint, params, retry_count + 1)
                else:
                    logger.error(
                        f"x Request failed after {self.max_retries} retries. "
                        f"Status: {status_code}, URL: {url}"
                    )
                    raise
            
            # 5xx: 服务器错误 - 线性退避
            elif 500 <= status_code < 600:
                if retry_count < self.max_retries:
                    wait_time = 10  # 固定 10 秒
                    
                    # 重試日誌（重試次數、等待時間）
                    logger.warning(
                        f"Server error ({status_code}) - Retry {retry_count + 1}/{self.max_retries}. "
                        f"Waiting {wait_time}s (linear backoff)..."
                    )
                    
                    time.sleep(wait_time)
                    return self._make_request(endpoint, params, retry_count + 1)
                else:
                    logger.error(
                        f"x Request failed after {self.max_retries} retries. "
                        f"Status: {status_code}, URL: {url}, Response: {response_body}"
                    )
                    raise
            
            # 4xx: 客户端错误（除 429）- 不重试
            else:
                logger.error(
                    f"x Client error ({status_code}) - No retry. "
                    f"URL: {url}, Response: {response_body}"
                )
                raise
        
        except requests.exceptions.Timeout as e:
            logger.error(
                f"x Request timeout after {time.time() - start_time:.2f}s - "
                f"URL: {url}, Error: {str(e)}"
            )
            raise
        
        except requests.exceptions.ConnectionError as e:
            logger.error(
                f"x Connection error - URL: {url}, Error: {str(e)}"
            )
            raise
        
        except requests.exceptions.RequestException as e:
            logger.error(
                f"x Network error - URL: {url}, Error: {str(e)}"
            )
            raise
    
    # ==================== 股票数据 API ====================
    
    def get_quote(self, symbol: str) -> Dict[str, Any]:
        """
        获取股票报价
        
        Args:
            symbol: 股票代码
        
        Returns:
            dict: 报价数据
        """
        # 使用 chart API 获取报价数据
        endpoint = f"{self.CHART_ENDPOINT}/{symbol}"
        params = {
            'interval': '1d',
            'range': '1d'
        }
        
        return self._make_request(endpoint, params)
    
    def get_historical_data(
        self, 
        symbol: str, 
        interval: str = '1d',
        period: str = '1mo'
    ) -> Dict[str, Any]:
        """
        获取历史数据
        
        Args:
            symbol: 股票代码
            interval: 时间间隔（1m, 5m, 1d, 1wk, 1mo）
            period: 时间范围（1d, 5d, 1mo, 3mo, 1y）
        
        Returns:
            dict: 历史数据
        """
        endpoint = f"{self.CHART_ENDPOINT}/{symbol}"
        params = {
            'interval': interval,
            'range': period
        }
        
        return self._make_request(endpoint, params)
    
    def get_option_chain(
        self, 
        symbol: str, 
        expiration: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取期权链
        
        Args:
            symbol: 股票代码
            expiration: 到期日（可选）
        
        Returns:
            dict: 期权链数据
        """
        endpoint = f"{self.OPTIONS_ENDPOINT}/{symbol}"
        params = {}
        if expiration:
            params['date'] = expiration
        
        return self._make_request(endpoint, params)



class YahooDataParser:
    """
    Yahoo Finance 数据解析器
    
    提供統一的接口解析 Yahoo Finance API 的各種響應格式。
    所有解析方法都返回標準化的數據結構，便於系統其他部分使用。
    """
    
    @staticmethod
    def parse_quote(response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        解析股票报价响应
        
        Args:
            response: Yahoo Finance Chart API 原始響應
        
        Returns:
            標準化的股票數據字典，包含以下字段：
            - symbol: 股票代碼
            - current_price: 當前價格
            - open: 開盤價
            - high: 最高價
            - low: 最低價
            - volume: 成交量
            - previous_close: 前收盤價
            - market_cap: 市值（Chart API 不提供，返回 0）
            - pe_ratio: 市盈率（Chart API 不提供，返回 0）
            - dividend_rate: 股息率（Chart API 不提供，返回 0）
            - eps: 每股收益（Chart API 不提供，返回 0）
            - fifty_two_week_high: 52週最高價（Chart API 不提供，返回 0）
            - fifty_two_week_low: 52週最低價（Chart API 不提供，返回 0）
            - beta: Beta 係數（Chart API 不提供，返回 0）
            - company_name: 公司名稱（Chart API 不提供，返回空字符串）
            - sector: 行業（Chart API 不提供，返回空字符串）
            - industry: 子行業（Chart API 不提供，返回空字符串）
            - data_source: 數據來源標記 ('yahoo_finance')
            
            解析失敗返回 None
            
        Note:
            Chart API 主要提供價格數據，不包含基本面數據。
            如需完整的基本面數據，應使用 quoteSummary API 或降級到其他數據源。
        """
        try:
            # 驗證響應結構
            if not response or not isinstance(response, dict):
                logger.error("x Invalid response: not a dict")
                return None
            
            chart = response.get('chart', {})
            if not chart:
                logger.error("x Missing 'chart' key in response")
                return None
            
            result = chart.get('result', [])
            if not result or len(result) == 0:
                logger.error("x Empty result in quote response")
                return None
            
            data = result[0]
            meta = data.get('meta', {})
            
            if not meta:
                logger.warning("! Missing 'meta' in response, using empty dict")
            
            # 提取價格數據
            parsed_data = {
                'symbol': meta.get('symbol', ''),
                'current_price': meta.get('regularMarketPrice', 0),
                'open': meta.get('regularMarketOpen', 0),
                'high': meta.get('regularMarketDayHigh', 0),
                'low': meta.get('regularMarketDayLow', 0),
                'volume': meta.get('regularMarketVolume', 0),
                'previous_close': meta.get('previousClose', 0),
                # Chart API 不提供的字段（使用默認值）
                'market_cap': 0,
                'pe_ratio': 0,
                'dividend_rate': 0,
                'eps': 0,
                'fifty_two_week_high': 0,
                'fifty_two_week_low': 0,
                'beta': 0,
                'company_name': '',
                'sector': '',
                'industry': '',
                'data_source': 'yahoo_finance'
            }
            
            # 驗證關鍵字段
            if not parsed_data['symbol']:
                logger.warning("! Missing symbol in parsed data")
            
            if parsed_data['current_price'] == 0:
                logger.warning("! Current price is 0, data may be incomplete")
            
            logger.debug(f"* Successfully parsed quote for {parsed_data['symbol']}")
            return parsed_data
            
        except KeyError as e:
            logger.error(f"x Missing required key in response: {e}")
            return None
        except TypeError as e:
            logger.error(f"x Type error while parsing quote: {e}")
            return None
        except Exception as e:
            logger.error(f"x Unexpected error parsing quote response: {e}")
            logger.debug(f"Response structure: {response}")
            return None
    
    @staticmethod
    def parse_option_chain(response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        解析期权链响应
        
        Args:
            response: Yahoo Finance Options API 原始響應
        
        Returns:
            標準化的期權數據字典，包含以下字段：
            - calls: Call 期權列表（list of dict）
            - puts: Put 期權列表（list of dict）
            - expiration: 到期日期（Unix timestamp 或日期字符串）
            - data_source: 數據來源標記 ('yahoo_finance')
            
            每個期權包含：
            - contractSymbol: 合約代碼
            - strike: 行使價
            - lastPrice: 最新價格
            - bid: 買價
            - ask: 賣價
            - volume: 成交量
            - openInterest: 未平倉量
            - impliedVolatility: 隱含波動率
            
            解析失敗返回 None
        """
        try:
            # 驗證響應結構
            if not response or not isinstance(response, dict):
                logger.error("x Invalid response: not a dict")
                return None
            
            option_chain = response.get('optionChain', {})
            if not option_chain:
                logger.error("x Missing 'optionChain' key in response")
                return None
            
            result = option_chain.get('result', [])
            if not result or len(result) == 0:
                logger.error("x Empty result in option chain response")
                return None
            
            data = result[0]
            options = data.get('options', [])
            
            if not options or len(options) == 0:
                logger.error("x No options data in response")
                return None
            
            option_data = options[0]
            
            # 提取 calls 和 puts
            calls = option_data.get('calls', [])
            puts = option_data.get('puts', [])
            
            if not calls and not puts:
                logger.warning("! Both calls and puts are empty")
            
            parsed_data = {
                'calls': calls,
                'puts': puts,
                'expiration': option_data.get('expirationDate', ''),
                'data_source': 'yahoo_finance'
            }
            
            logger.debug(
                f"* Successfully parsed option chain: "
                f"{len(calls)} calls, {len(puts)} puts"
            )
            return parsed_data
            
        except KeyError as e:
            logger.error(f"x Missing required key in response: {e}")
            return None
        except TypeError as e:
            logger.error(f"x Type error while parsing option chain: {e}")
            return None
        except Exception as e:
            logger.error(f"x Unexpected error parsing option chain response: {e}")
            logger.debug(f"Response structure: {response}")
            return None
    
    @staticmethod
    def parse_historical_data(response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        解析历史数据响应
        
        Args:
            response: Yahoo Finance Chart API 原始響應
        
        Returns:
            歷史數據字典，包含以下字段：
            - timestamps: Unix 時間戳列表
            - open: 開盤價列表
            - high: 最高價列表
            - low: 最低價列表
            - close: 收盤價列表
            - volume: 成交量列表
            - data_source: 數據來源標記 ('yahoo_finance')
            
            所有列表長度相同，對應同一時間序列。
            解析失敗返回 None
            
        Note:
            可以使用 pandas.DataFrame 將數據轉換為表格格式：
            ```python
            import pandas as pd
            df = pd.DataFrame(parsed_data)
            df['date'] = pd.to_datetime(df['timestamps'], unit='s')
            ```
        """
        try:
            # 驗證響應結構
            if not response or not isinstance(response, dict):
                logger.error("x Invalid response: not a dict")
                return None
            
            chart = response.get('chart', {})
            if not chart:
                logger.error("x Missing 'chart' key in response")
                return None
            
            result = chart.get('result', [])
            if not result or len(result) == 0:
                logger.error("x Empty result in historical data response")
                return None
            
            data = result[0]
            timestamps = data.get('timestamp', [])
            
            if not timestamps:
                logger.error("x No timestamps in historical data")
                return None
            
            indicators = data.get('indicators', {})
            if not indicators:
                logger.error("x Missing 'indicators' in response")
                return None
            
            quote_list = indicators.get('quote', [])
            if not quote_list or len(quote_list) == 0:
                logger.error("x No quote data in indicators")
                return None
            
            quote = quote_list[0]
            
            # 提取 OHLCV 數據
            parsed_data = {
                'timestamps': timestamps,
                'open': quote.get('open', []),
                'high': quote.get('high', []),
                'low': quote.get('low', []),
                'close': quote.get('close', []),
                'volume': quote.get('volume', []),
                'data_source': 'yahoo_finance'
            }
            
            # 驗證數據長度一致性
            data_length = len(timestamps)
            for key in ['open', 'high', 'low', 'close', 'volume']:
                if len(parsed_data[key]) != data_length:
                    logger.warning(
                        f"! Length mismatch: {key} has {len(parsed_data[key])} "
                        f"items but timestamps has {data_length}"
                    )
            
            logger.debug(f"* Successfully parsed {data_length} historical data points")
            return parsed_data
            
        except KeyError as e:
            logger.error(f"x Missing required key in response: {e}")
            return None
        except TypeError as e:
            logger.error(f"x Type error while parsing historical data: {e}")
            return None
        except IndexError as e:
            logger.error(f"x Index error while parsing historical data: {e}")
            return None
        except Exception as e:
            logger.error(f"x Unexpected error parsing historical data response: {e}")
            logger.debug(f"Response structure: {response}")
            return None


# 使用示例
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("\n" + "=" * 70)
    print("Yahoo Finance 客户端示例（简化版，无需 OAuth）")
    print("=" * 70)
    
    # 初始化客户端（无需 OAuth 参数）
    client = YahooFinanceV2Client()
    
    # 测试获取股票数据
    print("\n测试获取 AAPL 股票数据...")
    try:
        response = client.get_quote('AAPL')
        stock_info = YahooDataParser.parse_quote(response)
        
        if stock_info:
            print(f"\n股票代码: {stock_info['symbol']}")
            print(f"当前股价: ${stock_info['current_price']:.2f}")
            print(f"开盘价: ${stock_info['open']:.2f}")
            print(f"成交量: {stock_info['volume']:,}")
            print("\n* Yahoo Finance API 运行正常")
        else:
            print("\n x 数据解析失败")
    except Exception as e:
        print(f"\n x API 调用失败: {e}")

