# data_layer/data_fetcher.py
"""
完整數據獲取類 (第1階段完整實現)
集成 Yahoo Finance 2.0 OAuth API
"""

import yfinance as yf
import pandas as pd
import numpy as np
from fredapi import Fred
import finnhub
import time
import traceback
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List
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

# 導入統一的數據標準化工具
try:
    from utils.data_normalization import normalize_numeric_value, is_valid_numeric
    DATA_NORMALIZATION_AVAILABLE = True
except ImportError:
    DATA_NORMALIZATION_AVAILABLE = False
    # 提供回退實現
    def normalize_numeric_value(value, default=None):
        if value is None:
            return default
        if isinstance(value, float) and (np.isnan(value) or np.isinf(value)):
            return default
        return value
    def is_valid_numeric(value):
        if value is None:
            return False
        if isinstance(value, float) and (np.isnan(value) or np.isinf(value)):
            return False
        return True

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


class IVNormalizer:
    """
    IV（隱含波動率）數據標準化工具
    
    解決問題：
    - Yahoo Finance 返回的 IV 是小數格式（如 0.6 表示 60%）
    - 系統內部使用百分比格式（如 60 表示 60%）
    - 避免在多個位置重複轉換導致錯誤
    
    使用示例:
        >>> result = IVNormalizer.normalize_iv(0.65, source='yahoo_finance')
        >>> print(result['normalized_iv'])  # 65.0
        >>> print(result['was_decimal'])    # True
    """
    
    # IV 閾值常量
    DECIMAL_THRESHOLD = 1.0  # 小於此值視為小數格式
    MIN_VALID_IV = 0.01      # 最小有效 IV（1%）
    MAX_VALID_IV = 500.0     # 最大有效 IV（500%）
    ABNORMAL_HIGH_IV = 200.0 # 異常高 IV 閾值
    ABNORMAL_LOW_IV = 5.0    # 異常低 IV 閾值
    
    @staticmethod
    def is_decimal_format(iv_value: float) -> bool:
        """
        判斷 IV 是否為小數格式 (0-1)
        
        參數:
            iv_value: IV 值
        
        返回:
            bool: True 表示小數格式，False 表示百分比格式
        """
        if iv_value is None:
            return False
        
        # 小於 1 的正數視為小數格式
        # 注意：某些極低 IV 股票可能有 0.5% 的 IV，但這種情況很罕見
        return 0 < iv_value < IVNormalizer.DECIMAL_THRESHOLD
    
    @staticmethod
    def normalize_iv(iv_value: float, source: str = 'unknown') -> Dict[str, Any]:
        """
        將 IV 標準化為百分比格式
        
        參數:
            iv_value: 原始 IV 值
            source: 數據來源標識（用於日誌）
        
        返回:
            dict: {
                'normalized_iv': float,  # 百分比格式 (0-500+)
                'original_iv': float,    # 原始值
                'was_decimal': bool,     # 是否從小數轉換
                'source': str,           # 數據來源
                'is_valid': bool,        # 是否為有效值
                'is_abnormal': bool,     # 是否為異常值
                'abnormal_reason': str   # 異常原因（如果有）
            }
        """
        result = {
            'normalized_iv': None,
            'original_iv': iv_value,
            'was_decimal': False,
            'source': source,
            'is_valid': False,
            'is_abnormal': False,
            'abnormal_reason': None
        }
        
        # 處理無效輸入
        if iv_value is None:
            result['abnormal_reason'] = 'IV value is None'
            logger.warning(f"IV 標準化: 輸入值為 None (來源: {source})")
            return result
        
        try:
            iv_float = float(iv_value)
        except (ValueError, TypeError):
            result['abnormal_reason'] = f'Cannot convert to float: {iv_value}'
            logger.warning(f"IV 標準化: 無法轉換為數字 '{iv_value}' (來源: {source})")
            return result
        
        # 處理負數和 NaN
        if iv_float < 0 or np.isnan(iv_float):
            result['abnormal_reason'] = f'Invalid IV value: {iv_float}'
            logger.warning(f"IV 標準化: 無效值 {iv_float} (來源: {source})")
            return result
        
        # 判斷格式並轉換
        was_decimal = IVNormalizer.is_decimal_format(iv_float)
        
        if was_decimal:
            normalized_iv = iv_float * 100
            logger.debug(f"IV 標準化: {iv_float} -> {normalized_iv}% (小數轉百分比, 來源: {source})")
        else:
            normalized_iv = iv_float
            logger.debug(f"IV 標準化: {iv_float}% (已是百分比格式, 來源: {source})")
        
        result['normalized_iv'] = normalized_iv
        result['was_decimal'] = was_decimal
        result['is_valid'] = True
        
        # 檢查異常值
        if normalized_iv > IVNormalizer.ABNORMAL_HIGH_IV:
            result['is_abnormal'] = True
            result['abnormal_reason'] = f'IV 異常高: {normalized_iv:.2f}% > {IVNormalizer.ABNORMAL_HIGH_IV}%'
            logger.warning(f"IV 標準化警告: {result['abnormal_reason']} (來源: {source})")
        elif normalized_iv < IVNormalizer.ABNORMAL_LOW_IV:
            result['is_abnormal'] = True
            result['abnormal_reason'] = f'IV 異常低: {normalized_iv:.2f}% < {IVNormalizer.ABNORMAL_LOW_IV}%'
            logger.warning(f"IV 標準化警告: {result['abnormal_reason']} (來源: {source})")
        
        return result
    
    @staticmethod
    def validate_iv_consistency(api_iv: float, calculated_iv: float, 
                                 tolerance_percent: float = 5.0) -> Dict[str, Any]:
        """
        驗證 API IV 和計算 IV 的一致性
        
        參數:
            api_iv: API 提供的 IV（百分比格式）
            calculated_iv: 計算得出的 IV（百分比格式）
            tolerance_percent: 允許的差異百分比
        
        返回:
            dict: {
                'is_consistent': bool,
                'difference': float,
                'difference_percent': float,
                'recommended_iv': float,
                'recommendation_reason': str
            }
        """
        if api_iv is None or calculated_iv is None:
            return {
                'is_consistent': False,
                'difference': None,
                'difference_percent': None,
                'recommended_iv': api_iv or calculated_iv,
                'recommendation_reason': 'One or both IV values are None'
            }
        
        difference = abs(api_iv - calculated_iv)
        difference_percent = (difference / api_iv * 100) if api_iv > 0 else 0
        is_consistent = difference_percent <= tolerance_percent
        
        if is_consistent:
            # 一致時使用平均值
            recommended_iv = (api_iv + calculated_iv) / 2
            reason = f'IV 一致 (差異 {difference_percent:.1f}% <= {tolerance_percent}%)，使用平均值'
        else:
            # 不一致時優先使用 API 值（通常更可靠）
            recommended_iv = api_iv
            reason = f'IV 不一致 (差異 {difference_percent:.1f}% > {tolerance_percent}%)，使用 API 值'
            logger.warning(f"IV 驗證警告: API IV={api_iv:.2f}%, 計算 IV={calculated_iv:.2f}%, 差異={difference_percent:.1f}%")
        
        return {
            'is_consistent': is_consistent,
            'difference': difference,
            'difference_percent': difference_percent,
            'recommended_iv': recommended_iv,
            'recommendation_reason': reason
        }


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
                    port = settings.IBKR_PORT_PAPER if settings.IBKR_USE_PAPER else settings.IBKR_PORT_LIVE
                    mode = 'paper' if settings.IBKR_USE_PAPER else 'live'
                    
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
            
            # Yahoo Finance 客户端（優化版，支持 UA 輪換和智能重試）
            if YAHOO_V2_AVAILABLE:
                try:
                    # 使用較長的延遲（12秒）避免 429 錯誤
                    # Yahoo Finance 對連續請求非常敏感，特別是期權鏈和歷史數據
                    # 2025-12-07: 從 8 秒增加到 12 秒，因為仍然遇到 429 錯誤
                    yahoo_delay = max(self.request_delay, 12.0)
                    self.yahoo_v2_client = YahooFinanceV2Client(
                        request_delay=yahoo_delay,
                        max_retries=5  # 增加重試次數
                    )
                    logger.info(f"* Yahoo Finance 客户端已初始化（優化版，延遲: {yahoo_delay}s）")
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
            
            # Alpha Vantage 客戶端（技術指標 + 歷史數據）
            if settings.ALPHA_VANTAGE_API_KEY:
                try:
                    from data_layer.alpha_vantage_client import AlphaVantageClient
                    self.alpha_vantage_client = AlphaVantageClient(
                        api_key=settings.ALPHA_VANTAGE_API_KEY,
                        request_delay=12.0  # Alpha Vantage 免費版限制: 5次/分鐘
                    )
                    logger.info("* Alpha Vantage 客戶端已初始化（技術指標 + 歷史數據）")
                except Exception as e:
                    logger.warning(f"! Alpha Vantage 初始化失敗: {e}")
                    self._record_api_failure('Alpha Vantage', str(e))
                    self.alpha_vantage_client = None
            else:
                logger.info("i Alpha Vantage 未配置，跳過初始化")
                self.alpha_vantage_client = None
            
            # Massive API 客戶端（備用數據源）
            if settings.MASSIVE_API_KEY:
                try:
                    from data_layer.massive_api_client import MassiveAPIClient
                    self.massive_api_client = MassiveAPIClient(
                        api_key=settings.MASSIVE_API_KEY,
                        request_delay=1.0
                    )
                    logger.info("* Massive API 客戶端已初始化（備用數據源）")
                except Exception as e:
                    logger.warning(f"! Massive API 初始化失敗: {e}")
                    self._record_api_failure('Massive API', str(e))
                    self.massive_api_client = None
            else:
                logger.info("i Massive API 未配置，跳過初始化")
                self.massive_api_client = None
            
            return True
        except Exception as e:
            logger.error(f"x 客户端初始化失敗: {e}")
            return False
    
    def _record_api_failure(
        self, 
        api_name: str, 
        error_message: str,
        operation: str = None,
        request_url: str = None,
        request_params: Dict = None,
        response_status: int = None,
        stack_trace: str = None
    ):
        """
        記錄 API 故障（增強版）
        
        記錄完整的錯誤上下文信息，包括請求 URL、參數和響應狀態碼。
        同時實現錯誤日誌清理機制，限制每個 API 最多保留 100 條記錄，
        並清理超過 24 小時的舊記錄。
        
        參數:
            api_name: API 名稱 ('Finnhub', 'Yahoo V2', etc.)
            error_message: 錯誤消息
            operation: 操作名稱 ('get_earnings_calendar', etc.)
            request_url: 請求 URL（可選）
            request_params: 請求參數（可選）
            response_status: HTTP 響應狀態碼（可選）
            stack_trace: 錯誤堆棧（可選）
        
        Requirements: 5.3, 5.4, 7.1, 7.2, 7.3, 7.4
        """
        if api_name not in self.api_failures:
            self.api_failures[api_name] = []
        
        # 構建詳細的錯誤記錄
        error_record = {
            'timestamp': datetime.now().isoformat(),
            'error': error_message
        }
        
        # 添加可選的上下文信息
        if operation:
            error_record['operation'] = operation
        if request_url:
            # 清理敏感信息（API Keys）
            error_record['request_url'] = self._sanitize_url(request_url)
        if request_params:
            # 清理敏感信息
            error_record['request_params'] = self._sanitize_params(request_params)
        if response_status:
            error_record['response_status'] = response_status
        if stack_trace:
            # 截斷過長的堆棧信息
            error_record['stack_trace'] = stack_trace[:2000] if len(stack_trace) > 2000 else stack_trace
        
        self.api_failures[api_name].append(error_record)
        
        # 錯誤日誌清理機制
        self._cleanup_api_failure_records(api_name)
        
        # 記錄日誌（使用結構化格式）
        log_parts = [f"API 故障: {api_name}"]
        if operation:
            log_parts.append(f"操作: {operation}")
        log_parts.append(f"錯誤: {error_message}")
        if response_status:
            log_parts.append(f"狀態碼: {response_status}")
        
        logger.warning(" | ".join(log_parts))
        
        if stack_trace:
            logger.debug(f"堆棧信息: {stack_trace[:500]}...")
    
    def _cleanup_api_failure_records(self, api_name: str):
        """
        清理 API 故障記錄
        
        限制每個 API 最多保留 100 條記錄，並清理超過 24 小時的舊記錄。
        
        參數:
            api_name: API 名稱
        
        Requirements: 7.1, 7.2
        """
        if api_name not in self.api_failures:
            return
        
        records = self.api_failures[api_name]
        
        # 限制: 每個 API 最多保留 100 條記錄
        max_records = getattr(settings, 'MAX_API_FAILURE_RECORDS', 100)
        if len(records) > max_records:
            self.api_failures[api_name] = records[-max_records:]
            logger.debug(f"清理 {api_name} 故障記錄，保留最近 {max_records} 條")
        
        # 清理超過 24 小時的記錄
        retention_hours = getattr(settings, 'API_FAILURE_RETENTION_HOURS', 24)
        cutoff_time = datetime.now() - timedelta(hours=retention_hours)
        
        original_count = len(self.api_failures[api_name])
        self.api_failures[api_name] = [
            record for record in self.api_failures[api_name]
            if self._parse_timestamp(record.get('timestamp', '')) > cutoff_time
        ]
        
        cleaned_count = original_count - len(self.api_failures[api_name])
        if cleaned_count > 0:
            logger.debug(f"清理 {api_name} 過期故障記錄: {cleaned_count} 條")
    
    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """
        解析時間戳字符串
        
        參數:
            timestamp_str: ISO 格式的時間戳字符串
        
        返回:
            datetime 對象，解析失敗時返回最小時間
        """
        try:
            return datetime.fromisoformat(timestamp_str)
        except (ValueError, TypeError):
            return datetime.min
    
    def _sanitize_url(self, url: str) -> str:
        """
        清理 URL 中的敏感信息（API Keys）
        
        參數:
            url: 原始 URL
        
        返回:
            清理後的 URL
        """
        if not url:
            return url
        
        # 替換常見的 API Key 參數
        import re
        patterns = [
            (r'(api_?key=)[^&]+', r'\1***'),
            (r'(apikey=)[^&]+', r'\1***'),
            (r'(token=)[^&]+', r'\1***'),
            (r'(key=)[^&]+', r'\1***'),
        ]
        
        result = url
        for pattern, replacement in patterns:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        
        return result
    
    def _sanitize_params(self, params: Dict) -> Dict:
        """
        清理參數中的敏感信息
        
        參數:
            params: 原始參數字典
        
        返回:
            清理後的參數字典
        """
        if not params:
            return params
        
        sensitive_keys = ['api_key', 'apikey', 'token', 'key', 'secret', 'password']
        result = params.copy()
        
        for key in result:
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                result[key] = '***'
        
        return result
    
    def _sanitize_log_message(self, message: str) -> str:
        """
        清理日誌消息中的敏感信息
        
        在所有日誌輸出前清理敏感信息，包括 API Keys、密碼等。
        只顯示 API Key 的前4位和後4位，中間用 *** 替代。
        
        參數:
            message: 原始日誌消息
        
        返回:
            清理後的日誌消息
        
        Requirements: Security Considerations
        """
        if not message:
            return message
        
        import re
        
        # 從環境變量獲取需要清理的 API Keys
        api_key_names = [
            'FRED_API_KEY', 'FINNHUB_API_KEY', 'RAPIDAPI_KEY',
            'ALPHA_VANTAGE_API_KEY', 'MASSIVE_API_KEY'
        ]
        
        result = message
        
        for key_name in api_key_names:
            key_value = os.environ.get(key_name, '')
            if key_value and len(key_value) > 8 and key_value in result:
                # 只顯示前4位和後4位
                masked = f"{key_value[:4]}...{key_value[-4:]}"
                result = result.replace(key_value, masked)
        
        # 清理常見的敏感模式
        patterns = [
            # API Key 模式 (32-64 字符的字母數字字符串)
            (r'(["\']?(?:api[_-]?key|apikey|token|secret)["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9]{32,64})(["\']?)', 
             r'\1***REDACTED***\3'),
            # Bearer Token
            (r'(Bearer\s+)[a-zA-Z0-9._-]+', r'\1***REDACTED***'),
        ]
        
        for pattern, replacement in patterns:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        
        return result
    
    def _validate_ticker(self, ticker: str) -> bool:
        """
        驗證股票代碼格式
        
        確保股票代碼符合有效格式，防止注入攻擊和無效請求。
        
        有效格式:
        - 1-10 個字符
        - 只允許大寫字母、數字、點號(.)和連字符(-)
        - 例如: AAPL, BRK.B, BRK-A, GOOGL
        
        參數:
            ticker: 股票代碼
        
        返回:
            bool: 是否為有效的股票代碼
        
        Requirements: Security Considerations
        """
        if not ticker:
            logger.warning("股票代碼為空")
            return False
        
        import re
        
        # 轉換為大寫
        ticker_upper = ticker.upper().strip()
        
        # 驗證長度
        if len(ticker_upper) < 1 or len(ticker_upper) > 10:
            logger.warning(f"股票代碼長度無效: {len(ticker_upper)} (應為 1-10)")
            return False
        
        # 驗證格式: 只允許字母、數字、點號和連字符
        pattern = r'^[A-Z0-9.\-]{1,10}$'
        if not re.match(pattern, ticker_upper):
            logger.warning(f"股票代碼格式無效: {ticker_upper}")
            return False
        
        # 不允許以點號或連字符開頭或結尾
        if ticker_upper.startswith('.') or ticker_upper.startswith('-'):
            logger.warning(f"股票代碼不能以特殊字符開頭: {ticker_upper}")
            return False
        
        if ticker_upper.endswith('.') or ticker_upper.endswith('-'):
            logger.warning(f"股票代碼不能以特殊字符結尾: {ticker_upper}")
            return False
        
        return True
    
    def _normalize_ticker(self, ticker: str) -> Optional[str]:
        """
        標準化股票代碼
        
        將股票代碼轉換為標準格式（大寫、去除空白）。
        如果代碼無效，返回 None。
        
        參數:
            ticker: 原始股票代碼
        
        返回:
            str: 標準化後的股票代碼，無效時返回 None
        
        Requirements: Security Considerations
        """
        if not ticker:
            return None
        
        normalized = ticker.upper().strip()
        
        if self._validate_ticker(normalized):
            return normalized
        
        return None
    
    def _handle_api_failure(
        self, 
        api_name: str, 
        operation: str, 
        error: Exception,
        request_url: str = None,
        request_params: Dict = None,
        response_status: int = None
    ) -> None:
        """
        統一的 API 失敗處理
        
        提供統一的錯誤處理接口，自動提取錯誤類型、消息和堆棧信息，
        並調用 _record_api_failure 記錄詳細的錯誤上下文。
        
        參數:
            api_name: API 名稱 ('Finnhub', 'Yahoo V2', etc.)
            operation: 操作名稱 ('get_earnings_calendar', etc.)
            error: 異常對象
            request_url: 請求 URL（可選）
            request_params: 請求參數（可選）
            response_status: HTTP 響應狀態碼（可選）
        
        Requirements: 5.3, 5.4, 7.1, 7.2, 7.3, 7.4
        """
        # 提取錯誤信息
        error_type = type(error).__name__
        error_message = str(error)
        stack_trace = traceback.format_exc()
        
        # 構建完整的錯誤消息
        full_error_message = f"{operation}: [{error_type}] {error_message}"
        
        # 記錄 API 故障
        self._record_api_failure(
            api_name=api_name,
            error_message=full_error_message,
            operation=operation,
            request_url=request_url,
            request_params=request_params,
            response_status=response_status,
            stack_trace=stack_trace
        )
        
        # 記錄詳細的錯誤日誌
        logger.error(f"✗ {api_name} {operation} 失敗: [{error_type}] {error_message}")
        logger.debug(f"完整堆棧信息:\n{stack_trace}")
    
    def cleanup_all_api_failure_records(self):
        """
        清理所有 API 的故障記錄
        
        遍歷所有 API 並執行清理操作。
        """
        for api_name in list(self.api_failures.keys()):
            self._cleanup_api_failure_records(api_name)
        
        logger.info("已清理所有 API 故障記錄")
    
    def get_api_failure_summary(self) -> Dict[str, Any]:
        """
        獲取 API 故障摘要
        
        返回:
            dict: 包含各 API 故障統計的摘要
        """
        summary = {}
        
        for api_name, records in self.api_failures.items():
            if not records:
                continue
            
            # 統計各操作的故障次數
            operation_counts = {}
            status_counts = {}
            
            for record in records:
                op = record.get('operation', 'unknown')
                operation_counts[op] = operation_counts.get(op, 0) + 1
                
                status = record.get('response_status')
                if status:
                    status_counts[status] = status_counts.get(status, 0) + 1
            
            # 獲取最近的錯誤
            latest_error = records[-1] if records else None
            
            summary[api_name] = {
                'total_failures': len(records),
                'operation_counts': operation_counts,
                'status_counts': status_counts,
                'latest_error': latest_error,
                'first_failure': records[0].get('timestamp') if records else None,
                'last_failure': records[-1].get('timestamp') if records else None
            }
        
        return summary
    
    def _record_fallback(
        self, 
        data_type: str, 
        source_used: str,
        success: bool = True,
        error_reason: str = None
    ):
        """
        記錄使用的降級數據源（增強版）
        
        記錄完整的嘗試路徑，包括成功和失敗的數據源，以及失敗原因。
        這使得可以追蹤每次數據獲取操作的完整降級路徑。
        
        參數:
            data_type: 數據類型 ('stock_info', 'option_chain', etc.)
            source_used: 使用的數據源名稱
            success: 是否成功獲取數據
            error_reason: 失敗原因（僅當 success=False 時使用）
        
        Requirements: 5.2, 5.5
        """
        # 初始化 fallback_used 結構
        if data_type not in self.fallback_used:
            self.fallback_used[data_type] = []
        
        # 初始化嘗試路徑追蹤結構
        if not hasattr(self, '_attempt_paths'):
            self._attempt_paths = {}
        
        if data_type not in self._attempt_paths:
            self._attempt_paths[data_type] = {
                'current_attempt': [],
                'history': []
            }
        
        # 記錄當前嘗試
        attempt_record = {
            'source': source_used,
            'success': success,
            'timestamp': datetime.now().isoformat()
        }
        
        if not success and error_reason:
            attempt_record['error_reason'] = error_reason
        
        self._attempt_paths[data_type]['current_attempt'].append(attempt_record)
        
        # 如果成功，記錄到 fallback_used 並完成當前嘗試路徑
        if success:
            if source_used not in self.fallback_used[data_type]:
                self.fallback_used[data_type].append(source_used)
            
            # 輸出完整的嘗試路徑日誌
            self._log_attempt_path(data_type)
            
            # 保存到歷史記錄並重置當前嘗試
            self._attempt_paths[data_type]['history'].append(
                self._attempt_paths[data_type]['current_attempt'].copy()
            )
            self._attempt_paths[data_type]['current_attempt'] = []
            
            # 限制歷史記錄數量（最多保留 50 條）
            if len(self._attempt_paths[data_type]['history']) > 50:
                self._attempt_paths[data_type]['history'] = \
                    self._attempt_paths[data_type]['history'][-50:]
    
    def _log_attempt_path(self, data_type: str):
        """
        輸出完整的嘗試路徑日誌
        
        在日誌中輸出數據獲取操作的完整嘗試路徑，包括所有嘗試過的數據源
        及其結果（成功/失敗）。
        
        參數:
            data_type: 數據類型
        
        Requirements: 5.5
        """
        if not hasattr(self, '_attempt_paths') or data_type not in self._attempt_paths:
            return
        
        attempts = self._attempt_paths[data_type]['current_attempt']
        if not attempts:
            return
        
        # 構建嘗試路徑字符串
        path_parts = []
        for attempt in attempts:
            source = attempt['source']
            if attempt['success']:
                path_parts.append(f"{source}(✓)")
            else:
                error = attempt.get('error_reason', 'failed')
                # 截斷過長的錯誤信息
                if len(error) > 30:
                    error = error[:27] + '...'
                path_parts.append(f"{source}(✗:{error})")
        
        path_str = " → ".join(path_parts)
        
        # 統計信息
        total_attempts = len(attempts)
        failed_attempts = sum(1 for a in attempts if not a['success'])
        
        # 輸出日誌
        if failed_attempts > 0:
            logger.info(f"  降級路徑 [{data_type}]: {path_str}")
            logger.info(f"  嘗試統計: {total_attempts} 次嘗試, {failed_attempts} 次失敗")
        else:
            logger.debug(f"  數據源路徑 [{data_type}]: {path_str}")
    
    def _record_fallback_failure(self, data_type: str, source: str, error_reason: str):
        """
        記錄降級嘗試失敗
        
        當某個數據源嘗試失敗時調用此方法，記錄失敗信息到嘗試路徑中。
        
        參數:
            data_type: 數據類型
            source: 失敗的數據源名稱
            error_reason: 失敗原因
        
        Requirements: 5.2, 5.5
        """
        self._record_fallback(data_type, source, success=False, error_reason=error_reason)
    
    def get_attempt_path_summary(self, data_type: str = None) -> Dict[str, Any]:
        """
        獲取嘗試路徑摘要
        
        返回指定數據類型或所有數據類型的嘗試路徑統計信息。
        
        參數:
            data_type: 數據類型（可選，如不指定則返回所有類型）
        
        返回:
            dict: 嘗試路徑摘要，包含各數據類型的嘗試統計
        
        Requirements: 5.5
        """
        if not hasattr(self, '_attempt_paths'):
            return {}
        
        def summarize_type(dt: str) -> Dict:
            if dt not in self._attempt_paths:
                return {}
            
            history = self._attempt_paths[dt]['history']
            if not history:
                return {'total_operations': 0}
            
            # 統計各數據源的使用次數和成功率
            source_stats = {}
            total_attempts = 0
            total_failures = 0
            
            for path in history:
                for attempt in path:
                    source = attempt['source']
                    if source not in source_stats:
                        source_stats[source] = {'attempts': 0, 'successes': 0, 'failures': 0}
                    
                    source_stats[source]['attempts'] += 1
                    total_attempts += 1
                    
                    if attempt['success']:
                        source_stats[source]['successes'] += 1
                    else:
                        source_stats[source]['failures'] += 1
                        total_failures += 1
            
            # 計算成功率
            for source in source_stats:
                stats = source_stats[source]
                stats['success_rate'] = (
                    stats['successes'] / stats['attempts'] * 100 
                    if stats['attempts'] > 0 else 0
                )
            
            return {
                'total_operations': len(history),
                'total_attempts': total_attempts,
                'total_failures': total_failures,
                'average_attempts_per_operation': total_attempts / len(history) if history else 0,
                'source_statistics': source_stats
            }
        
        if data_type:
            return {data_type: summarize_type(data_type)}
        else:
            return {dt: summarize_type(dt) for dt in self._attempt_paths.keys()}
    
    def _validate_and_supplement_finviz_data(
        self, 
        finviz_data: Dict, 
        ticker: str
    ) -> Optional[Dict]:
        """
        驗證 Finviz 數據並補充缺失的關鍵字段
        
        當 Finviz 返回部分數據時，此方法會：
        1. 記錄哪些字段可用、哪些字段缺失
        2. 對於關鍵字段（price, eps_ttm, pe）缺失時，嘗試從 yfinance 補充
        3. 對於非關鍵字段缺失，使用 None 值並繼續處理
        4. 評估數據質量（complete/partial/minimal）
        
        參數:
            finviz_data: 從 Finviz 獲取的原始數據
            ticker: 股票代碼
        
        返回:
            dict: 增強後的數據，包含以下額外字段：
                - 'missing_fields': 缺失的字段列表
                - 'supplemented_fields': 從 yfinance 補充的字段列表
                - 'data_quality': 'complete' | 'partial' | 'minimal'
                - 'data_source': 數據來源標記
            如果關鍵字段無法補充，返回 None
        
        Requirements: 4.1, 4.2, 4.3, 4.4, 4.5
        """
        # 定義所有預期的 Finviz 字段
        EXPECTED_FINVIZ_FIELDS = [
            'price', 'eps_ttm', 'pe', 'forward_pe', 'peg', 'market_cap',
            'volume', 'dividend_yield', 'beta', 'atr', 'rsi', 'company_name',
            'sector', 'industry', 'target_price', 'profit_margin', 
            'operating_margin', 'roe', 'roa', 'debt_eq', 'insider_own',
            'inst_own', 'short_float', 'avg_volume', 'eps_next_y'
        ]
        
        # 定義關鍵字段（必須有值才能繼續）
        CRITICAL_FIELDS = ['price', 'eps_ttm', 'pe']
        
        # 初始化結果
        result = finviz_data.copy()
        result['missing_fields'] = []
        result['supplemented_fields'] = []
        result['data_source'] = 'Finviz'
        
        # 記錄缺失的字段
        for field in EXPECTED_FINVIZ_FIELDS:
            if field not in result or result.get(field) is None:
                result['missing_fields'].append(field)
        
        # 記錄字段可用性日誌
        available_count = len(EXPECTED_FINVIZ_FIELDS) - len(result['missing_fields'])
        logger.info(f"  Finviz 字段可用性: {available_count}/{len(EXPECTED_FINVIZ_FIELDS)}")
        
        if result['missing_fields']:
            logger.debug(f"  缺失字段: {', '.join(result['missing_fields'])}")
        
        # 檢查關鍵字段是否缺失
        missing_critical = [f for f in CRITICAL_FIELDS if f in result['missing_fields']]
        
        if missing_critical:
            logger.warning(f"  ! Finviz 缺失關鍵字段: {', '.join(missing_critical)}")
            
            # 嘗試從 yfinance 補充關鍵字段
            try:
                logger.info(f"  嘗試從 yfinance 補充關鍵字段...")
                yf_ticker = yf.Ticker(ticker)
                yf_info = yf_ticker.info
                
                # 映射 yfinance 字段到 Finviz 字段
                yf_field_mapping = {
                    'price': 'currentPrice',
                    'eps_ttm': 'trailingEps',
                    'pe': 'trailingPE'
                }
                
                supplemented = []
                for finviz_field in missing_critical:
                    yf_field = yf_field_mapping.get(finviz_field)
                    if yf_field and yf_info.get(yf_field) is not None:
                        result[finviz_field] = yf_info[yf_field]
                        supplemented.append(finviz_field)
                        logger.info(f"    * 補充 {finviz_field}: {result[finviz_field]}")
                
                if supplemented:
                    result['supplemented_fields'] = supplemented
                    result['data_source'] = 'Finviz+yfinance'
                    # 從 missing_fields 中移除已補充的字段
                    result['missing_fields'] = [f for f in result['missing_fields'] if f not in supplemented]
                    logger.info(f"  * 成功從 yfinance 補充 {len(supplemented)} 個關鍵字段")
                
                # 再次檢查是否還有關鍵字段缺失
                still_missing_critical = [f for f in CRITICAL_FIELDS if result.get(f) is None]
                if still_missing_critical:
                    logger.error(f"  x 無法補充關鍵字段: {', '.join(still_missing_critical)}")
                    self._record_api_failure('Finviz', f"Missing critical fields: {still_missing_critical}")
                    return None
                    
            except Exception as e:
                logger.error(f"  x yfinance 補充失敗: {e}")
                self._record_api_failure('yfinance', f"supplement_finviz: {e}")
                return None
        
        # 計算數據質量
        total_fields = len(EXPECTED_FINVIZ_FIELDS)
        available_fields = total_fields - len(result['missing_fields'])
        quality_ratio = available_fields / total_fields
        
        if quality_ratio >= 0.9:
            result['data_quality'] = 'complete'
        elif quality_ratio >= 0.6:
            result['data_quality'] = 'partial'
        else:
            result['data_quality'] = 'minimal'
        
        logger.info(f"  數據質量: {result['data_quality']} ({available_fields}/{total_fields} 字段, {quality_ratio*100:.1f}%)")
        
        return result
    
    def get_api_status_report(self) -> Dict[str, Any]:
        """
        獲取 API 狀態報告（增強版）
        
        返回包含以下信息的報告：
        - API 故障記錄
        - 降級使用情況
        - 成功率統計
        - 自主計算統計
        - 數據源健康度評分
        
        返回:
            dict: 包含 API 故障、降級使用情況和自主計算統計的報告
        
        Requirements: 6.1, 6.2, 6.3, 6.4, 6.5
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
        
        # 計算成功率統計（Requirements 6.2）
        success_rate_stats = self._calculate_success_rates()
        
        # 計算數據源健康度評分（Requirements 6.5）
        health_score = self._calculate_health_score(
            total_failures, 
            total_fallback_calls,
            success_rate_stats
        )
        
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
            
            # 成功率統計（Requirements 6.2）
            'success_rates': success_rate_stats,
            
            # 降級使用統計（Requirements 6.3）
            'fallback_statistics': self.get_attempt_path_summary(),
            
            # 數據源健康度評分（Requirements 6.5）
            'health_score': health_score,
            
            # 自主計算模塊可用性
            'self_calculation_available': {
                'bs_calculator': self.bs_calculator is not None,
                'greeks_calculator': self.greeks_calculator is not None,
                'iv_calculator': self.iv_calculator is not None
            }
        }
    
    def _calculate_success_rates(self) -> Dict[str, Any]:
        """
        計算各 API 的成功率統計
        
        基於嘗試路徑歷史記錄計算每個數據源的成功率。
        
        返回:
            dict: 各 API 的成功率統計
        
        Requirements: 6.2
        """
        if not hasattr(self, '_attempt_paths'):
            return {}
        
        api_stats = {}
        
        for data_type, paths_data in self._attempt_paths.items():
            history = paths_data.get('history', [])
            
            for path in history:
                for attempt in path:
                    source = attempt['source']
                    
                    if source not in api_stats:
                        api_stats[source] = {
                            'total_attempts': 0,
                            'successes': 0,
                            'failures': 0
                        }
                    
                    api_stats[source]['total_attempts'] += 1
                    if attempt['success']:
                        api_stats[source]['successes'] += 1
                    else:
                        api_stats[source]['failures'] += 1
        
        # 計算成功率
        for source, stats in api_stats.items():
            if stats['total_attempts'] > 0:
                stats['success_rate'] = round(
                    stats['successes'] / stats['total_attempts'] * 100, 2
                )
            else:
                stats['success_rate'] = 0.0
        
        return api_stats
    
    def _calculate_health_score(
        self, 
        total_failures: int, 
        total_fallback_calls: int,
        success_rates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        計算數據源健康度評分
        
        評分標準：
        - 100: 優秀 - 無故障，主要數據源正常
        - 80-99: 良好 - 少量故障，降級正常工作
        - 60-79: 一般 - 較多故障，依賴降級方案
        - 40-59: 較差 - 大量故障，數據可靠性下降
        - 0-39: 危險 - 嚴重故障，需要立即處理
        
        返回:
            dict: 健康度評分和狀態
        
        Requirements: 6.5
        """
        # 基礎分數 100
        score = 100.0
        issues = []
        
        # 根據故障數量扣分
        if total_failures > 0:
            # 每個故障扣 2 分，最多扣 30 分
            failure_penalty = min(total_failures * 2, 30)
            score -= failure_penalty
            if total_failures > 5:
                issues.append(f"高故障率: {total_failures} 次故障")
        
        # 根據降級使用情況扣分
        if total_fallback_calls > 0:
            # 計算主要數據源的成功率
            primary_sources = ['finnhub', 'Finviz', 'IBKR', 'Yahoo V2']
            primary_success_rate = 0
            primary_count = 0
            
            for source in primary_sources:
                if source in success_rates:
                    primary_success_rate += success_rates[source].get('success_rate', 0)
                    primary_count += 1
            
            if primary_count > 0:
                avg_primary_rate = primary_success_rate / primary_count
                if avg_primary_rate < 80:
                    # 主要數據源成功率低於 80% 扣分
                    rate_penalty = (80 - avg_primary_rate) * 0.5
                    score -= rate_penalty
                    issues.append(f"主要數據源成功率低: {avg_primary_rate:.1f}%")
        
        # 檢查關鍵客戶端可用性
        if not self.finnhub_client:
            score -= 10
            issues.append("Finnhub 客戶端不可用")
        
        if self.use_ibkr and (not self.ibkr_client or not self.ibkr_client.is_connected()):
            score -= 15
            issues.append("IBKR 已啟用但未連接")
        
        # 確保分數在 0-100 範圍內
        score = max(0, min(100, score))
        
        # 確定健康狀態
        if score >= 80:
            status = 'healthy'
            status_text = '健康'
        elif score >= 60:
            status = 'degraded'
            status_text = '降級'
        elif score >= 40:
            status = 'warning'
            status_text = '警告'
        else:
            status = 'critical'
            status_text = '危險'
        
        return {
            'score': round(score, 1),
            'status': status,
            'status_text': status_text,
            'issues': issues,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_health_check(self) -> Dict[str, Any]:
        """
        系統健康檢查
        
        執行快速健康檢查，返回系統狀態和任何警告或錯誤。
        
        返回:
            dict: 健康檢查結果
            {
                'status': 'healthy' | 'degraded' | 'unhealthy',
                'warnings': List[str],
                'errors': List[str],
                'api_availability': Dict[str, bool],
                'timestamp': str
            }
        
        Requirements: 6.1, 6.2, 6.3, 6.4, 6.5
        """
        health = {
            'status': 'healthy',
            'warnings': [],
            'errors': [],
            'api_availability': {},
            'timestamp': datetime.now().isoformat()
        }
        
        # 檢查各 API 客戶端可用性
        health['api_availability'] = {
            'finnhub': self.finnhub_client is not None,
            'fred': self.fred_client is not None,
            'yahoo_v2': self.yahoo_v2_client is not None,
            'yfinance': self.yfinance_client is not None,
            'finviz': self.finviz_scraper is not None,
            'ibkr': self.ibkr_client is not None and (
                self.ibkr_client.is_connected() if self.ibkr_client else False
            ),
            'rapidapi': getattr(self, 'rapidapi_client', None) is not None,
            'alpha_vantage': getattr(self, 'alpha_vantage_client', None) is not None,
            'massive_api': getattr(self, 'massive_api_client', None) is not None
        }
        
        # 檢查 API 故障率
        for api_name, failures in self.api_failures.items():
            failure_count = len(failures)
            if failure_count > 10:
                health['errors'].append(f"{api_name} 有 {failure_count} 次故障")
            elif failure_count > 5:
                health['warnings'].append(f"{api_name} 有 {failure_count} 次故障")
        
        # 檢查 RapidAPI 使用量
        if hasattr(self, 'rapidapi_client') and self.rapidapi_client:
            if hasattr(self.rapidapi_client, 'rate_limiter'):
                usage = getattr(self.rapidapi_client.rate_limiter, 'usage_count', 0)
                if usage > 450:
                    health['warnings'].append(f"RapidAPI 使用量接近限制: {usage}/500")
                elif usage > 400:
                    health['warnings'].append(f"RapidAPI 使用量較高: {usage}/500")
        
        # 檢查 IBKR 連接狀態
        if self.use_ibkr:
            if not self.ibkr_client:
                health['warnings'].append("IBKR 已啟用但客戶端未初始化")
            elif not self.ibkr_client.is_connected():
                health['warnings'].append("IBKR 已啟用但未連接")
        
        # 檢查自主計算模塊
        if not self.bs_calculator or not self.greeks_calculator or not self.iv_calculator:
            health['warnings'].append("部分自主計算模塊不可用")
        
        # 確定整體狀態
        if health['errors']:
            health['status'] = 'unhealthy'
        elif health['warnings']:
            health['status'] = 'degraded'
        else:
            health['status'] = 'healthy'
        
        return health
    
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
        
        降級順序: IBKR → Finnhub → Alpha Vantage → Finviz → Yahoo Finance → yfinance
        
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
        
        # 方案0: 最高優先級 - IBKR（如果已連接）
        if self.ibkr_client and self.ibkr_client.is_connected():
            try:
                self._rate_limit_delay()
                logger.info("  使用 IBKR API (最高優先級)...")
                stock_data = self.ibkr_client.get_stock_info(ticker)
                
                if stock_data and stock_data.get('current_price', 0) > 0:
                    logger.info(f"* 成功獲取 {ticker} 基本信息 (IBKR)")
                    logger.info(f"  當前股價: ${stock_data['current_price']:.2f}")
                    self._record_fallback('stock_info', 'IBKR')
                    return stock_data
                else:
                    logger.warning("! IBKR 返回無效數據，降級到 Finnhub")
                    self._record_fallback_failure('stock_info', 'IBKR', '返回無效數據')
            except Exception as e:
                logger.warning(f"! IBKR 獲取失敗: {e}，降級到 Finnhub")
                self._record_api_failure('IBKR', f"get_stock_info: {e}")
                self._record_fallback_failure('stock_info', 'IBKR', str(e))
        
        # 方案1: Finnhub（實時股價，第二優先級）
        if self.finnhub_client:
            try:
                logger.info("  使用 Finnhub API...")
                self._rate_limit_delay()
                
                # 獲取實時報價
                quote = self.finnhub_client.quote(ticker)
                
                if quote and quote.get('c', 0) > 0:  # 'c' = current price
                    # 獲取公司基本資料
                    profile = None
                    try:
                        profile = self.finnhub_client.company_profile2(symbol=ticker)
                    except:
                        pass
                    
                    stock_data = {
                        'ticker': ticker,
                        'current_price': quote.get('c', 0),  # current price
                        'open': quote.get('o', 0),  # open
                        'high': quote.get('h', 0),  # high
                        'low': quote.get('l', 0),  # low
                        'previous_close': quote.get('pc', 0),  # previous close
                        'change': quote.get('d', 0),  # change
                        'change_percent': quote.get('dp', 0),  # change percent
                        'volume': None,  # Finnhub quote 不提供 volume
                        'data_source': 'Finnhub'
                    }
                    
                    # 補充公司資料
                    if profile:
                        stock_data.update({
                            'company_name': profile.get('name', ''),
                            'market_cap': profile.get('marketCapitalization', 0) * 1000000 if profile.get('marketCapitalization') else 0,
                            'sector': profile.get('finnhubIndustry', ''),
                            'industry': profile.get('finnhubIndustry', ''),
                            'country': profile.get('country', ''),
                            'exchange': profile.get('exchange', ''),
                            'ipo_date': profile.get('ipo', ''),
                            'logo': profile.get('logo', ''),
                            'weburl': profile.get('weburl', '')
                        })
                    
                    logger.info(f"* 成功獲取 {ticker} 基本信息 (Finnhub)")
                    logger.info(f"  當前股價: ${stock_data['current_price']:.2f}")
                    self._record_fallback('stock_info', 'Finnhub')
                    return stock_data
                else:
                    logger.warning("! Finnhub 返回無效數據，降級到 Alpha Vantage")
                    self._record_fallback_failure('stock_info', 'Finnhub', '返回無效數據')
            except Exception as e:
                logger.warning(f"! Finnhub 獲取失敗: {e}，降級到 Alpha Vantage")
                self._record_api_failure('Finnhub', f"get_stock_info: {e}")
                self._record_fallback_failure('stock_info', 'Finnhub', str(e))
        
        # 方案2: Alpha Vantage（第三優先級）
        if hasattr(self, 'alpha_vantage_client') and self.alpha_vantage_client:
            try:
                logger.info("  使用 Alpha Vantage API...")
                quote_data = self.alpha_vantage_client.get_quote(ticker)
                
                if quote_data and quote_data.get('current_price', 0) > 0:
                    # 嘗試獲取公司概況補充數據
                    overview = None
                    try:
                        overview = self.alpha_vantage_client.get_company_overview(ticker)
                    except:
                        pass
                    
                    stock_data = {
                        'ticker': ticker,
                        'current_price': quote_data.get('current_price', 0),
                        'open': quote_data.get('open', 0),
                        'high': quote_data.get('high', 0),
                        'low': quote_data.get('low', 0),
                        'volume': quote_data.get('volume', 0),
                        'previous_close': quote_data.get('previous_close', 0),
                        'change': quote_data.get('change', 0),
                        'change_percent': quote_data.get('change_percent', 0),
                        'data_source': 'Alpha Vantage'
                    }
                    
                    # 補充公司概況數據
                    if overview:
                        stock_data.update({
                            'market_cap': overview.get('market_cap', 0),
                            'pe_ratio': overview.get('pe_ratio', 0),
                            'forward_pe': overview.get('forward_pe', 0),
                            'eps': overview.get('eps', 0),
                            'beta': overview.get('beta', 0),
                            'dividend_rate': overview.get('dividend_yield', 0),
                            'company_name': overview.get('company_name', ''),
                            'sector': overview.get('sector', ''),
                            'industry': overview.get('industry', ''),
                            'fifty_two_week_high': overview.get('52_week_high', 0),
                            'fifty_two_week_low': overview.get('52_week_low', 0)
                        })
                    
                    logger.info(f"* 成功獲取 {ticker} 基本信息 (Alpha Vantage)")
                    logger.info(f"  當前股價: ${stock_data['current_price']:.2f}")
                    self._record_fallback('stock_info', 'Alpha Vantage')
                    return stock_data
                else:
                    logger.warning("! Alpha Vantage 返回無效數據，降級到 Finviz")
                    self._record_fallback_failure('stock_info', 'Alpha Vantage', '返回無效數據')
            except Exception as e:
                logger.warning(f"! Alpha Vantage 獲取失敗: {e}，降級到 Finviz")
                self._record_api_failure('Alpha Vantage', f"get_stock_info: {e}")
                self._record_fallback_failure('stock_info', 'Alpha Vantage', str(e))
        
        # 方案3: 使用 Finviz（準確的基本面數據）
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
                        logger.warning("! Finviz 數據驗證失敗，降級到 Yahoo Finance")
                        self._record_fallback_failure('stock_info', 'Finviz', '數據驗證失敗')
                else:
                    logger.warning("! Finviz 未返回數據，降級到 Yahoo Finance")
                    self._record_fallback_failure('stock_info', 'Finviz', '未返回數據')
                    
            except Exception as e:
                logger.warning(f"! Finviz 獲取失敗: {e}，降級到 Yahoo Finance")
                self._record_api_failure('Finviz', f"get_stock_info: {e}")
                self._record_fallback_failure('stock_info', 'Finviz', str(e))
        
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
                else:
                    logger.warning("! Yahoo Finance 返回空數據，降級到 Massive API")
                    self._record_fallback_failure('stock_info', 'Yahoo Finance', '返回空數據')
            except Exception as e:
                logger.warning(f"Yahoo Finance 获取失败: {e}，降级到 Massive API")
                self._record_api_failure('Yahoo Finance', f"get_stock_info: {e}")
                self._record_fallback_failure('stock_info', 'Yahoo Finance', str(e))
        
        # 方案4: 降级到 Massive API
        if hasattr(self, 'massive_api_client') and self.massive_api_client:
            try:
                logger.info("  使用 Massive API...")
                quote_data = self.massive_api_client.get_quote(ticker)
                
                if quote_data and quote_data.get('current_price', 0) > 0:
                    # 嘗試獲取公司信息補充數據
                    company_info = None
                    try:
                        company_info = self.massive_api_client.get_company_info(ticker)
                    except:
                        pass
                    
                    stock_data = {
                        'ticker': ticker,
                        'current_price': quote_data.get('current_price', 0),
                        'open': quote_data.get('open', 0),
                        'high': quote_data.get('high', 0),
                        'low': quote_data.get('low', 0),
                        'volume': quote_data.get('volume', 0),
                        'previous_close': quote_data.get('previous_close', 0),
                        'data_source': 'Massive API'
                    }
                    
                    # 補充公司信息
                    if company_info:
                        stock_data.update({
                            'market_cap': company_info.get('market_cap', 0),
                            'pe_ratio': company_info.get('pe_ratio', 0),
                            'eps': company_info.get('eps', 0),
                            'beta': company_info.get('beta', 0),
                            'dividend_rate': company_info.get('dividend_yield', 0),
                            'company_name': company_info.get('company_name', ''),
                            'sector': company_info.get('sector', ''),
                            'industry': company_info.get('industry', '')
                        })
                    
                    logger.info(f"* 成功獲取 {ticker} 基本信息 (Massive API)")
                    logger.info(f"  當前股價: ${stock_data['current_price']:.2f}")
                    self._record_fallback('stock_info', 'Massive API')
                    return stock_data
                else:
                    logger.warning("! Massive API 返回無效數據，降級到 yfinance")
                    self._record_fallback_failure('stock_info', 'Massive API', '返回無效數據')
            except Exception as e:
                logger.warning(f"! Massive API 獲取失敗: {e}，降級到 yfinance")
                self._record_api_failure('Massive API', f"get_stock_info: {e}")
                self._record_fallback_failure('stock_info', 'Massive API', str(e))
        
        # 方案5: 降级到 yfinance（最後備用）
        try:
            self._rate_limit_delay()
            logger.info("  使用 yfinance (最後備用)...")
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
                'industry': info.get('industry', ''),
                'data_source': 'yfinance'
            }
            
            logger.info(f"* 成功獲取 {ticker} 基本信息 (yfinance)")
            logger.info(f"  當前股價: ${stock_data['current_price']:.2f}")
            if stock_data['pe_ratio']:
                logger.info(f"  市盈率: {stock_data['pe_ratio']:.2f}")
            if stock_data['eps']:
                logger.info(f"  EPS: ${stock_data['eps']:.2f}")
            self._record_fallback('stock_info', 'yfinance')
            
            return stock_data
            
        except Exception as e:
            logger.error(f"x 獲取 {ticker} 基本信息失敗: {e}")
            self._record_api_failure('yfinance', f"get_stock_info: {e}")
            return None
    
    def get_historical_data(self, ticker, period='1mo', interval='1d', max_retries=3):
        """
        獲取歷史OHLCV數據（支持多數據源降級）
        
        降級順序: IBKR → Alpha Vantage → yfinance → Massive API
        
        參數:
            ticker: 股票代碼
            period: 時間週期 ('1d', '5d', '1mo', '3mo', '1y')
            interval: K線間隔 ('1m', '5m', '15m', '30m', '60m', '1d')
            max_retries: 最大重試次數（默認3次）
        
        返回: DataFrame
        """
        logger.info(f"開始獲取 {ticker} 歷史數據... (週期: {period}, 間隔: {interval})")
        
        # 方案0: 最高優先級 - IBKR（如果已連接）
        if self.ibkr_client and self.ibkr_client.is_connected():
            try:
                logger.info("  使用 IBKR API (最高優先級)...")
                hist = self.ibkr_client.get_historical_data(ticker, period=period, interval=interval)
                
                if hist is not None and not hist.empty:
                    logger.info(f"* 成功獲取 {ticker} 的 {len(hist)} 條歷史記錄 (IBKR)")
                    self._record_fallback('historical_data', 'IBKR')
                    return hist
                else:
                    logger.warning("! IBKR 返回空數據，降級到 Alpha Vantage")
                    self._record_fallback_failure('historical_data', 'IBKR', '返回空數據')
            except Exception as e:
                logger.warning(f"! IBKR 獲取失敗: {e}，降級到 Alpha Vantage")
                self._record_api_failure('IBKR', f"get_historical_data: {e}")
                self._record_fallback_failure('historical_data', 'IBKR', str(e))
        
        # 方案0.5: yfinance（第二優先級 - 使用 curl_cffi，更不容易被限流）
        # 2025-12-07: 將 yfinance 提升到 Yahoo Finance V2 之前，因為 yfinance 0.2.66 有更好的 429 處理
        try:
            logger.info(f"  使用 yfinance 獲取歷史數據...")
            stock = yf.Ticker(ticker)
            hist = stock.history(period=period, interval=interval)
            
            if hist is not None and not hist.empty:
                logger.info(f"* 成功獲取 {ticker} 的 {len(hist)} 條歷史記錄 (yfinance)")
                self._record_fallback('historical_data', 'yfinance')
                return hist
            else:
                logger.warning(f"! yfinance 未獲得 {ticker} 的歷史數據，降級到 Yahoo Finance V2")
                self._record_fallback_failure('historical_data', 'yfinance', '未獲得數據')
        except Exception as e:
            logger.warning(f"! yfinance 獲取失敗: {e}，降級到 Yahoo Finance V2")
            self._record_api_failure('yfinance', f"get_historical_data: {e}")
            self._record_fallback_failure('historical_data', 'yfinance', str(e))
        
        # 方案0.6: Yahoo Finance V2（第三優先級 - 備用）
        if self.yahoo_v2_client:
            try:
                logger.info(f"  使用 Yahoo Finance V2 獲取歷史數據...")
                
                response = self.yahoo_v2_client.get_historical_data(ticker, period=period, interval=interval)
                
                if response and 'chart' in response:
                    result = response['chart'].get('result', [])
                    if result and len(result) > 0:
                        data = result[0]
                        timestamps = data.get('timestamp', [])
                        indicators = data.get('indicators', {})
                        quote = indicators.get('quote', [{}])[0]
                        
                        if timestamps and quote:
                            hist = pd.DataFrame({
                                'Open': quote.get('open', []),
                                'High': quote.get('high', []),
                                'Low': quote.get('low', []),
                                'Close': quote.get('close', []),
                                'Volume': quote.get('volume', [])
                            }, index=pd.to_datetime(timestamps, unit='s'))
                            
                            # 移除 NaN 行
                            hist = hist.dropna()
                            
                            if not hist.empty:
                                logger.info(f"* 成功獲取 {ticker} 的 {len(hist)} 條歷史記錄 (Yahoo Finance V2)")
                                self._record_fallback('historical_data', 'Yahoo Finance V2')
                                return hist
                
                logger.warning(f"! Yahoo Finance V2 未獲得 {ticker} 的歷史數據，降級到 Alpha Vantage")
                self._record_fallback_failure('historical_data', 'Yahoo Finance V2', '未獲得數據')
                    
            except Exception as e:
                logger.warning(f"! Yahoo Finance V2 獲取失敗: {e}，降級到 Alpha Vantage")
                self._record_api_failure('Yahoo Finance V2', f"get_historical_data: {e}")
                self._record_fallback_failure('historical_data', 'Yahoo Finance V2', str(e))
        
        # 方案0.7: Alpha Vantage（第四優先級）
        if hasattr(self, 'alpha_vantage_client') and self.alpha_vantage_client:
            try:
                logger.info(f"  使用 Alpha Vantage 獲取歷史數據...")
                
                # 根據 period 決定 outputsize
                outputsize = 'full' if period in ['1y', '2y', '5y', 'max'] else 'compact'
                
                hist = self.alpha_vantage_client.get_daily_prices(ticker, outputsize=outputsize)
                
                if hist is not None and not hist.empty:
                    logger.info(f"* 成功獲取 {ticker} 的 {len(hist)} 條歷史記錄 (Alpha Vantage)")
                    self._record_fallback('historical_data', 'Alpha Vantage')
                    return hist
                else:
                    logger.warning(f"! Alpha Vantage 未獲得 {ticker} 的歷史數據，降級到 yfinance")
                    self._record_fallback_failure('historical_data', 'Alpha Vantage', '未獲得數據')
                    
            except Exception as e:
                logger.warning(f"! Alpha Vantage 獲取失敗: {e}，降級到 yfinance")
                self._record_api_failure('Alpha Vantage', f"get_historical_data: {e}")
                self._record_fallback_failure('historical_data', 'Alpha Vantage', str(e))
        
        # 方案1: yfinance 已在上面嘗試過，這裡跳過
        # 2025-12-07: yfinance 已提升到第二優先級，不需要在這裡重複嘗試
        logger.info("  yfinance 已在上面嘗試過，降級到 Massive API...")
        
        # 方案2: 降級到 Massive API
        if hasattr(self, 'massive_api_client') and self.massive_api_client:
            try:
                logger.info(f"  使用 Massive API 獲取歷史數據...")
                
                # 根據 period 計算天數
                period_days = {
                    '1d': 1, '5d': 5, '1mo': 30, '3mo': 90, 
                    '6mo': 180, '1y': 365, '2y': 730, '5y': 1825
                }
                days = period_days.get(period, 100)
                
                hist = self.massive_api_client.get_daily_prices(ticker, days=days)
                
                if hist is not None and not hist.empty:
                    logger.info(f"* 成功獲取 {ticker} 的 {len(hist)} 條歷史記錄 (Massive API)")
                    self._record_fallback('historical_data', 'Massive API')
                    return hist
                else:
                    logger.warning(f"! Massive API 未獲得 {ticker} 的歷史數據，降級到 RapidAPI")
                    self._record_fallback_failure('historical_data', 'Massive API', '未獲得數據')
                    
            except Exception as e:
                logger.warning(f"! Massive API 獲取失敗: {e}，降級到 RapidAPI")
                self._record_api_failure('Massive API', f"get_historical_data: {e}")
                self._record_fallback_failure('historical_data', 'Massive API', str(e))
        
        # 方案3: 降級到 RapidAPI（最後備用）
        if hasattr(self, 'rapidapi_client') and self.rapidapi_client:
            try:
                logger.info(f"  使用 RapidAPI 獲取歷史數據...")
                
                response = self.rapidapi_client.get_historical_data(ticker, period=period)
                
                if response and response.get('body'):
                    body = response['body']
                    
                    # 解析 RapidAPI 歷史數據
                    if isinstance(body, list) and len(body) > 0:
                        hist = pd.DataFrame(body)
                        
                        # 標準化列名
                        column_mapping = {
                            'date': 'Date',
                            'open': 'Open',
                            'high': 'High',
                            'low': 'Low',
                            'close': 'Close',
                            'volume': 'Volume'
                        }
                        
                        for old_name, new_name in column_mapping.items():
                            if old_name in hist.columns:
                                hist.rename(columns={old_name: new_name}, inplace=True)
                        
                        # 設置日期索引
                        if 'Date' in hist.columns:
                            hist['Date'] = pd.to_datetime(hist['Date'])
                            hist.set_index('Date', inplace=True)
                        
                        if not hist.empty:
                            logger.info(f"* 成功獲取 {ticker} 的 {len(hist)} 條歷史記錄 (RapidAPI)")
                            self._record_fallback('historical_data', 'RapidAPI')
                            return hist
                
                logger.warning(f"! RapidAPI 未獲得 {ticker} 的歷史數據")
                self._record_fallback_failure('historical_data', 'RapidAPI', '未獲得數據')
                    
            except Exception as e:
                logger.warning(f"! RapidAPI 獲取失敗: {e}")
                self._record_api_failure('RapidAPI', f"get_historical_data: {e}")
                self._record_fallback_failure('historical_data', 'RapidAPI', str(e))
        
        # 所有數據源都失敗，輸出完整嘗試路徑
        self._log_attempt_path('historical_data')
        logger.error(f"x 所有數據源都無法獲取 {ticker} 歷史數據")
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
        
        降級順序: IBKR → Yahoo Finance V2 → yfinance
        
        注意: Finnhub 不提供期權數據，所以不在降級順序中
        
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
        # 注意: IBKR 只返回合約基本信息，不包含市場數據（IV, bid, ask）
        # 因此即使 IBKR 連接成功，我們仍需要從 Yahoo Finance 獲取市場數據
        if self.ibkr_client and self.ibkr_client.is_connected():
            try:
                logger.info("  使用 IBKR...")
                chain_data = self.ibkr_client.get_option_chain(ticker, expiration)
                
                if chain_data:
                    # 轉換為 DataFrame
                    calls_df = pd.DataFrame(chain_data['calls'])
                    puts_df = pd.DataFrame(chain_data['puts'])
                    
                    # 檢查是否真的有數據（不只是空 DataFrame）
                    if len(calls_df) > 0 or len(puts_df) > 0:
                        # 檢查是否有 IV 數據（IBKR 通常不返回 IV，需要額外訂閱）
                        has_iv = 'impliedVolatility' in calls_df.columns and calls_df['impliedVolatility'].notna().any()
                        
                        if has_iv:
                            logger.info(f"* 成功獲取 {ticker} {expiration} 期權鏈 (IBKR - 含IV)")
                            logger.info(f"  Call期權: {len(calls_df)} 個")
                            logger.info(f"  Put期權: {len(puts_df)} 個")
                            self._record_fallback('option_chain', 'ibkr')
                            
                            return {
                                'calls': calls_df,
                                'puts': puts_df,
                                'expiration': expiration,
                                'data_source': 'ibkr'
                            }
                        else:
                            # IBKR 返回了合約但沒有 IV，需要降級到 Yahoo Finance 獲取市場數據
                            logger.info(f"  IBKR 返回 {len(calls_df)} calls, {len(puts_df)} puts (僅合約信息，無IV)")
                            logger.info(f"  降級到 Yahoo Finance 獲取市場數據...")
                            self._record_fallback_failure('option_chain', 'IBKR', '無IV數據，需要市場數據訂閱')
                    else:
                        logger.warning(f"! IBKR 返回 0 個期權合約，降級到 Yahoo Finance")
                        self._record_fallback_failure('option_chain', 'IBKR', '返回0個合約')
                else:
                    logger.warning("! IBKR 返回空期權數據，降級到 Yahoo Finance")
                    self._record_fallback_failure('option_chain', 'IBKR', '返回空數據')
            except Exception as e:
                logger.warning(f"! IBKR 獲取期權鏈失敗: {e}，降級到 Yahoo Finance")
                self._record_api_failure('ibkr', f"get_option_chain: {str(e)}")
                self._record_fallback_failure('option_chain', 'IBKR', str(e))
        
        # 方案2: 降級到 Yahoo Finance V2（簡化版，帶 User-Agent）
        if self.yahoo_v2_client:
            try:
                logger.info("  使用 Yahoo Finance API...")
                
                # 直接將用戶指定的到期日轉換為 timestamp
                # 跳過 get_available_expirations 調用以減少請求次數，避免 429 錯誤
                from datetime import datetime
                import calendar
                try:
                    exp_date = datetime.strptime(expiration, '%Y-%m-%d')
                    # 使用 UTC 時間戳
                    exp_timestamp = calendar.timegm(exp_date.timetuple())
                except:
                    exp_timestamp = None
                
                actual_expiration = expiration
                actual_timestamp = exp_timestamp
                
                # 直接使用用戶指定的到期日，如果不存在 Yahoo Finance 會返回最近的
                response = self.yahoo_v2_client.get_option_chain(ticker, actual_timestamp if actual_timestamp else actual_expiration)
                chain_data = YahooDataParser.parse_option_chain(response)
                
                if chain_data and chain_data.get('calls') and chain_data.get('puts'):
                    # 轉換為 DataFrame
                    calls_df = pd.DataFrame(chain_data['calls'])
                    puts_df = pd.DataFrame(chain_data['puts'])
                    
                    # 使用 IVNormalizer 標準化 IV（避免重複轉換）
                    if 'impliedVolatility' in calls_df.columns:
                        # 記錄原始值用於調試
                        if not calls_df.empty:
                            sample_raw = calls_df['impliedVolatility'].iloc[0]
                            logger.debug(f"  Yahoo Finance Call IV 原始值樣本: {sample_raw}")
                        
                        # 使用 IVNormalizer 進行標準化
                        calls_df['impliedVolatility'] = calls_df['impliedVolatility'].apply(
                            lambda x: IVNormalizer.normalize_iv(x, 'yahoo_finance')['normalized_iv'] if pd.notna(x) else None
                        )
                        
                        if not calls_df.empty:
                            sample_norm = calls_df['impliedVolatility'].iloc[0]
                            logger.debug(f"  Yahoo Finance Call IV 標準化後樣本: {sample_norm}%")
                    
                    if 'impliedVolatility' in puts_df.columns:
                        puts_df['impliedVolatility'] = puts_df['impliedVolatility'].apply(
                            lambda x: IVNormalizer.normalize_iv(x, 'yahoo_finance')['normalized_iv'] if pd.notna(x) else None
                        )
                    
                    # 檢查數據有效性：lastPrice 不能全為 0
                    has_valid_call_price = False
                    has_valid_put_price = False
                    
                    if not calls_df.empty and 'lastPrice' in calls_df.columns:
                        # 檢查 ATM 附近的期權是否有有效價格
                        has_valid_call_price = (calls_df['lastPrice'] > 0).sum() > len(calls_df) * 0.3
                    
                    if not puts_df.empty and 'lastPrice' in puts_df.columns:
                        has_valid_put_price = (puts_df['lastPrice'] > 0).sum() > len(puts_df) * 0.3
                    
                    if has_valid_call_price or has_valid_put_price:
                        logger.info(f"* 成功獲取 {ticker} {actual_expiration} 期權鏈 (Yahoo Finance)")
                        logger.info(f"  Call期權: {len(calls_df)} 個")
                        logger.info(f"  Put期權: {len(puts_df)} 個")
                        self._record_fallback('option_chain', 'Yahoo Finance')
                        
                        return {
                            'calls': calls_df,
                            'puts': puts_df,
                            'expiration': actual_expiration,
                            'data_source': 'yahoo_finance'
                        }
                    else:
                        # 數據不完整，嘗試其他數據源
                        logger.warning("! Yahoo Finance 返回的期權數據 lastPrice 大部分為 0，嘗試其他數據源")
                        self._record_fallback_failure('option_chain', 'Yahoo Finance', 'lastPrice 大部分為 0')
                else:
                    logger.warning("! Yahoo Finance 返回空期權數據，降級到 yfinance")
                    self._record_fallback_failure('option_chain', 'Yahoo Finance', '返回空數據')
            except Exception as e:
                logger.warning(f"! Yahoo Finance 獲取期權鏈失敗: {e}，降級到 yfinance")
                self._record_api_failure('Yahoo Finance', f"get_option_chain: {str(e)}")
                self._record_fallback_failure('option_chain', 'Yahoo Finance', str(e))
        
        # 方案3: 降級到 yfinance
        try:
            self._rate_limit_delay()
            logger.info("  使用 yfinance...")
            stock = yf.Ticker(ticker)
            option_chain = stock.option_chain(expiration)
            
            calls = option_chain.calls.copy()
            puts = option_chain.puts.copy()
            
            # 使用 IVNormalizer 標準化 IV（避免重複轉換）
            if 'impliedVolatility' in calls.columns and not calls.empty:
                sample_iv_before = calls['impliedVolatility'].iloc[0]
                logger.debug(f"  yfinance Call IV 原始值樣本: {sample_iv_before}")
                
                calls['impliedVolatility'] = calls['impliedVolatility'].apply(
                    lambda x: IVNormalizer.normalize_iv(x, 'yfinance')['normalized_iv'] if pd.notna(x) else None
                )
                
                sample_iv_after = calls['impliedVolatility'].iloc[0]
                logger.debug(f"  yfinance Call IV 標準化後樣本: {sample_iv_after}%")
            
            if 'impliedVolatility' in puts.columns:
                puts['impliedVolatility'] = puts['impliedVolatility'].apply(
                    lambda x: IVNormalizer.normalize_iv(x, 'yfinance')['normalized_iv'] if pd.notna(x) else None
                )
            
            # 檢查數據有效性：lastPrice 不能全為 0
            has_valid_call_price = False
            has_valid_put_price = False
            
            if not calls.empty and 'lastPrice' in calls.columns:
                has_valid_call_price = (calls['lastPrice'] > 0).sum() > len(calls) * 0.3
            
            if not puts.empty and 'lastPrice' in puts.columns:
                has_valid_put_price = (puts['lastPrice'] > 0).sum() > len(puts) * 0.3
            
            if has_valid_call_price or has_valid_put_price:
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
            else:
                # 數據不完整，嘗試 RapidAPI
                logger.warning("! yfinance 返回的期權數據 lastPrice 大部分為 0，嘗試 RapidAPI")
                self._record_fallback_failure('option_chain', 'yfinance', 'lastPrice 大部分為 0')
            
        except Exception as e:
            logger.error(f"x yfinance 獲取期權鏈失敗: {e}")
            self._record_api_failure('yfinance', f"get_option_chain: {str(e)}")
            self._record_fallback_failure('option_chain', 'yfinance', str(e))
        
        # 方案4: 嘗試 RapidAPI 增強版（如果啟用）
        if hasattr(self, 'rapidapi_client') and self.rapidapi_client:
            try:
                logger.info("  使用 RapidAPI (增強版)...")
                
                # 使用增強版方法獲取更完整的期權數據
                result = self.rapidapi_client.get_option_chain_enhanced(ticker, expiration)
                
                if result:
                    calls_df = result.get('calls', pd.DataFrame())
                    puts_df = result.get('puts', pd.DataFrame())
                    
                    # 驗證數據有效性
                    has_valid_data = False
                    if not calls_df.empty and 'lastPrice' in calls_df.columns:
                        has_valid_data = (calls_df['lastPrice'] > 0).any()
                    if not has_valid_data and not puts_df.empty and 'lastPrice' in puts_df.columns:
                        has_valid_data = (puts_df['lastPrice'] > 0).any()
                    
                    if has_valid_data:
                        # 使用 IVNormalizer 標準化 IV（確保百分比格式）
                        if 'impliedVolatility' in calls_df.columns:
                            calls_df['impliedVolatility'] = calls_df['impliedVolatility'].apply(
                                lambda x: IVNormalizer.normalize_iv(x, 'rapidapi')['normalized_iv'] if pd.notna(x) else None
                            )
                        if 'impliedVolatility' in puts_df.columns:
                            puts_df['impliedVolatility'] = puts_df['impliedVolatility'].apply(
                                lambda x: IVNormalizer.normalize_iv(x, 'rapidapi')['normalized_iv'] if pd.notna(x) else None
                            )
                        
                        logger.info(f"* 成功獲取 {ticker} {expiration} 期權鏈 (RapidAPI 增強版)")
                        logger.info(f"  Call期權: {len(calls_df)} 個")
                        logger.info(f"  Put期權: {len(puts_df)} 個")
                        logger.info(f"  數據來源: {result.get('data_source', 'RapidAPI')}")
                        self._record_fallback('option_chain', 'RapidAPI')
                        
                        return {
                            'calls': calls_df,
                            'puts': puts_df,
                            'expiration': result.get('expiration', expiration),
                            'data_source': result.get('data_source', 'rapidapi')
                        }
                    else:
                        logger.warning("! RapidAPI 返回的期權數據 lastPrice 全為 0")
                        self._record_fallback_failure('option_chain', 'RapidAPI', 'lastPrice 全為 0')
                else:
                    logger.warning("! RapidAPI 返回空期權數據")
                    self._record_fallback_failure('option_chain', 'RapidAPI', '返回空數據')
            except Exception as e:
                logger.error(f"x RapidAPI 獲取期權鏈失敗: {e}")
                self._record_api_failure('RapidAPI', f"get_option_chain: {str(e)}")
                self._record_fallback_failure('option_chain', 'RapidAPI', str(e))
        
        # 方案5: 最後降級 - 返回空數據結構（避免系統崩潰）
        # 輸出完整嘗試路徑
        self._log_attempt_path('option_chain')
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
                    self._record_fallback('option_greeks', 'IBKR')
                    return greeks
                else:
                    logger.warning("! IBKR 返回空 Greeks 數據，降級到自主計算")
                    self._record_fallback_failure('option_greeks', 'IBKR', '返回空數據')
            except Exception as e:
                logger.warning(f"! IBKR 獲取 Greeks 失敗: {e}，降級到自主計算")
                self._record_api_failure('ibkr', f"get_option_greeks: {str(e)}")
                self._record_fallback_failure('option_greeks', 'IBKR', str(e))
        
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
                    self._record_fallback_failure('option_greeks', 'self_calculated', '參數不足')
                    
            except Exception as e:
                logger.error(f"x 自主計算 Greeks 失敗: {e}")
                self._record_api_failure('self_calculated', f"get_option_greeks: {str(e)}")
                self._record_fallback_failure('option_greeks', 'self_calculated', str(e))
        
        # 方案4: 最後降級 - 返回默認值（避免系統崩潰）
        # 輸出完整嘗試路徑
        self._log_attempt_path('option_greeks')
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
            'current_price': float,
            'strike_price_diff': float,
            'strike_price_diff_percent': float
        }
        
        Requirements: 1.2 - ATM 期權選擇邏輯增強日誌
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
            logger.debug(f"  可用行使價數量: {len(strikes)}")
            logger.debug(f"  行使價範圍: ${min(strikes):.2f} - ${max(strikes):.2f}")
            
            atm_strike = min(strikes, key=lambda x: abs(x - current_price))
            
            # 計算價差
            strike_diff = abs(atm_strike - current_price)
            strike_diff_percent = (strike_diff / current_price * 100) if current_price > 0 else 0
            
            call_atm = calls[calls['strike'] == atm_strike].iloc[0]
            put_atm = puts[puts['strike'] == atm_strike].iloc[0]
            
            # 增強日誌：記錄選擇的行使價和對應的 IV
            logger.info(f"* {ticker} ATM期權選擇結果:")
            logger.info(f"  當前股價: ${current_price:.2f}")
            logger.info(f"  選擇行使價: ${atm_strike:.2f}")
            logger.info(f"  價差: ${strike_diff:.2f} ({strike_diff_percent:.2f}%)")
            
            # 記錄 IV 值（已經過 IVNormalizer 標準化）
            call_iv = call_atm.get('impliedVolatility')
            put_iv = put_atm.get('impliedVolatility')
            
            if call_iv is not None:
                logger.info(f"  ATM Call IV: {call_iv:.2f}%")
            else:
                logger.warning(f"  ATM Call IV: N/A")
            
            if put_iv is not None:
                logger.info(f"  ATM Put IV: {put_iv:.2f}%")
            else:
                logger.warning(f"  ATM Put IV: N/A")
            
            # 如果 Call 和 Put IV 差異過大，記錄警告
            if call_iv is not None and put_iv is not None:
                iv_diff = abs(call_iv - put_iv)
                if iv_diff > 5:  # 差異超過 5%
                    logger.warning(f"  ! Call/Put IV 差異較大: {iv_diff:.2f}%")
            
            return {
                'call_atm': call_atm,
                'put_atm': put_atm,
                'atm_strike': atm_strike,
                'current_price': current_price,
                'strike_price_diff': strike_diff,
                'strike_price_diff_percent': strike_diff_percent
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
                self._record_fallback_failure('risk_free_rate', 'FRED', '客戶端未初始化')
                self._log_attempt_path('risk_free_rate')
                return None
            
            logger.info("開始獲取無風險利率...")
            dgs10 = self.fred_client.get_series('DGS10')
            
            if dgs10 is None or dgs10.empty:
                logger.warning("! 無法獲取10年期國債收益率")
                self._record_fallback_failure('risk_free_rate', 'FRED', '無法獲取數據')
                self._log_attempt_path('risk_free_rate')
                return None
            
            rate = dgs10.iloc[-1]
            logger.info(f"* 10年期國債收益率: {rate:.2f}%")
            self._record_fallback('risk_free_rate', 'FRED')
            
            return rate
            
        except Exception as e:
            logger.error(f"x 獲取無風險利率失敗: {e}")
            self._record_fallback_failure('risk_free_rate', 'FRED', str(e))
            self._log_attempt_path('risk_free_rate')
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
                    self._record_fallback('vix', 'Yahoo Finance')
                    return vix_value
                else:
                    logger.warning("! Yahoo Finance VIX 數據為空，降級到 FRED")
                    self._record_fallback_failure('vix', 'Yahoo Finance', '數據為空')
            except Exception as e:
                logger.warning(f"! Yahoo Finance 獲取 VIX 失敗: {e}，降級到 FRED")
                self._record_fallback_failure('vix', 'Yahoo Finance', str(e))
            
            # 降級：使用 FRED 獲取 VIX（可能有延遲）
            if self.fred_client:
                vix = self.fred_client.get_series('VIXCLS')
                
                if vix is not None and not vix.empty:
                    vix_value = vix.iloc[-1]
                    logger.info(f"* VIX指數 (FRED 收盤價): {vix_value:.2f}")
                    logger.warning("  ! 注意：FRED VIX 數據可能有1天延遲")
                    self._record_fallback('vix', 'FRED')
                    return vix_value
                else:
                    logger.warning("! FRED 無法獲取VIX")
                    self._record_fallback_failure('vix', 'FRED', '無法獲取數據')
                    self._log_attempt_path('vix')
                    return None
            else:
                logger.warning("! FRED客户端未初始化，無法獲取VIX")
                self._log_attempt_path('vix')
                return None
            
        except Exception as e:
            logger.error(f"x 獲取VIX失敗: {e}")
            self._log_attempt_path('vix')
            return None
    
    # ==================== 歷史IV數據 ====================
    
    def get_historical_iv(self, ticker: str, days: int = 252) -> Optional[pd.Series]:
        """
        獲取歷史隱含波動率數據（用於計算 IV Rank 和 IV Percentile）
        
        由於大多數免費 API 不提供歷史 IV 數據，此方法使用以下策略：
        1. 嘗試從期權數據計算當前 IV
        2. 使用歷史股價波動率作為 IV 的代理（HV 作為 IV 的近似）
        
        參數:
            ticker: 股票代碼
            days: 需要的歷史天數（默認 252 = 1年交易日）
        
        返回:
            pd.Series: 歷史 IV 數據（如果可用），否則返回 None
        
        注意:
            - 真正的歷史 IV 數據需要付費數據源（如 CBOE, IVolatility）
            - 此方法使用 HV 作為 IV 的近似，這在大多數情況下是合理的
            - 對於更精確的 IV Rank/Percentile，建議接入專業數據源
        """
        try:
            logger.info(f"開始獲取 {ticker} 的歷史IV數據（{days}天）...")
            
            # 策略：使用歷史波動率作為 IV 的代理
            # 原因：免費 API 通常不提供歷史 IV，但 HV 和 IV 高度相關
            
            # 獲取更長期的歷史數據（需要額外的數據來計算滾動 HV）
            extended_days = days + 30  # 額外 30 天用於計算滾動窗口
            
            # 使用 yfinance 獲取歷史數據
            try:
                stock = yf.Ticker(ticker)
                # 計算需要的期間（考慮週末和假期，大約需要 1.5 倍的日曆天數）
                calendar_days = int(extended_days * 1.5)
                hist = stock.history(period=f"{calendar_days}d")
                
                if hist.empty or len(hist) < 30:
                    logger.warning(f"! {ticker} 歷史數據不足，無法計算歷史 IV")
                    return None
                
                # 計算滾動 30 天歷史波動率作為 IV 的代理
                log_returns = np.log(hist['Close'] / hist['Close'].shift(1))
                rolling_hv = log_returns.rolling(window=30).std() * np.sqrt(252)
                
                # 移除 NaN 值
                rolling_hv = rolling_hv.dropna()
                
                if len(rolling_hv) < days:
                    logger.warning(f"! {ticker} 滾動 HV 數據不足: {len(rolling_hv)} < {days}")
                    # 如果數據不足 252 天，但有足夠的數據（至少 60 天），仍然返回
                    if len(rolling_hv) >= 60:
                        logger.info(f"  使用可用的 {len(rolling_hv)} 天數據")
                        return rolling_hv
                    return None
                
                # 取最近 days 天的數據
                historical_iv = rolling_hv.iloc[-days:]
                
                logger.info(f"* 成功獲取 {ticker} 歷史 IV 代理數據")
                logger.info(f"  數據點數: {len(historical_iv)}")
                logger.info(f"  IV 範圍: {historical_iv.min()*100:.2f}% ~ {historical_iv.max()*100:.2f}%")
                logger.info(f"  當前 IV (HV代理): {historical_iv.iloc[-1]*100:.2f}%")
                logger.info(f"  注意: 使用 30 天滾動 HV 作為 IV 的代理")
                
                return historical_iv
                
            except Exception as e:
                logger.warning(f"! yfinance 獲取歷史數據失敗: {e}")
                return None
            
        except Exception as e:
            logger.error(f"x 獲取歷史 IV 失敗: {e}")
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
                self._record_fallback_failure('earnings_calendar', 'Finnhub', '無近期業績安排')
                
            except Exception as e:
                logger.warning(f"! Finnhub 獲取業績日期失敗: {e}，降級到 yfinance")
                self._record_api_failure('Finnhub', f"get_earnings_calendar: {e}")
                self._record_fallback_failure('earnings_calendar', 'Finnhub', str(e))
        else:
            logger.info("  Finnhub 客戶端未初始化，跳過")
            self._record_fallback_failure('earnings_calendar', 'Finnhub', '客戶端未初始化')
        
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
            self._record_fallback_failure('earnings_calendar', 'yfinance', '無業績日期')
            
        except Exception as e:
            logger.warning(f"! yfinance 獲取業績日期失敗: {e}，嘗試歷史推測")
            self._record_api_failure('yfinance', f"get_earnings_calendar: {e}")
            self._record_fallback_failure('earnings_calendar', 'yfinance', str(e))
        
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
            self._record_fallback_failure('earnings_calendar', 'estimated', str(e))
        
        # 所有方案都失敗，輸出完整嘗試路徑
        self._log_attempt_path('earnings_calendar')
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
                'insider_own', 'inst_own', 'short_float', 'avg_volume', 'eps_next_y'
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
                self._record_fallback('dividend_calendar', 'yfinance')
                return result
            else:
                logger.warning(f"! yfinance 無 {ticker} 除息日期，嘗試 Finnhub")
                self._record_fallback_failure('dividend_calendar', 'yfinance', '無除息日期')
            
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
                        self._record_fallback('dividend_calendar', 'Finnhub')
                        return result
                    else:
                        logger.warning(f"! Finnhub 無 {ticker} 派息數據")
                        self._record_fallback_failure('dividend_calendar', 'Finnhub', '無派息數據')
                except Exception as e:
                    logger.warning(f"  Finnhub派息數據獲取失敗: {e}")
                    self._record_fallback_failure('dividend_calendar', 'Finnhub', str(e))
            else:
                self._record_fallback_failure('dividend_calendar', 'Finnhub', '客戶端未初始化')
            
            # 所有方案都失敗，輸出完整嘗試路徑
            self._log_attempt_path('dividend_calendar')
            logger.warning(f"! {ticker} 無派息信息")
            return None
            
        except Exception as e:
            logger.error(f"x 獲取 {ticker} 派息信息失敗: {e}")
            self._log_attempt_path('dividend_calendar')
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
            
            # ✅ 補充 Finviz 數據（如果主數據源不是 Finviz）
            if stock_info.get('data_source') != 'Finviz' and hasattr(self, 'finviz_scraper') and self.finviz_scraper:
                logger.info("  補充 Finviz 數據...")
                try:
                    finviz_data = self.finviz_scraper.get_stock_fundamentals(ticker)
                    if finviz_data:
                        # 補充 Finviz 特有的字段
                        finviz_fields_to_add = [
                            'insider_own', 'inst_own', 'short_float', 'avg_volume',
                            'peg', 'roe', 'roa', 'profit_margin', 'operating_margin',
                            'debt_eq', 'atr', 'rsi', 'beta', 'target_price',
                            'forward_pe', 'sector', 'industry', 'company_name'
                        ]
                        for field in finviz_fields_to_add:
                            if finviz_data.get(field) is not None and stock_info.get(field) is None:
                                stock_info[field] = finviz_data[field]
                        # 特殊處理：peg -> peg_ratio
                        if finviz_data.get('peg') is not None and stock_info.get('peg_ratio') is None:
                            stock_info['peg_ratio'] = finviz_data['peg']
                        logger.info(f"  * Finviz 數據補充完成")
                except Exception as e:
                    logger.warning(f"  ! Finviz 數據補充失敗: {e}")
            
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
            
            # 獲取 IV 值（已在 get_option_chain 中通過 IVNormalizer 標準化）
            raw_iv = call_atm['impliedVolatility']
            
            # 使用 IVNormalizer 驗證 IV 值（不再重複轉換）
            iv_result = IVNormalizer.normalize_iv(raw_iv, source='atm_option')
            
            if iv_result['is_valid']:
                iv = iv_result['normalized_iv']
                logger.info(f"  * ATM Call IV: {iv:.2f}% (行使價: ${atm_strike:.2f})")
                
                # 檢查是否為異常值
                if iv_result['is_abnormal']:
                    logger.warning(f"  ! IV 異常警告: {iv_result['abnormal_reason']}")
                    # 嘗試使用 Put IV 作為備選
                    put_iv_raw = put_atm['impliedVolatility']
                    put_iv_result = IVNormalizer.normalize_iv(put_iv_raw, source='atm_put_option')
                    if put_iv_result['is_valid'] and not put_iv_result['is_abnormal']:
                        logger.info(f"  * 使用 Put IV 作為備選: {put_iv_result['normalized_iv']:.2f}%")
                        # 使用 Call 和 Put IV 的平均值
                        iv = (iv + put_iv_result['normalized_iv']) / 2
                        logger.info(f"  * 使用 Call/Put IV 平均值: {iv:.2f}%")
            else:
                logger.error(f"  x IV 值無效: {iv_result['abnormal_reason']}")
                # 使用默認 IV
                iv = 30.0
                logger.warning(f"  ! 使用默認 IV: {iv}%")
            
            # 5. 基本面數據
            logger.info("\n[步驟5/6] 獲取基本面數據...")
            eps = self.get_eps(ticker)
            dividends = self.get_dividends(ticker)
            
            # 5.1 歷史數據 (用於 Module 18 HV計算 + IV Rank/Percentile)
            logger.info("\n[步驟5.1/6] 獲取歷史數據 (用於HV計算和IV Rank)...")
            # 獲取足夠的歷史數據以計算 IV Rank/Percentile (需要 252+ 天數據)
            # 使用 1y (1年) 以確保有足夠的數據
            historical_data = self.get_historical_data(ticker, period='1y', interval='1d')
            if historical_data is not None and not historical_data.empty:
                logger.info(f"  * 獲取了 {len(historical_data)} 條歷史記錄")
                if len(historical_data) >= 252:
                    logger.info(f"  * 數據足夠計算 IV Rank/Percentile (252天基準)")
                else:
                    logger.warning(f"  ! 數據不足252天，IV Rank/Percentile 可能不準確")
            else:
                logger.warning("  ! 無法獲取歷史數據，HV 和 IV Rank 計算將跳過")

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
                
                # 股票數據（使用 .get() 確保有默認值）
                'current_price': current_price,
                'stock_open': stock_info.get('open', 0),
                'stock_high': stock_info.get('high', 0),
                'stock_low': stock_info.get('low', 0),
                'volume': stock_info.get('volume', 0),
                'market_cap': stock_info.get('market_cap', 0),
                'pe_ratio': stock_info.get('pe_ratio', 0),
                'eps': eps,
                'company_name': stock_info.get('company_name', ticker),
                'sector': stock_info.get('sector', 'Unknown'),
                'industry': stock_info.get('industry', 'Unknown'),
                
                # 派息數據
                'annual_dividend': dividends.get('annual_dividend', 0) if dividends else 0,
                'dividend_rate': stock_info.get('dividend_rate', 0),
                
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
                # 只記錄一次 Finviz 數據不完整的故障，而不是每個字段都記錄
                # 這樣可以避免故障計數膨脹
                if len(missing_finviz_fields) == len(finviz_fields):
                    # 所有字段都缺失，說明 Finviz 連接可能失敗
                    self._record_api_failure('Finviz', f"連接失敗: 所有 {len(finviz_fields)} 個字段都無法獲取")
                elif len(missing_finviz_fields) > len(finviz_fields) * 0.5:
                    # 超過一半字段缺失，記錄一次警告
                    self._record_api_failure('Finviz', f"數據不完整: {len(missing_finviz_fields)}/{len(finviz_fields)} 字段缺失")
            
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


    # ==================== 技術指標 (Alpha Vantage 整合) ====================
    
    def get_technical_indicators(self, ticker: str, indicators: list = None) -> Dict[str, Any]:
        """
        獲取技術指標（支持多數據源降級）
        
        降級順序: Finviz → Alpha Vantage → 自主計算
        
        參數:
            ticker: 股票代碼
            indicators: 指標列表 ['atr', 'rsi', 'sma', 'ema']，默認 ['atr', 'rsi']
        
        返回:
            dict: 包含請求的技術指標
        """
        if indicators is None:
            indicators = ['atr', 'rsi']
        
        logger.info(f"開始獲取 {ticker} 技術指標: {indicators}")
        
        results = {
            'ticker': ticker,
            'timestamp': datetime.now().isoformat()
        }
        
        for indicator in indicators:
            indicator_lower = indicator.lower()
            
            # 方案1: 嘗試從 Finviz 獲取（如果已有數據）
            if self.finviz_scraper:
                try:
                    finviz_data = self.finviz_scraper.get_stock_fundamentals(ticker)
                    if finviz_data:
                        if indicator_lower == 'atr' and finviz_data.get('atr'):
                            results['atr'] = finviz_data['atr']
                            results['atr_source'] = 'Finviz'
                            self._record_fallback(f'technical_{indicator_lower}', 'Finviz')
                            logger.info(f"  * ATR (Finviz): ${results['atr']:.2f}")
                            continue
                        elif indicator_lower == 'rsi' and finviz_data.get('rsi'):
                            results['rsi'] = finviz_data['rsi']
                            results['rsi_source'] = 'Finviz'
                            self._record_fallback(f'technical_{indicator_lower}', 'Finviz')
                            logger.info(f"  * RSI (Finviz): {results['rsi']:.2f}")
                            continue
                        elif indicator_lower == 'beta' and finviz_data.get('beta'):
                            results['beta'] = finviz_data['beta']
                            results['beta_source'] = 'Finviz'
                            self._record_fallback(f'technical_{indicator_lower}', 'Finviz')
                            logger.info(f"  * Beta (Finviz): {results['beta']:.2f}")
                            continue
                except Exception as e:
                    logger.debug(f"  Finviz 獲取 {indicator} 失敗: {e}")
            
            # 方案2: 降級到 Alpha Vantage
            if hasattr(self, 'alpha_vantage_client') and self.alpha_vantage_client:
                try:
                    if indicator_lower == 'atr':
                        atr_data = self.alpha_vantage_client.get_atr(ticker)
                        if atr_data:
                            results['atr'] = atr_data['atr']
                            results['atr_source'] = 'Alpha Vantage'
                            self._record_fallback(f'technical_{indicator_lower}', 'Alpha Vantage')
                            logger.info(f"  * ATR (Alpha Vantage): ${results['atr']:.2f}")
                            continue
                    
                    elif indicator_lower == 'rsi':
                        rsi_data = self.alpha_vantage_client.get_rsi(ticker)
                        if rsi_data:
                            results['rsi'] = rsi_data['rsi']
                            results['rsi_signal'] = rsi_data.get('signal_cn', '')
                            results['rsi_source'] = 'Alpha Vantage'
                            self._record_fallback(f'technical_{indicator_lower}', 'Alpha Vantage')
                            logger.info(f"  * RSI (Alpha Vantage): {results['rsi']:.2f}")
                            continue
                    
                    elif indicator_lower == 'sma':
                        sma_data = self.alpha_vantage_client.get_sma(ticker)
                        if sma_data:
                            results['sma'] = sma_data['sma']
                            results['sma_source'] = 'Alpha Vantage'
                            self._record_fallback(f'technical_{indicator_lower}', 'Alpha Vantage')
                            logger.info(f"  * SMA (Alpha Vantage): ${results['sma']:.2f}")
                            continue
                    
                    elif indicator_lower == 'ema':
                        ema_data = self.alpha_vantage_client.get_ema(ticker)
                        if ema_data:
                            results['ema'] = ema_data['ema']
                            results['ema_source'] = 'Alpha Vantage'
                            self._record_fallback(f'technical_{indicator_lower}', 'Alpha Vantage')
                            logger.info(f"  * EMA (Alpha Vantage): ${results['ema']:.2f}")
                            continue
                            
                except Exception as e:
                    logger.warning(f"  Alpha Vantage 獲取 {indicator} 失敗: {e}")
                    self._record_api_failure('Alpha Vantage', f"get_{indicator}: {e}")
            
            # 方案3: 自主計算（僅適用於 ATR）
            if indicator_lower == 'atr':
                try:
                    logger.info(f"  嘗試自主計算 ATR...")
                    hist = self.get_historical_data(ticker, period='1mo', interval='1d')
                    if hist is not None and len(hist) >= 14:
                        # 計算 ATR
                        high = hist['High']
                        low = hist['Low']
                        close = hist['Close']
                        
                        tr1 = high - low
                        tr2 = abs(high - close.shift(1))
                        tr3 = abs(low - close.shift(1))
                        
                        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
                        atr = tr.rolling(window=14).mean().iloc[-1]
                        
                        results['atr'] = atr
                        results['atr_source'] = 'Self-Calculated'
                        self._record_fallback(f'technical_{indicator_lower}', 'Self-Calculated')
                        logger.info(f"  * ATR (自主計算): ${atr:.2f}")
                        continue
                except Exception as e:
                    logger.warning(f"  自主計算 ATR 失敗: {e}")
            
            # 如果所有方案都失敗
            logger.warning(f"  ! 無法獲取 {indicator}")
            results[indicator_lower] = None
        
        logger.info(f"* 技術指標獲取完成")
        return results
    
    def get_atr(self, ticker: str) -> Optional[float]:
        """
        獲取 ATR (Average True Range)
        
        降級順序: Finviz → Alpha Vantage → 自主計算
        
        參數:
            ticker: 股票代碼
        
        返回:
            float: ATR 值，失敗返回 None
        """
        result = self.get_technical_indicators(ticker, ['atr'])
        return result.get('atr')
    
    def get_rsi(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        獲取 RSI (Relative Strength Index)
        
        降級順序: Finviz → Alpha Vantage
        
        參數:
            ticker: 股票代碼
        
        返回:
            dict: {'rsi': float, 'signal': str}，失敗返回 None
        """
        result = self.get_technical_indicators(ticker, ['rsi'])
        if result.get('rsi') is not None:
            return {
                'rsi': result['rsi'],
                'signal': result.get('rsi_signal', ''),
                'source': result.get('rsi_source', '')
            }
        return None

    # ==================== Finnhub K線數據 (Module 24 技術方向分析) ====================
    
    def get_finnhub_candles(self, ticker: str, resolution: str = 'D',
                           days: int = 200) -> Optional[pd.DataFrame]:
        """
        從 Finnhub 獲取 K 線數據
        
        參數:
            ticker: 股票代碼
            resolution: 時間框架 ('1', '5', '15', '30', '60', 'D', 'W', 'M')
            days: 回看天數
        
        返回:
            pd.DataFrame: 包含 Open, High, Low, Close, Volume 的 DataFrame
        
        Requirements: 1.1, 2.1
        """
        try:
            logger.info(f"從 Finnhub 獲取 {ticker} K線數據 (resolution={resolution}, days={days})...")
            
            if not self.finnhub_client:
                logger.warning("Finnhub 客戶端未初始化")
                return None
            
            # 計算時間範圍
            to_time = int(datetime.now().timestamp())
            from_time = int((datetime.now() - timedelta(days=days)).timestamp())
            
            # 調用 Finnhub API
            candles = self.finnhub_client.stock_candles(
                ticker.upper(),
                resolution,
                from_time,
                to_time
            )
            
            if candles and candles.get('s') == 'ok':
                df = pd.DataFrame({
                    'Open': candles['o'],
                    'High': candles['h'],
                    'Low': candles['l'],
                    'Close': candles['c'],
                    'Volume': candles['v'],
                    'Timestamp': candles['t']
                })
                
                # 轉換時間戳為日期索引
                df['Date'] = pd.to_datetime(df['Timestamp'], unit='s')
                df.set_index('Date', inplace=True)
                df.drop('Timestamp', axis=1, inplace=True)
                
                logger.info(f"  * 成功獲取 {len(df)} 根 K 線")
                self._record_fallback(f'candles_{resolution}', 'Finnhub')
                return df
            else:
                logger.warning(f"  ! Finnhub 返回無效數據: {candles.get('s', 'unknown')}")
                return None
                
        except Exception as e:
            logger.warning(f"  ! Finnhub K線獲取失敗: {e}")
            self._record_api_failure('Finnhub', f"stock_candles: {e}")
            return None
    
    def get_daily_candles(self, ticker: str, days: int = 200) -> Optional[pd.DataFrame]:
        """
        獲取日線 K 線數據（支持降級）
        
        降級順序: Finnhub → Yahoo Finance
        
        Requirements: 1.1, 1.4
        """
        # 方案1: Finnhub
        df = self.get_finnhub_candles(ticker, 'D', days)
        if df is not None and len(df) >= 50:
            return df
        
        # 方案2: 降級到 Yahoo Finance
        logger.info(f"  降級到 Yahoo Finance 獲取日線數據...")
        try:
            hist = self.get_historical_data(ticker, period=f'{days}d', interval='1d')
            if hist is not None and len(hist) >= 50:
                self._record_fallback('candles_D', 'Yahoo Finance')
                return hist
        except Exception as e:
            logger.warning(f"  ! Yahoo Finance 日線獲取失敗: {e}")
        
        return None
    
    def get_intraday_candles(self, ticker: str, resolution: str = '15',
                            days: int = 5) -> Optional[pd.DataFrame]:
        """
        獲取日內 K 線數據（支持降級）
        
        降級順序: Finnhub → Yahoo Finance
        
        參數:
            ticker: 股票代碼
            resolution: 時間框架 ('1', '5', '15', '30', '60')
            days: 回看天數
        
        Requirements: 2.1, 2.4
        """
        # 方案1: Finnhub
        df = self.get_finnhub_candles(ticker, resolution, days)
        if df is not None and len(df) >= 20:
            return df
        
        # 方案2: 降級到 Yahoo Finance
        logger.info(f"  降級到 Yahoo Finance 獲取 {resolution} 分鐘數據...")
        try:
            # Yahoo Finance 的 interval 格式
            yf_interval = f'{resolution}m'
            hist = self.get_historical_data(ticker, period=f'{days}d', interval=yf_interval)
            if hist is not None and len(hist) >= 20:
                self._record_fallback(f'candles_{resolution}', 'Yahoo Finance')
                return hist
        except Exception as e:
            logger.warning(f"  ! Yahoo Finance {resolution}分鐘數據獲取失敗: {e}")
        
        return None
    
    def get_finnhub_aggregate_indicator(self, ticker: str, 
                                        resolution: str = 'D') -> Optional[Dict]:
        """
        從 Finnhub 獲取綜合技術分析信號
        
        返回:
            {
                'signal': 'buy' | 'sell' | 'neutral',
                'buy_count': int,
                'sell_count': int,
                'neutral_count': int,
                'adx': float,
                'trending': bool
            }
        
        Requirements: 1.1
        """
        try:
            logger.info(f"從 Finnhub 獲取 {ticker} 綜合技術分析...")
            
            if not self.finnhub_client:
                logger.warning("Finnhub 客戶端未初始化")
                return None
            
            result = self.finnhub_client.aggregate_indicator(ticker.upper(), resolution)
            
            if result:
                tech_analysis = result.get('technicalAnalysis', {})
                trend = result.get('trend', {})
                
                output = {
                    'signal': tech_analysis.get('signal', 'neutral'),
                    'buy_count': tech_analysis.get('count', {}).get('buy', 0),
                    'sell_count': tech_analysis.get('count', {}).get('sell', 0),
                    'neutral_count': tech_analysis.get('count', {}).get('neutral', 0),
                    'adx': trend.get('adx'),
                    'trending': trend.get('trending', False)
                }
                
                logger.info(f"  * 綜合信號: {output['signal']} (買:{output['buy_count']}, 賣:{output['sell_count']})")
                return output
            
            return None
            
        except Exception as e:
            logger.warning(f"  ! Finnhub 綜合指標獲取失敗: {e}")
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
