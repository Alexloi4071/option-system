#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
快速測試 main.py 中 Module 15-19 的集成
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_integration():
    """測試 Module 15-19 是否已集成到 main.py"""
    print("=" * 80)
    print("測試 main.py 模塊集成")
    print("=" * 80)
    
    # 讀取 main.py 內容
    with open('main.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 檢查是否包含新模塊的計算邏輯
    checks = [
        ('Module 15 導入', 'from calculation_layer.module15_black_scholes import BlackScholesCalculator'),
        ('Module 16 導入', 'from calculation_layer.module16_greeks import GreeksCalculator'),
        ('Module 17 導入', 'from calculation_layer.module17_implied_volatility import ImpliedVolatilityCalculator'),
        ('Module 18 導入', 'from calculation_layer.module18_historical_volatility import HistoricalVolatilityCalculator'),
        ('Module 19 導入', 'from calculation_layer.module19_put_call_parity import PutCallParityValidator'),
        ('Module 15 計算', "bs_calc = BlackScholesCalculator()"),
        ('Module 16 計算', "greeks_calc = GreeksCalculator()"),
        ('Module 17 計算', "iv_calc = ImpliedVolatilityCalculator()"),
        ('Module 18 計算', "hv_calc = HistoricalVolatilityCalculator()"),
        ('Module 19 計算', "parity_validator = PutCallParityValidator()"),
        ('Module 15 結果保存', "self.analysis_results['module15_black_scholes']"),
        ('Module 16 結果保存', "self.analysis_results['module16_greeks']"),
        ('Module 17 結果保存', "self.analysis_results['module17_implied_volatility']"),
        ('Module 18 結果保存', "self.analysis_results['module18_historical_volatility']"),
        ('Module 19 結果保存', "self.analysis_results['module19_put_call_parity']"),
        ('共同參數準備', "risk_free_rate = analysis_data.get('risk_free_rate'"),
        ('時間參數計算', "time_to_expiration_years = days_to_expiration / 365.0"),
        ('波動率參數', "volatility_estimate = analysis_data.get('implied_volatility'"),
    ]
    
    passed = 0
    failed = 0
    
    print("\n檢查項目:")
    for name, check_str in checks:
        if check_str in content:
            print(f"  ✓ {name}")
            passed += 1
        else:
            print(f"  ✗ {name} - 未找到")
            failed += 1
    
    print("\n" + "=" * 80)
    print(f"測試結果: {passed}/{len(checks)} 通過")
    print("=" * 80)
    
    if failed == 0:
        print("\n✅ 所有檢查通過！Module 15-19 已成功集成到 main.py")
        return True
    else:
        print(f"\n⚠ {failed} 個檢查失敗")
        return False

if __name__ == "__main__":
    success = test_integration()
    sys.exit(0 if success else 1)
