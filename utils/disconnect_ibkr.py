#!/usr/bin/env python3
"""
強制斷開所有 IBKR Gateway 連接的工具腳本

用途：當 IBKR Gateway 連接槽被佔用時，使用此腳本清理連接
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ib_insync import IB
import time

def disconnect_all_ibkr_connections():
    """嘗試斷開所有可能的 IBKR 連接"""
    
    # 嘗試的客戶端 ID 列表（常見的 ID）
    client_ids = [0, 1, 2, 3, 4, 5, 10, 100, 999]
    
    # 嘗試的端口列表
    ports = [4002, 7497]  # 4002=Gateway paper, 7497=TWS paper
    
    disconnected_count = 0
    
    for port in ports:
        for client_id in client_ids:
            try:
                print(f"嘗試斷開 port={port}, clientId={client_id}...", end=" ")
                
                ib = IB()
                ib.connect('127.0.0.1', port, clientId=client_id, timeout=2)
                
                if ib.isConnected():
                    ib.disconnect()
                    disconnected_count += 1
                    print(f"✓ 已斷開")
                else:
                    print("- 未連接")
                    
            except Exception as e:
                # 連接失敗是正常的（說明該 ID 沒有被佔用）
                print(f"- {type(e).__name__}")
                pass
            
            time.sleep(0.1)  # 短暫延遲避免過快請求
    
    print(f"\n總共斷開了 {disconnected_count} 個連接")
    
    if disconnected_count == 0:
        print("沒有發現活動的 IBKR 連接")
    else:
        print(f"已清理 {disconnected_count} 個連接，現在可以重新連接了")

if __name__ == "__main__":
    print("="*60)
    print("IBKR Gateway 連接清理工具")
    print("="*60)
    print()
    
    disconnect_all_ibkr_connections()
    
    print()
    print("="*60)
    print("完成")
    print("="*60)
