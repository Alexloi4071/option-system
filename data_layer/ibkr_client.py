# data_layer/ibkr_client.py
"""
Interactive Brokers (IBKR) API 客戶端
支持 TWS 和 IB Gateway 連接

優化功能:
- 動態 Market Data Type 切換 (RTH vs 盤後)
- 完整 Generic Tick Tags 配置
- Greeks 數據收斂等待機制
- Underlying Price 驗證
- 數據質量評估
- 增強錯誤處理
"""

import logging
import time
import os
from typing import Dict, Optional, Any, List, TypedDict
from datetime import datetime, time as dt_time
import pytz

logger = logging.getLogger(__name__)

# ============================================================================
# TypedDict Definitions for Option Data Structures
# ============================================================================

class OptionGreeksData(TypedDict, total=False):
    """
    TypedDict for option Greeks data returned by get_option_greeks()
    
    This structure ensures consistent return types and provides type hints
    for downstream modules.
    """
    # Contract identification
    strike: float
    expiration: str
    option_type: str
    
    # Greeks
    delta: Optional[float]
    gamma: Optional[float]
    theta: Optional[float]
    vega: Optional[float]
    rho: Optional[float]
    
    # Volatility and prices
    impliedVol: Optional[float]
    undPrice: Optional[float]
    optPrice: Optional[float]
    
    # Quote data
    bid: Optional[float]
    ask: Optional[float]
    last: Optional[float]
    mid: Optional[float]
    
    # Volume and open interest
    volume: Optional[int]
    openInterest: Optional[int]
    
    # Metadata
    source: str
    greeks_source: str
    data_quality: str
    market_data_type: int
    outside_rth: bool
    greeks_converged: bool
    convergence_time: Optional[float]
    undPrice_valid: Optional[bool]
    
    # Warnings and quality indicators
    warnings: List[str]
    iv_spike_warning: Optional[bool]
    
    # Additional metadata
    metadata: Optional[Dict[str, Any]]
    iv_metadata: Optional[Dict[str, Any]]


class OptionQuoteData(TypedDict, total=False):
    """
    TypedDict for option quote data returned by get_option_quote()
    
    This structure ensures consistent return types for option quotes.
    """
    # Contract identification
    strike: float
    expiration: str
    option_type: str
    
    # Quote data
    bid: Optional[float]
    ask: Optional[float]
    last: Optional[float]
    mid: Optional[float]
    markPrice: Optional[float]
    
    # Volume and open interest
    volume: Optional[int]
    openInterest: Optional[int]
    
    # Greeks (if available)
    delta: Optional[float]
    gamma: Optional[float]
    theta: Optional[float]
    vega: Optional[float]
    impliedVolatility: Optional[float]
    undPrice: Optional[float]
    optPrice: Optional[float]
    greeks_source: Optional[str]
    
    # Metadata
    data_source: str
    data_quality: str
    market_data_type: int
    outside_rth: bool
    tick_tags_used: str
    
    # Warnings
    warnings: List[str]
    iv_spike_warning: Optional[bool]

# ============================================================================
# Market Data Type 常量
# ============================================================================
MARKET_DATA_TYPE_LIVE = 1           # 實時數據 (RTH 期間使用)
MARKET_DATA_TYPE_FROZEN = 2         # 凍結數據 (盤後使用，返回收盤價)
MARKET_DATA_TYPE_DELAYED = 3        # 延遲數據 (15-20分鐘延遲)
MARKET_DATA_TYPE_DELAYED_FROZEN = 4 # 延遲凍結數據

# ============================================================================
# RTH (Regular Trading Hours) 時間定義 - 美東時間
# ============================================================================
RTH_START = dt_time(9, 30)   # 09:30 ET
RTH_END = dt_time(16, 0)     # 16:00 ET
ET_TIMEZONE = pytz.timezone('America/New_York')

# ============================================================================
# Greeks 收斂參數
# ============================================================================
GREEKS_INITIAL_TIMEOUT = 10      # 初始等待時間（秒）
GREEKS_STABILIZATION_TIMEOUT = 3 # 穩定等待時間（秒）
GREEKS_STABILITY_TOLERANCE = 0.001  # Greeks 穩定性容差

# ============================================================================
# 價格驗證參數
# ============================================================================
PRICE_MISMATCH_THRESHOLD = 0.01  # 1% 價格偏差閾值
IV_SPIKE_THRESHOLD = 3.0         # 300% IV 異常閾值

# ============================================================================
# 錯誤處理參數
# ============================================================================
MAX_RECENT_ERRORS = 50
BACKOFF_BASE = 2.0
BACKOFF_MAX = 60.0

# ============================================================================
# Dark Pool 數據常量
# ============================================================================
DARK_POOL_TICK_TAGS   = '233,375'       # Tick 48 (rtVolume) + Tick 77 (rtTradeVolume)
DARK_POOL_VWAP_TAG    = '258'           # Tick 74 (VWAP) - 備用
DARK_POOL_EXCHANGE    = 'D'             # FINRA ADF / Dark Pool
DARK_POOL_BLOCK_SIZE  = 10_000          # 大單門檻（股數）

# ============================================================================
# Generic Tick Tags 完整配置
# 參考: https://interactivebrokers.github.io/tws-api/tick_types.html
# ============================================================================
TICK_TAGS_CONFIG = {
    'CORE': {
        # 期權交易核心數據 - 適用於股票和期權
        '100': 'Option Call/Put Volume (Tick 29,30)',
        '101': 'Option Call/Put Open Interest (Tick 27,28)',
        '104': 'Option Historical Volatility 30-day (Tick 23)',
        '106': 'Option Implied Volatility 30-day (Tick 24)',
    },
    'RECOMMENDED': {
        # 推薦的額外數據 - 適用於股票和期權
        '105': 'Average Option Volume (Tick 87)',
        '165': '52-Week High/Low + 90-day Avg Volume (Tick 15-21)',
        '232': 'Mark Price - Theoretical calculated value (Tick 37)',
        '233': 'RT Volume / Time & Sales (Tick 48) - 異動大單監測',
        '236': 'Shortable status + Shortable Shares (Tick 46,89) - 做空可用性',
    },
    'ADVANCED_OPTION_SAFE': {
        # 進階分析數據 - 適用於期權（排除新聞相關標籤）
        # '225': 'Auction Data - Volume/Price/Imbalance (Tick 34-36,61)',  # 需要額外訂閱，Paper Trading 不可用
        '293': 'Trade Count for the day (Tick 54)',
        '294': 'Trade Rate per minute (Tick 55)',
        '295': 'Volume Rate per minute (Tick 56)',
        '318': 'Last RTH Trade price (Tick 57)',
        '375': 'RT Trade Volume excluding unreportable (Tick 77)',
        '411': 'RT Historical Volatility 30-day (Tick 58)',
        '456': 'IB Dividends info (Tick 59)',
        '595': 'Short-Term Volume 3/5/10 minutes (Tick 63-65)',
    },
    'STOCK_ONLY': {
        # 僅適用於股票（不能用於期權）
        '292': 'News feed for contract (Tick 62) - 只能用於股票/指數/現金',
    }
}

def build_generic_tick_list(categories: List[str] = None, contract_type: str = 'option') -> str:
    """
    構建 Generic Tick Tags 字符串
    
    參數:
        categories: 要包含的類別列表，默認根據 contract_type 自動選擇
        contract_type: 'stock' 或 'option'，用於排除不適用的標籤
    
    返回:
        str: 逗號分隔的 tick tag 字符串
    """
    if categories is None:
        if contract_type == 'stock':
            # 股票可以使用所有標籤，包括新聞
            categories = ['CORE', 'RECOMMENDED', 'ADVANCED_OPTION_SAFE', 'STOCK_ONLY']
        else:
            # 期權不能使用新聞相關標籤（會導致 Error 10094）
            categories = ['CORE', 'RECOMMENDED', 'ADVANCED_OPTION_SAFE']
    
    tags = []
    for category in categories:
        if category in TICK_TAGS_CONFIG:
            tags.extend(TICK_TAGS_CONFIG[category].keys())
    
    # 按數字排序並去重
    return ','.join(sorted(set(tags), key=int))

# 嘗試導入 ib_insync（IBKR Python API）
try:
    from ib_insync import IB, Stock, Option, Contract, util
    IB_INSYNC_AVAILABLE = True
except ImportError:
    IB_INSYNC_AVAILABLE = False
    # 定義虛擬類以防止 NameError
    class Contract: pass
    class IB: pass
    class Stock: pass
    class Option: pass
    logger.warning("! ib_insync 未安裝，IBKR 功能將不可用。安裝: pip install ib_insync")

# Import dataclass for TickByTickData
from dataclasses import dataclass, field
from typing import Generator


@dataclass
class TickByTickData:
    """
    Tick-by-Tick data structure for real-time market data
    
    Attributes:
        ticker: Stock symbol
        timestamp: Tick timestamp
        price: Trade price
        size: Trade size (shares)
        exchange: Exchange code ('D' for FINRA ADF/dark pools)
        tick_type: Type of tick ('Last', 'AllLast', 'BidAsk', 'MidPoint')
        tick_tags: Dictionary mapping tick tag IDs to values
    """
    ticker: str
    timestamp: datetime
    price: float
    size: int
    exchange: str
    tick_type: str
    tick_tags: Dict[int, Any] = field(default_factory=dict)
    
    def get_tag(self, tag_id: int) -> Any:
        """Get value for a specific tick tag ID"""
        return self.tick_tags.get(tag_id)
    
    def has_tag(self, tag_id: int) -> bool:
        """Check if a specific tick tag exists"""
        return tag_id in self.tick_tags
    
    def has_tags(self, *tag_ids: int) -> bool:
        """Check if all specified tick tags exist"""
        return all(tag_id in self.tick_tags for tag_id in tag_ids)


