# config/api_config.py
"""
API配置

本模塊定義了系統支持的所有 API 數據源的配置信息，包括：
- API 名稱和類型
- 速率限制
- 認證要求
- 提供的數據類型
- 數據優先級

配置說明:
-----------
所有 API Keys 和敏感配置應存儲在 .env 文件中，而非此文件。
此文件僅定義 API 的元數據和行為配置。

環境變量配置 (.env):
-------------------
# RapidAPI 配置
RAPIDAPI_ENABLED=True           # 是否啟用 RapidAPI
RAPIDAPI_KEY=your_api_key       # API 密鑰
RAPIDAPI_HOST=yahoo-finance127.p.rapidapi.com  # API 主機
RAPIDAPI_MONTHLY_LIMIT=500      # 每月請求限制

# 緩存配置
CACHE_DURATION_STOCK_INFO=300   # 股票信息緩存時長（秒）
CACHE_DURATION_OPTION_CHAIN=60  # 期權鏈緩存時長（秒）
CACHE_DURATION_HISTORICAL=3600  # 歷史數據緩存時長（秒）
CACHE_DURATION_EARNINGS=3600    # 業績日曆緩存時長（秒）
CACHE_DURATION_VIX=60           # VIX 緩存時長（秒）

# 錯誤處理配置
MAX_API_FAILURE_RECORDS=100     # 每個 API 最多保留的故障記錄數
API_FAILURE_RETENTION_HOURS=24  # 故障記錄保留時間（小時）

# 功能開關
ENABLE_ENHANCED_FINVIZ=True     # 啟用增強版 Finviz 錯誤處理

使用示例:
--------
>>> from config.api_config import api_config
>>> print(api_config.RAPIDAPI['rate_limit'])
500
>>> print(api_config.DATA_PRIORITY['stock_price'])
['ibkr', 'finviz', 'alpha_vantage', 'yfinance', 'yahoo_v2', 'finnhub', 'rapidapi']
"""


