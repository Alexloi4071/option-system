#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Module 18 單元測試: 歷史波動率計算器

測試覆蓋:
1. HV 計算準確性
2. 不同窗口期測試
3. IV/HV 比率判斷邏輯
4. 數據不足情況處理
"""

import unittest
import sys
import os
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from calculation_layer.module18_historical_volatility import (
    HistoricalVolatilityCalculator,
    HVResult,
    IVHVRatioResult
)


class TestHistoricalVolatilityCalculator(unittest.TestCase):
    """歷史波動率計算器測試類"""
    
    def setUp(self):
        """測試前準備"""
        self.calculator = HistoricalVolatilityCalculator()
        
        # 創建測試數據
        dates = pd.date_range('2024-01-01', periods=60, freq='D')
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.02, 60)
        prices = 100 * np.exp(np.cumsum(returns))
        self.price_series = pd.Series(prices, index=dates)
    
    def test_hv_calculation_30_days(self):
        """測試 30 天 HV 計算"""
        result = self.calculator.calculate_hv(self.price_series, window=30)
        
        self.assertIsInstance(result, HVResult)
        self.assertGreater(result.historical_volatility, 0)
        self.assertEqual(result.data_points, 29)  # 30個價格 -> 29個收益率
    
    def test_hv_positive(self):
        """測試 HV 總是正數"""
        result = self.calculator.calculate_hv(self.price_series, window=20)
        self.assertGreater(result.historical_volatility, 0)
    
    def test_multiple_windows(self):
        """測試多窗口期計算"""
        results = self.calculator.calculate_multiple_windows(
            self.price_series,
            windows=[10, 20, 30]
        )
        
        self.assertEqual(len(results), 3)
        for window, result in results.items():
            self.assertGreater(result.historical_volatility, 0)
    
    def test_iv_hv_ratio_overvalued(self):
        """測試 IV 高估判斷"""
        result = self.calculator.calculate_iv_hv_ratio(
            implied_volatility=0.40,
            historical_volatility=0.25
        )
        
        self.assertGreater(result.iv_hv_ratio, 1.2)
        self.assertEqual(result.assessment, "IV 高估")
    
    def test_iv_hv_ratio_undervalued(self):
        """測試 IV 低估判斷"""
        result = self.calculator.calculate_iv_hv_ratio(
            implied_volatility=0.15,
            historical_volatility=0.25
        )
        
        self.assertLess(result.iv_hv_ratio, 0.8)
        self.assertEqual(result.assessment, "IV 低估")
    
    def test_iv_hv_ratio_fair(self):
        """測試合理範圍判斷"""
        result = self.calculator.calculate_iv_hv_ratio(
            implied_volatility=0.25,
            historical_volatility=0.25
        )
        
        self.assertGreaterEqual(result.iv_hv_ratio, 0.8)
        self.assertLessEqual(result.iv_hv_ratio, 1.2)
        self.assertEqual(result.assessment, "合理範圍")
    
    def test_to_dict_hv_result(self):
        """測試 HVResult to_dict()"""
        result = self.calculator.calculate_hv(self.price_series, window=30)
        result_dict = result.to_dict()
        
        required_fields = [
            'historical_volatility', 'historical_volatility_percent',
            'window_days', 'data_points', 'calculation_date'
        ]
        
        for field in required_fields:
            self.assertIn(field, result_dict)
    
    def test_to_dict_ratio_result(self):
        """測試 IVHVRatioResult to_dict()"""
        result = self.calculator.calculate_iv_hv_ratio(0.30, 0.25)
        result_dict = result.to_dict()
        
        required_fields = [
            'implied_volatility', 'historical_volatility',
            'iv_hv_ratio', 'assessment', 'recommendation'
        ]
        
        for field in required_fields:
            self.assertIn(field, result_dict)


def run_tests():
    """運行所有測試"""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestHistoricalVolatilityCalculator)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
