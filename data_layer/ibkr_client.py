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
    logger.warning("⚠ ib_insync 未安裝，IBKR 功能將不可用。安裝: pip install ib_insync")


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
            logger.error("✗ ib_insync 未安裝，無法連接 IBKR")
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
                logger.info(f"✓ IBKR 連接成功 ({self.mode} mode)")
                return True
            else:
                logger.error("✗ IBKR 連接失敗：未連接狀態")
                return False
                
        except Exception as e:
            self.connection_attempts += 1
            self.last_error = str(e)
            logger.warning(f"⚠ IBKR 連接失敗 (嘗試 {self.connection_attempts}/{self.max_connection_attempts}): {e}")
            
            if self.connection_attempts >= self.max_connection_attempts:
                logger.error(f"✗ IBKR 連接失敗，已達最大重試次數。請檢查 TWS/Gateway 是否運行")
            
            return False
    
    def disconnect(self):
        """斷開連接"""
        if self.connected and self.ib.isConnected():
            try:
                self.ib.disconnect()
                self.connected = False
                logger.info("✓ IBKR 已斷開連接")
            except Exception as e:
                logger.error(f"✗ IBKR 斷開連接失敗: {e}")
    
    def is_connected(self) -> bool:
        """檢查是否已連接"""
        if not IB_INSYNC_AVAILABLE:
            return False
        
        try:
            return self.ib.isConnected() if self.ib else False
        except:
            return False
    
    def get_option_chain(self, ticker: str, expiration: str) -> Optional[Dict[str, Any]]:
        """
        獲取期權鏈數據
        
        參數:
            ticker: 股票代碼
            expiration: 到期日期 (YYYY-MM-DD)
        
        返回:
            dict: 期權鏈數據，失敗返回 None
        """
        if not self.is_connected():
            if not self.connect():
                logger.warning("⚠ IBKR 未連接，無法獲取期權鏈")
                return None
        
        try:
            logger.info(f"開始獲取 {ticker} {expiration} 期權鏈 (IBKR)...")
            
            # 創建股票合約
            stock = Stock(ticker, 'SMART', 'USD')
            self.ib.qualifyContracts(stock)
            
            # 獲取期權鏈
            chains = self.ib.reqSecDefOptParams(
                stock.symbol,
                '',
                stock.secType,
                stock.conId
            )
            
            if not chains:
                logger.warning(f"⚠ {ticker} 無可用期權鏈")
                return None
            
            # 找到匹配的到期日
            target_exp = datetime.strptime(expiration, '%Y-%m-%d').date()
            matching_chain = None
            
            for chain in chains:
                for exp_date in chain.expirations:
                    if exp_date == target_exp:
                        matching_chain = chain
                        break
                if matching_chain:
                    break
            
            if not matching_chain:
                logger.warning(f"⚠ 未找到 {ticker} {expiration} 的期權鏈")
                return None
            
            # 構建期權合約列表
            calls = []
            puts = []
            
            for strike in matching_chain.strikes:
                # Call 期權
                call_contract = Option(
                    ticker, 
                    expiration, 
                    strike, 
                    'C', 
                    'SMART'
                )
                self.ib.qualifyContracts(call_contract)
                
                if call_contract:
                    call_data = self._get_option_data(call_contract)
                    if call_data:
                        calls.append(call_data)
                
                # Put 期權
                put_contract = Option(
                    ticker, 
                    expiration, 
                    strike, 
                    'P', 
                    'SMART'
                )
                self.ib.qualifyContracts(put_contract)
                
                if put_contract:
                    put_data = self._get_option_data(put_contract)
                    if put_data:
                        puts.append(put_data)
            
            logger.info(f"✓ 獲取 {ticker} 期權鏈成功: {len(calls)} calls, {len(puts)} puts")
            
            return {
                'calls': calls,
                'puts': puts,
                'expiration': expiration,
                'data_source': 'ibkr'
            }
            
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"✗ 獲取 {ticker} 期權鏈失敗: {e}")
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
                logger.warning("⚠ IBKR 未連接，無法獲取 Greeks")
                return None
        
        try:
            logger.info(f"開始獲取 {ticker} {strike} {option_type} Greeks (IBKR)...")
            
            # 創建期權合約
            option = Option(ticker, expiration, strike, option_type, 'SMART')
            self.ib.qualifyContracts(option)
            
            # 訂閱市場數據
            self.ib.reqMktData(option, '', False, False)
            time.sleep(1)  # 等待數據更新
            
            # 獲取 Greeks
            ticker_data = self.ib.ticker(option)
            
            if not ticker_data:
                logger.warning(f"⚠ 無法獲取 {ticker} {strike} 的市場數據")
                return None
            
            greeks = {
                'delta': ticker_data.modelGreeks.delta if ticker_data.modelGreeks else None,
                'gamma': ticker_data.modelGreeks.gamma if ticker_data.modelGreeks else None,
                'theta': ticker_data.modelGreeks.theta if ticker_data.modelGreeks else None,
                'vega': ticker_data.modelGreeks.vega if ticker_data.modelGreeks else None,
                'rho': ticker_data.modelGreeks.rho if ticker_data.modelGreeks else None
            }
            
            # 過濾 None 值
            greeks = {k: v for k, v in greeks.items() if v is not None}
            
            if greeks:
                logger.info(f"✓ 獲取 Greeks 成功: {greeks}")
                return greeks
            else:
                logger.warning(f"⚠ 無法獲取完整的 Greeks 數據")
                return None
                
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"✗ 獲取 Greeks 失敗: {e}")
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
            option = Option(ticker, expiration, strike, option_type, 'SMART')
            self.ib.qualifyContracts(option)
            self.ib.reqMktData(option, '', False, False)
            time.sleep(1)
            
            ticker_data = self.ib.ticker(option)
            if ticker_data and ticker_data.bid and ticker_data.ask:
                spread = ticker_data.ask - ticker_data.bid
                logger.info(f"✓ Bid/Ask 價差: ${spread:.2f}")
                return float(spread)
            else:
                return None
                
        except Exception as e:
            logger.error(f"✗ 獲取 Bid/Ask 價差失敗: {e}")
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
        print("✓ IBKR 連接成功")
        
        # 測試獲取期權鏈
        chain = client.get_option_chain('AAPL', '2024-12-20')
        if chain:
            print(f"✓ 獲取期權鏈成功: {len(chain['calls'])} calls")
        
        client.disconnect()
    else:
        print("✗ IBKR 連接失敗，請確保 TWS 或 IB Gateway 正在運行")

