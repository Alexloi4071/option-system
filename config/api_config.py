# config/api_config.py
"""
API配置
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
    
    # 數據優先級（按順序嘗試，第一個失敗時自動嘗試下一個）
    DATA_PRIORITY = {
        'stock_price': ['ibkr', 'yfinance', 'yahoo_v2', 'finnhub', 'rapidapi'],
        'option_chain': ['ibkr', 'yfinance', 'yahoo_v2'],
        'implied_volatility': ['ibkr', 'yfinance', 'yahoo_v2'],
        'option_greeks': ['ibkr', 'yfinance'],  # IBKR提供真實Greeks，yfinance可估算
        'bid_ask_spread': ['ibkr', 'yfinance', 'yahoo_v2'],
        'risk_free_rate': ['FRED'],
        'eps': ['yfinance', 'yahoo_v2', 'finnhub'],
        'dividends': ['yfinance', 'yahoo_v2', 'finnhub'],
        'vix': ['FRED', 'yfinance'],
        'earnings_date': ['finnhub'],           # 业绩日期（岗位10）
        'dividend_date': ['yfinance', 'finnhub'], # 派息日期（岗位9）
        'historical_data': ['ibkr', 'yfinance', 'yahoo_v2', 'rapidapi'],
        'real_time_quote': ['ibkr', 'yahoo_v2', 'finnhub', 'rapidapi'],
        'company_news': ['finnhub', 'rapidapi'],
        'open_interest': ['ibkr', 'yfinance'],
        'volume': ['ibkr', 'yfinance', 'yahoo_v2']
    }


api_config = APIConfig()
