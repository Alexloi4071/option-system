# data_layer/data_policy.py
"""
數據來源策略與 Schema 定義

定義系統中所有數據欄位的權責來源、標準 schema 和單位規範。
這是整個數據層的 single source of truth。

設計原則:
1. 欄位級權責（Field Authority）而非整包 fallback
2. 明確的數據來源優先級
3. 統一的 schema 和單位標準
4. 可追溯的數據來源 metadata

Ref: option-data-review.md Section I, IV Stage 1
"""

from typing import TypedDict, Literal, Optional, List, Dict, Any
from enum import Enum


# ============================================================================
# 數據來源常數定義
# ============================================================================

class DataSource(str, Enum):
    """數據來源枚舉"""
    # 主要數據源
    FINNHUB = 'finnhub'
    FINVIZ = 'finviz'
    IBKR_SNAPSHOT = 'ibkr_snapshot'
    IBKR_TICK = 'ibkr_tick'
    
    # 備用數據源
    ALPHA_VANTAGE = 'alpha_vantage'
    YAHOO_V2 = 'yahoo_v2'
    YFINANCE = 'yfinance'
    RAPIDAPI = 'rapidapi'
    MASSIVE_API = 'massive_api'
    
    # 計算來源
    LOCAL_BS = 'local_black_scholes'
    LOCAL_GREEKS = 'local_greeks_calculator'
    
    # 特殊標記
    EMPTY = 'empty'
    UNKNOWN = 'unknown'


# ============================================================================
# IV/HV 單位標準
# ============================================================================

class VolatilityUnit(str, Enum):
    """波動率單位標準"""
    PERCENTAGE = 'percentage'  # 百分比格式: 0-100 (例如 25 表示 25%)
    DECIMAL = 'decimal'        # 小數格式: 0-1 (例如 0.25 表示 25%)


# 系統統一使用百分比格式 (0-100)
VOLATILITY_UNIT_STANDARD = VolatilityUnit.PERCENTAGE

# IV/HV 有效範圍
IV_MIN_VALID = 1.0      # 最小有效 IV: 1%
IV_MAX_VALID = 500.0    # 最大有效 IV: 500%
IV_ABNORMAL_HIGH = 200.0  # 異常高 IV 閾值: 200%
IV_ABNORMAL_LOW = 5.0     # 異常低 IV 閾值: 5%


# ============================================================================
# 欄位權責表 (Field Authority Map)
# ============================================================================

# 股票報價欄位權責
STOCK_QUOTE_AUTHORITY: Dict[str, List[str]] = {
    'current_price': [DataSource.FINNHUB, DataSource.ALPHA_VANTAGE, DataSource.YFINANCE],
    'open': [DataSource.FINNHUB, DataSource.ALPHA_VANTAGE, DataSource.YFINANCE],
    'intraday_high': [DataSource.FINNHUB, DataSource.ALPHA_VANTAGE, DataSource.YFINANCE],
    'intraday_low': [DataSource.FINNHUB, DataSource.ALPHA_VANTAGE, DataSource.YFINANCE],
    'previous_close': [DataSource.FINNHUB, DataSource.ALPHA_VANTAGE, DataSource.YFINANCE],
    'volume': [DataSource.FINNHUB, DataSource.ALPHA_VANTAGE, DataSource.YFINANCE],
    'change': [DataSource.FINNHUB, DataSource.ALPHA_VANTAGE, DataSource.YFINANCE],
    'change_percent': [DataSource.FINNHUB, DataSource.ALPHA_VANTAGE, DataSource.YFINANCE],
}

# 股票基本面欄位權責
STOCK_FUNDAMENTALS_AUTHORITY: Dict[str, List[str]] = {
    'market_cap': [DataSource.FINVIZ, DataSource.FINNHUB, DataSource.ALPHA_VANTAGE],
    'pe_ratio': [DataSource.FINVIZ, DataSource.FINNHUB, DataSource.ALPHA_VANTAGE],
    'forward_pe': [DataSource.FINVIZ, DataSource.ALPHA_VANTAGE],
    'peg_ratio': [DataSource.FINVIZ],
    'eps': [DataSource.FINVIZ, DataSource.FINNHUB, DataSource.ALPHA_VANTAGE],
    'eps_ttm': [DataSource.FINVIZ],
    'eps_next_y': [DataSource.FINVIZ],
    'beta': [DataSource.FINVIZ, DataSource.FINNHUB, DataSource.ALPHA_VANTAGE],
    'sector': [DataSource.FINVIZ, DataSource.FINNHUB],
    'industry': [DataSource.FINVIZ, DataSource.FINNHUB],
    'company_name': [DataSource.FINVIZ, DataSource.FINNHUB],
    'profit_margin': [DataSource.FINVIZ],
    'operating_margin': [DataSource.FINVIZ],
    'roe': [DataSource.FINVIZ],
    'roa': [DataSource.FINVIZ],
    'debt_eq': [DataSource.FINVIZ],
    'insider_own': [DataSource.FINVIZ],
    'inst_own': [DataSource.FINVIZ],
    'short_float': [DataSource.FINVIZ],
}

