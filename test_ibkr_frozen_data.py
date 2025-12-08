"""
IBKR 凍結數據測試 - 用於休市時間
"""

import logging
import time
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from ib_insync import IB, Stock, Option, util

def test_frozen_data():
    """測試凍結數據（休市時可用）"""
    ib = IB()
    
    try:
        print("\n" + "="*60)
        print("IBKR 凍結數據測試 (適用於休市時間)")
        print("="*60)
        
        # 連接
        ib.connect('127.0.0.1', 7497, clientId=998)
        print("✓ 已連接到 TWS")
        
        # 創建 QQQ 股票合約
        stock = Stock('QQQ', 'SMART', 'USD')
        ib.qualifyContracts(stock)
        
        # 測試不同的市場數據類型
        data_types = {
            1: "Live (實時)",
            2: "Frozen (凍結 - 休市時的最後價格)",
            3: "Delayed (延遲 15分鐘)",
            4: "Delayed Frozen (延遲凍結)"
        }
        
        for data_type, desc in data_types.items():
            print(f"\n--- 測試 Type {data_type}: {desc} ---")
            ib.reqMarketDataType(data_type)
            
            ticker = ib.reqMktData(stock, '', False, False)
            time.sleep(3)
            
            # 檢查數據
            last = ticker.last if ticker.last == ticker.last else "N/A"
            bid = ticker.bid if ticker.bid == ticker.bid else "N/A"
            ask = ticker.ask if ticker.ask == ticker.ask else "N/A"
            close = ticker.close if ticker.close == ticker.close else "N/A"
            
            print(f"  Last: {last}")
            print(f"  Bid: {bid}")
            print(f"  Ask: {ask}")
            print(f"  Close: {close}")
            
            ib.cancelMktData(stock)
        
        # 測試期權數據
        print("\n" + "="*60)
        print("測試期權數據 (使用 Frozen 類型)")
        print("="*60)
        
        # 使用 Frozen 數據
        ib.reqMarketDataType(2)
        
        # 獲取期權鏈找到有效的行權價
        chains = ib.reqSecDefOptParams(stock.symbol, '', stock.secType, stock.conId)
        
        if chains:
            # 找到 SMART 交易所的鏈
            smart_chain = None
            for chain in chains:
                if chain.exchange == 'SMART' and len(chain.strikes) > 100:
                    smart_chain = chain
                    break
            
            if smart_chain:
                print(f"\n使用 SMART 交易所期權鏈")
                print(f"  到期日: {sorted(smart_chain.expirations)[:5]}")
                
                # 選擇一個中間的行權價
                sorted_strikes = sorted(smart_chain.strikes)
                mid_idx = len(sorted_strikes) // 2
                test_strike = sorted_strikes[mid_idx]
                
                print(f"  測試行權價: ${test_strike}")
                
                # 測試 2026-01-16 到期的期權
                exp_date = '20260116'
                
                # 檢查這個到期日是否存在
                if exp_date in smart_chain.expirations:
                    print(f"  ✓ 到期日 {exp_date} 存在")
                else:
                    print(f"  ✗ 到期日 {exp_date} 不存在")
                    print(f"  可用到期日: {sorted(smart_chain.expirations)[:10]}")
                    # 使用最近的到期日
                    exp_date = sorted(smart_chain.expirations)[0]
                    print(f"  使用替代到期日: {exp_date}")
                
                # 創建期權合約
                call_option = Option('QQQ', exp_date, test_strike, 'C', 'SMART')
                qualified = ib.qualifyContracts(call_option)
                
                if qualified and call_option.conId:
                    print(f"\n✓ 期權合約: {call_option.localSymbol}")
                    
                    # 請求數據
                    opt_ticker = ib.reqMktData(call_option, '106', False, False)
                    
                    print("  等待數據 (最多10秒)...")
                    for i in range(10):
                        time.sleep(1)
                        
                        # 檢查是否有數據
                        bid = opt_ticker.bid if opt_ticker.bid == opt_ticker.bid else None
                        ask = opt_ticker.ask if opt_ticker.ask == opt_ticker.ask else None
                        last = opt_ticker.last if opt_ticker.last == opt_ticker.last else None
                        
                        if bid or ask or last:
                            print(f"  {i+1}秒: 收到數據!")
                            break
                        else:
                            print(f"  {i+1}秒: 等待中...")
                    
                    # 顯示結果
                    print(f"\n  期權報價:")
                    print(f"    Bid: {opt_ticker.bid}")
                    print(f"    Ask: {opt_ticker.ask}")
                    print(f"    Last: {opt_ticker.last}")
                    print(f"    Volume: {opt_ticker.volume}")
                    print(f"    IV: {opt_ticker.impliedVolatility}")
                    
                    if opt_ticker.modelGreeks:
                        print(f"\n  Greeks:")
                        print(f"    Delta: {opt_ticker.modelGreeks.delta}")
                        print(f"    Gamma: {opt_ticker.modelGreeks.gamma}")
                        print(f"    Theta: {opt_ticker.modelGreeks.theta}")
                        print(f"    Vega: {opt_ticker.modelGreeks.vega}")
                    
                    ib.cancelMktData(call_option)
        
        print("\n" + "="*60)
        print("結論")
        print("="*60)
        print("""
如果所有數據都是 nan，可能的原因：
1. 現在是美股休市時間（週末或假日）
2. 需要等待市場開盤才能獲取實時數據
3. Frozen 數據在某些情況下也可能不可用

建議：
- 在美股交易時間（美東 9:30 AM - 4:00 PM）再次測試
- 或者使用 Yahoo Finance 作為備用數據源
""")
        
    except Exception as e:
        print(f"✗ 錯誤: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if ib.isConnected():
            ib.disconnect()
            print("\n已斷開連接")


if __name__ == "__main__":
    test_frozen_data()
