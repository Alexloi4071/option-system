#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
集成測試: Module 17 → Module 15 → Module 3 集成

測試覆蓋:
1. Module 17 → Module 15 集成: ATM IV 正確傳遞到 BS 計算
2. Module 17 → Module 15 → Module 3 集成: 套戥水位使用正確的 IV 來源
3. IV 不一致警告的觸發

**Feature: option-calculation-fixes**
**Validates: Requirements 3.1, 3.2, 3.3, 4.1, 4.2, 4.3, 4.4**
"""

import sys
import os
import unittest

# 添加項目根目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from calculation_layer.module15_black_scholes import BlackScholesCalculator
from calculation_layer.module16_greeks import GreeksCalculator
from calculation_layer.module17_implied_volatility import ImpliedVolatilityCalculator
from calculation_layer.module22_optimal_strike import OptimalStrikeCalculator
from calculation_layer.module23_dynamic_iv_threshold import DynamicIVThresholdCalculator
from calculation_layer.module3_arbitrage_spread import ArbitrageSpreadCalculator


class TestModule17ToModule15Integration(unittest.TestCase):
    """
    測試 Module 17 → Module 15 集成
    
    驗證:
    - ATM IV 正確傳遞到 BS 計算
    - ATM IV 不可用時的回退邏輯
    
    **Validates: Requirements 3.1, 3.2, 3.3**
    """
    
    def setUp(self):
        """測試前準備"""
        self.bs_calculator = BlackScholesCalculator()
        self.iv_calculator = ImpliedVolatilityCalculator()
    
    def test_atm_iv_correctly_passed_to_bs_calculation(self):
        """
        測試 ATM IV 正確傳遞到 BS 計算
        
        **Validates: Requirements 3.1, 3.3**
        """
        # 模擬期權鏈數據
        option_chain = {
            'calls': [
                {'strike': 195.0, 'impliedVolatility': 0.28},
                {'strike': 200.0, 'impliedVolatility': 0.25},  # ATM
                {'strike': 205.0, 'impliedVolatility': 0.27}
            ],
            'puts': [
                {'strike': 195.0, 'impliedVolatility': 0.29},
                {'strike': 200.0, 'impliedVolatility': 0.26},  # ATM
                {'strike': 205.0, 'impliedVolatility': 0.28}
            ]
        }
        current_price = 200.0
        
        # Step 1: 從 Module 17 提取 ATM IV
        atm_iv_result = self.iv_calculator.extract_atm_iv_from_chain(
            option_chain=option_chain,
            current_price=current_price,
            option_type='call'
        )
        
        self.assertIsNotNone(atm_iv_result, "應該成功提取 ATM IV")
        self.assertAlmostEqual(atm_iv_result.atm_iv, 0.25, places=2)
        
        # Step 2: 將 ATM IV 傳遞到 Module 15 計算
        market_iv = 0.30  # 不同於 ATM IV
        
        bs_result = self.bs_calculator.calculate_option_price_with_atm_iv(
            stock_price=current_price,
            strike_price=200.0,
            risk_free_rate=0.05,
            time_to_expiration=0.077,  # 約 28 天
            market_iv=market_iv,
            atm_iv=atm_iv_result.atm_iv,
            option_type='call'
        )
        
        # 驗證使用了 ATM IV
        self.assertEqual(bs_result.iv_source, 'ATM IV (Module 17)')
        self.assertAlmostEqual(bs_result.volatility, atm_iv_result.atm_iv, places=4)
    
    def test_fallback_to_market_iv_when_atm_iv_unavailable(self):
        """
        測試 ATM IV 不可用時的回退邏輯
        
        **Validates: Requirements 3.2**
        """
        # 空期權鏈
        option_chain = {'calls': [], 'puts': []}
        current_price = 200.0
        
        # Step 1: 嘗試從空期權鏈提取 ATM IV
        atm_iv_result = self.iv_calculator.extract_atm_iv_from_chain(
            option_chain=option_chain,
            current_price=current_price,
            option_type='call'
        )
        
        self.assertIsNone(atm_iv_result, "空期權鏈應該返回 None")
        
        # Step 2: 使用 None ATM IV 調用 Module 15
        market_iv = 0.30
        
        bs_result = self.bs_calculator.calculate_option_price_with_atm_iv(
            stock_price=current_price,
            strike_price=200.0,
            risk_free_rate=0.05,
            time_to_expiration=0.077,
            market_iv=market_iv,
            atm_iv=None,  # ATM IV 不可用
            option_type='call'
        )
        
        # 驗證回退到 Market IV
        self.assertEqual(bs_result.iv_source, 'Market IV (fallback)')
        self.assertAlmostEqual(bs_result.volatility, market_iv, places=4)
    
    def test_fallback_when_atm_iv_is_zero(self):
        """
        測試 ATM IV 為零時的回退邏輯
        
        **Validates: Requirements 3.2**
        """
        market_iv = 0.30
        
        bs_result = self.bs_calculator.calculate_option_price_with_atm_iv(
            stock_price=200.0,
            strike_price=200.0,
            risk_free_rate=0.05,
            time_to_expiration=0.077,
            market_iv=market_iv,
            atm_iv=0.0,  # 無效的 ATM IV
            option_type='call'
        )
        
        # 驗證回退到 Market IV
        self.assertEqual(bs_result.iv_source, 'Market IV (fallback)')
        self.assertAlmostEqual(bs_result.volatility, market_iv, places=4)
    
    def test_atm_iv_extraction_from_puts(self):
        """
        測試從 Put 期權提取 ATM IV
        
        **Validates: Requirements 3.1**
        """
        option_chain = {
            'calls': [],  # 無 Call 數據
            'puts': [
                {'strike': 195.0, 'impliedVolatility': 0.29},
                {'strike': 200.0, 'impliedVolatility': 0.26},  # ATM
                {'strike': 205.0, 'impliedVolatility': 0.28}
            ]
        }
        current_price = 200.0
        
        # 優先使用 Call，但 Call 為空，應該回退到 Put
        atm_iv_result = self.iv_calculator.extract_atm_iv_from_chain(
            option_chain=option_chain,
            current_price=current_price,
            option_type='call'
        )
        
        self.assertIsNotNone(atm_iv_result)
        self.assertEqual(atm_iv_result.option_type, 'put')
        self.assertAlmostEqual(atm_iv_result.atm_iv, 0.26, places=2)
    
    def test_iv_source_correctly_labeled_in_result(self):
        """
        測試 IV 來源在結果中正確標註
        
        **Validates: Requirements 3.3**
        """
        # 測試使用 ATM IV
        result_with_atm = self.bs_calculator.calculate_option_price_with_atm_iv(
            stock_price=200.0,
            strike_price=200.0,
            risk_free_rate=0.05,
            time_to_expiration=0.077,
            market_iv=0.30,
            atm_iv=0.25,
            option_type='call'
        )
        self.assertEqual(result_with_atm.iv_source, 'ATM IV (Module 17)')
        
        # 測試回退到 Market IV
        result_fallback = self.bs_calculator.calculate_option_price_with_atm_iv(
            stock_price=200.0,
            strike_price=200.0,
            risk_free_rate=0.05,
            time_to_expiration=0.077,
            market_iv=0.30,
            atm_iv=None,
            option_type='call'
        )
        self.assertEqual(result_fallback.iv_source, 'Market IV (fallback)')


class TestModule17ToModule15ToModule3Integration(unittest.TestCase):
    """
    測試 Module 17 → Module 15 → Module 3 集成
    
    驗證:
    - 套戥水位使用正確的 IV 來源
    - IV 不一致警告的觸發
    
    **Validates: Requirements 4.1, 4.2, 4.3, 4.4**
    """
    
    def setUp(self):
        """測試前準備"""
        self.bs_calculator = BlackScholesCalculator()
        self.iv_calculator = ImpliedVolatilityCalculator()
        self.arbitrage_calculator = ArbitrageSpreadCalculator()
    
    def test_arbitrage_uses_atm_iv_from_module17(self):
        """
        測試套戥水位使用來自 Module 17 的 ATM IV
        
        **Validates: Requirements 4.1, 4.3**
        """
        # 模擬期權鏈數據
        option_chain = {
            'calls': [
                {'strike': 195.0, 'impliedVolatility': 0.28},
                {'strike': 200.0, 'impliedVolatility': 0.25},  # ATM
                {'strike': 205.0, 'impliedVolatility': 0.27}
            ],
            'puts': []
        }
        current_price = 200.0
        market_option_price = 5.50
        
        # Step 1: 從 Module 17 提取 ATM IV
        atm_iv_result = self.iv_calculator.extract_atm_iv_from_chain(
            option_chain=option_chain,
            current_price=current_price,
            option_type='call'
        )
        
        self.assertIsNotNone(atm_iv_result)
        
        # Step 2: 使用 ATM IV 計算套戥水位
        market_iv = 0.35  # 不同於 ATM IV
        
        result = self.arbitrage_calculator.calculate_with_atm_iv(
            market_option_price=market_option_price,
            stock_price=current_price,
            strike_price=200.0,
            risk_free_rate=0.05,
            time_to_expiration=0.077,
            market_iv=market_iv,
            atm_iv=atm_iv_result.atm_iv,
            option_type='call'
        )
        
        # 驗證使用了 ATM IV
        self.assertEqual(result.iv_source, 'ATM IV (Module 17)')
        self.assertAlmostEqual(result.iv_used, atm_iv_result.atm_iv, places=4)
    
    def test_iv_inconsistency_warning_triggered(self):
        """
        測試 IV 不一致警告的觸發
        
        當 ATM IV 與 Market IV 差異超過 30% 時，應該觸發警告
        
        **Validates: Requirements 4.2, 4.4**
        """
        current_price = 200.0
        market_option_price = 5.50
        
        # ATM IV 與 Market IV 差異超過 30%
        atm_iv = 0.20  # 20%
        market_iv = 0.35  # 35%，差異 75%
        
        result = self.arbitrage_calculator.calculate_with_atm_iv(
            market_option_price=market_option_price,
            stock_price=current_price,
            strike_price=200.0,
            risk_free_rate=0.05,
            time_to_expiration=0.077,
            market_iv=market_iv,
            atm_iv=atm_iv,
            option_type='call'
        )
        
        # 驗證警告被觸發
        self.assertIsNotNone(result.iv_warning)
        self.assertIn('ATM IV', result.iv_warning)
        self.assertIn('Market IV', result.iv_warning)
    
    def test_no_warning_when_iv_consistent(self):
        """
        測試 IV 一致時不觸發警告
        
        **Validates: Requirements 4.4**
        """
        current_price = 200.0
        market_option_price = 5.50
        
        # ATM IV 與 Market IV 差異小於 30%
        atm_iv = 0.25  # 25%
        market_iv = 0.28  # 28%，差異 12%
        
        result = self.arbitrage_calculator.calculate_with_atm_iv(
            market_option_price=market_option_price,
            stock_price=current_price,
            strike_price=200.0,
            risk_free_rate=0.05,
            time_to_expiration=0.077,
            market_iv=market_iv,
            atm_iv=atm_iv,
            option_type='call'
        )
        
        # 驗證沒有警告
        self.assertIsNone(result.iv_warning)
    
    def test_arbitrage_fallback_to_market_iv(self):
        """
        測試套戥水位在 ATM IV 不可用時回退到 Market IV
        
        **Validates: Requirements 4.1**
        """
        current_price = 200.0
        market_option_price = 5.50
        market_iv = 0.30
        
        result = self.arbitrage_calculator.calculate_with_atm_iv(
            market_option_price=market_option_price,
            stock_price=current_price,
            strike_price=200.0,
            risk_free_rate=0.05,
            time_to_expiration=0.077,
            market_iv=market_iv,
            atm_iv=None,  # ATM IV 不可用
            option_type='call'
        )
        
        # 驗證回退到 Market IV
        self.assertEqual(result.iv_source, 'Market IV (fallback)')
        self.assertAlmostEqual(result.iv_used, market_iv, places=4)
    
    def test_iv_source_displayed_in_result(self):
        """
        測試 IV 來源在結果中正確顯示
        
        **Validates: Requirements 4.3**
        """
        current_price = 200.0
        market_option_price = 5.50
        
        result = self.arbitrage_calculator.calculate_with_atm_iv(
            market_option_price=market_option_price,
            stock_price=current_price,
            strike_price=200.0,
            risk_free_rate=0.05,
            time_to_expiration=0.077,
            market_iv=0.30,
            atm_iv=0.25,
            option_type='call'
        )
        
        # 驗證結果包含 IV 來源信息
        result_dict = result.to_dict()
        self.assertIn('iv_source', result_dict)
        self.assertIn('iv_used', result_dict)
        self.assertIn('iv_used_percent', result_dict)
    
    def test_large_spread_with_iv_inconsistency_warning(self):
        """
        測試套戥價差超過 5% 且 IV 不一致時的警告
        
        **Validates: Requirements 4.2**
        """
        current_price = 200.0
        
        # 使用較大的 ATM IV 差異來產生較大的價差
        atm_iv = 0.15  # 15%
        market_iv = 0.35  # 35%
        
        # 計算使用 ATM IV 的理論價格
        bs_result = self.bs_calculator.calculate_option_price_with_atm_iv(
            stock_price=current_price,
            strike_price=200.0,
            risk_free_rate=0.05,
            time_to_expiration=0.077,
            market_iv=market_iv,
            atm_iv=atm_iv,
            option_type='call'
        )
        
        # 設置市場價格使價差超過 5%
        theoretical_price = bs_result.option_price
        market_option_price = theoretical_price * 1.10  # 10% 高於理論價
        
        result = self.arbitrage_calculator.calculate_with_atm_iv(
            market_option_price=market_option_price,
            stock_price=current_price,
            strike_price=200.0,
            risk_free_rate=0.05,
            time_to_expiration=0.077,
            market_iv=market_iv,
            atm_iv=atm_iv,
            option_type='call'
        )
        
        # 驗證警告包含 IV 不一致信息
        self.assertIsNotNone(result.iv_warning)


class TestFullIntegrationChain(unittest.TestCase):
    """
    完整集成鏈測試
    
    測試從期權鏈數據到套戥水位計算的完整流程
    """
    
    def setUp(self):
        """測試前準備"""
        self.bs_calculator = BlackScholesCalculator()
        self.iv_calculator = ImpliedVolatilityCalculator()
        self.arbitrage_calculator = ArbitrageSpreadCalculator()
    
    def test_full_integration_chain_with_atm_iv(self):
        """
        測試完整集成鏈: 期權鏈 → ATM IV → BS 定價 → 套戥水位
        
        **Validates: Requirements 3.1, 3.2, 3.3, 4.1, 4.2, 4.3, 4.4**
        """
        # 模擬 GOOG 期權數據
        option_chain = {
            'calls': [
                {'strike': 190.0, 'impliedVolatility': 0.32},
                {'strike': 195.0, 'impliedVolatility': 0.28},
                {'strike': 200.0, 'impliedVolatility': 0.25},  # ATM
                {'strike': 205.0, 'impliedVolatility': 0.27},
                {'strike': 210.0, 'impliedVolatility': 0.30}
            ],
            'puts': [
                {'strike': 190.0, 'impliedVolatility': 0.33},
                {'strike': 195.0, 'impliedVolatility': 0.29},
                {'strike': 200.0, 'impliedVolatility': 0.26},  # ATM
                {'strike': 205.0, 'impliedVolatility': 0.28},
                {'strike': 210.0, 'impliedVolatility': 0.31}
            ]
        }
        current_price = 200.0
        market_option_price = 5.50
        market_iv = 0.30
        
        # Step 1: 從 Module 17 提取 ATM IV
        atm_iv_result = self.iv_calculator.extract_atm_iv_from_chain(
            option_chain=option_chain,
            current_price=current_price,
            option_type='call'
        )
        
        self.assertIsNotNone(atm_iv_result)
        self.assertAlmostEqual(atm_iv_result.atm_iv, 0.25, places=2)
        self.assertEqual(atm_iv_result.option_type, 'call')
        
        # Step 2: 使用 ATM IV 計算 BS 理論價格
        bs_result = self.bs_calculator.calculate_option_price_with_atm_iv(
            stock_price=current_price,
            strike_price=200.0,
            risk_free_rate=0.05,
            time_to_expiration=0.077,
            market_iv=market_iv,
            atm_iv=atm_iv_result.atm_iv,
            option_type='call'
        )
        
        self.assertEqual(bs_result.iv_source, 'ATM IV (Module 17)')
        self.assertGreater(bs_result.option_price, 0)
        
        # Step 3: 計算套戥水位
        arbitrage_result = self.arbitrage_calculator.calculate_with_atm_iv(
            market_option_price=market_option_price,
            stock_price=current_price,
            strike_price=200.0,
            risk_free_rate=0.05,
            time_to_expiration=0.077,
            market_iv=market_iv,
            atm_iv=atm_iv_result.atm_iv,
            option_type='call'
        )
        
        # 驗證套戥水位結果
        self.assertEqual(arbitrage_result.iv_source, 'ATM IV (Module 17)')
        self.assertAlmostEqual(arbitrage_result.iv_used, atm_iv_result.atm_iv, places=4)
        self.assertIsNotNone(arbitrage_result.fair_value)
        self.assertIsNotNone(arbitrage_result.arbitrage_spread)
        self.assertIsNotNone(arbitrage_result.recommendation)
    
    def test_full_integration_chain_with_fallback(self):
        """
        測試完整集成鏈（回退模式）: 空期權鏈 → 回退 Market IV → BS 定價 → 套戥水位
        
        **Validates: Requirements 3.2, 4.1**
        """
        # 空期權鏈
        option_chain = {'calls': [], 'puts': []}
        current_price = 200.0
        market_option_price = 5.50
        market_iv = 0.30
        
        # Step 1: 嘗試從空期權鏈提取 ATM IV
        atm_iv_result = self.iv_calculator.extract_atm_iv_from_chain(
            option_chain=option_chain,
            current_price=current_price,
            option_type='call'
        )
        
        self.assertIsNone(atm_iv_result)
        
        # Step 2: 使用 None ATM IV 計算 BS 理論價格（應回退到 Market IV）
        bs_result = self.bs_calculator.calculate_option_price_with_atm_iv(
            stock_price=current_price,
            strike_price=200.0,
            risk_free_rate=0.05,
            time_to_expiration=0.077,
            market_iv=market_iv,
            atm_iv=None,
            option_type='call'
        )
        
        self.assertEqual(bs_result.iv_source, 'Market IV (fallback)')
        
        # Step 3: 計算套戥水位（應回退到 Market IV）
        arbitrage_result = self.arbitrage_calculator.calculate_with_atm_iv(
            market_option_price=market_option_price,
            stock_price=current_price,
            strike_price=200.0,
            risk_free_rate=0.05,
            time_to_expiration=0.077,
            market_iv=market_iv,
            atm_iv=None,
            option_type='call'
        )
        
        # 驗證回退到 Market IV
        self.assertEqual(arbitrage_result.iv_source, 'Market IV (fallback)')
        self.assertAlmostEqual(arbitrage_result.iv_used, market_iv, places=4)


def run_tests():
    """運行所有測試"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestModule17ToModule15Integration))
    suite.addTests(loader.loadTestsFromTestCase(TestModule17ToModule15ToModule3Integration))
    suite.addTests(loader.loadTestsFromTestCase(TestFullIntegrationChain))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)



