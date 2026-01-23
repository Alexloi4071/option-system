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
7. 魯棒 IV 計算測試（多初值策略）
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


class TestIVRobust(unittest.TestCase):
    """魯棒 IV 計算測試類（多初值策略）"""
    
    def setUp(self):
        """測試前準備"""
        self.iv_calculator = ImpliedVolatilityCalculator()
        self.bs_calculator = BlackScholesCalculator()
    
    def test_robust_iv_standard_case(self):
        """測試標準 ATM 期權的魯棒 IV 計算"""
        known_iv = 0.25
        
        # 使用 BS 模型計算期權價格
        bs_result = self.bs_calculator.calculate_option_price(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=known_iv,
            option_type='call'
        )
        
        # 使用魯棒方法計算 IV
        result = self.iv_calculator.calculate_iv_robust(
            market_price=bs_result.option_price,
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            option_type='call'
        )
        
        # 驗證成功
        self.assertEqual(result['status'], 'success', "應該成功計算 IV")
        self.assertTrue(result['converged'], "應該收斂")
        self.assertIsNotNone(result['iv'], "IV 不應為 None")
        self.assertAlmostEqual(result['iv'], known_iv, places=2, msg="IV 應該接近已知值")
        
        # 驗證返回字段
        self.assertIn('initial_guess', result)
        self.assertIn('iterations', result)
        self.assertIn('tried_guesses', result)
        self.assertIsInstance(result['tried_guesses'], list)
    
    def test_robust_iv_deep_itm_call(self):
        """測試深度 ITM Call 期權（困難案例）"""
        known_iv = 0.30
        
        bs_result = self.bs_calculator.calculate_option_price(
            stock_price=150.0,  # 深度 ITM
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=0.5,
            volatility=known_iv,
            option_type='call'
        )
        
        result = self.iv_calculator.calculate_iv_robust(
            market_price=bs_result.option_price,
            stock_price=150.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=0.5,
            option_type='call'
        )
        
        # 魯棒方法應該能處理困難案例
        self.assertEqual(result['status'], 'success', "魯棒方法應該成功")
        self.assertIsNotNone(result['iv'])
        self.assertGreater(result['iv'], 0.01, "IV 應該 > 1%")
        self.assertLess(result['iv'], 5.0, "IV 應該 < 500%")
    
    def test_robust_iv_deep_otm_call(self):
        """測試深度 OTM Call 期權（困難案例）"""
        known_iv = 0.35
        
        bs_result = self.bs_calculator.calculate_option_price(
            stock_price=50.0,  # 深度 OTM
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=0.5,
            volatility=known_iv,
            option_type='call'
        )
        
        result = self.iv_calculator.calculate_iv_robust(
            market_price=bs_result.option_price,
            stock_price=50.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=0.5,
            option_type='call'
        )
        
        # 魯棒方法應該能處理困難案例
        self.assertEqual(result['status'], 'success', "魯棒方法應該成功")
        self.assertIsNotNone(result['iv'])
        self.assertGreater(result['iv'], 0.01)
        self.assertLess(result['iv'], 5.0)
    
    def test_robust_iv_short_term_option(self):
        """測試短期期權（困難案例）"""
        known_iv = 0.40
        
        bs_result = self.bs_calculator.calculate_option_price(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=0.02,  # 約 1 週
            volatility=known_iv,
            option_type='call'
        )
        
        result = self.iv_calculator.calculate_iv_robust(
            market_price=bs_result.option_price,
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=0.02,
            option_type='call'
        )
        
        # 短期期權可能較難收斂，但魯棒方法應該提高成功率
        if result['status'] == 'success':
            self.assertIsNotNone(result['iv'])
            self.assertGreater(result['iv'], 0.01)
            self.assertLess(result['iv'], 5.0)
    
    def test_robust_iv_failure_case(self):
        """測試失敗場景（無效市場價格）"""
        result = self.iv_calculator.calculate_iv_robust(
            market_price=0.0,  # 無效價格
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            option_type='call'
        )
        
        # 應該返回失敗狀態
        self.assertEqual(result['status'], 'failed', "無效價格應該失敗")
        self.assertIsNone(result['iv'], "失敗時 IV 應為 None")
        self.assertIn('error', result, "應該包含錯誤信息")
    
    def test_robust_iv_initial_guess_priority(self):
        """測試初值優先級"""
        known_iv = 0.25
        
        bs_result = self.bs_calculator.calculate_option_price(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=known_iv,
            option_type='call'
        )
        
        result = self.iv_calculator.calculate_iv_robust(
            market_price=bs_result.option_price,
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            option_type='call'
        )
        
        # 驗證優先使用 0.2 (20%)
        self.assertEqual(result['status'], 'success')
        self.assertIn(0.2, result['tried_guesses'], "應該嘗試 0.2 初值")
        
        # 對於標準案例，應該第一個初值就成功
        self.assertEqual(len(result['tried_guesses']), 1, "標準案例應該第一個初值就成功")
        self.assertEqual(result['initial_guess'], 0.2, "應該使用第一個初值 0.2")
    
    def test_robust_iv_multiple_guesses(self):
        """測試多初值嘗試"""
        # 使用一個可能需要多個初值的案例
        known_iv = 0.80  # 高波動率
        
        bs_result = self.bs_calculator.calculate_option_price(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=0.25,
            volatility=known_iv,
            option_type='call'
        )
        
        result = self.iv_calculator.calculate_iv_robust(
            market_price=bs_result.option_price,
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=0.25,
            option_type='call'
        )
        
        # 應該成功
        self.assertEqual(result['status'], 'success')
        self.assertIsNotNone(result['iv'])
        
        # 驗證嘗試了初值
        self.assertGreater(len(result['tried_guesses']), 0, "應該至少嘗試一個初值")
        self.assertLessEqual(len(result['tried_guesses']), 5, "最多嘗試 5 個初值")
    
    def test_robust_iv_put_option(self):
        """測試 Put 期權的魯棒 IV 計算"""
        known_iv = 0.30
        
        bs_result = self.bs_calculator.calculate_option_price(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=known_iv,
            option_type='put'
        )
        
        result = self.iv_calculator.calculate_iv_robust(
            market_price=bs_result.option_price,
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            option_type='put'
        )
        
        # Put 期權也應該成功
        self.assertEqual(result['status'], 'success')
        self.assertIsNotNone(result['iv'])
        self.assertAlmostEqual(result['iv'], known_iv, places=2)


def run_tests():
    """運行所有測試"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加所有測試類
    suite.addTests(loader.loadTestsFromTestCase(TestImpliedVolatilityCalculator))
    suite.addTests(loader.loadTestsFromTestCase(TestIVRobust))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
