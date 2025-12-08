"""
IBKR 市場數據訂閱測試腳本
檢查可用的市場數據和期權數據獲取能力
"""

import logging
import time
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from ib_insync import IB, Stock, Option, util
    print("✓ ib_insync 已安裝")
except ImportError:
    print("✗ ib_insync 未安裝，請運行: pip install ib_insync")
    exit(1)


def test_ibkr_connection():
    """測試 IBKR 連接和市場數據"""
    ib = IB()
    
    try:
        # 連接到 TWS
        print("\n" + "="*60)
        print("步驟 1: 連接到 TWS")
        print("="*60)
        
        ib.connect('127.0.0.1', 7497, clientId=999)
        
        if ib.isConnected():
            print("✓ 已連接到 TWS")
            
            # 獲取帳戶信息
            accounts = ib.managedAccounts()
            print(f"  帳戶: {accounts}")
        else:
            print("✗ 連接失敗")
            return
        
        # 測試不同的市場數據類型
        print("\n" + "="*60)
        print("步驟 2: 測試市場數據類型")
        print("="*60)
        
        # 創建 QQQ 股票合約
        stock = Stock('QQQ', 'SMART', 'USD')
        ib.qualifyContracts(stock)
        print(f"✓ QQQ 股票合約: conId={stock.conId}")
        
        # 測試實時數據 (Type 1)
        print("\n--- 測試實時數據 (Type 1) ---")
        ib.reqMarketDataType(1)
        ticker = ib.reqMktData(stock, '', False, False)
        time.sleep(2)
        
        print(f"  Last: {ticker.last}")
        print(f"  Bid: {ticker.bid}")
        print(f"  Ask: {ticker.ask}")
        print(f"  Close: {ticker.close}")
        print(f"  Volume: {ticker.volume}")
        
        ib.cancelMktData(stock)
        
        # 測試延遲數據 (Type 3)
        print("\n--- 測試延遲數據 (Type 3) ---")
        ib.reqMarketDataType(3)
        ticker = ib.reqMktData(stock, '', False, False)
        time.sleep(2)
        
        print(f"  Last: {ticker.last}")
        print(f"  Bid: {ticker.bid}")
        print(f"  Ask: {ticker.ask}")
        print(f"  Close: {ticker.close}")
        
        ib.cancelMktData(stock)
        
        # 獲取期權鏈
        print("\n" + "="*60)
        print("步驟 3: 獲取 QQQ 期權鏈")
        print("="*60)
        
        chains = ib.reqSecDefOptParams(stock.symbol, '', stock.secType, stock.conId)
        
        if chains:
            print(f"✓ 找到 {len(chains)} 個期權鏈")
            
            for i, chain in enumerate(chains):
                print(f"\n  鏈 {i+1}:")
                print(f"    交易所: {chain.exchange}")
                print(f"    到期日數量: {len(chain.expirations)}")
                print(f"    行權價數量: {len(chain.strikes)}")
                print(f"    前5個到期日: {sorted(chain.expirations)[:5]}")
                
                # 只顯示第一個鏈的詳細信息
                if i == 0:
                    # 找到最近的到期日
                    sorted_exp = sorted(chain.expirations)
                    if sorted_exp:
                        nearest_exp = sorted_exp[0]
                        print(f"\n    最近到期日: {nearest_exp}")
                        
                        # 找到接近當前價格的行權價
                        current_price = ticker.last or ticker.close or 500
                        nearby_strikes = [s for s in chain.strikes if abs(s - current_price) < 20]
                        print(f"    接近當前價格的行權價 (±$20): {sorted(nearby_strikes)[:10]}")
        else:
            print("✗ 無法獲取期權鏈")
        
        # 測試獲取單個期權合約
        print("\n" + "="*60)
        print("步驟 4: 測試獲取單個 QQQ 期權數據")
        print("="*60)
        
        # 使用 2026-01-16 到期日
        exp_date = '20260116'
        
        # 先獲取可用的行權價
        if chains:
            chain = chains[0]
            current_price = ticker.last or ticker.close or 500
            
            # 找到最接近當前價格的行權價
            closest_strike = min(chain.strikes, key=lambda x: abs(x - current_price))
            print(f"\n當前 QQQ 價格: ${current_price:.2f}")
            print(f"選擇行權價: ${closest_strike}")
            
            # 測試 Call 期權
            print(f"\n--- 測試 Call 期權 (Strike={closest_strike}, Exp={exp_date}) ---")
            
            call_option = Option('QQQ', exp_date, closest_strike, 'C', 'SMART')
            qualified = ib.qualifyContracts(call_option)
            
            if qualified and call_option.conId:
                print(f"✓ 期權合約已驗證: {call_option.localSymbol}, conId={call_option.conId}")
                
                # 請求市場數據
                ib.reqMarketDataType(1)  # 嘗試實時數據
                opt_ticker = ib.reqMktData(call_option, '106', False, False)
                
                print("  等待數據...")
                for i in range(5):
                    time.sleep(1)
                    print(f"  {i+1}秒: bid={opt_ticker.bid}, ask={opt_ticker.ask}, last={opt_ticker.last}")
                    
                    # 檢查是否有數據
                    if opt_ticker.bid and opt_ticker.bid > 0:
                        break
                
                print(f"\n  期權數據:")
                print(f"    Bid: {opt_ticker.bid}")
                print(f"    Ask: {opt_ticker.ask}")
                print(f"    Last: {opt_ticker.last}")
                print(f"    Volume: {opt_ticker.volume}")
                print(f"    Open Interest: {opt_ticker.openInterest}")
                print(f"    IV: {opt_ticker.impliedVolatility}")
                
                if opt_ticker.modelGreeks:
                    print(f"\n  Greeks (modelGreeks):")
                    print(f"    Delta: {opt_ticker.modelGreeks.delta}")
                    print(f"    Gamma: {opt_ticker.modelGreeks.gamma}")
                    print(f"    Theta: {opt_ticker.modelGreeks.theta}")
                    print(f"    Vega: {opt_ticker.modelGreeks.vega}")
                    print(f"    IV: {opt_ticker.modelGreeks.impliedVol}")
                else:
                    print("\n  ✗ modelGreeks 不可用")
                
                ib.cancelMktData(call_option)
            else:
                print(f"✗ 無法驗證期權合約")
        
        # 檢查錯誤消息
        print("\n" + "="*60)
        print("步驟 5: 檢查錯誤和警告")
        print("="*60)
        
        # 等待一下看是否有錯誤
        time.sleep(2)
        
        print("\n測試完成!")
        
    except Exception as e:
        print(f"✗ 錯誤: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if ib.isConnected():
            ib.disconnect()
            print("\n已斷開 TWS 連接")


if __name__ == "__main__":
    test_ibkr_connection()
