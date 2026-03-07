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
from utils.yfinance_patch import get_patched_session

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

# 導入 bid/ask 估算工具
try:
    from utils.validation import BidAskEstimator, process_option_with_fallback
    BID_ASK_ESTIMATOR_AVAILABLE = True
except ImportError:
    BID_ASK_ESTIMATOR_AVAILABLE = False
    BidAskEstimator = None
    process_option_with_fallback = None
    logger_init = logging.getLogger(__name__)
    logger_init.debug("Bid/Ask 估算工具不可用")

# 嘗試導入 Yahoo Finance 客户端（简化版）
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


class SensitiveDataFilter(logging.Filter):
    """
    日誌過濾器 - 自動清理敏感信息（Task 21.2）
    
    這個過濾器會在所有日誌消息輸出前自動清理敏感信息，
    包括 API Keys、密碼等。只顯示 API Key 的前4位和後4位。
    
    Requirements: 1.14, 2.14
    """
    
    def __init__(self):
        super().__init__()
        # 從環境變量獲取需要清理的 API Keys
        self.api_key_names = [
            'FRED_API_KEY', 'FINNHUB_API_KEY', 'RAPIDAPI_KEY',
            'ALPHA_VANTAGE_API_KEY', 'MASSIVE_API_KEY'
        ]
    
    def filter(self, record):
        """
        過濾日誌記錄，清理敏感信息
        
        參數:
            record: 日誌記錄對象
        
        返回:
            True（總是允許日誌通過，但會修改消息內容）
        """
        # 清理日誌消息
        if hasattr(record, 'msg') and record.msg:
            record.msg = self._sanitize_message(str(record.msg))
        
        # 清理日誌參數
        if hasattr(record, 'args') and record.args:
            record.args = tuple(
                self._sanitize_message(str(arg)) if isinstance(arg, str) else arg
                for arg in record.args
            )
        
        return True
    
    def _sanitize_message(self, message: str) -> str:
        """
        清理消息中的敏感信息
        
        參數:
            message: 原始消息
        
        返回:
            清理後的消息
        """
        if not message:
            return message
        
        import re
        
        result = message
        
        # 清理環境變量中的實際 API Keys
        for key_name in self.api_key_names:
            key_value = os.environ.get(key_name, '')
            if key_value and len(key_value) > 8 and key_value in result:
                # 只顯示前4位和後4位
                masked = f"{key_value[:4]}...{key_value[-4:]}"
                result = result.replace(key_value, masked)
        
        # Pattern 1: API keys in URLs
        pattern1 = r'([?&](?:token|apikey|api_key|key)=)([a-zA-Z0-9]{4})[a-zA-Z0-9]+([a-zA-Z0-9]{4})'
        result = re.sub(pattern1, r'\1\2...\3', result, flags=re.IGNORECASE)
        
        # Pattern 2: Standalone API keys (12+ characters)
        pattern2 = r'\b([a-zA-Z0-9]{4})[a-zA-Z0-9]{12,}([a-zA-Z0-9]{4})\b'
        def replace_if_api_key(match):
            full_match = match.group(0)
            if len(full_match) >= 20:
                return f"{match.group(1)}...{match.group(2)}"
            return full_match
        result = re.sub(pattern2, replace_if_api_key, result)
        
        # Pattern 3: Passwords in URLs
        pattern3 = r'([?&](?:password|passwd|pwd)=)[^&\s]+'
        result = re.sub(pattern3, r'\1***', result, flags=re.IGNORECASE)
        
        # Bearer Token
        result = re.sub(r'(Bearer\s+)[a-zA-Z0-9._-]+', r'\1***', result, flags=re.IGNORECASE)
        
        return result


# 應用 SensitiveDataFilter 到所有日誌處理器（Task 21.2）
_sensitive_filter = SensitiveDataFilter()
for handler in logger.handlers:
    handler.addFilter(_sensitive_filter)

