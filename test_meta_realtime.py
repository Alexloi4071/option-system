"""
測試 META 實時數據
"""

import logging
import time
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

from ib_insync import IB, Stock, Option

def test_meta():
    ib = IB()
    
    try:
        print("="*60)
        print(f"測試時間: {datetime.now()}")
        print("今天是星期日，美股休市")
        print("="*60)
        
        ib.connect('127.0.0.1', 7497, clientId=997)
        print("✓ 已連接到 TWS")
        
        # 測試 META 股票
        print("\n--- 測試 META 股票數據 ---")
        stock = Stock('META', 'SMART', 'USD')
        ib.qualifyContracts(stock)
        print(f"✓ META 合約: conId={stock.conId}")
        
        # 測試所有數據類型
        for data_type in [1, 2, 3, 4]:
            type_names = {1: "Live", 2: "Frozen", 3: "Delayed", 4: "Delayed Frozen"}
            print(f"\n  Type {data_type} ({type_names[data_type]}):")
            
            ib.reqMarketDataType(data_type)
            ticker = ib.reqMktData(stock, '', False, False)
            time.sleep(2)
            
            # 檢查 nan
            def safe_val(v):
                if v is None:
                    return "None"
                if isinstance(v, float) and v != v:  # NaN check
                    return "nan"
                return f"{v:.2f}" if isinstance(v, float) else str(v)
            
            print(f"    Last: {safe_val(ticker.last)}, Bid: {safe_val(ticker.bid)}, Ask: {safe_val(ticker.ask)}, Close: {safe_val(ticker.close)}")
            ib.cancelMktData(stock)
        
        # 測試 META 期權
        print("\n--- 測試 META 期權數據 ---")
        
        # 獲取期權鏈
        chains = ib.reqSecDefOptParams('META', '', 'STK', stock.conId)
        
        if chains:
            # 找到 SMART 鏈
            for chain in chains:
                if chain.exchange == 'SMART':
                    print(f"✓ 找到 SMART 期權鏈")
                    print(f"  到期日數量: {len(chain.expirations)}")
                    print(f"  行權價數量: {len(chain.strikes)}")
                    
                    # 檢查 2026-01-16
                    if '20260116' in chain.expirations:
                        print(f"  ✓ 2026-01-16 到期日存在")
                    else:
                        print(f"  ✗ 2026-01-16 不存在")
                        print(f"  可用到期日: {sorted(chain.expirations)[:10]}")
                    
                    # 選擇一個行權價測試
                    sorted_strikes = sorted(chain.strikes)
                    # 找接近 $570 的行權價 (META 當前價格約 $570)
                    test_strike = min(sorted_strikes, key=lambda x: abs(x - 570))
                    print(f"\n  測試行權價: ${test_strike}")
                    
                    # 創建期權合約
                    exp_date = '20260116' if '20260116' in chain.expirations else sorted(chain.expirations)[0]
                    call = Option('META', exp_date, test_strike, 'C', 'SMART')
                    qualified = ib.qualifyContracts(call)
                    
                    if qualified and call.conId:
                        print(f"  ✓ 期權合約: {call.localSymbol}, conId={call.conId}")
                        
                        # 測試不同數據類型
                        for data_type in [1, 2, 3, 4]:
                            type_names = {1: "Live", 2: "Frozen", 3: "Delayed", 4: "Delayed Frozen"}
                            print(f"\n    Type {data_type} ({type_names[data_type]}):")
                            
                            ib.reqMarketDataType(data_type)
                            opt_ticker = ib.reqMktData(call, '106', False, False)
                            time.sleep(3)
                            
                            print(f"      Bid: {safe_val(opt_ticker.bid)}, Ask: {safe_val(opt_ticker.ask)}, Last: {safe_val(opt_ticker.last)}")
                            print(f"      IV: {safe_val(opt_ticker.impliedVolatility)}")
                            
                            if opt_ticker.modelGreeks:
                                print(f"      Delta: {safe_val(opt_ticker.modelGreeks.delta)}")
                            else:
                                print(f"      Greeks: 不可用")
                            
                            ib.cancelMktData(call)
                    break
        
        print("\n" + "="*60)
        print("結論:")
        print("="*60)
        print("""
1. 今天是星期日，美股休市，所以實時數據不可用
2. OPRA 訂閱通常需要 24 小時才能生效
3. 建議明天（星期一）美股開盤後再測試

如果明天測試仍然是 nan，請檢查：
- IBKR Account Management -> Market Data Subscriptions
- 確認 OPRA 狀態是 "Active"
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
    test_meta()
