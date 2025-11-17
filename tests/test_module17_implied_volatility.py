#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Module 17 單元測試: 隱含波動率計算器

測試覆蓋:
1. IV 反推準確性測試
2. 收斂速度測試
3. 未收斂情況處理
4. 異常值檢測
5. Call 和 Put 期權測試
6. 不同波動率水平測試
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from calculation_layer.module17_implied_volatility import (
    ImpliedVolatilityCalculator,
    IVResult
)
from calculation_layer.module15_black_scholes import BlackScholesCalculator


class TestImpliedVolatilityCalculator(unittest.TestCase):
    """隱含波動率計算器測試類"""
    
    def setUp(self):
        """測試前準備"""
        self.iv_calculator = ImpliedVolatilityCalculator()
        self.bs_calculator = BlackScholesCalculator()
    
    def test_iv_accuracy_low_volatility(self):
        """測試低波動率 IV 反推準確性"""
        known_iv = 0.15  # 15%
        
        # 使用 BS 模型計算期權價格
        bs_result = self.bs_calculator.calculate_option_price(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=known_iv,
            option_type='call'
        )
        
        # 從價格反推 IV
        iv_result = self.iv_calculator.calculate_implied_volatility(
            market_price=bs_result.option_price,
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            option_type='call'
        )
        
        # 驗證準確性
        self.assertTrue(iv_result.converged, "應該收斂")
        self.assertAlmostEqual(
            iv_result.implied_volatility,
            known_iv,
            places=3,
            msg="IV 反推應該準確到 0.1%"
        )
    
    def test_iv_accuracy_medium_volatility(self):
        """測試中等波動率 IV 反推準確性"""
        known_iv = 0.25  # 25%
        
        bs_result = self.bs_calculator.calculate_option_price(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=known_iv,
            option_type='call'
        )
        
        iv_result = self.iv_calculator.calculate_implied_volatility(
            market_price=bs_result.option_price,
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            option_type='call'
        )
        
        self.assertTrue(iv_result.converged)
        self.assertAlmostEqual(iv_result.implied_volatility, known_iv, places=3)
    
    def test_iv_accuracy_high_volatility(self):
        """測試高波動率 IV 反推準確性"""
        known_iv = 0.50  # 50%
        
        bs_result = self.bs_calculator.calculate_option_price(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=0.5,
            volatility=known_iv,
            option_type='call'
        )
        
        iv_result = self.iv_calculator.calculate_implied_volatility(
            market_price=bs_result.option_price,
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=0.5,
            option_type='call'
        )
        
        self.assertTrue(iv_result.converged)
        self.assertAlmostEqual(iv_result.implied_volatility, known_iv, places=3)
    
    def test_put_option_iv(self):
        """測試 Put 期權 IV 反推"""
        known_iv = 0.20
        
        bs_result = self.bs_calculator.calculate_option_price(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=known_iv,
            option_type='put'
        )
        
        iv_result = self.iv_calculator.calculate_implied_volatility(
            market_price=bs_result.option_price,
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            option_type='put'
        )
        
        self.assertTrue(iv_result.converged)
        self.assertAlmostEqual(iv_result.implied_volatility, known_iv, places=3)
    
    def test_convergence_speed(self):
        """測試收斂速度"""
        known_iv = 0.25
        
        bs_result = self.bs_calculator.calculate_option_price(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=known_iv,
            option_type='call'
        )
        
        iv_result = self.iv_calculator.calculate_implied_volatility(
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
            msg="應該在 10 次迭代內收斂"
        )
    
    def test_itm_call_iv(self):
        """測試 ITM Call 期權 IV"""
        known_iv = 0.30
        
        bs_result = self.bs_calculator.calculate_option_price(
            stock_price=110.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=0.5,
            volatility=known_iv,
            option_type='call'
        )
        
        iv_result = self.iv_calculator.calculate_implied_volatility(
            market_price=bs_result.option_price,
            stock_price=110.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=0.5,
            option_type='call'
        )
        
        self.assertTrue(iv_result.converged)
        self.assertAlmostEqual(iv_result.implied_volatility, known_iv, places=2)
    
    def test_otm_call_iv(self):
        """測試 OTM Call 期權 IV"""
        known_iv = 0.35
        
        bs_result = self.bs_calculator.calculate_option_price(
            stock_price=90.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=0.5,
            volatility=known_iv,
            option_type='call'
        )
        
        iv_result = self.iv_calculator.calculate_implied_volatility(
            market_price=bs_result.option_price,
            stock_price=90.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=0.5,
            option_type='call'
        )
        
        self.assertTrue(iv_result.converged)
        self.assertAlmostEqual(iv_result.implied_volatility, known_iv, places=2)
    
    def test_short_term_option_iv(self):
        """測試短期期權 IV"""
        known_iv = 0.25
        
        bs_result = self.bs_calculator.calculate_option_price(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=0.1,  # 約 1 個月
            volatility=known_iv,
            option_type='call'
        )
        
        iv_result = self.iv_calculator.calculate_implied_volatility(
            market_price=bs_result.option_price,
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=0.1,
            option_type='call'
        )
        
        self.assertTrue(iv_result.converged)
        self.assertAlmostEqual(iv_result.implied_volatility, known_iv, places=2)
    
    def test_long_term_option_iv(self):
        """測試長期期權 IV"""
        known_iv = 0.20
        
        bs_result = self.bs_calculator.calculate_option_price(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=2.0,  # 2 年
            volatility=known_iv,
            option_type='call'
        )
        
        iv_result = self.iv_calculator.calculate_implied_volatility(
            market_price=bs_result.option_price,
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=2.0,
            option_type='call'
        )
        
        self.assertTrue(iv_result.converged)
        self.assertAlmostEqual(iv_result.implied_volatility, known_iv, places=3)
    
    def test_result_type(self):
        """測試結果類型"""
        bs_result = self.bs_calculator.calculate_option_price(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.25,
            option_type='call'
        )
        
        iv_result = self.iv_calculator.calculate_implied_volatility(
            market_price=bs_result.option_price,
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            option_type='call'
        )
        
        # 驗證結果類型
        self.assertIsInstance(iv_result, IVResult)
        self.assertIsNotNone(iv_result.implied_volatility)
        self.assertIsNotNone(iv_result.iterations)
        self.assertIsNotNone(iv_result.converged)
    
    def test_to_dict_method(self):
        """測試 to_dict() 方法"""
        bs_result = self.bs_calculator.calculate_option_price(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.25,
            option_type='call'
        )
        
        iv_result = self.iv_calculator.calculate_implied_volatility(
            market_price=bs_result.option_price,
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            option_type='call'
        )
        
        result_dict = iv_result.to_dict()
        
        # 驗證字典包含所有必要字段
        required_fields = [
            'market_price', 'implied_volatility', 'implied_volatility_percent',
            'iterations', 'converged', 'bs_price', 'price_difference',
            'initial_guess', 'calculation_date'
        ]
        
        for field in required_fields:
            self.assertIn(field, result_dict, msg=f"字典應該包含 {field} 字段")
    
    def test_invalid_market_price(self):
        """測試無效市場價格"""
        with self.assertRaises(ValueError):
            self.iv_calculator.calculate_implied_volatility(
                market_price=-10.0,  # 負價格
                stock_price=100.0,
                strike_price=100.0,
                risk_free_rate=0.05,
                time_to_expiration=1.0,
                option_type='call'
            )
    
    def test_invalid_time_to_expiration(self):
        """測試無效到期時間"""
        with self.assertRaises(ValueError):
            self.iv_calculator.calculate_implied_volatility(
                market_price=10.0,
                stock_price=100.0,
                strike_price=100.0,
                risk_free_rate=0.05,
                time_to_expiration=-1.0,  # 負時間
                option_type='call'
            )
    
    def test_price_difference_accuracy(self):
        """測試價格差異準確性"""
        known_iv = 0.25
        
        bs_result = self.bs_calculator.calculate_option_price(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=known_iv,
            option_type='call'
        )
        
        iv_result = self.iv_calculator.calculate_implied_volatility(
            market_price=bs_result.option_price,
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            option_type='call'
        )
        
        # 價格差異應該非常小
        self.assertLess(
            abs(iv_result.price_difference),
            0.001,
            msg="價格差異應該 < $0.001"
        )


def run_tests():
    """運行所有測試"""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestImpliedVolatilityCalculator)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