# 同時應用到根日誌記錄器，確保所有模塊的日誌都被過濾
root_logger = logging.getLogger()
for handler in root_logger.handlers:
    if not any(isinstance(f, SensitiveDataFilter) for f in handler.filters):
        handler.addFilter(_sensitive_filter)


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
    def normalize(raw_iv: float, source: str, ticker: str = '') -> float:
        """
        Task 17.3: Simplified IV normalization method for use in get_option_chain()
        
        Normalizes IV to percentage format (0-100) and logs conversions.
        
        參數:
            raw_iv: Raw IV value from data source
            source: Data source name ('IBKR', 'Yahoo', 'Finnhub', etc.)
            ticker: Stock ticker (optional, for logging)
        
        返回:
            float: Normalized IV in percentage format, or None if invalid
        
        Requirements: 1.12, 2.12, 3.11
        """
        if raw_iv is None:
            return None
        
        try:
            iv_float = float(raw_iv)
        except (ValueError, TypeError):
            logger.warning(f"IV normalized: invalid value '{raw_iv}' from {source} for {ticker}")
            return None
        
        # Handle negative or NaN
        if iv_float < 0 or np.isnan(iv_float):
            logger.warning(f"IV normalized: invalid value {iv_float} from {source} for {ticker}")
            return None
        
        # Detect format and normalize
        if 0 < iv_float < 1.0:
            # Decimal format (0-1) -> convert to percentage
            normalized = iv_float * 100
            format_detected = 'decimal'
            logger.info(f"IV normalized: {iv_float} -> {normalized:.2f}% (source: {source}, ticker: {ticker})")
        elif 0 <= iv_float <= 100:
            # Already percentage format
            normalized = iv_float
            format_detected = 'percentage'
            logger.debug(f"IV normalized: {iv_float}% (already percentage, source: {source}, ticker: {ticker})")
        else:
            # Abnormal value (>100)
            normalized = iv_float
            format_detected = 'abnormal'
            logger.warning(f"IV normalized: abnormal value {iv_float} from {source} for {ticker}")
        
        return normalized
    
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
    
    def __init__(self, use_ibkr: bool = None, ibkr_client=None):
        """
        初始化數據獲取器
        
        參數:
            use_ibkr: 是否使用 IBKR（None 時從 settings 讀取）
            ibkr_client: 現有的 IBKRClient 實例 (用於共享連接)
        """
        self.yahoo_v2_client = None
        self.yfinance_client = None
        self.fred_client = None
        self.finnhub_client = None
        self.ibkr_client = None
        self.finviz_scraper = None  # Finviz 抓取器
        self.last_request_time = 0
        self.request_delay = settings.REQUEST_DELAY
        self.session = get_patched_session()
        
        # API 故障記錄（用於報告）
        self.api_failures = {}  # {api_name: [error_messages]}
        self.fallback_used = {}  # {data_type: [used_sources]}
        
        # 模塊執行狀態追蹤（Task 20.1）
        self.module_status = {}  # {module_name: {'status': 'success'|'skipped'|'failed', 'reason': str|None}}
        
        # 動態速率限制（Task 22.1）
        self.base_delay = 3  # 基礎延遲（秒）
        self.current_delay = self.base_delay  # 當前延遲（秒）
        self.rate_limit_events = []  # 速率限制事件記錄
        self.max_delay = 30  # 最大延遲（秒）
        self.min_delay = self.base_delay  # 最小延遲（秒）
        
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
        
        self.initialization_status = self._initialize_clients(ibkr_client)
        logger.info("DataFetcher已初始化")
    
    def _initialize_clients(self, shared_ibkr_client=None):
        """初始化各API客户端"""
        # Fix Bug 1.6: Initialize client_status dictionary to track initialization results
        self.client_status = {}
        
        try:
            # IBKR 客户端（如果启用）
            if self.use_ibkr:
                # 記錄 IBKR 配置狀態
                logger.info("=" * 50)
                logger.info("IBKR 初始化開始")
                logger.info(f"  IBKR_ENABLED (settings): {settings.IBKR_ENABLED}")
                logger.info(f"  IBKR_AVAILABLE (ib_insync 導入): {IBKR_AVAILABLE}")
                logger.info(f"  use_ibkr (最終決定): {self.use_ibkr}")
                
                if not IBKR_AVAILABLE:
                    error_msg = "ib_insync 模塊未安裝或導入失敗"
                    logger.error(f"x {error_msg}")
                    logger.info("  建議: pip install ib_insync")
                    self.client_status['ibkr'] = {'available': False, 'error': f'Import failed: {error_msg}'}
                    logger.info("=" * 50)
                elif shared_ibkr_client:
                     self.ibkr_client = shared_ibkr_client
                     logger.info("* 使用共享的 IBKR 客户端")
                     # Test connection
                     if hasattr(shared_ibkr_client, '_test_connection'):
                         if shared_ibkr_client._test_connection():
                             actual_client_id = getattr(shared_ibkr_client, 'client_id', 'unknown')
                             logger.info(f"  ✓ 共享連接已驗證 (Client ID: {actual_client_id})")
                             self.client_status['ibkr'] = {'available': True, 'error': None, 'client_id': actual_client_id}
                         else:
                             self.client_status['ibkr'] = {'available': False, 'error': 'Connection test failed'}
                     else:
                         # Fallback for older clients without _test_connection
                         is_conn = shared_ibkr_client.is_connected() if hasattr(shared_ibkr_client, 'is_connected') else shared_ibkr_client.connected
                         actual_client_id = getattr(shared_ibkr_client, 'client_id', 'unknown')
                         self.client_status['ibkr'] = {'available': is_conn, 'error': None if is_conn else 'Not connected', 'client_id': actual_client_id}
                     logger.info("=" * 50)
                else:
                    try:
                        port = settings.IBKR_PORT_PAPER if settings.IBKR_USE_PAPER else settings.IBKR_PORT_LIVE
                        mode = 'paper' if settings.IBKR_USE_PAPER else 'live'
                        
                        logger.info(f"  連接參數:")
                        logger.info(f"    主機: {settings.IBKR_HOST}")
                        logger.info(f"    端口: {port} ({'Paper Trading' if settings.IBKR_USE_PAPER else 'Live Trading'})")
                        logger.info(f"    Client ID: {settings.IBKR_CLIENT_ID}")
                        logger.info(f"    模式: {mode}")
                        
                        self.ibkr_client = IBKRClient(
                            host=settings.IBKR_HOST,
                            port=port,
                            client_id=settings.IBKR_CLIENT_ID,
                            mode=mode
                        )
                        
                        # 尝试连接（不强制，失败时使用降级方案）
                        if self.ibkr_client.connect():
                            actual_client_id = self.ibkr_client.client_id
                            if actual_client_id != settings.IBKR_CLIENT_ID:
                                logger.warning(f"  ! Client ID 已自動調整: {settings.IBKR_CLIENT_ID} → {actual_client_id}")
                            logger.info(f"* IBKR 客户端已初始化并连接 (Client ID: {actual_client_id})")
                            self.client_status['ibkr'] = {'available': True, 'error': None, 'client_id': actual_client_id}
                        else:
                            error_msg = self.ibkr_client.last_error if hasattr(self.ibkr_client, 'last_error') and self.ibkr_client.last_error else 'Unknown error'
                            logger.warning(f"! IBKR 客户端初始化但未连接: {error_msg}")
                            logger.warning("  將使用降級方案 (Yahoo Finance)")
                            logger.info("  可能原因:")
                            logger.info("    1. IBKR Gateway 未運行")
                            logger.info("    2. 端口配置錯誤")
                            logger.info("    3. Client ID 衝突（已嘗試自動切換）")
                            logger.info("    4. 網絡連接問題")
                            self.client_status['ibkr'] = {'available': False, 'error': f'Connection failed: {error_msg}'}
                    except Exception as e:
                        error_msg = str(e)
                        error_type = type(e).__name__
                        
                        logger.error(f"x IBKR 初始化失败: {error_type} - {error_msg}")
                        
                        # 根據錯誤類型提供具體建議
                        if 'ConnectionRefusedError' in error_type or 'refused' in error_msg.lower():
                            logger.info("  診斷建議:")
                            logger.info("    1. 確認 IBKR Gateway 正在運行")
                            logger.info(f"    2. 檢查端口配置是否正確 (當前: {port})")
                            logger.info("    3. 檢查防火牆設置")
                        elif 'TimeoutError' in error_type or 'timeout' in error_msg.lower():
                            logger.info("  診斷建議:")
                            logger.info("    1. 檢查網絡連接")
                            logger.info("    2. 增加連接超時時間")
                            logger.info("    3. 確認 IBKR Gateway 響應正常")
                        elif 'clientId' in error_msg.lower() and 'already in use' in error_msg.lower():
                            logger.info("  診斷建議:")
                            logger.info("    1. Client ID 衝突（系統已嘗試自動切換）")
                            logger.info("    2. 關閉其他使用相同 Client ID 的程序")
                            logger.info("    3. 或修改 .env 中的 IBKR_CLIENT_ID")
                        else:
                            logger.info("  診斷建議:")
                            logger.info("    1. 檢查錯誤信息")
                            logger.info("    2. 確認 IBKR Gateway 配置正確")
                            logger.info("    3. 查看 IBKR Gateway 日誌")
                        
                        logger.warning("  將使用降級方案 (Yahoo Finance)")
                        self._record_api_failure('ibkr', error_msg)
                        self.ibkr_client = None
                        self.client_status['ibkr'] = {'available': False, 'error': f'{error_type}: {error_msg}'}
                    
                    logger.info("=" * 50)
            else:
                logger.info("=" * 50)
                logger.info("IBKR 未啟用")
                logger.info(f"  IBKR_ENABLED (settings): {settings.IBKR_ENABLED}")
                logger.info(f"  IBKR_AVAILABLE (ib_insync 導入): {IBKR_AVAILABLE}")
                logger.info("  將使用其他數據源 (Yahoo Finance)")
                logger.info("=" * 50)
                self.client_status['ibkr'] = {'available': False, 'error': 'Not enabled'}
            
            # Yahoo Finance 客户端（優化版，支持 UA 輪換和智能重試）
            # Yahoo Finance 客户端（優化版，支持 UA 輪換和智能重試）
            if YAHOO_V2_AVAILABLE:
                try:
                    # 使用較長的延遲（12秒）避免 429 錯誤
                    yahoo_delay = max(self.request_delay, 12.0)
                    self.yahoo_v2_client = YahooFinanceV2Client(
                        request_delay=yahoo_delay,
                        max_retries=5  # 增加重試次數
                    )
                    logger.info(f"* Yahoo Finance 客户端已初始化（優化版，延遲: {yahoo_delay}s）")
                    self.client_status['yahoo'] = {'available': True, 'error': None}
                except Exception as e:
                    logger.warning(f"! Yahoo Finance 初始化失败: {e}")
                    self._record_api_failure('yahoo_v2', str(e))
                    self.yahoo_v2_client = None
                    self.client_status['yahoo'] = {'available': False, 'error': str(e)}
            else:
                self.client_status['yahoo'] = {'available': False, 'error': 'YahooFinanceV2Client not available'}
            
            # yfinance 作为降级方案
            self.yfinance_client = yf
            logger.info("* yfinance客户端已初始化（降级方案）")
            
            # FRED客户端
            if settings.FRED_API_KEY:
                try:
                    self.fred_client = Fred(api_key=settings.FRED_API_KEY)
                    logger.info("* FRED客户端已初始化")
                    # Validate API key by making a test request
                    self.client_status['fred'] = self._validate_fred_client()
                except Exception as e:
                    logger.warning(f"! FRED 初始化失败: {e}")
                    self._record_api_failure('FRED', str(e))
                    self.fred_client = None
                    self.client_status['fred'] = {'available': False, 'error': str(e)}
            else:
                logger.warning("! FRED_API_KEY未設置，FRED功能將不可用")
                self.client_status['fred'] = {'available': False, 'error': 'API key not configured'}
            
            # Finnhub客户端
            if settings.FINNHUB_API_KEY:
                try:
                    self.finnhub_client = finnhub.Client(api_key=settings.FINNHUB_API_KEY)
                    logger.info("* Finnhub客户端已初始化")
                    # Validate API key
                    self.client_status['finnhub'] = self._validate_finnhub_client()
                except Exception as e:
                    logger.warning(f"! Finnhub 初始化失败: {e}")
                    self._record_api_failure('finnhub', str(e))
                    self.finnhub_client = None
                    self.client_status['finnhub'] = {'available': False, 'error': str(e)}
            else:
                logger.warning("! FINNHUB_API_KEY未設置，Finnhub功能將不可用")
                self.client_status['finnhub'] = {'available': False, 'error': 'API key not configured'}
            
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
                    self.client_status['alpha_vantage'] = {'available': True, 'error': None}
                except Exception as e:
                    logger.warning(f"! Alpha Vantage 初始化失敗: {e}")
                    self._record_api_failure('Alpha Vantage', str(e))
                    self.alpha_vantage_client = None
                    self.client_status['alpha_vantage'] = {'available': False, 'error': str(e)}
            else:
                logger.info("i Alpha Vantage 未配置，跳過初始化")
                self.alpha_vantage_client = None
                self.client_status['alpha_vantage'] = {'available': False, 'error': 'API key not configured'}
            
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
            
            # Fix Bug 1.6: Print initialization summary
            self._print_initialization_summary()
            
            return True
        except Exception as e:
            logger.error(f"x 客户端初始化失敗: {e}")
            return False

    def _validate_finnhub_client(self) -> Dict[str, Any]:
        """
        Validate Finnhub API client by testing API key

        Returns:
            Dict with 'available' (bool) and 'error' (str or None)
        """
        try:
            if not self.finnhub_client:
                return {'available': False, 'error': 'Client not initialized'}

            # Test API key with a simple quote request
            test_result = self.finnhub_client.quote('AAPL')

            if test_result and 'c' in test_result:
                return {'available': True, 'error': None}
            else:
                return {'available': False, 'error': 'Invalid API response'}
        except Exception as e:
            error_msg = str(e)
            if 'Invalid API key' in error_msg or '401' in error_msg or '403' in error_msg:
                return {'available': False, 'error': 'Invalid API Key'}
            else:
                return {'available': False, 'error': f'Validation failed: {error_msg}'}

    def _validate_fred_client(self) -> Dict[str, Any]:
        """
        Validate FRED API client by testing API key

        Returns:
            Dict with 'available' (bool) and 'error' (str or None)
        """
        try:
            if not self.fred_client:
                return {'available': False, 'error': 'Client not initialized'}

            # Test API key with a simple series request
            test_result = self.fred_client.get_series('DGS10', limit=1)

            if test_result is not None and len(test_result) > 0:
                return {'available': True, 'error': None}
            else:
                return {'available': False, 'error': 'Invalid API response'}
        except Exception as e:
            error_msg = str(e)
            if 'Invalid API key' in error_msg or '400' in error_msg or '403' in error_msg:
                return {'available': False, 'error': 'Invalid API Key'}
            else:
                return {'available': False, 'error': f'Validation failed: {error_msg}'}

    def _print_initialization_summary(self):
        """
        Print API Client Initialization Summary to console

        Format:
        API Client Initialization Summary:
        ✓ IBKR Gateway (port 4002)
        ✗ Finnhub (Invalid API Key)
        ✓ Yahoo Finance
        """
        logger.info("=" * 80)
        logger.info("API Client Initialization Summary:")
        logger.info("=" * 80)

        for client_name, status in self.client_status.items():
            if status['available']:
                # Get additional info for IBKR
                if client_name == 'ibkr' and self.ibkr_client:
                    port = self.ibkr_client.port
                    logger.info(f"✓ {client_name.upper()} Gateway (port {port})")
                else:
                    logger.info(f"✓ {client_name.upper()}")
            else:
                error = status.get('error', 'Unknown error')
                logger.info(f"✗ {client_name.upper()} ({error})")

        logger.info("=" * 80)

    
    def _record_api_failure(
        self, 
        api_name: str, 
        error_message: str,
        operation: str = None,
        request_url: str = None,
        request_params: Dict = None,
        response_status: int = None,
        stack_trace: str = None,
        error_type: str = None,
        data_type: str = None
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
            error_type: 錯誤類型 ('ConnectionTimeout', '429', '403', etc.)
            data_type: 數據類型 ('stock_price', 'option_chain', 'earnings', etc.)
        
        Requirements: 5.3, 5.4, 7.1, 7.2, 7.3, 7.4
        """
        if api_name not in self.api_failures:
            self.api_failures[api_name] = []
        
        # 構建詳細的錯誤記錄
        error_record = {
            'timestamp': datetime.now().isoformat(),
            'error_message': error_message,
            'error': error_message  # 保留向後兼容性
        }
        
        # 添加錯誤類型（如果未提供，嘗試從錯誤消息推斷）
        if error_type:
            error_record['error_type'] = error_type
        elif response_status:
            error_record['error_type'] = f'HTTP_{response_status}'
        else:
            # 嘗試從錯誤消息推斷錯誤類型
            error_lower = error_message.lower()
            if 'timeout' in error_lower or 'timed out' in error_lower:
                error_record['error_type'] = 'ConnectionTimeout'
            elif 'connection' in error_lower:
                error_record['error_type'] = 'ConnectionError'
            elif 'rate limit' in error_lower or '429' in error_message:
                error_record['error_type'] = 'RateLimitError'
            elif 'forbidden' in error_lower or '403' in error_message:
                error_record['error_type'] = 'ForbiddenError'
            elif 'not found' in error_lower or '404' in error_message:
                error_record['error_type'] = 'NotFoundError'
            else:
                error_record['error_type'] = 'UnknownError'
        
        # 添加數據類型
        if data_type:
            error_record['data_type'] = data_type
        
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
            error_record['http_status'] = response_status  # 添加 http_status 別名
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
        if data_type:
            log_parts.append(f"數據類型: {data_type}")
        log_parts.append(f"錯誤: {error_message}")
        if error_type:
            log_parts.append(f"類型: {error_type}")
        if response_status:
            log_parts.append(f"狀態碼: {response_status}")
        
        logger.warning(" | ".join(log_parts))
        
        if stack_trace:
            logger.debug(f"堆棧信息: {stack_trace[:500]}...")
    
    def _check_data_completeness(self, data: Dict[str, Any], required_fields: List[str]) -> Dict[str, Any]:
        """
        Task 19.1: Check data completeness and identify missing fields with reasons
        
        Parameters:
            data: Data dictionary to check
            required_fields: List of required field names
        
        Returns:
            dict: {
                'complete': bool,
                'missing_fields': List[str],
                'missing_reasons': Dict[str, str],
                'completeness_percentage': float
            }
        """
        missing_fields = []
        missing_reasons = {}
        
        for field in required_fields:
            if field not in data or data[field] is None or data[field] == 'N/A':
                missing_fields.append(field)
                # Get reason for missing field
                reason = self._get_missing_reason(field)
                missing_reasons[field] = reason
                logger.warning(f"Missing {field}: {reason}")
        
        completeness_percentage = ((len(required_fields) - len(missing_fields)) / len(required_fields)) * 100
        
        return {
            'complete': len(missing_fields) == 0,
            'missing_fields': missing_fields,
            'missing_reasons': missing_reasons,
            'completeness_percentage': completeness_percentage
        }
    
    def _get_missing_reason(self, field: str) -> str:
        """
        Task 19.1: Determine the reason why a field is missing
        
        Parameters:
            field: Field name
        
        Returns:
            str: Reason for missing field
        """
        # Check API failures for this field
        field_to_api_mapping = {
            'eps': ['Finnhub', 'Alpha Vantage', 'Yahoo Finance'],
            'dividend': ['Yahoo Finance', 'Alpha Vantage'],
            'risk_free_rate': ['FRED'],
            'vix': ['Yahoo Finance', 'CBOE'],
            'iv': ['IBKR', 'Yahoo Finance'],
            'greeks': ['IBKR'],
            'beta': ['Finnhub', 'Yahoo Finance'],
            'market_cap': ['Finnhub', 'Yahoo Finance'],
            'pe_ratio': ['Finnhub', 'Yahoo Finance'],
            'forward_pe': ['Finnhub', 'Yahoo Finance']
        }
        
        potential_sources = field_to_api_mapping.get(field, [])
        
        # Check if any of the potential sources failed
        failed_sources = []
        for source in potential_sources:
            if source in self.api_failures and len(self.api_failures[source]) > 0:
                # Get the most recent error
                recent_error = self.api_failures[source][-1]
                error_msg = recent_error.get('error', 'Unknown error')
                failed_sources.append(f"{source} ({error_msg})")
        
        if failed_sources:
            return f"All sources failed: {', '.join(failed_sources)}"
        elif not potential_sources:
            return "No data source configured for this field"
        else:
            return f"Data not available from {', '.join(potential_sources)}"
    
    def format_field_with_reason(self, field_name: str, value: Any, data_source: str = None) -> str:
        """
        Task 19.2: Format a field with failure reason annotation or data source
        
        Parameters:
            field_name: Name of the field
            value: Field value
            data_source: Data source name (if available)
        
        Returns:
            str: Formatted field string with annotation
        
        Examples:
            - "EPS: $2.50 (Source: Finnhub)"
            - "EPS: N/A (IBKR connection failed, Finnhub API key invalid)"
            - "VIX: N/A (All sources failed: IBKR timeout, Yahoo 429 error)"
        """
        if value is None or value == 'N/A' or (isinstance(value, str) and value.strip() == ''):
            # Field is missing, add failure reason
            reason = self._get_missing_reason(field_name)
            return f"{field_name}: N/A ({reason})"
        else:
            # Field has value, add data source if available
            if data_source:
                return f"{field_name}: {value} (Source: {data_source})"
            else:
                return f"{field_name}: {value}"
    
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
        清理日誌消息中的敏感信息（Task 21.1）
        
        在所有日誌輸出前清理敏感信息，包括 API Keys、密碼等。
        只顯示 API Key 的前4位和後4位，中間用 ... 替代。
        
        參數:
            message: 原始日誌消息
        
        返回:
            清理後的日誌消息
        
        Requirements: 1.14, 2.14
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
        
        # 清理環境變量中的實際 API Keys
        for key_name in api_key_names:
            key_value = os.environ.get(key_name, '')
            if key_value and len(key_value) > 8 and key_value in result:
                # 只顯示前4位和後4位
                masked = f"{key_value[:4]}...{key_value[-4:]}"
                result = result.replace(key_value, masked)
        
        # Pattern 1: API keys in URLs
        # 匹配 ?token=abc123xyz789def456 或 &apikey=abc123xyz789def456
        # 替換為 ?token=abc1...f456 或 &apikey=abc1...f456
        pattern1 = r'([?&](?:token|apikey|api_key|key)=)([a-zA-Z0-9]{4})[a-zA-Z0-9]+([a-zA-Z0-9]{4})'
        result = re.sub(pattern1, r'\1\2...\3', result, flags=re.IGNORECASE)
        
        # Pattern 2: Standalone API keys (12+ characters)
        # 匹配獨立的長字符串 API keys
        # 替換為 abc1...x789
        pattern2 = r'\b([a-zA-Z0-9]{4})[a-zA-Z0-9]{12,}([a-zA-Z0-9]{4})\b'
        # 需要確保不是普通單詞，檢查上下文
        def replace_if_api_key(match):
            full_match = match.group(0)
            # 如果長度 >= 20，很可能是 API key
            if len(full_match) >= 20:
                return f"{match.group(1)}...{match.group(2)}"
            return full_match
        result = re.sub(pattern2, replace_if_api_key, result)
        
        # Pattern 3: Passwords in URLs
        # 匹配 ?password=xxx 或 &pwd=xxx
        # 替換為 ?password=*** 或 &pwd=***
        pattern3 = r'([?&](?:password|passwd|pwd)=)[^&\s]+'
        result = re.sub(pattern3, r'\1***', result, flags=re.IGNORECASE)
        
        # 額外清理：Bearer Token
        result = re.sub(r'(Bearer\s+)[a-zA-Z0-9._-]+', r'\1***', result, flags=re.IGNORECASE)
        
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
                - total_failures: 總故障次數
                - by_source: 按來源分類的故障統計
                - by_error_type: 按錯誤類型分類的故障統計
                - recent_failures: 最近的故障記錄（每個來源最多5條）
        """
        total_failures = 0
        by_source = {}
        by_error_type = {}
        recent_failures = []
        
        for api_name, records in self.api_failures.items():
            if not records:
                continue
            
            # 統計該來源的故障次數
            source_count = len(records)
            total_failures += source_count
            by_source[api_name] = source_count
            
            # 統計錯誤類型
            for record in records:
                error_type = record.get('error_type', 'Unknown')
                by_error_type[error_type] = by_error_type.get(error_type, 0) + 1
            
            # 收集最近的故障（每個來源最多5條）
            recent_records = records[-5:] if len(records) > 5 else records
            for record in recent_records:
                recent_failures.append({
                    'source': api_name,
                    'timestamp': record.get('timestamp'),
                    'error_type': record.get('error_type', 'Unknown'),
                    'error_message': record.get('error_message', ''),
                    'operation': record.get('operation', 'unknown'),
                    'response_status': record.get('response_status')
                })
        
        # 按時間戳排序最近的故障（最新的在前）
        recent_failures.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        summary = {
            'total_failures': total_failures,
            'by_source': by_source,
            'by_error_type': by_error_type,
            'recent_failures': recent_failures[:25]  # 限制最多返回25條最近的故障
        }
        
        return summary
    
    def execute_module(
        self,
        module_name: str,
        module_func: callable,
        required_data: List[str] = None,
        *args,
        **kwargs
    ) -> Any:
        """
        執行模塊並追蹤狀態（Task 20.1）
        
        這是一個包裝方法，用於執行分析模塊並記錄執行狀態。
        在執行前檢查所需數據是否可用，執行後記錄成功或失敗狀態。
        
        參數:
            module_name: 模塊名稱（用於狀態追蹤）
            module_func: 要執行的模塊函數
            required_data: 所需數據字段列表（可選）
            *args, **kwargs: 傳遞給模塊函數的參數
        
        返回:
            模塊函數的返回值，如果跳過或失敗則返回 None
        
        Requirements: 1.7, 2.7
        """
        # 檢查所需數據
        if required_data:
            missing_data = []
            for field in required_data:
                # 檢查 kwargs 中是否有該字段且不為 None
                if field in kwargs:
                    value = kwargs[field]
                    if value is None or (isinstance(value, (int, float)) and pd.isna(value)):
                        missing_data.append(field)
                else:
                    missing_data.append(field)
            
            if missing_data:
                reason = f"Missing required data: {', '.join(missing_data)}"
                self.module_status[module_name] = {
                    'status': 'skipped',
                    'reason': reason
                }
                logger.info(f"Module {module_name} skipped: {reason}")
                return None
        
        # 執行模塊
        try:
            result = module_func(*args, **kwargs)
            self.module_status[module_name] = {
                'status': 'success',
                'reason': None
            }
            logger.info(f"Module {module_name} success")
            return result
        except Exception as e:
            error_type = type(e).__name__
            error_message = str(e)
            reason = f"{error_type}: {error_message}"
            self.module_status[module_name] = {
                'status': 'failed',
                'reason': reason
            }
            logger.error(f"Module {module_name} failed: {reason}")
            return None
    
    def get_module_execution_summary(self) -> Dict[str, Any]:
        """
        獲取模塊執行摘要（Task 20.2）
        
        返回:
            dict: 包含模塊執行統計的摘要
                - total_modules: 總模塊數
                - successful: 成功執行的模塊數
                - skipped: 跳過的模塊數
                - failed: 失敗的模塊數
                - modules: 各模塊的詳細狀態
        
        Requirements: 1.7, 2.7
        """
        total_modules = len(self.module_status)
        successful = sum(1 for m in self.module_status.values() if m['status'] == 'success')
        skipped = sum(1 for m in self.module_status.values() if m['status'] == 'skipped')
        failed = sum(1 for m in self.module_status.values() if m['status'] == 'failed')
        
        summary = {
            'total_modules': total_modules,
            'successful': successful,
            'skipped': skipped,
            'failed': failed,
            'modules': self.module_status.copy()
        }
        
        return summary
    
    def _adjust_delay_on_rate_limit(self):
        """
        在遇到速率限制時調整延遲（Task 22.1）
        
        當收到 429 錯誤時，將當前延遲加倍（最大 30 秒）。
        記錄速率限制事件以供報告使用。
        
        Requirements: 1.13, 2.13
        """
        old_delay = self.current_delay
        self.current_delay = min(self.current_delay * 2, self.max_delay)
        
        # 記錄速率限制事件
        event = {
            'timestamp': datetime.now().isoformat(),
            'old_delay': old_delay,
            'new_delay': self.current_delay
        }
        self.rate_limit_events.append(event)
        
        # 清理超過 24 小時的舊事件
        cutoff_time = datetime.now() - timedelta(hours=24)
        self.rate_limit_events = [
            e for e in self.rate_limit_events
            if datetime.fromisoformat(e['timestamp']) > cutoff_time
        ]
        
        logger.info(f"Rate limit hit, increasing delay to {self.current_delay}s")
    
    def _reset_delay_on_success(self):
        """
        在請求成功時逐漸降低延遲（Task 22.1）
        
        當請求成功時，將當前延遲乘以 0.8（最小為基礎延遲）。
        這允許系統在速率限制解除後逐漸恢復到正常速度。
        
        Requirements: 1.13, 2.13
        """
        old_delay = self.current_delay
        self.current_delay = max(self.current_delay * 0.8, self.min_delay)
        
        if old_delay != self.current_delay:
            logger.info(f"Request successful, decreasing delay to {self.current_delay}s")
    
    def get_rate_limit_summary(self) -> Dict[str, Any]:
        """
        獲取速率限制摘要（Task 22.2）
        
        返回:
            dict: 包含速率限制統計的摘要
                - current_delay: 當前延遲（秒）
                - base_delay: 基礎延遲（秒）
                - rate_limit_events_count: 24小時內的速率限制事件數
                - last_event: 最近的速率限制事件
                - events: 所有速率限制事件列表
        
        Requirements: 1.13, 2.13
        """
        last_event = self.rate_limit_events[-1] if self.rate_limit_events else None
        
        summary = {
            'current_delay': self.current_delay,
            'base_delay': self.base_delay,
            'rate_limit_events_count': len(self.rate_limit_events),
            'last_event': last_event,
            'events': self.rate_limit_events.copy()
        }
        
        return summary
    
    def _optimize_dataframe_memory(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        優化 DataFrame 內存使用
        - 將 float64 轉換為 float32（在精度允許的情況下）
        - 使用 categorical 類型處理重複字符串值
        - 跳過包含 unhashable 類型（dict, list, set）的列
        """
        if df.empty:
            return df
        
        # 轉換數值列為 float32
        float_cols = df.select_dtypes(include=['float64']).columns
        for col in float_cols:
            # 檢查是否可以安全轉換為 float32
            # 只轉換不會損失精度的列
            try:
                df[col] = df[col].astype('float32')
            except (ValueError, OverflowError):
                # 如果轉換失敗，保持原樣
                pass
        
        # 轉換重複字符串為 categorical
        object_cols = df.select_dtypes(include=['object']).columns
        for col in object_cols:
            try:
                # 檢查列是否包含 unhashable 類型（dict, list, set）
                sample_value = df[col].dropna().iloc[0] if not df[col].dropna().empty else None
                if sample_value is not None and isinstance(sample_value, (dict, list, set)):
                    logger.debug(f"跳過優化列 '{col}'：包含 unhashable 類型 {type(sample_value).__name__}")
                    continue
                
                # 只有當唯一值數量少於總行數的 50% 時才轉換
                if df[col].nunique() < len(df) * 0.5:
                    try:
                        df[col] = df[col].astype('category')
                    except (ValueError, TypeError):
                        pass
            except (TypeError, KeyError, IndexError):
                # 處理邊緣情況：空列、nunique() 失敗等
                logger.debug(f"跳過優化列 '{col}'：發生錯誤")
                continue
        
        return df
    
    def _safe_int(self, value, default=0):
        """安全地將值轉換為整數"""
        try:
            if pd.isna(value):
                return default
            return int(value)
        except (ValueError, TypeError):
            return default
    
    def _fill_missing_bid_ask(self, option_df: pd.DataFrame, option_type: str = 'call') -> pd.DataFrame:
        """
        填補缺失的 bid/ask 數據
        
        當期權數據缺失 bid/ask 時，使用估算值填補
        
        參數:
            option_df: 期權 DataFrame
            option_type: 'call' 或 'put'
        
        返回:
            DataFrame: 填補後的期權數據
        
        Requirements: Code_Fix_Plan.md - 問題3
        """
        if option_df.empty:
            return option_df
        
        if not BID_ASK_ESTIMATOR_AVAILABLE or BidAskEstimator is None:
            return option_df
        
        result_df = option_df.copy()
        filled_count = 0
        
        for idx, row in result_df.iterrows():
            bid = row.get('bid')
            ask = row.get('ask')
            
            # 檢查是否需要估算
            needs_estimation = (
                pd.isna(bid) or pd.isna(ask) or
                bid <= 0 or ask <= 0
            )
            
            if needs_estimation:
                market_price = row.get('lastPrice') or row.get('last')
                
                if market_price and market_price > 0:
                    estimated = BidAskEstimator.estimate_bid_ask(
                        market_price=market_price,
                        open_interest=self._safe_int(row.get('openInterest')),
                        volume=self._safe_int(row.get('volume')),
                        option_type=option_type
                    )
                    
                    if estimated:
                        result_df.at[idx, 'bid'] = estimated['bid']
                        result_df.at[idx, 'ask'] = estimated['ask']
                        result_df.at[idx, 'bid_ask_estimated'] = True
                        filled_count += 1
        
        if filled_count > 0:
            logger.info(f"  填補了 {filled_count} 個 {option_type} 期權的 bid/ask 數據")
        
        return result_df

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
    
    # ==================== Task 16: API Degradation Chain and Retry Mechanisms ====================
    
    # Task 16.1: Enhanced API degradation logic
    FALLBACK_TRIGGERS = [
        ConnectionError,
        TimeoutError,
        Exception,  # Includes HTTPError, DataValidationError, etc.
    ]
    
    def _fetch_with_fallback(self, data_type: str, sources: List[str], fetch_func_map: Dict[str, callable], *args, **kwargs):
        """
        Fetch data with fallback mechanism through multiple sources.
        
        Implements the API degradation chain by attempting each data source in priority order.
        Logs each attempt and records failures for diagnostics.
        
        Args:
            data_type: Type of data being fetched (e.g., 'stock_info', 'option_chain')
            sources: List of data source names in priority order
            fetch_func_map: Dict mapping source names to fetch functions
            *args, **kwargs: Arguments to pass to fetch functions
        
        Returns:
            Data from the first successful source, or None if all fail
        
        Requirements: 1.3, 1.4, 2.3, 2.4, 3.1
        """
        # Initialize attempt path tracking if not exists
        if not hasattr(self, '_attempt_paths'):
            self._attempt_paths = {}
        
        if data_type not in self._attempt_paths:
            self._attempt_paths[data_type] = {'history': [], 'current_attempt': []}
        
        current_attempt = []
        
        for source in sources:
            fetch_func = fetch_func_map.get(source)
            
            if not fetch_func:
                logger.debug(f"  {source}: No fetch function available, skipping")
                continue
            
            try:
                logger.info(f"Attempting {source} for {data_type}...")
                
                # Attempt to fetch data
                result = fetch_func(*args, **kwargs)
                
                if result is not None:
                    # Success
                    logger.info(f"✓ {source} succeeded for {data_type}")
                    current_attempt.append({
                        'source': source,
                        'success': True,
                        'error_reason': None,
                        'timestamp': datetime.now().isoformat()
                    })
                    
                    # Record successful fallback
                    self._record_fallback(data_type, source, success=True)
                    
                    # Save attempt history
                    self._attempt_paths[data_type]['history'].append(current_attempt)
                    
                    return result
                else:
                    # Returned None - treat as failure
                    error_msg = "Returned None or empty data"
                    logger.warning(f"{source} failed: {error_msg}, trying next source...")
                    
                    current_attempt.append({
                        'source': source,
                        'success': False,
                        'error_reason': error_msg,
                        'timestamp': datetime.now().isoformat()
                    })
                    
                    self._record_fallback_failure(data_type, source, error_msg)
                    
            except Exception as e:
                # Exception occurred
                error_type = type(e).__name__
                error_message = str(e)
                full_error = f"{error_type} - {error_message}"
                
                logger.warning(f"{source} failed: {full_error}, trying next source...")
                
                current_attempt.append({
                    'source': source,
                    'success': False,
                    'error_reason': full_error,
                    'timestamp': datetime.now().isoformat()
                })
                
                # Record API failure
                self._record_api_failure(source, error_message, operation=f'fetch_{data_type}')
                self._record_fallback_failure(data_type, source, full_error)
        
        # All sources failed
        logger.error(f"✗ All sources failed for {data_type}")
        self._attempt_paths[data_type]['history'].append(current_attempt)
        
        return None
    
    # Task 16.2: Intelligent retry mechanism with exponential backoff
    def _retry_with_backoff(self, func: callable, max_retries: int = 3, base_delay: float = 2.0, *args, **kwargs):
        """
        Retry a function with exponential backoff.
        
        Implements intelligent retry logic with exponential backoff for transient errors.
        Special handling for 429 (rate limit) errors.
        
        Args:
            func: Function to retry
            max_retries: Maximum number of retry attempts
            base_delay: Base delay in seconds (default 2.0)
            *args, **kwargs: Arguments to pass to the function
        
        Returns:
            Result from successful function call
        
        Raises:
            Exception: After max retries exceeded
        
        Requirements: 1.8, 2.8, 3.12
        """
        import requests
        
        for attempt in range(1, max_retries + 1):
            try:
                return func(*args, **kwargs)
                
            except requests.exceptions.HTTPError as e:
                if hasattr(e, 'response') and e.response is not None and e.response.status_code == 429:
                    # Rate limit error - use exponential backoff
                    if attempt < max_retries:
                        delay = min(base_delay * (2 ** (attempt - 1)), 60)
                        logger.warning(f"Rate limit hit, retrying in {delay}s... (attempt {attempt}/{max_retries})")
                        time.sleep(delay)
                    else:
                        logger.error(f"Max retries exceeded after {max_retries} attempts")
                        raise Exception(f"MaxRetriesExceeded: Failed after {max_retries} attempts due to rate limiting")
                else:
                    # Other HTTP error - don't retry
                    raise
                    
            except (ConnectionError, TimeoutError) as e:
                # Transient network errors - retry with backoff
                if attempt < max_retries:
                    delay = min(base_delay * (2 ** (attempt - 1)), 60)
                    logger.warning(f"Network error, retrying in {delay}s... (attempt {attempt}/{max_retries}): {e}")
                    time.sleep(delay)
                else:
                    logger.error(f"Max retries exceeded after {max_retries} attempts")
                    raise Exception(f"MaxRetriesExceeded: Failed after {max_retries} attempts due to network errors")
            
            except Exception as e:
                # Other exceptions - don't retry
                raise
        
        # Should not reach here
        raise Exception(f"MaxRetriesExceeded: Failed after {max_retries} attempts")
    
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
                yf_ticker = yf.Ticker(ticker, session=self.session)
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
    
    # ========================================================================
    # Stage 2: 新的欄位級數據獲取函式（漸進式重構）
    # 這些函式遵循 data_policy.py 定義的欄位權責
    # ========================================================================
    
    def get_stock_quote_primary(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        獲取股票實時報價（Quote 數據）
        
        職責：只負責實時價格與技術數據
        主來源：Finnhub → Alpha Vantage → yfinance
        
        返回欄位：
        - current_price, open, intraday_high, intraday_low
        - previous_close, volume, change, change_percent
        - data_source, data_timestamp, is_market_hours
        
        Ref: option-data-review.md Section II.2, data_policy.py STOCK_QUOTE_AUTHORITY
        """
        from data_layer.data_policy import DataSource, StockQuoteSchema
        from datetime import datetime as _dt
        
        logger.info(f"獲取 {ticker} 實時報價（Quote Primary）...")
        
        # 方案1: Finnhub（最高優先級）
        if self.finnhub_client:
            try:
                logger.info("  使用 Finnhub API...")
                self._rate_limit_delay()
                
                quote = self.finnhub_client.quote(ticker)
                
                if quote and quote.get('c', 0) > 0:
                    quote_data: StockQuoteSchema = {
                        'ticker': ticker,
                        'current_price': quote.get('c', 0),
                        'open': quote.get('o', 0),
                        'intraday_high': quote.get('h', 0),
                        'intraday_low': quote.get('l', 0),
                        'previous_close': quote.get('pc', 0),
                        'change': quote.get('d', 0),
                        'change_percent': quote.get('dp', 0),
                        'volume': None,  # Finnhub quote 不提供 volume
                        'data_source': DataSource.FINNHUB,
                        'is_market_hours': True,
                        'data_timestamp': _dt.now().isoformat(),
                    }
                    
                    logger.info(f"* 成功獲取 {ticker} 報價 (Finnhub): ${quote_data['current_price']:.2f}")
                    self._record_fallback('stock_quote', DataSource.FINNHUB)
                    return quote_data
                else:
                    logger.warning("! Finnhub 返回無效數據")
                    self._record_fallback_failure('stock_quote', DataSource.FINNHUB, '返回無效數據')
            except Exception as e:
                logger.warning(f"! Finnhub 獲取失敗: {e}")
                self._record_api_failure('Finnhub', f"get_stock_quote_primary: {e}")
                self._record_fallback_failure('stock_quote', DataSource.FINNHUB, str(e))
        
        # 方案2: Alpha Vantage
        if hasattr(self, 'alpha_vantage_client') and self.alpha_vantage_client:
            try:
                logger.info("  使用 Alpha Vantage API...")
                quote_data_av = self.alpha_vantage_client.get_quote(ticker)
                
                if quote_data_av and quote_data_av.get('current_price', 0) > 0:
                    quote_data: StockQuoteSchema = {
                        'ticker': ticker,
                        'current_price': quote_data_av.get('current_price', 0),
                        'open': quote_data_av.get('open', 0),
                        'intraday_high': quote_data_av.get('high', 0),
                        'intraday_low': quote_data_av.get('low', 0),
                        'previous_close': quote_data_av.get('previous_close', 0),
                        'volume': quote_data_av.get('volume', 0),
                        'change': quote_data_av.get('change', 0),
                        'change_percent': quote_data_av.get('change_percent', 0),
                        'data_source': DataSource.ALPHA_VANTAGE,
                        'data_timestamp': _dt.now().isoformat(),
                    }
                    
                    logger.info(f"* 成功獲取 {ticker} 報價 (Alpha Vantage): ${quote_data['current_price']:.2f}")
                    self._record_fallback('stock_quote', DataSource.ALPHA_VANTAGE)
                    return quote_data
                else:
                    logger.warning("! Alpha Vantage 返回無效數據")
                    self._record_fallback_failure('stock_quote', DataSource.ALPHA_VANTAGE, '返回無效數據')
            except Exception as e:
                logger.warning(f"! Alpha Vantage 獲取失敗: {e}")
                self._record_api_failure('Alpha Vantage', f"get_stock_quote_primary: {e}")
                self._record_fallback_failure('stock_quote', DataSource.ALPHA_VANTAGE, str(e))
        
        # 方案3: yfinance（最後備用）
        try:
            self._rate_limit_delay()
            logger.info("  使用 yfinance...")
            stock = yf.Ticker(ticker, session=self.session)
            info = stock.info
            
            if info.get('currentPrice', 0) > 0 or info.get('regularMarketPrice', 0) > 0:
                current_price = info.get('currentPrice') or info.get('regularMarketPrice', 0)
                quote_data: StockQuoteSchema = {
                    'ticker': ticker,
                    'current_price': current_price,
                    'open': info.get('open', 0),
                    'intraday_high': info.get('dayHigh', 0),
                    'intraday_low': info.get('dayLow', 0),
                    'previous_close': info.get('previousClose', 0),
                    'volume': info.get('volume', 0),
                    'data_source': DataSource.YFINANCE,
                    'data_timestamp': _dt.now().isoformat(),
                }
                
                logger.info(f"* 成功獲取 {ticker} 報價 (yfinance): ${quote_data['current_price']:.2f}")
                self._record_fallback('stock_quote', DataSource.YFINANCE)
                return quote_data
        except Exception as e:
            logger.error(f"x yfinance 獲取報價失敗: {e}")
            self._record_api_failure('yfinance', f"get_stock_quote_primary: {e}")
        
        logger.error(f"x 無法獲取 {ticker} 報價（所有來源失敗）")
        return None
    
    def get_stock_fundamentals_primary(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        獲取股票基本面數據
        
        職責：只負責公司基本面與財務數據
        主來源：Finviz → Finnhub → Alpha Vantage
        
        返回欄位：
        - market_cap, pe_ratio, forward_pe, peg_ratio
        - eps, eps_ttm, eps_next_y, beta
        - sector, industry, company_name
        - profit_margin, operating_margin, roe, roa, debt_eq
        - insider_own, inst_own, short_float
        - data_source
        
        Ref: option-data-review.md Section II.2, data_policy.py STOCK_FUNDAMENTALS_AUTHORITY
        """
        from data_layer.data_policy import DataSource, StockFundamentalsSchema
        
        logger.info(f"獲取 {ticker} 基本面數據（Fundamentals Primary）...")
        
        # 方案1: Finviz（最高優先級，最完整的基本面數據）
        if hasattr(self, 'finviz_scraper') and self.finviz_scraper:
            try:
                logger.info("  使用 Finviz...")
                finviz_data = self.finviz_scraper.get_stock_fundamentals(ticker)
                
                if finviz_data:
                    validated_data = self._validate_and_supplement_finviz_data(finviz_data, ticker)
                    
                    if validated_data:
                        fundamentals: StockFundamentalsSchema = {
                            'ticker': ticker,
                            'market_cap': validated_data.get('market_cap'),
                            'pe_ratio': validated_data.get('pe'),
                            'forward_pe': validated_data.get('forward_pe'),
                            'peg_ratio': validated_data.get('peg'),
                            'eps': validated_data.get('eps_ttm'),
                            'eps_ttm': validated_data.get('eps_ttm'),
                            'eps_next_y': validated_data.get('eps_next_y'),
                            'beta': validated_data.get('beta'),
                            'sector': validated_data.get('sector'),
                            'industry': validated_data.get('industry'),
                            'company_name': validated_data.get('company_name'),
                            'profit_margin': validated_data.get('profit_margin'),
                            'operating_margin': validated_data.get('operating_margin'),
                            'roe': validated_data.get('roe'),
                            'roa': validated_data.get('roa'),
                            'debt_eq': validated_data.get('debt_eq'),
                            'insider_own': validated_data.get('insider_own'),
                            'inst_own': validated_data.get('inst_own'),
                            'short_float': validated_data.get('short_float'),
                            'data_source': DataSource.FINVIZ,
                        }
                        
                        logger.info(f"* 成功獲取 {ticker} 基本面 (Finviz)")
                        if fundamentals.get('pe_ratio'):
                            logger.info(f"  P/E: {fundamentals['pe_ratio']:.2f}")
                        if fundamentals.get('eps'):
                            logger.info(f"  EPS: ${fundamentals['eps']:.2f}")
                        
                        self._record_fallback('stock_fundamentals', DataSource.FINVIZ)
                        return fundamentals
                    else:
                        logger.warning("! Finviz 數據驗證失敗")
                        self._record_fallback_failure('stock_fundamentals', DataSource.FINVIZ, '數據驗證失敗')
                else:
                    logger.warning("! Finviz 未返回數據")
                    self._record_fallback_failure('stock_fundamentals', DataSource.FINVIZ, '未返回數據')
            except Exception as e:
                logger.warning(f"! Finviz 獲取失敗: {e}")
                self._record_api_failure('Finviz', f"get_stock_fundamentals_primary: {e}")
                self._record_fallback_failure('stock_fundamentals', DataSource.FINVIZ, str(e))
        
        # 方案2: Finnhub（備用）
        if self.finnhub_client:
            try:
                logger.info("  使用 Finnhub API...")
                self._rate_limit_delay()
                
                profile = self.finnhub_client.company_profile2(symbol=ticker)
                
                if profile:
                    fundamentals: StockFundamentalsSchema = {
                        'ticker': ticker,
                        'company_name': profile.get('name', ''),
                        'market_cap': profile.get('marketCapitalization', 0) * 1000000 if profile.get('marketCapitalization') else 0,
                        'sector': profile.get('finnhubIndustry', ''),
                        'industry': profile.get('finnhubIndustry', ''),
                        'data_source': DataSource.FINNHUB,
                    }
                    
                    logger.info(f"* 成功獲取 {ticker} 基本面 (Finnhub，部分數據)")
                    self._record_fallback('stock_fundamentals', DataSource.FINNHUB)
                    return fundamentals
            except Exception as e:
                logger.warning(f"! Finnhub 獲取基本面失敗: {e}")
                self._record_api_failure('Finnhub', f"get_stock_fundamentals_primary: {e}")
        
        # 方案3: Alpha Vantage（備用）
        if hasattr(self, 'alpha_vantage_client') and self.alpha_vantage_client:
            try:
                logger.info("  使用 Alpha Vantage API...")
                overview = self.alpha_vantage_client.get_company_overview(ticker)
                
                if overview:
                    fundamentals: StockFundamentalsSchema = {
                        'ticker': ticker,
                        'market_cap': overview.get('market_cap', 0),
                        'pe_ratio': overview.get('pe_ratio', 0),
                        'forward_pe': overview.get('forward_pe', 0),
                        'eps': overview.get('eps', 0),
                        'beta': overview.get('beta', 0),
                        'company_name': overview.get('company_name', ''),
                        'sector': overview.get('sector', ''),
                        'industry': overview.get('industry', ''),
                        'data_source': DataSource.ALPHA_VANTAGE,
                    }
                    
                    logger.info(f"* 成功獲取 {ticker} 基本面 (Alpha Vantage)")
                    self._record_fallback('stock_fundamentals', DataSource.ALPHA_VANTAGE)
                    return fundamentals
            except Exception as e:
                logger.warning(f"! Alpha Vantage 獲取基本面失敗: {e}")
                self._record_api_failure('Alpha Vantage', f"get_stock_fundamentals_primary: {e}")
        
        logger.error(f"x 無法獲取 {ticker} 基本面（所有來源失敗）")
        return None
    
    def get_stock_advanced_from_ibkr(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        獲取股票進階數據（IBKR 專屬）
        
        職責：只負責 IBKR Tick 提供的進階指標
        主來源：IBKR Tick 104/106/232/456
        
        返回欄位：
        - historical_volatility_30d (HV-30, Tick 104)
        - implied_volatility_30d (IV-30, Tick 106)
        - dividend_yield (Tick 456)
        - annual_dividend (Tick 456)
        - mark_price (Tick 232)
        - hv_source, div_source, data_source
        
        注意：此函式不應被用作主股價來源
        
        Ref: option-data-review.md Section III.2, data_policy.py STOCK_ADVANCED_AUTHORITY
        """
        from data_layer.data_policy import DataSource, StockAdvancedSchema
        
        logger.info(f"獲取 {ticker} 進階數據（IBKR Advanced）...")
        
        if not (self.use_ibkr and self.ibkr_client and self.ibkr_client.is_connected()):
            logger.warning("! IBKR 未連接，無法獲取進階數據")
            return None
        
        try:
            ibkr_data = self.ibkr_client.get_stock_full_data(ticker)
            
            if ibkr_data:
                # 注意：不包含 price 欄位，避免被誤用為主股價
                advanced: StockAdvancedSchema = {
                    'ticker': ticker,
                    'historical_volatility_30d': ibkr_data.get('historical_volatility', 0) * 100 if ibkr_data.get('historical_volatility') else None,
                    'implied_volatility_30d': ibkr_data.get('implied_volatility_30d', 0) * 100 if ibkr_data.get('implied_volatility_30d') else None,
                    'dividend_yield': ibkr_data.get('dividend_yield', 0),
                    'annual_dividend': ibkr_data.get('annual_dividend', 0),
                    'mark_price': ibkr_data.get('mark_price'),
                    'hv_source': ibkr_data.get('hv_source', DataSource.IBKR_TICK),
                    'div_source': ibkr_data.get('div_source', DataSource.IBKR_TICK),
                    'data_source': DataSource.IBKR_TICK,
                }
                
                logger.info(f"* 成功獲取 {ticker} 進階數據 (IBKR)")
                if advanced.get('historical_volatility_30d'):
                    logger.info(f"  HV-30: {advanced['historical_volatility_30d']:.2f}%")
                if advanced.get('dividend_yield'):
                    logger.info(f"  Div Yield: {advanced['dividend_yield']*100:.2f}%")
                
                self._record_fallback('stock_advanced', DataSource.IBKR_TICK)
                return advanced
            else:
                logger.warning("! IBKR 返回空數據")
                return None
        except Exception as e:
            logger.error(f"x IBKR 獲取進階數據失敗: {e}")
            self._record_api_failure('IBKR', f"get_stock_advanced_from_ibkr: {e}")
            return None
    
    def merge_stock_snapshot(
        self,
        quote: Optional[Dict[str, Any]] = None,
        fundamentals: Optional[Dict[str, Any]] = None,
        advanced: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        合併股票快照數據（欄位級合併）
        
        遵循 data_policy.py 定義的欄位權責，禁止錯誤覆蓋。
        
        合併規則：
        1. Quote 欄位優先級：Finnhub > Alpha Vantage > yfinance
        2. Fundamentals 欄位優先級：Finviz > Finnhub > Alpha Vantage
        3. Advanced 欄位優先級：IBKR Tick（獨佔）
        4. 禁止 Finviz/IBKR 覆蓋 Finnhub 的 current_price
        5. 記錄每個欄位的實際來源
        
        參數:
            quote: Quote 數據（來自 get_stock_quote_primary）
            fundamentals: Fundamentals 數據（來自 get_stock_fundamentals_primary）
            advanced: Advanced 數據（來自 get_stock_advanced_from_ibkr）
        
        返回:
            Dict: 完整的股票快照，包含 field_sources metadata
        
        Ref: option-data-review.md Section II.2
        """
        from data_layer.data_policy import DataSource, StockSnapshotSchema, assess_data_quality, STOCK_QUOTE_REQUIRED_FIELDS
        
        if not any([quote, fundamentals, advanced]):
            logger.error("x merge_stock_snapshot: 所有輸入都為 None")
            return None
        
        snapshot: StockSnapshotSchema = {}
        field_sources: Dict[str, str] = {}
        
        # 合併 Quote 數據
        if quote:
            for key, value in quote.items():
                if key not in ['data_source', 'data_timestamp', 'is_market_hours'] and value is not None:
                    snapshot[key] = value
                    field_sources[key] = quote.get('data_source', DataSource.UNKNOWN)
            
            # 保留 metadata
            if 'data_timestamp' in quote:
                snapshot['data_timestamp'] = quote['data_timestamp']
            if 'is_market_hours' in quote:
                snapshot['is_market_hours'] = quote['is_market_hours']
        
        # 合併 Fundamentals 數據（不覆蓋 Quote 欄位）
        if fundamentals:
            for key, value in fundamentals.items():
                if key not in ['data_source', 'ticker'] and value is not None:
                    # 只在欄位不存在時才添加
                    if key not in snapshot:
                        snapshot[key] = value
                        field_sources[key] = fundamentals.get('data_source', DataSource.UNKNOWN)
        
        # 合併 Advanced 數據（IBKR 專屬欄位）
        if advanced:
            for key, value in advanced.items():
                if key not in ['data_source', 'ticker', 'hv_source', 'div_source'] and value is not None:
                    snapshot[key] = value
                    field_sources[key] = advanced.get('data_source', DataSource.UNKNOWN)
        
        # 添加 metadata
        snapshot['field_sources'] = field_sources
        snapshot['data_quality'] = assess_data_quality(snapshot, STOCK_QUOTE_REQUIRED_FIELDS)
        
        logger.info(f"* 合併股票快照完成，數據質量: {snapshot['data_quality']}")
        logger.debug(f"  欄位來源: {field_sources}")
        
        return snapshot
    
    # ========================================================================
    # 原有的 get_stock_info（保留以保持向後兼容）
    # 未來將逐步遷移到新的 get_stock_quote_primary + merge_stock_snapshot
    # ========================================================================
    
    def get_stock_info(self, ticker):
        """
        獲取股票基本信息（支持多数据源降级）
        
        降級順序: Finnhub（實時） → Alpha Vantage → Finviz → Yahoo Finance → yfinance
        
        注意: IBKR 不用於股票價格獲取，只用於期權數據（OPRA 實時數據）
              這樣可以避免 IBKR 延遲數據的問題，同時利用 Finnhub 的免費實時報價
        
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
        
        # 方案1: Finnhub（實時股價，最高優先級）
        # 注意: IBKR 只用於期權數據，股票價格優先使用 Finnhub 免費實時報價
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
                    
                    from datetime import datetime as _dt
                    stock_data = {
                        'ticker': ticker,
                        'current_price': quote.get('c', 0),  # current price
                        'open': quote.get('o', 0),  # open
                        # Fix: 改名 intraday_high/low，明確這是盤中未結算值（非歷史已確定值）
                        # 避免下游 ML/HV 計算誤用未結算盤中數據（倒推風險）
                        'intraday_high': quote.get('h', 0),   # ⚠️ 盤中最高（未結算）
                        'intraday_low': quote.get('l', 0),    # ⚠️ 盤中最低（未結算）
                        'high': quote.get('h', 0),            # 向後兼容保留
                        'low': quote.get('l', 0),             # 向後兼容保留
                        'previous_close': quote.get('pc', 0),  # previous close
                        'change': quote.get('d', 0),          # change
                        'change_percent': quote.get('dp', 0), # change percent
                        'volume': None,  # Finnhub quote 不提供 volume
                        'data_source': 'Finnhub',
                        'is_market_hours': True,              # 標記為盤中數據
                        'data_timestamp': _dt.now().isoformat(),  # 記錄抓取時間
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
                    # 不提早返回，留到後面合併 IBKR 數據
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
                    # 不提早返回
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
                        # 不提早返回
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
        
        # 如果前面都失敗了，才完全依賴 IBKR
        if not stock_data and self.use_ibkr and self.ibkr_client and self.ibkr_client.is_connected():
            try:
                logger.info("  使用 IBKR 獲取股價與進階Tick...")
                ibkr_data = self.ibkr_client.get_stock_full_data(ticker)
                
                if ibkr_data and ibkr_data.get('price') and ibkr_data['price'] > 0:
                    price = ibkr_data['price']
                    stock_data = {
                        'ticker': ticker,
                        'current_price': price,
                        'open': price, # 暫時用當前價代替
                        'high': price, 
                        'low': price,
                        'dividend_rate': ibkr_data.get('dividend_yield', 0),
                        'historical_volatility': ibkr_data.get('historical_volatility', 0) * 100 if ibkr_data.get('historical_volatility') else None,
                        'mark_price': ibkr_data.get('mark_price'),
                        'data_source': 'IBKR'
                    }
                    logger.info(f"* 成功獲取 {ticker} 基本信息 (IBKR)")
                    logger.info(f"  當前股價: ${price:.2f}")
                    self._record_fallback('stock_info', 'IBKR')
                else:
                    logger.warning("! IBKR 返回無效股價")
            except Exception as e:
                logger.warning(f"! IBKR 獲取股價失敗: {e}")
                
        # 最終合併 IBKR 的高級數據防護網 (HV, Dividends, MarkPrice)
        if stock_data and self.use_ibkr and stock_data.get('data_source') != 'IBKR':
            try:
                ibkr_data = self.ibkr_client.get_stock_full_data(ticker)
                if ibkr_data:
                    if 'dividend_rate' not in stock_data or not stock_data['dividend_rate']:
                        stock_data['dividend_rate'] = ibkr_data.get('dividend_yield', 0)
                    if 'historical_volatility' not in stock_data or not stock_data['historical_volatility']:
                        stock_data['historical_volatility'] = ibkr_data.get('historical_volatility', 0) * 100 if ibkr_data.get('historical_volatility') else None
                    if 'mark_price' not in stock_data or not stock_data['mark_price']:
                        stock_data['mark_price'] = ibkr_data.get('mark_price', stock_data.get('mark_price'))
            except Exception as e:
                logger.debug(f"合併 IBKR 進階 Tick 時發生錯誤: {e}")

        # 如果前面的主要來源都成功了，返回結果
        if stock_data:
            return stock_data
        
        # 方案4: 降级到 Massive API（前面都失敗時才使用）
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
            stock = yf.Ticker(ticker, session=self.session)
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
        
        # 最終檢查: 如果所有來源都失敗
        logger.error(f"x 無法獲取 {ticker} 基本信息 (所有來源失敗)")
        self._record_fallback_failure('stock_info', 'All Sources', '全部失敗')
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
            stock = yf.Ticker(ticker, session=self.session)
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
        獲取所有期權到期日期 (增強版：IBKR 優先)
        
        策略:
        1. 優先使用 IBKR (reqSecDefOptParams)
        2. 如果失敗，回退到 YahooFinanceV2Client
        3. 如果失敗，回退到 yfinance (已打補丁)
        
        參數:
            ticker: 股票代碼
        
        返回: list of str (格式: YYYY-MM-DD)
        """
        try:
            self._rate_limit_delay()
            logger.info(f"開始獲取 {ticker} 期權到期日期...")
            
            # 使用標準標示符
            ticker_normalized = self._normalize_ticker(ticker) or ticker
            
            # 方案 1: IBKR (最優先)
            if self.use_ibkr and self.ibkr_client and self.ibkr_client.is_connected():
                try:
                    logger.info("  使用 IBKR API...")
                    expirations = self.ibkr_client.get_option_expirations(ticker_normalized)
                    
                    if expirations and len(expirations) > 0:
                        logger.info(f"✓ 成功獲取 {ticker} 的 {len(expirations)} 個到期日期 (IBKR)")
                        self._record_fallback('option_expirations', 'ibkr')
                        return expirations
                    else:
                        logger.warning("! IBKR 獲取到期日列表為空，嘗試備用方案")
                        self._record_fallback_failure('option_expirations', 'ibkr', '返回空列表')
                except Exception as e:
                    logger.warning(f"! IBKR 獲取到期日失敗: {e}")
                    self._record_api_failure('ibkr', f"get_option_expirations: {e}")
                    self._record_fallback_failure('option_expirations', 'ibkr', str(e))
            
            # 方案 2: Yahoo Finance V2 Client (備用)
            if hasattr(self, 'yahoo_v2_client') and self.yahoo_v2_client:
                try:
                    logger.info("  備用: 嘗試使用 Yahoo Finance V2 API...")
                    expirations_raw = self.yahoo_v2_client.get_available_expirations(ticker_normalized)
                    
                    if expirations_raw:
                        # 轉換 Unix 時間戳為 YYYY-MM-DD
                        expirations = []
                        for ts in expirations_raw:
                            try:
                                # Yahoo 返回的是 UTC 時間戳
                                expirations.append(datetime.fromtimestamp(ts).strftime('%Y-%m-%d'))
                            except:
                                continue
                        
                        if expirations:
                            logger.info(f"✓ 成功獲取 {ticker} 的 {len(expirations)} 個到期日期 (Yahoo V2)")
                            self._record_fallback('option_expirations', 'yahoo_v2')
                            return sorted(list(set(expirations)))
                except Exception as e:
                    logger.warning(f"! Yahoo V2 獲取到期日失敗: {e}")
                    self._record_api_failure('Yahoo V2', f"get_option_expirations: {e}")
            
            # 方案 3: yfinance (最後備用)
            try:
                logger.info("  備用: 嘗試使用 yfinance (已打補丁)...")
                stock = yf.Ticker(ticker_normalized, session=self.session)
                expirations = stock.options
                
                if expirations:
                    logger.info(f"✓ 成功獲取 {ticker} 的 {len(expirations)} 個到期日期 (yfinance)")
                    self._record_fallback('option_expirations', 'yfinance')
                    return list(expirations)
            except Exception as e:
                logger.warning(f"! yfinance 獲取到期日失敗: {e}")
                self._record_api_failure('yfinance', f"get_option_expirations: {e}")
                
            logger.error(f"✗ 獲取 {ticker} 所有的期權到期日期均失敗")
            return []
            
        except Exception as ge:
            logger.error(f"✗ get_option_expirations 發生未預期錯誤: {ge}")
            return []
    
    def _merge_ibkr_opra_with_yahoo(self, yahoo_df: pd.DataFrame, ticker: str, 
                                       expiration: str, option_type: str) -> pd.DataFrame:
        """
        整合 IBKR OPRA 實時 bid/ask 數據和 Yahoo Finance 的 IV 數據
        
        數據源分工:
        - IBKR OPRA: bid, ask, volume, openInterest (實時)
        - Yahoo Finance: impliedVolatility, lastPrice, 其他數據
        
        注意: 如果 IBKR 無法返回有效的 bid/ask 數據（例如沒有 OPRA 訂閱），
              會自動跳過整合，保留 Yahoo Finance 的原始數據
        
        參數:
            yahoo_df: Yahoo Finance 的期權 DataFrame
            ticker: 股票代碼
            expiration: 到期日期
            option_type: 'call' 或 'put'
        
        返回:
            DataFrame: 整合後的期權數據
        """
        if yahoo_df.empty or not self.ibkr_client or not self.ibkr_client.is_connected():
            return yahoo_df
        
        logger.info(f"  嘗試整合 IBKR OPRA 實時數據 ({option_type})...")
        
        # 先測試一個期權，看 IBKR 是否能返回有效的 bid/ask
        test_strike = yahoo_df['strike'].iloc[len(yahoo_df) // 2] if 'strike' in yahoo_df.columns else None
        if test_strike is None:
            logger.warning("    無法找到測試行使價，跳過 IBKR 整合")
            return yahoo_df
        
        right = 'C' if option_type.lower() == 'call' else 'P'
        
        try:
            test_quote = self.ibkr_client.get_option_quote(
                ticker=ticker,
                strike=float(test_strike),
                expiration=expiration,
                option_type=right
            )
            
            # 檢查是否有有效的 bid/ask 數據
            has_valid_bid_ask = (
                test_quote and 
                ('bid' in test_quote and test_quote['bid'] is not None and test_quote['bid'] > 0) or
                ('ask' in test_quote and test_quote['ask'] is not None and test_quote['ask'] > 0)
            )
            
            if not has_valid_bid_ask:
                logger.info(f"    IBKR 未返回有效 bid/ask 數據（可能未訂閱 OPRA），跳過整合")
                logger.info(f"    將使用 Yahoo Finance 的 bid/ask 數據")
                return yahoo_df
                
        except Exception as e:
            logger.warning(f"    IBKR OPRA 測試失敗: {e}，跳過整合")
            return yahoo_df
        
        # IBKR 可以返回有效數據，繼續整合
        logger.info(f"    IBKR OPRA 數據可用，開始整合...")
        
        # 限制更新數量，避免過多 API 請求（只更新 ATM 附近的期權）
        max_updates = 10
        updated_count = 0
        failed_count = 0
        
        for idx, row in yahoo_df.iterrows():
            if updated_count >= max_updates:
                break
            
            # 如果連續失敗太多次，停止嘗試
            if failed_count >= 3:
                logger.info(f"    連續失敗 {failed_count} 次，停止 IBKR 整合")
                break
            
            strike = row.get('strike')
            if strike is None:
                continue
            
            # 跳過已經測試過的行使價
            if strike == test_strike:
                # 使用測試結果
                if 'bid' in test_quote and test_quote['bid'] is not None:
                    yahoo_df.at[idx, 'bid'] = test_quote['bid']
                if 'ask' in test_quote and test_quote['ask'] is not None:
                    yahoo_df.at[idx, 'ask'] = test_quote['ask']
                if 'volume' in test_quote and test_quote['volume'] is not None:
                    yahoo_df.at[idx, 'volume'] = test_quote['volume']
                if 'mid' in test_quote and test_quote['mid'] is not None:
                    yahoo_df.at[idx, 'mid'] = test_quote['mid']
                yahoo_df.at[idx, 'bid_ask_source'] = 'ibkr_opra'
                updated_count += 1
                continue
            
            try:
                # 獲取 IBKR OPRA 實時報價
                opra_quote = self.ibkr_client.get_option_quote(
                    ticker=ticker,
                    strike=float(strike),
                    expiration=expiration,
                    option_type=right
                )
                
                if opra_quote:
                    has_data = False
                    # 用 IBKR OPRA 的實時數據覆蓋 Yahoo Finance 的數據
                    if 'bid' in opra_quote and opra_quote['bid'] is not None and opra_quote['bid'] > 0:
                        yahoo_df.at[idx, 'bid'] = opra_quote['bid']
                        has_data = True
                    if 'ask' in opra_quote and opra_quote['ask'] is not None and opra_quote['ask'] > 0:
                        yahoo_df.at[idx, 'ask'] = opra_quote['ask']
                        has_data = True
                    if 'volume' in opra_quote and opra_quote['volume'] is not None:
                        yahoo_df.at[idx, 'volume'] = opra_quote['volume']
                    if 'mid' in opra_quote and opra_quote['mid'] is not None:
                        yahoo_df.at[idx, 'mid'] = opra_quote['mid']
                    
                    if has_data:
                        yahoo_df.at[idx, 'bid_ask_source'] = 'ibkr_opra'
                        updated_count += 1
                        failed_count = 0  # 重置失敗計數
                    else:
                        failed_count += 1
                else:
                    failed_count += 1
                    
            except Exception as e:
                logger.debug(f"  獲取 {strike} {right} OPRA 報價失敗: {e}")
                failed_count += 1
                continue
        
        if updated_count > 0:
            logger.info(f"    已更新 {updated_count} 個期權的 IBKR OPRA 實時 bid/ask")
        else:
            logger.info(f"    未能更新任何期權的 bid/ask，將使用 Yahoo Finance 數據")
        
        return yahoo_df
    
    def get_option_chain(self, ticker, expiration, strike_range_pct=30):
        """
        獲取完整期權鏈（整合多數據源）- 優化內存使用
        
        數據整合策略 (No-Yahoo Mode):
        1. IBKR OPRA (優先): 使用智能快照獲取期權鏈結構及實時數據 (Price + Greeks)
        2. RapidAPI (備用): 如果配置了 RapidAPI
        3. 失敗: 返回空數據 (不再使用 Yahoo Finance)
        
        數據源分工:
        - 股票價格: Finnhub (實時)
        - 期權數據: IBKR (Snapshot)
        
        參數:
            ticker: 股票代碼
            expiration: 到期日期 (YYYY-MM-DD格式)
            strike_range_pct: 行使價過濾範圍百分比 (默認 30%)，只獲取 ATM ± strike_range_pct% 的行使價
        
        返回: dict
        {
            'calls': DataFrame,
            'puts': DataFrame,
            'expiration': str,
            'data_source': str
        }
        """
        import gc
        
        logger.info(f"開始獲取 {ticker} {expiration} 期權鏈 (IBKR First, 行使價範圍: ±{strike_range_pct}%)...")
        
        # 0. 獲取當前股價（用於過濾期權鏈）
        current_price = 0
        stock_info = self.get_stock_info(ticker)
        if stock_info:
            current_price = stock_info.get('current_price', 0)
        
        # 計算行使價過濾範圍
        strike_min = current_price * (1 - strike_range_pct / 100) if current_price > 0 else 0
        strike_max = current_price * (1 + strike_range_pct / 100) if current_price > 0 else float('inf')
        
        logger.info(f"  行使價過濾範圍: ${strike_min:.2f} - ${strike_max:.2f} (中心: ${current_price:.2f})")
        
        # 1. IBKR 方案 (優先)
        if self.use_ibkr and self.ibkr_client and self.ibkr_client.is_connected():
            try:
                logger.info(f"  使用 IBKR Snapshot (Center: {current_price})...")
                
                # 調用新的智能快照方法
                # 如果有股價，則獲取 ATM +/- 30% (擴大一點範圍)
                # 如果無股價，則獲取全部 (center_strike=None)
                chain_data = self.ibkr_client.get_option_chain_snapshot(
                    ticker, 
                    expiration, 
                    center_strike=current_price if current_price > 0 else None
                )
                
                if chain_data and (chain_data['calls'] or chain_data['puts']):
                    calls_df = pd.DataFrame(chain_data['calls'])
                    puts_df = pd.DataFrame(chain_data['puts'])
                    
                    # 應用行使價過濾
                    if not calls_df.empty and 'strike' in calls_df.columns and current_price > 0:
                        original_count = len(calls_df)
                        calls_df = calls_df[(calls_df['strike'] >= strike_min) & (calls_df['strike'] <= strike_max)]
                        logger.info(f"  Call 期權過濾: {original_count} -> {len(calls_df)} 個")
                    
                    if not puts_df.empty and 'strike' in puts_df.columns and current_price > 0:
                        original_count = len(puts_df)
                        puts_df = puts_df[(puts_df['strike'] >= strike_min) & (puts_df['strike'] <= strike_max)]
                        logger.info(f"  Put 期權過濾: {original_count} -> {len(puts_df)} 個")
                    
                    # 優化數據類型以減少內存使用
                    calls_df = self._optimize_dataframe_memory(calls_df)
                    puts_df = self._optimize_dataframe_memory(puts_df)
                    
                    if not calls_df.empty or not puts_df.empty:
                        logger.info(f"* 成功獲取 {ticker} {expiration} 期權鏈 (IBKR Snapshot)")
                        logger.info(f"  Call期權: {len(calls_df)} 個")
                        logger.info(f"  Put期權: {len(puts_df)} 個")
                        
                        # 清理內存
                        gc.collect()
                        
                        return {
                            'calls': calls_df,
                            'puts': puts_df,
                            'expiration': expiration,
                            'data_source': 'ibkr_snapshot'
                        }
                    else:
                        logger.warning("! IBKR 返回了空數據結構")
                else:
                    logger.warning("! IBKR 獲取期權鏈快照失敗")
                    
            except Exception as e:
                logger.error(f"x IBKR 獲取期權鏈失敗: {e}")
                
        # 2. RapidAPI
        # ... (保留 RapidAPI 作為備用) ...
        # [原有 RapidAPI 邏輯]
         
        # [已移除 Yahoo Finance 邏輯]
        
        # 方案3: 降級到 yfinance
        try:
            self._rate_limit_delay()
            logger.info("  使用 yfinance...")
            stock = yf.Ticker(ticker, session=self.session)
            option_chain = stock.option_chain(expiration)
            
            calls = option_chain.calls.copy()
            puts = option_chain.puts.copy()
            
            # 應用行使價過濾
            if not calls.empty and 'strike' in calls.columns and current_price > 0:
                original_count = len(calls)
                calls = calls[(calls['strike'] >= strike_min) & (calls['strike'] <= strike_max)]
                logger.info(f"  Call 期權過濾: {original_count} -> {len(calls)} 個")
                
                # 每處理 50 個行使價記錄進度
                if len(calls) > 50:
                    for i in range(0, len(calls), 50):
                        logger.info(f"  處理 Call 期權: {i}/{len(calls)}")
            
            if not puts.empty and 'strike' in puts.columns and current_price > 0:
                original_count = len(puts)
                puts = puts[(puts['strike'] >= strike_min) & (puts['strike'] <= strike_max)]
                logger.info(f"  Put 期權過濾: {original_count} -> {len(puts)} 個")
                
                # 每處理 50 個行使價記錄進度
                if len(puts) > 50:
                    for i in range(0, len(puts), 50):
                        logger.info(f"  處理 Put 期權: {i}/{len(puts)}")
            
            # Task 17.3: Use simplified IVNormalizer.normalize() method and add metadata
            if 'impliedVolatility' in calls.columns and not calls.empty:
                sample_iv_before = calls['impliedVolatility'].iloc[0] if not calls.empty else None
                logger.debug(f"  yfinance Call IV 原始值樣本: {sample_iv_before}")
                
                # Apply normalization and add metadata
                def normalize_with_metadata(x, ticker_symbol):
                    if pd.notna(x):
                        normalized = IVNormalizer.normalize(x, source='Yahoo', ticker=ticker_symbol)
                        return normalized
                    return None
                
                calls['impliedVolatility'] = calls['impliedVolatility'].apply(
                    lambda x: normalize_with_metadata(x, ticker)
                )
                
                # Add IV metadata column
                calls['iv_metadata'] = calls['impliedVolatility'].apply(
                    lambda x: {
                        'original_value': sample_iv_before,
                        'normalized_value': x,
                        'source': 'Yahoo',
                        'format_detected': 'decimal' if sample_iv_before and 0 < sample_iv_before < 1.0 else 'percentage'
                    } if x is not None else None
                )
                
                sample_iv_after = calls['impliedVolatility'].iloc[0] if not calls.empty else None
                logger.debug(f"  yfinance Call IV 標準化後樣本: {sample_iv_after}%")
            
            if 'impliedVolatility' in puts.columns and not puts.empty:
                sample_iv_before = puts['impliedVolatility'].iloc[0] if not puts.empty else None
                
                puts['impliedVolatility'] = puts['impliedVolatility'].apply(
                    lambda x: normalize_with_metadata(x, ticker)
                )
                
                # Add IV metadata column
                puts['iv_metadata'] = puts['impliedVolatility'].apply(
                    lambda x: {
                        'original_value': sample_iv_before,
                        'normalized_value': x,
                        'source': 'Yahoo',
                        'format_detected': 'decimal' if sample_iv_before and 0 < sample_iv_before < 1.0 else 'percentage'
                    } if x is not None else None
                )
            
            # 優化數據類型以減少內存使用
            calls = self._optimize_dataframe_memory(calls)
            puts = self._optimize_dataframe_memory(puts)
            
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
                
                # 整合 IBKR OPRA 實時 bid/ask 數據（如果可用）
                ibkr_available = self.use_ibkr and self.ibkr_client and self.ibkr_client.is_connected()
                if ibkr_available:
                    calls = self._merge_ibkr_opra_with_yahoo(calls, ticker, expiration, 'call')
                    puts = self._merge_ibkr_opra_with_yahoo(puts, ticker, expiration, 'put')
                    data_source = 'yfinance+ibkr_opra'
                else:
                    data_source = 'yfinance'
                
                self._record_fallback('option_chain', data_source)
                
                # 填補缺失的 bid/ask 數據（對於沒有 IBKR 數據的期權）
                calls = self._fill_missing_bid_ask(calls, 'call')
                puts = self._fill_missing_bid_ask(puts, 'put')
                
                # 清理內存
                gc.collect()
                
                return {
                    'calls': calls,
                    'puts': puts,
                    'expiration': expiration,
                    'data_source': data_source
                }
            else:
                # 數據不完整，嘗試 RapidAPI
                logger.warning("! yfinance 返回的期權數據 lastPrice 大部分為 0，嘗試 RapidAPI")
                self._record_fallback_failure('option_chain', 'yfinance', 'lastPrice 大部分為 0')
            
        except Exception as e:
            logger.error(f"x yfinance 獲取期權鏈失敗: {e}")
            self._record_api_failure('yfinance', f"get_option_chain: {str(e)}")
            self._record_fallback_failure('option_chain', 'yfinance', str(e))
        
        # 方案4: 嘗試 RapidAPI (如果啟用)
        # 這裡為了代碼簡潔，直接復用原有 RapidAPI 代碼塊 (需要確保前面的 indent 正確)
        if hasattr(self, 'rapidapi_client') and self.rapidapi_client:
            # ... (復用之前的邏輯)
            try:
                logger.info("  使用 RapidAPI (增強版)...")
                result = self.rapidapi_client.get_option_chain_enhanced(ticker, expiration)
                if result:
                    return result # 直接返回，假設格式正確
            except Exception as e:
                logger.error(f"RapidAPI 失敗: {e}")

        # 最終失敗
        logger.warning(f"! 無法從任何可用來源 (IBKR/RapidAPI) 獲取期權鏈")
        self._record_fallback('option_chain', 'empty')
        
        # 清理內存
        gc.collect()
        
        return {
            'calls': pd.DataFrame(),
            'puts': pd.DataFrame(),
            'expiration': expiration,
            'data_source': 'Empty (Yahoo Removed)'
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
                stock = yf.Ticker(ticker, session=self.session)
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
            stock = yf.Ticker(ticker, session=self.session)
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
            stock = yf.Ticker(ticker, session=self.session)
            
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
    
    def get_dividend_yield(self, ticker: str) -> float:
        """
        獲取年化股息率（支持多數據源降級）
        
        數據來源優先級:
        1. Yahoo Finance: info['dividendYield']（最優先，直接提供年化股息率）
        2. Finviz: fundamentals['dividend_yield']（降級方案）
        3. 計算方式: annual_dividend / current_price（最後降級）
        
        參數:
            ticker: 股票代碼
        
        返回:
            float: 年化股息率（小數形式，如 0.025 表示 2.5%）
                   如果無股息或獲取失敗，返回 0.0
        
        示例:
            >>> fetcher = DataFetcher()
            >>> # 高股息股票（如 KO）
            >>> div_yield = fetcher.get_dividend_yield('KO')
            >>> print(f"KO 股息率: {div_yield*100:.2f}%")
            
            >>> # 無股息股票（如 TSLA）
            >>> div_yield = fetcher.get_dividend_yield('TSLA')
            >>> print(f"TSLA 股息率: {div_yield*100:.2f}%")  # 應該是 0.00%
        
        注意:
            - 返回值已經是小數形式（如 0.03 表示 3%），無需再除以 100
            - 對於無股息股票，返回 0.0
            - 如果所有數據源都失敗，返回 0.0 並記錄警告
        """
        try:
            logger.info(f"開始獲取 {ticker} 股息率...")
            
            # 方法1: Yahoo Finance info['dividendYield']（最優先）
            try:
                stock = yf.Ticker(ticker, session=self.session)
                info = stock.info
                
                if 'dividendYield' in info and info['dividendYield'] is not None:
                    dividend_yield = float(info['dividendYield'])
                    
                    # Yahoo Finance 的 dividendYield 已經是小數形式（如 0.03 表示 3%）
                    if 0 <= dividend_yield <= 0.2:  # 合理範圍檢查（0% - 20%）
                        logger.info(f"* {ticker} 股息率: {dividend_yield*100:.2f}% (來源: Yahoo Finance)")
                        self._record_fallback('dividend_yield', 'Yahoo Finance', success=True)
                        return dividend_yield
                    else:
                        logger.warning(f"! Yahoo Finance 股息率超出合理範圍: {dividend_yield*100:.2f}%")
                
            except Exception as e:
                logger.debug(f"Yahoo Finance 股息率獲取失敗: {e}")
                self._record_fallback('dividend_yield', 'Yahoo Finance', success=False, error_reason=str(e))
            
            # 方法2: Finviz fundamentals['dividend_yield']（降級方案）
            if self.finviz_scraper:
                try:
                    fundamentals = self.finviz_scraper.get_fundamentals(ticker)
                    
                    if fundamentals and 'dividend_yield' in fundamentals:
                        div_yield_str = fundamentals['dividend_yield']
                        
                        # Finviz 返回格式: "3.25%" 或 "-"
                        if div_yield_str and div_yield_str != '-':
                            # 移除 % 符號並轉換為小數
                            dividend_yield = float(div_yield_str.rstrip('%')) / 100
                            
                            if 0 <= dividend_yield <= 0.2:
                                logger.info(f"* {ticker} 股息率: {dividend_yield*100:.2f}% (來源: Finviz)")
                                self._record_fallback('dividend_yield', 'Finviz', success=True)
                                return dividend_yield
                        else:
                            logger.debug(f"Finviz 顯示 {ticker} 無股息")
                
                except Exception as e:
                    logger.debug(f"Finviz 股息率獲取失敗: {e}")
                    self._record_fallback('dividend_yield', 'Finviz', success=False, error_reason=str(e))
            
            # 方法3: 計算方式 annual_dividend / current_price（最後降級）
            try:
                # 獲取年度股息
                div_data = self.get_dividends(ticker, years=1)
                
                if div_data and div_data['annual_dividend'] > 0:
                    annual_dividend = div_data['annual_dividend']
                    
                    # 獲取當前股價
                    stock_info = self.get_stock_info(ticker)
                    
                    if stock_info and 'current_price' in stock_info:
                        current_price = stock_info['current_price']
                        
                        if current_price > 0:
                            dividend_yield = annual_dividend / current_price
                            
                            if 0 <= dividend_yield <= 0.2:
                                logger.info(f"* {ticker} 股息率: {dividend_yield*100:.2f}% (來源: 計算)")
                                logger.info(f"  年度股息: ${annual_dividend:.2f}, 當前股價: ${current_price:.2f}")
                                self._record_fallback('dividend_yield', 'Calculated', success=True)
                                return dividend_yield
                            else:
                                logger.warning(f"! 計算的股息率超出合理範圍: {dividend_yield*100:.2f}%")
                
            except Exception as e:
                logger.debug(f"計算股息率失敗: {e}")
                self._record_fallback('dividend_yield', 'Calculated', success=False, error_reason=str(e))
            
            # 所有方法都失敗，返回 0.0
            logger.info(f"* {ticker} 無股息或無法獲取股息率，使用 0.0")
            return 0.0
            
        except Exception as e:
            logger.error(f"x 獲取 {ticker} 股息率失敗: {e}")
            logger.error(traceback.format_exc())
            return 0.0
    
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
                stock = yf.Ticker(ticker, session=self.session)
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
            stock = yf.Ticker(ticker, session=self.session)
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
                    stock = yf.Ticker(ticker, session=self.session)
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
            stock = yf.Ticker(ticker, session=self.session)
            
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
            stock = yf.Ticker(ticker, session=self.session)
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

    # ==================== Task 16: API Degradation Chain and Retry Mechanisms ====================

    # Task 16.1: Enhanced API degradation logic
    FALLBACK_TRIGGERS = [
        ConnectionError,
        TimeoutError,
        Exception,  # Includes HTTPError, DataValidationError, etc.
    ]

    def _fetch_with_fallback(self, data_type: str, sources: List[str], fetch_func_map: Dict[str, callable], *args, **kwargs):
        """
        Fetch data with fallback mechanism through multiple sources.

        Implements the API degradation chain by attempting each data source in priority order.
        Logs each attempt and records failures for diagnostics.

        Args:
            data_type: Type of data being fetched (e.g., 'stock_info', 'option_chain')
            sources: List of data source names in priority order
            fetch_func_map: Dict mapping source names to fetch functions
            *args, **kwargs: Arguments to pass to fetch functions

        Returns:
            Data from the first successful source, or None if all fail

        Requirements: 1.3, 1.4, 2.3, 2.4, 3.1
        """
        # Initialize attempt path tracking if not exists
        if not hasattr(self, '_attempt_paths'):
            self._attempt_paths = {}

        if data_type not in self._attempt_paths:
            self._attempt_paths[data_type] = {'history': []}

        current_attempt = []

        for source in sources:
            fetch_func = fetch_func_map.get(source)

            if not fetch_func:
                logger.debug(f"  {source}: No fetch function available, skipping")
                continue

            try:
                logger.info(f"Attempting {source} for {data_type}...")

                # Attempt to fetch data
                result = fetch_func(*args, **kwargs)

                if result is not None:
                    # Success
                    logger.info(f"✓ {source} succeeded for {data_type}")
                    current_attempt.append({
                        'source': source,
                        'success': True,
                        'error_reason': None,
                        'timestamp': datetime.now().isoformat()
                    })

                    # Record successful fallback
                    self._record_fallback(data_type, source)

                    # Save attempt history
                    self._attempt_paths[data_type]['history'].append(current_attempt)

                    return result
                else:
                    # Returned None - treat as failure
                    error_msg = "Returned None or empty data"
                    logger.warning(f"{source} failed: {error_msg}, trying next source...")

                    current_attempt.append({
                        'source': source,
                        'success': False,
                        'error_reason': error_msg,
                        'timestamp': datetime.now().isoformat()
                    })

                    self._record_fallback_failure(data_type, source, error_msg)

            except Exception as e:
                # Exception occurred
                error_type = type(e).__name__
                error_message = str(e)
                full_error = f"{error_type} - {error_message}"

                logger.warning(f"{source} failed: {full_error}, trying next source...")

                current_attempt.append({
                    'source': source,
                    'success': False,
                    'error_reason': full_error,
                    'timestamp': datetime.now().isoformat()
                })

                # Record API failure
                self._record_api_failure(source, error_message, operation=f'fetch_{data_type}')
                self._record_fallback_failure(data_type, source, full_error)

        # All sources failed
        logger.error(f"✗ All sources failed for {data_type}")
        self._attempt_paths[data_type]['history'].append(current_attempt)

        return None

    def _record_fallback(self, data_type: str, source: str):
        """
        Record successful fallback usage.

        Args:
            data_type: Type of data (e.g., 'stock_info')
            source: Data source name
        """
        if data_type not in self.fallback_used:
            self.fallback_used[data_type] = []

        self.fallback_used[data_type].append({
            'source': source,
            'timestamp': datetime.now().isoformat()
        })

    def _record_fallback_failure(self, data_type: str, source: str, reason: str):
        """
        Record fallback attempt failure.

        Args:
            data_type: Type of data
            source: Data source name
            reason: Failure reason
        """
        # This is already recorded in _attempt_paths by _fetch_with_fallback
        pass

    # Task 16.2: Intelligent retry mechanism with exponential backoff
    def _retry_with_backoff(self, func: callable, max_retries: int = 3, base_delay: float = 2.0, *args, **kwargs):
        """
        Retry a function with exponential backoff.

        Implements intelligent retry logic with exponential backoff for transient errors.
        Special handling for 429 (rate limit) errors.

        Args:
            func: Function to retry
            max_retries: Maximum number of retry attempts
            base_delay: Base delay in seconds (default 2.0)
            *args, **kwargs: Arguments to pass to the function

        Returns:
            Result from successful function call

        Raises:
            Exception: After max retries exceeded

        Requirements: 1.8, 2.8, 3.12
        """
        import requests

        for attempt in range(1, max_retries + 1):
            try:
                return func(*args, **kwargs)

            except requests.exceptions.HTTPError as e:
                if hasattr(e, 'response') and e.response is not None and e.response.status_code == 429:
                    # Rate limit error - use exponential backoff
                    if attempt < max_retries:
                        delay = min(base_delay * (2 ** (attempt - 1)), 60)
                        logger.warning(f"Rate limit hit, retrying in {delay}s... (attempt {attempt}/{max_retries})")
                        time.sleep(delay)
                    else:
                        logger.error(f"Max retries exceeded after {max_retries} attempts")
                        raise Exception(f"MaxRetriesExceeded: Failed after {max_retries} attempts due to rate limiting")
                else:
                    # Other HTTP error - don't retry
                    raise

            except (ConnectionError, TimeoutError) as e:
                # Transient network errors - retry with backoff
                if attempt < max_retries:
                    delay = min(base_delay * (2 ** (attempt - 1)), 60)
                    logger.warning(f"Network error, retrying in {delay}s... (attempt {attempt}/{max_retries}): {e}")
                    time.sleep(delay)
                else:
                    logger.error(f"Max retries exceeded after {max_retries} attempts")
                    raise Exception(f"MaxRetriesExceeded: Failed after {max_retries} attempts due to network errors")

            except Exception as e:
                # Other exceptions - don't retry
                raise

        # Should not reach here
        raise Exception(f"MaxRetriesExceeded: Failed after {max_retries} attempts")



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