class TestReportVerification(unittest.TestCase):
    """
    測試報告驗證: 驗證所有修復項目正確顯示
    
    驗證:
    - Theta 單位為「$/天」
    - Short Put 過濾正確
    - IV Rank 數據驗證
    - ATM IV 使用和來源標註
    - 套戥水位 IV 來源顯示
    
    **Validates: Requirements 1.2, 2.5, 3.3, 4.3, 5.3**
    """
    
    def setUp(self):
        """測試前準備"""
        self.bs_calculator = BlackScholesCalculator()
        self.iv_calculator = ImpliedVolatilityCalculator()
        self.arbitrage_calculator = ArbitrageSpreadCalculator()
        self.greeks_calculator = GreeksCalculator()
        self.optimal_strike_calculator = OptimalStrikeCalculator()
        self.iv_threshold_calculator = DynamicIVThresholdCalculator()
    
    def test_theta_unit_is_daily(self):
        """
        測試 Theta 單位為每日值
        
        **Validates: Requirements 1.1, 1.2**
        """
        # 計算 Theta
        theta = self.greeks_calculator.calculate_theta(
            stock_price=200.0,
            strike_price=200.0,
            risk_free_rate=0.05,
            time_to_expiration=0.077,  # 約 28 天
            volatility=0.25
        )
        
        # 驗證 Theta 是每日值（應該在 -$0.10 到 -$1.00 之間，對於 ATM 期權）
        # 年化 Theta 會是 -$36.5 到 -$365，每日值應該是這個除以 365
        self.assertLess(theta, 0, "Theta 應該是負數")
        self.assertGreater(theta, -2.0, "每日 Theta 應該大於 -$2.00")
        self.assertLess(theta, -0.01, "每日 Theta 應該小於 -$0.01")
    
    def test_short_put_filter_excludes_itm(self):
        """
        測試 Short Put 過濾排除 ITM 期權
        
        **Validates: Requirements 2.1, 2.2, 2.3**
        """
        # 模擬期權鏈數據，包含 ITM 和 OTM Put
        option_chain = {
            'calls': [],
            'puts': [
                # ITM Put (strike >= current_price)
                {'strike': 205.0, 'lastPrice': 8.0, 'bid': 7.5, 'ask': 8.5, 
                 'impliedVolatility': 30.0, 'delta': -0.65, 'volume': 100, 'openInterest': 500},
                {'strike': 200.0, 'lastPrice': 5.0, 'bid': 4.5, 'ask': 5.5, 
                 'impliedVolatility': 28.0, 'delta': -0.50, 'volume': 150, 'openInterest': 600},
                # OTM Put (strike < current_price)
                {'strike': 195.0, 'lastPrice': 3.0, 'bid': 2.5, 'ask': 3.5, 
                 'impliedVolatility': 26.0, 'delta': -0.35, 'volume': 200, 'openInterest': 700},
                {'strike': 190.0, 'lastPrice': 2.0, 'bid': 1.5, 'ask': 2.5, 
                 'impliedVolatility': 25.0, 'delta': -0.25, 'volume': 180, 'openInterest': 650},
                {'strike': 185.0, 'lastPrice': 1.0, 'bid': 0.8, 'ask': 1.2, 
                 'impliedVolatility': 24.0, 'delta': -0.15, 'volume': 120, 'openInterest': 550},
            ]
        }
        current_price = 200.0
        
        # 分析 Short Put 策略
        result = self.optimal_strike_calculator.analyze_strikes(
            current_price=current_price,
            option_chain=option_chain,
            strategy_type='short_put',
            days_to_expiration=28,
            iv_rank=50.0
        )
        
        # 驗證結果中沒有 ITM Put（strike >= current_price）
        if result and 'top_recommendations' in result:
            for rec in result['top_recommendations']:
                strike = rec.get('strike', 0)
                # ITM Put 應該被過濾
                self.assertLess(strike, current_price, 
                    f"ITM Put (strike={strike}) 不應該出現在推薦中")
                # 距離應該 >= 3%
                distance_pct = (current_price - strike) / current_price
                self.assertGreaterEqual(distance_pct, 0.03,
                    f"Short Put 距離 ({distance_pct*100:.1f}%) 應該 >= 3%")
    
    def test_iv_rank_data_validation_warning(self):
        """
        測試 IV Rank 數據驗證警告
        
        **Validates: Requirements 5.2, 5.3, 5.4**
        """
        # 測試數據不足的情況（少於 252 天但 >= 60 天）
        historical_iv = [25.0 + i * 0.1 for i in range(100)]  # 只有 100 天數據（百分比形式）
        current_iv = 30.0  # 百分比形式
        
        result = self.iv_threshold_calculator.calculate_thresholds(
            current_iv=current_iv,
            historical_iv=historical_iv
        )
        
        # 驗證結果包含數據天數
        self.assertEqual(result.historical_days, 100)
        
        # 驗證數據質量標記
        self.assertIn(result.data_quality, ['limited', 'insufficient'])
        
        # 驗證可靠性標記
        self.assertIn(result.reliability, ['moderate', 'unreliable'])
        
        # 驗證警告信息
        self.assertIsNotNone(result.warning)
    
    def test_iv_rank_sufficient_data(self):
        """
        測試 IV Rank 數據充足時無警告
        
        **Validates: Requirements 5.1, 5.4**
        """
        # 測試數據充足的情況（>= 252 天）
        historical_iv = [20.0 + i * 0.05 for i in range(260)]  # 260 天數據（百分比形式）
        current_iv = 30.0  # 百分比形式
        
        result = self.iv_threshold_calculator.calculate_thresholds(
            current_iv=current_iv,
            historical_iv=historical_iv
        )
        
        # 驗證數據質量為 sufficient
        self.assertEqual(result.data_quality, 'sufficient')
        self.assertEqual(result.reliability, 'reliable')
        
        # 驗證無警告
        self.assertIsNone(result.warning)
    
    def test_arbitrage_result_contains_iv_source(self):
        """
        測試套戥水位結果包含 IV 來源信息
        
        **Validates: Requirements 4.3**
        """
        result = self.arbitrage_calculator.calculate_with_atm_iv(
            market_option_price=5.50,
            stock_price=200.0,
            strike_price=200.0,
            risk_free_rate=0.05,
            time_to_expiration=0.077,
            market_iv=0.30,
            atm_iv=0.25,
            option_type='call'
        )
        
        # 驗證結果包含 IV 來源信息
        result_dict = result.to_dict()
        
        self.assertIn('iv_source', result_dict)
        self.assertIn('iv_used', result_dict)
        self.assertIn('iv_used_percent', result_dict)
        
        # 驗證 IV 來源正確
        self.assertEqual(result_dict['iv_source'], 'ATM IV (Module 17)')
        self.assertAlmostEqual(result_dict['iv_used'], 0.25, places=2)
    
    def test_bs_result_contains_iv_source(self):
        """
        測試 BS 定價結果包含 IV 來源信息
        
        **Validates: Requirements 3.3**
        """
        result = self.bs_calculator.calculate_option_price_with_atm_iv(
            stock_price=200.0,
            strike_price=200.0,
            risk_free_rate=0.05,
            time_to_expiration=0.077,
            market_iv=0.30,
            atm_iv=0.25,
            option_type='call'
        )
        
        # 驗證結果包含 IV 來源信息
        result_dict = result.to_dict()
        
        self.assertIn('iv_source', result_dict)
        self.assertEqual(result_dict['iv_source'], 'ATM IV (Module 17)')
    
    def test_complete_goog_like_analysis(self):
        """
        測試完整的 GOOG 類似分析
        
        模擬 GOOG 期權數據，驗證所有修復項目正確顯示
        
        **Validates: All Requirements**
        """
        # 模擬 GOOG 數據
        current_price = 195.50
        strike_price = 195.0
        risk_free_rate = 0.0435
        time_to_expiration = 0.077  # 約 28 天
        
        # 模擬期權鏈
        option_chain = {
            'calls': [
                {'strike': 185.0, 'impliedVolatility': 0.32, 'delta': 0.75},
                {'strike': 190.0, 'impliedVolatility': 0.28, 'delta': 0.60},
                {'strike': 195.0, 'impliedVolatility': 0.25, 'delta': 0.50},  # ATM
                {'strike': 200.0, 'impliedVolatility': 0.27, 'delta': 0.40},
                {'strike': 205.0, 'impliedVolatility': 0.30, 'delta': 0.30},
            ],
            'puts': [
                {'strike': 185.0, 'impliedVolatility': 0.33, 'delta': -0.25},
                {'strike': 190.0, 'impliedVolatility': 0.29, 'delta': -0.40},
                {'strike': 195.0, 'impliedVolatility': 0.26, 'delta': -0.50},  # ATM
                {'strike': 200.0, 'impliedVolatility': 0.28, 'delta': -0.60},
                {'strike': 205.0, 'impliedVolatility': 0.31, 'delta': -0.75},
            ]
        }
        
        # 1. 提取 ATM IV
        atm_iv_result = self.iv_calculator.extract_atm_iv_from_chain(
            option_chain=option_chain,
            current_price=current_price,
            option_type='call'
        )
        self.assertIsNotNone(atm_iv_result)
        atm_iv = atm_iv_result.atm_iv
        
        # 2. 計算 Greeks（包括 Theta）
        theta = self.greeks_calculator.calculate_theta(
            stock_price=current_price,
            strike_price=strike_price,
            risk_free_rate=risk_free_rate,
            time_to_expiration=time_to_expiration,
            volatility=atm_iv
        )
        # 驗證 Theta 是每日值
        self.assertLess(theta, 0)
        self.assertGreater(theta, -2.0)
        
        # 3. 計算 BS 理論價格
        bs_result = self.bs_calculator.calculate_option_price_with_atm_iv(
            stock_price=current_price,
            strike_price=strike_price,
            risk_free_rate=risk_free_rate,
            time_to_expiration=time_to_expiration,
            market_iv=0.30,
            atm_iv=atm_iv,
            option_type='call'
        )
        # 驗證 IV 來源
        self.assertEqual(bs_result.iv_source, 'ATM IV (Module 17)')
        
        # 4. 計算套戥水位
        market_option_price = 5.50
        arbitrage_result = self.arbitrage_calculator.calculate_with_atm_iv(
            market_option_price=market_option_price,
            stock_price=current_price,
            strike_price=strike_price,
            risk_free_rate=risk_free_rate,
            time_to_expiration=time_to_expiration,
            market_iv=0.30,
            atm_iv=atm_iv,
            option_type='call'
        )
        # 驗證 IV 來源
        self.assertEqual(arbitrage_result.iv_source, 'ATM IV (Module 17)')
        
        # 5. 計算 IV Rank（模擬歷史數據）
        historical_iv = [20.0 + i * 0.05 for i in range(260)]  # 百分比形式
        iv_rank_result = self.iv_threshold_calculator.calculate_thresholds(
            current_iv=atm_iv * 100,  # 轉換為百分比形式
            historical_iv=historical_iv
        )
        # 驗證數據質量
        self.assertEqual(iv_rank_result.data_quality, 'sufficient')
        
        # 6. 驗證所有結果都有正確的格式
        self.assertIsNotNone(bs_result.option_price)
        self.assertIsNotNone(arbitrage_result.fair_value)
        self.assertIsNotNone(arbitrage_result.arbitrage_spread)
        self.assertIsNotNone(iv_rank_result.status)


# 更新 run_tests 函數以包含新的測試類
def run_tests():
    """運行所有測試"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestModule17ToModule15Integration))
    suite.addTests(loader.loadTestsFromTestCase(TestModule17ToModule15ToModule3Integration))
    suite.addTests(loader.loadTestsFromTestCase(TestFullIntegrationChain))
    suite.addTests(loader.loadTestsFromTestCase(TestReportVerification))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
