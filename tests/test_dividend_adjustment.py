"""
測試股息調整功能 (US-1: Dividend Risk Adjustment)

測試範圍:
- Task 2.5.1: 測試 BS 股息調整（單元測試）
- Task 2.5.2: 測試 Parity 股息調整（單元測試）
- Task 2.5.3: 測試高股息股票（集成測試：KO, XOM）
- Task 2.5.4: 測試無股息股票（集成測試：TSLA）
- Task 2.5.5: 測試向後兼容性
"""

import sys
import os
# 添加父目錄到 sys.path，以便導入 calculation_layer 和 data_layer
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
import math
import pytest
from datetime import datetime

from calculation_layer.module15_black_scholes import BlackScholesCalculator
from calculation_layer.module19_put_call_parity import PutCallParityValidator
from data_layer.data_fetcher import DataFetcher


class TestBlackScholesDividendAdjustment(unittest.TestCase):
    """Task 2.5.1: 測試 Black-Scholes 股息調整（單元測試）"""
    
    def setUp(self):
        self.calc = BlackScholesCalculator()
        self.stock_price = 100.0
        self.strike_price = 100.0
        self.risk_free_rate = 0.05
        self.time_to_expiration = 1.0
        self.volatility = 0.20
    
    def test_dividend_adjustment_call_price_lower(self):
        """測試有股息時 Call 價格更低"""
        # 無股息
        result_no_div = self.calc.calculate_option_price(
            stock_price=self.stock_price,
            strike_price=self.strike_price,
            risk_free_rate=self.risk_free_rate,
            time_to_expiration=self.time_to_expiration,
            volatility=self.volatility,
            option_type='call',
            dividend_yield=0.0
        )
        
        # 有股息 (3%)
        result_with_div = self.calc.calculate_option_price(
            stock_price=self.stock_price,
            strike_price=self.strike_price,
            risk_free_rate=self.risk_free_rate,
            time_to_expiration=self.time_to_expiration,
            volatility=self.volatility,
            option_type='call',
            dividend_yield=0.03
        )
        
        # 有股息時，Call 價格應該更低
        self.assertLess(result_with_div.option_price, result_no_div.option_price,
                       "有股息時 Call 價格應該更低")
        
        # 驗證調整標識
        self.assertFalse(result_no_div.dividend_adjusted)
        self.assertTrue(result_with_div.dividend_adjusted)
        self.assertEqual(result_with_div.dividend_yield, 0.03)
    
    def test_dividend_adjustment_put_price_higher(self):
        """測試有股息時 Put 價格更高"""
        # 無股息
        result_no_div = self.calc.calculate_option_price(
            stock_price=self.stock_price,
            strike_price=self.strike_price,
            risk_free_rate=self.risk_free_rate,
            time_to_expiration=self.time_to_expiration,
            volatility=self.volatility,
            option_type='put',
            dividend_yield=0.0
        )
        
        # 有股息 (3%)
        result_with_div = self.calc.calculate_option_price(
            stock_price=self.stock_price,
            strike_price=self.strike_price,
            risk_free_rate=self.risk_free_rate,
            time_to_expiration=self.time_to_expiration,
            volatility=self.volatility,
            option_type='put',
            dividend_yield=0.03
        )
        
        # 有股息時，Put 價格應該更高
        self.assertGreater(result_with_div.option_price, result_no_div.option_price,
                          "有股息時 Put 價格應該更高")
        
        # 驗證調整標識
        self.assertFalse(result_no_div.dividend_adjusted)
        self.assertTrue(result_with_div.dividend_adjusted)
        self.assertEqual(result_with_div.dividend_yield, 0.03)
    
    def test_dividend_adjustment_formula(self):
        """測試股息調整公式: S_adjusted = S × e^(-q×T)"""
        dividend_yield = 0.025  # 2.5%
        
        result = self.calc.calculate_option_price(
            stock_price=self.stock_price,
            strike_price=self.strike_price,
            risk_free_rate=self.risk_free_rate,
            time_to_expiration=self.time_to_expiration,
            volatility=self.volatility,
            option_type='call',
            dividend_yield=dividend_yield
        )
        
        # 計算預期的調整後股價
        expected_adjusted_price = self.stock_price * math.exp(-dividend_yield * self.time_to_expiration)
        
        # 驗證調整後股價
        self.assertIsNotNone(result.adjusted_stock_price)
        self.assertAlmostEqual(result.adjusted_stock_price, expected_adjusted_price, places=4,
                              msg="調整後股價應該等於 S × e^(-q×T)")
    
    def test_high_dividend_impact(self):
        """測試高股息率對期權價格的影響"""
        # 測試不同股息率
        dividend_yields = [0.0, 0.02, 0.04, 0.06]
        call_prices = []
        put_prices = []
        
        for div_yield in dividend_yields:
            call_result = self.calc.calculate_option_price(
                stock_price=self.stock_price,
                strike_price=self.strike_price,
                risk_free_rate=self.risk_free_rate,
                time_to_expiration=self.time_to_expiration,
                volatility=self.volatility,
                option_type='call',
                dividend_yield=div_yield
            )
            put_result = self.calc.calculate_option_price(
                stock_price=self.stock_price,
                strike_price=self.strike_price,
                risk_free_rate=self.risk_free_rate,
                time_to_expiration=self.time_to_expiration,
                volatility=self.volatility,
                option_type='put',
                dividend_yield=div_yield
            )
            call_prices.append(call_result.option_price)
            put_prices.append(put_result.option_price)
        
        # 驗證 Call 價格隨股息率增加而遞減
        for i in range(len(call_prices) - 1):
            self.assertGreater(call_prices[i], call_prices[i+1],
                             f"Call 價格應該隨股息率增加而遞減 (div={dividend_yields[i]} vs {dividend_yields[i+1]})")
        
        # 驗證 Put 價格隨股息率增加而遞增
        for i in range(len(put_prices) - 1):
            self.assertLess(put_prices[i], put_prices[i+1],
                           f"Put 價格應該隨股息率增加而遞增 (div={dividend_yields[i]} vs {dividend_yields[i+1]})")


