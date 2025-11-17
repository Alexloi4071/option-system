#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Module 15 單元測試: Black-Scholes 期權定價模型

測試覆蓋:
1. Call 期權定價準確性
2. Put 期權定價準確性
3. Put-Call Parity 關係驗證
4. 邊界條件測試（ATM, ITM, OTM）
5. 輸入驗證測試
6. 標準正態分佈函數測試
7. d1, d2 計算測試
8. 特殊情況處理測試
"""

import unittest
import sys
import os
import math

# 添加項目根目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from calculation_layer.module15_black_scholes import (
    BlackScholesCalculator,
    BSPricingResult
)


class TestBlackScholesCalculator(unittest.TestCase):
    """Black-Scholes 計算器測試類"""
    
    def setUp(self):
        """測試前準備"""
        self.calculator = BlackScholesCalculator()
    
    def test_normal_cdf_basic_values(self):
        """測試標準正態累積分佈函數的基本值"""
        # N(0) 應該等於 0.5
        self.assertAlmostEqual(
            BlackScholesCalculator.normal_cdf(0),
            0.5,
            places=6,
            msg="N(0) 應該等於 0.5"
        )
        
        # N(1.96) 應該約等於 0.975 (95% 信心度)
        self.assertAlmostEqual(
            BlackScholesCalculator.normal_cdf(1.96),
            0.975,
            places=3,
            msg="N(1.96) 應該約等於 0.975"
        )
        
        # N(-1.96) 應該約等於 0.025
        self.assertAlmostEqual(
            BlackScholesCalculator.normal_cdf(-1.96),
            0.025,
            places=3,
            msg="N(-1.96) 應該約等於 0.025"
        )
        
        # N(2.58) 應該約等於 0.995 (99% 信心度)
        self.assertAlmostEqual(
            BlackScholesCalculator.normal_cdf(2.58),
            0.995,
            places=3,
            msg="N(2.58) 應該約等於 0.995"
        )
    
    def test_normal_pdf_basic_values(self):
        """測試標準正態概率密度函數的基本值"""
        # N'(0) 應該等於 1/√(2π) ≈ 0.3989
        expected = 1 / math.sqrt(2 * math.pi)
        self.assertAlmostEqual(
            BlackScholesCalculator.normal_pdf(0),
            expected,
            places=4,
            msg="N'(0) 應該等於 1/√(2π)"
        )
        
        # N'(x) 應該總是正數
        self.assertGreater(
            BlackScholesCalculator.normal_pdf(1),
            0,
            msg="N'(1) 應該大於 0"
        )
        
        self.assertGreater(
            BlackScholesCalculator.normal_pdf(-1),
            0,
            msg="N'(-1) 應該大於 0"
        )
    
    def test_calculate_d1_d2_standard_case(self):
        """測試 d1 和 d2 計算 - 標準情況"""
        d1, d2 = self.calculator.calculate_d1_d2(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.2
        )
        
        # 驗證 d1 和 d2 的關係: d2 = d1 - σ√T
        expected_d2 = d1 - 0.2 * math.sqrt(1.0)
        self.assertAlmostEqual(
            d2,
            expected_d2,
            places=6,
            msg="d2 應該等於 d1 - σ√T"
        )
        
        # 驗證 d1 的計算
        # d1 = [ln(S/K) + (r + σ²/2)×T] / (σ×√T)
        expected_d1 = (math.log(100.0/100.0) + (0.05 + 0.5 * 0.2**2) * 1.0) / (0.2 * math.sqrt(1.0))
        self.assertAlmostEqual(
            d1,
            expected_d1,
            places=6,
            msg="d1 計算應該正確"
        )
    
    def test_atm_call_option_pricing(self):
        """測試 ATM Call 期權定價"""
        result = self.calculator.calculate_option_price(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.2,
            option_type='call'
        )
        
        # 驗證結果類型
        self.assertIsInstance(result, BSPricingResult)
        
        # 驗證期權價格為正
        self.assertGreater(result.option_price, 0, msg="Call 期權價格應該大於 0")
        
        # ATM Call 期權價格應該在合理範圍內 (約 8-12 美元)
        self.assertGreater(result.option_price, 8, msg="ATM Call 價格應該 > 8")
        self.assertLess(result.option_price, 12, msg="ATM Call 價格應該 < 12")
        
        # 驗證 d1 和 d2 已計算
        self.assertIsNotNone(result.d1)
        self.assertIsNotNone(result.d2)
    
    def test_atm_put_option_pricing(self):
        """測試 ATM Put 期權定價"""
        result = self.calculator.calculate_option_price(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.2,
            option_type='put'
        )
        
        # 驗證期權價格為正
        self.assertGreater(result.option_price, 0, msg="Put 期權價格應該大於 0")
        
        # ATM Put 期權價格應該在合理範圍內 (約 4-8 美元)
        self.assertGreater(result.option_price, 4, msg="ATM Put 價格應該 > 4")
        self.assertLess(result.option_price, 8, msg="ATM Put 價格應該 < 8")
    
    def test_put_call_parity(self):
        """測試 Put-Call Parity 關係"""
        # 計算 Call 和 Put 期權
        call_result = self.calculator.calculate_option_price(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.2,
            option_type='call'
        )
        
        put_result = self.calculator.calculate_option_price(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.2,
            option_type='put'
        )
        
        # Put-Call Parity: C - P = S - K×e^(-r×T)
        parity_left = call_result.option_price - put_result.option_price
        parity_right = 100.0 - 100.0 * math.exp(-0.05 * 1.0)
        
        self.assertAlmostEqual(
            parity_left,
            parity_right,
            places=4,
            msg="Put-Call Parity 應該成立: C - P = S - K×e^(-r×T)"
        )
    
    def test_itm_call_option(self):
        """測試 ITM (In-The-Money) Call 期權"""
        result = self.calculator.calculate_option_price(
            stock_price=110.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=0.5,
            volatility=0.25,
            option_type='call'
        )
        
        # ITM Call 期權價格應該大於內在價值
        intrinsic_value = max(110.0 - 100.0, 0)
        self.assertGreater(
            result.option_price,
            intrinsic_value,
            msg="ITM Call 價格應該大於內在價值"
        )
        
        # 時間價值應該為正
        time_value = result.option_price - intrinsic_value
        self.assertGreater(time_value, 0, msg="時間價值應該大於 0")
    
    def test_otm_call_option(self):
        """測試 OTM (Out-of-The-Money) Call 期權"""
        result = self.calculator.calculate_option_price(
            stock_price=90.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=0.5,
            volatility=0.25,
            option_type='call'
        )
        
        # OTM Call 期權價格應該小於 ATM
        # 但仍然為正（有時間價值）
        self.assertGreater(result.option_price, 0, msg="OTM Call 價格應該大於 0")
        self.assertLess(result.option_price, 10, msg="OTM Call 價格應該較小")
    
    def test_itm_put_option(self):
        """測試 ITM Put 期權"""
        result = self.calculator.calculate_option_price(
            stock_price=90.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=0.5,
            volatility=0.25,
            option_type='put'
        )
        
        # ITM Put 期權價格應該大於內在價值
        intrinsic_value = max(100.0 - 90.0, 0)
        self.assertGreater(
            result.option_price,
            intrinsic_value,
            msg="ITM Put 價格應該大於內在價值"
        )
    
    def test_otm_put_option(self):
        """測試 OTM Put 期權"""
        result = self.calculator.calculate_option_price(
            stock_price=110.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=0.5,
            volatility=0.25,
            option_type='put'
        )
        
        # OTM Put 期權價格應該為正但較小
        self.assertGreater(result.option_price, 0, msg="OTM Put 價格應該大於 0")
        self.assertLess(result.option_price, 5, msg="OTM Put 價格應該較小")
    
    def test_input_validation_negative_stock_price(self):
        """測試輸入驗證 - 負股價"""
        with self.assertRaises(ValueError):
            self.calculator.calculate_option_price(
                stock_price=-100.0,
                strike_price=100.0,
                risk_free_rate=0.05,
                time_to_expiration=1.0,
                volatility=0.2,
                option_type='call'
            )
    
    def test_input_validation_negative_strike(self):
        """測試輸入驗證 - 負行使價"""
        with self.assertRaises(ValueError):
            self.calculator.calculate_option_price(
                stock_price=100.0,
                strike_price=-100.0,
                risk_free_rate=0.05,
                time_to_expiration=1.0,
                volatility=0.2,
                option_type='call'
            )
    
    def test_input_validation_negative_time(self):
        """測試輸入驗證 - 負到期時間"""
        with self.assertRaises(ValueError):
            self.calculator.calculate_option_price(
                stock_price=100.0,
                strike_price=100.0,
                risk_free_rate=0.05,
                time_to_expiration=-1.0,
                volatility=0.2,
                option_type='call'
            )
    
    def test_input_validation_negative_volatility(self):
        """測試輸入驗證 - 負波動率"""
        with self.assertRaises(ValueError):
            self.calculator.calculate_option_price(
                stock_price=100.0,
                strike_price=100.0,
                risk_free_rate=0.05,
                time_to_expiration=1.0,
                volatility=-0.2,
                option_type='call'
            )
    
    def test_input_validation_invalid_option_type(self):
        """測試輸入驗證 - 無效期權類型"""
        with self.assertRaises(ValueError):
            self.calculator.calculate_option_price(
                stock_price=100.0,
                strike_price=100.0,
                risk_free_rate=0.05,
                time_to_expiration=1.0,
                volatility=0.2,
                option_type='invalid'
            )
    
    def test_input_validation_extreme_volatility(self):
        """測試輸入驗證 - 極端波動率"""
        with self.assertRaises(ValueError):
            self.calculator.calculate_option_price(
                stock_price=100.0,
                strike_price=100.0,
                risk_free_rate=0.05,
                time_to_expiration=1.0,
                volatility=10.0,  # 1000% 波動率
                option_type='call'
            )
    
    def test_zero_time_to_expiration(self):
        """測試特殊情況 - 到期時間為0"""
        # 當到期時間為0時，期權價值應該等於內在價值
        # 但由於數值穩定性，我們使用極小值
        result = self.calculator.calculate_option_price(
            stock_price=110.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=0.0001,  # 接近0
            volatility=0.2,
            option_type='call'
        )
        
        intrinsic_value = max(110.0 - 100.0, 0)
        # 期權價格應該接近內在價值
        self.assertAlmostEqual(
            result.option_price,
            intrinsic_value,
            places=0,
            msg="到期時期權價格應該接近內在價值"
        )
    
    def test_high_volatility_effect(self):
        """測試高波動率的影響"""
        # 低波動率
        result_low_vol = self.calculator.calculate_option_price(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.1,
            option_type='call'
        )
        
        # 高波動率
        result_high_vol = self.calculator.calculate_option_price(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.4,
            option_type='call'
        )
        
        # 高波動率應該導致更高的期權價格
        self.assertGreater(
            result_high_vol.option_price,
            result_low_vol.option_price,
            msg="高波動率應該導致更高的期權價格"
        )
    
    def test_time_decay_effect(self):
        """測試時間衰減效應"""
        # 長期期權
        result_long_term = self.calculator.calculate_option_price(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.2,
            option_type='call'
        )
        
        # 短期期權
        result_short_term = self.calculator.calculate_option_price(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=0.25,
            volatility=0.2,
            option_type='call'
        )
        
        # 長期期權應該更貴（有更多時間價值）
        self.assertGreater(
            result_long_term.option_price,
            result_short_term.option_price,
            msg="長期期權應該比短期期權更貴"
        )
    
    def test_to_dict_method(self):
        """測試 to_dict() 方法"""
        result = self.calculator.calculate_option_price(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.2,
            option_type='call'
        )
        
        result_dict = result.to_dict()
        
        # 驗證字典包含所有必要字段
        required_fields = [
            'stock_price', 'strike_price', 'risk_free_rate',
            'time_to_expiration', 'volatility', 'option_type',
            'd1', 'd2', 'option_price', 'calculation_date', 'model'
        ]
        
        for field in required_fields:
            self.assertIn(field, result_dict, msg=f"字典應該包含 {field} 字段")
        
        # 驗證模型名稱
        self.assertEqual(result_dict['model'], 'Black-Scholes')


def run_tests():
    """運行所有測試"""
    # 創建測試套件
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestBlackScholesCalculator)
    
    # 運行測試
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 返回測試結果
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
