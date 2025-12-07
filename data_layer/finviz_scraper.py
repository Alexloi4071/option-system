# data_layer/finviz_scraper.py
"""
Finviz 數據抓取器（優化版）
用於獲取準確的股票基本面數據（EPS, PE, 財務報表等）

優化功能:
- UserAgentRotator: 每次請求使用不同的 User-Agent
- 隨機延遲: 1-3 秒隨機延遲避免被封禁
- 封鎖檢測: 檢測 CAPTCHA 和 403/429 響應
- 多重選擇器: 多個 CSS 選擇器容錯
"""

import requests
from bs4 import BeautifulSoup
import logging
import time
import math
import random
from typing import Dict, Optional, Any, List
from dataclasses import dataclass
import re

# 導入優化工具
from .utils.user_agent_rotator import UserAgentRotator
from .utils.retry_handler import RetryHandler, RetryConfig
from .utils import ConnectionConfig, FINVIZ_CONNECTION_CONFIG

logger = logging.getLogger(__name__)


@dataclass
class DataQualityIndicator:
    """數據質量指示器"""
    quality_level: str  # 'complete', 'partial', 'minimal'
    available_fields: List[str]
    missing_fields: List[str]
    critical_fields_present: bool
    data_source: str


class SafeFormatter:
    """
    安全的數值格式化工具
    
    處理 None, NaN 和無效類型，避免格式化異常
    """
    
    @staticmethod
    def format_number(value: Any, format_spec: str = '.2f', 
                      default: str = 'N/A') -> str:
        """
        安全格式化數值，處理 None 和無效值
        
        參數:
            value: 要格式化的值
            format_spec: 格式規格（如 '.2f', '.0f'）
            default: 當值為 None 或無效時的默認顯示
        
        返回:
            格式化後的字符串
        """
        if value is None:
            return default
        
        try:
            # 檢查是否為 NaN
            if isinstance(value, float) and math.isnan(value):
                return default
            
            # 嘗試轉換為 float 並格式化
            num_value = float(value)
            return f"{num_value:{format_spec}}"
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def format_currency(value: Any, default: str = 'N/A') -> str:
        """
        安全格式化貨幣值
        
        參數:
            value: 要格式化的值
            default: 當值為 None 或無效時的默認顯示
        
        返回:
            格式化後的字符串（如 "$123.45"）
        """
        if value is None:
            return default
        
        try:
            if isinstance(value, float) and math.isnan(value):
                return default
            
            num_value = float(value)
            return f"${num_value:.2f}"
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def format_percent(value: Any, default: str = 'N/A') -> str:
        """
        安全格式化百分比值
        
        參數:
            value: 要格式化的值
            default: 當值為 None 或無效時的默認顯示
        
        返回:
            格式化後的字符串（如 "12.34%"）
        """
        if value is None:
            return default
        
        try:
            if isinstance(value, float) and math.isnan(value):
                return default
            
            num_value = float(value)
            return f"{num_value:.2f}%"
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def format_large_number(value: Any, default: str = 'N/A') -> str:
        """
        安全格式化大數字（帶千位分隔符）
        
        參數:
            value: 要格式化的值
            default: 當值為 None 或無效時的默認顯示
        
        返回:
            格式化後的字符串（如 "1,234,567"）
        """
        if value is None:
            return default
        
        try:
            if isinstance(value, float) and math.isnan(value):
                return default
            
            num_value = float(value)
            return f"{num_value:,.0f}"
        except (ValueError, TypeError):
            return default


