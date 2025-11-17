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
    IBKR_ACCOUNT_ID = os.getenv("IBKR_ACCOUNT_ID", "")
    
    # RapidAPI設置
    RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")
    RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST", "yahoo-finance127.p.rapidapi.com")
    
    # Yahoo Finance 2.0 API設置 (Official OAuth)
    YAHOO_APP_ID = os.getenv("YAHOO_APP_ID", "")
    YAHOO_CLIENT_ID = os.getenv("YAHOO_CLIENT_ID", "")
    YAHOO_CLIENT_SECRET = os.getenv("YAHOO_CLIENT_SECRET", "")
    YAHOO_REDIRECT_URI = os.getenv("YAHOO_REDIRECT_URI", "https://yourdomain.com/callback")
    
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
    CACHE_TTL = 3600  # 秒
    CACHE_DIR = "cache/"
    
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
        
        if not cls.FRED_API_KEY:
            warnings.append("FRED_API_KEY未設置，無風險利率和VIX功能不可用")
        
        if not cls.FINNHUB_API_KEY:
            warnings.append("FINNHUB_API_KEY未設置，業績和派息監察功能不可用")
        
        if not cls.RAPIDAPI_KEY:
            warnings.append("RAPIDAPI_KEY未設置，備用數據源不可用")
        
        if not cls.YAHOO_CLIENT_ID or not cls.YAHOO_CLIENT_SECRET:
            warnings.append("Yahoo Finance 2.0 API未完整配置，OAuth功能不可用")
        
        # IBKR 配置檢查（僅在啟用時檢查）
        if cls.IBKR_ENABLED:
            if not cls.IBKR_HOST:
                warnings.append("IBKR_HOST 未配置，已啟用 IBKR 但缺少主機設定")
            if cls.IBKR_CLIENT_ID is None:
                warnings.append("IBKR_CLIENT_ID 未配置，已啟用 IBKR 但缺少 Client ID")
            # IBKR 未配置時不報錯，僅記錄信息（將使用降級方案）
        # 注意：IBKR 未啟用時不顯示警告，因為這是正常的降級情況
        
        if warnings:
            print("⚠ 配置警告:")
            for i, warning in enumerate(warnings, 1):
                print(f"  {i}. {warning}")
        else:
            print("✓ 所有API Keys已正確配置")
        
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