# 股票進階欄位權責（IBKR 專屬）
STOCK_ADVANCED_AUTHORITY: Dict[str, List[str]] = {
    'historical_volatility_30d': [DataSource.IBKR_TICK, DataSource.FINNHUB],
    'implied_volatility_30d': [DataSource.IBKR_TICK],
    'dividend_yield': [DataSource.IBKR_TICK, DataSource.FINVIZ, DataSource.YFINANCE],
    'annual_dividend': [DataSource.IBKR_TICK, DataSource.YFINANCE],
    'mark_price': [DataSource.IBKR_TICK],
}

# 期權鏈欄位權責
OPTION_CHAIN_AUTHORITY: Dict[str, List[str]] = {
    'strike': [DataSource.IBKR_SNAPSHOT, DataSource.YFINANCE],
    'expiration': [DataSource.IBKR_SNAPSHOT, DataSource.YFINANCE],
    'option_type': [DataSource.IBKR_SNAPSHOT, DataSource.YFINANCE],
    'bid': [DataSource.IBKR_SNAPSHOT, DataSource.YFINANCE],
    'ask': [DataSource.IBKR_SNAPSHOT, DataSource.YFINANCE],
    'lastPrice': [DataSource.IBKR_SNAPSHOT, DataSource.YFINANCE],
    'markPrice': [DataSource.IBKR_SNAPSHOT],
    'volume': [DataSource.IBKR_SNAPSHOT, DataSource.YFINANCE],
    'openInterest': [DataSource.IBKR_SNAPSHOT, DataSource.YFINANCE],
    'impliedVolatility': [DataSource.IBKR_SNAPSHOT, DataSource.YFINANCE],
    'delta': [DataSource.IBKR_SNAPSHOT, DataSource.LOCAL_GREEKS],
    'gamma': [DataSource.IBKR_SNAPSHOT, DataSource.LOCAL_GREEKS],
    'theta': [DataSource.IBKR_SNAPSHOT, DataSource.LOCAL_GREEKS],
    'vega': [DataSource.IBKR_SNAPSHOT, DataSource.LOCAL_GREEKS],
    'rho': [DataSource.IBKR_SNAPSHOT, DataSource.LOCAL_GREEKS],
}


# ============================================================================
# 標準 Schema 定義
# ============================================================================

class StockQuoteSchema(TypedDict, total=False):
    """股票報價 Schema（實時價格與技術數據）"""
    ticker: str
    current_price: float
    open: float
    intraday_high: float  # 盤中最高（未結算）
    intraday_low: float   # 盤中最低（未結算）
    previous_close: float
    volume: int
    change: float
    change_percent: float
    data_source: str
    data_timestamp: str
    is_market_hours: bool


class StockFundamentalsSchema(TypedDict, total=False):
    """股票基本面 Schema"""
    ticker: str
    market_cap: float
    pe_ratio: float
    forward_pe: float
    peg_ratio: float
    eps: float
    eps_ttm: float
    eps_next_y: float
    beta: float
    sector: str
    industry: str
    company_name: str
    profit_margin: float
    operating_margin: float
    roe: float
    roa: float
    debt_eq: float
    insider_own: float
    inst_own: float
    short_float: float
    data_source: str


class StockAdvancedSchema(TypedDict, total=False):
    """股票進階數據 Schema（IBKR 專屬）"""
    ticker: str
    historical_volatility_30d: float  # 百分比格式 (0-100)
    implied_volatility_30d: float     # 百分比格式 (0-100)
    dividend_yield: float             # 小數格式 (0-1)
    annual_dividend: float
    mark_price: float
    hv_source: str
    div_source: str
    data_source: str