class TestPutCallParityDividendAdjustment(unittest.TestCase):
    """Task 2.5.2: 測試 Parity 股息調整（單元測試）"""
    
    def setUp(self):
        self.validator = PutCallParityValidator()
        self.stock_price = 100.0
        self.strike_price = 100.0
        self.risk_free_rate = 0.05
        self.time_to_expiration = 1.0
    
    def test_parity_with_dividend(self):
        """測試含股息的 Put-Call Parity"""
        dividend_yield = 0.03
        
        # 使用理論價格驗證 Parity
        result = self.validator.validate_with_theoretical_prices(
            stock_price=self.stock_price,
            strike_price=self.strike_price,
            risk_free_rate=self.risk_free_rate,
            time_to_expiration=self.time_to_expiration,
            volatility=0.20,
            dividend_yield=dividend_yield
        )
        
        # 驗證調整標識
        self.assertTrue(result.dividend_adjusted)
        self.assertEqual(result.dividend_yield, dividend_yield)
        
        # 理論價格應該滿足 Parity（偏離應該很小）
        self.assertLess(abs(result.deviation), 0.01,
                       "理論價格應該滿足 Put-Call Parity")
    
    def test_parity_formula_with_dividend(self):
        """測試股息調整的 Parity 公式: C - P = S×e^(-q×T) - K×e^(-r×T)"""
        dividend_yield = 0.025
        
        # 計算理論差異
        adjusted_stock_price = self.stock_price * math.exp(-dividend_yield * self.time_to_expiration)
        discount_factor = math.exp(-self.risk_free_rate * self.time_to_expiration)
        expected_diff = adjusted_stock_price - self.strike_price * discount_factor
        
        # 使用理論價格驗證
        result = self.validator.validate_with_theoretical_prices(
            stock_price=self.stock_price,
            strike_price=self.strike_price,
            risk_free_rate=self.risk_free_rate,
            time_to_expiration=self.time_to_expiration,
            volatility=0.20,
            dividend_yield=dividend_yield
        )
        
        # 驗證理論差異
        self.assertAlmostEqual(result.theoretical_difference, expected_diff, places=4,
                              msg="理論差異應該等於 S×e^(-q×T) - K×e^(-r×T)")
    
    def test_parity_no_dividend_vs_with_dividend(self):
        """測試無股息 vs 有股息的 Parity 差異"""
        # 無股息
        result_no_div = self.validator.validate_with_theoretical_prices(
            stock_price=self.stock_price,
            strike_price=self.strike_price,
            risk_free_rate=self.risk_free_rate,
            time_to_expiration=self.time_to_expiration,
            volatility=0.20,
            dividend_yield=0.0
        )
        
        # 有股息
        result_with_div = self.validator.validate_with_theoretical_prices(
            stock_price=self.stock_price,
            strike_price=self.strike_price,
            risk_free_rate=self.risk_free_rate,
            time_to_expiration=self.time_to_expiration,
            volatility=0.20,
            dividend_yield=0.03
        )
        
        # 有股息時理論差異應該更小（因為股價被調整降低）
        self.assertLess(result_with_div.theoretical_difference, result_no_div.theoretical_difference,
                       "有股息時理論差異應該更小")
        
        # 驗證調整標識
        self.assertFalse(result_no_div.dividend_adjusted)
        self.assertTrue(result_with_div.dividend_adjusted)


