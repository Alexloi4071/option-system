import asyncio
import logging
import json
import os
import random
import math
import sys
from typing import List, Dict, Optional
from datetime import datetime

# Windows encoding fix to prevent UnicodeEncodeError on emojis
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from ib_insync import *
from config.settings import settings as SETTINGS
from config.strategy_profiles import ALL_PROFILES, StrategyProfile
from data_layer.finviz_scraper import FinvizScraper
from calculation_layer.module26_long_option_analysis import LongOptionAnalyzer
from calculation_layer.module29_short_option_analysis import ShortOptionAnalyzer
from calculation_layer.module30_unusual_activity import UnusualActivityAnalyzer
from calculation_layer.module24_technical_direction import TechnicalDirectionAnalyzer
from calculation_layer.module34_volume_profile import VolumeProfileAnalyzer
from data_layer.ibkr_client import IBKRClient # Import Client Wrapper
from data_layer.sqlite_manager import SQLiteManager
from main import OptionsAnalysisSystem # Import System

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scanner_service.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ScannerService")

class IBKRErrorFilter(logging.Filter):
    def filter(self, record):
        msg = record.getMessage()
        if "Error 200" in msg or "Error 2119" in msg or "Warning 2119" in msg:
            return False
        return True

logging.getLogger('ib_insync.wrapper').addFilter(IBKRErrorFilter())
logging.getLogger('ib_insync.ib').addFilter(IBKRErrorFilter())


# 配置 (這些現在應該從 settings 或 profiles 獲取，保留以免破壞舊代碼)
CLIENT_ID = 104 
SCAN_INTERVAL = 900 # 15 Minutes 
OUTPUT_FILE = "hot_options.json"
MOCK_MODE = False # 設置為 False 以啟用真實連接

