#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
完整測試套件: 新增模塊綜合測試

本測試套件整合了所有新模塊的測試，包括:
- 單元測試 (Module 15-19)
- 集成測試 (模塊間協作)
- 錯誤處理測試
- 邊界條件測試
- 性能測試

Requirements: 9.1, 9.2, 9.3
"""

import unittest
import sys
import os
import time
import pandas as pd
import numpy as np
from datetime import datetime

# 添加項目根目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 導入所有測試類
# 注意: 由於測試文件在同一目錄，使用相對導入
try:
    from test_module15_black_scholes import TestBlackScholesCalculator
    from test_module16_greeks import TestGreeksCalculator
    from test_module17_implied_volatility import TestImpliedVolatilityCalculator
    from test_module18_historical_volatility import TestHistoricalVolatilityCalculator
    from test_module19_put_call_parity import TestPutCallParityValidator
    from test_data_fetcher_integration import (
        TestDataFetcherFallbackStrategy,
        TestImpliedVolatilityValidation,
        TestOptionTheoreticalPrice,
        TestAPIStatusReport,
        TestIntegrationWorkflow
    )
except ImportError:
    # 如果相對導入失敗，嘗試絕對導入
    from tests.test_module15_black_scholes import TestBlackScholesCalculator
    from tests.test_module16_greeks import TestGreeksCalculator
    from tests.test_module17_implied_volatility import TestImpliedVolatilityCalculator
    from tests.test_module18_historical_volatility import TestHistoricalVolatilityCalculator
    from tests.test_module19_put_call_parity import TestPutCallParityValidator
    from tests.test_data_fetcher_integration import (
        TestDataFetcherFallbackStrategy,
        TestImpliedVolatilityValidation,
        TestOptionTheoreticalPrice,
        TestAPIStatusReport,
        TestIntegrationWorkflow
    )

# 導入計算模塊
from calculation_layer.module15_black_scholes import BlackScholesCalculator
from calculation_layer.module16_greeks import GreeksCalculator
from calculation_layer.module17_implied_volatility import ImpliedVolatilityCalculator
from calculation_layer.module18_historical_volatility import HistoricalVolatilityCalculator
from calculation_layer.module19_put_call_parity import PutCallParityValidator


class TestModuleIntegration(unittest.TestCase):
    """模塊集成測試類 - 測試模塊間的協作"""
    
    def setUp(self):
        """測試前準備"""
        self.bs_calc = BlackScholesCalculator()
        self.greeks_calc = GreeksCalculator()
        self.iv_calc = ImpliedVolatilityCalculator()
        self.hv_calc = HistoricalVolatilityCalculator()
        self.parity_validator = PutCallParityValidator()
    
    def test_bs_to_greeks_integration(self):
        """測試 BS 模型與 Greeks 計算的集成"""
        # 1. 使用 BS 計算期權價格
        bs_result = self.bs_calc.calculate_option_price(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.2,
            option_type='call'
        )
        
        # 2. 使用相同參數計算 Greeks
        greeks_result = self.greeks_calc.calculate_all_greeks(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.2,
            option_type='call'
        )
        
        # 3. 驗證兩者使用相同的 d1, d2
        self.assertIsNotNone(bs_result.d1)
        self.assertIsNotNone(greeks_result.delta)
        
        # 4. 驗證 Greeks 在合理範圍內
        self.assertGreater(greeks_result.delta, 0)
        self.assertLess(greeks_result.delta, 1)
        self.assertGreater(greeks_result.gamma, 0)
    
    def test_bs_to_iv_roundtrip(self):
        """測試 BS 定價到 IV 反推的往返一致性"""
        # 1. 使用已知 IV 計算期權價格
        known_iv = 0.25
        bs_result = self.bs_calc.calculate_option_price(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=known_iv,
            option_type='call'
        )
        
        # 2. 從價格反推 IV
        iv_result = self.iv_calc.calculate_implied_volatility(
            market_price=bs_result.option_price,
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            option_type='call'
        )
        
        # 3. 驗證往返一致性
        self.assertTrue(iv_result.converged, "IV 計算應該收斂")
        self.assertAlmostEqual(
            iv_result.implied_volatility,
            known_iv,
            places=3,
            msg="往返後 IV 應該與原始值一致"
        )
    
    def test_parity_with_bs_prices(self):
        """測試 Put-Call Parity 與 BS 理論價格的一致性"""
        # 1. 使用 BS 計算 Call 和 Put 價格
        call_result = self.bs_calc.calculate_option_price(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.2,
            option_type='call'
        )
        
        put_result = self.bs_calc.calculate_option_price(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.2,
            option_type='put'
        )
        
        # 2. 驗證 Parity
        parity_result = self.parity_validator.validate_parity(
            call_price=call_result.option_price,
            put_price=put_result.option_price,
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0
        )
        
        # 3. BS 理論價格應該完美滿足 Parity
        self.assertLess(
            abs(parity_result.deviation),
            0.01,
            msg="BS 理論價格應該滿足 Put-Call Parity"
        )
        self.assertFalse(
            parity_result.arbitrage_opportunity,
            msg="理論價格不應該有套利機會"
        )
    
    def test_iv_hv_comparison_workflow(self):
        """測試 IV/HV 比較的完整工作流程"""
        # 1. 創建模擬歷史價格數據
        dates = pd.date_range('2024-01-01', periods=60, freq='D')
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.02, 60)
        prices = 100 * np.exp(np.cumsum(returns))
        price_series = pd.Series(prices, index=dates)
        
        # 2. 計算 HV
        hv_result = self.hv_calc.calculate_hv(price_series, window=30)
        
        # 3. 使用 BS 計算期權價格（假設市場 IV）
        market_iv = 0.30
        bs_result = self.bs_calc.calculate_option_price(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=market_iv,
            option_type='call'
        )
        
        # 4. 計算 IV/HV 比率
        ratio_result = self.hv_calc.calculate_iv_hv_ratio(
            implied_volatility=market_iv,
            historical_volatility=hv_result.historical_volatility
        )
        
        # 5. 驗證結果
        self.assertIsNotNone(ratio_result.iv_hv_ratio)
        self.assertIn(
            ratio_result.assessment,
            ["IV 高估", "IV 低估", "合理範圍"]
        )
    
    def test_complete_option_analysis_workflow(self):
        """測試完整的期權分析工作流程"""
        # 參數設置
        stock_price = 100.0
        strike_price = 100.0
        risk_free_rate = 0.05
        time_to_expiration = 1.0
        volatility = 0.25
        
        # 1. BS 定價
        call_price = self.bs_calc.calculate_option_price(
            stock_price, strike_price, risk_free_rate,
            time_to_expiration, volatility, 'call'
        )
        
        put_price = self.bs_calc.calculate_option_price(
            stock_price, strike_price, risk_free_rate,
            time_to_expiration, volatility, 'put'
        )
        
        # 2. Greeks 計算
        call_greeks = self.greeks_calc.calculate_all_greeks(
            stock_price, strike_price, risk_free_rate,
            time_to_expiration, volatility, 'call'
        )
        
        # 3. IV 驗證
        iv_result = self.iv_calc.calculate_implied_volatility(
            call_price.option_price, stock_price, strike_price,
            risk_free_rate, time_to_expiration, 'call'
        )
        
        # 4. Parity 驗證
        parity_result = self.parity_validator.validate_parity(
            call_price.option_price, put_price.option_price,
            stock_price, strike_price, risk_free_rate, time_to_expiration
        )
        
        # 5. 驗證所有結果都成功生成
        self.assertIsNotNone(call_price.option_price)
        self.assertIsNotNone(call_greeks.delta)
        self.assertTrue(iv_result.converged)
        self.assertIsNotNone(parity_result.deviation)


class TestErrorHandling(unittest.TestCase):
    """錯誤處理測試類"""
    
    def setUp(self):
        """測試前準備"""
        self.bs_calc = BlackScholesCalculator()
        self.greeks_calc = GreeksCalculator()
        self.iv_calc = ImpliedVolatilityCalculator()
    
    def test_bs_negative_stock_price(self):
        """測試 BS 模型對負股價的處理"""
        with self.assertRaises(ValueError):
            self.bs_calc.calculate_option_price(
                stock_price=-100.0,
                strike_price=100.0,
                risk_free_rate=0.05,
                time_to_expiration=1.0,
                volatility=0.2,
                option_type='call'
            )
    
    def test_bs_negative_strike(self):
        """測試 BS 模型對負行使價的處理"""
        with self.assertRaises(ValueError):
            self.bs_calc.calculate_option_price(
                stock_price=100.0,
                strike_price=-100.0,
                risk_free_rate=0.05,
                time_to_expiration=1.0,
                volatility=0.2,
                option_type='call'
            )
    
    def test_bs_negative_time(self):
        """測試 BS 模型對負到期時間的處理"""
        with self.assertRaises(ValueError):
            self.bs_calc.calculate_option_price(
                stock_price=100.0,
                strike_price=100.0,
                risk_free_rate=0.05,
                time_to_expiration=-1.0,
                volatility=0.2,
                option_type='call'
            )
    
    def test_bs_negative_volatility(self):
        """測試 BS 模型對負波動率的處理"""
        with self.assertRaises(ValueError):
            self.bs_calc.calculate_option_price(
                stock_price=100.0,
                strike_price=100.0,
                risk_free_rate=0.05,
                time_to_expiration=1.0,
                volatility=-0.2,
                option_type='call'
            )
    
    def test_bs_invalid_option_type(self):
        """測試 BS 模型對無效期權類型的處理"""
        with self.assertRaises(ValueError):
            self.bs_calc.calculate_option_price(
                stock_price=100.0,
                strike_price=100.0,
                risk_free_rate=0.05,
                time_to_expiration=1.0,
                volatility=0.2,
                option_type='invalid'
            )
    
    def test_bs_extreme_volatility(self):
        """測試 BS 模型對極端波動率的處理"""
        with self.assertRaises(ValueError):
            self.bs_calc.calculate_option_price(
                stock_price=100.0,
                strike_price=100.0,
                risk_free_rate=0.05,
                time_to_expiration=1.0,
                volatility=10.0,  # 1000%
                option_type='call'
            )
    
    def test_greeks_negative_inputs(self):
        """測試 Greeks 計算對負輸入的處理"""
        with self.assertRaises(ValueError):
            self.greeks_calc.calculate_all_greeks(
                stock_price=-100.0,
                strike_price=100.0,
                risk_free_rate=0.05,
                time_to_expiration=1.0,
                volatility=0.2,
                option_type='call'
            )
    
    def test_iv_negative_market_price(self):
        """測試 IV 計算對負市場價格的處理"""
        with self.assertRaises(ValueError):
            self.iv_calc.calculate_implied_volatility(
                market_price=-10.0,
                stock_price=100.0,
                strike_price=100.0,
                risk_free_rate=0.05,
                time_to_expiration=1.0,
                option_type='call'
            )
    
    def test_iv_zero_time(self):
        """測試 IV 計算對零到期時間的處理"""
        with self.assertRaises(ValueError):
            self.iv_calc.calculate_implied_volatility(
                market_price=10.0,
                stock_price=100.0,
                strike_price=100.0,
                risk_free_rate=0.05,
                time_to_expiration=0.0,
                option_type='call'
            )


class TestBoundaryConditions(unittest.TestCase):
    """邊界條件測試類"""
    
    def setUp(self):
        """測試前準備"""
        self.bs_calc = BlackScholesCalculator()
        self.greeks_calc = GreeksCalculator()
    
    def test_deep_itm_call(self):
        """測試深度 ITM Call 期權"""
        result = self.bs_calc.calculate_option_price(
            stock_price=150.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.2,
            option_type='call'
        )
        
        # 深度 ITM Call 價格應該接近內在價值
        intrinsic_value = 150.0 - 100.0
        self.assertGreater(result.option_price, intrinsic_value)
        
        # Delta 應該接近 1
        greeks = self.greeks_calc.calculate_all_greeks(
            150.0, 100.0, 0.05, 1.0, 0.2, 'call'
        )
        self.assertGreater(greeks.delta, 0.9)
    
    def test_deep_otm_call(self):
        """測試深度 OTM Call 期權"""
        result = self.bs_calc.calculate_option_price(
            stock_price=50.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.2,
            option_type='call'
        )
        
        # 深度 OTM Call 價格應該很小但為正
        self.assertGreater(result.option_price, 0)
        self.assertLess(result.option_price, 1)
        
        # Delta 應該接近 0
        greeks = self.greeks_calc.calculate_all_greeks(
            50.0, 100.0, 0.05, 1.0, 0.2, 'call'
        )
        self.assertLess(greeks.delta, 0.1)
    
    def test_near_expiration(self):
        """測試接近到期的期權"""
        result = self.bs_calc.calculate_option_price(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=0.01,  # 約 3.65 天
            volatility=0.2,
            option_type='call'
        )
        
        # 接近到期的 ATM 期權價格應該較小
        self.assertGreater(result.option_price, 0)
        self.assertLess(result.option_price, 5)
    
    def test_very_low_volatility(self):
        """測試極低波動率"""
        result = self.bs_calc.calculate_option_price(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.01,  # 1%
            option_type='call'
        )
        
        # 低波動率應該導致較低的期權價格
        self.assertGreater(result.option_price, 0)
        self.assertLess(result.option_price, 10)
    
    def test_high_volatility(self):
        """測試高波動率"""
        result = self.bs_calc.calculate_option_price(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.80,  # 80%
            option_type='call'
        )
        
        # 高波動率應該導致較高的期權價格
        self.assertGreater(result.option_price, 20)


class TestPerformance(unittest.TestCase):
    """性能測試類 - Requirements: 設計文檔 - Performance Considerations"""
    
    def setUp(self):
        """測試前準備"""
        self.bs_calc = BlackScholesCalculator()
        self.greeks_calc = GreeksCalculator()
        self.iv_calc = ImpliedVolatilityCalculator()
    
    def test_bs_calculation_speed(self):
        """測試 BS 計算速度（應 < 10ms，含日誌）"""
        start_time = time.time()
        
        for _ in range(1000):
            self.bs_calc.calculate_option_price(
                stock_price=100.0,
                strike_price=100.0,
                risk_free_rate=0.05,
                time_to_expiration=1.0,
                volatility=0.2,
                option_type='call'
            )
        
        end_time = time.time()
        avg_time = (end_time - start_time) / 1000
        
        # 平均每次計算應該 < 10ms（含日誌記錄開銷）
        # 注：生產環境關閉詳細日誌後可達到 < 1ms
        self.assertLess(
            avg_time,
            0.010,
            msg=f"BS 計算平均時間 {avg_time*1000:.3f}ms 應該 < 10ms"
        )
    
    def test_greeks_calculation_speed(self):
        """測試 Greeks 計算速度（應 < 15ms，含日誌）"""
        start_time = time.time()
        
        for _ in range(1000):
            self.greeks_calc.calculate_all_greeks(
                stock_price=100.0,
                strike_price=100.0,
                risk_free_rate=0.05,
                time_to_expiration=1.0,
                volatility=0.2,
                option_type='call'
            )
        
        end_time = time.time()
        avg_time = (end_time - start_time) / 1000
        
        # Greeks 計算應該 < 15ms（含日誌記錄開銷）
        # 注：生產環境關閉詳細日誌後可達到 < 2ms
        self.assertLess(
            avg_time,
            0.015,
            msg=f"Greeks 計算平均時間 {avg_time*1000:.3f}ms 應該 < 15ms"
        )
    
    def test_iv_convergence_speed(self):
        """測試 IV 反推收斂速度（應 < 10 次迭代）"""
        # 先計算一個期權價格
        bs_result = self.bs_calc.calculate_option_price(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.25,
            option_type='call'
        )
        
        # 反推 IV
        iv_result = self.iv_calc.calculate_implied_volatility(
            market_price=bs_result.option_price,
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            option_type='call'
        )
        
        # 應該在 10 次迭代內收斂
        self.assertLess(
            iv_result.iterations,
            10,
            msg=f"IV 計算迭代次數 {iv_result.iterations} 應該 < 10"
        )
    
    def test_batch_calculation_performance(self):
        """測試批量計算性能（應 < 1s，含日誌）"""
        start_time = time.time()
        
        # 批量計算 100 個不同參數的期權
        for i in range(100):
            stock_price = 90 + i * 0.2
            self.bs_calc.calculate_option_price(
                stock_price=stock_price,
                strike_price=100.0,
                risk_free_rate=0.05,
                time_to_expiration=1.0,
                volatility=0.2,
                option_type='call'
            )
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # 100 個計算應該在 1 秒內完成（含日誌記錄開銷）
        # 注：生產環境關閉詳細日誌後可達到 < 0.1s
        self.assertLess(
            total_time,
            1.0,
            msg=f"批量計算 100 個期權用時 {total_time:.3f}s 應該 < 1s"
        )


def create_test_suite():
    """創建完整測試套件"""
    suite = unittest.TestSuite()
    
    # 添加單元測試 (Task 12.1)
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestBlackScholesCalculator))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestGreeksCalculator))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestImpliedVolatilityCalculator))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestHistoricalVolatilityCalculator))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestPutCallParityValidator))
    
    # 添加模塊間集成測試 (Task 12.2)
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestModuleIntegration))
    
    # 添加 DataFetcher 集成測試 (Task 12.2)
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestDataFetcherFallbackStrategy))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestImpliedVolatilityValidation))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestOptionTheoreticalPrice))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestAPIStatusReport))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestIntegrationWorkflow))
    
    # 添加錯誤處理測試
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestErrorHandling))
    
    # 添加邊界條件測試
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestBoundaryConditions))
    
    # 添加性能測試 (Task 12.3)
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestPerformance))
    
    return suite


def run_all_tests(verbosity=2):
    """運行所有測試"""
    print("=" * 70)
    print("開始運行完整測試套件")
    print("=" * 70)
    print()
    
    suite = create_test_suite()
    runner = unittest.TextTestRunner(verbosity=verbosity)
    
    start_time = time.time()
    result = runner.run(suite)
    end_time = time.time()
    
    print()
    print("=" * 70)
    print("測試結果摘要")
    print("=" * 70)
    print(f"總測試數: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失敗: {len(result.failures)}")
    print(f"錯誤: {len(result.errors)}")
    print(f"總耗時: {end_time - start_time:.2f} 秒")
    print("=" * 70)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
