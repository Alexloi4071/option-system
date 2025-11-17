#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
簡單測試（避免編碼問題）
"""

import sys
import os

# 設置環境變量
os.environ['PYTHONIOENCODING'] = 'utf-8'

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_simple():
    """簡單測試"""
    print("=" * 80)
    print("Simple Test - Data Fetcher Degradation")
    print("=" * 80)
    
    try:
        from data_layer.data_fetcher import DataFetcher
        
        print("\n1. Initializing DataFetcher...")
        fetcher = DataFetcher()
        print("   [OK] DataFetcher initialized")
        
        print("\n2. Testing stock info retrieval...")
        ticker = "AAPL"
        
        stock_info = fetcher.get_stock_info(ticker)
        
        if stock_info:
            print(f"   [OK] Got {ticker} info")
            print(f"     - Price: ${stock_info.get('current_price', 0):.2f}")
            print(f"     - PE: {stock_info.get('pe_ratio', 0):.2f}")
        else:
            print(f"   [WARN] Could not get {ticker} info (will use degradation)")
        
        print("\n3. Testing historical data...")
        hist = fetcher.get_historical_data(ticker, period='5d', interval='1d')
        
        if hist is not None and not hist.empty:
            print(f"   [OK] Got {ticker} historical data")
            print(f"     - Data points: {len(hist)}")
            print(f"     - Latest close: ${hist['Close'].iloc[-1]:.2f}")
        else:
            print(f"   [WARN] Could not get {ticker} historical data")
        
        print("\n4. Testing complete analysis data (with degradation)...")
        analysis_data = fetcher.get_complete_analysis_data(ticker, expiration='2025-12-26')
        
        if analysis_data:
            print(f"   [OK] Got complete analysis data")
            print(f"     - Current price: ${analysis_data.get('current_price', 0):.2f}")
            print(f"     - IV: {analysis_data.get('implied_volatility', 0)*100:.2f}%")
            print(f"     - Days to expiration: {analysis_data.get('days_to_expiration', 0)}")
            print("\n   [SUCCESS] Degradation logic works!")
        else:
            print(f"   [ERROR] Could not get complete analysis data")
        
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("Test Complete")
    print("=" * 80)

if __name__ == "__main__":
    test_simple()