class ScannerService:
    def __init__(self):
        self.ib = IB()
        self.ib.errorEvent += self.on_error
        self.finviz = FinvizScraper()
        self.analyzer = LongOptionAnalyzer()
        self.short_analyzer = ShortOptionAnalyzer()
        self.uoa_analyzer = UnusualActivityAnalyzer()  # 異動期權分析器
        self.tech_analyzer = TechnicalDirectionAnalyzer()
        self.volume_profile = VolumeProfileAnalyzer()
        self.db = SQLiteManager()
        self.is_connected = False
        self.running = False
        self.latest_opportunities = []
        self._loop_task = None
        self.last_scan_time = None
        self.status_message = "Ready"
        self.analysis_system = None # Lazy init to avoid circular import/config issues

    async def _fetch_dark_pool_top_candidates(self, opportunities: List[Dict]) -> List[Dict]:
        """
        [Phase 5] Auto-trigger Dark Pool scanning for the top 3 candidates.
        Executes in an isolated thread to avoid blocking the main scanner loop limit.
        """
        if not opportunities:
            return opportunities
            
        # 1. Sort by score and get Top 3 tickers
        target_opps = sorted(opportunities, key=lambda x: x.get('score', 0), reverse=True)[:3]
        target_tickers = list(set([opp['ticker'] for opp in target_opps]))
        
        if not target_tickers:
            return opportunities
            
        logger.info(f"========== 啟動 Phase 5 暗池深度掃描 (Top {len(target_tickers)} 候選: {target_tickers}) ==========")
        
        def fetch_in_thread(tickers):
            import asyncio
            import random
            from data_layer.data_fetcher import DataFetcher
            from data_layer.ibkr_client import IBKRClient
            from config.settings import settings as SETTINGS
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            client = None
            fetcher = None
            dp_results = {}
            try:
                client = IBKRClient(
                    client_id=random.randint(1100, 1999), 
                    mode='paper' if SETTINGS.IBKR_USE_PAPER else 'live', 
                    port=SETTINGS.IBKR_PORT_PAPER if SETTINGS.IBKR_USE_PAPER else SETTINGS.IBKR_PORT_LIVE
                )
                if client.connect(timeout=5):
                    fetcher = DataFetcher(use_ibkr=True, ibkr_client=client)
                    for t in tickers:
                        logger.info(f"  [Dark Pool] 正在獲取 {t} 機構暗池大單 (需時 ~30 秒)...")
                        dp_data = fetcher.get_dark_pool_data(ticker=t, duration_seconds=30)
                        if dp_data:
                            dp_results[t] = dp_data
            except Exception as e:
                logger.error(f"Background Dark Pool Error: {e}")
            finally:
                if client:
                    client.disconnect()
                loop.close()
                
            return dp_results
            
        try:
            # 2. Run strictly in background thread to unblock the main async loop
            dp_results = await asyncio.to_thread(fetch_in_thread, target_tickers)
            
            # 3. Attach results back to the opportunities
            if dp_results:
                for opp in opportunities:
                    ticker = opp.get('ticker')
                    if ticker in dp_results:
                        opp['dark_pool'] = dp_results[ticker]
                        opp['dp_ratio'] = dp_results[ticker].get('dp_ratio', 0)
                        logger.info(f"  ✅ 成功附加 {ticker} 暗池數據 (DP Ratio: {opp['dp_ratio']}%)")
        except Exception as e:
            logger.warning(f"Dark Pool 背景掃描失敗: {e}")
            
        return opportunities

    def clear_opportunities(self):
        self.latest_opportunities = []
        logger.info("Cleared previous opportunities.")
        
    def sanitize_data(self, data):
        """Recursively replace NaN/Infinity with None for JSON compliance"""
        if isinstance(data, dict):
            return {k: self.sanitize_data(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self.sanitize_data(i) for i in data]
        elif isinstance(data, float):
            if math.isnan(data) or math.isinf(data):
                return None
        return data
        
    def on_error(self, reqId, errorCode, errorString, contract):
        if errorCode not in [200, 2104, 2106, 2108, 2119, 2158]: # 忽略常見的市場數據連接與查無合約提示
            logger.error(f"IBKR Error {errorCode}: {errorString}")

    async def connect(self):
        if self.is_connected and self.ib.isConnected():
            return True
        # Determine port based on configuration
        port = SETTINGS.IBKR_PORT_PAPER if SETTINGS.IBKR_USE_PAPER else SETTINGS.IBKR_PORT_LIVE
        logger.info(f"Connecting to IBKR (Host: {SETTINGS.IBKR_HOST}, Port: {port}, ClientId: {CLIENT_ID})...")
        try:
            await self.ib.connectAsync(SETTINGS.IBKR_HOST, port, clientId=CLIENT_ID)
            self.is_connected = True
            logger.info("IBKR Connected!")
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            self.is_connected = False
            return False

    async def start(self, selected_strategies: List[str] = None):
        """Start the scanner loop"""
        if self.running:
            logger.warning("Scanner is already running.")
            return
            
        self.running = True
        self.clear_opportunities() # Clear old data on start
        self._loop_task = asyncio.create_task(self.run_loop(selected_strategies))
        logger.info(f"Scanner started with strategies: {selected_strategies}")

    async def stop(self):
        """Stop the scanner loop"""
        if not self.running:
            return
            
        self.running = False
        logger.info("Scanner Service Stopping...")
        
        # Wait for the loop task to finish
        if self._loop_task:
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass
            self._loop_task = None
            
        if self.ib.isConnected():
             self.ib.disconnect()
             self.is_connected = False
        logger.info("Scanner Service Stopped properly.")

    async def get_candidates_for_profile(self, profile_name: str, profile: StrategyProfile) -> List[str]:
        """
        Get list of ticker candidates for a given profile.
        Tries Finviz Screener first, then falls back to static list.
        """
        logger.info(f"正在為策略 '{profile.name}' 獲取候選清單...")
        
        # 1. Try Dynamic Fetch via Finviz
        candidates = []
        try:
            # Note: Finviz scraper might block or fail, handle gracefully
            if not MOCK_MODE:
                results = self.finviz.get_screener_results(profile.criteria.finviz_filters, limit=10)
                candidates = [r['ticker'] for r in results]
                if candidates:
                    logger.info(f"[{profile.name}] 從 Finviz 獲取到 {len(candidates)} 隻股票: {candidates}")
        except Exception as e:
            logger.warning(f"[{profile.name}] Finviz 搜索失敗: {e}")
            
        # 2. Fallback to Static List 
        STATIC_WATCHLISTS = {
            "The_Titans": ["NVDA", "TSLA", "AAPL", "AMD", "MSFT", "AMZN", "GOOGL", "META", "ASML", "AVGO", "AMAT"],
            "Momentum_Growth": ["PLTR", "COIN", "MARA", "MSTR", "SMCI", "ARM", "CVNA"],
            "Catalysts_News": ["NVDA", "TSLA"],
            # 中小型股: AI / 量子計算 / 無人機 / 創新科技
            "Small_Cap_Movers": ["SOUN", "IONQ", "RGTI", "QBTS", "BBAI", "KULR", "ACHR", "RXRX", "RCAT", "ASTS"],
        }
        
        if not candidates:
            candidates = STATIC_WATCHLISTS.get(profile_name, [])
            logger.info(f"[{profile.name}] 使用靜態默認清單: {candidates}")
            
        return candidates

    async def scan_ticker(self, ticker: str, profile: StrategyProfile) -> List[Dict]:
        if not self.running: return []
        return await self._scan_ticker_impl(ticker, profile)

    async def _scan_ticker_impl(self, ticker: str, profile: StrategyProfile) -> List[Dict]:
        """
        Analyze a single ticker for opportunities based on the profile.
        Checks:
        1. Pre-market / Real-time Gap
        2. Volume
        3. Option Analysis (Long Call / Long Put)
        """
        logger.info(f"開始分析 {ticker} ({profile.name})...")
        
        # 1. Get Market Data (Price, Gap, Volume)
        contract = Stock(ticker, 'SMART', 'USD')
        await self.ib.qualifyContractsAsync(contract)
        
        # Set Market Data Type to 4 (Delayed Frozen) to support offline/weekend data
        self.ib.reqMarketDataType(4)
        
        # Request Snapshot
        ticker_data = self.ib.reqMktData(contract, '', True, False)
        # Wait for data (IBKR snapshot is async but usually fast, looping a bit safely)
        for _ in range(10):
            await asyncio.sleep(0.5)
            # Check if we have either last or close available and not nan
            has_last = ticker_data.last is not None and not math.isnan(ticker_data.last) and ticker_data.last > 0
            has_close = ticker_data.close is not None and not math.isnan(ticker_data.close) and ticker_data.close > 0
            if has_last or has_close:
                break
                
        has_last = ticker_data.last is not None and not math.isnan(ticker_data.last) and ticker_data.last > 0
        has_close = ticker_data.close is not None and not math.isnan(ticker_data.close) and ticker_data.close > 0
                
        if not has_last and not has_close:
            logger.warning(f"{ticker} 無法獲取有效報價，跳過")
            return []
            
        # Calculate Gap
        # Note: In pre-market, 'close' is usually yesterday's close. 'last' is current pre-market price.
        prev_close = ticker_data.close if has_close else ticker_data.last
        current_price = ticker_data.last if has_last else prev_close
        
        gap_pct = 0.0
        if prev_close > 0:
            gap_pct = ((current_price - prev_close) / prev_close) * 100
            
        volume = ticker_data.volume if ticker_data.volume is not None and not math.isnan(ticker_data.volume) else 0
        
        logger.info(f"{ticker}: Price={current_price}, Gap={gap_pct:.2f}%, Vol={volume}")
        
        # 2. Filter by Profile Criteria
        criteria = profile.criteria
        
        # Check Gap (Bypass if exactly 0.0 which means market is closed/frozen data)
        is_offline = (gap_pct == 0.0)

        if not is_offline and abs(gap_pct) < criteria.gap_min_pct:
            logger.info(f"{ticker} Gap {gap_pct:.2f}% < Min {criteria.gap_min_pct}%, 忽略")
            return []
            
        if not is_offline and criteria.gap_max_pct and abs(gap_pct) > criteria.gap_max_pct:
            # For Titans, we skip if gap is TOO big (might be overextended).
            # For Catalysts, gap_max_pct is None (unlimited).
            logger.info(f"{ticker} Gap {gap_pct:.2f}% > Max {criteria.gap_max_pct}%, 忽略")
            return []
            
        # Check Volume (if available in pre-market)
        # IBKR pre-market volume can be tricky, sometimes it's daily volume.
        # We'll be lenient here if volume is 0 or missing, but log it.
        # if volume < criteria.min_volume: ...
        
        # 3. Determine Direction & Analyze Options
        found_opportunities = []
        
        # Auto-Detect Direction
        # Gap Up -> Long Call
        # Gap Down -> Long Put
        # If offline, just default to CALL to test the system pipeline
        direction = "CALL" if gap_pct > 0 or is_offline else "PUT"
        
        # --- Long Strategies (Trend Following) ---
        if 'LONG_CALL' in criteria.preferred_strategies and direction == "CALL":
            # Analyze Long Call
            res = await self.analyze_options(ticker, current_price, "C", profile)
            if res: found_opportunities.append(res)
            
        if 'LONG_PUT' in criteria.preferred_strategies and direction == "PUT":
            # Analyze Long Put
            res = await self.analyze_options(ticker, current_price, "P", profile)
            if res: found_opportunities.append(res)

        # --- Short Strategies (Reversion / Income) ---
        # Short Call (Bearish/Neutral): Fade the rip (Gap Up > 3%)
        if 'SHORT_CALL' in criteria.preferred_strategies and gap_pct > 3.0:
             # Sell Call (OTM)
             res = await self.analyze_short_options(ticker, current_price, "C", profile)
             if res: found_opportunities.append(res)

        # Short Put (Bullish/Neutral): Buy the dip (Gap Down > 4%) OR Bullish Trend (Gap Up > 0.5% for Titans)
        if 'SHORT_PUT' in criteria.preferred_strategies:
             is_dip_buy = gap_pct < -4.0
             is_bullish_income = gap_pct > 0.5 and profile.name == "The_Titans"
             
             if is_dip_buy or is_bullish_income or is_offline:
                 # Sell Put (OTM)
                 res = await self.analyze_short_options(ticker, current_price, "P", profile)
                 if res: found_opportunities.append(res)
            
        return found_opportunities

    async def run_deep_analysis(self, ticker: str, setup_info: Dict = None):
        """
        Run the full 32-module analysis for a specific ticker.
        Executes in a separate thread with its own Event Loop and IB connection to avoid blocking the main scanner.
        """
        logger.info(f"Triggering Deep Analysis for {ticker}...")
        self.status_message = f"Initializing Deep Analysis for {ticker}..."
        
        # Parse setup_info
        strike = setup_info.get('strike') if setup_info else None
        expiry = setup_info.get('expiry') if setup_info else None
        
        strat = setup_info.get('strategy', '') if setup_info else ''
        option_type = None
        if 'CALL' in strat: option_type = 'C'
        elif 'PUT' in strat: option_type = 'P'
        
        # Define Progress Callback (Thread-safe)
        def progress_callback(step, total, message, module_name=None):
            self.status_message = f"analyzing {ticker}: [{step}/{total}] {message}"
            logger.info(self.status_message)

        # Thread Function
        def run_analysis_in_thread():
            import asyncio
            import random
            from main import OptionsAnalysisSystem
            from data_layer.ibkr_client import IBKRClient
            
            # 1. Create a NEW Event Loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            client = None
            try:
                # 2. Create ISOALTED IB Client
                # Random ID to avoid conflict with Scanner(104) and Others
                # Retry a few times if ID taken
                for _ in range(3):
                    try:
                        temp_id = random.randint(200, 999)
                        client = IBKRClient(
                            client_id=temp_id,
                            mode=('paper' if SETTINGS.IBKR_USE_PAPER else 'live'),
                            port=(SETTINGS.IBKR_PORT_PAPER if SETTINGS.IBKR_USE_PAPER else SETTINGS.IBKR_PORT_LIVE)
                        )
                        if client.connect(timeout=5):
                            break
                    except Exception:
                        continue
                
                if not client or not client.is_connected():
                    raise Exception("Failed to establish isolated IBKR connection for analysis.")

                # 3. Init System with this client
                system = OptionsAnalysisSystem(use_ibkr=True, ibkr_client=client)
                
                # 4. Run Analysis (Synchronous, but uses 'loop' we just created)
                result = system.run_complete_analysis(
                    ticker=ticker,
                    strike=strike,
                    expiration=expiry,
                    option_type=option_type,
                    progress_callback=progress_callback
                )
                
                # 5. Report Generation is handled internally by main.py
                msg = f"Completed Deep Analysis for {ticker}."
                progress_callback(32, 32, "Analysis & Report Finished")
                
                return result
                
            except Exception as e:
                logger.error(f"Thread Analysis Error: {e}")
                raise e
            finally:
                if client: client.disconnect()
                loop.close()

        try:
            # Execute in thread
            result = await asyncio.to_thread(run_analysis_in_thread)
            self.status_message = f"Deep Analysis for {ticker} Completed."
            return result
        except Exception as e:
            logger.error(f"Deep Analysis Failed: {e}")
            self.status_message = f"Analysis Failed: {str(e)}"
            raise e

    async def analyze_options(self, ticker: str, stock_price: float, right: str, profile: StrategyProfile, target_strike_price: float = None) -> Optional[Dict]:
        """
        Fetch option chain and score the best contract.
        """
        # Get Option Chain (Next Weekly or Monthly)
        contract = Stock(ticker, 'SMART', 'USD')
        await self.ib.qualifyContractsAsync(contract)
        
        chains = await self.ib.reqSecDefOptParamsAsync(contract.symbol, '', contract.secType, contract.conId)
        if not chains:
            return None
            
        # Select SMART exchange chain
        chain = next((c for c in chains if c.exchange == 'SMART'), chains[0])
        
        # 中短線策略: 目標找 30-90 天到期的合約
        # 30天以上: Theta 衰減壓力小，有足夠時間讓方向顯現
        # 90天以內: 槓桿效果仍然顯著，不用付 LEAPS 溢價
        today_str = datetime.now().strftime('%Y%m%d')
        today = datetime.now()
        expirations = sorted([exp for exp in chain.expirations if exp > today_str])
        if not expirations:
            return None
        
        # 篩選出 30-90 天範圍內的到期日
        target_expirations = []
        for exp in expirations:
            exp_date = datetime.strptime(exp, '%Y%m%d')
            dte = (exp_date - today).days
            if 30 <= dte <= 90:
                target_expirations.append(exp)
        
        # 如果 30-90 天範圍內沒有合約，退而求其次選最近的 >21 天到期
        if not target_expirations:
            for exp in expirations:
                exp_date = datetime.strptime(exp, '%Y%m%d')
                dte = (exp_date - today).days
                if dte >= 21:
                    target_expirations.append(exp)
                    break
        
        if not target_expirations:
            return None
        
        expiry = target_expirations[0]  # 選最接近 30 天的到期日
        
        # Find Strikes
        strikes = [k for k in chain.strikes if k % 1 == 0 or k % 2.5 == 0] # Filter weird strikes
        
        if target_strike_price is not None:
            # We already have a specific strike from Volume Profile
            target_strikes = [k for k in strikes if abs(k - target_strike_price) < (stock_price * 0.10)]
            target_strike = min(target_strikes, key=lambda x: abs(x - target_strike_price)) if target_strikes else min(strikes, key=lambda x: abs(x - target_strike_price))
        elif right == 'C': # CALL
            target_strikes = [k for k in strikes if k >= stock_price * 0.95 and k <= stock_price * 1.05]
            if not target_strikes: return None
            target_strike = min(target_strikes, key=lambda x: abs(x - stock_price))
        else: # PUT
            target_strikes = [k for k in strikes if k <= stock_price * 1.05 and k >= stock_price * 0.95]
            if not target_strikes: return None
            target_strike = min(target_strikes, key=lambda x: abs(x - stock_price))
        
        # Get Option Market Data
        opt_contract = Option(ticker, expiry, target_strike, right, 'SMART')
        await self.ib.qualifyContractsAsync(opt_contract)
        
        # Set Market Data Type to 4 (Delayed Frozen) for options as well
        self.ib.reqMarketDataType(4)
        
        # Request snapshot
        # Request snapshot with Generic Ticks for IV and Greeks (100: Option Vol, 101: OI, 106: IV)
        opt_data = self.ib.reqMktData(opt_contract, '100,101,106', False, False)
        # Only wait briefly but check if stopped
        for _ in range(10): 
            if not self.running: return None
            await asyncio.sleep(0.1)
            has_bid = opt_data.bid is not None and not math.isnan(opt_data.bid) and opt_data.bid > 0
            has_ask = opt_data.ask is not None and not math.isnan(opt_data.ask) and opt_data.ask > 0
            has_close = opt_data.close is not None and not math.isnan(opt_data.close) and opt_data.close > 0
            if (has_bid and has_ask) or has_close:
                break
        
        has_bid = opt_data.bid is not None and not math.isnan(opt_data.bid) and opt_data.bid > 0
        has_ask = opt_data.ask is not None and not math.isnan(opt_data.ask) and opt_data.ask > 0
        has_close = opt_data.close is not None and not math.isnan(opt_data.close) and opt_data.close > 0
        
        if not (has_bid and has_ask) and not has_close:
            return None

        # Run Analysis Module 26
        # Note: module26 expects certain args.
        # We can map IBKR data to what the analyzer needs.
        # Implied Vol and Greeks are in opt_data.modelGreeks if available, or opt_data.impliedVolatility
        iv = opt_data.impliedVolatility if opt_data.impliedVolatility is not None and not math.isnan(opt_data.impliedVolatility) else 0.5
        
        if has_bid and has_ask:
            premium = (opt_data.bid + opt_data.ask) / 2
        else:
            premium = opt_data.close
        
        # 動態計算真實 DTE (比寫死 7 天更準確)
        actual_dte = (datetime.strptime(expiry, '%Y%m%d') - datetime.now()).days
        
        analysis_result = {}
        if right == 'C':
            analysis_result = self.analyzer.analyze_long_call(
                stock_price=stock_price, strike_price=target_strike, premium=premium,
                days_to_expiration=actual_dte,
                iv=iv
            )
        else:
            analysis_result = self.analyzer.analyze_long_put(
                stock_price=stock_price, strike_price=target_strike, premium=premium,
                days_to_expiration=actual_dte,
                iv=iv
            )
            
        # Check Score
        score = analysis_result.get('score', {}).get('total_score', 0)
        
        if score > 60: # Threshold
            return {
                'ticker': ticker,
                'profile': profile.name,
                'strategy': f"LONG_{right == 'C' and 'CALL' or 'PUT'}",
                'strike': target_strike,
                'expiry': expiry,
                'price': stock_price,
                'premium': premium,
                'score': score,
                'analysis': analysis_result
            }
        return None

    async def analyze_short_options(self, ticker: str, stock_price: float, right: str, profile: StrategyProfile, target_strike_price: float = None) -> Optional[Dict]:
        """
        Analyze Short Call/Put opportunities.
        """
        # Get Option Chain
        contract = Stock(ticker, 'SMART', 'USD')
        await self.ib.qualifyContractsAsync(contract)
        chains = await self.ib.reqSecDefOptParamsAsync(contract.symbol, '', contract.secType, contract.conId)
        if not chains: return None
        chain = next((c for c in chains if c.exchange == 'SMART'), chains[0])
        
        # Expiry: Short strategies prefer < 30-45 days to maximize Theta decay.
        # Let's pick ~14-21 days.
        expirations = sorted([exp for exp in chain.expirations if exp > datetime.now().strftime('%Y%m%d')])
        if not expirations: return None
        # Pick 2nd or 3rd expiry (approx 2 weeks)
        expiry = expirations[min(2, len(expirations)-1)] 

        # Find Strikes (OTM)
        strikes = [k for k in chain.strikes if k % 1 == 0 or k % 2.5 == 0]
        
        if target_strike_price is not None:
            target_strikes = [k for k in strikes if abs(k - target_strike_price) < (stock_price * 0.10)]
            target_strike = min(target_strikes, key=lambda x: abs(x - target_strike_price)) if target_strikes else min(strikes, key=lambda x: abs(x - target_strike_price))
        elif right == 'C': # Short Call -> Want OTM (Strike > Price)
            target_strikes = [k for k in strikes if k > stock_price * 1.05 and k < stock_price * 1.15]
            if not target_strikes: return None
            target_strike = target_strikes[0]
        else: # Short Put -> Want OTM (Strike < Price)
            target_strikes = [k for k in strikes if k < stock_price * 0.95 and k > stock_price * 0.85]
            if not target_strikes: return None
            target_strike = target_strikes[-1]
        
        # Get Data
        opt_contract = Option(ticker, expiry, target_strike, right, 'SMART')
        await self.ib.qualifyContractsAsync(opt_contract)
        self.ib.reqMarketDataType(4)
        opt_data = self.ib.reqMktData(opt_contract, '100,101,106', False, False)
        
        for _ in range(10): 
            if not self.running: return None
            await asyncio.sleep(0.1)
            has_bid = opt_data.bid is not None and not math.isnan(opt_data.bid) and opt_data.bid > 0
            has_ask = opt_data.ask is not None and not math.isnan(opt_data.ask) and opt_data.ask > 0
            has_close = opt_data.close is not None and not math.isnan(opt_data.close) and opt_data.close > 0
            if (has_bid and has_ask) or has_close:
                break
            
        has_bid = opt_data.bid is not None and not math.isnan(opt_data.bid) and opt_data.bid > 0
        has_ask = opt_data.ask is not None and not math.isnan(opt_data.ask) and opt_data.ask > 0
        has_close = opt_data.close is not None and not math.isnan(opt_data.close) and opt_data.close > 0
        
        if not has_bid and not has_close: return None # No buyers
        
        iv = opt_data.impliedVolatility if opt_data.impliedVolatility is not None and not math.isnan(opt_data.impliedVolatility) else 0.5
        delta = opt_data.modelGreeks.delta if opt_data.modelGreeks and not math.isnan(opt_data.modelGreeks.delta) else (0.2 if right=='C' else -0.2)
        theta = opt_data.modelGreeks.theta if opt_data.modelGreeks and not math.isnan(opt_data.modelGreeks.theta) else 0.1
        
        if has_bid and has_ask:
            premium = (opt_data.bid + opt_data.ask) / 2
        else:
            premium = opt_data.close
        
        # Run Short Analysis
        days_to_expiry = 14 # Approx
        
        if right == 'C':
            analysis = self.short_analyzer.analyze_short_call(
                stock_price, target_strike, premium, days_to_expiry, delta, theta, iv
            )
        else:
            analysis = self.short_analyzer.analyze_short_put(
                stock_price, target_strike, premium, days_to_expiry, delta, theta, iv
            )
            
        score = analysis.get('score', {}).get('total_score', 0)
        
        if score >= 0:
             return {
                'ticker': ticker,
                'profile': profile.name,
                'strategy': f"SHORT_{right == 'C' and 'CALL' or 'PUT'}",
                'strike': target_strike,
                'expiry': expiry,
                'price': stock_price,
                'premium': premium,
                'score': score,
                'analysis': analysis
            }
        return None

    async def scan_for_unusual_activity(self, ticker: str) -> List[Dict]:
        """
        異動期權偵測 (UOA) - 對一岇股票主動投放的 30-90 天期符進行分析
        檢測: Volume Spike / 高 Vol/OI 比率 / 機構大單
        """
        if not self.running:
            return []
        
        logger.info(f"[UOA] 檢查 {ticker} 的異動期權訊號...")
        results = []
        
        try:
            import pandas as pd
            from datetime import datetime
            
            contract = Stock(ticker, 'SMART', 'USD')
            await self.ib.qualifyContractsAsync(contract)
            chains = await self.ib.reqSecDefOptParamsAsync(contract.symbol, '', contract.secType, contract.conId)
            if not chains:
                return []
            
            chain = next((c for c in chains if c.exchange == 'SMART'), chains[0])
            
            # 選 30-90 天到期日
            today = datetime.now()
            today_str = today.strftime('%Y%m%d')
            expirations = sorted([exp for exp in chain.expirations if exp > today_str])
            target_exp = None
            for exp in expirations:
                dte = (datetime.strptime(exp, '%Y%m%d') - today).days
                if 30 <= dte <= 90:
                    target_exp = exp
                    break
            if not target_exp:
                return []
            
            # 獲取股價
            stk_data = self.ib.reqMktData(contract, '', True, False)
            await asyncio.sleep(1)
            current_price = stk_data.last or stk_data.close or 0
            if current_price <= 0:
                return []
            
            # 獲取期權鎔定賃 (ATM 上下各 10%)
            strikes = sorted([k for k in chain.strikes
                              if current_price * 0.90 <= k <= current_price * 1.10])
            if not strikes:
                return []
            
            # 分別獲取 Call / Put 快照
            all_rows_call = []
            all_rows_put = []
            
            for strike in strikes[:10]:  # 限制 10 個自動計算數，避免超載
                for right in ('C', 'P'):
                    opt = Option(ticker, target_exp, strike, right, 'SMART')
                    try:
                        await self.ib.qualifyContractsAsync(opt)
                        self.ib.reqMarketDataType(4)
                        opt_data = self.ib.reqMktData(opt, '100,101', False, False)
                        await asyncio.sleep(0.2)
                        
                        vol = getattr(opt_data, 'volume', None)
                        oi = getattr(opt_data, 'openInterest', None)
                        last = getattr(opt_data, 'lastPrice', None) or getattr(opt_data, 'close', None)
                        
                        row = {
                            'strike': strike,
                            'volume': vol if vol and not math.isnan(vol) else 0,
                            'openInterest': oi if oi and not math.isnan(oi) else 0,
                            'lastPrice': last if last and not math.isnan(last) else 0,
                        }
                        if right == 'C':
                            all_rows_call.append(row)
                        else:
                            all_rows_put.append(row)
                    except Exception:
                        continue
            
            calls_df = pd.DataFrame(all_rows_call) if all_rows_call else pd.DataFrame()
            puts_df = pd.DataFrame(all_rows_put) if all_rows_put else pd.DataFrame()
            
            # 執行 UOA 分析
            uoa_result = self.uoa_analyzer.analyze_chain(calls_df, puts_df)
            
            for signal in uoa_result.get('calls', []) + uoa_result.get('puts', []):
                if signal.strength >= 60:  # 只國報高分訊號
                    results.append({
                        'ticker': ticker,
                        'profile': 'UOA_Scanner',
                        'strategy': f"異動_{'CALL' if signal.option_type == 'call' else 'PUT'}",
                        'strike': signal.strike,
                        'expiry': target_exp,
                        'price': current_price,
                        'premium': signal.metrics.get('premium', 0),
                        'score': signal.strength,
                        'signal_type': signal.signal_type,
                        'description': signal.description,
                        'analysis': signal.to_dict()
                    })
                    logger.info(f"  ⚡ [UOA] {ticker} 異動訊號: {signal.description}")
        
        except Exception as e:
            logger.warning(f"[UOA] {ticker} 分析失敗: {e}")
        
        return results

    async def run_loop(self, selected_strategies: List[str] = None, single_pass: bool = False):
        """Main Loop: UOA-First Pipeline"""
        logger.info("啟動掃描服務 (UOA-First 模式)...")
        import pandas as pd
        from datetime import datetime, timedelta
        
        # Filter profiles based on selection
        active_profiles = list(ALL_PROFILES.values()) 
        if selected_strategies:
            active_profiles = [p for p in active_profiles if p.name in selected_strategies]
            logger.info(f"已選擇策略: {selected_strategies}")
        
        try:
            while self.running:
                if not self.is_connected:
                    await self.connect()
                    
                if not self.ib.isConnected():
                    logger.error("IBKR 未連接，等待重試...")
                    await asyncio.sleep(10)
                    continue

                all_opportunities = []
                
                # Part 1: UOA 首重掃描
                logger.info("[UOA] 開始從選定策略名單中偵測異動期權...")
                all_tickers = set()
                profile_mapping = {}
                for profile in active_profiles:
                    tickers = await self.get_candidates_for_profile(profile.name, profile)
                    for t in tickers:
                        all_tickers.add(t)
                        if t not in profile_mapping:
                            profile_mapping[t] = profile
                
                logger.info(f"========== 啟動 UOA 第一階段掃描 ({len(all_tickers)} 支股票) ==========")
                for ticker in all_tickers:
                    if not self.running: break
                    
                    # 1. 第一層過濾: UOA 異動偵測 (Smart Money)
                    uoa_opps = await self.scan_for_unusual_activity(ticker)
                    if not uoa_opps:
                        continue
                        
                    # 找出最強的一個訊號
                    best_uoa = sorted(uoa_opps, key=lambda x: x['score'], reverse=True)[0]
                    direction = 'CALL' if 'CALL' in best_uoa['strategy'] else 'PUT'
                    
                    logger.info(f"  ⚡ {ticker} 發現強烈異動 ({direction}, Score: {best_uoa['score']})，進入技術面確認...")
                    
                    # 2. 第二層確認: 讀取 K 線進行多重均線與籌碼分析
                    contract = Stock(ticker, 'SMART', 'USD')
                    await self.ib.qualifyContractsAsync(contract)
                    
                    stk_data = self.ib.reqMktData(contract, '', True, False)
                    await asyncio.sleep(1)
                    current_price = stk_data.last or stk_data.close
                    if not current_price: continue

                    bars = await self.ib.reqHistoricalDataAsync(
                        contract, endDateTime='', durationStr='1 Y',
                        barSizeSetting='1 day', whatToShow='TRADES', useRTH=True
                    )
                    
                    if not bars or len(bars) < 50:
                        logger.warning(f"  {ticker} 歷史數據不足，跳過技術面確認。")
                        continue
                        
                    df = pd.DataFrame([{
                        'Date': b.date, 'Open': b.open, 'High': b.high, 
                        'Low': b.low, 'Close': b.close, 'Volume': b.volume
                    } for b in bars])
                    df.set_index('Date', inplace=True)
                    
                    # 技術面趨勢分析
                    tech_result = self.tech_analyzer.analyze(ticker, df, current_price=current_price)
                    daily_trend = tech_result.daily_trend.trend # 'Bullish', 'Bearish', 'Neutral'
                    
                    # 趨勢必須支持異動方向
                    if direction == 'CALL' and daily_trend != 'Bullish':
                        logger.info(f"  {ticker} 放棄: UOA(Call) 與均線趨勢({daily_trend})衝突。")
                        continue
                    if direction == 'PUT' and daily_trend != 'Bearish':
                        logger.info(f"  {ticker} 放棄: UOA(Put) 與均線趨勢({daily_trend})衝突。")
                        continue
                        
                    # 籌碼分佈分析 (POC/HVN)
                    vp_result = self.volume_profile.analyze(ticker, df, current_price=current_price)
                    if not vp_result: continue
                    
                    # 3. 第三層: 基於 POC/HVN 的精準行使價選擇
                    target_strike = current_price
                    if direction == 'CALL':
                        supports = vp_result.get_support_levels(current_price)
                        if supports:
                            target_strike = supports[0] # 取最靠近現價的下方支撐
                            logger.info(f"  {ticker} 趨勢吻合！尋找到下方籌碼支撐位: {target_strike:.2f}")
                        else:
                            target_strike = current_price * 0.95
                    else:
                        resistances = vp_result.get_resistance_levels(current_price)
                        if resistances:
                            target_strike = resistances[0] # 取最靠近現價的上方阻力
                            logger.info(f"  {ticker} 趨勢吻合！尋找到上方籌碼阻力位: {target_strike:.2f}")
                        else:
                            target_strike = current_price * 1.05
                            
                    # 4. 生成選中的期權機會
                    profile = profile_mapping.get(ticker)
                    if not profile: continue
                    
                    # 分析 Long 方向 (如果 Profile 支持)
                    if 'LONG_CALL' in profile.criteria.preferred_strategies and direction == 'CALL':
                        res = await self.analyze_options(ticker, current_price, "C", profile, target_strike_price=target_strike)
                        if res: 
                            res['reasoning'] = f"UOA偵測 + {daily_trend}確認 + 支撐位({target_strike:.2f})"
                            res['uoa_score'] = best_uoa['score']
                            all_opportunities.append(res)
                            
                    if 'LONG_PUT' in profile.criteria.preferred_strategies and direction == 'PUT':
                        res = await self.analyze_options(ticker, current_price, "P", profile, target_strike_price=target_strike)
                        if res: 
                            res['reasoning'] = f"UOA偵測 + {daily_trend}確認 + 阻力位({target_strike:.2f})"
                            res['uoa_score'] = best_uoa['score']
                            all_opportunities.append(res)
                            
                    # 分析 Short 放向防守 (如果 Profile 支持)
                    if 'SHORT_PUT' in profile.criteria.preferred_strategies and direction == 'CALL':
                        res = await self.analyze_short_options(ticker, current_price, "P", profile, target_strike_price=target_strike)
                        if res: 
                            res['reasoning'] = f"UOA大單看漲 + {daily_trend}確認 + 賣出支撐區間Put防守({target_strike:.2f})"
                            res['uoa_score'] = best_uoa['score']
                            all_opportunities.append(res)
                            
                    if 'SHORT_CALL' in profile.criteria.preferred_strategies and direction == 'PUT':
                        res = await self.analyze_short_options(ticker, current_price, "C", profile, target_strike_price=target_strike)
                        if res: 
                            res['reasoning'] = f"UOA大單看跌 + {daily_trend}確認 + 賣出阻力區間Call防守({target_strike:.2f})"
                            res['uoa_score'] = best_uoa['score']
                            all_opportunities.append(res)
                            
                # Output Results
                if all_opportunities:
                    # [Phase 5] Auto Fetch Dark Pool for top 3 before saving
                    all_opportunities = await self._fetch_dark_pool_top_candidates(all_opportunities)
                    
                    # Sanitize data to remove NaNs before usage
                    clean_opps = self.sanitize_data(all_opportunities)
                    self.latest_opportunities = clean_opps # Update in-memory for Web UI
                    self.last_scan_time = datetime.now()
                    self.status_message = f"Scan Complete. Found {len(clean_opps)} opportunities."
                    logger.info(f"掃描完成! 發現 {len(clean_opps)} 個機會")
                    
                    # [NEW] Phase E: Trigger Deep Analysis for Top 1 Pick
                    try:
                        if clean_opps:
                            top_opp = sorted(clean_opps, key=lambda x: x.get('score', 0), reverse=True)[0]
                            logger.info(f"🏆 自動觸發 Top 1 候選標的深度分析 (40 模組): {top_opp['ticker']}")
                            asyncio.create_task(self.run_deep_analysis(
                                ticker=top_opp['ticker'],
                                setup_info={
                                    'strike': top_opp.get('strike'),
                                    'expiry': top_opp.get('expiry'),
                                    'strategy': top_opp.get('strategy')
                                }
                            ))
                    except Exception as e:
                        logger.error(f"Failed to auto-trigger deep analysis: {e}")

                    # Save to file as backup
                    try:
                        with open(OUTPUT_FILE, 'w') as f:
                            json.dump(clean_opps, f, default=str, indent=4)
                        # Save to SQLite
                        self.db.bulk_insert(clean_opps)
                    except Exception as e:
                        logger.error(f"Failed to save results: {e}")
                else:
                    self.last_scan_time = datetime.now()
                    self.status_message = "Scan Complete. No opportunities found."
                    logger.info("本輪掃描未發現高分機會。")
                    try:
                        with open(OUTPUT_FILE, 'w') as f:
                            json.dump([], f)
                    except Exception as e:
                        logger.error(f"Failed to clear results file: {e}")
                    
                if single_pass:
                    logger.info("Single pass complete. Exiting loop.")
                    break
                    
                # Wait interval
                for _ in range(SCAN_INTERVAL):
                    if not self.running: break
                    
                    # Check connection health periodically
                    if not self.ib.isConnected():
                         logger.warning("IBKR Disconnected! Attempting reconnect...")
                         await self.connect()

                    await asyncio.sleep(1)
                    
        except KeyboardInterrupt:
            logger.info("Scanner Service Stopped")
        except Exception as e:
            logger.error(f"Scanner Loop Error: {e}")
        finally:
            self.running = False
            self.ib.disconnect()

    async def run_loop_technical(self, selected_strategies: List[str] = None, single_pass: bool = False):
        """Technical-First Pipeline (RSI, MACD, MA, Vol Profile) - 適用於盤前或無期權即時異動環境"""
        logger.info("啟動掃描服務 (Technical-First 模式)...")
        import pandas as pd
        from datetime import datetime
        
        active_profiles = list(ALL_PROFILES.values()) 
        if selected_strategies:
            active_profiles = [p for p in active_profiles if p.name in selected_strategies]
            logger.info(f"已選擇策略: {selected_strategies}")
            
        try:
            while self.running:
                if not self.is_connected:
                    await self.connect()
                if not self.ib.isConnected():
                    logger.error("IBKR 未連接，等待重試...")
                    await asyncio.sleep(10)
                    continue

                all_opportunities = []
                all_tickers = set()
                profile_mapping = {}
                for profile in active_profiles:
                    tickers = await self.get_candidates_for_profile(profile.name, profile)
                    for t in tickers:
                        all_tickers.add(t)
                        if t not in profile_mapping:
                            profile_mapping[t] = profile

                logger.info(f"========== 啟動 Technical-First 掃描 ({len(all_tickers)} 支股票) ==========")
                for ticker in all_tickers:
                    if not self.running: break
                    
                    try:
                        contract = Stock(ticker, 'SMART', 'USD')
                        await self.ib.qualifyContractsAsync(contract)
                        
                        stk_data = self.ib.reqMktData(contract, '', True, False)
                        await asyncio.sleep(1)
                        current_price = stk_data.last or stk_data.close
                        if not current_price: continue
                        
                        bars = await self.ib.reqHistoricalDataAsync(
                            contract, endDateTime='', durationStr='1 Y',
                            barSizeSetting='1 day', whatToShow='TRADES', useRTH=True
                        )
                        if not bars or len(bars) < 50:
                            continue
                            
                        df = pd.DataFrame([{
                            'Date': b.date, 'Open': b.open, 'High': b.high, 
                            'Low': b.low, 'Close': b.close, 'Volume': b.volume
                        } for b in bars])
                        df.set_index('Date', inplace=True)
                        
                        # 1. 技術面趨勢分析 (MA, RSI, MACD)
                        tech_result = self.tech_analyzer.analyze(ticker, df, current_price=current_price)
                        daily_trend = tech_result.daily_trend.trend # 'Bullish', 'Bearish', 'Neutral'
                        rsi = tech_result.daily_trend.rsi or 50.0
                        
                        if daily_trend == 'Neutral':
                            continue
                            
                        # 2. 籌碼分佈分析 (POC/HVN)
                        vp_result = self.volume_profile.analyze(ticker, df, current_price=current_price)
                        if not vp_result: continue
                        
                        profile = profile_mapping.get(ticker)
                        if not profile: continue
                        
                        logger.info(f"  > {ticker} 趨勢: {daily_trend}, RSI: {rsi:.1f}, POC: {vp_result.poc:.2f}")
                        
                        # 3. 決策邏輯
                        target_strike = current_price
                        reasoning = ""
                        
                        # Bullish (避免 RSI 超買)
                        if daily_trend == 'Bullish' and rsi < 70:
                            supports = vp_result.get_support_levels(current_price)
                            if supports:
                                target_strike = max(supports)
                            else:
                                target_strike = vp_result.poc
                                
                            reasoning = f"Tech 看漲 (RSI:{rsi:.1f}) + 籌碼支撐({target_strike:.2f})"
                            
                            if 'LONG_CALL' in profile.criteria.preferred_strategies:
                                res = await self.analyze_options(ticker, current_price, "C", profile, target_strike_price=target_strike)
                                if res: 
                                    res['reasoning'] = reasoning; res['uoa_score'] = 0; all_opportunities.append(res)
                            if 'SHORT_PUT' in profile.criteria.preferred_strategies:
                                res = await self.analyze_short_options(ticker, current_price, "P", profile, target_strike_price=target_strike)
                                if res: 
                                    res['reasoning'] = reasoning; res['uoa_score'] = 0; all_opportunities.append(res)
                                    
                        # Bearish (避免 RSI 超賣)
                        elif daily_trend == 'Bearish' and rsi > 30:
                            resistances = vp_result.get_resistance_levels(current_price)
                            if resistances:
                                target_strike = min(resistances)
                            else:
                                target_strike = vp_result.poc
                                
                            reasoning = f"Tech 看跌 (RSI:{rsi:.1f}) + 籌碼阻力({target_strike:.2f})"
                            
                            if 'LONG_PUT' in profile.criteria.preferred_strategies:
                                res = await self.analyze_options(ticker, current_price, "P", profile, target_strike_price=target_strike)
                                if res: 
                                    res['reasoning'] = reasoning; res['uoa_score'] = 0; all_opportunities.append(res)
                            if 'SHORT_CALL' in profile.criteria.preferred_strategies:
                                res = await self.analyze_short_options(ticker, current_price, "C", profile, target_strike_price=target_strike)
                                if res: 
                                    res['reasoning'] = reasoning; res['uoa_score'] = 0; all_opportunities.append(res)
                                    
                    except Exception as e:
                        logger.warning(f"  {ticker} Technical 掃描錯誤: {e}")

                # output
                if all_opportunities:
                    # [Phase 5] Auto Fetch Dark Pool for top 3 before saving
                    all_opportunities = await self._fetch_dark_pool_top_candidates(all_opportunities)
                
                    clean_opps = self.sanitize_data(all_opportunities)
                    self.latest_opportunities = clean_opps
                    self.last_scan_time = datetime.now()
                    self.status_message = f"Tech Scan Complete. Found {len(clean_opps)} opportunities."
                    logger.info(f"技術面掃描完成! 發現 {len(clean_opps)} 個機會")
                    
                    # [NEW] Phase E: Trigger Deep Analysis for Top 1 Pick
                    try:
                        if clean_opps:
                            top_opp = sorted(clean_opps, key=lambda x: x.get('score', 0), reverse=True)[0]
                            logger.info(f"🏆 自動觸發 Top 1 候選標的技術面深度分析 (40 模組): {top_opp['ticker']}")
                            asyncio.create_task(self.run_deep_analysis(
                                ticker=top_opp['ticker'],
                                setup_info={
                                    'strike': top_opp.get('strike'),
                                    'expiry': top_opp.get('expiry'),
                                    'strategy': top_opp.get('strategy')
                                }
                            ))
                    except Exception as e:
                        logger.error(f"Failed to auto-trigger deep analysis in tech loop: {e}")

                    try:
                        with open(OUTPUT_FILE, 'w') as f:
                            json.dump(clean_opps, f, default=str, indent=4)
                        self.db.bulk_insert(clean_opps)
                    except Exception as e:
                        logger.error(f"Failed to save results: {e}")
                else:
                    self.last_scan_time = datetime.now()
                    self.status_message = "Tech Scan Complete. No opportunities found."
                    logger.info("本輪技術面掃描未發現符合條件機會。")
                    try:
                        with open(OUTPUT_FILE, 'w') as f:
                            json.dump([], f)
                    except Exception as e:
                        logger.error(f"Failed to clear results file: {e}")

                if single_pass:
                    logger.info("Single pass complete. Exiting loop.")
                    break
                
                for _ in range(SCAN_INTERVAL):
                    if not self.running: break
                    if not self.ib.isConnected(): await self.connect()
                    await asyncio.sleep(1)

        except KeyboardInterrupt:
            logger.info("Scanner Service Stopped")
        except Exception as e:
            logger.error(f"Technical Loop Error: {e}")
        finally:
            self.running = False
            self.ib.disconnect()

    def run(self):
        self.running = True
        asyncio.run(self.run_loop())

if __name__ == "__main__":
    service = ScannerService()
    service.run()
