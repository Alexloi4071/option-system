# data_layer/data_fetcher.py
"""
完整數據獲取類 (第1階段完整實現)
集成 Yahoo Finance 2.0 OAuth API
"""

import yfinance as yf
import pandas as pd
from fredapi import Fred
import finnhub
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
import logging
import sys
import os

# 添加config模塊到路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import settings
from config.api_config import api_config

# 尝试导入交易日计算器（可选）
try:
    from utils.trading_days import TradingDaysCalculator
    TRADING_DAYS_AVAILABLE = True
except ImportError:
    TRADING_DAYS_AVAILABLE = False
    TradingDaysCalculator = None
    logger_init = logging.getLogger(__name__)
    logger_init.warning("交易日计算器不可用（缺少 pandas_market_calendars），将使用日历日计算")

# 尝试导入 Yahoo Finance 客户端（简化版）
try:
    from data_layer.yahoo_finance_v2_client import YahooFinanceV2Client, YahooDataParser
    YAHOO_V2_AVAILABLE = True
except ImportError:
    YAHOO_V2_AVAILABLE = False
    logger_init = logging.getLogger(__name__)
    logger_init.warning("Yahoo Finance 客户端不可用，将使用 yfinance")

# 尝试导入 IBKR 客户端
try:
    from data_layer.ibkr_client import IBKRClient
    IBKR_AVAILABLE = True
except ImportError:
    IBKR_AVAILABLE = False
    logger_init = logging.getLogger(__name__)
    logger_init.warning("IBKR 客户端不可用，将使用其他数据源")

# 配置日誌
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"{settings.LOG_DIR}data_fetcher_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)