class APIConfig:
    """API配置"""
    
    YFINANCE = {
        'name': 'yfinance',
        'type': 'free',
        'rate_limit': None,
        'requires_auth': False,
        'provides': [
            'stock_price',
            'historical_data',
            'option_chain',
            'implied_volatility',
            'dividends',
            'eps'
        ]
    }
    
    FRED = {
        'name': 'FRED',
        'type': 'free',
        'rate_limit': 120,  # per minute
        'requires_auth': True,
        'provides': [
            'risk_free_rate',
            'vix',
            'economic_data'
        ]
    }
    
    FINNHUB = {
        'name': 'Finnhub',
        'type': 'freemium',
        'rate_limit': 60,
        'requires_auth': True,
        'provides': [
            'real_time_quote',
            'company_profile',
            'basic_financials',
            'earnings_calendar',      # 业绩日历（岗位10）
            'dividend_calendar',      # 派息日历（岗位9）
            'company_news',           # 公司新闻
            'recommendation_trends'   # 分析师评级
        ]
    }
    
    RAPIDAPI = {
        'name': 'RapidAPI',
        'type': 'freemium',
        'rate_limit': 500,  # per month (免費版)
        'requires_auth': True,
        'provides': [
            'stock_price',
            'historical_data',
            'real_time_quote',
            'company_profile',
            'news'
        ]
    }
    
    YAHOO_FINANCE_V2 = {
        'name': 'Yahoo Finance 2.0 (Official)',
        'type': 'official',
        'rate_limit': None,  # 基於OAuth配額
        'requires_auth': True,
        'auth_type': 'OAuth2',
        'provides': [
            'stock_price',
            'historical_data',
            'option_chain',
            'real_time_quote',
            'fundamentals',
            'analyst_recommendations'
        ]
    }
    
    IBKR = {
        'name': 'Interactive Brokers (IBKR)',
        'type': 'premium',
        'rate_limit': None,  # 實時數據，無限制
        'requires_auth': True,
        'auth_type': 'TWS/Gateway',
        'requires_tws': True,  # 需要 TWS 或 IB Gateway 運行
        'provides': [
            'real_time_quote',
            'option_chain',
            'option_greeks',      # Delta, Gamma, Theta, Vega, Rho
            'bid_ask_spread',     # 實時買賣價差
            'implied_volatility', # 實時IV
            'open_interest',      # 未平倉量
            'volume',             # 成交量
            'historical_data'     # 歷史數據
        ],
        'fallback_on_error': True  # 錯誤時自動降級
    }
    
    ALPHA_VANTAGE = {
        'name': 'Alpha Vantage',
        'type': 'freemium',
        'rate_limit': 5,  # 5次/分鐘 (免費版)
        'daily_limit': 500,  # 500次/天 (免費版)
        'requires_auth': True,
        'provides': [
            'stock_price',
            'historical_data',
            'atr',                # ATR 技術指標
            'rsi',                # RSI 技術指標
            'sma',                # SMA 移動平均
            'ema',                # EMA 移動平均
            'company_overview',   # 公司概況
            'eps',                # EPS
            'pe_ratio',           # PE 比率
            'beta'                # Beta 係數
        ],
        'fallback_on_error': True
    }
    
    # 數據優先級（按順序嘗試，第一個失敗時自動嘗試下一個）
    # 
    # 降級策略說明:
    # - 每個數據類型都有預定義的降級順序
    # - 當主要數據源失敗時，系統會自動嘗試下一個數據源
    # - 所有降級操作都會被記錄，可通過 get_api_status_report() 查看
    # - 如果所有數據源都失敗，返回 None（不拋出異常）
    #
    # 2024-12-12 更新: 根據用戶訂閱情況優化
    # 用戶已訂閱: IBKR OPRA (期權即時報價)
    # 
    # 優先級原則:
    # 1. IBKR - 最高優先 (已付費，期權數據最準確)
    # 2. Finnhub - 第二優先 (免費60次/分鐘，股價/基本面)
    # 3. Finviz - 第三優先 (免費無限制，基本面指標)
    # 4. yfinance - 備用 (免費無限制，期權鏈備用)
    # 5. Alpha Vantage - 最後備用 (免費5次/分鐘限制嚴格)
    # 6. RapidAPI - 保護配額 (免費500次/月，僅緊急備用)
    #
    DATA_PRIORITY = {
        # ========== 股價/即時報價 ==========
        # IBKR(付費) > Finnhub(免費60/分) > Finviz(免費) > yfinance(備用)
        'stock_price': ['ibkr', 'finnhub', 'finviz', 'yfinance', 'yahoo_v2', 'alpha_vantage'],
        'real_time_quote': ['ibkr', 'finnhub', 'finviz', 'yfinance', 'yahoo_v2'],
        
        # ========== 期權數據 (IBKR OPRA 訂閱) ==========
        # IBKR(OPRA付費) > yfinance(免費) > RapidAPI(保護配額)
        'option_chain': ['ibkr', 'yfinance', 'yahoo_v2', 'rapidapi'],
        'implied_volatility': ['ibkr', 'yfinance', 'yahoo_v2', 'rapidapi'],
        'option_greeks': ['ibkr', 'yfinance', 'rapidapi'],
        'bid_ask_spread': ['ibkr', 'yfinance', 'yahoo_v2'],
        'open_interest': ['ibkr', 'yfinance', 'rapidapi'],
        'volume': ['ibkr', 'finnhub', 'yfinance', 'yahoo_v2'],
        
        # ========== 基本面數據 ==========
        # Finviz(免費無限) > Finnhub(免費60/分) > Alpha Vantage(限制嚴格)
        'eps': ['finviz', 'finnhub', 'alpha_vantage', 'yfinance', 'yahoo_v2'],
        'pe_ratio': ['finviz', 'finnhub', 'alpha_vantage', 'yfinance', 'yahoo_v2'],
        'dividends': ['finnhub', 'yfinance', 'alpha_vantage', 'yahoo_v2'],
        'company_overview': ['finviz', 'finnhub', 'alpha_vantage', 'yfinance'],
        
        # ========== 技術分析數據 ==========
        # Finviz(免費有ATR/RSI) > Finnhub > Alpha Vantage(限制嚴格)
        'atr': ['finviz', 'finnhub', 'alpha_vantage'],
        'rsi': ['finviz', 'finnhub', 'alpha_vantage'],
        'sma': ['finnhub', 'alpha_vantage'],
        'ema': ['finnhub', 'alpha_vantage'],
        'beta': ['finviz', 'finnhub', 'alpha_vantage', 'yfinance'],
        
        # ========== 宏觀數據 ==========
        # FRED(專用免費) > Finnhub > yfinance
        'risk_free_rate': ['FRED'],
        'vix': ['FRED', 'finnhub', 'yfinance'],
        
        # ========== 日曆數據 ==========
        # Finnhub(免費) > yfinance(備用)
        'earnings_date': ['finnhub', 'yfinance', 'estimated'],
        'dividend_date': ['finnhub', 'yfinance', 'alpha_vantage'],
        
        # ========== 歷史數據 ==========
        # IBKR(付費) > Finnhub > yfinance(免費無限)
        'historical_data': ['ibkr', 'finnhub', 'yfinance', 'yahoo_v2', 'alpha_vantage'],
        
        # ========== 新聞 ==========
        'company_news': ['finnhub', 'rapidapi']
    }


api_config = APIConfig()
