#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API 連接測試腳本
測試所有數據源的連接狀態
"""

import os
import sys
import time
from datetime import datetime

# 添加項目路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 載入環境變量
from dotenv import load_dotenv
load_dotenv()

print("=" * 70)
print("API 連接測試")
print(f"測試時間: {datetime.now()}")
print("=" * 70)

# 測試股票代碼
TEST_TICKER = "AAPL"

def test_finnhub():
    """測試 Finnhub API"""
    print("\n[1] 測試 Finnhub API...")
    api_key = os.getenv('FINNHUB_API_KEY')
    
    if not api_key:
        print("   ❌ FINNHUB_API_KEY 未設置")
        return False
    
    print(f"   API Key: {api_key[:8]}...{api_key[-4:]}")
    
    try:
        import finnhub
        client = finnhub.Client(api_key=api_key)
        
        # 測試獲取報價
        quote = client.quote(TEST_TICKER)
        
        if quote and quote.get('c', 0) > 0:
            print(f"   ✅ Finnhub 連接成功!")
            print(f"   {TEST_TICKER} 當前價格: ${quote['c']:.2f}")
            print(f"   開盤: ${quote['o']:.2f}, 最高: ${quote['h']:.2f}, 最低: ${quote['l']:.2f}")
            return True
        else:
            print(f"   ❌ Finnhub 返回無效數據: {quote}")
            return False
            
    except Exception as e:
        print(f"   ❌ Finnhub 錯誤: {e}")
        return False

def test_alpha_vantage():
    """測試 Alpha Vantage API"""
    print("\n[2] 測試 Alpha Vantage API...")
    api_key = os.getenv('ALPHA_VANTAGE_API_KEY')
    
    if not api_key:
        print("   ❌ ALPHA_VANTAGE_API_KEY 未設置")
        return False
    
    print(f"   API Key: {api_key[:4]}...{api_key[-4:]}")
    
    try:
        import requests
        url = "https://www.alphavantage.co/query"
        params = {
            'function': 'GLOBAL_QUOTE',
            'symbol': TEST_TICKER,
            'apikey': api_key
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if 'Global Quote' in data and data['Global Quote']:
            quote = data['Global Quote']
            price = float(quote.get('05. price', 0))
            print(f"   ✅ Alpha Vantage 連接成功!")
            print(f"   {TEST_TICKER} 當前價格: ${price:.2f}")
            return True
        elif 'Information' in data:
            print(f"   ⚠️ Alpha Vantage 限制: {data['Information'][:80]}...")
            return False
        elif 'Note' in data:
            print(f"   ⚠️ Alpha Vantage 限制: {data['Note'][:80]}...")
            return False
        else:
            print(f"   ❌ Alpha Vantage 返回無效數據: {data}")
            return False
            
    except Exception as e:
        print(f"   ❌ Alpha Vantage 錯誤: {e}")
        return False

def test_fred():
    """測試 FRED API"""
    print("\n[3] 測試 FRED API...")
    api_key = os.getenv('FRED_API_KEY')
    
    if not api_key:
        print("   ❌ FRED_API_KEY 未設置")
        return False
    
    print(f"   API Key: {api_key[:8]}...{api_key[-4:]}")
    
    try:
        from fredapi import Fred
        fred = Fred(api_key=api_key)
        
        # 獲取 10 年期國債收益率
        rate = fred.get_series_latest_release('DGS10')
        
        if rate is not None and len(rate) > 0:
            latest_rate = rate.iloc[-1]
            print(f"   ✅ FRED 連接成功!")
            print(f"   10年期國債收益率: {latest_rate:.2f}%")
            return True
        else:
            print("   ❌ FRED 返回無效數據")
            return False
            
    except Exception as e:
        print(f"   ❌ FRED 錯誤: {e}")
        return False

def test_yahoo_finance():
    """測試 Yahoo Finance API"""
    print("\n[4] 測試 Yahoo Finance API...")
    
    try:
        import requests
        
        # 測試 Yahoo Finance V2 API
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{TEST_TICKER}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        params = {'interval': '1d', 'range': '1d'}
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        data = response.json()
        
        if response.status_code == 200 and 'chart' in data:
            result = data['chart']['result']
            if result and len(result) > 0:
                meta = result[0].get('meta', {})
                price = meta.get('regularMarketPrice', 0)
                print(f"   ✅ Yahoo Finance 連接成功!")
                print(f"   {TEST_TICKER} 當前價格: ${price:.2f}")
                return True
        
        print(f"   ❌ Yahoo Finance 返回無效數據: {response.status_code}")
        return False
            
    except Exception as e:
        print(f"   ❌ Yahoo Finance 錯誤: {e}")
        return False

def test_yfinance():
    """測試 yfinance 庫"""
    print("\n[5] 測試 yfinance 庫...")
    
    try:
        import yfinance as yf
        
        ticker = yf.Ticker(TEST_TICKER)
        info = ticker.info
        
        if info and info.get('currentPrice', 0) > 0:
            price = info.get('currentPrice') or info.get('regularMarketPrice', 0)
            print(f"   ✅ yfinance 連接成功!")
            print(f"   {TEST_TICKER} 當前價格: ${price:.2f}")
            return True
        elif info and info.get('regularMarketPrice', 0) > 0:
            price = info.get('regularMarketPrice', 0)
            print(f"   ✅ yfinance 連接成功!")
            print(f"   {TEST_TICKER} 當前價格: ${price:.2f}")
            return True
        else:
            print(f"   ❌ yfinance 返回無效數據")
            return False
            
    except Exception as e:
        print(f"   ❌ yfinance 錯誤: {e}")
        return False

def test_finviz():
    """測試 Finviz 抓取"""
    print("\n[6] 測試 Finviz 抓取...")
    
    try:
        import requests
        from bs4 import BeautifulSoup
        
        url = f"https://finviz.com/quote.ashx?t={TEST_TICKER}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 嘗試找到價格
            price_element = soup.find('strong', class_='quote-price_wrapper_price')
            if price_element:
                price = float(price_element.text.replace(',', ''))
                print(f"   ✅ Finviz 連接成功!")
                print(f"   {TEST_TICKER} 當前價格: ${price:.2f}")
                return True
            else:
                # 嘗試其他方式
                tables = soup.find_all('table', class_='snapshot-table2')
                if tables:
                    print(f"   ✅ Finviz 連接成功! (找到數據表格)")
                    return True
                    
            print(f"   ⚠️ Finviz 連接成功但無法解析價格")
            return True
        else:
            print(f"   ❌ Finviz 返回狀態碼: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ Finviz 錯誤: {e}")
        return False

def test_rapidapi():
    """測試 RapidAPI (yahoo-finance15)"""
    print("\n[7] 測試 RapidAPI...")
    api_key = os.getenv('RAPIDAPI_KEY')
    api_host = os.getenv('RAPIDAPI_HOST')
    rapidapi_enabled = os.getenv('RAPIDAPI_ENABLED', 'False').lower() == 'true'
    
    if not rapidapi_enabled:
        print("   ⚠️ RapidAPI 未啟用 (RAPIDAPI_ENABLED=False)")
        return None
    
    if not api_key or not api_host:
        print("   ❌ RAPIDAPI_KEY 或 RAPIDAPI_HOST 未設置")
        return False
    
    print(f"   API Key: {api_key[:8]}...{api_key[-4:]}")
    print(f"   Host: {api_host}")
    
    try:
        import requests
        
        # 使用 yahoo-finance15 的正確端點
        url = f"https://{api_host}/api/v1/markets/quote"
        headers = {
            'X-RapidAPI-Key': api_key,
            'X-RapidAPI-Host': api_host
        }
        params = {
            'ticker': TEST_TICKER,
            'type': 'STOCKS'
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('body'):
                body = data['body']
                # 嘗試獲取價格
                price = body.get('regularMarketPrice') or body.get('price')
                print(f"   ✅ RapidAPI 連接成功!")
                if price:
                    print(f"   {TEST_TICKER} 當前價格: ${price}")
                else:
                    print(f"   響應: {str(body)[:100]}...")
                return True
            else:
                print(f"   ✅ RapidAPI 連接成功!")
                print(f"   響應: {str(data)[:100]}...")
                return True
        else:
            print(f"   ❌ RapidAPI 返回狀態碼: {response.status_code}")
            print(f"   響應: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"   ❌ RapidAPI 錯誤: {e}")
        return False

def test_ibkr():
    """測試 IBKR 連接"""
    print("\n[8] 測試 IBKR 連接...")
    
    ibkr_enabled = os.getenv('IBKR_ENABLED', 'False').lower() == 'true'
    
    if not ibkr_enabled:
        print("   ⚠️ IBKR 未啟用 (IBKR_ENABLED=False)")
        return None
    
    try:
        from ib_insync import IB
        
        ib = IB()
        host = os.getenv('IBKR_HOST', '127.0.0.1')
        port = int(os.getenv('IBKR_PORT_PAPER', 7497))
        client_id = int(os.getenv('IBKR_CLIENT_ID', 1))
        
        print(f"   嘗試連接 {host}:{port} (client_id={client_id})...")
        
        ib.connect(host=host, port=port, clientId=client_id, timeout=5)
        
        if ib.isConnected():
            print(f"   ✅ IBKR 連接成功!")
            ib.disconnect()
            return True
        else:
            print("   ❌ IBKR 連接失敗")
            return False
            
    except Exception as e:
        print(f"   ❌ IBKR 錯誤: {e}")
        print("   提示: 請確保 TWS 或 IB Gateway 正在運行")
        return False

def main():
    """主測試函數"""
    results = {}
    
    # 測試各 API
    results['Finnhub'] = test_finnhub()
    time.sleep(1)
    
    results['Alpha Vantage'] = test_alpha_vantage()
    time.sleep(1)
    
    results['FRED'] = test_fred()
    time.sleep(1)
    
    results['Yahoo Finance'] = test_yahoo_finance()
    time.sleep(1)
    
    results['yfinance'] = test_yfinance()
    time.sleep(1)
    
    results['Finviz'] = test_finviz()
    time.sleep(1)
    
    results['RapidAPI'] = test_rapidapi()
    time.sleep(1)
    
    results['IBKR'] = test_ibkr()
    
    # 總結
    print("\n" + "=" * 70)
    print("測試結果總結")
    print("=" * 70)
    
    success_count = 0
    fail_count = 0
    skip_count = 0
    
    for api, status in results.items():
        if status is True:
            print(f"   ✅ {api}: 成功")
            success_count += 1
        elif status is False:
            print(f"   ❌ {api}: 失敗")
            fail_count += 1
        else:
            print(f"   ⚠️ {api}: 跳過")
            skip_count += 1
    
    print(f"\n總計: {success_count} 成功, {fail_count} 失敗, {skip_count} 跳過")
    print("=" * 70)
    
    return fail_count == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