class DataFetcher:
    """完整數據獲取類（支持多数据源降级）"""
    
    def __init__(self, use_ibkr: bool = None):
        """
        初始化數據獲取器
        
        參數:
            use_ibkr: 是否使用 IBKR（None 時從 settings 讀取）
        """
        self.yahoo_v2_client = None
        self.yfinance_client = None
        self.fred_client = None
        self.finnhub_client = None
        self.ibkr_client = None
        self.finviz_scraper = None  # Finviz 抓取器
        self.last_request_time = 0
        self.request_delay = settings.REQUEST_DELAY
        
        # API 故障記錄（用於報告）
        self.api_failures = {}  # {api_name: [error_messages]}
        self.fallback_used = {}  # {data_type: [used_sources]}
        
        # 初始化交易日计算器（如果可用）
        if TRADING_DAYS_AVAILABLE and TradingDaysCalculator:
            try:
                self.trading_days_calc = TradingDaysCalculator(exchange='NYSE')
            except Exception as exc:
                logger.warning("! 無法初始化交易日曆: %s", exc)
                self.trading_days_calc = None
        else:
            self.trading_days_calc = None
            logger.info("i 交易日计算器不可用，将使用日历日计算")
        
        # 決定是否使用 IBKR
        if use_ibkr is None:
            use_ibkr = settings.IBKR_ENABLED
        
        self.use_ibkr = use_ibkr and IBKR_AVAILABLE
        
        # 初始化自主計算模塊（用於降級策略）
        try:
            from calculation_layer.module15_black_scholes import BlackScholesCalculator
            from calculation_layer.module16_greeks import GreeksCalculator
            from calculation_layer.module17_implied_volatility import ImpliedVolatilityCalculator
            
            self.bs_calculator = BlackScholesCalculator()
            self.greeks_calculator = GreeksCalculator()
            self.iv_calculator = ImpliedVolatilityCalculator()
            logger.info("* 自主計算模塊已初始化（BS, Greeks, IV）")
        except ImportError as e:
            logger.warning(f"! 自主計算模塊不可用: {e}，降級策略將受限")
            self.bs_calculator = None
            self.greeks_calculator = None
            self.iv_calculator = None
        
        self.initialization_status = self._initialize_clients()
        logger.info("DataFetcher已初始化")
    
    def _initialize_clients(self):
        """初始化各API客户端"""
        try:
            # IBKR 客户端（如果启用）
            if self.use_ibkr:
                try:
                    port = settings.IBKR_PORT_PAPER if settings.IBKR_ENABLED else settings.IBKR_PORT_LIVE
                    mode = 'paper' if port == settings.IBKR_PORT_PAPER else 'live'
                    
                    self.ibkr_client = IBKRClient(
                        host=settings.IBKR_HOST,
                        port=port,
                        client_id=settings.IBKR_CLIENT_ID,
                        mode=mode
                    )
                    
                    # 尝试连接（不强制，失败时使用降级方案）
                    if self.ibkr_client.connect():
                        logger.info("* IBKR 客户端已初始化并连接")
                    else:
                        logger.warning("! IBKR 客户端初始化但未连接，将使用降级方案")
                        # 不设置为 None，保留客户端以便后续重试
                except Exception as e:
                    logger.warning(f"! IBKR 初始化失败: {e}，将使用降级方案")
                    self._record_api_failure('ibkr', str(e))
                    self.ibkr_client = None
            else:
                logger.info("i IBKR 未启用，将使用其他数据源")
            
            # Yahoo Finance 客户端（简化版，无需 OAuth）
            if YAHOO_V2_AVAILABLE:
                try:
                    self.yahoo_v2_client = YahooFinanceV2Client(
                        request_delay=self.request_delay,
                        max_retries=3
                    )
                    logger.info("* Yahoo Finance 客户端已初始化（简化版，无需 OAuth）")
                except Exception as e:
                    logger.warning(f"! Yahoo Finance 初始化失败: {e}")
                    self._record_api_failure('yahoo_v2', str(e))
                    self.yahoo_v2_client = None
            
            # yfinance 作为降级方案
            self.yfinance_client = yf
            logger.info("* yfinance客户端已初始化（降级方案）")
            
            # FRED客户端
            if settings.FRED_API_KEY:
                try:
                    self.fred_client = Fred(api_key=settings.FRED_API_KEY)
                    logger.info("* FRED客户端已初始化")
                except Exception as e:
                    logger.warning(f"! FRED 初始化失败: {e}")
                    self._record_api_failure('FRED', str(e))
                    self.fred_client = None
            else:
                logger.warning("! FRED_API_KEY未設置，FRED功能將不可用")
            
            # Finnhub客户端
            if settings.FINNHUB_API_KEY:
                try:
                    self.finnhub_client = finnhub.Client(api_key=settings.FINNHUB_API_KEY)
                    logger.info("* Finnhub客户端已初始化")
                except Exception as e:
                    logger.warning(f"! Finnhub 初始化失败: {e}")
                    self._record_api_failure('finnhub', str(e))
                    self.finnhub_client = None
            else:
                logger.warning("! FINNHUB_API_KEY未設置，Finnhub功能將不可用")
            
            # Finviz 抓取器（無需 API Key，免費使用）
            try:
                from data_layer.finviz_scraper import FinvizScraper
                self.finviz_scraper = FinvizScraper(request_delay=self.request_delay)
                logger.info("* Finviz 抓取器已初始化")
            except Exception as e:
                logger.warning(f"! Finviz 初始化失敗: {e}")
                self._record_api_failure('Finviz', str(e))
                self.finviz_scraper = None
            
            # RapidAPI 客戶端（備用數據源）
            if settings.RAPIDAPI_KEY and settings.RAPIDAPI_HOST:
                try:
                    from data_layer.rapidapi_client import RapidAPIClient
                    self.rapidapi_client = RapidAPIClient(
                        api_key=settings.RAPIDAPI_KEY,
                        host=settings.RAPIDAPI_HOST,
                        request_delay=self.request_delay,
                        monthly_limit=500  # 免費版限制
                    )
                    logger.info("* RapidAPI 客戶端已初始化")
                except Exception as e:
                    logger.warning(f"! RapidAPI 初始化失敗: {e}")
                    self._record_api_failure('RapidAPI', str(e))
                    self.rapidapi_client = None
            else:
                logger.info("i RapidAPI 未配置，跳過初始化")
                self.rapidapi_client = None
            
            return True
        except Exception as e:
            logger.error(f"x 客户端初始化失敗: {e}")
            return False
    
    def _record_api_failure(self, api_name: str, error_message: str):
        """記錄 API 故障"""
        if api_name not in self.api_failures:
            self.api_failures[api_name] = []
        self.api_failures[api_name].append({
            'timestamp': datetime.now().isoformat(),
            'error': error_message
        })
        logger.debug(f"記錄 API 故障: {api_name} - {error_message}")
    
    def _record_fallback(self, data_type: str, source_used: str):
        """記錄使用的降級數據源"""
        if data_type not in self.fallback_used:
            self.fallback_used[data_type] = []
        if source_used not in self.fallback_used[data_type]:
            self.fallback_used[data_type].append(source_used)
    
    def get_api_status_report(self) -> Dict[str, Any]:
        """
        獲取 API 狀態報告（增強版）
        
        返回:
            dict: 包含 API 故障、降級使用情況和自主計算統計的報告
        """
        # 計算降級使用統計
        total_fallback_calls = sum(len(sources) for sources in self.fallback_used.values())
        
        # 統計各降級方案的使用次數
        fallback_stats = {}
        for data_type, sources in self.fallback_used.items():
            fallback_stats[data_type] = {
                'sources_used': sources,
                'call_count': len(sources)
            }
        
        # 統計自主計算的使用情況
        self_calculated_count = 0
        self_calculated_types = []
        
        for data_type, sources in self.fallback_used.items():
            for source in sources:
                if 'self_calculated' in source.lower() or 'bs_calculated' in source.lower():
                    self_calculated_count += 1
                    if data_type not in self_calculated_types:
                        self_calculated_types.append(data_type)
        
        # 計算自主計算使用百分比
        self_calculated_percentage = (self_calculated_count / total_fallback_calls * 100) if total_fallback_calls > 0 else 0
        
        # 統計各 API 的故障次數
        api_failure_counts = {api: len(errors) for api, errors in self.api_failures.items()}
        total_failures = sum(api_failure_counts.values())
        
        return {
            # 原有字段
            'api_failures': self.api_failures,
            'fallback_used': self.fallback_used,
            'ibkr_enabled': self.use_ibkr,
            'ibkr_connected': self.ibkr_client.is_connected() if self.ibkr_client else False,
            
            # 新增統計字段
            'statistics': {
                'total_fallback_calls': total_fallback_calls,
                'total_api_failures': total_failures,
                'self_calculated_count': self_calculated_count,
                'self_calculated_percentage': round(self_calculated_percentage, 2),
                'self_calculated_types': self_calculated_types,
                'api_failure_counts': api_failure_counts,
                'fallback_by_type': fallback_stats
            },
            
            # 自主計算模塊可用性
            'self_calculation_available': {
                'bs_calculator': self.bs_calculator is not None,
                'greeks_calculator': self.greeks_calculator is not None,
                'iv_calculator': self.iv_calculator is not None
            }
        }
    
    def _rate_limit_delay(self, retry_count: int = 0):
        """
        请求速率限制（帶指數退避）
        
        參數:
            retry_count: 重試次數（用於指數退避）
        """
        elapsed = time.time() - self.last_request_time
        
        # 基礎延遲
        base_delay = self.request_delay
        
        # 如果是重試，使用指數退避
        if retry_count > 0:
            # 指數退避: 2^retry_count * base_delay，最多 30 秒
            backoff_delay = min(base_delay * (2 ** retry_count), 30.0)
            logger.info(f"重試 #{retry_count}，使用指數退避延遲: {backoff_delay:.2f}秒")
            time.sleep(backoff_delay)
        elif elapsed < base_delay:
            # 正常速率限制
            sleep_time = base_delay - elapsed
            logger.debug(f"速率限制延迟: {sleep_time:.2f}秒")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    # ==================== 股票基本數據 ====================
    
    def get_stock_info(self, ticker):
        """
        獲取股票基本信息（支持多数据源降级）
        
        降級順序: IBKR → Yahoo Finance 2.0 → yfinance
        
        參數:
            ticker: 股票代碼
        
        返回: dict
        {
            'ticker': str,
            'current_price': float,
            'open': float,
            'high': float,
            'low': float,
            'volume': int,
            'market_cap': float,
            'pe_ratio': float,
            'dividend_rate': float,
            'eps': float
        }
        """
        logger.info(f"開始獲取 {ticker} 基本信息...")
        
        # 方案1: 優先使用 Finviz（最準確的基本面數據）
        if hasattr(self, 'finviz_scraper') and self.finviz_scraper:
            try:
                logger.info("  使用 Finviz...")
                finviz_data = self.finviz_scraper.get_stock_fundamentals(ticker)
                
                if finviz_data:
                    # 驗證和補充 Finviz 數據
                    validated_data = self._validate_and_supplement_finviz_data(finviz_data, ticker)
                    
                    if validated_data:
                        # 轉換為標準格式
                        stock_data = {
                            'ticker': ticker,
                            'current_price': validated_data.get('price', 0),
                            'open': None,  # Finviz 不提供當日開盤價
                            'high': None,
                            'low': None,
                            'volume': validated_data.get('volume'),
                            'market_cap': validated_data.get('market_cap'),
                            'pe_ratio': validated_data.get('pe'),
                            'forward_pe': validated_data.get('forward_pe'),
                            'peg_ratio': validated_data.get('peg'),
                            'dividend_rate': validated_data.get('dividend_yield'),
                            'eps': validated_data.get('eps_ttm'),
                            'eps_next_y': validated_data.get('eps_next_y'),
                            'beta': validated_data.get('beta'),
                            'atr': validated_data.get('atr'),
                            'rsi': validated_data.get('rsi'),
                            'company_name': validated_data.get('company_name'),
                            'sector': validated_data.get('sector'),
                            'industry': validated_data.get('industry'),
                            'target_price': validated_data.get('target_price'),
                            'profit_margin': validated_data.get('profit_margin'),
                            'operating_margin': validated_data.get('operating_margin'),
                            'roe': validated_data.get('roe'),
                            'roa': validated_data.get('roa'),
                            'debt_eq': validated_data.get('debt_eq'),
                            'insider_own': validated_data.get('insider_own'),
                            'inst_own': validated_data.get('inst_own'),
                            'short_float': validated_data.get('short_float'),
                            'avg_volume': validated_data.get('avg_volume'),
                            'data_source': validated_data.get('data_source', 'Finviz'),
                            'missing_fields': validated_data.get('missing_fields', []),
                            'supplemented_fields': validated_data.get('supplemented_fields', []),
                            'data_quality': validated_data.get('data_quality', 'complete')
                        }
                        
                        logger.info(f"* 成功獲取 {ticker} 基本信息 (Finviz)")
                        logger.info(f"  當前股價: ${stock_data['current_price']:.2f}")
                        if stock_data['eps']:
                            logger.info(f"  EPS (TTM): ${stock_data['eps']:.2f}")
                        if stock_data['pe_ratio']:
                            logger.info(f"  P/E: {stock_data['pe_ratio']:.2f}")
                        
                        # 記錄數據質量
                        if stock_data['data_quality'] != 'complete':
                            logger.warning(f"  ! 數據質量: {stock_data['data_quality']}")
                        if stock_data['supplemented_fields']:
                            logger.info(f"  i 補充字段: {', '.join(stock_data['supplemented_fields'])}")
                        
                        self._record_fallback('stock_info', 'Finviz')
                        return stock_data
                    else:
                        logger.warning("! Finviz 數據驗證失敗，降級到 IBKR")
                else:
                    logger.warning("! Finviz 未返回數據，降級到 IBKR")
                    
            except Exception as e:
                logger.warning(f"! Finviz 獲取失敗: {e}，降級到 IBKR")
                self._record_api_failure('Finviz', f"get_stock_info: {e}")
        
        # 方案2: 嘗試使用 IBKR
        if self.ibkr_client and self.ibkr_client.is_connected():
            try:
                self._rate_limit_delay()
                logger.info("  使用 IBKR API...")
                stock_data = self.ibkr_client.get_stock_info(ticker)
                
                if stock_data:
                    logger.info(f"* 成功獲取 {ticker} 基本信息 (IBKR)")
                    logger.info(f"  當前股價: ${stock_data['current_price']:.2f}")
                    self._record_fallback_used('stock_info', 'IBKR')
                    return stock_data
            except Exception as e:
                logger.warning(f"IBKR 獲取失敗: {e}，降級到 Yahoo Finance 2.0")
                self._record_api_failure('IBKR', f"get_stock_info: {e}")
        
        # 方案3: 降級到 Yahoo Finance（简化版）
        if self.yahoo_v2_client:
            try:
                logger.info("  使用 Yahoo Finance API...")
                response = self.yahoo_v2_client.get_quote(ticker)
                stock_data = YahooDataParser.parse_quote(response)
                
                if stock_data:
                    logger.info(f"* 成功獲取 {ticker} 基本信息 (Yahoo Finance)")
                    logger.info(f"  當前股價: ${stock_data['current_price']:.2f}")
                    self._record_fallback('stock_info', 'Yahoo Finance')
                    return stock_data
            except Exception as e:
                logger.warning(f"Yahoo Finance 获取失败: {e}，降级到 yfinance")
                self._record_api_failure('Yahoo Finance', f"get_stock_info: {e}")
        
        # 方案4: 降级到 yfinance
        try:
            self._rate_limit_delay()
            logger.info("  使用 yfinance...")
            stock = yf.Ticker(ticker)
            info = stock.info
            
            stock_data = {
                'ticker': ticker,
                'current_price': info.get('currentPrice', 0),
                'open': info.get('open', 0),
                'high': info.get('dayHigh', 0),
                'low': info.get('dayLow', 0),
                'volume': info.get('volume', 0),
                'market_cap': info.get('marketCap', 0),
                'pe_ratio': info.get('trailingPE', 0),
                'dividend_rate': info.get('dividendRate', 0),
                'eps': info.get('trailingEps', 0),
                'fifty_two_week_high': info.get('fiftyTwoWeekHigh', 0),
                'fifty_two_week_low': info.get('fiftyTwoWeekLow', 0),
                'beta': info.get('beta', 0),
                'company_name': info.get('longName', ''),
                'sector': info.get('sector', ''),
                'industry': info.get('industry', '')
            }
            
            logger.info(f"* 成功獲取 {ticker} 基本信息 (yfinance)")
            logger.info(f"  當前股價: ${stock_data['current_price']:.2f}")
            logger.info(f"  市盈率: {stock_data['pe_ratio']:.2f}")
            logger.info(f"  EPS: ${stock_data['eps']:.2f}")
            self._record_fallback_used('stock_info', 'yfinance')
            
            return stock_data
            
        except Exception as e:
            logger.error(f"x 獲取 {ticker} 基本信息失敗: {e}")
            self._record_api_failure('yfinance', f"get_stock_info: {e}")
            return None
    
    def get_historical_data(self, ticker, period='1mo', interval='1d', max_retries=3):
        """
        獲取歷史OHLCV數據（帶智能重試機制和指數退避）
        
        參數:
            ticker: 股票代碼
            period: 時間週期 ('1d', '5d', '1mo', '3mo', '1y')
            interval: K線間隔 ('1m', '5m', '15m', '30m', '60m', '1d')
            max_retries: 最大重試次數（默認3次）
        
        返回: DataFrame
        """
        for attempt in range(max_retries + 1):
            try:
                # 使用帶指數退避的速率限制
                self._rate_limit_delay(retry_count=attempt)
                
                if attempt > 0:
                    logger.info(f"  重試獲取 {ticker} 歷史數據 (嘗試 {attempt + 1}/{max_retries + 1})...")
                else:
                    logger.info(f"開始獲取 {ticker} 歷史數據... (週期: {period}, 間隔: {interval})")
                
                stock = yf.Ticker(ticker)
                hist = stock.history(period=period, interval=interval)
                
                if hist.empty:
                    logger.warning(f"! 未獲得 {ticker} 的歷史數據")
                    return None
                
                logger.info(f"* 成功獲取 {ticker} 的 {len(hist)} 條歷史記錄")
                
                return hist
                
            except Exception as e:
                error_msg = str(e).lower()
                
                # 檢查是否是速率限制錯誤
                if 'rate limit' in error_msg or '429' in error_msg or 'too many requests' in error_msg:
                    if attempt < max_retries:
                        logger.warning(f"! API 速率限制，將使用指數退避重試 (嘗試 {attempt + 1}/{max_retries + 1})")
                        continue
                    else:
                        logger.error(f"x API 速率限制，已達最大重試次數")
                        self._record_api_failure('yfinance', f"Rate limit exceeded: {e}")
                        return None
                else:
                    if attempt < max_retries:
                        logger.warning(f"! 獲取歷史數據失敗 (嘗試 {attempt + 1}/{max_retries + 1}): {e}")
                    else:
                        logger.error(f"x 獲取 {ticker} 歷史數據失敗 (已重試 {max_retries} 次): {e}")
                        self._record_api_failure('yfinance', f"get_historical_data: {e}")
                        return None
    
    # ==================== 期權數據 ====================
    
    def get_option_expirations(self, ticker):
        """
        獲取所有期權到期日期
        
        參數:
            ticker: 股票代碼
        
        返回: list of str
        """
        try:
            self._rate_limit_delay()  # 添加延迟
            logger.info(f"開始獲取 {ticker} 期權到期日期...")
            stock = yf.Ticker(ticker)
            expirations = stock.options
            
            if not expirations:
                logger.warning(f"! {ticker} 無可用期權")
                return []
            
            logger.info(f"* 成功獲取 {ticker} 的 {len(expirations)} 個到期日期")
            logger.info(f"  最近期權: {expirations[0]}")
            
            return expirations
            
        except Exception as e:
            logger.error(f"x 獲取 {ticker} 期權到期日期失敗: {e}")
            return []
    
    def get_option_chain(self, ticker, expiration):
        """
        獲取完整期權鏈（支持多數據源降級）
        
        參數:
            ticker: 股票代碼
            expiration: 到期日期 (YYYY-MM-DD格式)
        
        返回: dict
        {
            'calls': DataFrame,
            'puts': DataFrame,
            'expiration': str,
            'data_source': str
        }
        """
        logger.info(f"開始獲取 {ticker} {expiration} 期權鏈...")
        
        # 方案1: 嘗試使用 IBKR（如果啟用）
        if self.ibkr_client and self.ibkr_client.is_connected():
            try:
                logger.info("  使用 IBKR...")
                chain_data = self.ibkr_client.get_option_chain(ticker, expiration)
                
                if chain_data:
                    # 轉換為 DataFrame
                    calls_df = pd.DataFrame(chain_data['calls'])
                    puts_df = pd.DataFrame(chain_data['puts'])
                    
                    logger.info(f"* 成功獲取 {ticker} {expiration} 期權鏈 (IBKR)")
                    logger.info(f"  Call期權: {len(calls_df)} 個")
                    logger.info(f"  Put期權: {len(puts_df)} 個")
                    self._record_fallback('option_chain', 'ibkr')
                    
                    return {
                        'calls': calls_df,
                        'puts': puts_df,
                        'expiration': expiration,
                        'data_source': 'ibkr'
                    }
            except Exception as e:
                logger.warning(f"! IBKR 獲取期權鏈失敗: {e}，降級到 Yahoo Finance")
                self._record_api_failure('ibkr', f"get_option_chain: {str(e)}")
        
        # 方案2: 降級到 Yahoo Finance V2（簡化版，帶 User-Agent）
        if self.yahoo_v2_client:
            try:
                logger.info("  使用 Yahoo Finance API...")
                response = self.yahoo_v2_client.get_option_chain(ticker, expiration)
                chain_data = YahooDataParser.parse_option_chain(response)
                
                if chain_data and chain_data.get('calls') and chain_data.get('puts'):
                    # 轉換為 DataFrame
                    calls_df = pd.DataFrame(chain_data['calls'])
                    puts_df = pd.DataFrame(chain_data['puts'])
                    
                    # 轉換 IV 為百分比形式（如果存在）
                    if 'impliedVolatility' in calls_df.columns:
                        calls_df['impliedVolatility'] = calls_df['impliedVolatility'] * 100
                    if 'impliedVolatility' in puts_df.columns:
                        puts_df['impliedVolatility'] = puts_df['impliedVolatility'] * 100
                    
                    logger.info(f"* 成功獲取 {ticker} {expiration} 期權鏈 (Yahoo Finance)")
                    logger.info(f"  Call期權: {len(calls_df)} 個")
                    logger.info(f"  Put期權: {len(puts_df)} 個")
                    self._record_fallback('option_chain', 'Yahoo Finance')
                    
                    return {
                        'calls': calls_df,
                        'puts': puts_df,
                        'expiration': expiration,
                        'data_source': 'yahoo_finance'
                    }
            except Exception as e:
                logger.warning(f"! Yahoo Finance 獲取期權鏈失敗: {e}，降級到 yfinance")
                self._record_api_failure('Yahoo Finance', f"get_option_chain: {str(e)}")
        
        # 方案3: 降級到 yfinance
        try:
            self._rate_limit_delay()
            logger.info("  使用 yfinance...")
            stock = yf.Ticker(ticker)
            option_chain = stock.option_chain(expiration)
            
            calls = option_chain.calls.copy()
            puts = option_chain.puts.copy()
            
            # 調試：檢查轉換前的IV值
            if 'impliedVolatility' in calls.columns and not calls.empty:
                sample_iv_before = calls['impliedVolatility'].iloc[0]
                logger.debug(f"  轉換前 IV 樣本: {sample_iv_before}")
                calls['impliedVolatility'] = calls['impliedVolatility'] * 100
                sample_iv_after = calls['impliedVolatility'].iloc[0]
                logger.debug(f"  轉換後 IV 樣本: {sample_iv_after}")
            
            if 'impliedVolatility' in puts.columns:
                puts['impliedVolatility'] = puts['impliedVolatility'] * 100
            
            logger.info(f"* 成功獲取 {ticker} {expiration} 期權鏈 (yfinance)")
            logger.info(f"  Call期權: {len(calls)} 個")
            logger.info(f"  Put期權: {len(puts)} 個")
            self._record_fallback('option_chain', 'yfinance')
            
            return {
                'calls': calls,
                'puts': puts,
                'expiration': expiration,
                'data_source': 'yfinance'
            }
            
        except Exception as e:
            logger.error(f"x yfinance 獲取期權鏈失敗: {e}")
            self._record_api_failure('yfinance', f"get_option_chain: {str(e)}")
        
        # 方案3: 最後降級 - 返回空數據結構（避免系統崩潰）
        logger.warning("! 所有數據源失敗，返回空期權鏈")
        self._record_fallback('option_chain', 'empty')
        return {
            'calls': pd.DataFrame(),
            'puts': pd.DataFrame(),
            'expiration': expiration,
            'data_source': 'Empty (All Sources Failed)'
        }
    
    def get_option_greeks(self, ticker: str, strike: float, 
                         expiration: str, option_type: str = 'C',
                         stock_price: float = None, iv: float = None,
                         risk_free_rate: float = None) -> Optional[Dict[str, float]]:
        """
        獲取期權 Greeks（Delta, Gamma, Theta, Vega, Rho）
        支持4級降級策略
        
        參數:
            ticker: 股票代碼
            strike: 行使價
            expiration: 到期日期 (YYYY-MM-DD)
            option_type: 'C' (Call) 或 'P' (Put)
            stock_price: 當前股價（可選，用於自主計算）
            iv: 隱含波動率（可選，用於自主計算）
            risk_free_rate: 無風險利率（可選，用於自主計算）
        
        返回:
            dict: {'delta': float, 'gamma': float, 'theta': float, 'vega': float, 'rho': float, 'source': str}
            失敗返回默認值
        """
        logger.info(f"開始獲取 {ticker} {strike} {option_type} Greeks...")
        
        # 方案1: 嘗試使用 IBKR（提供真實 Greeks）
        if self.ibkr_client and self.ibkr_client.is_connected():
            try:
                logger.info("  使用 IBKR...")
                greeks = self.ibkr_client.get_option_greeks(ticker, strike, expiration, option_type)
                
                if greeks:
                    logger.info(f"* 成功獲取 Greeks (IBKR)")
                    greeks['source'] = 'IBKR'
                    self._record_fallback('option_greeks', 'ibkr')
                    return greeks
            except Exception as e:
                logger.warning(f"! IBKR 獲取 Greeks 失敗: {e}，降級到 Yahoo V2")
                self._record_api_failure('ibkr', f"get_option_greeks: {str(e)}")
        
        # 方案2: Yahoo Finance 不提供 Greeks 數據，直接跳過
        # 降級到自主計算
        
        # 方案3: 使用自主計算（新增）
        if self.greeks_calculator:
            try:
                logger.info("  使用自主計算 Greeks...")
                
                # 獲取必要的參數
                if stock_price is None:
                    stock_info = self.get_stock_info(ticker)
                    stock_price = stock_info['current_price'] if stock_info else None
                
                if iv is None:
                    iv = self.extract_implied_volatility(ticker, expiration)
                    if iv:
                        iv = iv / 100.0  # 轉換為小數形式
                
                if risk_free_rate is None:
                    risk_free_rate = self.get_risk_free_rate()
                    if risk_free_rate:
                        risk_free_rate = risk_free_rate / 100.0  # 轉換為小數形式
                
                # 計算到期時間
                from datetime import datetime
                exp_date = datetime.strptime(expiration, '%Y-%m-%d')
                today = datetime.now()
                days_to_exp = (exp_date - today).days
                time_to_exp = days_to_exp / 365.0
                
                # 驗證所有參數都可用
                if all([stock_price, iv, risk_free_rate, time_to_exp > 0]):
                    # 轉換期權類型
                    opt_type = 'call' if option_type.upper() == 'C' else 'put'
                    
                    # 計算 Greeks
                    greeks_result = self.greeks_calculator.calculate_all_greeks(
                        stock_price=stock_price,
                        strike_price=strike,
                        risk_free_rate=risk_free_rate,
                        time_to_expiration=time_to_exp,
                        volatility=iv,
                        option_type=opt_type
                    )
                    
                    greeks_dict = {
                        'delta': greeks_result.delta,
                        'gamma': greeks_result.gamma,
                        'theta': greeks_result.theta,
                        'vega': greeks_result.vega,
                        'rho': greeks_result.rho,
                        'source': 'Self-Calculated (BS Model)'
                    }
                    
                    logger.info(f"* 成功自主計算 Greeks")
                    logger.info(f"  Delta: {greeks_dict['delta']:.4f}")
                    logger.info(f"  Gamma: {greeks_dict['gamma']:.4f}")
                    logger.info(f"  Theta: {greeks_dict['theta']:.4f}")
                    logger.info(f"  Vega: {greeks_dict['vega']:.4f}")
                    logger.info(f"  Rho: {greeks_dict['rho']:.4f}")
                    
                    self._record_fallback('option_greeks', 'self_calculated')
                    return greeks_dict
                else:
                    logger.warning(f"! 自主計算參數不足: stock_price={stock_price}, iv={iv}, rate={risk_free_rate}")
                    
            except Exception as e:
                logger.error(f"x 自主計算 Greeks 失敗: {e}")
                self._record_api_failure('self_calculated', f"get_option_greeks: {str(e)}")
        
        # 方案4: 最後降級 - 返回默認值（避免系統崩潰）
        logger.warning("! 所有方案失敗，使用默認 Greeks 值")
        default_greeks = {
            'delta': 0.5 if option_type.upper() == 'C' else -0.5,
            'gamma': 0.0,
            'theta': 0.0,
            'vega': 0.0,
            'rho': 0.0,
            'source': 'Default (All Methods Failed)'
        }
        self._record_fallback('option_greeks', 'default')
        return default_greeks
    
    def get_atm_option(self, ticker, expiration, option_chain_data=None, current_price=None):
        """
        獲取ATM (At-The-Money) 期權
        
        參數:
            ticker: 股票代碼
            expiration: 到期日期
            option_chain_data: 已獲取的期權鏈數據 (可選，避免重複獲取)
            current_price: 當前股價 (可選)
        
        返回: dict
        {
            'call_atm': Series,
            'put_atm': Series,
            'atm_strike': float,
            'current_price': float
        }
        """
        try:
            logger.info(f"開始獲取 {ticker} ATM期權...")
            
            # 如果沒有提供期權鏈數據，則獲取
            if option_chain_data is None:
                option_chain_data = self.get_option_chain(ticker, expiration)
                if not option_chain_data:
                    raise ValueError("無法獲取期權鏈數據")
            
            calls = option_chain_data['calls']
            puts = option_chain_data['puts']
            
            # 如果沒有提供當前股價，則獲取
            if current_price is None:
                stock = yf.Ticker(ticker)
                current_price = stock.info['currentPrice']
            
            # 找最接近的行使價
            strikes = calls['strike'].values
            atm_strike = min(strikes, key=lambda x: abs(x - current_price))
            
            call_atm = calls[calls['strike'] == atm_strike].iloc[0]
            put_atm = puts[puts['strike'] == atm_strike].iloc[0]
            
            logger.info(f"* {ticker} ATM行使價: ${atm_strike:.2f}")
            logger.info(f"  當前股價: ${current_price:.2f}")
            
            return {
                'call_atm': call_atm,
                'put_atm': put_atm,
                'atm_strike': atm_strike,
                'current_price': current_price
            }
            
        except Exception as e:
            logger.error(f"x 獲取 {ticker} ATM期權失敗: {e}")
            return None
    
    def extract_implied_volatility(self, ticker, expiration):
        """
        提取隱含波動率 (IV)
        
        參數:
            ticker: 股票代碼
            expiration: 到期日期
        
        返回: float (百分比形式 0-100)
        """
        try:
            logger.info(f"開始提取 {ticker} 隱含波動率...")
            atm_data = self.get_atm_option(ticker, expiration)
            if atm_data is None:
                return None
            
            iv = float(atm_data['call_atm']['impliedVolatility'])
            
            logger.info(f"* {ticker} 隱含波動率: {iv:.2f}%")
            
            return iv
            
        except Exception as e:
            logger.error(f"x 提取 {ticker} IV失敗: {e}")
            return None
    
    def get_implied_volatility_with_validation(
        self,
        ticker: str,
        strike: float,
        expiration: str,
        option_type: str = 'C',
        market_price: float = None
    ) -> Optional[Dict[str, Any]]:
        """
        獲取隱含波動率並驗證（新增方法）
        
        此方法結合 API 提供的 IV 和自主反推的 IV，提供更可靠的波動率數據。
        
        工作流程:
        1. 從 API 獲取市場提供的 IV
        2. 使用 Module 17 從期權價格反推 IV
        3. 對比兩者差異並驗證
        4. 返回推薦的 IV 值
        
        參數:
            ticker: 股票代碼
            strike: 行使價
            expiration: 到期日期 (YYYY-MM-DD)
            option_type: 'C' (Call) 或 'P' (Put)
            market_price: 期權市場價格（可選，如不提供則從 API 獲取）
        
        返回:
            dict: {
                'api_iv': float,              # API 提供的 IV（百分比）
                'calculated_iv': float,       # 反推計算的 IV（百分比）
                'iv_difference': float,       # 差異（百分比點）
                'iv_difference_percent': float, # 差異百分比
                'validation_passed': bool,    # 驗證是否通過（差異 < 5%）
                'recommended_iv': float,      # 推薦使用的 IV（百分比）
                'data_source': str,           # 數據來源說明
                'converged': bool,            # 反推計算是否收斂
                'iterations': int,            # 迭代次數
                'calculation_date': str       # 計算日期
            }
            失敗返回 None
        """
        logger.info(f"開始 IV 驗證: {ticker} {strike} {option_type}...")
        
        if not self.iv_calculator:
            logger.warning("! IV 計算器不可用，無法進行驗證")
            return None
        
        try:
            # 步驟1: 獲取 API 提供的 IV
            api_iv = None
            try:
                logger.info("  步驟1: 獲取 API 提供的 IV...")
                
                # 嘗試從期權鏈獲取
                option_chain = self.get_option_chain(ticker, expiration)
                if option_chain and not option_chain['calls'].empty:
                    df = option_chain['calls'] if option_type.upper() == 'C' else option_chain['puts']
                    
                    # 找到對應行使價的期權
                    matching_options = df[df['strike'] == strike]
                    if not matching_options.empty:
                        api_iv = float(matching_options.iloc[0]['impliedVolatility'])
                        logger.info(f"  * API IV: {api_iv:.2f}%")
                    else:
                        logger.warning(f"  ! 未找到行使價 {strike} 的期權")
                        
            except Exception as e:
                logger.warning(f"  ! 獲取 API IV 失敗: {e}")
            
            # 步驟2: 獲取必要參數用於反推計算
            logger.info("  步驟2: 準備反推計算參數...")
            
            # 獲取股價
            stock_info = self.get_stock_info(ticker)
            if not stock_info:
                logger.error("  x 無法獲取股價")
                return None
            stock_price = stock_info['current_price']
            
            # 獲取市場期權價格
            if market_price is None:
                try:
                    option_chain = self.get_option_chain(ticker, expiration)
                    if option_chain and not option_chain['calls'].empty:
                        df = option_chain['calls'] if option_type.upper() == 'C' else option_chain['puts']
                        matching_options = df[df['strike'] == strike]
                        if not matching_options.empty:
                            market_price = float(matching_options.iloc[0]['lastPrice'])
                            logger.info(f"  * 市場價格: ${market_price:.2f}")
                        else:
                            logger.error(f"  x 未找到行使價 {strike} 的期權價格")
                            return None
                except Exception as e:
                    logger.error(f"  x 獲取期權價格失敗: {e}")
                    return None
            
            # 獲取無風險利率
            risk_free_rate = self.get_risk_free_rate()
            if risk_free_rate is None:
                logger.warning("  ! 無法獲取無風險利率，使用默認值 5%")
                risk_free_rate = 5.0
            risk_free_rate = risk_free_rate / 100.0  # 轉換為小數形式
            
            # 計算到期時間
            from datetime import datetime
            exp_date = datetime.strptime(expiration, '%Y-%m-%d')
            today = datetime.now()
            days_to_exp = (exp_date - today).days
            time_to_exp = days_to_exp / 365.0
            
            if time_to_exp <= 0:
                logger.error("  x 期權已到期或到期時間無效")
                return None
            
            logger.info(f"  * 參數準備完成: S=${stock_price:.2f}, K=${strike:.2f}, T={time_to_exp:.4f}年")
            
            # 步驟3: 使用 Module 17 反推 IV
            logger.info("  步驟3: 使用 Newton-Raphson 反推 IV...")
            
            opt_type = 'call' if option_type.upper() == 'C' else 'put'
            
            iv_result = self.iv_calculator.calculate_implied_volatility(
                market_price=market_price,
                stock_price=stock_price,
                strike_price=strike,
                risk_free_rate=risk_free_rate,
                time_to_expiration=time_to_exp,
                option_type=opt_type
            )
            
            calculated_iv = iv_result.implied_volatility * 100  # 轉換為百分比
            converged = iv_result.converged
            iterations = iv_result.iterations
            
            logger.info(f"  * 反推 IV: {calculated_iv:.2f}% (迭代 {iterations} 次, 收斂: {converged})")
            
            # 步驟4: 對比和驗證
            logger.info("  步驟4: 對比和驗證...")
            
            if api_iv is not None:
                iv_difference = abs(calculated_iv - api_iv)
                iv_difference_percent = (iv_difference / api_iv * 100) if api_iv > 0 else 0
                validation_passed = iv_difference_percent < 5.0  # 差異小於 5% 視為通過
                
                logger.info(f"  API IV: {api_iv:.2f}%")
                logger.info(f"  計算 IV: {calculated_iv:.2f}%")
                logger.info(f"  差異: {iv_difference:.2f}% ({iv_difference_percent:.1f}%)")
                
                if validation_passed:
                    logger.info("  * 驗證通過（差異 < 5%）")
                    recommended_iv = (api_iv + calculated_iv) / 2  # 使用平均值
                    data_source = "API + Calculated (Average)"
                else:
                    logger.warning(f"  ! 驗證失敗（差異 {iv_difference_percent:.1f}% >= 5%）")
                    # 如果反推收斂，優先使用反推值
                    if converged:
                        recommended_iv = calculated_iv
                        data_source = "Calculated (API Validation Failed)"
                    else:
                        recommended_iv = api_iv
                        data_source = "API (Calculation Not Converged)"
            else:
                # 沒有 API IV，只能使用計算值
                logger.warning("  ! 無 API IV，僅使用計算值")
                iv_difference = 0
                iv_difference_percent = 0
                validation_passed = converged
                recommended_iv = calculated_iv
                data_source = "Calculated Only (No API Data)"
            
            result = {
                'api_iv': api_iv,
                'calculated_iv': calculated_iv,
                'iv_difference': iv_difference,
                'iv_difference_percent': iv_difference_percent,
                'validation_passed': validation_passed,
                'recommended_iv': recommended_iv,
                'data_source': data_source,
                'converged': converged,
                'iterations': iterations,
                'calculation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            logger.info(f"* IV 驗證完成")
            logger.info(f"  推薦 IV: {recommended_iv:.2f}% ({data_source})")
            
            self._record_fallback('iv_validation', 'completed')
            return result
            
        except Exception as e:
            logger.error(f"x IV 驗證失敗: {e}")
            self._record_api_failure('iv_validation', str(e))
            return None
    
    def get_option_theoretical_price(
        self,
        ticker: str,
        strike: float,
        expiration: str,
        option_type: str = 'C',
        stock_price: float = None,
        volatility: float = None,
        risk_free_rate: float = None
    ) -> Optional[Dict[str, Any]]:
        """
        獲取期權理論價格（新增方法）
        
        使用 Black-Scholes 模型計算期權理論價格，作為 API 失敗時的降級方案。
        
        參數:
            ticker: 股票代碼
            strike: 行使價
            expiration: 到期日期 (YYYY-MM-DD)
            option_type: 'C' (Call) 或 'P' (Put)
            stock_price: 當前股價（可選，如不提供則從 API 獲取）
            volatility: 波動率（小數形式，可選，如不提供則從 API 獲取）
            risk_free_rate: 無風險利率（小數形式，可選，如不提供則從 API 獲取）
        
        返回:
            dict: {
                'theoretical_price': float,    # 理論價格
                'stock_price': float,          # 股價
                'strike_price': float,         # 行使價
                'volatility': float,           # 波動率（小數形式）
                'volatility_percent': float,   # 波動率（百分比）
                'risk_free_rate': float,       # 無風險利率（小數形式）
                'risk_free_rate_percent': float, # 無風險利率（百分比）
                'time_to_expiration': float,   # 到期時間（年）
                'days_to_expiration': int,     # 到期天數
                'option_type': str,            # 期權類型
                'd1': float,                   # BS 模型 d1 參數
                'd2': float,                   # BS 模型 d2 參數
                'data_source': str,            # 數據來源說明
                'calculation_date': str        # 計算日期
            }
            失敗返回 None
        """
        logger.info(f"開始計算期權理論價: {ticker} {strike} {option_type}...")
        
        if not self.bs_calculator:
            logger.warning("! BS 計算器不可用，無法計算理論價")
            return None
        
        try:
            # 步驟1: 獲取股價
            if stock_price is None:
                logger.info("  步驟1: 獲取股價...")
                stock_info = self.get_stock_info(ticker)
                if not stock_info:
                    logger.error("  x 無法獲取股價")
                    return None
                stock_price = stock_info['current_price']
                logger.info(f"  * 股價: ${stock_price:.2f}")
            else:
                logger.info(f"  使用提供的股價: ${stock_price:.2f}")
            
            # 步驟2: 獲取波動率
            if volatility is None:
                logger.info("  步驟2: 獲取波動率...")
                iv = self.extract_implied_volatility(ticker, expiration)
                if iv is None:
                    logger.warning("  ! 無法獲取 IV，使用默認值 30%")
                    volatility = 0.30
                else:
                    volatility = iv / 100.0  # 轉換為小數形式
                logger.info(f"  * 波動率: {volatility*100:.2f}%")
            else:
                logger.info(f"  使用提供的波動率: {volatility*100:.2f}%")
            
            # 步驟3: 獲取無風險利率
            if risk_free_rate is None:
                logger.info("  步驟3: 獲取無風險利率...")
                rate = self.get_risk_free_rate()
                if rate is None:
                    logger.warning("  ! 無法獲取無風險利率，使用默認值 5%")
                    risk_free_rate = 0.05
                else:
                    risk_free_rate = rate / 100.0  # 轉換為小數形式
                logger.info(f"  * 無風險利率: {risk_free_rate*100:.2f}%")
            else:
                logger.info(f"  使用提供的無風險利率: {risk_free_rate*100:.2f}%")
            
            # 步驟4: 計算到期時間
            logger.info("  步驟4: 計算到期時間...")
            from datetime import datetime
            exp_date = datetime.strptime(expiration, '%Y-%m-%d')
            today = datetime.now()
            days_to_exp = (exp_date - today).days
            time_to_exp = days_to_exp / 365.0
            
            if time_to_exp <= 0:
                logger.error("  x 期權已到期或到期時間無效")
                return None
            
            logger.info(f"  * 到期時間: {days_to_exp} 天 ({time_to_exp:.4f} 年)")
            
            # 步驟5: 使用 BS 模型計算理論價
            logger.info("  步驟5: 計算 Black-Scholes 理論價...")
            
            opt_type = 'call' if option_type.upper() == 'C' else 'put'
            
            bs_result = self.bs_calculator.calculate_option_price(
                stock_price=stock_price,
                strike_price=strike,
                risk_free_rate=risk_free_rate,
                time_to_expiration=time_to_exp,
                volatility=volatility,
                option_type=opt_type
            )
            
            theoretical_price = bs_result.option_price
            d1 = bs_result.d1
            d2 = bs_result.d2
            
            logger.info(f"  * 理論價格: ${theoretical_price:.2f}")
            logger.info(f"  d1: {d1:.4f}, d2: {d2:.4f}")
            
            # 構建返回結果
            result = {
                'theoretical_price': theoretical_price,
                'stock_price': stock_price,
                'strike_price': strike,
                'volatility': volatility,
                'volatility_percent': volatility * 100,
                'risk_free_rate': risk_free_rate,
                'risk_free_rate_percent': risk_free_rate * 100,
                'time_to_expiration': time_to_exp,
                'days_to_expiration': days_to_exp,
                'option_type': opt_type,
                'd1': d1,
                'd2': d2,
                'data_source': 'Black-Scholes Model (Self-Calculated)',
                'calculation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            logger.info(f"* 期權理論價計算完成")
            logger.info(f"  {opt_type.upper()} 期權理論價: ${theoretical_price:.2f}")
            
            self._record_fallback('option_theoretical_price', 'bs_calculated')
            return result
            
        except Exception as e:
            logger.error(f"x 期權理論價計算失敗: {e}")
            self._record_api_failure('option_theoretical_price', str(e))
            return None
    
    # ==================== 基本面數據 ====================
    
    def get_eps(self, ticker):
        """
        獲取EPS (每股收益)
        
        參數:
            ticker: 股票代碼
        
        返回: float
        """
        try:
            logger.info(f"開始獲取 {ticker} EPS...")
            stock = yf.Ticker(ticker)
            eps = stock.info.get('trailingEps', None)
            
            if eps:
                logger.info(f"* {ticker} EPS: ${eps:.2f}")
            else:
                logger.warning(f"! {ticker} 無EPS數據")
            
            return eps
            
        except Exception as e:
            logger.error(f"x 獲取 {ticker} EPS失敗: {e}")
            return None
    
    def get_dividends(self, ticker, years=1):
        """
        獲取派息信息
        
        參數:
            ticker: 股票代碼
            years: 回溯年數
        
        返回: dict
        {
            'annual_dividend': float,
            'dividend_history': Series,
            'total_recent_dividends': float
        }
        """
        try:
            logger.info(f"開始獲取 {ticker} 派息信息...")
            stock = yf.Ticker(ticker)
            
            # 獲取派息歷史
            div_hist = stock.dividends
            
            if div_hist.empty:
                logger.warning(f"! {ticker} 無派息歷史")
                return {
                    'annual_dividend': 0,
                    'dividend_history': None,
                    'total_recent_dividends': 0
                }
            
            # 最近X年派息
            cutoff_date = datetime.now() - timedelta(days=365*years)
            
            # 處理timezone問題：如果index有timezone，轉換cutoff_date
            if hasattr(div_hist.index, 'tz') and div_hist.index.tz is not None:
                # 將cutoff_date轉換為與index相同的timezone
                import pytz
                cutoff_date = cutoff_date.replace(tzinfo=pytz.UTC).astimezone(div_hist.index.tz)
            
            recent_div = div_hist[div_hist.index >= cutoff_date]
            annual_div = recent_div.sum()
            
            logger.info(f"* {ticker} 年派息: ${annual_div:.4f}")
            logger.info(f"  派息次數: {len(recent_div)}")
            
            return {
                'annual_dividend': annual_div,
                'dividend_history': recent_div,
                'total_recent_dividends': annual_div
            }
            
        except Exception as e:
            logger.error(f"x 獲取 {ticker} 派息失敗: {e}")
            return None
    
    # ==================== 宏觀數據 ====================
    
    def get_risk_free_rate(self):
        """
        獲取無風險利率 (10年期國債收益率)
        
        返回: float (百分比形式)
        """
        try:
            if not self.fred_client:
                logger.warning("! FRED客户端未初始化，無法獲取利率")
                return None
            
            logger.info("開始獲取無風險利率...")
            dgs10 = self.fred_client.get_series('DGS10')
            
            if dgs10 is None or dgs10.empty:
                logger.warning("! 無法獲取10年期國債收益率")
                return None
            
            rate = dgs10.iloc[-1]
            logger.info(f"* 10年期國債收益率: {rate:.2f}%")
            
            return rate
            
        except Exception as e:
            logger.error(f"x 獲取無風險利率失敗: {e}")
            return None
    
    def get_vix(self):
        """
        獲取VIX指數（CBOE Volatility Index）
        
        優先使用 Yahoo Finance 獲取實時 VIX，失敗時降級到 FRED
        
        返回: float
        """
        try:
            # 優先使用 Yahoo Finance 獲取實時 VIX
            logger.info("開始獲取VIX指數...")
            try:
                vix_ticker = yf.Ticker("^VIX")
                vix_data = vix_ticker.history(period="1d")
                
                if not vix_data.empty:
                    vix_value = float(vix_data['Close'].iloc[-1])
                    logger.info(f"* VIX指數 (Yahoo Finance 實時): {vix_value:.2f}")
                    return vix_value
                else:
                    logger.warning("! Yahoo Finance VIX 數據為空，降級到 FRED")
            except Exception as e:
                logger.warning(f"! Yahoo Finance 獲取 VIX 失敗: {e}，降級到 FRED")
            
            # 降級：使用 FRED 獲取 VIX（可能有延遲）
            if self.fred_client:
                vix = self.fred_client.get_series('VIXCLS')
                
                if vix is not None and not vix.empty:
                    vix_value = vix.iloc[-1]
                    logger.info(f"* VIX指數 (FRED 收盤價): {vix_value:.2f}")
                    logger.warning("  ! 注意：FRED VIX 數據可能有1天延遲")
                    return vix_value
                else:
                    logger.warning("! FRED 無法獲取VIX")
                    return None
            else:
                logger.warning("! FRED客户端未初始化，無法獲取VIX")
                return None
            
        except Exception as e:
            logger.error(f"x 獲取VIX失敗: {e}")
            return None
    
    # ==================== 業績和派息數據 ====================
    
    def get_earnings_calendar(self, ticker):
        """
        獲取業績發布日期（多層降級）- 岗位10監察
        
        降級順序:
        1. Finnhub API
        2. yfinance calendar
        3. 歷史業績日期推測（+90天）
        
        參數:
            ticker: 股票代碼
        
        返回: dict
        {
            'next_earnings_date': str (YYYY-MM-DD),
            'earnings_call_time': str,
            'eps_estimate': float,
            'revenue_estimate': float,
            'data_source': str,  # 'finnhub', 'yfinance', 'estimated'
            'is_estimated': bool,
            'confidence': str  # 'high', 'medium', 'low'
        }
        """
        logger.info(f"開始獲取 {ticker} 業績日期...")
        
        # 方案1: 優先使用 Finnhub
        if self.finnhub_client:
            try:
                logger.info("  使用 Finnhub API...")
                
                # 獲取財報日曆 (未來90天)
                from_date = datetime.now().strftime('%Y-%m-%d')
                to_date = (datetime.now() + timedelta(days=90)).strftime('%Y-%m-%d')
                
                earnings = self.finnhub_client.earnings_calendar(
                    _from=from_date,
                    to=to_date,
                    symbol=ticker,
                    international=False
                )
                
                if earnings and 'earningsCalendar' in earnings:
                    calendar = earnings['earningsCalendar']
                    
                    if len(calendar) > 0:
                        next_earnings = calendar[0]
                        
                        result = {
                            'next_earnings_date': next_earnings.get('date', ''),
                            'earnings_call_time': next_earnings.get('hour', 'bmo'),
                            'eps_estimate': next_earnings.get('epsEstimate', 0),
                            'revenue_estimate': next_earnings.get('revenueEstimate', 0),
                            'data_source': 'finnhub',
                            'is_estimated': False,
                            'confidence': 'high'
                        }
                        
                        logger.info(f"* 從 Finnhub 獲取 {ticker} 業績日期: {result['next_earnings_date']} ({result['earnings_call_time']})")
                        self._record_fallback('earnings_calendar', 'finnhub')
                        return result
                
                logger.warning(f"! Finnhub 無 {ticker} 近期業績安排，嘗試降級到 yfinance")
                
            except Exception as e:
                logger.warning(f"! Finnhub 獲取業績日期失敗: {e}，降級到 yfinance")
                self._record_api_failure('Finnhub', f"get_earnings_calendar: {e}")
        else:
            logger.info("  Finnhub 客戶端未初始化，跳過")
        
        # 方案2: 降級到 yfinance calendar
        try:
            logger.info("  使用 yfinance calendar...")
            stock = yf.Ticker(ticker)
            calendar = stock.calendar
            
            if calendar is not None and not calendar.empty:
                # yfinance calendar 返回 DataFrame，包含 'Earnings Date' 等信息
                if 'Earnings Date' in calendar.index:
                    earnings_date = calendar.loc['Earnings Date']
                    
                    # 處理可能的多個日期（範圍）
                    if isinstance(earnings_date, pd.Series):
                        # 取第一個日期
                        next_date = earnings_date.iloc[0] if len(earnings_date) > 0 else None
                    else:
                        next_date = earnings_date
                    
                    if next_date and not pd.isna(next_date):
                        # 轉換為字符串格式
                        if isinstance(next_date, pd.Timestamp):
                            date_str = next_date.strftime('%Y-%m-%d')
                        else:
                            date_str = str(next_date)
                        
                        result = {
                            'next_earnings_date': date_str,
                            'earnings_call_time': 'unknown',  # yfinance 不提供
                            'eps_estimate': 0,  # yfinance calendar 不提供
                            'revenue_estimate': 0,
                            'data_source': 'yfinance',
                            'is_estimated': False,
                            'confidence': 'medium'
                        }
                        
                        logger.info(f"* 從 yfinance 獲取 {ticker} 業績日期: {result['next_earnings_date']}")
                        self._record_fallback('earnings_calendar', 'yfinance')
                        return result
            
            logger.warning(f"! yfinance 無 {ticker} 業績日期，嘗試歷史推測")
            
        except Exception as e:
            logger.warning(f"! yfinance 獲取業績日期失敗: {e}，嘗試歷史推測")
            self._record_api_failure('yfinance', f"get_earnings_calendar: {e}")
        
        # 方案3: 最後降級 - 使用歷史業績日期推測
        try:
            logger.info("  使用歷史業績日期推測...")
            estimated_result = self._estimate_earnings_date_from_history(ticker)
            
            if estimated_result:
                logger.info(f"* 推測 {ticker} 下次業績日期: {estimated_result['next_earnings_date']} (基於歷史數據)")
                logger.warning("  ! 注意：此日期為推測值，可能不準確")
                self._record_fallback('earnings_calendar', 'estimated')
                return estimated_result
            
        except Exception as e:
            logger.error(f"x 歷史推測失敗: {e}")
            self._record_api_failure('earnings_estimation', str(e))
        
        # 所有方案都失敗
        logger.error(f"x 所有方案都無法獲取 {ticker} 業績日期")
        return None
    
    def _validate_and_supplement_finviz_data(
        self, 
        finviz_data: Dict, 
        ticker: str
    ) -> Optional[Dict]:
        """
        驗證 Finviz 數據並補充缺失的關鍵字段
        
        策略:
        1. 檢查關鍵字段（price, eps, pe）是否存在
        2. 如果關鍵字段缺失，嘗試從 yfinance 補充
        3. 記錄缺失和補充的字段
        4. 評估數據質量（complete/partial/minimal）
        
        參數:
            finviz_data: Finviz 原始數據
            ticker: 股票代碼
        
        返回:
            增強後的數據字典，包含:
            - missing_fields: 缺失的字段列表
            - supplemented_fields: 從其他源補充的字段列表
            - data_quality: 'complete' | 'partial' | 'minimal'
            - data_source: 'Finviz' | 'Finviz+yfinance'
            
            驗證失敗返回 None
        """
        try:
            # 定義關鍵字段和所有預期字段
            critical_fields = ['price', 'eps_ttm', 'pe']
            all_expected_fields = [
                'price', 'eps_ttm', 'pe', 'forward_pe', 'peg', 'market_cap',
                'volume', 'dividend_yield', 'beta', 'atr', 'rsi',
                'company_name', 'sector', 'industry', 'target_price',
                'profit_margin', 'operating_margin', 'roe', 'roa', 'debt_eq',
                'insider_own', 'inst_own', 'short_float', 'avg_volume'
            ]
            
            # 檢查缺失字段
            missing_fields = []
            missing_critical = []
            
            for field in all_expected_fields:
                if field not in finviz_data or finviz_data[field] is None:
                    missing_fields.append(field)
                    if field in critical_fields:
                        missing_critical.append(field)
            
            # 記錄缺失字段
            if missing_fields:
                logger.warning(f"! Finviz 缺失字段 ({len(missing_fields)}/{len(all_expected_fields)}): {', '.join(missing_fields[:5])}")
                if len(missing_fields) > 5:
                    logger.debug(f"  完整缺失列表: {', '.join(missing_fields)}")
            
            # 如果關鍵字段缺失，嘗試從 yfinance 補充
            supplemented_fields = []
            if missing_critical:
                logger.info(f"  嘗試從 yfinance 補充關鍵字段: {', '.join(missing_critical)}")
                
                try:
                    stock = yf.Ticker(ticker)
                    info = stock.info
                    
                    # 補充 price
                    if 'price' in missing_critical and 'currentPrice' in info:
                        finviz_data['price'] = info['currentPrice']
                        supplemented_fields.append('price')
                        logger.debug(f"  * 補充 price: ${info['currentPrice']:.2f}")
                    
                    # 補充 eps
                    if 'eps_ttm' in missing_critical and 'trailingEps' in info:
                        finviz_data['eps_ttm'] = info['trailingEps']
                        supplemented_fields.append('eps_ttm')
                        logger.debug(f"  * 補充 eps_ttm: ${info['trailingEps']:.2f}")
                    
                    # 補充 pe
                    if 'pe' in missing_critical and 'trailingPE' in info:
                        finviz_data['pe'] = info['trailingPE']
                        supplemented_fields.append('pe')
                        logger.debug(f"  * 補充 pe: {info['trailingPE']:.2f}")
                    
                    if supplemented_fields:
                        logger.info(f"  * 成功補充 {len(supplemented_fields)} 個關鍵字段")
                    
                except Exception as e:
                    logger.warning(f"  ! yfinance 補充失敗: {e}")
            
            # 再次檢查關鍵字段
            still_missing_critical = [f for f in critical_fields
                                     if f not in finviz_data or finviz_data[f] is None]
            
            if still_missing_critical:
                logger.error(f"  x 關鍵字段仍然缺失: {', '.join(still_missing_critical)}")
                return None
            
            # 計算數據質量
            available_fields = sum(1 for f in all_expected_fields 
                                 if f in finviz_data and finviz_data[f] is not None)
            quality_ratio = available_fields / len(all_expected_fields)
            
            if quality_ratio >= 0.9:
                data_quality = 'complete'
            elif quality_ratio >= 0.6:
                data_quality = 'partial'
            else:
                data_quality = 'minimal'
            
            logger.debug(f"  數據質量: {data_quality} ({available_fields}/{len(all_expected_fields)} 字段可用)")
            
            # 添加元數據
            finviz_data['missing_fields'] = missing_fields
            finviz_data['supplemented_fields'] = supplemented_fields
            finviz_data['data_quality'] = data_quality
            finviz_data['data_source'] = 'Finviz+yfinance' if supplemented_fields else 'Finviz'
            
            return finviz_data
            
        except Exception as e:
            logger.error(f"x Finviz 數據驗證失敗: {e}")
            return None
    
    def _estimate_earnings_date_from_history(self, ticker: str) -> Optional[Dict]:
        """
        從歷史業績日期推測下次業績日期
        
        策略:
        1. 獲取過去的業績日期（如果可用）
        2. 計算平均間隔（通常為 90 天左右）
        3. 從最後一次業績日期推測下次日期
        
        參數:
            ticker: 股票代碼
        
        返回:
            推測的業績日期字典，失敗返回 None
        """
        try:
            stock = yf.Ticker(ticker)
            
            # 嘗試獲取歷史業績日期
            # yfinance 的 earnings_dates 屬性包含歷史業績日期
            try:
                earnings_dates = stock.earnings_dates
                
                if earnings_dates is not None and not earnings_dates.empty:
                    # 獲取最近的業績日期
                    latest_earnings = earnings_dates.index[0]
                    
                    # 計算距今天數
                    days_since_last = (datetime.now() - latest_earnings).days
                    
                    # 計算下次業績日期（假設每季度發布，90天間隔）
                    # 從最後業績日期開始，每次加90天，直到找到未來的日期
                    next_date = latest_earnings
                    while (next_date - datetime.now()).days < 0:
                        next_date = next_date + timedelta(days=90)
                    
                    # 如果推測日期太遠（超過120天），可能計算有誤，使用保守估計
                    days_until = (next_date - datetime.now()).days
                    if days_until > 120:
                        next_date = datetime.now() + timedelta(days=90)
                    
                    result = {
                        'next_earnings_date': next_date.strftime('%Y-%m-%d'),
                        'earnings_call_time': 'unknown',
                        'eps_estimate': 0,
                        'revenue_estimate': 0,
                        'data_source': 'estimated',
                        'is_estimated': True,
                        'confidence': 'low',
                        'estimation_basis': f'Last earnings: {latest_earnings.strftime("%Y-%m-%d")}, {days_since_last} days ago'
                    }
                    
                    logger.debug(f"  推測基礎: 最後業績日期 {latest_earnings.strftime('%Y-%m-%d')}，距今 {days_since_last} 天")
                    return result
                    
            except AttributeError:
                # earnings_dates 屬性不存在
                logger.debug("  yfinance earnings_dates 不可用")
            
            # 如果無法獲取歷史日期，使用固定的季度推測
            # 假設公司每季度發布業績（90天）
            logger.debug("  使用固定季度間隔推測（90天）")
            next_date = datetime.now() + timedelta(days=90)
            
            result = {
                'next_earnings_date': next_date.strftime('%Y-%m-%d'),
                'earnings_call_time': 'unknown',
                'eps_estimate': 0,
                'revenue_estimate': 0,
                'data_source': 'estimated',
                'is_estimated': True,
                'confidence': 'low',
                'estimation_basis': 'Fixed 90-day interval (no historical data)'
            }
            
            return result
            
        except Exception as e:
            logger.error(f"x 推測業績日期失敗: {e}")
            return None
    
    def get_dividend_calendar(self, ticker):
        """
        獲取派息日期 - 岗位9監察
        
        優先使用yfinance，失敗則嘗試finnhub
        
        參數:
            ticker: 股票代碼
        
        返回: dict
        {
            'ex_dividend_date': str (YYYY-MM-DD),
            'payment_date': str (YYYY-MM-DD),
            'dividend_amount': float,
            'frequency': str
        }
        """
        try:
            logger.info(f"開始獲取 {ticker} 派息信息...")
            
            # 方法1: 使用yfinance (主要)
            stock = yf.Ticker(ticker)
            info = stock.info
            
            result = {
                'ex_dividend_date': '',
                'payment_date': '',
                'dividend_amount': 0.0,
                'frequency': ''
            }
            
            # 從info獲取派息信息
            if 'exDividendDate' in info and info['exDividendDate']:
                try:
                    ex_date = datetime.fromtimestamp(info['exDividendDate'])
                    result['ex_dividend_date'] = ex_date.strftime('%Y-%m-%d')
                except:
                    pass
            
            if 'dividendRate' in info:
                result['dividend_amount'] = info.get('dividendRate', 0.0)
            
            # 推測派息頻率
            dividends = stock.dividends
            if len(dividends) >= 4:
                result['frequency'] = '季度'
            elif len(dividends) >= 2:
                result['frequency'] = '半年'
            elif len(dividends) >= 1:
                result['frequency'] = '年度'
                
            # 如果yfinance沒有除息日，嘗試從歷史推測
            if not result['ex_dividend_date'] and len(dividends) > 0:
                last_dividend_date = dividends.index[-1]
                # 推測下次派息日期 (約3個月後)
                next_dividend_date = last_dividend_date + timedelta(days=90)
                result['ex_dividend_date'] = next_dividend_date.strftime('%Y-%m-%d')
                logger.info(f"  (推測) 下次除息日: {result['ex_dividend_date']}")
            
            if result['ex_dividend_date']:
                logger.info(f"* {ticker} 除息日: {result['ex_dividend_date']}")
                return result
            
            # 方法2: 使用finnhub (備用)
            if self.finnhub_client:
                logger.info(f"  嘗試使用Finnhub獲取派息信息...")
                
                try:
                    dividends_data = self.finnhub_client.stock_dividends(
                        ticker,
                        _from=(datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d'),
                        to=(datetime.now() + timedelta(days=180)).strftime('%Y-%m-%d')
                    )
                    
                    if dividends_data and len(dividends_data) > 0:
                        # 查找未來的派息日期
                        future_dividends = [d for d in dividends_data
                                          if datetime.strptime(d.get('exDate', ''), '%Y-%m-%d') > datetime.now()]
                        
                        if future_dividends:
                            latest = future_dividends[0]
                        else:
                            latest = dividends_data[-1]
                        
                        result['ex_dividend_date'] = latest.get('exDate', '')
                        result['payment_date'] = latest.get('payDate', '')
                        result['dividend_amount'] = latest.get('amount', 0.0)
                        
                        logger.info(f"* {ticker} 除息日(Finnhub): {result['ex_dividend_date']}")
                        return result
                except Exception as e:
                    logger.warning(f"  Finnhub派息數據獲取失敗: {e}")
            
            logger.warning(f"! {ticker} 無派息信息")
            return None
            
        except Exception as e:
            logger.error(f"x 獲取 {ticker} 派息信息失敗: {e}")
            return None
    
    # ==================== 完整數據包 ====================
    
    def get_complete_analysis_data(self, ticker, expiration=None):
        """
        獲取完整的分析所需數據包
        
        參數:
            ticker: 股票代碼
            expiration: 期權到期日期 (可選)
        
        返回: dict (包含所有必需數據)
        """
        try:
            logger.info("=" * 70)
            logger.info(f"開始獲取 {ticker} 的完整分析數據包...")
            logger.info("=" * 70)
            
            # 1. 股票基本信息
            logger.info("\n[步驟1/6] 獲取股票基本信息...")
            stock_info = self.get_stock_info(ticker)
            if not stock_info:
                logger.warning(f"! 無法從 API 獲取 {ticker} 基本信息，使用降級方案...")
                # 降級方案：使用最小化的默認數據結構
                stock_info = {
                    'ticker': ticker,
                    'current_price': 0,  # 將在後續步驟中嘗試獲取
                    'open': 0,
                    'high': 0,
                    'low': 0,
                    'volume': 0,
                    'market_cap': 0,
                    'pe_ratio': 25.0,  # 使用市場平均 PE
                    'dividend_rate': 0,
                    'eps': 0,
                    'fifty_two_week_high': 0,
                    'fifty_two_week_low': 0,
                    'beta': 1.0,  # 使用市場 beta
                    'company_name': ticker,
                    'sector': 'Unknown',
                    'industry': 'Unknown'
                }
            
            current_price = stock_info['current_price']
            
            # 如果 current_price 為 0，嘗試從歷史數據獲取
            if current_price == 0:
                logger.info("  嘗試從歷史數據獲取當前價格...")
                try:
                    hist = self.get_historical_data(ticker, period='1d', interval='1d')
                    if hist is not None and not hist.empty:
                        current_price = float(hist['Close'].iloc[-1])
                        stock_info['current_price'] = current_price
                        stock_info['open'] = float(hist['Open'].iloc[-1])
                        stock_info['high'] = float(hist['High'].iloc[-1])
                        stock_info['low'] = float(hist['Low'].iloc[-1])
                        stock_info['volume'] = int(hist['Volume'].iloc[-1])
                        logger.info(f"  * 從歷史數據獲取價格: ${current_price:.2f}")
                except Exception as e:
                    logger.warning(f"  從歷史數據獲取價格失敗: {e}")
            
            # 最後檢查：如果還是沒有價格，則無法繼續
            if current_price == 0:
                raise ValueError(f"{ticker} 無法獲取有效股價，請稍後重試或檢查網絡連接")
            
            # 2. 確定期權到期日
            logger.info("\n[步驟2/6] 確定期權到期日期...")
            if expiration is None:
                expirations = self.get_option_expirations(ticker)
                if not expirations:
                    raise ValueError(f"{ticker} 無可用期權")
                expiration = expirations[0]  # 最近期權
            
            logger.info(f"使用期權到期日: {expiration}")
            
            # 3. 期權鏈數據
            logger.info("\n[步驟3/6] 獲取期權鏈數據...")
            option_chain = self.get_option_chain(ticker, expiration)
            if not option_chain:
                raise ValueError(f"無法獲取 {ticker} 期權鏈")
            
            # 4. ATM 期權數據與隱含波動率
            logger.info("\n[步驟4/6] 獲取ATM期權與隱含波動率...")
            atm_data = self.get_atm_option(ticker, expiration, option_chain_data=option_chain, current_price=current_price)
            if atm_data is None:
                raise ValueError(f"無法獲取 {ticker} ATM 期權資料")
            
            call_atm = atm_data['call_atm']
            put_atm = atm_data['put_atm']
            atm_strike = atm_data['atm_strike']
            iv = float(call_atm['impliedVolatility'])
            
            # 調試：檢查IV值
            logger.debug(f"  原始 IV 值: {iv}")
            
            # 如果IV看起來是小數格式（0-1），轉換為百分比
            if 0 < iv < 1:
                logger.warning(f"  ! IV 是小數格式 ({iv})，轉換為百分比")
                iv = iv * 100
                logger.info(f"  * IV 已轉換: {iv:.2f}%")
            
            # 5. 基本面數據
            logger.info("\n[步驟5/6] 獲取基本面數據...")
            eps = self.get_eps(ticker)
            dividends = self.get_dividends(ticker)
            
            # 5.1 歷史數據 (用於 Module 18 HV計算)
            logger.info("\n[步驟5.1/6] 獲取歷史數據 (用於HV計算)...")
            # 獲取足夠的歷史數據以計算 60日 HV (需要約 90 天數據)
            historical_data = self.get_historical_data(ticker, period='3mo', interval='1d')
            if historical_data is not None and not historical_data.empty:
                logger.info(f"  * 獲取了 {len(historical_data)} 條歷史記錄")
            else:
                logger.warning("  ! 無法獲取歷史數據，HV 計算將跳過")

            # 6. 宏觀數據
            logger.info("\n[步驟6/7] 獲取宏觀數據...")
            risk_free_rate = self.get_risk_free_rate()
            vix = self.get_vix()
            
            # 7. 業績和派息數據
            logger.info("\n[步驟7/7] 獲取業績和派息日期...")
            earnings_calendar = self.get_earnings_calendar(ticker)
            dividend_calendar = self.get_dividend_calendar(ticker)
            
            # 計算天數至到期
            exp_date = pd.to_datetime(expiration).to_pydatetime()
            today_dt = datetime.now()
            if self.trading_days_calc:
                days_to_exp = self.trading_days_calc.calculate_trading_days(
                    today_dt,
                    exp_date
                )
            else:
                days_to_exp = max(0, (exp_date.date() - today_dt.date()).days)
            
            # 組合完整數據包
            complete_data = {
                'ticker': ticker,
                'timestamp': datetime.now(),
                'analysis_date': today_dt.strftime('%Y-%m-%d'),
                
                # 股票數據
                'current_price': current_price,
                'stock_open': stock_info['open'],
                'stock_high': stock_info['high'],
                'stock_low': stock_info['low'],
                'volume': stock_info['volume'],
                'market_cap': stock_info['market_cap'],
                'pe_ratio': stock_info['pe_ratio'],
                'eps': eps,
                'company_name': stock_info['company_name'],
                'sector': stock_info['sector'],
                'industry': stock_info['industry'],
                
                # 派息數據
                'annual_dividend': dividends.get('annual_dividend', 0) if dividends else 0,
                'dividend_rate': stock_info['dividend_rate'],
                
                # ✅ Finviz 額外數據（所有權結構）
                'insider_own': stock_info.get('insider_own'),
                'inst_own': stock_info.get('inst_own'),
                'short_float': stock_info.get('short_float'),
                'avg_volume': stock_info.get('avg_volume'),
                
                # ✅ Finviz 額外數據（基本面指標）
                'forward_pe': stock_info.get('forward_pe'),
                'peg_ratio': stock_info.get('peg_ratio'),
                'roe': stock_info.get('roe'),
                'roa': stock_info.get('roa'),
                'profit_margin': stock_info.get('profit_margin'),
                'operating_margin': stock_info.get('operating_margin'),
                'debt_eq': stock_info.get('debt_eq'),
                
                # ✅ Finviz 額外數據（技術指標）
                # 注意：ATR 用於 Module 14 崗位8（《期權制勝》第十四課）
                # RSI 和 Beta 保留供未來使用，但不屬於原書的12監察崗位
                'atr': stock_info.get('atr'),
                'rsi': stock_info.get('rsi'),
                'beta': stock_info.get('beta'),
                'target_price': stock_info.get('target_price'),
                
                # 期權數據
                'expiration_date': expiration,
                'days_to_expiration': days_to_exp,
                'implied_volatility': iv,
                'option_chain': option_chain,
                'atm_option': {
                    'strike': float(atm_strike),
                    'call': call_atm.to_dict(),
                    'put': put_atm.to_dict()
                },
                
                # 宏觀數據
                'risk_free_rate': risk_free_rate,
                'vix': vix,
                
                # 業績和派息數據
                'next_earnings_date': earnings_calendar.get('next_earnings_date', '') if earnings_calendar else '',
                'earnings_call_time': earnings_calendar.get('earnings_call_time', '') if earnings_calendar else '',
                'eps_estimate': earnings_calendar.get('eps_estimate', 0) if earnings_calendar else 0,
                'ex_dividend_date': dividend_calendar.get('ex_dividend_date', '') if dividend_calendar else '',
                'dividend_payment_date': dividend_calendar.get('payment_date', '') if dividend_calendar else '',
                'dividend_frequency': dividend_calendar.get('frequency', '') if dividend_calendar else '',
                
                # 歷史數據
                'historical_data': historical_data
            }
            
            # ✅ Task 6: 記錄 Finviz 數據獲取狀態（增強版）
            finviz_fields = ['insider_own', 'inst_own', 'short_float', 'avg_volume', 
                           'peg_ratio', 'roe', 'profit_margin', 'debt_eq', 'atr', 'rsi', 'beta']
            available_finviz_fields = [f for f in finviz_fields if complete_data.get(f) is not None]
            missing_finviz_fields = [f for f in finviz_fields if complete_data.get(f) is None]
            
            # 詳細記錄每個字段的狀態
            logger.info(f"\n{'='*70}")
            logger.info(f"Finviz 數據完整性檢查:")
            logger.info(f"{'='*70}")
            
            if available_finviz_fields:
                logger.info(f"* 可用字段 ({len(available_finviz_fields)}/{len(finviz_fields)}):")
                for field in available_finviz_fields:
                    value = complete_data.get(field)
                    logger.info(f"  * {field}: {value}")
            
            if missing_finviz_fields:
                logger.warning(f"! 缺失字段 ({len(missing_finviz_fields)}/{len(finviz_fields)}):")
                for field in missing_finviz_fields:
                    logger.warning(f"  x {field}: 數據不可用")
                    # 記錄到 API 故障報告
                    self._record_api_failure('Finviz', f"Missing field: {field}")
            
            # 記錄降級使用情況
            if missing_finviz_fields:
                self._record_fallback('finviz_data', f'Partial data ({len(available_finviz_fields)}/{len(finviz_fields)} fields)')
            
            logger.info(f"{'='*70}")
            
            logger.info("\n" + "=" * 70)
            logger.info(f"* 成功獲取 {ticker} 的完整分析數據")
            logger.info("=" * 70)
            
            return complete_data
            
        except Exception as e:
            logger.error(f"\nx 獲取完整分析數據失敗: {e}")
            return None


# 使用示例
if __name__ == "__main__":
    logger.info("啟動DataFetcher測試...")
    
    fetcher = DataFetcher()
    
    # 獲取AAPL的完整分析數據
    data = fetcher.get_complete_analysis_data('AAPL')
    
    if data:
        print("\n" + "=" * 70)
        print("完整分析數據獲取成功！")
        print("=" * 70)
        print(f"股票代碼: {data['ticker']}")
        print(f"公司名稱: {data['company_name']}")
        print(f"當前股價: ${data['current_price']:.2f}")
        print(f"隱含波動率: {data['implied_volatility']:.2f}%")
        print(f"無風險利率: {data['risk_free_rate']:.2f}%")
        print(f"VIX: {data['vix']:.2f}")
        print(f"EPS: ${data['eps']:.2f}")
        print(f"派息: ${data['annual_dividend']:.2f}")
        print(f"期權到期日: {data['expiration_date']}")
        print(f"距離到期: {data['days_to_expiration']} 天")
        print("=" * 70)
