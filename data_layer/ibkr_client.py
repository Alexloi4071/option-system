# data_layer/ibkr_client.py
"""
Interactive Brokers (IBKR) API 客戶端
支持 TWS 和 IB Gateway 連接
"""

import logging
import time
from typing import Dict, Optional, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

# 嘗試導入 ib_insync（IBKR Python API）
try:
    from ib_insync import IB, Stock, Option, Contract, util
    IB_INSYNC_AVAILABLE = True
except ImportError:
    IB_INSYNC_AVAILABLE = False
    # 定義虛擬類以防止 NameError
    class Contract: pass
    class IB: pass
    class Stock: pass
    class Option: pass
    logger.warning("! ib_insync 未安裝，IBKR 功能將不可用。安裝: pip install ib_insync")


class IBKRClient:
    """
    Interactive Brokers 客戶端
    
    功能:
    - 連接 TWS 或 IB Gateway
    - 獲取實時期權數據
    - 獲取 Greeks (Delta, Gamma, Theta, Vega, Rho)
    - 獲取實時 Bid/Ask 價差
    - 自動重試和錯誤處理
    - 支持降級到其他數據源
    """
    
    def __init__(self, host: str = "127.0.0.1", port: int = 7497, 
                 client_id: int = 100, mode: str = 'paper'):
        """
        初始化 IBKR 客戶端
        
        參數:
            host: TWS/Gateway 主機地址 (默認 127.0.0.1)
            port: 端口 (7497=Paper, 7496=Live)
            client_id: 客戶端 ID (必須唯一)
            mode: 'paper' 或 'live'
        """
        if not IB_INSYNC_AVAILABLE:
            raise ImportError("ib_insync 未安裝，無法使用 IBKR 功能")
        
        self.host = host
        self.port = port
        self.client_id = client_id
        self.mode = mode
        self.ib = IB()
        self.connected = False
        self.last_error = None
        self.connection_attempts = 0
        self.max_connection_attempts = 3
        
        logger.info(f"IBKR 客戶端初始化: {host}:{port} (mode={mode}, client_id={client_id})")
    
    def connect(self, timeout: int = 10) -> bool:
        """
        連接到 TWS/Gateway
        
        參數:
            timeout: 連接超時時間（秒）
        
        返回:
            bool: 是否成功連接
        """
        if self.connected:
            logger.info("IBKR 已連接，無需重複連接")
            return True
        
        if not IB_INSYNC_AVAILABLE:
            logger.error("x ib_insync 未安裝，無法連接 IBKR")
            return False
        
        try:
            logger.info(f"嘗試連接 IBKR {self.host}:{self.port}...")
            self.ib.connect(
                host=self.host,
                port=self.port,
                clientId=self.client_id,
                timeout=timeout
            )
            
            if self.ib.isConnected():
                self.connected = True
                self.connection_attempts = 0
                
                # 設置市場數據類型
                # Market data type: 1=Live, 2=Frozen, 3=Delayed, 4=Delayed Frozen
                # 默認使用延遲數據（股票），期權會單獨設置為實時（OPRA）
                self.ib.reqMarketDataType(3)  # 使用延遲數據作為默認
                logger.info(f"* IBKR 連接成功 ({self.mode} mode)")
                logger.info("  已設置為延遲市場數據模式 (Delayed) - 期權將使用 OPRA 實時數據")
                return True
            else:
                logger.error("x IBKR 連接失敗：未連接狀態")
                return False
                
        except Exception as e:
            self.connection_attempts += 1
            self.last_error = str(e)
            logger.warning(f"! IBKR 連接失敗 (嘗試 {self.connection_attempts}/{self.max_connection_attempts}): {e}")
            
            if self.connection_attempts >= self.max_connection_attempts:
                logger.error(f"x IBKR 連接失敗，已達最大重試次數。請檢查 TWS/Gateway 是否運行")
            
            return False
    
    def disconnect(self):
        """斷開連接"""
        if self.connected and self.ib.isConnected():
            try:
                self.ib.disconnect()
                self.connected = False
                logger.info("* IBKR 已斷開連接")
            except Exception as e:
                logger.error(f"x IBKR 斷開連接失敗: {e}")
    
    def is_connected(self) -> bool:
        """檢查是否已連接"""
        if not IB_INSYNC_AVAILABLE:
            return False
        
        try:
            return self.ib.isConnected() if self.ib else False
        except:
            return False
    
    def get_option_chain(self, ticker: str, expiration: str, stock_price: float = 0) -> Optional[Dict[str, Any]]:
        """
        獲取期權鏈數據（只獲取合約信息，不獲取市場數據）
        
        注意：此方法只返回期權合約的基本信息（行使價、到期日等），
        不包含市場數據（bid/ask/last）和 Greeks。
        Greeks 應由本地計算模塊（Black-Scholes）計算。
        
        參數:
            ticker: 股票代碼
            expiration: 到期日期 (YYYY-MM-DD)
            stock_price: 當前股價（用於過濾行使價範圍，可選）
        
        返回:
            dict: 期權鏈數據，失敗返回 None
        """
        if not self.is_connected():
            if not self.connect():
                logger.warning("! IBKR 未連接，無法獲取期權鏈")
                return None
        
        try:
            logger.info(f"開始獲取 {ticker} {expiration} 期權鏈 (IBKR - 僅合約信息)...")
            
            # 創建股票合約
            stock = Stock(ticker, 'SMART', 'USD')
            self.ib.qualifyContracts(stock)
            
            # 獲取期權鏈定義（不需要市場數據訂閱）
            chains = self.ib.reqSecDefOptParams(
                stock.symbol,
                '',
                stock.secType,
                stock.conId
            )
            
            if not chains:
                logger.warning(f"! {ticker} 無可用期權鏈")
                return None
            
            # 找到匹配的到期日
            target_exp_str = expiration.replace('-', '')  # 轉換為 'YYYYMMDD' 格式
            matching_chain = None
            available_expirations = []
            
            for chain in chains:
                for exp_date in chain.expirations:
                    if isinstance(exp_date, str):
                        exp_str = exp_date
                    else:
                        exp_str = exp_date.strftime('%Y%m%d')
                    
                    available_expirations.append(exp_str)
                    
                    if exp_str == target_exp_str:
                        matching_chain = chain
                        break
                if matching_chain:
                    break
            
            if not matching_chain:
                logger.warning(f"! 未找到 {ticker} {expiration} 的期權鏈")
                logger.info(f"  目標到期日: {target_exp_str}")
                logger.info(f"  可用到期日 (前10個): {sorted(set(available_expirations))[:10]}")
                return None
            
            # 構建期權合約列表
            calls = []
            puts = []
            
            # 轉換日期格式: YYYY-MM-DD -> YYYYMMDD
            exp_formatted = expiration.replace('-', '')
            
            # 使用傳入的股價或默認範圍
            current_price = stock_price if stock_price > 0 else 0
            
            # 過濾行使價：只保留接近當前股價的（±30%範圍內）
            if current_price > 0:
                min_strike = current_price * 0.7
                max_strike = current_price * 1.3
                filtered_strikes = [s for s in matching_chain.strikes if min_strike <= s <= max_strike]
                logger.info(f"  過濾行使價: {len(matching_chain.strikes)} -> {len(filtered_strikes)} (股價 ${current_price:.2f})")
            else:
                # 如果無法獲取股價，只取中間的 50 個行使價
                all_strikes = sorted(matching_chain.strikes)
                mid = len(all_strikes) // 2
                filtered_strikes = all_strikes[max(0, mid-25):mid+25]
                logger.info(f"  限制行使價數量: {len(matching_chain.strikes)} -> {len(filtered_strikes)}")
            
            # 使用 reqContractDetails 獲取實際存在的期權合約（不需要市場數據訂閱）
            logger.info(f"  使用 reqContractDetails 獲取期權合約列表...")
            
            option_filter = Option(
                symbol=ticker,
                lastTradeDateOrContractMonth=exp_formatted,
                exchange='SMART',
                currency='USD'
            )
            
            try:
                # 獲取所有匹配的期權合約
                contract_details_list = self.ib.reqContractDetails(option_filter)
                
                if contract_details_list:
                    logger.info(f"  找到 {len(contract_details_list)} 個期權合約")
                    
                    # 過濾行使價範圍，只返回合約基本信息
                    for cd in contract_details_list:
                        contract = cd.contract
                        strike = contract.strike
                        
                        # 只處理在價格範圍內的行使價
                        if current_price > 0:
                            if strike < current_price * 0.7 or strike > current_price * 1.3:
                                continue
                        
                        # 只返回合約基本信息，不獲取市場數據
                        option_data = {
                            'strike': strike,
                            'expiration': expiration,
                            'option_type': contract.right,
                            'conId': contract.conId,
                            'localSymbol': contract.localSymbol,
                            'multiplier': int(contract.multiplier) if contract.multiplier else 100,
                            'data_source': 'ibkr'
                        }
                        
                        if contract.right == 'C':
                            calls.append(option_data)
                        else:
                            puts.append(option_data)
                    
                    # 按行使價排序
                    calls.sort(key=lambda x: x['strike'])
                    puts.sort(key=lambda x: x['strike'])
                    
                    logger.info(f"* 獲取 {ticker} 期權鏈完成: {len(calls)} calls, {len(puts)} puts")
                    
                    return {
                        'calls': calls,
                        'puts': puts,
                        'expiration': expiration,
                        'strikes': sorted(set([c['strike'] for c in calls + puts])),
                        'data_source': 'ibkr'
                    }
                else:
                    logger.warning(f"! reqContractDetails 未返回任何合約")
                    return None
                    
            except Exception as e:
                logger.warning(f"! reqContractDetails 失敗: {e}")
                return None
            
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"x 獲取 {ticker} 期權鏈失敗: {e}")
            return None
    
    def get_option_greeks(self, ticker: str, strike: float, 
                          expiration: str, option_type: str = 'C') -> Optional[Dict[str, float]]:
        """
        獲取期權 Greeks
        
        參數:
            ticker: 股票代碼
            strike: 行使價
            expiration: 到期日期 (YYYY-MM-DD)
            option_type: 'C' (Call) 或 'P' (Put)
        
        返回:
            dict: {'delta': float, 'gamma': float, 'theta': float, 'vega': float, 'rho': float}
        """
        if not self.is_connected():
            if not self.connect():
                logger.warning("! IBKR 未連接，無法獲取 Greeks")
                return None
        
        try:
            logger.info(f"開始獲取 {ticker} {strike} {option_type} Greeks (IBKR)...")
            
            # 轉換日期格式: YYYY-MM-DD -> YYYYMMDD
            exp_formatted = expiration.replace('-', '')
            
            # 創建期權合約
            option = Option(
                symbol=ticker,
                lastTradeDateOrContractMonth=exp_formatted,
                strike=strike,
                right=option_type,
                exchange='SMART',
                currency='USD'
            )
            qualified = self.ib.qualifyContracts(option)
            
            if not qualified:
                logger.warning(f"! 無法驗證期權合約: {ticker} {strike} {option_type}")
                return None
            
            logger.info(f"  期權合約已驗證: {option.localSymbol}, conId={option.conId}")
            
            # 請求期權市場數據 - 使用流式數據
            # genericTickList: 106=Option Implied Volatility
            self.ib.reqMktData(option, '106', False, False)  # snapshot=False
            
            # 等待數據更新
            ticker_data = None
            for _ in range(5):  # 最多等待 5 秒
                time.sleep(1)
                ticker_data = self.ib.ticker(option)
                # 檢查是否有有效的報價數據（不是 NaN）
                if ticker_data:
                    has_bid = ticker_data.bid is not None and not (isinstance(ticker_data.bid, float) and ticker_data.bid != ticker_data.bid)
                    has_ask = ticker_data.ask is not None and not (isinstance(ticker_data.ask, float) and ticker_data.ask != ticker_data.ask)
                    has_last = ticker_data.last is not None and not (isinstance(ticker_data.last, float) and ticker_data.last != ticker_data.last)
                    if has_bid or has_ask or has_last:
                        break
            
            if not ticker_data:
                logger.warning(f"! 無法獲取 {ticker} {strike} 的市場數據")
                return None
            
            # 收集所有可用數據
            result = {}
            
            # 1. 優先使用 IBKR 的 modelGreeks（如果可用）
            if ticker_data.modelGreeks:
                logger.info("  使用 IBKR modelGreeks")
                result = {
                    'delta': ticker_data.modelGreeks.delta,
                    'gamma': ticker_data.modelGreeks.gamma,
                    'theta': ticker_data.modelGreeks.theta,
                    'vega': ticker_data.modelGreeks.vega,
                    'rho': ticker_data.modelGreeks.rho,
                    'impliedVol': ticker_data.modelGreeks.impliedVol,
                    'source': 'ibkr_model'
                }
            
            # 2. 獲取期權報價數據（OPRA 數據）
            try:
                if ticker_data.bid is not None and not (isinstance(ticker_data.bid, float) and ticker_data.bid != ticker_data.bid):
                    result['bid'] = float(ticker_data.bid)
                if ticker_data.ask is not None and not (isinstance(ticker_data.ask, float) and ticker_data.ask != ticker_data.ask):
                    result['ask'] = float(ticker_data.ask)
                if ticker_data.last is not None and not (isinstance(ticker_data.last, float) and ticker_data.last != ticker_data.last):
                    result['last'] = float(ticker_data.last)
                if ticker_data.volume is not None and ticker_data.volume > 0:
                    result['volume'] = int(ticker_data.volume)
            except (ValueError, TypeError) as e:
                logger.debug(f"  處理報價數據時出錯: {e}")
            
            # 3. 嘗試獲取 IV（從不同來源）
            if ticker_data.impliedVolatility and ticker_data.impliedVolatility > 0:
                result['impliedVol'] = float(ticker_data.impliedVolatility)
                result['iv_source'] = 'ibkr_tick'
            
            # 過濾 None 值
            result = {k: v for k, v in result.items() if v is not None}
            
            # 取消市場數據訂閱
            try:
                self.ib.cancelMktData(option)
            except:
                pass
            
            if result:
                logger.info(f"* 獲取期權數據成功: {result}")
                return result
            else:
                logger.warning(f"! 無法獲取期權數據")
                return None
                
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"x 獲取 Greeks 失敗: {e}")
            return None
    
    def get_option_quote(self, ticker: str, strike: float, 
                         expiration: str, option_type: str = 'C') -> Optional[Dict[str, Any]]:
        """
        獲取期權報價數據（使用 OPRA 數據）
        
        這個方法專門獲取期權的基本報價數據，不依賴 modelGreeks。
        適用於只有 OPRA 訂閱的情況。
        
        參數:
            ticker: 股票代碼
            strike: 行使價
            expiration: 到期日期 (YYYY-MM-DD)
            option_type: 'C' (Call) 或 'P' (Put)
        
        返回:
            dict: {'bid': float, 'ask': float, 'last': float, 'volume': int, 'iv': float}
        """
        if not self.is_connected():
            if not self.connect():
                logger.warning("! IBKR 未連接，無法獲取期權報價")
                return None
        
        try:
            logger.info(f"開始獲取 {ticker} {strike} {option_type} 期權報價 (IBKR OPRA)...")
            
            # 轉換日期格式
            exp_formatted = expiration.replace('-', '')
            
            # 創建期權合約
            option = Option(
                symbol=ticker,
                lastTradeDateOrContractMonth=exp_formatted,
                strike=strike,
                right=option_type,
                exchange='SMART',
                currency='USD'
            )
            qualified = self.ib.qualifyContracts(option)
            
            if not qualified:
                logger.warning(f"! 無法驗證期權合約: {ticker} {strike} {option_type}")
                return None
            
            # 請求期權報價 - 使用流式數據（不是快照）
            self.ib.reqMktData(option, '', False, False)  # snapshot=False
            
            # 等待數據
            ticker_data = None
            for _ in range(5):
                time.sleep(1)
                ticker_data = self.ib.ticker(option)
                # 檢查是否有有效的報價數據（不是 NaN）
                if ticker_data:
                    has_bid = ticker_data.bid is not None and not (isinstance(ticker_data.bid, float) and ticker_data.bid != ticker_data.bid)
                    has_ask = ticker_data.ask is not None and not (isinstance(ticker_data.ask, float) and ticker_data.ask != ticker_data.ask)
                    if has_bid or has_ask:
                        break
            
            if not ticker_data:
                return None
            
            result = {
                'strike': strike,
                'expiration': expiration,
                'option_type': option_type,
                'data_source': 'ibkr_opra'
            }
            
            # 收集報價數據 - 處理 NaN 值
            try:
                if ticker_data.bid is not None and not (isinstance(ticker_data.bid, float) and ticker_data.bid != ticker_data.bid):
                    result['bid'] = float(ticker_data.bid)
                if ticker_data.ask is not None and not (isinstance(ticker_data.ask, float) and ticker_data.ask != ticker_data.ask):
                    result['ask'] = float(ticker_data.ask)
                if ticker_data.last is not None and not (isinstance(ticker_data.last, float) and ticker_data.last != ticker_data.last):
                    result['last'] = float(ticker_data.last)
                if ticker_data.volume is not None and ticker_data.volume > 0:
                    result['volume'] = int(ticker_data.volume)
            except (ValueError, TypeError) as e:
                logger.debug(f"  處理報價數據時出錯: {e}")
            
            # 計算中間價
            if 'bid' in result and 'ask' in result:
                result['mid'] = (result['bid'] + result['ask']) / 2
            
            # 取消市場數據訂閱
            self.ib.cancelMktData(option)
            
            logger.info(f"* 獲取期權報價成功: {result}")
            return result
            
        except Exception as e:
            logger.error(f"x 獲取期權報價失敗: {e}")
            return None
    
    def get_bid_ask_spread(self, ticker: str, strike: float, 
                          expiration: str, option_type: str = 'C') -> Optional[float]:
        """
        獲取實時 Bid/Ask 價差
        
        參數:
            ticker: 股票代碼
            strike: 行使價
            expiration: 到期日期
            option_type: 'C' 或 'P'
        
        返回:
            float: 價差（美元），失敗返回 None
        """
        if not self.is_connected():
            if not self.connect():
                return None
        
        try:
            # 轉換日期格式: YYYY-MM-DD -> YYYYMMDD
            exp_formatted = expiration.replace('-', '')
            
            option = Option(ticker, exp_formatted, strike, option_type, 'SMART')
            self.ib.qualifyContracts(option)
            self.ib.reqMktData(option, '', False, False)
            time.sleep(1)
            
            ticker_data = self.ib.ticker(option)
            if ticker_data and ticker_data.bid and ticker_data.ask:
                spread = ticker_data.ask - ticker_data.bid
                logger.info(f"* Bid/Ask 價差: ${spread:.2f}")
                return float(spread)
            else:
                return None
                
        except Exception as e:
            logger.error(f"x 獲取 Bid/Ask 價差失敗: {e}")
            return None
    
    def _get_option_data(self, contract: Contract) -> Optional[Dict[str, Any]]:
        """獲取單個期權合約的市場數據"""
        try:
            self.ib.reqMktData(contract, '', False, False)
            time.sleep(0.5)  # 等待數據
            
            ticker_data = self.ib.ticker(contract)
            if not ticker_data:
                return None
            
            return {
                'strike': contract.strike,
                'expiration': contract.lastTradeDateOrContractMonth,
                'option_type': contract.right,
                'bid': float(ticker_data.bid) if ticker_data.bid else 0.0,
                'ask': float(ticker_data.ask) if ticker_data.ask else 0.0,
                'last': float(ticker_data.last) if ticker_data.last else 0.0,
                'volume': int(ticker_data.volume) if ticker_data.volume else 0,
                'open_interest': int(ticker_data.openInterest) if ticker_data.openInterest else 0,
                'implied_volatility': float(ticker_data.impliedVolatility) * 100 if ticker_data.impliedVolatility else None,  # 轉換為百分比
                'delta': float(ticker_data.modelGreeks.delta) if ticker_data.modelGreeks and ticker_data.modelGreeks.delta else None,
                'gamma': float(ticker_data.modelGreeks.gamma) if ticker_data.modelGreeks and ticker_data.modelGreeks.gamma else None,
                'theta': float(ticker_data.modelGreeks.theta) if ticker_data.modelGreeks and ticker_data.modelGreeks.theta else None,
                'vega': float(ticker_data.modelGreeks.vega) if ticker_data.modelGreeks and ticker_data.modelGreeks.vega else None,
                'data_source': 'ibkr'
            }
        except Exception as e:
            logger.debug(f"獲取期權數據失敗: {e}")
            return None
    
    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.disconnect()


# 使用示例
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # 測試連接
    client = IBKRClient(mode='paper')
    
    if client.connect():
        print("* IBKR 連接成功")
        
        # 測試獲取期權鏈
        chain = client.get_option_chain('AAPL', '2024-12-20')
        if chain:
            print(f"* 獲取期權鏈成功: {len(chain['calls'])} calls")
        
        client.disconnect()
    else:
        print("x IBKR 連接失敗，請確保 TWS 或 IB Gateway 正在運行")

