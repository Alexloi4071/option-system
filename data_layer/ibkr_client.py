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
from typing import Dict, Optional, Any, List
from datetime import datetime, time as dt_time
import pytz

logger = logging.getLogger(__name__)

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
        '225': 'Auction Data - Volume/Price/Imbalance (Tick 34-36,61)',
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
    
    def __init__(self, host: str = "127.0.0.1", port: int = 7497, 
                 client_id: int = 100, mode: str = 'paper',
                 market_data_type: int = None,
                 tick_tag_categories: List[str] = None):
        """
        初始化 IBKR 客戶端
        
        參數:
            host: TWS/Gateway 主機地址 (默認 127.0.0.1)
            port: 端口 (7497=Paper, 7496=Live)
            client_id: 客戶端 ID (必須唯一)
            mode: 'paper' 或 'live'
            market_data_type: 強制指定 Market Data Type (1=Live, 2=Frozen)，None 為自動
            tick_tag_categories: Generic Tick Tags 類別，默認全部
        """
        if not IB_INSYNC_AVAILABLE:
            raise ImportError("ib_insync 未安裝，無法使用 IBKR 功能")
        
        self.host = host
        self.port = port
        self.client_id = client_id
        self.mode = mode
        self.ib = IB()
        self.connected = False
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
        
        logger.info(f"IBKR 客戶端初始化: {host}:{port} (mode={mode}, client_id={client_id})")
        logger.info(f"  Generic Tick Tags (期權): {self._generic_tick_list}")
    
    def connect(self, timeout: int = 10, market_data_type: int = None) -> bool:
        """
        連接到 TWS/Gateway（帶指數退避重試）
        
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
        
        while self.connection_attempts < self.max_connection_attempts:
            try:
                logger.info(f"嘗試連接 IBKR {self.host}:{self.port} (嘗試 {self.connection_attempts + 1}/{self.max_connection_attempts})...")
                self.ib.connect(
                    host=self.host,
                    port=self.port,
                    clientId=self.client_id,
                    timeout=timeout
                )
                
                if self.ib.isConnected():
                    self.connected = True
                    self.connection_attempts = 0
                    
                    # 動態設置 Market Data Type
                    self._apply_market_data_type(market_data_type)
                    
                    logger.info(f"* IBKR 連接成功 ({self.mode} mode)")
                    logger.info("  數據源配置:")
                    logger.info(f"    - Market Data Type: {self._current_market_data_type} ({self._get_market_data_type_name()})")
                    logger.info(f"    - Generic Tick Tags: {self._generic_tick_list}")
                    logger.info(f"    - 當前是否 RTH: {self.is_rth()}")
                    return True
                else:
                    logger.warning("! IBKR 連接後狀態異常：未連接")
                    self.connection_attempts += 1
                    
            except Exception as e:
                self.connection_attempts += 1
                self.last_error = str(e)
                self._record_error(0, str(e), 'connect')
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
                          known_stock_price: float = None) -> Optional[Dict[str, Any]]:
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
            dict: 包含 Greeks、數據質量指標、警告等完整信息
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
                result['impliedVol'] = greeks.get('impliedVol')
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
                result['greeks_source'] = 'unavailable'
                result['greeks_converged'] = False
            
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
                         expiration: str, option_type: str = 'C') -> Optional[Dict[str, Any]]:
        """
        獲取期權報價數據（優化版，使用完整 Tick Tags）
        
        這個方法專門獲取期權的基本報價數據，包含數據質量指標。
        
        參數:
            ticker: 股票代碼
            strike: 行使價
            expiration: 到期日期 (YYYY-MM-DD)
            option_type: 'C' (Call) 或 'P' (Put)
        
        返回:
            dict: 包含報價、數據質量、警告等完整信息
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
                    result['impliedVol'] = ticker_data.modelGreeks.impliedVol
                    result['undPrice'] = ticker_data.modelGreeks.undPrice
                    result['optPrice'] = ticker_data.modelGreeks.optPrice
                    result['greeks_source'] = 'ibkr_model'
                    
                    # 檢查 IV 異常
                    if result.get('impliedVol') and result['impliedVol'] > IV_SPIKE_THRESHOLD:
                        result['warnings'].append(f'IV 異常高 ({result["impliedVol"]*100:.1f}%)')
                        result['iv_spike_warning'] = True
                    
            except (ValueError, TypeError) as e:
                logger.debug(f"  處理報價數據時出錯: {e}")
            
            # 計算中間價
            if 'bid' in result and 'ask' in result:
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
            self.ib.reqMktData(option, '', False, False)
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
            self.ib.reqMktData(contract, '', False, False)
            time.sleep(0.5)  # 等待數據
            
            ticker_data = self.ib.ticker(contract)
            if not ticker_data:
                return None
            
            return {
                'strike': contract.strike,
                'expiration': contract.lastTradeDateOrContractMonth,
                'option_type': contract.right,
                'bid': float(ticker_data.bid) if ticker_data.bid else 0.0,
                'ask': float(ticker_data.ask) if ticker_data.ask else 0.0,
                'last': float(ticker_data.last) if ticker_data.last else 0.0,
                'volume': int(ticker_data.volume) if ticker_data.volume else 0,
                'open_interest': int(ticker_data.openInterest) if ticker_data.openInterest else 0,
                'implied_volatility': float(ticker_data.impliedVolatility) * 100 if ticker_data.impliedVolatility else None,  # 轉換為百分比
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
            
            # 使用 reqMktData (Snapshot)
            self.ib.reqMktData(contract, '', True, False)
            
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
        獲取期權鏈快照（結構 + 實時數據）
        
        高效獲取整個期權鏈的實時數據。
        策略：
        1. 獲取所有合約
        2. 過濾（如果指定了 center_strike，只獲取附近的合約，例如 +/- 20%）
        3. 批量請求快照數據
        4. 收集結果
        
        參數:
            ticker: 股票代碼
            expiration: 到期日
            center_strike: 中心行使價（通常是當前股價），用於過濾。如果為 None 則獲取全部（慎用）
            
        返回:
            dict: 包含 'calls', 'puts' DataFrames
        """
        if not self.is_connected() and not self.connect():
            return None
            
        import math  # Move import here to fix UnboundLocalError
            
        try:
            logger.info(f"正在獲取 {ticker} {expiration} 期權鏈快照 (Base)...")
            
            # 1. 獲取鏈結構
            self.refresh_market_data_type()
            
            # 格式化日期
            exp_formatted = expiration.replace('-', '')
            
            # 查找合約
            # 為了效率，我們直接使用 reqSecDefOptParams (如果已經有緩存最好，這裡簡化)
            # 復用 get_option_chain 的邏輯獲取合約列表
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
            
            # 直接請求 snapshot=False (使用流式數據短暫抓取)
            # 原因: IBKR API 的纯 Snapshot 模式 (True) 經常會忽略 Generic Ticks (如 Greeks, 100, 101, 104, 106)。
            # 使用流式訂閱 + 短暫等待 + 取消訂閱 (即 "Streaming Burst") 是確保獲取完整 Greeks 數據的官方推薦做法。
            for contract in all_contracts:
                self.ib.reqMktData(contract, self._generic_tick_list, False, False) 
            
            # 3. 等待數據填充
            # 這裡我們等待最多 8 秒
            start_time = time.time()
            while time.time() - start_time < 8:
                self.ib.sleep(0.2)
                # 檢查是否還有未返回數據的（簡單檢查 last/bid/ask 任意一個）
                pending = 0
                for c in all_contracts:
                    t = self.ib.ticker(c)
                    has_data =  (t.last and not  math.isnan(t.last)) or \
                                (t.bid and not math.isnan(t.bid)) or \
                                (t.modelGreeks and t.modelGreeks.impliedVol)
                    if not has_data:
                        pending += 1
                
                if pending == 0:
                    break
                # Fast exit if most are done? Maybe not.
                    
            # 4. 收集結果
            call_data = []
            put_data = []
            
            for contract in all_contracts:
                t = self.ib.ticker(contract)
                
                # 提取數據 - 使用安全的屬性獲取方式
                def safe_int(val, default=0):
                    """安全轉換為整數，處理 None 和 NaN"""
                    if val is None:
                        return default
                    try:
                        if math.isnan(val):
                            return default
                        return int(val)
                    except (TypeError, ValueError):
                        return default
                
                # 獲取 Open Interest（根據期權類型選擇正確的屬性）
                # 對於期權合約，IBKR 可能返回:
                # - callOpenInterest / putOpenInterest (Tick 27/28 via generic tick 101)
                # - 或直接的 openInterest 屬性
                oi = None
                call_oi = getattr(t, 'callOpenInterest', None)
                put_oi = getattr(t, 'putOpenInterest', None) 
                generic_oi = getattr(t, 'openInterest', None)
                
                if contract.right == 'C':
                    oi = call_oi or generic_oi
                else:
                    oi = put_oi or generic_oi
                
                # DEBUG: 記錄第一個合約的 OI 信息
                if contract == all_contracts[0]:
                    logger.debug(f"  [OI Debug] Contract: {contract.localSymbol}")
                    logger.debug(f"    callOpenInterest: {call_oi}, putOpenInterest: {put_oi}, openInterest: {generic_oi}")
                    logger.debug(f"    Ticker attrs: {[a for a in dir(t) if 'interest' in a.lower() or 'oi' in a.lower()]}")
                
                item = {
                    'contractSymbol': ticker,
                    'strike': contract.strike,
                    'currency': 'USD',
                    'lastPrice': t.last if self._is_valid_price(t.last) else 0.0,
                    'bid': t.bid if self._is_valid_price(t.bid) else 0.0,
                    'ask': t.ask if self._is_valid_price(t.ask) else 0.0,
                    'volume': safe_int(t.volume),
                    'openInterest': safe_int(oi),
                    'impliedVolatility': t.modelGreeks.impliedVol * 100 if t.modelGreeks and t.modelGreeks.impliedVol else None,
                    'delta': t.modelGreeks.delta if t.modelGreeks else None,
                    'gamma': t.modelGreeks.gamma if t.modelGreeks else None,
                    'theta': t.modelGreeks.theta if t.modelGreeks else None,
                    'vega': t.modelGreeks.vega if t.modelGreeks else None,
                    'inTheMoney': False,
                    'expiration': expiration
                }
                
                # 填充 greeks_source
                if item['delta'] is not None:
                    item['greeks_source'] = 'ibkr'
                
                if contract.right == 'C':
                    call_data.append(item)
                else:
                    put_data.append(item)
            
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

    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.disconnect()


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

