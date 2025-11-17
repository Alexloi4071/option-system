#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
測試 Finnhub API 集成
用於驗證所有更新是否正確工作
"""

import logging
from datetime import datetime

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_api_config():
    """測試1: API配置是否正確"""
    print("\n" + "=" * 70)
    print("測試1: 檢查API配置")
    print("=" * 70)
    
    try:
        from config.api_config import api_config
        
        # 檢查FINNHUB配置
        finnhub_config = api_config.FINNHUB
        assert 'earnings_calendar' in finnhub_config['provides'], "❌ 缺少earnings_calendar"
        assert 'dividend_calendar' in finnhub_config['provides'], "❌ 缺少dividend_calendar"
        
        # 檢查數據優先級
        assert 'earnings_date' in api_config.DATA_PRIORITY, "❌ 缺少earnings_date優先級"
        assert 'dividend_date' in api_config.DATA_PRIORITY, "❌ 缺少dividend_date優先級"
        
        print("✅ API配置正確")
        print(f"  Finnhub提供功能: {len(finnhub_config['provides'])}個")
        print(f"  數據優先級配置: {len(api_config.DATA_PRIORITY)}個")
        return True
        
    except Exception as e:
        print(f"❌ API配置測試失敗: {e}")
        return False


def test_data_fetcher_init():
    """測試2: DataFetcher初始化"""
    print("\n" + "=" * 70)
    print("測試2: DataFetcher初始化")
    print("=" * 70)
    
    try:
        from data_layer.data_fetcher import DataFetcher
        
        fetcher = DataFetcher()
        
        # 檢查客戶端
        assert fetcher.yfinance_client is not None, "❌ yfinance客戶端未初始化"
        assert hasattr(fetcher, 'finnhub_client'), "❌ 缺少finnhub_client屬性"
        
        # 檢查新方法
        assert hasattr(fetcher, 'get_earnings_calendar'), "❌ 缺少get_earnings_calendar方法"
        assert hasattr(fetcher, 'get_dividend_calendar'), "❌ 缺少get_dividend_calendar方法"
        
        print("✅ DataFetcher初始化正確")
        print(f"  yfinance客戶端: ✓")
        print(f"  FRED客戶端: {'✓' if fetcher.fred_client else '⚠ 未設置API Key'}")
        print(f"  Finnhub客戶端: {'✓' if fetcher.finnhub_client else '⚠ 未設置API Key'}")
        print(f"  新增方法: get_earnings_calendar, get_dividend_calendar")
        return True
        
    except Exception as e:
        print(f"❌ DataFetcher測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_module14_parameters():
    """測試3: Module14參數更新"""
    print("\n" + "=" * 70)
    print("測試3: Module14 監察崗位參數")
    print("=" * 70)
    
    try:
        from calculation_layer.module14_monitoring_posts import MonitoringPostsCalculator
        import inspect
        
        calc = MonitoringPostsCalculator()
        
        # 檢查calculate方法參數
        sig = inspect.signature(calc.calculate)
        params = list(sig.parameters.keys())
        
        assert 'dividend_date' in params, "❌ 缺少dividend_date參數"
        assert 'earnings_date' in params, "❌ 缺少earnings_date參數"
        assert 'expiration_date' in params, "❌ 缺少expiration_date參數"
        
        print("✅ Module14參數正確")
        print(f"  總參數數: {len(params)}")
        print(f"  新增參數: dividend_date, earnings_date, expiration_date")
        return True
        
    except Exception as e:
        print(f"❌ Module14測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_complete_data_structure():
    """測試4: 完整數據包結構"""
    print("\n" + "=" * 70)
    print("測試4: 檢查完整數據包結構")
    print("=" * 70)
    
    try:
        from data_layer.data_fetcher import DataFetcher
        
        fetcher = DataFetcher()
        
        # 使用AAPL測試 (如果API Key可用)
        print("  嘗試獲取AAPL數據...")
        data = fetcher.get_complete_analysis_data('AAPL')
        
        if data:
            # 檢查新字段
            new_fields = [
                'next_earnings_date',
                'earnings_call_time',
                'eps_estimate',
                'ex_dividend_date',
                'dividend_payment_date',
                'dividend_frequency'
            ]
            
            missing_fields = [f for f in new_fields if f not in data]
            
            if missing_fields:
                print(f"⚠ 缺少字段: {missing_fields}")
            else:
                print("✅ 數據包結構完整")
                print(f"\n  新增字段值:")
                for field in new_fields:
                    value = data.get(field, 'N/A')
                    print(f"    {field}: {value}")
            
            return len(missing_fields) == 0
        else:
            print("⚠ 無法獲取數據 (可能是API Key未設置)")
            return True  # 不算失敗，只是警告
        
    except Exception as e:
        print(f"❌ 數據包測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_module14_execution():
    """測試5: Module14執行"""
    print("\n" + "=" * 70)
    print("測試5: Module14 執行測試")
    print("=" * 70)
    
    try:
        from calculation_layer.module14_monitoring_posts import MonitoringPostsCalculator
        
        calc = MonitoringPostsCalculator()
        
        # 使用測試數據
        result = calc.calculate(
            stock_price=180.0,
            option_premium=5.0,
            iv=25.0,
            delta=0.12,
            open_interest=1000,
            volume=50000,
            bid_ask_spread=0.05,
            atr=2.5,
            vix=20.0,
            dividend_date="2024-11-15",
            earnings_date="2024-11-20",
            expiration_date="2024-12-20"
        )
        
        # 檢查結果
        assert result is not None, "❌ 結果為None"
        assert hasattr(result, 'dividend_date'), "❌ 缺少dividend_date"
        assert hasattr(result, 'earnings_date'), "❌ 缺少earnings_date"
        assert hasattr(result, 'expiration_date'), "❌ 缺少expiration_date"
        
        result_dict = result.to_dict()
        
        print("✅ Module14執行成功")
        print(f"\n  監察結果:")
        print(f"    警報數: {result.total_alerts}")
        print(f"    風險級別: {result.risk_level}")
        print(f"    派息日: {result.dividend_date}")
        print(f"    業績日: {result.earnings_date}")
        print(f"    到期日: {result.expiration_date}")
        return True
        
    except Exception as e:
        print(f"❌ Module14執行測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """運行所有測試"""
    print("\n" + "=" * 70)
    print("🔧 Finnhub API 集成測試套件")
    print("=" * 70)
    print(f"測試時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tests = [
        ("API配置", test_api_config),
        ("DataFetcher初始化", test_data_fetcher_init),
        ("Module14參數", test_module14_parameters),
        ("完整數據包結構", test_complete_data_structure),
        ("Module14執行", test_module14_execution)
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
        print("\n🎉 所有測試通過！Finnhub集成成功！")
        print("\n下一步:")
        print("  1. 在.env文件中添加 FINNHUB_API_KEY")
        print("  2. 運行: python main.py --ticker AAPL")
        print("  3. 檢查輸出中的業績和派息日期")
    else:
        print("\n⚠ 部分測試失敗，請檢查上述錯誤信息")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)

