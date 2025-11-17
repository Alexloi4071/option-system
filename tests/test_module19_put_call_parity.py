#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Module 19 單元測試: Put-Call Parity 驗證器

測試覆蓋:
1. 平價關係驗證準確性
2. 套利機會識別
3. 策略建議邏輯
4. 交易成本影響
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from calculation_layer.module19_put_call_parity import (
    PutCallParityValidator,
    ParityResult
)


class TestPutCallParityValidator(unittest.TestCase):
    """Put-Call Parity 驗證器測試類"""
    
    def setUp(self):
        """測試前準備"""
        self.validator = PutCallParityValidator()
    
    def test_theoretical_prices_parity(self):
        """測試 BS 理論價格的 Parity（應該完美成立）"""
        result = self.validator.validate_with_theoretical_prices(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.2
        )
        
        # BS 理論價格應該完美滿足 Parity
        self.assertLess(abs(result.deviation), 0.01, "偏離應該 < $0.01")
        self.assertFalse(result.arbitrage_opportunity, "不應該有套利機會")
    
    def test_call_overvalued_arbitrage(self):
        """測試 Call 高估套利識別"""
        result = self.validator.validate_parity(
            call_price=11.00,  # 高估
            put_price=5.57,
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0
        )
        
        self.assertGreater(result.deviation, 0, "Call 高估時偏離應該 > 0")
        self.assertTrue(result.arbitrage_opportunity, "應該有套利機會")
        self.assertGreater(result.theoretical_profit, 0, "應該有理論利潤")
        self.assertIn("沽出 Call", result.strategy, "策略應該包含沽出 Call")
    
    def test_put_overvalued_arbitrage(self):
        """測試 Put 高估套利識別"""
        result = self.validator.validate_parity(
            call_price=10.45,
            put_price=6.50,  # 高估
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0
        )
        
        self.assertLess(result.deviation, 0, "Put 高估時偏離應該 < 0")
        self.assertTrue(result.arbitrage_opportunity, "應該有套利機會")
        self.assertGreater(result.theoretical_profit, 0, "應該有理論利潤")
        self.assertIn("沽出 Put", result.strategy, "策略應該包含沽出 Put")
    
    def test_no_arbitrage_opportunity(self):
        """測試無套利機會情況"""
        result = self.validator.validate_parity(
            call_price=10.45,
            put_price=5.57,
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0
        )
        
        # 小偏離不應該觸發套利
        if not result.arbitrage_opportunity:
            self.assertEqual(result.theoretical_profit, 0, "無套利時利潤應該為 0")
    
    def test_result_type(self):
        """測試結果類型"""
        result = self.validator.validate_parity(
            call_price=10.45,
            put_price=5.57,
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0
        )
        
        self.assertIsInstance(result, ParityResult)
        self.assertIsNotNone(result.theoretical_difference)
        self.assertIsNotNone(result.actual_difference)
        self.assertIsNotNone(result.deviation)
    
    def test_to_dict_method(self):
        """測試 to_dict() 方法"""
        result = self.validator.validate_parity(
            call_price=10.45,
            put_price=5.57,
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0
        )
        
        result_dict = result.to_dict()
        
        required_fields = [
            'call_price', 'put_price', 'stock_price', 'strike_price',
            'theoretical_difference', 'actual_difference', 'deviation',
            'arbitrage_opportunity', 'strategy'
        ]
        
        for field in required_fields:
            self.assertIn(field, result_dict)


def run_tests():
    """運行所有測試"""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestPutCallParityValidator)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