class TestBackwardCompatibility(unittest.TestCase):
    """Task 2.5.5: 測試向後兼容性"""
    
    def setUp(self):
        self.bs_calc = BlackScholesCalculator()
        self.parity_validator = PutCallParityValidator()
        self.stock_price = 100.0
        self.strike_price = 100.0
        self.risk_free_rate = 0.05
        self.time_to_expiration = 1.0
        self.volatility = 0.20
    
    def test_bs_default_dividend_zero(self):
        """測試 BS 模型默認股息率為 0"""
        # 不提供 dividend_yield 參數
        result_default = self.bs_calc.calculate_option_price(
            stock_price=self.stock_price,
            strike_price=self.strike_price,
            risk_free_rate=self.risk_free_rate,
            time_to_expiration=self.time_to_expiration,
            volatility=self.volatility,
            option_type='call'
        )
        
        # 明確提供 dividend_yield=0.0
        result_explicit_zero = self.bs_calc.calculate_option_price(
            stock_price=self.stock_price,
            strike_price=self.strike_price,
            risk_free_rate=self.risk_free_rate,
            time_to_expiration=self.time_to_expiration,
            volatility=self.volatility,
            option_type='call',
            dividend_yield=0.0
        )
        
        # 兩者應該完全相同
        self.assertAlmostEqual(result_default.option_price, result_explicit_zero.option_price, places=6,
                              msg="默認行為應該與 dividend_yield=0.0 相同")
        self.assertEqual(result_default.dividend_yield, 0.0)
        self.assertFalse(result_default.dividend_adjusted)
    
    def test_parity_default_dividend_zero(self):
        """測試 Parity 驗證器默認股息率為 0"""
        # 不提供 dividend_yield 參數
        result_default = self.parity_validator.validate_with_theoretical_prices(
            stock_price=self.stock_price,
            strike_price=self.strike_price,
            risk_free_rate=self.risk_free_rate,
            time_to_expiration=self.time_to_expiration,
            volatility=self.volatility
        )
        
        # 明確提供 dividend_yield=0.0
        result_explicit_zero = self.parity_validator.validate_with_theoretical_prices(
            stock_price=self.stock_price,
            strike_price=self.strike_price,
            risk_free_rate=self.risk_free_rate,
            time_to_expiration=self.time_to_expiration,
            volatility=self.volatility,
            dividend_yield=0.0
        )
        
        # 兩者應該完全相同
        self.assertAlmostEqual(result_default.theoretical_difference, 
                              result_explicit_zero.theoretical_difference, places=6,
                              msg="默認行為應該與 dividend_yield=0.0 相同")
        self.assertEqual(result_default.dividend_yield, 0.0)
        self.assertFalse(result_default.dividend_adjusted)
    
    def test_zero_dividend_no_adjustment(self):
        """測試 dividend_yield=0 時不進行調整"""
        result = self.bs_calc.calculate_option_price(
            stock_price=self.stock_price,
            strike_price=self.strike_price,
            risk_free_rate=self.risk_free_rate,
            time_to_expiration=self.time_to_expiration,
            volatility=self.volatility,
            option_type='call',
            dividend_yield=0.0
        )
        
        # 當 dividend_yield=0 時，adjusted_stock_price 應該等於 stock_price
        # 因為 e^(-0×T) = e^0 = 1
        if result.adjusted_stock_price is not None:
            self.assertAlmostEqual(result.adjusted_stock_price, self.stock_price, places=6,
                                  msg="dividend_yield=0 時調整後股價應該等於原股價")


# ========== 集成測試（需要真實 API 調用，默認跳過）==========