class StockSnapshotSchema(TypedDict, total=False):
    """完整股票快照 Schema（合併 Quote + Fundamentals + Advanced）"""
    # 基本信息
    ticker: str
    
    # Quote 欄位
    current_price: float
    open: float
    intraday_high: float
    intraday_low: float
    previous_close: float
    volume: int
    change: float
    change_percent: float
    
    # Fundamentals 欄位
    market_cap: float
    pe_ratio: float
    forward_pe: float
    peg_ratio: float
    eps: float
    eps_ttm: float
    eps_next_y: float
    beta: float
    sector: str
    industry: str
    company_name: str
    profit_margin: float
    operating_margin: float
    roe: float
    roa: float
    debt_eq: float
    insider_own: float
    inst_own: float
    short_float: float
    
    # Advanced 欄位
    historical_volatility_30d: float
    implied_volatility_30d: float
    dividend_yield: float
    annual_dividend: float
    mark_price: float
    
    # Metadata
    field_sources: Dict[str, str]  # 欄位級來源追蹤
    data_quality: str              # 'complete', 'partial', 'minimal'
    data_timestamp: str
    is_market_hours: bool


class OptionSnapshotSchema(TypedDict, total=False):
    """期權快照 Schema（統一格式）"""
    # 合約識別
    ticker: str
    strike: float
    expiration: str  # YYYY-MM-DD
    option_type: Literal['C', 'P']
    
    # 價格數據
    bid: float
    ask: float
    lastPrice: float
    markPrice: float
    
    # 成交量與持倉
    volume: int
    openInterest: int
    
    # Greeks
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float
    
    # 波動率（統一為百分比格式 0-100）
    impliedVolatility: float
    
    # Metadata
    greeks_source: str  # 'ibkr', 'local_calculation'
    iv_source: str
    data_source: str
    data_quality: str


class HistoricalBarSchema(TypedDict, total=False):
    """歷史 K 線 Schema"""
    ticker: str
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    data_source: str


# ============================================================================
# 數據質量評估
# ============================================================================

class DataQuality(str, Enum):
    """數據質量等級"""
    COMPLETE = 'complete'    # 所有必需欄位都有有效值
    PARTIAL = 'partial'      # 部分必需欄位缺失
    MINIMAL = 'minimal'      # 僅有最基本欄位
    INVALID = 'invalid'      # 數據無效


# 必需欄位定義
STOCK_QUOTE_REQUIRED_FIELDS = ['ticker', 'current_price']
STOCK_FUNDAMENTALS_REQUIRED_FIELDS = ['ticker', 'market_cap', 'pe_ratio', 'eps']
OPTION_SNAPSHOT_REQUIRED_FIELDS = ['strike', 'expiration', 'option_type', 'bid', 'ask', 'impliedVolatility']


# ============================================================================
# 輔助函數
# ============================================================================

def get_field_authority(field_name: str, data_type: str = 'stock_quote') -> List[str]:
    """
    獲取欄位的權責來源列表
    
    參數:
        field_name: 欄位名稱
        data_type: 數據類型 ('stock_quote', 'stock_fundamentals', 'stock_advanced', 'option_chain')
    
    返回:
        List[str]: 數據來源優先級列表
    """
    authority_map = {
        'stock_quote': STOCK_QUOTE_AUTHORITY,
        'stock_fundamentals': STOCK_FUNDAMENTALS_AUTHORITY,
        'stock_advanced': STOCK_ADVANCED_AUTHORITY,
        'option_chain': OPTION_CHAIN_AUTHORITY,
    }
    
    authority = authority_map.get(data_type, {})
    return authority.get(field_name, [DataSource.UNKNOWN])


def assess_data_quality(data: Dict[str, Any], required_fields: List[str]) -> DataQuality:
    """
    評估數據質量
    
    參數:
        data: 數據字典
        required_fields: 必需欄位列表
    
    返回:
        DataQuality: 數據質量等級
    """
    if not data:
        return DataQuality.INVALID
    
    valid_count = sum(1 for field in required_fields if data.get(field) is not None)
    
    if valid_count == len(required_fields):
        return DataQuality.COMPLETE
    elif valid_count >= len(required_fields) * 0.5:
        return DataQuality.PARTIAL
    elif valid_count > 0:
        return DataQuality.MINIMAL
    else:
        return DataQuality.INVALID


def normalize_volatility(value: float, from_unit: VolatilityUnit) -> float:
    """
    標準化波動率值到系統標準單位（百分比）
    
    參數:
        value: 原始波動率值
        from_unit: 原始單位
    
    返回:
        float: 標準化後的值（百分比格式 0-100）
    """
    if from_unit == VolatilityUnit.DECIMAL:
        return value * 100
    return value


def validate_volatility(value: float) -> bool:
    """
    驗證波動率值是否在有效範圍內
    
    參數:
        value: 波動率值（百分比格式）
    
    返回:
        bool: 是否有效
    """
    return IV_MIN_VALID <= value <= IV_MAX_VALID
