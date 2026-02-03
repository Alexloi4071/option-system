#!/usr/bin/env python3
"""
測試 IBKR 連接和期權數據獲取
"""

import sys
sys.path.append('.')

from config.settings import settings
from data_layer.ibkr_client import IBKRClient

def test_ibkr_connection():
    print("=== IBKR 連接測試 ===")
    print(f"IBKR_ENABLED: {settings.IBKR_ENABLED}")
    print(f"IBKR_USE_PAPER: {settings.IBKR_USE_PAPER}")
    print(f"IBKR_HOST: {settings.IBKR_HOST}")
    print(f"IBKR_PORT_PAPER: {settings.IBKR_PORT_PAPER}")
    print(f"IBKR_CLIENT_ID: {settings.IBKR_CLIENT_ID}")
    
    # 選擇端口
    port = settings.IBKR_PORT_PAPER if settings.IBKR_USE_PAPER else settings.IBKR_PORT_LIVE
    mode = 'paper' if port == settings.IBKR_PORT_PAPER else 'live'
    
    print(f"\n選擇的端口: {port}")
    print(f"模式: {mode}")
    
    print("\n嘗試連接 IBKR...")
    
    try:
        client = IBKRClient(
            host=settings.IBKR_HOST,
            port=port,
            client_id=settings.IBKR_CLIENT_ID,
            mode=mode
        )
        
        if client.connect(timeout=15):
            print("✓ IBKR 連接成功!")
            
            # 測試獲取 MSFT 期權數據
            ticker = 'MSFT'
            expiration = '2026-02-02'
            print(f"\n測試獲取 {ticker} 期權數據 (到期日: {expiration})...")
            
            # 測試 0: 獲取期權鏈結構
            print(f"\n--- 測試 0: 獲取期權鏈結構 ---")
            chain = client.get_option_chain(ticker, expiration)
            if chain and chain['calls']:
                print(f"✓ 獲取期權鏈成功: {len(chain['calls'])} calls, {len(chain['puts'])} puts")
                # 選擇一個 ATM 附近的行使價進行後續測試
                # 這裡簡單取中間的一個
                test_call = chain['calls'][len(chain['calls'])//2]
                strike = test_call['strike']
                print(f"  選擇測試行使價: {strike}")
                
                # 測試 1: 獲取期權報價 (OPRA 數據)
                print(f"\n--- 測試 1: 獲取期權報價 (OPRA) ---")
                quote = client.get_option_quote(ticker, strike, expiration, 'C')
                if quote:
                    print(f"✓ 獲取期權報價成功:")
                    for k, v in quote.items():
                        print(f"  {k}: {v}")
                else:
                    print("✗ 獲取期權報價失敗")
                
                # 測試 2: 獲取 Greeks
                print(f"\n--- 測試 2: 獲取 Greeks ---")
                greeks = client.get_option_greeks(ticker, strike, expiration, 'C')
                if greeks:
                    print(f"✓ 獲取 Greeks 成功:")
                    for k, v in greeks.items():
                        print(f"  {k}: {v}")
                else:
                    print("✗ 獲取 Greeks 失敗 (可能需要額外訂閱)")
                
                # 測試 3: 獲取 Bid/Ask 價差
                print(f"\n--- 測試 3: 獲取 Bid/Ask 價差 ---")
                spread = client.get_bid_ask_spread(ticker, strike, expiration, 'C')
                if spread is not None:
                    print(f"✓ Bid/Ask 價差: ${spread:.2f}")
                else:
                    print("✗ 獲取 Bid/Ask 失敗")
            else:
                print(f"✗ 無法獲取期權鏈結構，跳過後續測試。請檢查代碼或到期日是否正確。")
            
            client.disconnect()
            print("\n✓ 測試完成，已斷開連接")
        else:
            print("✗ IBKR 連接失敗")
            print(f"  錯誤: {client.last_error}")
            
    except Exception as e:
        print(f"✗ 測試失敗: {e}")

if __name__ == "__main__":
    test_ibkr_connection()
