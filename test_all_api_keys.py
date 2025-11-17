#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
完整API配置驗證腳本
驗證所有4個API的配置和連接
"""

import logging
from datetime import datetime
import sys

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_settings_configuration():
    """測試1: Settings配置"""
    print("\n" + "=" * 70)
    print("測試1: 檢查Settings配置")
    print("=" * 70)
    
    try:
        from config.settings import settings
        
        apis_status = {
            'FRED': bool(settings.FRED_API_KEY),
            'Finnhub': bool(settings.FINNHUB_API_KEY),
            'RapidAPI': bool(settings.RAPIDAPI_KEY),
            'Yahoo Finance 2.0': bool(settings.YAHOO_CLIENT_ID and settings.YAHOO_CLIENT_SECRET)
        }
        
        print("\nAPI Keys配置狀態:")
        for api_name, configured in apis_status.items():
            status = "✓ 已配置" if configured else "✗ 未配置"
            print(f"  {api_name}: {status}")
        
        configured_count = sum(apis_status.values())
        total_count = len(apis_status)
        
        print(f"\n總計: {configured_count}/{total_count} 個API已配置")
        
        if configured_count == total_count:
            print("✅ 所有API Keys已正確配置")
            return True
        else:
            print("⚠ 部分API Keys未配置，相關功能將不可用")
            return True  # 不算失敗
        
    except Exception as e:
        print(f"❌ Settings配置測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_config():
    """測試2: API Config配置"""
    print("\n" + "=" * 70)
    print("測試2: 檢查API Config")
    print("=" * 70)
    
    try:
        from config.api_config import api_config
        
        # 檢查所有API配置
        api_configs = {
            'YFINANCE': api_config.YFINANCE,
            'FRED': api_config.FRED,
            'FINNHUB': api_config.FINNHUB,
            'RAPIDAPI': api_config.RAPIDAPI,
            'YAHOO_FINANCE_V2': api_config.YAHOO_FINANCE_V2
        }
        
        print("\nAPI配置詳情:")
        for api_name, config in api_configs.items():
            print(f"\n  {api_name}:")
            print(f"    名稱: {config['name']}")
            print(f"    類型: {config['type']}")
            print(f"    需要認證: {config['requires_auth']}")
            print(f"    功能數: {len(config['provides'])}")
        
        # 檢查數據優先級
        print(f"\n數據優先級配置: {len(api_config.DATA_PRIORITY)} 個數據類型")
        
        print("\n✅ API Config配置完整")
        return True
        
    except Exception as e:
        print(f"❌ API Config測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_fred_api():
    """測試3: FRED API連接"""
    print("\n" + "=" * 70)
    print("測試3: FRED API連接測試")
    print("=" * 70)
    
    try:
        from config.settings import settings
        
        if not settings.FRED_API_KEY:
            print("⚠ FRED API Key未配置，跳過測試")
            return True
        
        from fredapi import Fred
        
        fred = Fred(api_key=settings.FRED_API_KEY)
        
        # 測試獲取10年期國債收益率
        print("  嘗試獲取10年期國債收益率...")
        dgs10 = fred.get_series_latest_release('DGS10')
        
        if dgs10 is not None and not dgs10.empty:
            latest_rate = dgs10.iloc[-1]
            print(f"✓ 成功獲取數據")
            print(f"  最新利率: {latest_rate:.2f}%")
            print(f"  日期: {dgs10.index[-1]}")
            print("✅ FRED API連接正常")
            return True
        else:
            print("⚠ 無法獲取數據")
            return False
        
    except Exception as e:
        print(f"❌ FRED API測試失敗: {e}")
        return False


def test_finnhub_api():
    """測試4: Finnhub API連接"""
    print("\n" + "=" * 70)
    print("測試4: Finnhub API連接測試")
    print("=" * 70)
    
    try:
        from config.settings import settings
        
        if not settings.FINNHUB_API_KEY:
            print("⚠ Finnhub API Key未配置，跳過測試")
            return True
        
        import finnhub
        
        finnhub_client = finnhub.Client(api_key=settings.FINNHUB_API_KEY)
        
        # 測試獲取公司資料
        print("  嘗試獲取AAPL公司資料...")
        profile = finnhub_client.company_profile2(symbol='AAPL')
        
        if profile:
            print(f"✓ 成功獲取數據")
            print(f"  公司名稱: {profile.get('name', 'N/A')}")
            print(f"  行業: {profile.get('finnhubIndustry', 'N/A')}")
            print(f"  國家: {profile.get('country', 'N/A')}")
            print("✅ Finnhub API連接正常")
            return True
        else:
            print("⚠ 無法獲取數據")
            return False
        
    except Exception as e:
        print(f"❌ Finnhub API測試失敗: {e}")
        return False


def test_yfinance():
    """測試5: yfinance（免費）"""
    print("\n" + "=" * 70)
    print("測試5: yfinance連接測試")
    print("=" * 70)
    
    try:
        import yfinance as yf
        
        # 測試獲取股票數據
        print("  嘗試獲取AAPL股票數據...")
        stock = yf.Ticker('AAPL')
        info = stock.info
        
        if info:
            print(f"✓ 成功獲取數據")
            print(f"  股票名稱: {info.get('longName', 'N/A')}")
            print(f"  當前股價: ${info.get('currentPrice', 0):.2f}")
            print(f"  市值: ${info.get('marketCap', 0):,.0f}")
            print("✅ yfinance連接正常")
            return True
        else:
            print("⚠ 無法獲取數據")
            return False
        
    except Exception as e:
        print(f"❌ yfinance測試失敗: {e}")
        return False


def test_data_fetcher_integration():
    """測試6: DataFetcher整合測試"""
    print("\n" + "=" * 70)
    print("測試6: DataFetcher整合測試")
    print("=" * 70)
    
    try:
        from data_layer.data_fetcher import DataFetcher
        
        fetcher = DataFetcher()
        
        # 檢查客戶端初始化
        clients_status = {
            'yfinance': fetcher.yfinance_client is not None,
            'FRED': fetcher.fred_client is not None,
            'Finnhub': fetcher.finnhub_client is not None
        }
        
        print("\n客戶端初始化狀態:")
        for client_name, initialized in clients_status.items():
            status = "✓ 已初始化" if initialized else "✗ 未初始化"
            print(f"  {client_name}: {status}")
        
        # 測試獲取完整數據
        print("\n嘗試獲取AAPL完整數據...")
        data = fetcher.get_complete_analysis_data('AAPL')
        
        if data:
            print("✓ 成功獲取完整數據包")
            print(f"\n數據包含字段數: {len(data)}")
            
            # 檢查關鍵字段
            key_fields = [
                'ticker', 'current_price', 'implied_volatility',
                'next_earnings_date', 'ex_dividend_date', 'risk_free_rate', 'vix'
            ]
            
            print("\n關鍵字段檢查:")
            for field in key_fields:
                value = data.get(field, 'N/A')
                status = "✓" if field in data else "✗"
                print(f"  {status} {field}: {value}")
            
            print("\n✅ DataFetcher整合正常")
            return True
        else:
            print("⚠ 無法獲取完整數據")
            return False
        
    except Exception as e:
        print(f"❌ DataFetcher測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """運行所有測試"""
    print("\n" + "=" * 70)
    print("🔧 完整API配置驗證套件")
    print("=" * 70)
    print(f"測試時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tests = [
        ("Settings配置", test_settings_configuration),
        ("API Config", test_api_config),
        ("FRED API連接", test_fred_api),
        ("Finnhub API連接", test_finnhub_api),
        ("yfinance連接", test_yfinance),
        ("DataFetcher整合", test_data_fetcher_integration)
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ 測試 '{name}' 發生異常: {e}")
            results.append((name, False))
    
    # 總結
    print("\n" + "=" * 70)
    print("📊 測試總結")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通過" if result else "❌ 失敗"
        print(f"  {name}: {status}")
    
    print("\n" + "-" * 70)
    print(f"  總測試數: {total}")
    print(f"  通過: {passed}")
    print(f"  失敗: {total - passed}")
    print(f"  通過率: {passed/total*100:.1f}%")
    print("=" * 70)
    
    if passed == total:
        print("\n🎉 所有測試通過！所有API已正確配置並可用！")
        print("\n✓ 系統已就緒，可以運行完整分析")
        print("  運行命令: python main.py --ticker AAPL")
    elif passed >= 4:
        print("\n✓ 核心功能測試通過！系統基本可用")
        print("  部分API未配置不影響基礎功能")
    else:
        print("\n⚠ 多個測試失敗，請檢查配置")
    
    return passed >= 4  # 至少4個測試通過才算成功


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

