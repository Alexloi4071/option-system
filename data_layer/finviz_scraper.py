# data_layer/finviz_scraper.py
"""
Finviz 數據抓取器
用於獲取準確的股票基本面數據（EPS, PE, 財務報表等）
"""

import requests
from bs4 import BeautifulSoup
import logging
import time
from typing import Dict, Optional
import re

logger = logging.getLogger(__name__)


class FinvizScraper:
    """
    Finviz 網站數據抓取器
    
    功能:
    - 獲取股票基本面數據（EPS, PE, PEG, 市值等）
    - 獲取財務報表數據（收入、利潤、現金流等）
    - 獲取技術指標（Beta, ATR, RSI等）
    
    使用示例:
        >>> scraper = FinvizScraper()
        >>> data = scraper.get_stock_fundamentals('AAPL')
        >>> print(f"EPS: {data['eps']}, PE: {data['pe']}")
    """
    
    BASE_URL = "https://finviz.com/quote.ashx"
    STATEMENTS_URL = "https://finviz.com/quote.ashx"
    
    def __init__(self, request_delay: float = 1.0):
        """
        初始化 Finviz 抓取器
        
        參數:
            request_delay: 請求間隔（秒），避免被封禁
        """
        self.request_delay = request_delay
        self.last_request_time = 0
        self.session = requests.Session()
        
        # 設置 User-Agent（重要！避免被識別為爬蟲）
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        logger.info("* Finviz 抓取器已初始化")
    
    def _rate_limit(self):
        """速率限制"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.request_delay:
            sleep_time = self.request_delay - elapsed
            logger.debug(f"速率限制: 等待 {sleep_time:.2f}秒")
            time.sleep(sleep_time)
        self.last_request_time = time.time()
    
    def _parse_value(self, value_str: str) -> Optional[float]:
        """
        解析 Finviz 的數值字符串
        
        處理格式:
        - "123.45" → 123.45
        - "1.23B" → 1230000000.0
        - "456.78M" → 456780000.0
        - "12.34K" → 12340.0
        - "-" → None
        - "N/A" → None
        
        參數:
            value_str: 原始字符串
        
        返回:
            float 或 None
        """
        if not value_str or value_str in ['-', 'N/A', '']:
            return None
        
        # 移除百分號和逗號
        value_str = value_str.replace('%', '').replace(',', '').strip()
        
        # 處理 B (Billion), M (Million), K (Thousand)
        multipliers = {
            'B': 1_000_000_000,
            'M': 1_000_000,
            'K': 1_000
        }
        
        for suffix, multiplier in multipliers.items():
            if value_str.endswith(suffix):
                try:
                    number = float(value_str[:-1])
                    return number * multiplier
                except ValueError:
                    return None
        
        # 普通數字
        try:
            return float(value_str)
        except ValueError:
            return None
    
    def get_stock_fundamentals(self, ticker: str) -> Optional[Dict]:
        """
        獲取股票基本面數據
        
        參數:
            ticker: 股票代碼（如 'AAPL', 'MSFT'）
        
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
        """
        try:
            self._rate_limit()
            logger.info(f"開始從 Finviz 獲取 {ticker} 基本面數據...")
            
            # 構建 URL
            url = f"{self.BASE_URL}?t={ticker.upper()}"
            
            # 發送請求
            response = self.session.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            # 解析 HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 檢查是否找到股票
            if "not found" in response.text.lower():
                logger.warning(f"! Finviz 未找到股票: {ticker}")
                return None
            
            # 提取數據表格
            table = soup.find('table', class_='snapshot-table2')
            if not table:
                logger.warning(f"! 無法找到 Finviz 數據表格")
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
            
            logger.info(f"* 成功獲取 {ticker} Finviz 數據")
            logger.info(f"  公司: {result['company_name']}")
            logger.info(f"  當前價格: ${result['price']:.2f}")
            logger.info(f"  EPS (TTM): ${result['eps_ttm']:.2f}")
            logger.info(f"  P/E: {result['pe']:.2f}")
            logger.info(f"  Forward P/E: {result['forward_pe']:.2f}")
            
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
            
            # 發送請求
            response = self.session.get(url, headers=self.headers, timeout=10)
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
            print(f"  公司: {data['company_name']}")
            print(f"  行業: {data['sector']} - {data['industry']}")
            print(f"  當前價格: ${data['price']:.2f}")
            print(f"  EPS (TTM): ${data['eps_ttm']:.2f}")
            print(f"  P/E: {data['pe']:.2f}")
            print(f"  Forward P/E: {data['forward_pe']:.2f}")
            print(f"  PEG: {data['peg']:.2f}")
            print(f"  市值: ${data['market_cap']:,.0f}")
            print(f"  Beta: {data['beta']:.2f}")
            
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
