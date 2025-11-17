# config/constants.py
"""
常量定義
"""


class Constants:
    """系統常量"""
    
    # 數學常量 (來自書籍)
    IV_DIVIDER = 3.464                    # √12，用於IV月度轉換
    SQRT_12 = 3.464                       # 一年12個月的平方根
    
    # 時間常量
    DAYS_PER_YEAR = 365                   # 年天數
    DAYS_PER_MONTH = 30                   # 月天數（平均）
    TRADING_DAYS_PER_YEAR = 252           # 交易日天數
    
    # 期權常量
    OPTION_MULTIPLIER = 100               # 期權合約乘數
    DEFAULT_TRADING_FEE = 0.10            # 默認交易費用（美元）
    
    # PE估值範圍 (來自書籍第十課)
    PE_BEAR_MARKET = 8.5                  # 熊市PE倍數
    PE_BULL_MARKET = 25.0                 # 牛市PE倍數
    PE_NORMAL = 15.0                      # 正常市場PE倍數
    PE_GROWTH_STOCK = 30.0                # 成長股PE倍數
    
    # 利率與PE關係 (來自書籍第十課)
    # 長期債息與PE的反向關係
    RATE_PE_MULTIPLIER = 100              # 利率PE乘數
    # 公式: PE = 100 / 長期債息
    
    # 對沖比例 (來自書籍)
    DELTA_HEDGE_RATIO = 1.0               # Delta對沖比例
    
    # 期權定價相關
    RISK_FREE_RATE_DEFAULT = 4.5          # 默認無風險利率(%)
    
    # 監察崗位Delta範圍 (來自書籍第十四課)
    MONITOR_DELTA_MIN = 0.10              # 監察崗位最小Delta
    MONITOR_DELTA_MAX = 0.15              # 監察崗位最大Delta
    
    # 波動率範圍
    IV_MIN = 5.0                          # 最小IV (%)
    IV_MAX = 500.0                        # 最大IV (%)
    IV_NORMAL = 20.0                      # 正常IV (%)
    
    # Black-Scholes 模型常量 (Module 15)
    BS_MAX_ITERATIONS = 100               # BS模型最大迭代次數
    BS_TOLERANCE = 0.0001                 # BS模型收斂容差
    BS_INITIAL_IV_GUESS = 0.3             # IV反推初始猜測值 (30%)
    
    # Greeks 計算常量 (Module 16)
    GREEKS_PRECISION = 6                  # Greeks計算精度（小數位）
    
    # 歷史波動率常量 (Module 18)
    HV_DEFAULT_WINDOW = 30                # HV默認回溯窗口（天）
    HV_TRADING_DAYS_PER_YEAR = 252        # HV計算使用的年交易日數
    
    # Put-Call Parity 驗證常量 (Module 19)
    PARITY_TRANSACTION_COST = 0.005       # 平價驗證交易成本 (0.5%)
    
    # IV/HV 比率閾值 (Module 18)
    IV_HV_OVERVALUED_THRESHOLD = 1.2      # IV高估閾值（IV/HV > 1.2）
    IV_HV_UNDERVALUED_THRESHOLD = 0.8     # IV低估閾值（IV/HV < 0.8）
    
    # 價格精度
    PRICE_DECIMAL_PLACES = 2              # 價格保留小數位
    PERCENTAGE_DECIMAL_PLACES = 2         # 百分比保留小數位
    IV_DECIMAL_PLACES = 2                 # IV保留小數位
    
    # 數據驗證閾值
    MAX_STOCK_PRICE = 1000000.0           # 最大股價
    MIN_STOCK_PRICE = 0.01                # 最小股價
    MAX_PE_RATIO = 1000.0                 # 最大PE
    MIN_PE_RATIO = 0.1                    # 最小PE
    
    # 報告格式
    REPORT_DATE_FORMAT = '%Y-%m-%d'       # 報告日期格式
    REPORT_TIME_FORMAT = '%H:%M:%S'       # 報告時間格式
    REPORT_DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'  # 完整日期時間格式


# 期權四招 (來自書籍第一課)
class OptionStrategies:
    """期權四招常量"""
    
    LONG_CALL = "Long Call"               # 買入Call
    LONG_PUT = "Long Put"                 # 買入Put
    SHORT_CALL = "Short Call"             # 沽出Call
    SHORT_PUT = "Short Put"               # 沽出Put
    
    ALL_STRATEGIES = [LONG_CALL, LONG_PUT, SHORT_CALL, SHORT_PUT]


# 12監察崗位 (來自書籍第十四課)
class MonitoringPosts:
    """12監察崗位常量"""
    
    POST_1 = "崗位1: 正股價格監察"
    POST_2 = "崗位2: 期權金監察"
    POST_3 = "崗位3: 隱含波動率監察"
    POST_4 = "崗位4: Delta 0.1-0.15監察"
    POST_5 = "崗位5: 未平倉合約監察"
    POST_6 = "崗位6: 成交量監察"
    POST_7 = "崗位7: 買賣盤差價監察"
    POST_8 = "崗位8: ATR波幅監察"
    POST_9 = "崗位9: 派息日監察"
    POST_10 = "崗位10: 業績公佈監察"
    POST_11 = "崗位11: 到期日監察"
    POST_12 = "崗位12: 市場情緒監察"
    
    ALL_POSTS = [
        POST_1, POST_2, POST_3, POST_4, POST_5, POST_6,
        POST_7, POST_8, POST_9, POST_10, POST_11, POST_12
    ]


# 市場狀態 (來自書籍)
class MarketConditions:
    """市場狀態常量"""
    
    BULL_MARKET = "牛市"
    BEAR_MARKET = "熊市"
    NORMAL_MARKET = "正常市場"
    HIGH_VOLATILITY = "高波動"
    LOW_VOLATILITY = "低波動"


constants = Constants()
option_strategies = OptionStrategies()
monitoring_posts = MonitoringPosts()
market_conditions = MarketConditions()