@pytest.mark.skip(reason="需要真實 API 調用，手動運行時取消跳過")
class TestHighDividendStocks(unittest.TestCase):
    """Task 2.5.3: 測試高股息股票（集成測試：KO, XOM）"""
    
    def setUp(self):
        self.fetcher = DataFetcher(use_ibkr=False)
        self.bs_calc = BlackScholesCalculator()
    
    def test_ko_dividend_yield(self):
        """測試 KO (Coca-Cola) 股息率獲取"""
        ticker = 'KO'
        dividend_yield = self.fetcher.get_dividend_yield(ticker)
        
        # KO 通常有 2.5-3.5% 的股息率
        self.assertGreater(dividend_yield, 0.02, f"{ticker} 應該有股息")
        self.assertLess(dividend_yield, 0.05, f"{ticker} 股息率應該在合理範圍內")
        print(f"\n{ticker} 股息率: {dividend_yield:.4f} ({dividend_yield*100:.2f}%)")
    
    def test_xom_dividend_yield(self):
        """測試 XOM (Exxon Mobil) 股息率獲取"""
        ticker = 'XOM'
        dividend_yield = self.fetcher.get_dividend_yield(ticker)
        
        # XOM 通常有 3-4% 的股息率
        self.assertGreater(dividend_yield, 0.025, f"{ticker} 應該有股息")
        self.assertLess(dividend_yield, 0.06, f"{ticker} 股息率應該在合理範圍內")
        print(f"\n{ticker} 股息率: {dividend_yield:.4f} ({dividend_yield*100:.2f}%)")
    
    def test_high_dividend_option_pricing(self):
        """測試高股息股票的期權定價影響"""
        ticker = 'KO'
        
        # 獲取股息率
        dividend_yield = self.fetcher.get_dividend_yield(ticker)
        
        # 獲取當前股價
        stock_data = self.fetcher.get_stock_data(ticker)
        current_price = stock_data.get('current_price', 50.0)
        
        # 計算 ATM Call 期權價格（無股息 vs 有股息）
        strike_price = current_price
        
        call_no_div = self.bs_calc.calculate_option_price(
            stock_price=current_price,
            strike_price=strike_price,
            risk_free_rate=0.045,
            time_to_expiration=0.25,  # 3個月
            volatility=0.20,
            option_type='call',
            dividend_yield=0.0
        )
        
        call_with_div = self.bs_calc.calculate_option_price(
            stock_price=current_price,
            strike_price=strike_price,
            risk_free_rate=0.045,
            time_to_expiration=0.25,
            volatility=0.20,
            option_type='call',
            dividend_yield=dividend_yield
        )
        
        # 計算價格差異
        price_diff = call_no_div.option_price - call_with_div.option_price
        price_diff_pct = (price_diff / call_no_div.option_price) * 100
        
        print(f"\n{ticker} ATM Call 期權價格比較:")
        print(f"  無股息: ${call_no_div.option_price:.2f}")
        print(f"  有股息 ({dividend_yield*100:.2f}%): ${call_with_div.option_price:.2f}")
        print(f"  差異: ${price_diff:.2f} ({price_diff_pct:.2f}%)")
        
        # 驗證有股息時價格更低
        self.assertLess(call_with_div.option_price, call_no_div.option_price,
                       "有股息時 Call 價格應該更低")


@pytest.mark.skip(reason="需要真實 API 調用，手動運行時取消跳過")
class TestNoDividendStocks(unittest.TestCase):
    """Task 2.5.4: 測試無股息股票（集成測試：TSLA）"""
    
    def setUp(self):
        self.fetcher = DataFetcher(use_ibkr=False)
    
    def test_tsla_no_dividend(self):
        """測試 TSLA (Tesla) 無股息"""
        ticker = 'TSLA'
        dividend_yield = self.fetcher.get_dividend_yield(ticker)
        
        # TSLA 不支付股息
        self.assertEqual(dividend_yield, 0.0, f"{ticker} 應該無股息")
        print(f"\n{ticker} 股息率: {dividend_yield:.4f} (無股息)")
    
    def test_googl_no_dividend(self):
        """測試 GOOGL (Alphabet) 無股息"""
        ticker = 'GOOGL'
        dividend_yield = self.fetcher.get_dividend_yield(ticker)
        
        # GOOGL 不支付股息
        self.assertEqual(dividend_yield, 0.0, f"{ticker} 應該無股息")
        print(f"\n{ticker} 股息率: {dividend_yield:.4f} (無股息)")


if __name__ == '__main__':
    # 運行單元測試（不包括集成測試）
    unittest.main(argv=[''], verbosity=2, exit=False)
    
    # 如果要運行集成測試，取消下面的註釋
    # pytest.main([__file__, '-v', '-s'])
