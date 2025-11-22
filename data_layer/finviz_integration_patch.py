# data_layer/finviz_integration_patch.py
"""
Finviz 整合補丁
用於將 Finviz 數據源整合到 DataFetcher 中

使用方法:
1. 在 data_fetcher.py 的 __init__ 方法中添加:
   from data_layer.finviz_scraper import FinvizScraper
   self.finviz_scraper = FinvizScraper(request_delay=self.request_delay)

2. 在 _initialize_clients 方法中添加:
   # Finviz 抓取器（無需 API Key）
   try:
       from data_layer.finviz_scraper import FinvizScraper
       self.finviz_scraper = FinvizScraper(request_delay=self.request_delay)
       logger.info("✓ Finviz 抓取器已初始化")
   except Exception as e:
       logger.warning(f"⚠ Finviz 初始化失敗: {e}")
       self.finviz_scraper = None

3. 修改 get_stock_info 方法，添加 Finviz 作為優先數據源
"""

def get_stock_info_with_finviz(self, ticker):
    """
    獲取股票基本信息（優先使用 Finviz）
    
    降級順序: Finviz → IBKR → Yahoo Finance 2.0 → yfinance
    
    參數:
        ticker: 股票代碼
    
    返回: dict
    """
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"開始獲取 {ticker} 基本信息...")
    
    # 方案1: 優先使用 Finviz（最準確的基本面數據）
    if hasattr(self, 'finviz_scraper') and self.finviz_scraper:
        try:
            logger.info("  使用 Finviz...")
            finviz_data = self.finviz_scraper.get_stock_fundamentals(ticker)
            
            if finviz_data:
                # 轉換為標準格式
                stock_data = {
                    'ticker': ticker,
                    'current_price': finviz_data['price'],
                    'open': None,  # Finviz 不提供當日開盤價
                    'high': None,
                    'low': None,
                    'volume': finviz_data['volume'],
                    'market_cap': finviz_data['market_cap'],
                    'pe_ratio': finviz_data['pe'],  # ← 使用真實 PE！
                    'forward_pe': finviz_data['forward_pe'],  # ← 前瞻 PE
                    'dividend_rate': finviz_data['dividend_yield'],
                    'eps': finviz_data['eps_ttm'],  # ← 使用真實 EPS！
                    'eps_next_y': finviz_data['eps_next_y'],
                    'peg_ratio': finviz_data['peg'],
                    'beta': finviz_data['beta'],
                    'atr': finviz_data['atr'],
                    'rsi': finviz_data['rsi'],
                    'company_name': finviz_data['company_name'],
                    'sector': finviz_data['sector'],
                    'industry': finviz_data['industry'],
                    'target_price': finviz_data['target_price'],
                    'profit_margin': finviz_data['profit_margin'],
                    'operating_margin': finviz_data['operating_margin'],
                    'roe': finviz_data['roe'],
                    'roa': finviz_data['roa'],
                    'debt_eq': finviz_data['debt_eq'],
                    'data_source': 'Finviz'
                }
                
                logger.info(f"✓ 成功獲取 {ticker} 基本信息 (Finviz)")
                logger.info(f"  當前股價: ${stock_data['current_price']:.2f}")
                logger.info(f"  EPS (TTM): ${stock_data['eps']:.2f}")
                logger.info(f"  P/E: {stock_data['pe_ratio']:.2f}")
                logger.info(f"  Forward P/E: {stock_data['forward_pe']:.2f}")
                
                self._record_fallback('stock_info', 'Finviz')
                return stock_data
        except Exception as e:
            logger.warning(f"⚠ Finviz 獲取失敗: {e}，降級到 IBKR")
            self._record_api_failure('Finviz', f"get_stock_info: {e}")
    
    # 方案2: 降級到 IBKR
    if self.ibkr_client and self.ibkr_client.is_connected():
        try:
            self._rate_limit_delay()
            logger.info("  使用 IBKR API...")
            stock_data = self.ibkr_client.get_stock_info(ticker)
            
            if stock_data:
                logger.info(f"✓ 成功獲取 {ticker} 基本信息 (IBKR)")
                logger.info(f"  當前股價: ${stock_data['current_price']:.2f}")
                self._record_fallback('stock_info', 'IBKR')
                return stock_data
        except Exception as e:
            logger.warning(f"⚠ IBKR 獲取失敗: {e}，降級到 Yahoo Finance")
            self._record_api_failure('IBKR', f"get_stock_info: {e}")
    
    # 方案3: 降級到 Yahoo Finance（简化版）
    if self.yahoo_v2_client:
        try:
            logger.info("  使用 Yahoo Finance API...")
            response = self.yahoo_v2_client.get_quote(ticker)
            from data_layer.yahoo_finance_v2_client import YahooDataParser
            stock_data = YahooDataParser.parse_quote(response)
            
            if stock_data:
                logger.info(f"✓ 成功獲取 {ticker} 基本信息 (Yahoo Finance)")
                logger.info(f"  當前股價: ${stock_data['current_price']:.2f}")
                self._record_fallback('stock_info', 'Yahoo Finance')
                return stock_data
        except Exception as e:
            logger.warning(f"⚠ Yahoo Finance 获取失败: {e}，降级到 yfinance")
            self._record_api_failure('Yahoo Finance', f"get_stock_info: {e}")
    
    # 方案4: 降级到 yfinance
    try:
        import yfinance as yf
        self._rate_limit_delay()
        logger.info("  使用 yfinance...")
        stock = yf.Ticker(ticker)
        info = stock.info
        
        stock_data = {
            'ticker': ticker,
            'current_price': info.get('currentPrice', 0),
            'open': info.get('open', 0),
            'high': info.get('dayHigh', 0),
            'low': info.get('dayLow', 0),
            'volume': info.get('volume', 0),
            'market_cap': info.get('marketCap', 0),
            'pe_ratio': info.get('trailingPE', 0),
            'forward_pe': info.get('forwardPE', 0),
            'dividend_rate': info.get('dividendRate', 0),
            'eps': info.get('trailingEps', 0),
            'fifty_two_week_high': info.get('fiftyTwoWeekHigh', 0),
            'fifty_two_week_low': info.get('fiftyTwoWeekLow', 0),
            'beta': info.get('beta', 0),
            'company_name': info.get('longName', ''),
            'sector': info.get('sector', ''),
            'industry': info.get('industry', ''),
            'data_source': 'yfinance'
        }
        
        logger.info(f"✓ 成功獲取 {ticker} 基本信息 (yfinance)")
        logger.info(f"  當前股價: ${stock_data['current_price']:.2f}")
        logger.info(f"  市盈率: {stock_data['pe_ratio']:.2f}")
        logger.info(f"  EPS: ${stock_data['eps']:.2f}")
        self._record_fallback('stock_info', 'yfinance')
        
        return stock_data
        
    except Exception as e:
        logger.error(f"✗ 獲取 {ticker} 基本信息失敗: {e}")
        self._record_api_failure('yfinance', f"get_stock_info: {e}")
        return None


