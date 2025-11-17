#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
測試降級邏輯
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_degradation():
    """測試 DataFetcher 的降級邏輯"""
    print("=" * 80)
    print("測試 DataFetcher 降級邏輯")
    print("=" * 80)
    
    from data_layer.data_fetcher import DataFetcher
    
    # 創建 DataFetcher 實例
    print("\n1. 初始化 DataFetcher...")
    fetcher = DataFetcher()
    print("   ✓ DataFetcher 初始化成功")
    
    # 測試獲取股票信息（可能會遇到速率限制）
    print("\n2. 測試獲取股票信息...")
    ticker = "AAPL"
    
    try:
        stock_info = fetcher.get_stock_info(ticker)
        
        if stock_info:
            print(f"   ✓ 成功獲取 {ticker} 信息")
            print(f"     - 當前價格: ${stock_info.get('current_price', 0):.2f}")
            print(f"     - PE 比率: {stock_info.get('pe_ratio', 0):.2f}")
            print(f"     - EPS: ${stock_info.get('eps', 0):.2f}")
        else:
            print(f"   ⚠ 無法獲取 {ticker} 信息（將使用降級方案）")
    except Exception as e:
        print(f"   ✗ 錯誤: {e}")
    
    # 測試獲取歷史數據
    print("\n3. 測試獲取歷史數據...")
    try:
        hist = fetcher.get_historical_data(ticker, period='5d', interval='1d')
        
        if hist is not None and not hist.empty:
            print(f"   ✓ 成功獲取 {ticker} 歷史數據")
            print(f"     - 數據點數: {len(hist)}")
            print(f"     - 最新收盤價: ${hist['Close'].iloc[-1]:.2f}")
        else:
            print(f"   ⚠ 無法獲取 {ticker} 歷史數據")
    except Exception as e:
        print(f"   ✗ 錯誤: {e}")
    
    # 測試完整分析數據獲取（使用降級邏輯）
    print("\n4. 測試完整分析數據獲取（帶降級）...")
    try:
        analysis_data = fetcher.get_complete_analysis_data(ticker, expiration='2025-12-26')
        
        if analysis_data:
            print(f"   ✓ 成功獲取完整分析數據")
            print(f"     - 當前價格: ${analysis_data.get('current_price', 0):.2f}")
            print(f"     - 隱含波動率: {analysis_data.get('implied_volatility', 0)*100:.2f}%")
            print(f"     - 到期天數: {analysis_data.get('days_to_expiration', 0)}")
        else:
            print(f"   ✗ 無法獲取完整分析數據")
    except Exception as e:
        print(f"   ✗ 錯誤: {e}")
    
    print("\n" + "=" * 80)
    print("測試完成")
    print("=" * 80)

if __name__ == "__main__":
    test_degradation()
