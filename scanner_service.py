import asyncio
import logging
import json
import os
import random
import math
from typing import List, Dict, Optional
from datetime import datetime

from ib_insync import *
from config.settings import settings as SETTINGS
from config.strategy_profiles import ALL_PROFILES, StrategyProfile
from data_layer.finviz_scraper import FinvizScraper
from calculation_layer.module26_long_option_analysis import LongOptionAnalyzer
from calculation_layer.module28_short_option_analysis import ShortOptionAnalyzer
from data_layer.ibkr_client import IBKRClient # Import Client Wrapper
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
        self.is_connected = False
        self.running = False
        self.latest_opportunities = []
        self._loop_task = None
        self.last_scan_time = None
        self.status_message = "Ready"
        self.analysis_system = None # Lazy init to avoid circular import/config issues

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
        if errorCode not in [2104, 2106, 2158]: # 忽略常見的市場數據連接提示
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
            "The_Titans": ["NVDA", "TSLA", "AAPL", "AMD", "MSFT", "AMZN", "GOOGL", "META"],
            "Momentum_Growth": ["PLTR", "COIN", "MARA", "MSTR", "SMCI", "ARM", "CVNA"],
            "Catalysts_News": ["NVDA", "TSLA"] 
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
                
                # 5. Generate Report
                msg = f"Generating Report for {ticker}..."
                progress_callback(32, 32, "Generating Report")
                system.report_generator.generate_json_report(result, ticker)
                
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

    async def analyze_options(self, ticker: str, stock_price: float, right: str, profile: StrategyProfile) -> Optional[Dict]:
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
        
        # Find expiry (closest to 14-30 days for Titans, maybe shorter for Momentum?)
        # For simplicity, let's pick the 2nd or 3rd expiry (approx 1-2 weeks out) to avoid 0DTE risks for now.
        expirations = sorted([exp for exp in chain.expirations if exp > datetime.now().strftime('%Y%m%d')])
        if not expirations:
            return None
        expiry = expirations[min(1, len(expirations)-1)] # Pick 2nd expiry if available
        
        # Find Strikes
        strikes = [k for k in chain.strikes if k % 1 == 0 or k % 2.5 == 0] # Filter weird strikes
        
        if right == 'C': # CALL
            # For Calls, we want ITM/ATM or slightly OTM. Let's look around ATM.
            # Delta ~ 0.5
            target_strikes = [k for k in strikes if k >= stock_price * 0.95 and k <= stock_price * 1.05]
        else: # PUT
            target_strikes = [k for k in strikes if k <= stock_price * 1.05 and k >= stock_price * 0.95]
            
        if not target_strikes:
            return None
            
        # Select closest to ATM
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
        
        analysis_result = {}
        if right == 'C':
            analysis_result = self.analyzer.analyze_long_call(
                stock_price=stock_price, strike_price=target_strike, premium=premium,
                days_to_expiration=7, # Approx
                iv=iv
            )
        else:
            analysis_result = self.analyzer.analyze_long_put(
                stock_price=stock_price, strike_price=target_strike, premium=premium,
                days_to_expiration=7,
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

    async def analyze_short_options(self, ticker: str, stock_price: float, right: str, profile: StrategyProfile) -> Optional[Dict]:
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
        
        if right == 'C': # Short Call -> Want OTM (Strike > Price)
            # Target Delta ~0.20-0.30 -> Usually 5-10% OTM depending on IV
            target_strikes = [k for k in strikes if k > stock_price * 1.05 and k < stock_price * 1.15]
        else: # Short Put -> Want OTM (Strike < Price)
            target_strikes = [k for k in strikes if k < stock_price * 0.95 and k > stock_price * 0.85]
            
        if not target_strikes: return None
        
        # Select strike closest to desired range
        target_strike = target_strikes[0] if target_strikes else strikes[0] # Fallback
        
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
        
        if score > 50:
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

    async def run_loop(self, selected_strategies: List[str] = None):
        """Main Loop"""
        logger.info("啟動掃描服務...")
        
        # Filter profiles based on selection
        active_profiles = list(ALL_PROFILES.values()) # Convert dict_values to list
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
                
                # Scan each active profile
                for profile in active_profiles:
                    if not self.running: break
                    
                    tickers = await self.get_candidates_for_profile(profile.name, profile)
                    
                    for ticker in tickers:
                        if not self.running: break
                        opps = await self.scan_ticker(ticker, profile)
                        if opps:
                            all_opportunities.extend(opps)
                            
                # Output Results
                if all_opportunities:
                    # Sanitize data to remove NaNs before usage
                    clean_opps = self.sanitize_data(all_opportunities)
                    self.latest_opportunities = clean_opps # Update in-memory for Web UI
                    self.last_scan_time = datetime.now()
                    self.status_message = f"Scan Complete. Found {len(clean_opps)} opportunities."
                    logger.info(f"掃描完成! 發現 {len(clean_opps)} 個機會")
                    # Save to file as backup
                    try:
                        with open(OUTPUT_FILE, 'w') as f:
                            json.dump(clean_opps, f, default=str, indent=4)
                    except Exception as e:
                        logger.error(f"Failed to save results: {e}")
                else:
                    self.last_scan_time = datetime.now()
                    self.status_message = "Scan Complete. No opportunities found."
                    logger.info("本輪掃描未發現高分機會。")
                    
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

    def run(self):
        self.running = True
        asyncio.run(self.run_loop())

if __name__ == "__main__":
    service = ScannerService()
    service.run()