class IBKRClient:
    """
    Interactive Brokers 客戶端
    
    功能:
    - 連接 TWS 或 IB Gateway
    - 獲取實時期權數據
    - 獲取 Greeks (Delta, Gamma, Theta, Vega, Rho)
    - 獲取實時 Bid/Ask 價差
    - 自動重試和錯誤處理
    - 支持降級到其他數據源
    
    優化功能 (v2.0):
    - 動態 Market Data Type 切換 (RTH vs 盤後)
    - 完整 Generic Tick Tags 配置
    - Greeks 數據收斂等待機制
    - Underlying Price 驗證
    - 數據質量評估
    """
    
    def __init__(self, host: str = "127.0.0.1", port: int = None, 
                 client_id: int = 100, mode: str = 'paper',
                 market_data_type: int = None,
                 tick_tag_categories: List[str] = None,
                 ib_instance=None): # New param
        """
        初始化 IBKR 客戶端
        
        參數:
            ...
            ib_instance: 現有的 IB 實例（用於共享連接）
        """
        if not IB_INSYNC_AVAILABLE:
            raise ImportError("ib_insync 未安裝，無法使用 IBKR 功能")
        
        self.host = host
        # Fix Bug 1.9: Read port from environment variable instead of hardcoded default
        if port is None:
            port = int(os.getenv('IBKR_PORT_PAPER', 4002))
        
        # 驗證端口配置
        common_ports = [4001, 4002, 7496, 7497]
        if port not in common_ports:
            logger.warning(f"! 端口 {port} 不在常見範圍內 {common_ports}")
            logger.warning("  常見端口配置:")
            logger.warning("    4002 - IB Gateway Paper Trading")
            logger.warning("    4001 - IB Gateway Live Trading")
            logger.warning("    7497 - TWS Paper Trading")
            logger.warning("    7496 - TWS Live Trading")
        
        self.port = port
        logger.info(f"Connecting to IBKR Gateway on port {port}")
        
        # 驗證 Client ID 範圍
        if client_id < 0 or client_id > 9999:
            logger.error(f"x Client ID {client_id} 超出有效範圍 (0-9999)")
            logger.warning("  建議使用 1-9999 範圍內的 Client ID")
        elif client_id == 0:
            logger.warning(f"! Client ID 0 是有效的但不推薦使用")
            logger.warning("  建議使用 1-9999 範圍內的 Client ID")
        
        self.client_id = client_id
        self.mode = mode
        self.ib = ib_instance if ib_instance else IB() # Use existing or create new
        self.connected = ib_instance.isConnected() if ib_instance else False
        self.last_error = None
        self.connection_attempts = 0
        self.max_connection_attempts = 3
        
        # 新增: Market Data Type 管理
        self._market_data_type_override = market_data_type
        self._current_market_data_type = None
        
        # 新增: Generic Tick Tags 配置
        # 注意: 默認使用期權安全的標籤（不包含 Tag 292 新聞）
        self._tick_tag_categories = tick_tag_categories or ['CORE', 'RECOMMENDED', 'ADVANCED_OPTION_SAFE']
        self._generic_tick_list = build_generic_tick_list(self._tick_tag_categories, contract_type='option')
        # 為股票準備完整的 tick list（包含新聞）
        self._stock_tick_list = build_generic_tick_list(contract_type='stock')
        
        # 新增: 錯誤追蹤
        self._recent_errors: List[Dict] = []
        
        # 新增: 數據質量追蹤
        self._data_quality_tracker: Dict[str, Any] = {}
        
        # Fix Bug 1.9: Add connection status flag (renamed to avoid conflict with is_connected() method)
        self._connection_verified = False
        
        logger.info(f"IBKR 客戶端初始化: {host}:{port} (mode={mode}, client_id={client_id})")
        logger.info(f"  Generic Tick Tags (期權): {self._generic_tick_list}")
    
    def _test_connection(self) -> bool:
        """
        Test IBKR connection after initialization
        
        Returns:
            bool: True if connected, False otherwise
        """
        try:
            if self.ib and self.ib.isConnected():
                self._connection_verified = True
                logger.info(f"✓ IBKR Gateway connection verified on port {self.port}")
                return True
            else:
                self._connection_verified = False
                logger.warning(f"✗ IBKR Gateway not connected on port {self.port}")
                return False
        except Exception as e:
            self._connection_verified = False
            error_msg = f"IBKR connection test failed: {type(e).__name__} - {str(e)}"
            logger.error(error_msg)
            self._record_error(0, error_msg, '_test_connection')
            return False
    
    def connect(self, timeout: int = 10, market_data_type: int = None) -> bool:
        """
        連接到 TWS/Gateway（帶指數退避重試和動態 Client ID 分配）
        
        參數:
            timeout: 連接超時時間（秒）
            market_data_type: 強制指定 Market Data Type，None 為自動判斷
        
        返回:
            bool: 是否成功連接
        """
        if self.connected:
            logger.info("IBKR 已連接，無需重複連接")
            return True
        
        if not IB_INSYNC_AVAILABLE:
            logger.error("x ib_insync 未安裝，無法連接 IBKR")
            return False
        
        # 指數退避重試參數
        base_delay = 2.0  # 初始等待時間（秒）
        max_delay = 30.0  # 最大等待時間（秒）
        
        # 動態 Client ID 分配參數
        original_client_id = self.client_id
        max_client_id_attempts = 10  # 最多嘗試 10 個不同的 Client ID
        client_id_offset = 0
        
        while self.connection_attempts < self.max_connection_attempts:
            try:
                # 計算當前嘗試的 Client ID
                current_client_id = original_client_id + client_id_offset
                
                # 確保 Client ID 在有效範圍內 (1-9999)
                if current_client_id > 9999:
                    logger.error(f"x Client ID {current_client_id} 超出有效範圍 (1-9999)，無法繼續嘗試")
                    break
                
                if client_id_offset > 0:
                    logger.info(f"  嘗試使用替代 Client ID: {current_client_id} (原始: {original_client_id})")
                
                logger.info(f"嘗試連接 IBKR {self.host}:{self.port} (嘗試 {self.connection_attempts + 1}/{self.max_connection_attempts}, Client ID: {current_client_id})...")
                self.ib.connect(
                    host=self.host,
                    port=self.port,
                    clientId=current_client_id,
                    timeout=timeout
                )
                
                if self.ib.isConnected():
                    self.connected = True
                    self._connection_verified = True  # Fix Bug 1.9: Set connection verified flag
                    self.connection_attempts = 0
                    
                    # 更新實際使用的 Client ID
                    if current_client_id != original_client_id:
                        logger.warning(f"! Client ID {original_client_id} 已被佔用，已自動切換到 Client ID {current_client_id}")
                        self.client_id = current_client_id
                    
                    # 動態設置 Market Data Type
                    self._apply_market_data_type(market_data_type)
                    
                    logger.info(f"* IBKR 連接成功 ({self.mode} mode, Client ID: {current_client_id})")
                    logger.info("  數據源配置:")
                    logger.info(f"    - Market Data Type: {self._current_market_data_type} ({self._get_market_data_type_name()})")
                    logger.info(f"    - Generic Tick Tags: {self._generic_tick_list}")
                    logger.info(f"    - 當前是否 RTH: {self.is_rth()}")
                    return True
                else:
                    logger.warning("! IBKR 連接後狀態異常：未連接")
                    self.connection_attempts += 1
                    
            except Exception as e:
                error_msg = str(e)
                self.last_error = error_msg
                self._record_error(0, error_msg, 'connect')
                
                # 檢查是否是 Client ID 衝突錯誤
                is_client_id_conflict = (
                    'clientId' in error_msg.lower() and 'already in use' in error_msg.lower()
                ) or (
                    'Error 326' in error_msg  # IBKR Error Code 326: Client ID already in use
                )
                
                if is_client_id_conflict and client_id_offset < max_client_id_attempts:
                    # Client ID 衝突，嘗試下一個 ID
                    client_id_offset += 1
                    logger.warning(f"! Client ID {current_client_id} 已被佔用，嘗試 Client ID {original_client_id + client_id_offset}")
                    # 不增加 connection_attempts，因為這不是連接失敗，而是 Client ID 衝突
                    continue
                else:
                    # 其他錯誤或已達到 Client ID 嘗試上限
                    self.connection_attempts += 1
                    logger.warning(f"! IBKR 連接失敗 (嘗試 {self.connection_attempts}/{self.max_connection_attempts}): {e}")
            
            # 如果還有重試機會，使用指數退避等待
            if self.connection_attempts < self.max_connection_attempts:
                # 計算指數退避延遲: base_delay * 2^(attempt-1)
                delay = min(base_delay * (2 ** (self.connection_attempts - 1)), max_delay)
                logger.info(f"  等待 {delay:.1f} 秒後重試...")
                time.sleep(delay)
        
        logger.error(f"x IBKR 連接失敗，已達最大重試次數 ({self.max_connection_attempts})。請檢查 TWS/Gateway 是否運行")
        return False
    
    # ========================================================================
    # RTH 和 Market Data Type 管理方法
    # ========================================================================
    
    def is_rth(self) -> bool:
        """
        檢查當前是否在正常交易時段 (Regular Trading Hours)
        
        RTH: 週一至週五 09:30-16:00 美東時間
        
        返回:
            bool: True 如果在 RTH 內
        """
        now_et = datetime.now(ET_TIMEZONE)
        current_time = now_et.time()
        weekday = now_et.weekday()
        
        # 週末不是 RTH (週六=5, 週日=6)
        if weekday >= 5:
            return False
        
        # 檢查時間範圍
        return RTH_START <= current_time <= RTH_END
    
    def _determine_market_data_type(self, user_override: int = None) -> int:
        """
        決定應使用的 Market Data Type
        
        優先級:
        1. 方法參數 user_override
        2. 初始化時的 _market_data_type_override
        3. 根據 RTH 自動判斷
        
        返回:
            int: Market Data Type (1=Live, 2=Frozen)
        """
        # 優先使用用戶指定
        if user_override is not None:
            return user_override
        
        if self._market_data_type_override is not None:
            return self._market_data_type_override
        
        # 自動判斷: RTH 用 Live，盤後用 Frozen
        return MARKET_DATA_TYPE_LIVE if self.is_rth() else MARKET_DATA_TYPE_FROZEN
    
    def _apply_market_data_type(self, user_override: int = None):
        """應用 Market Data Type 設置"""
        data_type = self._determine_market_data_type(user_override)
        self._current_market_data_type = data_type
        self.ib.reqMarketDataType(data_type)
        
        reason = "用戶指定" if (user_override or self._market_data_type_override) else ("RTH 期間" if self.is_rth() else "盤後時段")
        logger.info(f"  Market Data Type 設置為 {data_type} ({self._get_market_data_type_name()}) - {reason}")
    
    def _get_market_data_type_name(self) -> str:
        """獲取 Market Data Type 名稱"""
        names = {
            MARKET_DATA_TYPE_LIVE: 'Live',
            MARKET_DATA_TYPE_FROZEN: 'Frozen',
            MARKET_DATA_TYPE_DELAYED: 'Delayed',
            MARKET_DATA_TYPE_DELAYED_FROZEN: 'Delayed Frozen'
        }
        return names.get(self._current_market_data_type, 'Unknown')
    
    @property
    def market_data_type(self) -> int:
        """獲取當前 Market Data Type"""
        return self._current_market_data_type
    
    def set_market_data_type(self, data_type: int):
        """
        手動設置 Market Data Type
        
        參數:
            data_type: 1=Live, 2=Frozen, 3=Delayed, 4=Delayed Frozen
        """
        if not self.is_connected():
            logger.warning("! IBKR 未連接，無法設置 Market Data Type")
            return
        
        old_type = self._current_market_data_type
        self._current_market_data_type = data_type
        self.ib.reqMarketDataType(data_type)
        logger.info(f"Market Data Type 從 {old_type} 切換到 {data_type} ({self._get_market_data_type_name()})")
    
    def get_market_data_type(self) -> Dict[str, Any]:
        """
        Task 18.1: Get current market data type information
        
        Returns:
            dict: Market data type information including:
                - data_type: 'Live', 'Frozen', 'Delayed', etc.
                - code: Market data type code (1, 2, 3, 4)
                - is_rth: Whether currently in regular trading hours
                - timestamp: Current timestamp
        """
        from datetime import datetime, timezone
        
        return {
            'data_type': self._get_market_data_type_name(),
            'code': self._current_market_data_type,
            'is_rth': self.is_rth(),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    def refresh_market_data_type(self):
        """根據當前時間刷新 Market Data Type"""
        if not self.is_connected():
            return
        
        new_type = self._determine_market_data_type()
        if new_type != self._current_market_data_type:
            self.set_market_data_type(new_type)
    
    # ========================================================================
    # 錯誤處理方法
    # ========================================================================
    
    def _record_error(self, error_code: int, error_msg: str, context: str = ''):
        """記錄錯誤"""
        error_record = {
            'timestamp': datetime.now().isoformat(),
            'code': error_code,
            'message': error_msg,
            'context': context
        }
        
        self._recent_errors.append(error_record)
        
        # 保持錯誤列表大小
        if len(self._recent_errors) > MAX_RECENT_ERRORS:
            self._recent_errors = self._recent_errors[-MAX_RECENT_ERRORS:]
        
        logger.error(f"IBKR Error [{error_code}]: {error_msg} ({context})")
    
    def get_recent_errors(self) -> List[Dict]:
        """獲取最近的錯誤記錄"""
        return self._recent_errors.copy()
    
    # ========================================================================
    # 數據質量評估方法
    # ========================================================================
    
    def _assess_data_quality(self, data: Dict) -> str:
        """
        評估數據質量
        
        返回:
            str: 'complete', 'partial', 或 'minimal'
        """
        required_fields = ['bid', 'ask', 'delta', 'gamma', 'theta', 'vega', 'impliedVol']
        optional_fields = ['volume', 'openInterest', 'undPrice', 'optPrice']
        
        required_count = sum(1 for f in required_fields if data.get(f) is not None)
        
        if required_count == len(required_fields):
            return 'complete'
        elif required_count >= len(required_fields) * 0.5:
            return 'partial'
        else:
            return 'minimal'
    
    # ========================================================================
    # Greeks 收斂等待方法
    # ========================================================================
    
    def _wait_for_greeks_convergence(self, option_contract, timeout: int = GREEKS_INITIAL_TIMEOUT) -> Dict:
        """
        等待 Greeks 數據收斂
        
        IBKR 的 Greeks 計算需要時間收斂，此方法會等待數據穩定後再返回
        
        參數:
            option_contract: 期權合約
            timeout: 最大等待時間（秒）
        
        返回:
            dict: 包含 greeks, converged, convergence_time, warnings
        """
        start_time = time.time()
        last_greeks = None
        stable_count = 0
        warnings = []
        
        while time.time() - start_time < timeout:
            ticker_data = self.ib.ticker(option_contract)
            
            if ticker_data and ticker_data.modelGreeks:
                current_greeks = {
                    'delta': ticker_data.modelGreeks.delta,
                    'gamma': ticker_data.modelGreeks.gamma,
                    'theta': ticker_data.modelGreeks.theta,
                    'vega': ticker_data.modelGreeks.vega,
                    'rho': getattr(ticker_data.modelGreeks, 'rho', None),
                    'impliedVol': ticker_data.modelGreeks.impliedVol,
                    'undPrice': ticker_data.modelGreeks.undPrice,
                    'optPrice': ticker_data.modelGreeks.optPrice,
                }
                
                # 檢查核心值是否有效
                core_values = [current_greeks['delta'], current_greeks['gamma'], 
                              current_greeks['theta'], current_greeks['vega']]
                
                if all(v is not None for v in core_values):
                    # 檢查是否穩定（與上次相同）
                    if last_greeks and self._greeks_are_stable(last_greeks, current_greeks):
                        stable_count += 1
                        if stable_count >= 2:
                            elapsed = time.time() - start_time
                            logger.info(f"  Greeks 收斂完成，耗時 {elapsed:.1f} 秒")
                            return {
                                'greeks': current_greeks,
                                'converged': True,
                                'convergence_time': elapsed,
                                'warnings': warnings
                            }
                    else:
                        stable_count = 0
                    
                    last_greeks = current_greeks
            
            time.sleep(0.5)
        
        # 超時返回部分數據
        elapsed = time.time() - start_time
        warnings.append(f'Greeks 未在 {timeout} 秒內完全收斂')
        logger.warning(f"  Greeks 收斂超時 ({elapsed:.1f} 秒)")
        
        return {
            'greeks': last_greeks,
            'converged': False,
            'convergence_time': elapsed,
            'warnings': warnings
        }
    
    def _greeks_are_stable(self, prev: Dict, curr: Dict, tolerance: float = GREEKS_STABILITY_TOLERANCE) -> bool:
        """檢查 Greeks 是否穩定"""
        for key in ['delta', 'gamma', 'theta', 'vega']:
            prev_val = prev.get(key)
            curr_val = curr.get(key)
            if prev_val is not None and curr_val is not None:
                if abs(prev_val - curr_val) > tolerance:
                    return False
        return True
    
    # ========================================================================
    # Underlying Price 驗證方法
    # ========================================================================
    
    def _validate_underlying_price(self, und_price: float, known_price: float = None) -> Dict:
        """
        驗證 IBKR 計算 Greeks 時使用的標的物價格
        
        參數:
            und_price: IBKR 返回的 undPrice
            known_price: 已知的股票價格（可選）
        
        返回:
            dict: 包含 valid, warnings, deviation 等信息
        """
        result = {
            'und_price': und_price,
            'valid': True,
            'warnings': []
        }
        
        # 檢查 undPrice 是否有效
        if und_price is None or und_price <= 0:
            result['valid'] = False
            result['warnings'].append('undPrice 為 None 或無效值')
            return result
        
        # 如果有已知價格，檢查偏差
        if known_price and known_price > 0:
            deviation = abs(und_price - known_price) / known_price
            result['known_price'] = known_price
            result['deviation'] = deviation
            
            if deviation > PRICE_MISMATCH_THRESHOLD:
                result['warnings'].append(
                    f'undPrice ({und_price:.2f}) 與已知價格 ({known_price:.2f}) 偏差 {deviation*100:.2f}%'
                )
                logger.warning(f"  價格偏差警告: undPrice={und_price:.2f}, known={known_price:.2f}, deviation={deviation*100:.2f}%")
        
        return result
    
    def disconnect(self):
        """斷開連接"""
        if self.connected and self.ib.isConnected():
            try:
                self.ib.disconnect()
                self.connected = False
                logger.info("* IBKR 已斷開連接")
            except Exception as e:
                logger.error(f"x IBKR 斷開連接失敗: {e}")
    
    def is_connected(self) -> bool:
        """檢查是否已連接"""
        if not IB_INSYNC_AVAILABLE:
            return False
        
        try:
            return self.ib.isConnected() if self.ib else False
        except:
            return False
    
    def get_option_expirations(self, ticker: str) -> Optional[list]:
        """
        獲取期權到期日列表 (使用 reqSecDefOptParams)
        
        參數:
            ticker: 股票代碼
        
        返回:
            list of str: 到期日期列表 (格式: YYYY-MM-DD)，失敗返回 None
        """
        if not self.is_connected():
            if not self.connect():
                logger.warning("! IBKR 未連接，無法獲取期權到期日")
                return None
        
        try:
            logger.info(f"開始獲取 {ticker} 期權到期日列表 (IBKR)...")
            
            # 創建股票合約
            stock = Stock(ticker, 'SMART', 'USD')
            self.ib.qualifyContracts(stock)
            
            # 獲取期權鏈定義
            chains = self.ib.reqSecDefOptParams(
                stock.symbol,
                '',
                stock.secType,
                stock.conId
            )
            
            if not chains:
                logger.warning(f"! {ticker} 無可用期權鏈定義 (IBKR)")
                return None
            
            # 收集所有到期日（去重）
            all_expirations = set()
            for chain in chains:
                for exp_date in chain.expirations:
                    if isinstance(exp_date, str):
                        # 格式: YYYYMMDD -> YYYY-MM-DD
                        if len(exp_date) == 8:
                            formatted = f"{exp_date[:4]}-{exp_date[4:6]}-{exp_date[6:8]}"
                            all_expirations.add(formatted)
                        else:
                            all_expirations.add(exp_date)
                    else:
                        all_expirations.add(exp_date.strftime('%Y-%m-%d'))
            
            if all_expirations:
                result = sorted(list(all_expirations))
                logger.info(f"✓ 成功獲取 {ticker} 的 {len(result)} 個到期日期 (IBKR)")
                return result
            else:
                logger.warning(f"! {ticker} IBKR 返回的到期日列表為空")
                return None
                
        except Exception as e:
            logger.error(f"✗ IBKR 獲取期權到期日失敗: {e}")
            return None
    
    def get_historical_data(self, ticker: str, period: str = '1mo', interval: str = '1d') -> Optional['pd.DataFrame']:
        """
        獲取歷史 OHLCV 數據 (使用 reqHistoricalData)
        
        參數:
            ticker: 股票代碼
            period: 時間週期 (yfinance 風格: '1d', '5d', '1mo', '3mo', '6mo', '1y', '2y')
            interval: K線間隔 (yfinance 風格: '1m', '5m', '15m', '30m', '1h', '1d', '1wk')
        
        返回:
            pandas DataFrame (Open, High, Low, Close, Volume)，失敗返回 None
        """
        import pandas as pd
        
        if not self.is_connected():
            if not self.connect():
                logger.warning("! IBKR 未連接，無法獲取歷史數據")
                return None
        
        try:
            logger.info(f"開始獲取 {ticker} 歷史數據 (IBKR)... (週期: {period}, 間隔: {interval})")
            
            # --- 將 yfinance 風格的 period 轉換為 IBKR 的 durationStr ---
            period_map = {
                '1d': '1 D',
                '2d': '2 D',
                '5d': '5 D',
                '1mo': '1 M',
                '3mo': '3 M',
                '6mo': '6 M',
                '1y': '1 Y',
                '2y': '2 Y',
            }
            # 也支持 '30d', '60d', '90d', '252d' 這類格式
            duration_str = period_map.get(period)
            if duration_str is None:
                # 嘗試解析 'Nd' 格式
                if period.endswith('d') and period[:-1].isdigit():
                    days = int(period[:-1])
                    duration_str = f"{days} D"
                else:
                    logger.warning(f"! 不支持的 period 格式: {period}，使用默認 1 M")
                    duration_str = '1 M'
            
            # --- 將 yfinance 風格的 interval 轉換為 IBKR 的 barSizeSetting ---
            interval_map = {
                '1m': '1 min',
                '2m': '2 mins',
                '5m': '5 mins',
                '15m': '15 mins',
                '30m': '30 mins',
                '1h': '1 hour',
                '60m': '1 hour',
                '1d': '1 day',
                '1wk': '1 week',
                '1mo': '1 month',
            }
            bar_size = interval_map.get(interval)
            if bar_size is None:
                logger.warning(f"! 不支持的 interval 格式: {interval}，使用默認 1 day")
                bar_size = '1 day'
            
            # 日線以上使用 TRADES，分鐘線也使用 TRADES
            what_to_show = 'TRADES'
            
            # 創建股票合約
            stock = Stock(ticker, 'SMART', 'USD')
            self.ib.qualifyContracts(stock)
            
            # 請求歷史數據
            bars = self.ib.reqHistoricalData(
                stock,
                endDateTime='',  # 到最新
                durationStr=duration_str,
                barSizeSetting=bar_size,
                whatToShow=what_to_show,
                useRTH=True,  # 只要常規交易時段
                formatDate=1  # 日期格式
            )
            
            if not bars:
                logger.warning(f"! IBKR 返回空的歷史數據 ({ticker})")
                return None
            
            # 將 BarData 轉換為 DataFrame
            data = []
            for bar in bars:
                data.append({
                    'Open': bar.open,
                    'High': bar.high,
                    'Low': bar.low,
                    'Close': bar.close,
                    'Volume': bar.volume
                })
            
            # 使用 bar.date 作為索引
            dates = [bar.date for bar in bars]
            df = pd.DataFrame(data, index=pd.DatetimeIndex(dates))
            df.index.name = 'Date'
            
            # 移除 NaN 行
            df = df.dropna()
            
            if df.empty:
                logger.warning(f"! IBKR 歷史數據轉換後為空 ({ticker})")
                return None
            
            logger.info(f"✓ 成功獲取 {ticker} 的 {len(df)} 條歷史記錄 (IBKR, {bar_size})")
            return df
            
        except Exception as e:
            logger.error(f"✗ IBKR 獲取歷史數據失敗: {e}")
            return None
    
    def get_intraday_bars(self, ticker: str, bar_size: str = '1 min', duration: str = '1 D') -> Optional['pd.DataFrame']:
        """
        獲取日內 OHLCV K線數據（Phase 8: VWAP/ORB 用）
        
        參數:
            ticker: 股票代碼
            bar_size: K線尺寸 ('1 min', '5 mins', '15 mins')
            duration: 時間範圍 ('1 D' = 今日數據)
        
        返回:
            pandas DataFrame (Open, High, Low, Close, Volume)，
            索引為 DatetimeIndex；失敗返回 None
        """
        # 將 bar_size 映射回 yfinance 格式，利用現有 get_historical_data
        bar_to_interval = {
            '1 min': '1m',
            '5 mins': '5m',
            '15 mins': '15m',
            '30 mins': '30m',
            '1 hour': '1h',
        }
        dur_to_period = {
            '1 D': '1d',
            '2 D': '2d',
        }
        interval = bar_to_interval.get(bar_size, '1m')
        period = dur_to_period.get(duration, '1d')
        
        logger.info(f"Phase 8: 獲取 {ticker} 日內 K 線 (bar={bar_size}, duration={duration})...")
        
        result = self.get_historical_data(ticker, period=period, interval=interval)
        
        if result is not None and not result.empty:
            logger.info(f"* Phase 8: 獲取 {ticker} 日內 {len(result)} 條 K 線")
        else:
            logger.warning(f"! Phase 8: {ticker} 日內 K 線為空（可能非盤中時段）")
        
        return result
    
    def get_option_chain(self, ticker: str, expiration: str, stock_price: float = 0) -> Optional[Dict[str, Any]]:
        """
        獲取期權鏈數據（只獲取合約信息，不獲取市場數據）
        
        注意：此方法只返回期權合約的基本信息（行使價、到期日等），
        不包含市場數據（bid/ask/last）和 Greeks。
        Greeks 應由本地計算模塊（Black-Scholes）計算。
        
        參數:
            ticker: 股票代碼
            expiration: 到期日期 (YYYY-MM-DD)
            stock_price: 當前股價（用於過濾行使價範圍，可選）
        
        返回:
            dict: 期權鏈數據，失敗返回 None
        """
        if not self.is_connected():
            if not self.connect():
                logger.warning("! IBKR 未連接，無法獲取期權鏈")
                return None
        
        try:
            logger.info(f"開始獲取 {ticker} {expiration} 期權鏈 (IBKR - 僅合約信息)...")
            
            # 創建股票合約
            stock = Stock(ticker, 'SMART', 'USD')
            self.ib.qualifyContracts(stock)
            
            # 獲取期權鏈定義（不需要市場數據訂閱）
            chains = self.ib.reqSecDefOptParams(
                stock.symbol,
                '',
                stock.secType,
                stock.conId
            )
            
            if not chains:
                logger.warning(f"! {ticker} 無可用期權鏈")
                return None
            
            # 找到匹配的到期日
            target_exp_str = expiration.replace('-', '')  # 轉換為 'YYYYMMDD' 格式
            matching_chain = None
            available_expirations = []
            
            for chain in chains:
                for exp_date in chain.expirations:
                    if isinstance(exp_date, str):
                        exp_str = exp_date
                    else:
                        exp_str = exp_date.strftime('%Y%m%d')
                    
                    available_expirations.append(exp_str)
                    
                    if exp_str == target_exp_str:
                        matching_chain = chain
                        break
                if matching_chain:
                    break
            
            if not matching_chain:
                logger.warning(f"! 未找到 {ticker} {expiration} 的期權鏈")
                logger.info(f"  目標到期日: {target_exp_str}")
                logger.info(f"  可用到期日 (前10個): {sorted(set(available_expirations))[:10]}")
                return None
            
            # 構建期權合約列表
            calls = []
            puts = []
            
            # 轉換日期格式: YYYY-MM-DD -> YYYYMMDD
            exp_formatted = expiration.replace('-', '')
            
            # 使用傳入的股價或默認範圍
            current_price = stock_price if stock_price > 0 else 0
            
            # 過濾行使價：只保留接近當前股價的（±30%範圍內）
            if current_price > 0:
                min_strike = current_price * 0.7
                max_strike = current_price * 1.3
                filtered_strikes = [s for s in matching_chain.strikes if min_strike <= s <= max_strike]
                logger.info(f"  過濾行使價: {len(matching_chain.strikes)} -> {len(filtered_strikes)} (股價 ${current_price:.2f})")
            else:
                # 如果無法獲取股價，只取中間的 50 個行使價
                all_strikes = sorted(matching_chain.strikes)
                mid = len(all_strikes) // 2
                filtered_strikes = all_strikes[max(0, mid-25):mid+25]
                logger.info(f"  限制行使價數量: {len(matching_chain.strikes)} -> {len(filtered_strikes)}")
            
            # 使用 reqContractDetails 獲取實際存在的期權合約（不需要市場數據訂閱）
            logger.info(f"  使用 reqContractDetails 獲取期權合約列表...")
            
            option_filter = Option(
                symbol=ticker,
                lastTradeDateOrContractMonth=exp_formatted,
                exchange='SMART',
                currency='USD'
            )
            
            try:
                # 獲取所有匹配的期權合約
                contract_details_list = self.ib.reqContractDetails(option_filter)
                
                if contract_details_list:
                    logger.info(f"  找到 {len(contract_details_list)} 個期權合約")
                    
                    # 過濾行使價範圍，只返回合約基本信息
                    for cd in contract_details_list:
                        contract = cd.contract
                        strike = contract.strike
                        
                        # 只處理在價格範圍內的行使價
                        if current_price > 0:
                            if strike < current_price * 0.7 or strike > current_price * 1.3:
                                continue
                        
                        # 只返回合約基本信息，不獲取市場數據
                        option_data = {
                            'strike': strike,
                            'expiration': expiration,
                            'option_type': contract.right,
                            'conId': contract.conId,
                            'localSymbol': contract.localSymbol,
                            'multiplier': int(contract.multiplier) if contract.multiplier else 100,
                            'data_source': 'ibkr'
                        }
                        
                        # Task 18.1: Add metadata with data type, timestamp
                        from datetime import datetime, timezone
                        option_data['metadata'] = {
                            'data_type': self._get_market_data_type_name(),
                            'timestamp': datetime.now(timezone.utc).isoformat(),
                            'market_data_type_code': self._current_market_data_type,
                            'is_rth': self.is_rth()
                        }
                        
                        # Add warning for frozen data
                        if self._current_market_data_type == MARKET_DATA_TYPE_FROZEN:
                            option_data['metadata']['frozen_data_warning'] = True
                        
                        if contract.right == 'C':
                            calls.append(option_data)
                        else:
                            puts.append(option_data)
                    
                    # 按行使價排序
                    calls.sort(key=lambda x: x['strike'])
                    puts.sort(key=lambda x: x['strike'])
                    
                    logger.info(f"* 獲取 {ticker} 期權鏈完成: {len(calls)} calls, {len(puts)} puts")
                    
                    return {
                        'calls': calls,
                        'puts': puts,
                        'expiration': expiration,
                        'strikes': sorted(set([c['strike'] for c in calls + puts])),
                        'data_source': 'ibkr'
                    }
                else:
                    logger.warning(f"! reqContractDetails 未返回任何合約")
                    return None
                    
            except Exception as e:
                logger.warning(f"! reqContractDetails 失敗: {e}")
                return None
            
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"x 獲取 {ticker} 期權鏈失敗: {e}")
            return None
    
    def get_option_greeks(self, ticker: str, strike: float, 
                          expiration: str, option_type: str = 'C',
                          known_stock_price: float = None) -> Optional[OptionGreeksData]:
        """
        獲取期權 Greeks（優化版）
        
        優化功能:
        - 使用完整 Generic Tick Tags
        - 等待 Greeks 數據收斂
        - 驗證 undPrice/optPrice
        - 數據質量評估
        - 盤外時段警告
        
        參數:
            ticker: 股票代碼
            strike: 行使價
            expiration: 到期日期 (YYYY-MM-DD)
            option_type: 'C' (Call) 或 'P' (Put)
            known_stock_price: 已知股價（用於驗證 undPrice）
        
        返回:
            OptionGreeksData: 包含 Greeks、數據質量指標、警告等完整信息
        """
        if not self.is_connected():
            if not self.connect():
                logger.warning("! IBKR 未連接，無法獲取 Greeks")
                return None
        
        try:
            logger.info(f"開始獲取 {ticker} {strike} {option_type} Greeks (IBKR 優化版)...")
            logger.info(f"  使用 Generic Tick Tags: {self._generic_tick_list}")
            
            # 刷新 Market Data Type（確保使用正確的類型）
            self.refresh_market_data_type()
            
            # 轉換日期格式: YYYY-MM-DD -> YYYYMMDD
            exp_formatted = expiration.replace('-', '')
            
            # 創建期權合約
            option = Option(
                symbol=ticker,
                lastTradeDateOrContractMonth=exp_formatted,
                strike=strike,
                right=option_type,
                exchange='SMART',
                currency='USD'
            )
            qualified = self.ib.qualifyContracts(option)
            
            if not qualified:
                logger.warning(f"! 無法驗證期權合約: {ticker} {strike} {option_type}")
                return None
            
            logger.info(f"  期權合約已驗證: {option.localSymbol}, conId={option.conId}")
            
            # 請求期權市場數據 - 使用完整 Generic Tick Tags
            self.ib.reqMktData(option, self._generic_tick_list, False, False)  # snapshot=False
            
            # 初始化結果
            result = {
                'strike': strike,
                'expiration': expiration,
                'option_type': option_type,
                'source': 'ibkr',
                'market_data_type': self._current_market_data_type,
                'outside_rth': not self.is_rth(),
                'warnings': []
            }
            
            # Task 18.1: Add metadata with data type, timestamp, and age
            from datetime import datetime, timezone
            current_time = datetime.now(timezone.utc)
            
            result['metadata'] = {
                'data_type': self._get_market_data_type_name(),  # 'Live', 'Frozen', 'Delayed'
                'timestamp': current_time.isoformat(),
                'market_data_type_code': self._current_market_data_type,
                'is_rth': self.is_rth()
            }
            
            # Add warning for frozen data
            if self._current_market_data_type == MARKET_DATA_TYPE_FROZEN:
                result['warnings'].append('⚠️ Warning: Data is from previous trading session (Frozen data)')
                result['metadata']['frozen_data_warning'] = True
            
            # 等待 Greeks 收斂
            convergence_result = self._wait_for_greeks_convergence(option, GREEKS_INITIAL_TIMEOUT)
            
            if convergence_result['greeks']:
                greeks = convergence_result['greeks']
                
                # 填充 Greeks 數據
                result['delta'] = greeks.get('delta')
                result['gamma'] = greeks.get('gamma')
                result['theta'] = greeks.get('theta')
                result['vega'] = greeks.get('vega')
                result['rho'] = greeks.get('rho')
                
                # Task 17.3: Apply IV normalization to IBKR data
                raw_iv = greeks.get('impliedVol')
                if raw_iv is not None:
                    # Import IVNormalizer
                    try:
                        from data_layer.data_fetcher import IVNormalizer
                        normalized_iv = IVNormalizer.normalize(raw_iv, source='IBKR', ticker=ticker)
                        result['impliedVol'] = normalized_iv
                        
                        # Add IV metadata
                        result['iv_metadata'] = {
                            'original_value': raw_iv,
                            'normalized_value': normalized_iv,
                            'source': 'IBKR',
                            'format_detected': 'decimal' if 0 < raw_iv < 1.0 else 'percentage'
                        }
                    except ImportError:
                        # Fallback if IVNormalizer not available
                        result['impliedVol'] = raw_iv
                        logger.warning("IVNormalizer not available, using raw IV value")
                else:
                    result['impliedVol'] = None
                
                result['undPrice'] = greeks.get('undPrice')
                result['optPrice'] = greeks.get('optPrice')
                result['greeks_converged'] = convergence_result['converged']
                result['convergence_time'] = convergence_result['convergence_time']
                result['greeks_source'] = 'ibkr_model'
                
                # 驗證 undPrice
                if greeks.get('undPrice'):
                    price_validation = self._validate_underlying_price(
                        greeks['undPrice'], 
                        known_stock_price
                    )
                    if price_validation['warnings']:
                        result['warnings'].extend(price_validation['warnings'])
                    result['undPrice_valid'] = price_validation['valid']
                
                # 檢查 IV 異常（盤外時段可能出現）
                if result.get('impliedVol') and result['impliedVol'] > IV_SPIKE_THRESHOLD:
                    result['warnings'].append(
                        f'IV 異常高 ({result["impliedVol"]*100:.1f}%)，可能因盤外時段 bid/ask 價差過大'
                    )
                    result['iv_spike_warning'] = True
            else:
                # Task 18.3: Fallback to local Black-Scholes calculator when IBKR Greeks timeout
                result['greeks_source'] = 'unavailable'
                result['greeks_converged'] = False
                
                # Try to use local Black-Scholes calculator as fallback
                logger.info("  IBKR Greeks unavailable, attempting local Black-Scholes calculator fallback...")
                
                try:
                    # Import Black-Scholes calculator
                    from calculation_layer.module15_black_scholes import BlackScholesCalculator
                    from calculation_layer.module16_greeks import GreeksCalculator
                    
                    # Get stock price (from known_stock_price or fetch it)
                    stock_price = known_stock_price
                    if stock_price is None:
                        # Try to get stock price from IBKR
                        stock = Stock(ticker, 'SMART', 'USD')
                        self.ib.qualifyContracts(stock)
                        stock_ticker = self.ib.reqMktData(stock, '', False, False)
                        self.ib.sleep(2)  # Wait for data
                        if stock_ticker and stock_ticker.last:
                            stock_price = float(stock_ticker.last)
                        self.ib.cancelMktData(stock)
                    
                    if stock_price is None:
                        logger.warning("  Cannot get stock price for local Greeks calculation")
                        result['warnings'].append('IBKR Greeks timeout, local calculator unavailable (no stock price)')
                    else:
                        # Calculate time to expiration
                        from datetime import datetime
                        exp_date = datetime.strptime(expiration, '%Y-%m-%d')
                        today = datetime.now()
                        days_to_exp = (exp_date - today).days
                        time_to_exp = days_to_exp / 365.0
                        
                        if time_to_exp <= 0:
                            logger.warning("  Option expired, cannot calculate Greeks")
                            result['warnings'].append('IBKR Greeks timeout, option expired')
                        else:
                            # Get risk-free rate (use default 5% if not available)
                            risk_free_rate = 0.05
                            
                            # Get IV from option price if available
                            option_price = result.get('mid') or result.get('last')
                            
                            if option_price and option_price > 0:
                                # Calculate Greeks using local calculator
                                greeks_calc = GreeksCalculator()
                                
                                # First, calculate IV from option price
                                from calculation_layer.module17_implied_volatility import ImpliedVolatilityCalculator
                                iv_calc = ImpliedVolatilityCalculator()
                                
                                calculated_iv = iv_calc.calculate_iv(
                                    option_price=option_price,
                                    stock_price=stock_price,
                                    strike_price=strike,
                                    time_to_expiration=time_to_exp,
                                    risk_free_rate=risk_free_rate,
                                    option_type='call' if option_type == 'C' else 'put'
                                )
                                
                                if calculated_iv and calculated_iv.implied_volatility:
                                    volatility = calculated_iv.implied_volatility
                                    
                                    # Calculate Greeks
                                    local_greeks = greeks_calc.calculate_greeks(
                                        stock_price=stock_price,
                                        strike_price=strike,
                                        time_to_expiration=time_to_exp,
                                        risk_free_rate=risk_free_rate,
                                        volatility=volatility,
                                        option_type='call' if option_type == 'C' else 'put'
                                    )
                                    
                                    # Fill in Greeks from local calculator
                                    result['delta'] = local_greeks.delta
                                    result['gamma'] = local_greeks.gamma
                                    result['theta'] = local_greeks.theta
                                    result['vega'] = local_greeks.vega
                                    result['rho'] = local_greeks.rho
                                    result['impliedVol'] = volatility * 100  # Convert to percentage
                                    result['undPrice'] = stock_price
                                    result['optPrice'] = option_price
                                    result['greeks_source'] = 'local_calculator_fallback'
                                    result['greeks_converged'] = True
                                    
                                    logger.info(f"  ✓ Local Black-Scholes calculator fallback successful")
                                    result['warnings'].append('Using local Black-Scholes calculator (IBKR timeout)')
                                else:
                                    logger.warning("  Cannot calculate IV for local Greeks")
                                    result['warnings'].append('IBKR Greeks timeout, local calculator failed (IV calculation)')
                            else:
                                logger.warning("  No option price available for local Greeks calculation")
                                result['warnings'].append('IBKR Greeks timeout, local calculator unavailable (no option price)')
                
                except Exception as e:
                    logger.error(f"  Local Black-Scholes calculator fallback failed: {e}")
                    result['warnings'].append(f'IBKR Greeks timeout, local calculator error: {str(e)}')
            
            # 添加收斂警告
            if convergence_result.get('warnings'):
                result['warnings'].extend(convergence_result['warnings'])
            
            # 獲取報價數據
            ticker_data = self.ib.ticker(option)
            if ticker_data:
                # Bid/Ask/Last
                if ticker_data.bid is not None and self._is_valid_price(ticker_data.bid):
                    result['bid'] = float(ticker_data.bid)
                if ticker_data.ask is not None and self._is_valid_price(ticker_data.ask):
                    result['ask'] = float(ticker_data.ask)
                if ticker_data.last is not None and self._is_valid_price(ticker_data.last):
                    result['last'] = float(ticker_data.last)
                
                # Volume 和 OI
                if ticker_data.volume is not None and ticker_data.volume > 0:
                    result['volume'] = int(ticker_data.volume)
                if hasattr(ticker_data, 'openInterest') and ticker_data.openInterest:
                    result['openInterest'] = int(ticker_data.openInterest)
                
                # 計算中間價
                if 'bid' in result and 'ask' in result:
                    result['mid'] = (result['bid'] + result['ask']) / 2
            
            # 評估數據質量
            result['data_quality'] = self._assess_data_quality(result)
            
            # 盤外時段警告
            if result['outside_rth']:
                result['warnings'].append('數據獲取於盤外時段，Greeks 可能不準確')
            
            # 取消市場數據訂閱
            try:
                self.ib.cancelMktData(option)
            except:
                pass
            
            # 過濾 None 值（保留重要字段）
            important_fields = ['strike', 'expiration', 'option_type', 'source', 'data_quality', 
                               'greeks_source', 'outside_rth', 'warnings', 'market_data_type']
            result = {k: v for k, v in result.items() if v is not None or k in important_fields}
            
            logger.info(f"* 獲取期權 Greeks 完成: data_quality={result.get('data_quality')}, converged={result.get('greeks_converged')}")
            return result
                
        except Exception as e:
            self.last_error = str(e)
            self._record_error(0, str(e), f'get_option_greeks({ticker}, {strike}, {option_type})')
            logger.error(f"x 獲取 Greeks 失敗: {e}")
            return None
    
    def _is_valid_price(self, price) -> bool:
        """檢查價格是否有效（非 NaN、非負、非 -1）"""
        if price is None:
            return False
        try:
            p = float(price)
            # 檢查 NaN
            if p != p:
                return False
            # 檢查負數和 -1（IBKR 用 -1 表示無數據）
            if p < 0:
                return False
            return True
        except (ValueError, TypeError):
            return False
    
    def get_option_quote(self, ticker: str, strike: float, 
                         expiration: str, option_type: str = 'C') -> Optional[OptionQuoteData]:
        """
        獲取期權報價數據（優化版，使用完整 Tick Tags）
        
        這個方法專門獲取期權的基本報價數據，包含數據質量指標。
        
        參數:
            ticker: 股票代碼
            strike: 行使價
            expiration: 到期日期 (YYYY-MM-DD)
            option_type: 'C' (Call) 或 'P' (Put)
        
        返回:
            OptionQuoteData: 包含報價、數據質量、警告等完整信息
        """
        if not self.is_connected():
            if not self.connect():
                logger.warning("! IBKR 未連接，無法獲取期權報價")
                return None
        
        try:
            logger.info(f"開始獲取 {ticker} {strike} {option_type} 期權報價 (IBKR 優化版)...")
            
            # 刷新 Market Data Type
            self.refresh_market_data_type()
            
            # 轉換日期格式
            exp_formatted = expiration.replace('-', '')
            
            # 創建期權合約
            option = Option(
                symbol=ticker,
                lastTradeDateOrContractMonth=exp_formatted,
                strike=strike,
                right=option_type,
                exchange='SMART',
                currency='USD'
            )
            
            try:
                qualified = self.ib.qualifyContracts(option)
            except Exception as qual_err:
                logger.debug(f"  合約驗證時出現警告（可忽略）: {qual_err}")
            
            if not qualified or not option.conId:
                logger.warning(f"! 無法驗證期權合約: {ticker} {strike} {option_type}")
                return None
            
            # 請求期權報價 - 使用完整 Generic Tick Tags
            self.ib.reqMktData(option, self._generic_tick_list, False, False)
            
            # 等待數據（增加等待時間以確保數據完整）
            ticker_data = None
            for i in range(10):  # 最多等待 10 秒
                time.sleep(1)
                ticker_data = self.ib.ticker(option)
                if ticker_data:
                    has_bid = self._is_valid_price(ticker_data.bid)
                    has_ask = self._is_valid_price(ticker_data.ask)
                    if has_bid or has_ask:
                        # 再等待一下讓更多數據到達
                        if i < 3:
                            continue
                        break
            
            if not ticker_data:
                return None
            
            result = {
                'strike': strike,
                'expiration': expiration,
                'option_type': option_type,
                'data_source': 'ibkr_opra',
                'market_data_type': self._current_market_data_type,
                'outside_rth': not self.is_rth(),
                'warnings': [],
                'tick_tags_used': self._generic_tick_list
            }
            
            # 收集報價數據
            try:
                logger.debug(f"  原始數據: bid={ticker_data.bid}, ask={ticker_data.ask}, last={ticker_data.last}, volume={ticker_data.volume}")
                
                if self._is_valid_price(ticker_data.bid):
                    result['bid'] = float(ticker_data.bid)
                
                if self._is_valid_price(ticker_data.ask):
                    result['ask'] = float(ticker_data.ask)
                
                if self._is_valid_price(ticker_data.last):
                    result['last'] = float(ticker_data.last)
                
                if ticker_data.volume is not None and ticker_data.volume > 0:
                    result['volume'] = int(ticker_data.volume)
                
                # Open Interest
                if hasattr(ticker_data, 'openInterest') and ticker_data.openInterest:
                    result['openInterest'] = int(ticker_data.openInterest)
                
                # Greeks（如果可用）
                if ticker_data.modelGreeks:
                    result['delta'] = ticker_data.modelGreeks.delta
                    result['gamma'] = ticker_data.modelGreeks.gamma
                    result['theta'] = ticker_data.modelGreeks.theta
                    result['vega'] = ticker_data.modelGreeks.vega
                    
                    # Task 17.3: Apply IV normalization to IBKR data
                    raw_iv = ticker_data.modelGreeks.impliedVol
                    if raw_iv is not None:
                        try:
                            from data_layer.data_fetcher import IVNormalizer
                            normalized_iv = IVNormalizer.normalize(raw_iv, source='IBKR', ticker=ticker)
                            result['impliedVolatility'] = normalized_iv
                        except ImportError:
                            result['impliedVolatility'] = raw_iv
                            logger.warning("IVNormalizer not available, using raw IV value")
                    else:
                        result['impliedVolatility'] = None
                    
                    result['undPrice'] = ticker_data.modelGreeks.undPrice
                    result['optPrice'] = ticker_data.modelGreeks.optPrice
                    result['greeks_source'] = 'ibkr_model'
                    
                    # 檢查 IV 異常
                    if result.get('impliedVolatility') and result['impliedVolatility'] > IV_SPIKE_THRESHOLD:
                        result['warnings'].append(f'IV 異常高 ({result["impliedVolatility"]*100:.1f}%)')
                        result['iv_spike_warning'] = True
                    
            except (ValueError, TypeError) as e:
                logger.debug(f"  處理報價數據時出錯: {e}")
            
            # Fix 11: 優先使用 Tick 232 Mark Price 作為中間價
            import math as _math
            mark_price = getattr(ticker_data, 'markPrice', None)
            if mark_price is not None:
                try:
                    mp = float(mark_price)
                    if not _math.isnan(mp) and mp > 0:
                        result['markPrice'] = mp
                        result['mid'] = mp  # 使用 IBKR 的 markPrice 而非 (bid+ask)/2
                        logger.debug(f"  Tick 232 Mark Price: ${mp:.4f}")
                except (TypeError, ValueError):
                    pass
            
            # Fallback: 如果沒有 markPrice，使用 (bid+ask)/2
            if 'mid' not in result and 'bid' in result and 'ask' in result:
                result['mid'] = (result['bid'] + result['ask']) / 2
            
            # 評估數據質量
            result['data_quality'] = self._assess_data_quality(result)
            
            # 盤外時段警告
            if result['outside_rth']:
                result['warnings'].append('數據獲取於盤外時段')
            
            # 取消市場數據訂閱
            self.ib.cancelMktData(option)
            
            logger.info(f"* 獲取期權報價成功: data_quality={result.get('data_quality')}")
            return result
            
        except Exception as e:
            self._record_error(0, str(e), f'get_option_quote({ticker}, {strike}, {option_type})')
            logger.error(f"x 獲取期權報價失敗: {e}")
            return None
    
    def get_bid_ask_spread(self, ticker: str, strike: float, 
                          expiration: str, option_type: str = 'C') -> Optional[float]:
        """
        獲取實時 Bid/Ask 價差
        
        參數:
            ticker: 股票代碼
            strike: 行使價
            expiration: 到期日期
            option_type: 'C' 或 'P'
        
        返回:
            float: 價差（美元），失敗返回 None
        """
        if not self.is_connected():
            if not self.connect():
                return None
        
        try:
            # 轉換日期格式: YYYY-MM-DD -> YYYYMMDD
            exp_formatted = expiration.replace('-', '')
            
            option = Option(ticker, exp_formatted, strike, option_type, 'SMART')
            self.ib.qualifyContracts(option)
            self.ib.reqMktData(option, self._generic_tick_list, False, False)
            time.sleep(1)
            
            ticker_data = self.ib.ticker(option)
            if ticker_data and ticker_data.bid and ticker_data.ask:
                spread = ticker_data.ask - ticker_data.bid
                logger.info(f"* Bid/Ask 價差: ${spread:.2f}")
                return float(spread)
            else:
                return None
                
        except Exception as e:
            logger.error(f"x 獲取 Bid/Ask 價差失敗: {e}")
            return None
    
    def _get_option_data(self, contract: Contract) -> Optional[Dict[str, Any]]:
        """獲取單個期權合約的市場數據"""
        try:
            self.ib.reqMktData(contract, getattr(self, '_generic_tick_list', ''), False, False)
            time.sleep(0.5)  # 等待數據
            
            ticker_data = self.ib.ticker(contract)
            if not ticker_data:
                return None
            
            # Task 17.3: Apply IV normalization to IBKR data
            raw_iv = ticker_data.impliedVolatility if ticker_data.impliedVolatility else None
            normalized_iv = None
            
            # 🔧 P-5 Fix: 過濾 IV = 0（無效數據）
            if raw_iv is not None and raw_iv > 0:
                try:
                    from data_layer.data_fetcher import IVNormalizer
                    # Extract ticker from contract symbol
                    ticker_symbol = contract.symbol
                    normalized_iv = IVNormalizer.normalize(raw_iv, source='IBKR', ticker=ticker_symbol)
                except ImportError:
                    # Fallback: manual conversion
                    normalized_iv = raw_iv * 100 if 0 < raw_iv < 1.0 else raw_iv
                    logger.warning("IVNormalizer not available, using manual conversion")
            elif raw_iv == 0:
                logger.debug(f"IV = 0 (無效數據)，設為 None")
                normalized_iv = None
            
            # 🔧 P-5 Fix: 過濾 openInterest = 0 的情況（設為 None 而非 0，避免下游除零）
            open_interest = ticker_data.openInterest if ticker_data.openInterest else None
            if open_interest == 0:
                open_interest = None
            
            return {
                'strike': contract.strike,
                'expiration': contract.lastTradeDateOrContractMonth,
                'option_type': contract.right,
                'bid': float(ticker_data.bid) if ticker_data.bid else 0.0,
                'ask': float(ticker_data.ask) if ticker_data.ask else 0.0,
                'last': float(ticker_data.last) if ticker_data.last else 0.0,
                'volume': int(ticker_data.volume) if ticker_data.volume else 0,
                'openInterest': int(open_interest) if open_interest else None,
                'impliedVolatility': normalized_iv,
                'delta': float(ticker_data.modelGreeks.delta) if ticker_data.modelGreeks and ticker_data.modelGreeks.delta else None,
                'gamma': float(ticker_data.modelGreeks.gamma) if ticker_data.modelGreeks and ticker_data.modelGreeks.gamma else None,
                'theta': float(ticker_data.modelGreeks.theta) if ticker_data.modelGreeks and ticker_data.modelGreeks.theta else None,
                'vega': float(ticker_data.modelGreeks.vega) if ticker_data.modelGreeks and ticker_data.modelGreeks.vega else None,
                'data_source': 'ibkr'
            }
        except Exception as e:
            logger.debug(f"獲取期權數據失敗: {e}")
            return None
    
    def get_stock_price(self, ticker: str) -> Optional[float]:
        """獲取實時股票價格"""
        if not self.is_connected() and not self.connect():
            return None
            
        import math
            
        try:
            contract = Stock(ticker, 'SMART', 'USD')
            self.ib.qualifyContracts(contract)
            
            # 使用 reqMktData (Snapshot)，加入 generic_tick_list
            self.ib.reqMktData(contract, getattr(self, '_generic_tick_list', ''), True, False)
            
            # 等待數據 (最多 4 秒)
            start_time = time.time()
            price = None
            while time.time() - start_time < 4:
                self.ib.sleep(0.1)
                t = self.ib.ticker(contract)
                if t.last and not math.isnan(t.last):
                    price = t.last
                    break
                elif t.close and not math.isnan(t.close):
                    price = t.close
                    
            if price:
                logger.info(f"獲取 {ticker} 股價成功: {price}")
                return price
            else:
                logger.warning(f"獲取 {ticker} 股價超時或數據無效")
                return None
        except Exception as e:
            logger.error(f"獲取股價失敗: {e}")
            return None

    def get_option_chain_snapshot(self, ticker: str, expiration: str, 
                                 center_strike: float = None) -> Optional[Dict[str, Any]]:
        """
        獲取期權鏈快照（結構 + 實時數據）- 統一 Schema
        
        高效獲取整個期權鏈的實時數據，返回統一的 OptionSnapshotSchema 格式。
        
        策略：
        1. 獲取所有合約
        2. 過濾（如果指定了 center_strike，只獲取附近的合約，例如 +/- 25%）
        3. 批量請求快照數據
        4. 收集結果並轉換為統一 schema
        
        參數:
            ticker: 股票代碼
            expiration: 到期日 (YYYY-MM-DD)
            center_strike: 中心行使價（通常是當前股價），用於過濾。如果為 None 則獲取全部（慎用）
            
        返回:
            dict: {
                'calls': List[OptionSnapshotSchema],
                'puts': List[OptionSnapshotSchema]
            }
        
        Ref: option-data-review.md Section III.4, data_policy.py OptionSnapshotSchema
        """
        if not self.is_connected() and not self.connect():
            return None
            
        import math
        from data_layer.data_policy import DataSource
            
        try:
            logger.info(f"正在獲取 {ticker} {expiration} 期權鏈快照（統一 Schema）...")
            
            # 1. 獲取鏈結構
            self.refresh_market_data_type()
            
            # 格式化日期
            exp_formatted = expiration.replace('-', '')
            
            # 查找合約
            chain_structure = self.get_option_chain(ticker, expiration, stock_price=center_strike if center_strike else 0)
            
            if not chain_structure:
                logger.warning("無法獲取期權鏈結構")
                return None
                
            calls = chain_structure.get('calls', [])
            puts = chain_structure.get('puts', [])
            
            all_contracts = []
            
            # 過濾邏輯 (如果提供了 center_strike)
            if center_strike:
                # 簡單過濾: +/- 25%
                lower_bound = center_strike * 0.75
                upper_bound = center_strike * 1.25
                
                valid_calls = [c for c in calls if lower_bound <= c['strike'] <= upper_bound]
                valid_puts = [c for c in puts if lower_bound <= c['strike'] <= upper_bound]
                
                logger.info(f"過濾合約: Calls {len(calls)}->{len(valid_calls)}, Puts {len(puts)}->{len(valid_puts)}")
                
                # 轉換為 Contract 對象
                for c in valid_calls:
                    contract = Option(ticker, exp_formatted, c['strike'], 'C', 'SMART')
                    contract.conId = c.get('conId', 0)
                    all_contracts.append(contract)
                    
                for p in valid_puts:
                    contract = Option(ticker, exp_formatted, p['strike'], 'P', 'SMART')
                    contract.conId = p.get('conId', 0)
                    all_contracts.append(contract)
            else:
                # 全部獲取 (注意流量控制)
                logger.warning("未指定 center_strike，將獲取完整期權鏈（可能較慢）")
                for c in calls:
                    all_contracts.append(Option(ticker, exp_formatted, c['strike'], 'C', 'SMART'))
                for p in puts:
                    all_contracts.append(Option(ticker, exp_formatted, p['strike'], 'P', 'SMART'))

            if not all_contracts:
                return {'calls': [], 'puts': []}

            # 2. 批量請求數據
            logger.info(f"請求 {len(all_contracts)} 個合約的快照數據...")
            
            # 使用流式訂閱 + 短暫等待 + 取消訂閱 (Streaming Burst)
            for contract in all_contracts:
                self.ib.reqMktData(contract, self._generic_tick_list, False, False) 
            
            # 3. 等待數據填充（最多 8 秒）
            start_time = time.time()
            while time.time() - start_time < 8:
                self.ib.sleep(0.2)
                pending = 0
                for c in all_contracts:
                    t = self.ib.ticker(c)
                    has_data = (t.last and not math.isnan(t.last)) or \
                               (t.bid and not math.isnan(t.bid)) or \
                               (t.modelGreeks and t.modelGreeks.impliedVol)
                    if not has_data:
                        pending += 1
                
                if pending == 0:
                    break
                    
            # 4. 收集結果並轉換為統一 schema
            call_data = []
            put_data = []
            
            for contract in all_contracts:
                # 轉換為統一 schema
                option_snapshot = self._convert_ticker_to_option_snapshot(
                    contract, ticker, expiration
                )
                
                if option_snapshot:
                    if contract.right == 'C':
                        call_data.append(option_snapshot)
                    else:
                        put_data.append(option_snapshot)
            
            # 取消訂閱
            for contract in all_contracts:
                self.ib.cancelMktData(contract)
                
            logger.info(f"快照獲取完成。Calls: {len(call_data)}, Puts: {len(put_data)}")
            
            return {
                'calls': call_data,
                'puts': put_data
            }
        except Exception as e:
            logger.error(f"獲取期權鏈快照失敗: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def _convert_ticker_to_option_snapshot(
        self, 
        contract: Contract, 
        ticker: str, 
        expiration: str
    ) -> Optional[Dict[str, Any]]:
        """
        將 IBKR Ticker 數據轉換為統一的 OptionSnapshotSchema
        
        這是統一 schema 的核心轉換函式，確保所有 IBKR 期權數據都使用相同格式。
        
        參數:
            contract: IBKR 合約對象
            ticker: 股票代碼
            expiration: 到期日 (YYYY-MM-DD)
        
        返回:
            Dict: OptionSnapshotSchema 格式的數據
        
        Ref: data_policy.py OptionSnapshotSchema
        """
        import math
        from data_layer.data_policy import DataSource, VOLATILITY_UNIT_STANDARD
        
        t = self.ib.ticker(contract)
        
        if not t:
            return None
        
        # 安全轉換函式
        def safe_int(val, default=0):
            if val is None:
                return default
            try:
                if math.isnan(val):
                    return default
                return int(val)
            except (TypeError, ValueError):
                return default
        
        def safe_float(val, default=0.0):
            if val is None:
                return default
            try:
                if math.isnan(val):
                    return default
                return float(val)
            except (TypeError, ValueError):
                return default
        
        # 獲取 Open Interest
        oi = None
        call_oi = getattr(t, 'callOpenInterest', None)
        put_oi = getattr(t, 'putOpenInterest', None) 
        generic_oi = getattr(t, 'openInterest', None)
        
        if contract.right == 'C':
            oi = call_oi or generic_oi
        else:
            oi = put_oi or generic_oi
        
        # IV 標準化（統一為百分比格式 0-100）
        raw_iv = t.modelGreeks.impliedVol if t.modelGreeks and t.modelGreeks.impliedVol else None
        normalized_iv = None
        
        if raw_iv is not None:
            try:
                from data_layer.data_fetcher import IVNormalizer
                normalized_iv = IVNormalizer.normalize(raw_iv, source='IBKR', ticker=ticker)
            except ImportError:
                # Fallback: manual conversion to percentage
                normalized_iv = raw_iv * 100 if 0 < raw_iv < 1.0 else raw_iv
        
        # 構建統一 schema
        option_snapshot = {
            # 合約識別
            'ticker': ticker,
            'strike': float(contract.strike),
            'expiration': expiration,
            'option_type': 'call' if contract.right == 'C' else 'put',  # Convert 'C'/'P' to 'call'/'put'
            
            # 價格數據 (使用 snake_case)
            'bid': safe_float(t.bid if self._is_valid_price(t.bid) else None),
            'ask': safe_float(t.ask if self._is_valid_price(t.ask) else None),
            'last_price': safe_float(t.last if self._is_valid_price(t.last) else None),
            'mark_price': safe_float(getattr(t, 'markPrice', None)),
            
            # 成交量與持倉 (使用 snake_case)
            'volume': safe_int(t.volume),
            'open_interest': safe_int(oi),
            
            # Greeks
            'delta': safe_float(t.modelGreeks.delta if t.modelGreeks else None),
            'gamma': safe_float(t.modelGreeks.gamma if t.modelGreeks else None),
            'theta': safe_float(t.modelGreeks.theta if t.modelGreeks else None),
            'vega': safe_float(t.modelGreeks.vega if t.modelGreeks else None),
            'rho': safe_float(getattr(t.modelGreeks, 'rho', None) if t.modelGreeks else None),
            
            # 波動率（統一為百分比格式 0-100，使用 snake_case）
            'implied_volatility': normalized_iv,
            
            # Metadata
            'greeks_source': DataSource.IBKR_SNAPSHOT if t.modelGreeks and t.modelGreeks.delta is not None else None,
            'iv_source': DataSource.IBKR_SNAPSHOT if normalized_iv is not None else None,
            'data_source': DataSource.IBKR_SNAPSHOT,
            'data_quality': self._assess_option_data_quality(t, contract),
        }
        
        return option_snapshot
    
    def _assess_option_data_quality(self, ticker_data, contract) -> str:
        """
        評估期權數據質量
        
        返回:
            str: 'complete', 'partial', 'minimal'
        """
        required_fields = ['bid', 'ask', 'impliedVolatility']
        optional_fields = ['delta', 'gamma', 'theta', 'vega', 'volume', 'openInterest']
        
        has_bid = ticker_data.bid and self._is_valid_price(ticker_data.bid)
        has_ask = ticker_data.ask and self._is_valid_price(ticker_data.ask)
        has_iv = ticker_data.modelGreeks and ticker_data.modelGreeks.impliedVol
        
        required_count = sum([has_bid, has_ask, has_iv])
        
        if required_count == 3:
            # 檢查 optional fields
            has_greeks = ticker_data.modelGreeks and ticker_data.modelGreeks.delta is not None
            has_volume = ticker_data.volume and ticker_data.volume > 0
            
            if has_greeks and has_volume:
                return 'complete'
            else:
                return 'partial'
        elif required_count >= 2:
            return 'partial'
        else:
            return 'minimal'

    def get_stock_full_data(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        獲取股票 IBKR 獨有的 advanced 欄位
        
        此函數只返回 IBKR 特有的高級數據，不返回主要股價欄位（price, bid, ask, volume）
        主要股價欄位應由 Finnhub 或 yfinance 提供
        
        Tick 104 (Historical Volatility 30-day) → 直接使用，替代 Yahoo Finance 重算
        Tick 456 (IB Dividends / Dividend Yield) → 直接使用，傳入 module16 Greeks
        Tick 232 (Mark Price) → IBKR 計算的理論中間價，比 (bid+ask)/2 更準
        Tick 106 (Implied Volatility 30-day) → IBKR 計算的 30 天隱含波動率
        
        返回:
            dict: {
                'mark_price': float,          # Tick 232 (IBKR 理論中間價)
                'historical_volatility_30d': float, # Tick 104 (IBKR HV-30)
                'implied_volatility_30d': float, # Tick 106 (IBKR IV-30)
                'dividend_yield': float,       # Tick 456 (IBKR Dividend Yield)
                'annual_dividend': float,      # Tick 456 (年度股息)
                'hv_source': 'ibkr_tick104',   # 數據來源標識
                'div_source': 'ibkr_tick456',
            }
        """
        if not self.is_connected():
            if not self.connect():
                return None

        try:
            logger.info(f"Fix 11: 獲取 {ticker} 完整股票數據 (含 Tick 104/456)...")
            self.refresh_market_data_type()

            stock = Stock(ticker, 'SMART', 'USD')
            self.ib.qualifyContracts(stock)

            # 使用包含 Tick 104/456 的完整 tick list（含 STOCK_ONLY 的新聞 Tick 292）
            stock_tick_list = self._stock_tick_list  # 包含 104, 106, 232, 456

            self.ib.reqMktData(stock, stock_tick_list, False, False)

            # 等待數據（最多 8 秒，確保 Tick 104/456 到達）
            ticker_data = None
            for i in range(8):
                time.sleep(1)
                ticker_data = self.ib.ticker(stock)
                if ticker_data:
                    # 等到至少有 price 和 hv
                    has_price = (
                        self._is_valid_price(getattr(ticker_data, 'last', None)) or
                        self._is_valid_price(getattr(ticker_data, 'close', None))
                    )
                    if has_price and i >= 2:
                        break

            if not ticker_data:
                logger.warning(f"! {ticker}: 無法獲取股票數據")
                return None

            result = {
                'ticker': ticker,
                'data_source': 'ibkr_tick',
                'hv_source': 'ibkr_tick104',   # Fix 11: 數據來源標識
                'div_source': 'ibkr_tick456',
            }

            import math

            # ── Tick 232: Mark Price（比 mid 更準） ─────────
            # IBKR 的 markPrice 是理論計算的中間價，而非簡單 (bid+ask)/2
            mark_price = getattr(ticker_data, 'markPrice', None)
            if mark_price is not None:
                try:
                    mp = float(mark_price)
                    if not math.isnan(mp) and mp > 0:
                        result['mark_price'] = mp
                        logger.info(f"  Tick 232 Mark Price: ${mp:.4f}")
                except (TypeError, ValueError):
                    pass

            # ── Tick 104: Historical Volatility 30d ─────────
            # Fix 11: 直接從 IBKR 獲取 HV，替代 Yahoo Finance 重算
            # Fix OPRA Review 1.3 & 1.4: 保持 percentage 格式，修正欄位名
            hv = getattr(ticker_data, 'histVolatility', None)
            if hv is None:
                # ib_insync 可能用不同屬性名
                hv = getattr(ticker_data, 'historicalVolatility', None)
            if hv is not None:
                try:
                    hv_val = float(hv)
                    if not math.isnan(hv_val) and hv_val > 0:
                        result['historical_volatility_30d'] = hv_val  # 保持 percentage 格式 (25.0 = 25%)
                        logger.info(f"  Tick 104 HV-30: {hv_val:.2f}%  ← 直接使用 IBKR 數據")
                except (TypeError, ValueError):
                    pass

            # ── Tick 106: Implied Volatility 30d ────────────
            # Fix OPRA Review 1.3: 保持 percentage 格式
            iv_30 = getattr(ticker_data, 'impliedVolatility', None)
            if iv_30 is not None:
                try:
                    iv_val = float(iv_30)
                    if not math.isnan(iv_val) and iv_val > 0:
                        result['implied_volatility_30d'] = iv_val  # 保持 percentage 格式 (25.0 = 25%)
                        logger.info(f"  Tick 106 IV-30:  {iv_val:.2f}%")
                except (TypeError, ValueError):
                    pass

            # ── Tick 456: IB Dividends / Dividend Yield ─────
            # Fix 11: 直接從 IBKR 獲取股息率，傳入 module16 Greeks
            # ib_insync 中 Tick 456 對應 dividends 屬性（格式: "past12,next12,nextDate,nextAmount"）
            div_info = getattr(ticker_data, 'dividends', None)
            if div_info:
                try:
                    # 格式: "0.6600,0.7800,20250610,0.1950"
                    # past12, next12, nextDate, nextAmount
                    parts = str(div_info).split(',')
                    if len(parts) >= 1 and parts[0]:
                        annual_div = float(parts[0])  # past 12 months dividends
                        # Get current price from ticker_data for dividend yield calculation
                        last = getattr(ticker_data, 'last', None)
                        close = getattr(ticker_data, 'close', None)
                        price = None
                        if self._is_valid_price(last):
                            price = float(last)
                        elif self._is_valid_price(close):
                            price = float(close)
                        
                        if price and price > 0 and annual_div > 0:
                            div_yield = annual_div / price
                            result['dividend_yield'] = div_yield
                            result['annual_dividend'] = annual_div
                            logger.info(f"  Tick 456 Div: ${annual_div:.4f}/年 → "
                                        f"Yield {div_yield*100:.2f}%  ← 直接使用 IBKR 數據")
                except (ValueError, IndexError):
                    pass

            # 取消訂閱
            try:
                self.ib.cancelMktData(stock)
            except Exception:
                pass

            logger.info(f"* Fix 11: {ticker} 完整數據獲取成功 "
                        f"(HV={'有' if 'historical_volatility' in result else '無'}, "
                        f"DivYield={'有' if 'dividend_yield' in result else '無'})")
            return result

        except Exception as e:
            self._record_error(0, str(e), f'get_stock_full_data({ticker})')
            logger.error(f"x Fix 11 獲取完整股票數據失敗: {e}")
            return None

    def get_dark_pool_ticks(
        self,
        ticker: str,
        duration_seconds: int    = 60,
        min_block_size: int      = DARK_POOL_BLOCK_SIZE,
        include_vwap: bool       = True,
        method: str              = 'both',   # 'diff' | 'exchange' | 'both'
    ) -> Optional[Dict[str, Any]]:
        """
        獲取 Dark Pool 訊號數據（雙方法交叉驗證）

        方法 A（差值法）── reqMktData + genericTickList='233,375'
          rtVolume   (Tick 48, tag 233) = 全部成交量（含 Dark Pool）
          rtTradeVolume (Tick 77, tag 375) = 只含可回報交易所成交量
          DP Volume = rtVolume_total - rtTradeVolume_total

        方法 B（Exchange 過濾法）── reqTickByTickData(AllLast) + exchange=='D'
          exchange=='D' 代表 FINRA ADF，即 Dark Pool 成交回報

        VWAP 來源（優先序）：
          1. Tick 48 rtVolume 字串第 5 欄（方法 A 附帶，最即時）
          2. Tick 74（tag 258），若方法 A 訂閱失敗時啟用

        參數:
            ticker:           股票代碼
            duration_seconds: 採樣時長（秒），建議生產環境用 300（5 分鐘）
            min_block_size:   大單門檻（股數），預設 10,000
            include_vwap:     是否解析 VWAP（略增 CPU）
            method:           'diff'（僅差值法）| 'exchange'（僅交易所過濾）| 'both'（雙重驗證）

        返回:
            {
              # ── 差值法結果（method A） ──────────────────────
              'rt_volume_total':      int,    # Tick 48 累計（全部成交）
              'rt_trade_volume_total': int,   # Tick 77 累計（可回報成交）
              'dp_volume_diff':       int,    # 差值法推算 DP 量 = Tick48 - Tick77
              'dp_ratio_diff':        float,  # DP 比例（差值法）0-100%

              # ── 交易所過濾法結果（method B） ──────────────────
              'dp_volume_exchange':   int,    # exchange=='D' 成交量合計
              'dp_ratio_exchange':    float,  # DP 比例（交易所過濾法）0-100%
              'dp_block_count':       int,    # 大單筆數（size >= min_block_size）
              'dp_block_volume':      int,    # 大單總量
              'dp_ticks':             List[TickByTickData],  # 原始 DP tick list

              # ── VWAP ─────────────────────────────────────────
              'vwap':                 float,  # 當前 VWAP（Tick 48 解析）

              # ── 交叉驗證 ─────────────────────────────────────
              'methods_agree':        bool,   # 兩方法 DP ratio 差距 < 5%
              'dp_ratio_consensus':   float,  # 兩方法平均（若 both）

              # ── Metadata ─────────────────────────────────────
              'ticker':               str,
              'duration_seconds':     int,
              'min_block_size':       int,
              'timestamp_start':      str,   # ISO 8601
              'timestamp_end':        str,
              'data_source':          'ibkr_dp',
              'warnings':             List[str],
            }
            None  ← 連線失敗或無法獲取數據
        """
        if not self.is_connected():
            if not self.connect():
                logger.warning(f"! {ticker}: IBKR 未連接，無法獲取 Dark Pool 數據")
                return None

        from datetime import datetime, timezone
        import math

        warnings: list = []
        result: Dict[str, Any] = {
            'ticker':           ticker,
            'duration_seconds': duration_seconds,
            'min_block_size':   min_block_size,
            'timestamp_start':  datetime.now(timezone.utc).isoformat(),
            'data_source':      'ibkr_dp',
            'warnings':         warnings,
            # 差值法預設
            'rt_volume_total':       0,
            'rt_trade_volume_total':  0,
            'dp_volume_diff':         0,
            'dp_ratio_diff':          0.0,
            # 交易所法預設
            'dp_volume_exchange':    0,
            'dp_ratio_exchange':     0.0,
            'dp_block_count':        0,
            'dp_block_volume':       0,
            'dp_ticks':              [],
            # VWAP
            'vwap':                  None,
            # 交叉驗證
            'methods_agree':         None,
            'dp_ratio_consensus':    None,
        }

        try:
            stock = Stock(ticker, 'SMART', 'USD')
            self.ib.qualifyContracts(stock)

            # ════════════════════════════════════════════════════
            # 方法 A：reqMktData + Tick 48 (233) + Tick 77 (375)
            # ════════════════════════════════════════════════════
            run_diff = method in ('diff', 'both')

            rt_volume_accum      = 0.0  # Tick 48 累計
            rt_trade_vol_accum   = 0.0  # Tick 77 累計
            last_vwap            = None

            if run_diff:
                # 構建 tick tag 字串
                tags_to_use = DARK_POOL_TICK_TAGS
                if include_vwap:
                    tags_to_use = DARK_POOL_TICK_TAGS + ',' + DARK_POOL_VWAP_TAG  # '233,258,375'

                logger.info(f"  方法 A：reqMktData with genericTickList='{tags_to_use}'")
                mkt_ticker = self.ib.reqMktData(stock, tags_to_use, False, False)

                # 等待 Tick 48 / 77 資料填入
                start_a = time.time()
                prev_rt_vol   = 0.0
                prev_rt_trade = 0.0

                while time.time() - start_a < duration_seconds:
                    self.ib.sleep(0.5)

                    # ── Tick 48: rtVolume 字串解析 ──────────────
                    # 格式: "price;size;unixTimeMs;totalVolume;vwap;singleTrade"
                    rt_vol_str = getattr(mkt_ticker, 'rtVolume', None)
                    if rt_vol_str:
                        try:
                            parts = str(rt_vol_str).split(';')
                            if len(parts) >= 4:
                                total_vol = float(parts[3])  # 累計總量（IBKR 原生）
                                if total_vol > prev_rt_vol:
                                    rt_volume_accum += (total_vol - prev_rt_vol)
                                    prev_rt_vol = total_vol

                                # VWAP 解析（第 5 欄）
                                if include_vwap and len(parts) >= 5:
                                    vwap_val = float(parts[4]) if parts[4] else None
                                    if vwap_val and not math.isnan(vwap_val) and vwap_val > 0:
                                        last_vwap = vwap_val
                        except (ValueError, IndexError):
                            pass

                    # ── Tick 77: rtTradeVolume（可回報成交） ────
                    rt_trade_vol = getattr(mkt_ticker, 'rtTradeVolume', None)
                    if rt_trade_vol is not None:
                        try:
                            tv = float(rt_trade_vol)
                            if not math.isnan(tv) and tv > prev_rt_trade:
                                rt_trade_vol_accum += (tv - prev_rt_trade)
                                prev_rt_trade = tv
                        except (TypeError, ValueError):
                            pass

                    # ── Tick 74: 備用 VWAP（若 Tick 48 沒有） ──
                    if include_vwap and last_vwap is None:
                        tick74_vwap = getattr(mkt_ticker, 'vwap', None)
                        if tick74_vwap is not None:
                            try:
                                v = float(tick74_vwap)
                                if not math.isnan(v) and v > 0:
                                    last_vwap = v
                            except (TypeError, ValueError):
                                pass

                # 取消訂閱
                try:
                    self.ib.cancelMktData(stock)
                except Exception:
                    pass

                # 填入差值法結果
                dp_diff = max(0, int(rt_volume_accum - rt_trade_vol_accum))
                total_a = int(rt_volume_accum)

                result['rt_volume_total']      = total_a
                result['rt_trade_volume_total'] = int(rt_trade_vol_accum)
                result['dp_volume_diff']        = dp_diff
                result['dp_ratio_diff']         = round(dp_diff / total_a * 100, 2) if total_a > 0 else 0.0
                result['vwap']                  = last_vwap

                if total_a == 0:
                    warnings.append("方法 A：duration 期間無 rtVolume 更新（可能非交易時段）")

                logger.info(
                    f"  方法 A 完成：rtVol={total_a}, rtTradeVol={int(rt_trade_vol_accum)}, "
                    f"DP={dp_diff} ({result['dp_ratio_diff']:.1f}%), VWAP={last_vwap}"
                )

            # ════════════════════════════════════════════════════
            # 方法 B：reqTickByTickData + exchange=='D' 過濾
            # ════════════════════════════════════════════════════
            run_exchange = method in ('exchange', 'both')

            dp_ticks_b:  list = []
            dp_vol_b:    int  = 0
            total_vol_b: int  = 0
            block_count  = 0
            block_vol    = 0

            if run_exchange:
                logger.info(f"  方法 B：reqTickByTickData AllLast, exchange_filter='D'")

                all_ticks_b:  list = []

                # 使用修正後的 req_tick_by_tick_data（注意：不傳 exchange_filter，自己篩）
                for tick in self.req_tick_by_tick_data(
                    contract=stock,
                    tick_type='AllLast',
                    exchange_filter=None,      # 先不過濾，讓所有 tick 流入以計算分母
                    timeout=float(duration_seconds),
                    max_ticks=None
                ):
                    all_ticks_b.append(tick)
                    total_vol_b += tick.size

                    if tick.exchange == DARK_POOL_EXCHANGE:
                        dp_ticks_b.append(tick)
                        dp_vol_b += tick.size

                        if tick.size >= min_block_size:
                            block_count += 1
                            block_vol   += tick.size

                result['dp_volume_exchange'] = dp_vol_b
                result['dp_ratio_exchange']  = round(dp_vol_b / total_vol_b * 100, 2) if total_vol_b > 0 else 0.0
                result['dp_block_count']     = block_count
                result['dp_block_volume']    = block_vol
                result['dp_ticks']           = dp_ticks_b   # 原始 DP tick list

                if total_vol_b == 0:
                    warnings.append("方法 B：duration 期間無 AllLast tick（可能非交易時段或 TWS 未授權）")

                logger.info(
                    f"  方法 B 完成：allTicks={len(all_ticks_b)}, DP ticks={len(dp_ticks_b)}, "
                    f"DP vol={dp_vol_b} ({result['dp_ratio_exchange']:.1f}%), "
                    f"block trades={block_count}"
                )

            # ════════════════════════════════════════════════════
            # 交叉驗證（method=='both' 時）
            # ════════════════════════════════════════════════════
            if run_diff and run_exchange:
                ratio_a = result['dp_ratio_diff']
                ratio_b = result['dp_ratio_exchange']
                diff_pct = abs(ratio_a - ratio_b)

                result['methods_agree']      = diff_pct < 5.0  # 差距 < 5% 視為一致
                result['dp_ratio_consensus'] = round((ratio_a + ratio_b) / 2, 2)

                if not result['methods_agree']:
                    warnings.append(
                        f"方法 A ({ratio_a:.1f}%) 與方法 B ({ratio_b:.1f}%) "
                        f"差距 {diff_pct:.1f}%，超過 5% 門檻，建議人工確認"
                    )
                logger.info(
                    f"  交叉驗證：agree={result['methods_agree']}, "
                    f"consensus DP ratio={result['dp_ratio_consensus']}%"
                )

            result['timestamp_end'] = datetime.now(timezone.utc).isoformat()
            return result

        except Exception as e:
            self._record_error(0, str(e), f'get_dark_pool_ticks({ticker})')
            logger.error(f"x get_dark_pool_ticks 失敗: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.disconnect()

    def get_discrete_dividends(self, ticker: str) -> list:
        """
        獲取未來離散股息時間表 (Discrete Dividends Schedule)
        使用 IBKR reqMktData 的 TickType 59 (IB Dividends).
        
        返回:
            list: 包含 (time_to_ex_date_years, dividend_amount) 的列表
        """
        if not self.is_connected():
            return []
            
        try:
            from ib_insync import Stock
            contract = Stock(ticker, 'SMART', 'USD')
            self.ib.qualifyContracts(contract)
            
            # 請求 tick type 59 包含 IB Dividends
            ticker_data = self.ib.reqMktData(contract, '59', snapshot=True, subscribe=False)
            self.ib.sleep(2)
            
            discrete_divs = []
            now = datetime.now()
            
            if ticker_data and ticker_data.dividends:
                div = ticker_data.dividends
                if getattr(div, 'nextDate', None) and getattr(div, 'nextAmount', None):
                    try:
                        ex_date = datetime.strptime(str(div.nextDate), "%Y%m%d")
                        if ex_date > now:
                            days_to_ex = (ex_date - now).days
                            years_to_ex = days_to_ex / 365.25
                            amount = float(div.nextAmount)
                            discrete_divs.append((years_to_ex, amount))
                            
                            # 簡單預測未來一年的股息 (假設每季度一次)
                            from datetime import timedelta
                            for i in range(1, 4):
                                projected_date = ex_date + timedelta(days=91.25 * i)
                                d_years = (projected_date - now).days / 365.25
                                if d_years > 0:
                                    discrete_divs.append((d_years, amount))
                            
                            logger.info(f"成功從 IBKR 獲取 {ticker} 離散股息: {discrete_divs}")
                    except Exception as e:
                        logger.warning(f"解析 IB 股息日期失敗 {ticker}: {e}")
            
            self.ib.cancelMktData(contract)
            return discrete_divs
            
        except Exception as e:
            logger.error(f"獲取 IBKR 離散股息失敗 {ticker}: {e}")
            return []
            
    def req_tick_by_tick_data(
        self,
        contract: Contract,
        tick_type: str = 'AllLast',
        exchange_filter: Optional[str] = None,
        timeout: float = 60.0,
        max_ticks: Optional[int] = None
    ) -> Generator[TickByTickData, None, None]:
        """
        Request tick-by-tick data stream with optional exchange filtering
        
        Fix: Dark Pool Patch 1.1 - 修正 ib_insync API 使用錯誤
        - 使用正確的屬性: tickByTickAllLasts / tickByTickBidAsks / tickByTickMidPoints
        - 修正 cancelTickByTickData 調用方式
        - 移除錯誤的 Tick 48/77 讀取邏輯（這些是 reqMktData 的屬性）
        
        Args:
            contract: IBKR contract object (Stock, Option, etc.)
            tick_type: Type of tick data ('Last', 'AllLast', 'BidAsk', 'MidPoint')
                      'AllLast' includes all trades including dark pools
            exchange_filter: Optional exchange filter ('D' for FINRA ADF/dark pools)
            timeout: Maximum time to stream data in seconds (default: 60.0)
            max_ticks: Optional maximum number of ticks to receive before stopping
        
        Yields:
            TickByTickData: Stream of tick-by-tick data objects
        
        Example:
            >>> client = IBKRClient()
            >>> client.connect()
            >>> contract = Stock('NVDA', 'SMART', 'USD')
            >>> # Stream for 30 seconds or until 100 ticks received
            >>> for tick in client.req_tick_by_tick_data(contract, 'AllLast', 'D', timeout=30.0, max_ticks=100):
            ...     print(f"Dark pool trade: {tick.price} x {tick.size}")
        """
        if not self.is_connected():
            logger.error("IBKR Gateway not connected")
            return

        try:
            self.ib.qualifyContracts(contract)

            ticker = self.ib.reqTickByTickData(
                contract=contract,
                tickType=tick_type,
                numberOfTicks=0,  # 0 = streaming
                ignoreSize=False
            )

            logger.info(
                f"Started tick-by-tick stream: {contract.symbol} "
                f"(type={tick_type}, exchange_filter={exchange_filter}, "
                f"timeout={timeout}s, max_ticks={max_ticks})"
            )

            start_time = time.time()
            tick_count = 0

            while self.is_connected():
                # Check timeout and max_ticks
                if time.time() - start_time >= timeout:
                    logger.info(f"Stream timeout after {timeout}s ({tick_count} ticks received)")
                    break
                if max_ticks is not None and tick_count >= max_ticks:
                    logger.info(f"Max ticks reached: {max_ticks}")
                    break

                # Let ib_insync event loop fill Ticker
                self.ib.sleep(0.02)

                # Read correct attribute based on tick_type
                if tick_type in ('AllLast', 'Last'):
                    raw_ticks = ticker.tickByTickAllLasts
                elif tick_type == 'BidAsk':
                    raw_ticks = ticker.tickByTickBidAsks
                elif tick_type == 'MidPoint':
                    raw_ticks = ticker.tickByTickMidPoints
                else:
                    raw_ticks = ticker.tickByTickAllLasts

                if not raw_ticks:
                    continue

                # Process and clear list to avoid duplicates
                batch = list(raw_ticks)
                raw_ticks.clear()  # Critical: clear processed ticks

                for tick in batch:
                    exchange = getattr(tick, 'exchange', '') or ''

                    # Exchange filter ('D' = FINRA ADF = Dark Pool)
                    if exchange_filter and exchange != exchange_filter:
                        continue

                    tick_data = TickByTickData(
                        ticker=contract.symbol,
                        timestamp=getattr(tick, 'time', datetime.now()),
                        price=float(getattr(tick, 'price', 0.0)),
                        size=int(getattr(tick, 'size', 0)),
                        exchange=exchange,
                        tick_type=tick_type,
                        tick_tags={}
                    )

                    tick_count += 1
                    yield tick_data

        except Exception as e:
            logger.error(f"req_tick_by_tick_data error: {e}")
            self._record_error(0, str(e), f'req_tick_by_tick_data({contract.symbol})')
        finally:
            # cancelTickByTickData needs contract + tickType, not req_id
            try:
                self.ib.cancelTickByTickData(contract, tick_type)
                logger.debug(f"Cancelled tick-by-tick: {contract.symbol} ({tick_type})")
            except Exception as e:
                logger.warning(f"Cancel tick-by-tick failed: {e}")





# 使用示例
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # 測試連接
    client = IBKRClient(mode='paper')
    
    if client.connect():
        print("* IBKR 連接成功")
        
        # 測試獲取期權鏈
        chain = client.get_option_chain('AAPL', '2024-12-20')
        if chain:
            print(f"* 獲取期權鏈成功: {len(chain['calls'])} calls")
        
        client.disconnect()
    else:
        print("x IBKR 連接失敗，請確保 TWS 或 IB Gateway 正在運行")

