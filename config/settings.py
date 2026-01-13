# config/settings.py
"""
全局系統設置
"""

import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import pytz

load_dotenv()


class Settings:
    """全局系統設置"""
    
    # 基本設置
    PROJECT_NAME = "Options Trading System"
    VERSION = "1.0.0"
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    TIMEZONE = pytz.timezone('America/New_York')
    
    # API設置
    FRED_API_KEY = os.getenv("FRED_API_KEY", "")
    FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")
    IBKR_ENABLED = os.getenv("IBKR_ENABLED", "False").lower() == "true"
    IBKR_HOST = os.getenv("IBKR_HOST", "127.0.0.1")
    IBKR_PORT_PAPER = int(os.getenv("IBKR_PORT_PAPER", "7497"))
    IBKR_PORT_LIVE = int(os.getenv("IBKR_PORT_LIVE", "7496"))
    IBKR_CLIENT_ID = int(os.getenv("IBKR_CLIENT_ID", "100"))
    IBKR_USE_PAPER = os.getenv("IBKR_USE_PAPER", "True").lower() == "true"  # 使用 Paper Trading
    IBKR_ACCOUNT_ID = os.getenv("IBKR_ACCOUNT_ID", "")
    
    # IBKR API 優化配置
    IBKR_GREEKS_TIMEOUT = int(os.getenv("IBKR_GREEKS_TIMEOUT", "10"))  # Greeks 收斂超時（秒）
    IBKR_GREEKS_STABILIZATION = int(os.getenv("IBKR_GREEKS_STABILIZATION", "3"))  # 穩定等待（秒）
    IBKR_TICK_TAG_CATEGORIES = os.getenv("IBKR_TICK_TAG_CATEGORIES", "CORE,RECOMMENDED,ADVANCED")  # Tick Tags 類別
    IBKR_REJECT_OUTSIDE_RTH = os.getenv("IBKR_REJECT_OUTSIDE_RTH", "False").lower() == "true"  # 拒絕盤外數據
    IBKR_IV_SPIKE_THRESHOLD = float(os.getenv("IBKR_IV_SPIKE_THRESHOLD", "3.0"))  # 300% IV 異常閾值
    IBKR_PRICE_MISMATCH_THRESHOLD = float(os.getenv("IBKR_PRICE_MISMATCH_THRESHOLD", "0.01"))  # 1% 價格偏差閾值
    
    # RapidAPI設置
    RAPIDAPI_ENABLED = os.getenv("RAPIDAPI_ENABLED", "True").lower() == "true"
    RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")
    RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST", "yahoo-finance127.p.rapidapi.com")
    RAPIDAPI_MONTHLY_LIMIT = int(os.getenv("RAPIDAPI_MONTHLY_LIMIT", "500"))
    
    # Alpha Vantage 設置
    ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "")
    
    # Massive API 設置
    MASSIVE_API_KEY = os.getenv("MASSIVE_API_KEY", "")
    
    # Yahoo Finance API 設置（公開API，無需認證）
    # 注意：Yahoo Finance API 已簡化，不需要 OAuth 認證
    # 系統會自動添加必需的 User-Agent header
    
    # 數據源設置
    PRIMARY_DATA_SOURCE = "yahoo_v2"  # 改为使用 Yahoo Finance 2.0
    FALLBACK_DATA_SOURCE = "yfinance"  # yfinance 作为降级方案
    BACKUP_DATA_SOURCE = "finnhub"
    
    # API 请求控制
    REQUEST_DELAY = float(os.getenv("REQUEST_DELAY", "2.0"))  # API请求间隔（秒）- 增加到2秒避免限流
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))  # 最大重试次数
    RETRY_DELAY = float(os.getenv("RETRY_DELAY", "5"))  # 重试延迟（秒）
    
    # 緩存設置
    ENABLE_CACHE = True
    CACHE_TTL = 3600  # 秒（默認緩存時長）
    CACHE_DIR = "cache/"
    
    # 不同數據類型的緩存時長（秒）
    # 這些設置允許根據數據的時效性需求設置不同的緩存時長
    CACHE_DURATION_STOCK_INFO = int(os.getenv("CACHE_DURATION_STOCK_INFO", "300"))  # 股票信息: 5分鐘
    CACHE_DURATION_OPTION_CHAIN = int(os.getenv("CACHE_DURATION_OPTION_CHAIN", "60"))  # 期權鏈: 1分鐘
    CACHE_DURATION_HISTORICAL = int(os.getenv("CACHE_DURATION_HISTORICAL", "3600"))  # 歷史數據: 1小時
    CACHE_DURATION_EARNINGS = int(os.getenv("CACHE_DURATION_EARNINGS", "3600"))  # 業績日曆: 1小時
    CACHE_DURATION_DIVIDEND = int(os.getenv("CACHE_DURATION_DIVIDEND", "3600"))  # 派息日曆: 1小時
    CACHE_DURATION_VIX = int(os.getenv("CACHE_DURATION_VIX", "60"))  # VIX: 1分鐘
    CACHE_DURATION_RISK_FREE_RATE = int(os.getenv("CACHE_DURATION_RISK_FREE_RATE", "3600"))  # 無風險利率: 1小時
    CACHE_DURATION_FUNDAMENTALS = int(os.getenv("CACHE_DURATION_FUNDAMENTALS", "1800"))  # 基本面數據: 30分鐘
    
    # 錯誤處理設置
    MAX_API_FAILURE_RECORDS = int(os.getenv("MAX_API_FAILURE_RECORDS", "100"))  # 每個 API 最多保留的故障記錄數
    API_FAILURE_RETENTION_HOURS = int(os.getenv("API_FAILURE_RETENTION_HOURS", "24"))  # 故障記錄保留時間（小時）
    
    # 功能開關設置
    ENABLE_ENHANCED_FINVIZ = os.getenv("ENABLE_ENHANCED_FINVIZ", "True").lower() == "true"  # 啟用增強版 Finviz 錯誤處理
    
    # 時間設置
    MARKET_OPEN_TIME = "09:30"
    MARKET_CLOSE_TIME = "16:00"
    
    # 計算參數 (來自書籍)
    IV_DIVIDER = 3.464          # √12
    DAYS_PER_YEAR = 365
    OPTION_MULTIPLIER = 100
    DEFAULT_TRADING_FEE = 0.10
    
    # PE估值範圍 (來自書籍第十課)
    PE_BEAR_MARKET = 8.5        # 熊市
    PE_BULL_MARKET = 25.0       # 牛市
    PE_NORMAL = 15.0            # 正常
    
    # 日誌設置
    LOG_DIR = "logs/"
    LOG_LEVEL = "INFO"
    
    # 輸出目錄
    OUTPUT_DIR = "output/"
    
    @classmethod
    def validate(cls):
        """驗證配置"""
        warnings = []
        errors = []
        
        # API Keys 驗證
        if not cls.FRED_API_KEY:
            warnings.append("FRED_API_KEY未設置，無風險利率和VIX功能不可用")
        
        if not cls.FINNHUB_API_KEY:
            warnings.append("FINNHUB_API_KEY未設置，業績和派息監察功能不可用")
        
        # RapidAPI 配置驗證
        if cls.RAPIDAPI_ENABLED:
            if not cls.RAPIDAPI_KEY:
                warnings.append("RAPIDAPI_KEY未設置，RapidAPI備用數據源不可用")
            if not cls.RAPIDAPI_HOST:
                warnings.append("RAPIDAPI_HOST未設置，RapidAPI備用數據源不可用")
            if cls.RAPIDAPI_MONTHLY_LIMIT <= 0:
                errors.append("RAPIDAPI_MONTHLY_LIMIT必須大於0")
        
        if not cls.ALPHA_VANTAGE_API_KEY:
            warnings.append("ALPHA_VANTAGE_API_KEY未設置，Alpha Vantage功能不可用")
        
        if not cls.MASSIVE_API_KEY:
            warnings.append("MASSIVE_API_KEY未設置，Massive API功能不可用")
        
        # IBKR 配置檢查（僅在啟用時檢查）
        if cls.IBKR_ENABLED:
            if not cls.IBKR_HOST:
                warnings.append("IBKR_HOST 未配置，已啟用 IBKR 但缺少主機設定")
            if cls.IBKR_CLIENT_ID is None:
                warnings.append("IBKR_CLIENT_ID 未配置，已啟用 IBKR 但缺少 Client ID")
            # IBKR 未配置時不報錯，僅記錄信息（將使用降級方案）
        # 注意：IBKR 未啟用時不顯示警告，因為這是正常的降級情況
        
        # 緩存設置驗證
        cache_settings = [
            ('CACHE_DURATION_STOCK_INFO', cls.CACHE_DURATION_STOCK_INFO),
            ('CACHE_DURATION_OPTION_CHAIN', cls.CACHE_DURATION_OPTION_CHAIN),
            ('CACHE_DURATION_HISTORICAL', cls.CACHE_DURATION_HISTORICAL),
            ('CACHE_DURATION_EARNINGS', cls.CACHE_DURATION_EARNINGS),
            ('CACHE_DURATION_DIVIDEND', cls.CACHE_DURATION_DIVIDEND),
            ('CACHE_DURATION_VIX', cls.CACHE_DURATION_VIX),
            ('CACHE_DURATION_RISK_FREE_RATE', cls.CACHE_DURATION_RISK_FREE_RATE),
            ('CACHE_DURATION_FUNDAMENTALS', cls.CACHE_DURATION_FUNDAMENTALS),
        ]
        for name, value in cache_settings:
            if value < 0:
                errors.append(f"{name}必須大於或等於0")
        
        # 錯誤處理設置驗證
        if cls.MAX_API_FAILURE_RECORDS <= 0:
            errors.append("MAX_API_FAILURE_RECORDS必須大於0")
        if cls.API_FAILURE_RETENTION_HOURS <= 0:
            errors.append("API_FAILURE_RETENTION_HOURS必須大於0")
        
        # API 請求控制驗證
        if cls.REQUEST_DELAY < 0:
            errors.append("REQUEST_DELAY必須大於或等於0")
        if cls.MAX_RETRIES < 0:
            errors.append("MAX_RETRIES必須大於或等於0")
        if cls.RETRY_DELAY < 0:
            errors.append("RETRY_DELAY必須大於或等於0")
        
        # 輸出驗證結果
        if errors:
            print("[ERROR] 配置錯誤:")
            for i, error in enumerate(errors, 1):
                print(f"  {i}. {error}")
            return False
        
        if warnings:
            print("[WARN] 配置警告:")
            for i, warning in enumerate(warnings, 1):
                print(f"  {i}. {warning}")
        else:
            print("[OK] 所有API Keys已正確配置")
        
        return True
    
    @classmethod
    def create_directories(cls):
        """創建必需的目錄"""
        for directory in [cls.LOG_DIR, cls.CACHE_DIR, cls.OUTPUT_DIR]:
            os.makedirs(directory, exist_ok=True)


settings = Settings()

# 初始化
settings.create_directories()
settings.validate()
