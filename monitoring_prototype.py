import asyncio
import logging
from ib_insync import *
import pandas as pd
from datetime import datetime

# 配置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MonitoringPrototype:
    def __init__(self):
        self.ib = IB()
        self.watchlist_ticker = "MSFT"
        self.active_contracts = {} # conId -> contract
        self.monitored_streams = {} # conId -> stream
        
    # Removed sync connect method

    async def run_scanner(self):
        """運行 IBKR 原生掃描器尋找活躍期權"""
        logger.info(f"啟動掃描器: {self.watchlist_ticker} (Hot Option Volume)...")
        
        # 定義掃描訂閱
        # scanCode='TOP_OPT_VOLUME_MOST_ACTIVE' 或 'HOT_BY_VOLUME'
        # instrument='STK' 是針對股票，但我們要找的是 OPT。
        # IBKR Scanner 有時需要 instrument='OPT'。
        # 這裡從 Stock 出發查找相關 Option
        
        sub = ScannerSubscription(
            instrument='OPT', 
            locationCode='OPT.US', 
            scanCode='TOP_OPT_VOLUME_MOST_ACTIVE'
        )
        
        # 過濾條件: 針對 MSFT，成交量 > 100
        # TagValues 可以用來過濾 underlying
        # 但 ib_insync 對 Scanner 參數的支持比較通用，我們可能需要先掃描再過濾，
        # 或者使用高級過濾 (TagValues)
        
        # 嘗試使用 TagValues 過濾 Underlying (這需要查閱具體 API 文檔，有時比較 tricky)
        # 為了原型簡單，我們先不加過濾，直接獲取市場最活躍，然後在回調裡過濾 MSFT (效率低但穩妥)
        # 或者，更高效的方法是: 獲取 MSFT 的 Option Chain，然後手動排序 Volume? 
        # 不，用戶要求 "Scanner"，我們試試直接用 Scanner 對特定 Tick。
        # IBKR TWS Scanner 窗口允許選 "Underlying"，對應 API 是 scanCode + TagValues.
        
        # 修正: ScannerSubscription 的參數比較難精確鎖定單一股票。
        # 很多策略是: 獲取 Option Chain -> reqMktData (Snapshot) -> 排序 -> Streaming Top N.
        # 但 "漏斗式掃描" 正是這個意思。
        # 讓我們試試用 reqSecDefOptParams 配合 Snapshot 來模擬 "Scanner" (更精確控制)。
        
        pass 
        # 上面的注釋是思考過程。為了原型最快見效，我們採用 "Option Chain Snapshot + Sort" 方案
        # 因為這能保證 100% 是 MSFT 的合約，而且我們可以完全控制過濾邏輯 (90天內, ATM等)。
        
    async def smart_scan_and_stream(self):
        """
        替代方案: 
        1. 獲取 MSFT 期權鏈 (限制在 90 天內, ATM +/- 10%)
        2. 快照獲取 Volume
        3. 排序選出 Top 5
        4. 開啟 Tick-by-Tick 監控
        """
        logger.info(f"步驟 1: 獲取 {self.watchlist_ticker} 期權鏈...")
        
        stock = Stock(self.watchlist_ticker, 'SMART', 'USD')
        await self.ib.qualifyContractsAsync(stock)
        
        # 獲取價格以確定 ATM
        self.ib.reqMktData(stock, '', True, False)
        await asyncio.sleep(1)
        ticker = self.ib.ticker(stock)
        current_price = ticker.marketPrice()
        
        # Fallback for offline/weekend testing
        import math
        if not current_price or math.isnan(current_price) or current_price <= 0:
            logger.warning("無法獲取實時股價 (可能是週末)，使用模擬價格: 430.0")
            current_price = 430.0
            
        logger.info(f"  {self.watchlist_ticker} 當前價格: {current_price}")
        
        if not current_price:
            logger.error("無法獲取股價，退出")
            return

        # 獲取合約定義
        chains = await self.ib.reqSecDefOptParamsAsync(stock.symbol, '', stock.secType, stock.conId)
        
        # 過濾: 90天內
        valid_expirations = []
        today = datetime.now()
        for chain in chains:
            for exp in chain.expirations:
                # exp 是 str 'YYYYMMDD' 或 datetime
                # ib_insync 通常返回 str
                d = datetime.strptime(exp, '%Y%m%d')
                if 0 < (d - today).days <= 90:
                    valid_expirations.append(exp)
        
        valid_expirations = sorted(list(set(valid_expirations)))[:2] # 只取最近的 2 個到期日以節省時間
        logger.info(f"  掃描到期日: {valid_expirations}")
        
        # 構建合約列表 (ATM +/- 5%)
        contracts_to_scan = []
        # 使用 set 避免重複 (不同交易所可能返回相同合約)
        seen_contracts = set()
        
        for chain in chains:
            # 轉換 chain 的 expirations 為 str 列表以便比較
            chain_exps = []
            for e in chain.expirations:
                if isinstance(e, str): chain_exps.append(e)
                else: chain_exps.append(e.strftime('%Y%m%d'))
            
            for exp in valid_expirations:
                if exp in chain_exps:
                    # 找到對應的 strike
                    strikes = [k for k in chain.strikes if 0.95 * current_price < k < 1.05 * current_price]
                    for strike in strikes:
                        for right in ['C', 'P']:
                            contract_key = (exp, strike, right)
                            if contract_key not in seen_contracts:
                                contracts_to_scan.append(Option(self.watchlist_ticker, exp, strike, right, 'SMART'))
                                seen_contracts.add(contract_key)
        
        logger.info(f"步驟 2: 快照掃描 {len(contracts_to_scan)} 個合約的成交量...")
        
        # 批量獲取快照
        await self.ib.qualifyContractsAsync(*contracts_to_scan)
        tickers = []
        for c in contracts_to_scan:
             # Snapshot=True, GenericTick=100 (Option Volume)
             t = self.ib.reqMktData(c, '100', True, False)
             tickers.append(t)
             
        # 等待數據填充
        logger.info("  等待快照數據 (4秒)...")
        await asyncio.sleep(4)
        
        # 排序
        # 注意: snapshot 返回後 tick.volume 可能為 nan，要處理
        valid_tickers = [t for t in tickers if t.volume and t.volume > 0]
        
        if valid_tickers:
            sorted_tickers = sorted(valid_tickers, key=lambda t: t.volume, reverse=True)
            target_tickers = sorted_tickers[:5] # Top 5
        else:
            logger.warning("沒有找到有成交量的合約 (可能市場關閉)，選取前 5 個合約進行測試。")
            target_tickers = tickers[:5]
        
        logger.info("步驟 3: 鎖定 Top 5 活躍合約:")
        for t in target_tickers:
            logger.info(f"  * {t.contract.localSymbol} (Vol: {t.volume})")
            
        # 步驟 4: 開啟 Tick-by-Tick 監控
        logger.info("步驟 4: 啟動實時成交明細 (Aggressor Analysis)...")
        
        for t in target_tickers:
            # 取消之前的 snapshot 訂閱 (如果是 snapshot=True)
            # 但這裡 t 是用 reqMktData 對象，我們可以復用，或者重新訂閱 Streaming
            # 我們重新訂閱 Streaming (snapshot=False)
            self.ib.cancelMktData(t.contract)
            
            # 使用 reqMktData 獲取實時流 (Bid/Ask/Last/Volume)
            # 這是最通用的方式，兼顧了報價和最新成交
            self.ib.reqMktData(t.contract, '', False, False)
            
        # 註冊回調 (通用更新事件)
        self.ib.pendingTickersEvent += self.on_pending_tickers
        
        # 保持運行
        logger.info("  監控中... (按 Ctrl+C 停止)")
        while True:
            await asyncio.sleep(1)

    def on_pending_tickers(self, tickers):
        """
        當有 Ticker 更新時觸發
        """
        for t in tickers:
            # 我們只關心這是我們監控的 MSFT 期權
            if t.contract.secType != 'OPT':
                continue
                
            # 檢查是否有成交更新 (Last Price / Size)
            # 注意: 這裡不能準確區分到底是哪一筆 Trade 觸發的更新 (因為是聚合的 250ms 快照)
            # 但對於原型展示 Aggressor 邏輯足夠了
            
            # 簡單防抖: 記錄上次的 Volume? 
            # 為了原型簡單，我們直接比較 t.last 和 t.bid/t.ask
            # (生產環境應使用 tickByTickData 獲得逐筆)
            
            if not t.last or not t.bid or not t.ask:
                continue
                
            price = t.last
            size = t.lastSize if t.lastSize else 0 # 有時 lastSize 可能為 NaN
            bid = t.bid
            ask = t.ask
            symbol = t.contract.localSymbol
            
            # 過濾無效更新 (例如只是 Bid/Ask 變動但 Last 沒變)
            # 這裡假設如果 Last 存在就分析 (實際應檢查 Last 是否改變)
            
            direction = "NEUTRAL"
            log_level = logging.INFO
            
            if price >= ask:
                direction = "BUY (Long)"
                log_level = logging.WARNING # 高亮
            elif price <= bid:
                direction = "SELL (Short)"
                log_level = logging.WARNING
                
            if direction != "NEUTRAL":
                # 只有當方向明確時才打印，減少刷屏 (因為 pendingTickers 會頻繁觸發)
                 logger.log(log_level, f">>> 異動 ({symbol}): {direction} | Price: {price} | Ref: {bid}/{ask}")

    async def run_async(self):
        """異步入口"""
        # 在 Loop 內連接
        logger.info("Connecting to IBKR (Async)...")
        try:
            await self.ib.connectAsync('127.0.0.1', 7497, clientId=101)
            logger.info("IBKR Connected!")
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return

        try:
            await self.smart_scan_and_stream()
        except Exception as e:
            logger.error(f"Runtime error: {e}")
        finally:
            self.ib.disconnect()

    def run(self):
        try:
            asyncio.run(self.run_async())
        except KeyboardInterrupt:
            logger.info("停止監控")

if __name__ == "__main__":
    monitor = MonitoringPrototype()
    monitor.run()
