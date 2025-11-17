# tests/test_stage1.py
"""
第1階段單元測試 - 數據層和模塊1測試
"""

import unittest
import sys
import os

# 添加父目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from calculation_layer.module1_support_resistance import SupportResistanceCalculator
from data_layer.data_validator import DataValidator
from utils.trading_days import TradingDaysCalculator


class TestSupportResistanceCalculator(unittest.TestCase):
    """支持/阻力位計算測試"""
    
    def setUp(self):
        """測試前設置"""
        self.calculator = SupportResistanceCalculator()
        self.default_days = 30
        self.default_z = 1.0
    
    def test_basic_calculation(self):
        """基本計算測試"""
        result = self.calculator.calculate(
            stock_price=180.0,
            implied_volatility=22.0,
            days_to_expiration=self.default_days,
            z_score=self.default_z
        )
        
        # 驗證計算正確性
        self.assertAlmostEqual(result.stock_price, 180.0)
        self.assertAlmostEqual(result.implied_volatility, 22.0)
        self.assertEqual(result.days_to_expiration, self.default_days)
        self.assertAlmostEqual(result.z_score, self.default_z)
        self.assertGreater(result.resistance_level, result.stock_price)
        self.assertLess(result.support_level, result.stock_price)
    
    def test_support_resistance_symmetry(self):
        """對稱性測試"""
        result = self.calculator.calculate(
            stock_price=100.0,
            implied_volatility=20.0,
            days_to_expiration=self.default_days,
            z_score=self.default_z
        )
        
        # 支持位和阻力位應該相對於股價對稱
        diff_up = result.resistance_level - result.stock_price
        diff_down = result.stock_price - result.support_level
        
        self.assertAlmostEqual(diff_up, diff_down, places=2)
    
    def test_high_volatility(self):
        """高波動率測試"""
        result = self.calculator.calculate(
            stock_price=100.0,
            implied_volatility=50.0,
            days_to_expiration=self.default_days,
            z_score=self.default_z
        )
        
        # 高波動率應該有更大的波幅
        self.assertGreater(result.volatility_percentage, 10.0)
    
    def test_low_volatility(self):
        """低波動率測試"""
        result = self.calculator.calculate(
            stock_price=100.0,
            implied_volatility=10.0,
            days_to_expiration=self.default_days,
            z_score=self.default_z
        )
        
        # 低波動率應該有較小的波幅
        self.assertLess(result.volatility_percentage, 5.0)
    
    def test_iv_sensitivity(self):
        """IV敏感度測試"""
        result_low = self.calculator.calculate(
            stock_price=100.0,
            implied_volatility=10.0,
            days_to_expiration=self.default_days,
            z_score=self.default_z
        )
        
        result_high = self.calculator.calculate(
            stock_price=100.0,
            implied_volatility=30.0,
            days_to_expiration=self.default_days,
            z_score=self.default_z
        )
        
        # 高IV的波幅應該是低IV波幅的3倍
        ratio = result_high.volatility_percentage / result_low.volatility_percentage
        self.assertAlmostEqual(ratio, 3.0, places=1)
    
    def test_invalid_stock_price(self):
        """無效股價測試"""
        with self.assertRaises(ValueError):
            self.calculator.calculate(
                stock_price=-100.0,
                implied_volatility=22.0,
                days_to_expiration=self.default_days,
                z_score=self.default_z
            )
    
    def test_invalid_iv(self):
        """無效IV測試"""
        with self.assertRaises(ValueError):
            self.calculator.calculate(
                stock_price=100.0,
                implied_volatility=-10.0,
                days_to_expiration=self.default_days,
                z_score=self.default_z
            )

    def test_invalid_days_to_expiration(self):
        """無效到期天數測試"""
        with self.assertRaises(ValueError):
            self.calculator.calculate(
                stock_price=100.0,
                implied_volatility=20.0,
                days_to_expiration=0,
                z_score=self.default_z
            )

    def test_invalid_z_score(self):
        """無效Z值測試"""
        with self.assertRaises(ValueError):
            self.calculator.calculate(
                stock_price=100.0,
                implied_volatility=20.0,
                days_to_expiration=self.default_days,
                z_score=-1.0
            )
    
    def test_formula_accuracy(self):
        """公式準確性測試"""
        stock_price = 180.50
        iv = 22.0
        days = 45
        z_score = 1.28
        
        result = self.calculator.calculate(
            stock_price=stock_price,
            implied_volatility=iv,
            days_to_expiration=days,
            z_score=z_score
        )
        
        # 手動驗證計算
        time_factor = (days / 365.0) ** 0.5
        expected_price_move = stock_price * (iv / 100) * time_factor * z_score
        expected_support = stock_price - expected_price_move
        expected_resistance = stock_price + expected_price_move
        
        self.assertAlmostEqual(result.price_move, expected_price_move, places=2)
        self.assertAlmostEqual(result.support_level, expected_support, places=2)
        self.assertAlmostEqual(result.resistance_level, expected_resistance, places=2)
        self.assertEqual(result.confidence_level, "80% (1.28 σ)")


class TestDataValidator(unittest.TestCase):
    """數據驗證測試"""
    
    def setUp(self):
        """測試前設置"""
        self.validator = DataValidator()
    
    def test_valid_stock_data(self):
        """有效數據測試"""
        test_data = {
            'ticker': 'AAPL',
            'current_price': 180.50,
            'implied_volatility': 22.0,
            'eps': 6.05,
            'risk_free_rate': 4.50
        }
        
        is_valid = self.validator.validate_stock_data(test_data)
        self.assertTrue(is_valid)
    
    def test_missing_required_field(self):
        """缺少必需字段測試"""
        test_data = {
            'ticker': 'AAPL',
            'current_price': 180.50,
            # 缺少 implied_volatility
            'eps': 6.05,
            'risk_free_rate': 4.50
        }
        
        is_valid = self.validator.validate_stock_data(test_data)
        self.assertFalse(is_valid)


class TestTradingDaysCalculator(unittest.TestCase):
    """交易日計算測試"""

    def setUp(self):
        self.calculator = TradingDaysCalculator(exchange='NYSE')

    def test_trading_days_basic(self):
        """基本交易日計算"""
        days = self.calculator.calculate_trading_days('2024-01-02', '2024-01-10')
        self.assertGreater(days, 0)

    def test_calendar_fallback(self):
        """週末區間應回傳非負"""
        days = self.calculator.calculate_trading_days('2024-01-06', '2024-01-07')
        self.assertGreaterEqual(days, 0)
    
    def test_invalid_stock_price(self):
        """無效股價測試"""
        test_data = {
            'ticker': 'AAPL',
            'current_price': 0,  # 無效
            'implied_volatility': 22.0,
            'eps': 6.05,
            'risk_free_rate': 4.50
        }
        
        is_valid = self.validator.validate_stock_data(test_data)
        self.assertFalse(is_valid)
    
    def test_invalid_iv(self):
        """無效IV測試"""
        test_data = {
            'ticker': 'AAPL',
            'current_price': 180.50,
            'implied_volatility': -10.0,  # 無效
            'eps': 6.05,
            'risk_free_rate': 4.50
        }
        
        is_valid = self.validator.validate_stock_data(test_data)
        self.assertFalse(is_valid)


if __name__ == '__main__':
    # 運行所有測試
    unittest.main(verbosity=2)