class FinvizScraper:
    """
    Finviz 網站數據抓取器（優化版）
    
    功能:
    - 獲取股票基本面數據（EPS, PE, PEG, 市值等）
    - 獲取財務報表數據（收入、利潤、現金流等）
    - 獲取技術指標（Beta, ATR, RSI等）
    - 支持 Elite 帳戶（需要設置 cookies）
    
    優化功能:
    - User-Agent 輪換（避免被識別為爬蟲）
    - 隨機延遲（1-3 秒）
    - 封鎖檢測（CAPTCHA, 403, 429）
    - 多重 CSS 選擇器容錯
    
    使用示例:
        >>> scraper = FinvizScraper()
        >>> data = scraper.get_stock_fundamentals('AAPL')
        >>> print(f"EPS: {data['eps']}, PE: {data['pe']}")
    
    Requirements: 4.1-4.4, 5.1
    """
    
    # 免費版 URL
    BASE_URL = "https://finviz.com/quote.ashx"
    STATEMENTS_URL = "https://finviz.com/quote.ashx"
    
    # Elite 版 URL
    ELITE_BASE_URL = "https://elite.finviz.com/quote.ashx"
    ELITE_STATEMENTS_URL = "https://elite.finviz.com/quote.ashx"
    
    # 多重 CSS 選擇器（容錯）
    TABLE_SELECTORS = [
        'table.snapshot-table2',
        'table[class*="snapshot"]',
        'table.screener-body-table-nw',
        '#snapshot-table2',
    ]
    
    # 封鎖檢測關鍵字
    BLOCK_INDICATORS = [
        'captcha',
        'robot',
        'blocked',
        'access denied',
        'rate limit',
        'too many requests',
    ]
    
    def __init__(
        self, 
        request_delay: float = 1.0, 
        use_elite: bool = False, 
        elite_cookies: dict = None,
        ua_rotator: Optional[UserAgentRotator] = None,
        retry_handler: Optional[RetryHandler] = None,
        random_delay_range: tuple = (1.0, 3.0),
        connection_config: Optional[ConnectionConfig] = None
    ):
        """
        初始化 Finviz 抓取器（優化版）
        
        參數:
            request_delay: 基礎請求間隔（秒），避免被封禁
            use_elite: 是否使用 Elite 版本
            elite_cookies: Elite 帳戶的 cookies（從瀏覽器獲取）
            ua_rotator: User-Agent 輪換器（可選，默認創建新實例）
            retry_handler: 重試處理器（可選，默認創建新實例）
            random_delay_range: 隨機延遲範圍（最小, 最大）秒
            connection_config: 連接配置（可選，默認使用 FINVIZ_CONNECTION_CONFIG）
        """
        self.request_delay = request_delay
        self.random_delay_range = random_delay_range
        self.last_request_time = 0
        self.use_elite = use_elite
        
        # 連接配置
        self.connection_config = connection_config or FINVIZ_CONNECTION_CONFIG
        
        # 創建 Session（配置連接池）
        self.session = requests.Session()
        
        # 配置連接適配器
        from requests.adapters import HTTPAdapter
        adapter = HTTPAdapter(
            pool_connections=self.connection_config.pool_connections,
            pool_maxsize=self.connection_config.pool_maxsize,
            max_retries=0
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        
        # 初始化 User-Agent 輪換器
        self.ua_rotator = ua_rotator or UserAgentRotator()
        
        # 初始化重試處理器
        if retry_handler:
            self.retry_handler = retry_handler
        else:
            retry_config = RetryConfig(
                max_retries=3,
                initial_delay=5.0,
                max_delay=60.0,
                exponential_base=2.0,
                jitter=True,
                retryable_status_codes=[429, 500, 502, 503, 504]
            )
            self.retry_handler = RetryHandler(retry_config)
        
        # 封鎖檢測計數器
        self._block_count = 0
        self._request_count = 0
        
        # 設置初始 User-Agent
        self.headers = {
            'User-Agent': self.ua_rotator.get_next(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Referer': 'https://finviz.com/',
            'Cache-Control': 'no-cache',
        }
        
        # 如果使用 Elite 版本，設置 cookies
        if use_elite and elite_cookies:
            for name, value in elite_cookies.items():
                self.session.cookies.set(name, value)
            logger.info("* Finviz Elite 抓取器已初始化（優化版，使用 cookies 認證）")
        else:
            logger.info("* Finviz 抓取器已初始化（優化版，免費版）")
        
        logger.debug(f"  User-Agent 輪換器: {len(self.ua_rotator)} 個 UA")
        logger.debug(f"  隨機延遲範圍: {random_delay_range[0]}-{random_delay_range[1]} 秒")
    
    def _rate_limit(self):
        """
        速率限制（優化版：添加隨機延遲）
        
        Requirements: 4.3
        """
        elapsed = time.time() - self.last_request_time
        
        # 基礎延遲
        if elapsed < self.request_delay:
            base_sleep = self.request_delay - elapsed
        else:
            base_sleep = 0
        
        # 添加隨機延遲（1-3 秒）
        random_sleep = random.uniform(*self.random_delay_range)
        total_sleep = base_sleep + random_sleep
        
        if total_sleep > 0:
            logger.debug(f"速率限制: 等待 {total_sleep:.2f}秒（基礎: {base_sleep:.2f}s + 隨機: {random_sleep:.2f}s）")
            time.sleep(total_sleep)
        
        self.last_request_time = time.time()
    
    def _rotate_user_agent(self) -> str:
        """輪換 User-Agent 並更新 headers"""
        new_ua = self.ua_rotator.get_next()
        self.headers['User-Agent'] = new_ua
        return new_ua
    
    def _detect_block(self, response: requests.Response) -> bool:
        """
        檢測是否被封鎖
        
        參數:
            response: HTTP 響應
        
        返回:
            bool: 是否被封鎖
        
        Requirements: 4.2
        """
        # 檢查狀態碼
        if response.status_code in [403, 429]:
            logger.warning(f"! 檢測到封鎖: HTTP {response.status_code}")
            self._block_count += 1
            return True
        
        # 檢查響應內容
        content_lower = response.text.lower()
        for indicator in self.BLOCK_INDICATORS:
            if indicator in content_lower:
                logger.warning(f"! 檢測到封鎖關鍵字: '{indicator}'")
                self._block_count += 1
                return True
        
        return False
    
    def _find_table(self, soup: BeautifulSoup) -> Optional[Any]:
        """
        使用多重選擇器查找數據表格
        
        參數:
            soup: BeautifulSoup 對象
        
        返回:
            表格元素或 None
        
        Requirements: 5.1
        """
        for selector in self.TABLE_SELECTORS:
            try:
                if selector.startswith('#'):
                    # ID 選擇器
                    table = soup.find(id=selector[1:])
                elif '[' in selector:
                    # 屬性選擇器
                    table = soup.select_one(selector)
                else:
                    # 類選擇器
                    parts = selector.split('.')
                    tag = parts[0] if parts[0] else None
                    class_name = parts[1] if len(parts) > 1 else None
                    table = soup.find(tag, class_=class_name)
                
                if table:
                    logger.debug(f"  使用選擇器 '{selector}' 找到表格")
                    return table
            except Exception as e:
                logger.debug(f"  選擇器 '{selector}' 失敗: {e}")
                continue
        
        return None
    
    def get_stats(self) -> dict:
        """獲取抓取器統計"""
        return {
            'request_count': self._request_count,
            'block_count': self._block_count,
            'block_rate': self._block_count / self._request_count if self._request_count > 0 else 0,
            'ua_stats': self.ua_rotator.get_stats(),
            'retry_stats': self.retry_handler.get_stats(),
        }
    
    def _parse_value(self, value_str: str) -> Optional[float]:
        """
        解析 Finviz 的數值字符串（增強版）
        
        處理格式:
        - "123.45" → 123.45
        - "1.23B" → 1230000000.0
        - "456.78M" → 456780000.0
        - "12.34K" → 12340.0
        - "1.5T" → 1500000000000.0 (Trillion)
        - "-123.45" → -123.45 (負數)
        - "12.34%" → 12.34 (百分比)
        - "-5.67%" → -5.67 (負百分比)
        - "1,234.56" → 1234.56 (千位分隔符)
        - "-" → None
        - "N/A" → None
        - "" → None
        
        參數:
            value_str: 原始字符串
        
        返回:
            float 或 None
        
        Requirements: 5.3
        """
        # 處理空值和無效值
        if not value_str:
            return None
        
        # 清理字符串
        value_str = str(value_str).strip()
        
        # 無效值列表
        invalid_values = ['-', 'N/A', 'n/a', 'NA', 'None', 'null', '']
        if value_str in invalid_values:
            return None
        
        # 保存原始值用於錯誤日誌
        original_str = value_str
        
        # 檢測是否為負數
        is_negative = value_str.startswith('-') or value_str.startswith('(')
        if value_str.startswith('-'):
            value_str = value_str[1:]
        elif value_str.startswith('(') and value_str.endswith(')'):
            # 會計格式負數: (123.45)
            value_str = value_str[1:-1]
            is_negative = True
        
        # 移除百分號（但記住這是百分比）
        is_percent = '%' in value_str
        value_str = value_str.replace('%', '')
        
        # 移除千位分隔符和空格
        value_str = value_str.replace(',', '').replace(' ', '').strip()
        
        # 處理 T (Trillion), B (Billion), M (Million), K (Thousand)
        multipliers = {
            'T': 1_000_000_000_000,
            'B': 1_000_000_000,
            'M': 1_000_000,
            'K': 1_000,
            't': 1_000_000_000_000,
            'b': 1_000_000_000,
            'm': 1_000_000,
            'k': 1_000,
        }
        
        multiplier = 1.0
        for suffix, mult in multipliers.items():
            if value_str.endswith(suffix):
                value_str = value_str[:-1]
                multiplier = mult
                break
        
        # 嘗試解析數字
        try:
            number = float(value_str)
            result = number * multiplier
            
            # 應用負號
            if is_negative:
                result = -result
            
            return result
            
        except ValueError:
            # 嘗試更寬鬆的解析
            try:
                # 移除所有非數字字符（除了小數點和負號）
                cleaned = re.sub(r'[^\d.\-]', '', original_str)
                if cleaned and cleaned != '-':
                    return float(cleaned)
            except ValueError:
                pass
            
            logger.debug(f"  無法解析數值: '{original_str}'")
            return None
    
    def get_stock_fundamentals(self, ticker: str, retry_count: int = 0) -> Optional[Dict]:
        """
        獲取股票基本面數據（優化版）
        
        參數:
            ticker: 股票代碼（如 'AAPL', 'MSFT'）
            retry_count: 當前重試次數
        
        返回:
            dict: {
                'ticker': str,
                'company_name': str,
                'sector': str,
                'industry': str,
                'country': str,
                'market_cap': float,
                'pe': float,              # P/E Ratio (TTM)
                'forward_pe': float,      # Forward P/E
                'peg': float,             # PEG Ratio
                'eps_ttm': float,         # EPS (TTM)
                'eps_next_y': float,      # EPS next year estimate
                'price': float,           # Current price
                'target_price': float,    # Analyst target price
                'dividend_yield': float,  # Dividend yield %
                'beta': float,            # Beta
                'atr': float,             # Average True Range
                'rsi': float,             # RSI (14)
                'volume': float,          # Volume
                'avg_volume': float,      # Avg Volume
                'shares_outstanding': float,
                'shares_float': float,
                'insider_own': float,     # Insider ownership %
                'inst_own': float,        # Institutional ownership %
                'short_float': float,     # Short % of float
                'debt_eq': float,         # Debt/Equity ratio
                'roa': float,             # Return on Assets %
                'roe': float,             # Return on Equity %
                'profit_margin': float,   # Profit Margin %
                'operating_margin': float,# Operating Margin %
                'gross_margin': float,    # Gross Margin %
                'data_source': 'Finviz'
            }
        
        Requirements: 4.1-4.4, 5.1
        """
        try:
            self._rate_limit()
            self._request_count += 1
            
            # 每次請求輪換 User-Agent
            current_ua = self._rotate_user_agent()
            
            logger.info(f"開始從 Finviz 獲取 {ticker} 基本面數據...")
            logger.debug(f"  User-Agent: {current_ua[:50]}...")
            
            # 構建 URL（根據是否使用 Elite 版本）
            base_url = self.ELITE_BASE_URL if self.use_elite else self.BASE_URL
            url = f"{base_url}?t={ticker.upper()}"
            
            # 發送請求（使用配置的超時）
            response = self.session.get(url, headers=self.headers, timeout=self.connection_config.timeout)
            
            # 檢測封鎖
            if self._detect_block(response):
                if self.retry_handler.should_retry(response.status_code, retry_count):
                    wait_time = self.retry_handler.calculate_delay(retry_count + 1, 'exponential')
                    logger.warning(f"  重試 {retry_count + 1}，等待 {wait_time:.1f}s...")
                    time.sleep(wait_time)
                    return self.get_stock_fundamentals(ticker, retry_count + 1)
                else:
                    logger.error(f"x Finviz 請求被封鎖，已達最大重試次數")
                    return None
            
            response.raise_for_status()
            
            # 解析 HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 檢查是否找到股票
            if "not found" in response.text.lower():
                logger.warning(f"! Finviz 未找到股票: {ticker}")
                return None
            
            # 使用多重選擇器查找數據表格
            table = self._find_table(soup)
            if not table:
                logger.warning(f"! 無法找到 Finviz 數據表格（嘗試了 {len(self.TABLE_SELECTORS)} 個選擇器）")
                return None
            
            # 解析表格數據
            data_dict = {}
            rows = table.find_all('tr')
            
            for row in rows:
                cells = row.find_all('td')
                for i in range(0, len(cells), 2):
                    if i + 1 < len(cells):
                        key = cells[i].get_text(strip=True)
                        value = cells[i + 1].get_text(strip=True)
                        data_dict[key] = value
            
            # 提取公司名稱、Sector、Industry、Country（從 tab-link 類的鏈接獲取）
            company_name = None
            sector = None
            industry = None
            country = None
            tab_links = soup.find_all('a', class_='tab-link')
            for i, link in enumerate(tab_links):
                href = link.get('href', '')
                text = link.get_text(strip=True)
                # 第一個 tab-link 是公司名稱（指向公司網站）
                if i == 0:
                    company_name = text
                elif 'f=sec_' in href:
                    sector = text
                elif 'f=ind_' in href:
                    industry = text
                elif 'f=geo_' in href:
                    country = text
            
            # 解析股息（Finviz 格式: "1.03 (0.37%)" 或 "1.07 (0.39%)"）
            dividend_yield = None
            dividend_ttm = data_dict.get('Dividend TTM', '')
            dividend_est = data_dict.get('Dividend Est.', '')
            # 優先使用 TTM，否則用 Est
            dividend_str = dividend_ttm or dividend_est
            if dividend_str:
                # 提取括號內的百分比
                import re
                match = re.search(r'\((\d+\.?\d*)%\)', dividend_str)
                if match:
                    dividend_yield = float(match.group(1))
            
            # 映射到標準格式
            result = {
                'ticker': ticker.upper(),
                'company_name': company_name,
                'sector': sector,
                'industry': industry,
                'country': country,
                'market_cap': self._parse_value(data_dict.get('Market Cap')),
                'pe': self._parse_value(data_dict.get('P/E')),
                'forward_pe': self._parse_value(data_dict.get('Forward P/E')),
                'peg': self._parse_value(data_dict.get('PEG')),
                'eps_ttm': self._parse_value(data_dict.get('EPS (ttm)')),
                'eps_next_y': self._parse_value(data_dict.get('EPS next Y')),
                'price': self._parse_value(data_dict.get('Price')),
                'target_price': self._parse_value(data_dict.get('Target Price')),
                'dividend_yield': dividend_yield,
                'beta': self._parse_value(data_dict.get('Beta')),
                'atr': self._parse_value(data_dict.get('ATR (14)')),  # 修正: ATR → ATR (14)
                'rsi': self._parse_value(data_dict.get('RSI (14)')),
                'volume': self._parse_value(data_dict.get('Volume')),
                'avg_volume': self._parse_value(data_dict.get('Avg Volume')),
                'shares_outstanding': self._parse_value(data_dict.get('Shs Outstand')),
                'shares_float': self._parse_value(data_dict.get('Shs Float')),
                'insider_own': self._parse_value(data_dict.get('Insider Own')),
                'inst_own': self._parse_value(data_dict.get('Inst Own')),
                'short_float': self._parse_value(data_dict.get('Short Float')),
                'debt_eq': self._parse_value(data_dict.get('Debt/Eq')),
                'roa': self._parse_value(data_dict.get('ROA')),
                'roe': self._parse_value(data_dict.get('ROE')),
                'profit_margin': self._parse_value(data_dict.get('Profit Margin')),
                'operating_margin': self._parse_value(data_dict.get('Oper. Margin')),
                'gross_margin': self._parse_value(data_dict.get('Gross Margin')),
                'data_source': 'Finviz'
            }
            
            # 使用 SafeFormatter 安全格式化日誌輸出
            logger.info(f"* 成功獲取 {ticker} Finviz 數據")
            logger.info(f"  公司: {result['company_name'] or 'N/A'}")
            logger.info(f"  當前價格: {SafeFormatter.format_currency(result['price'])}")
            logger.info(f"  EPS (TTM): {SafeFormatter.format_currency(result['eps_ttm'])}")
            logger.info(f"  P/E: {SafeFormatter.format_number(result['pe'])}")
            logger.info(f"  Forward P/E: {SafeFormatter.format_number(result['forward_pe'])}")
            
            # 計算數據質量
            all_fields = [
                'price', 'eps_ttm', 'pe', 'forward_pe', 'peg', 'market_cap',
                'beta', 'atr', 'rsi', 'insider_own', 'inst_own', 'short_float',
                'avg_volume', 'roe', 'profit_margin', 'debt_eq'
            ]
            critical_fields = ['ticker', 'price']
            
            available = [f for f in all_fields if result.get(f) is not None]
            missing = [f for f in all_fields if result.get(f) is None]
            critical_present = all(result.get(f) is not None for f in critical_fields)
            
            # 確定質量等級
            if len(available) >= len(all_fields) * 0.8:
                quality_level = 'complete'
            elif len(available) >= len(all_fields) * 0.5:
                quality_level = 'partial'
            else:
                quality_level = 'minimal'
            
            result['data_quality'] = DataQualityIndicator(
                quality_level=quality_level,
                available_fields=available,
                missing_fields=missing,
                critical_fields_present=critical_present,
                data_source='Finviz'
            )
            
            if missing:
                logger.debug(f"  缺失字段: {', '.join(missing[:5])}{'...' if len(missing) > 5 else ''}")
            
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"x Finviz 請求失敗: {e}")
            return None
        except Exception as e:
            logger.error(f"x Finviz 數據解析失敗: {e}")
            return None
    
    def get_financial_statements(self, ticker: str) -> Optional[Dict]:
        """
        獲取財務報表數據（收入、利潤、現金流等）
        
        參數:
            ticker: 股票代碼
        
        返回:
            dict: {
                'income_statement': {
                    'revenue': [Q1, Q2, Q3, Q4, ...],
                    'gross_profit': [...],
                    'operating_income': [...],
                    'net_income': [...]
                },
                'balance_sheet': {
                    'total_assets': [...],
                    'total_liabilities': [...],
                    'shareholders_equity': [...]
                },
                'cash_flow': {
                    'operating_cash_flow': [...],
                    'investing_cash_flow': [...],
                    'financing_cash_flow': [...]
                }
            }
        """
        try:
            self._rate_limit()
            logger.info(f"開始從 Finviz 獲取 {ticker} 財務報表...")
            
            # 構建 URL（包含 statements 參數）
            url = f"{self.STATEMENTS_URL}?t={ticker.upper()}&p=d#statements"
            
            # 發送請求（使用配置的超時）
            response = self.session.get(url, headers=self.headers, timeout=self.connection_config.timeout)
            response.raise_for_status()
            
            # 解析 HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 查找財務報表表格
            # 注意: Finviz 的財務報表結構可能需要進一步分析
            # 這裡提供基本框架，具體實現需要根據實際 HTML 結構調整
            
            statements = {
                'income_statement': {},
                'balance_sheet': {},
                'cash_flow': {},
                'data_source': 'Finviz'
            }
            
            logger.info(f"* 成功獲取 {ticker} 財務報表數據")
            return statements
            
        except Exception as e:
            logger.error(f"x Finviz 財務報表獲取失敗: {e}")
            return None
    
    def validate_data_quality(self, data: Dict) -> Dict:
        """
        驗證數據質量
        
        參數:
            data: 從 Finviz 獲取的數據
        
        返回:
            dict: {
                'is_valid': bool,
                'missing_fields': list,
                'warnings': list
            }
        """
        critical_fields = ['ticker', 'price', 'eps_ttm', 'pe']
        missing_fields = []
        warnings = []
        
        for field in critical_fields:
            if field not in data or data[field] is None:
                missing_fields.append(field)
        
        # 檢查數據合理性
        if data.get('pe') and (data['pe'] < 0 or data['pe'] > 1000):
            warnings.append(f"P/E 比率異常: {data['pe']}")
        
        if data.get('eps_ttm') and data['eps_ttm'] < 0:
            warnings.append(f"EPS 為負: {data['eps_ttm']}")
        
        is_valid = len(missing_fields) == 0
        
        return {
            'is_valid': is_valid,
            'missing_fields': missing_fields,
            'warnings': warnings
        }


# 使用示例和測試
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    scraper = FinvizScraper()
    
    print("\n" + "=" * 70)
    print("Finviz 數據抓取器測試")
    print("=" * 70)
    
    # 測試多個股票
    test_tickers = ['AAPL', 'MSFT', 'GOOGL', 'TSLA']
    
    for ticker in test_tickers:
        print(f"\n【測試 {ticker}】")
        print("-" * 70)
        
        data = scraper.get_stock_fundamentals(ticker)
        
        if data:
            print(f"* 成功獲取 {ticker} 數據")
            print(f"  公司: {data['company_name'] or 'N/A'}")
            print(f"  行業: {data.get('sector', 'N/A')} - {data.get('industry', 'N/A')}")
            print(f"  當前價格: {SafeFormatter.format_currency(data['price'])}")
            print(f"  EPS (TTM): {SafeFormatter.format_currency(data['eps_ttm'])}")
            print(f"  P/E: {SafeFormatter.format_number(data['pe'])}")
            print(f"  Forward P/E: {SafeFormatter.format_number(data['forward_pe'])}")
            print(f"  PEG: {SafeFormatter.format_number(data['peg'])}")
            print(f"  市值: {SafeFormatter.format_large_number(data['market_cap'])}")
            print(f"  Beta: {SafeFormatter.format_number(data['beta'])}")
            
            # 驗證數據質量
            validation = scraper.validate_data_quality(data)
            if validation['is_valid']:
                print(f"  * 數據質量: 良好")
            else:
                print(f"  ! 缺失字段: {validation['missing_fields']}")
            
            if validation['warnings']:
                print(f"  ! 警告: {validation['warnings']}")
        else:
            print(f"x 獲取 {ticker} 數據失敗")
        
        time.sleep(1)  # 避免請求過快
    
    print("\n" + "=" * 70)