# 使用說明
print("""
╔════════════════════════════════════════════════════════════════════╗
║           Finviz 整合補丁 - 使用說明                                ║
╚════════════════════════════════════════════════════════════════════╝

步驟 1: 在 data_fetcher.py 的 __init__ 方法中添加（第 77 行附近）:
────────────────────────────────────────────────────────────────────
self.finviz_scraper = None  # 添加這一行

步驟 2: 在 _initialize_clients 方法中添加（第 191 行之後）:
────────────────────────────────────────────────────────────────────
# Finviz 抓取器（無需 API Key，免費使用）
try:
    from data_layer.finviz_scraper import FinvizScraper
    self.finviz_scraper = FinvizScraper(request_delay=self.request_delay)
    logger.info("✓ Finviz 抓取器已初始化")
except Exception as e:
    logger.warning(f"⚠ Finviz 初始化失敗: {e}")
    self._record_api_failure('Finviz', str(e))
    self.finviz_scraper = None

步驟 3: 替換 get_stock_info 方法（第 295-400 行）:
────────────────────────────────────────────────────────────────────
將現有的 get_stock_info 方法替換為上面的 get_stock_info_with_finviz

或者，在方案1之前添加 Finviz 檢查:
────────────────────────────────────────────────────────────────────
# 方案0: 優先使用 Finviz（在 IBKR 之前）
if hasattr(self, 'finviz_scraper') and self.finviz_scraper:
    try:
        logger.info("  使用 Finviz...")
        finviz_data = self.finviz_scraper.get_stock_fundamentals(ticker)
        
        if finviz_data and finviz_data['price']:
            stock_data = {
                'ticker': ticker,
                'current_price': finviz_data['price'],
                'pe_ratio': finviz_data['pe'],
                'forward_pe': finviz_data['forward_pe'],
                'eps': finviz_data['eps_ttm'],
                'market_cap': finviz_data['market_cap'],
                'beta': finviz_data['beta'],
                'sector': finviz_data['sector'],
                'industry': finviz_data['industry'],
                'data_source': 'Finviz'
            }
            logger.info(f"✓ 成功獲取 {ticker} 基本信息 (Finviz)")
            self._record_fallback('stock_info', 'Finviz')
            return stock_data
    except Exception as e:
        logger.warning(f"⚠ Finviz 獲取失敗: {e}")
        self._record_api_failure('Finviz', f"get_stock_info: {e}")

優勢:
────────────────────────────────────────────────────────────────────
✓ 無需 API Key（完全免費）
✓ 數據更準確（特別是 EPS 和 PE）
✓ 提供 Forward PE（前瞻性估值）
✓ 包含更多基本面指標（ROE, ROA, Margins 等）
✓ 更新及時（通常比 Yahoo Finance 快）

注意事項:
────────────────────────────────────────────────────────────────────
⚠ 需要遵守速率限制（建議 1-2 秒/請求）
⚠ 需要設置正確的 User-Agent（已在 FinvizScraper 中處理）
⚠ 網站結構變化可能需要更新解析邏輯

測試:
────────────────────────────────────────────────────────────────────
python data_layer/finviz_scraper.py

完成後，Module 4 將使用真實的 PE 數據，不再顯示錯誤的估值！
""")
