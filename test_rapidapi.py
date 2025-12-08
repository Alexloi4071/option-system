#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""RapidAPI 連接測試腳本"""

import os
import sys
from dotenv import load_dotenv

# 載入環境變量
load_dotenv()

print('=== RapidAPI 配置測試 ===')
print(f'RAPIDAPI_ENABLED: {os.getenv("RAPIDAPI_ENABLED")}')
print(f'RAPIDAPI_HOST: {os.getenv("RAPIDAPI_HOST")}')
api_key = os.getenv("RAPIDAPI_KEY")
if api_key:
    print(f'RAPIDAPI_KEY: {api_key[:20]}...')
else:
    print('RAPIDAPI_KEY: 未設置')
    sys.exit(1)

from data_layer.rapidapi_client import RapidAPIClient

host = os.getenv('RAPIDAPI_HOST')

if api_key and host:
    client = RapidAPIClient(api_key, host)
    
    # 測試獲取報價
    print('\n--- 測試 1: 獲取 AAPL 報價 ---')
    quote = client.get_quote('AAPL')
    if quote:
        print('✓ RapidAPI 報價測試成功')
        print(f'響應類型: {type(quote)}')
        if isinstance(quote, dict):
            print(f'響應鍵: {list(quote.keys())[:5]}')
    else:
        print('✗ RapidAPI 報價測試失敗')
    
    # 測試獲取市場新聞
    print('\n--- 測試 2: 獲取市場新聞 ---')
    news = client.get_market_news('AAPL')
    if news:
        print('✓ RapidAPI 新聞測試成功')
        if isinstance(news, dict):
            print(f'響應鍵: {list(news.keys())[:5]}')
    else:
        print('✗ RapidAPI 新聞測試失敗')
    
    # 測試獲取期權鏈
    print('\n--- 測試 3: 獲取 AAPL 期權鏈 ---')
    options = client.get_options('AAPL')
    if options:
        print('✓ RapidAPI 期權鏈測試成功')
        if isinstance(options, dict):
            print(f'響應鍵: {list(options.keys())[:5]}')
    else:
        print('✗ RapidAPI 期權鏈測試失敗')
    
    print('\n=== 測試完成 ===')
    print(f'剩餘請求數: {client.rate_limiter.get_remaining()}')
else:
    print('✗ 請配置 RAPIDAPI_KEY 和 RAPIDAPI_HOST')
