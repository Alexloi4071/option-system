"""
測試 Vega 單位和計算準確性

本測試文件驗證：
1. Vega 的單位正確性（美元/百分點）
2. Vega 計算的準確性
3. Call 和 Put 的 Vega 對稱性
4. Vega 的特性（ATM 最大、時間效應等）
"""

import pytest
import sys
import os

# 添加項目根目錄到 Python 路徑
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from calculation_layer.module16_greeks import GreeksCalculator
from calculation_layer.module15_black_scholes import BlackScholesCalculator


class TestVegaUnit:
    """測試 Vega 單位正確性"""
    
    def setup_method(self):
        """測試前準備"""
        self.greeks_calc = GreeksCalculator()
        self.bs_calc = BlackScholesCalculator()
    
    def test_vega_unit_1_percentage_point(self):
        """測試 Vega 單位：IV 變化 1 個百分點"""
        # 基準參數
        stock_price = 100
        strike_price = 100
        risk_free_rate = 0.05
        time_to_expiration = 1.0
        base_iv = 0.20  # 20%
        
        # 計算 Vega
        vega = self.greeks_calc.calculate_vega(
            stock_price=stock_price,
            strike_price=strike_price,
            risk_free_rate=risk_free_rate,
            time_to_expiration=time_to_expiration,
            volatility=base_iv
        )
        
        # 計算基準價格
        base_price = self.bs_calc.calculate_option_price(
            stock_price=stock_price,
            strike_price=strike_price,
            risk_free_rate=risk_free_rate,
            time_to_expiration=time_to_expiration,
            volatility=base_iv,
            option_type='call'
        ).option_price
        
        # 計算 IV 變化 1 個百分點後的價格（20% → 21%）
        new_iv = 0.21
        new_price = self.bs_calc.calculate_option_price(
            stock_price=stock_price,
            strike_price=strike_price,
            risk_free_rate=risk_free_rate,
            time_to_expiration=time_to_expiration,
            volatility=new_iv,
            option_type='call'
        ).option_price
        
        # 實際價格變化
        actual_change = new_price - base_price
        
        # Vega 預測的價格變化（IV 變化 1 個百分點）
        expected_change = vega * 1
        
        # 驗證誤差在 1% 以內
        error_pct = abs(actual_change - expected_change) / abs(expected_change)
        
        print(f"\n測試 Vega 單位（IV 變化 1 個百分點）:")
        print(f"  Vega: {vega:.6f}")
        print(f"  基準價格 (IV=20%): ${base_price:.4f}")
        print(f"  新價格 (IV=21%): ${new_price:.4f}")
        print(f"  實際價格變化: ${actual_change:.6f}")
        print(f"  Vega 預測: ${expected_change:.6f}")
        print(f"  誤差: {error_pct*100:.4f}%")
        
        assert error_pct < 0.01, f"Vega 計算誤差過大: {error_pct*100:.2f}%"
    
    def test_vega_unit_5_percentage_points(self):
        """測試 Vega 單位：IV 變化 5 個百分點"""
        # 基準參數
        stock_price = 100
        strike_price = 100
        risk_free_rate = 0.05
        time_to_expiration = 1.0
        base_iv = 0.20  # 20%
        
        # 計算 Vega
        vega = self.greeks_calc.calculate_vega(
            stock_price=stock_price,
            strike_price=strike_price,
            risk_free_rate=risk_free_rate,
            time_to_expiration=time_to_expiration,
            volatility=base_iv
        )
        
        # 計算基準價格
        base_price = self.bs_calc.calculate_option_price(
            stock_price=stock_price,
            strike_price=strike_price,
            risk_free_rate=risk_free_rate,
            time_to_expiration=time_to_expiration,
            volatility=base_iv,
            option_type='call'
        ).option_price
        
        # 計算 IV 變化 5 個百分點後的價格（20% → 25%）
        new_iv = 0.25
        new_price = self.bs_calc.calculate_option_price(
            stock_price=stock_price,
            strike_price=strike_price,
            risk_free_rate=risk_free_rate,
            time_to_expiration=time_to_expiration,
            volatility=new_iv,
            option_type='call'
        ).option_price
        
        # 實際價格變化
        actual_change = new_price - base_price
        
        # Vega 預測的價格變化（IV 變化 5 個百分點）
        expected_change = vega * 5
        
        # 對於較大的 IV 變化，Vega 是線性近似，允許 5% 的誤差
        error_pct = abs(actual_change - expected_change) / abs(expected_change)
        
        print(f"\n測試 Vega 單位（IV 變化 5 個百分點）:")
        print(f"  Vega: {vega:.6f}")
        print(f"  基準價格 (IV=20%): ${base_price:.4f}")
        print(f"  新價格 (IV=25%): ${new_price:.4f}")
        print(f"  實際價格變化: ${actual_change:.6f}")
        print(f"  Vega 預測: ${expected_change:.6f}")
        print(f"  誤差: {error_pct*100:.4f}%")
        
        assert error_pct < 0.05, f"Vega 計算誤差過大: {error_pct*100:.2f}%"
    
    def test_vega_unit_negative_change(self):
        """測試 Vega 單位：IV 下降"""
        # 基準參數
        stock_price = 100
        strike_price = 100
        risk_free_rate = 0.05
        time_to_expiration = 1.0
        base_iv = 0.30  # 30%
        
        # 計算 Vega
        vega = self.greeks_calc.calculate_vega(
            stock_price=stock_price,
            strike_price=strike_price,
            risk_free_rate=risk_free_rate,
            time_to_expiration=time_to_expiration,
            volatility=base_iv
        )
        
        # 計算基準價格
        base_price = self.bs_calc.calculate_option_price(
            stock_price=stock_price,
            strike_price=strike_price,
            risk_free_rate=risk_free_rate,
            time_to_expiration=time_to_expiration,
            volatility=base_iv,
            option_type='call'
        ).option_price
        
        # 計算 IV 下降 5 個百分點後的價格（30% → 25%）
        new_iv = 0.25
        new_price = self.bs_calc.calculate_option_price(
            stock_price=stock_price,
            strike_price=strike_price,
            risk_free_rate=risk_free_rate,
            time_to_expiration=time_to_expiration,
            volatility=new_iv,
            option_type='call'
        ).option_price
        
        # 實際價格變化（應該為負）
        actual_change = new_price - base_price
        
        # Vega 預測的價格變化（IV 下降 5 個百分點）
        expected_change = vega * (-5)
        
        # 驗證誤差
        error_pct = abs(actual_change - expected_change) / abs(expected_change)
        
        print(f"\n測試 Vega 單位（IV 下降 5 個百分點）:")
        print(f"  Vega: {vega:.6f}")
        print(f"  基準價格 (IV=30%): ${base_price:.4f}")
        print(f"  新價格 (IV=25%): ${new_price:.4f}")
        print(f"  實際價格變化: ${actual_change:.6f}")
        print(f"  Vega 預測: ${expected_change:.6f}")
        print(f"  誤差: {error_pct*100:.4f}%")
        
        assert actual_change < 0, "IV 下降時，期權價格應該下降"
        assert error_pct < 0.05, f"Vega 計算誤差過大: {error_pct*100:.2f}%"


class TestVegaSymmetry:
    """測試 Vega 對稱性"""
    
    def setup_method(self):
        """測試前準備"""
        self.calc = GreeksCalculator()
    
    def test_call_put_vega_same(self):
        """測試 Call 和 Put 的 Vega 相同"""
        # 計算 Call Vega
        call_result = self.calc.calculate_all_greeks(
            stock_price=100,
            strike_price=100,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.20,
            option_type='call'
        )
        
        # 計算 Put Vega
        put_result = self.calc.calculate_all_greeks(
            stock_price=100,
            strike_price=100,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.20,
            option_type='put'
        )
        
        print(f"\n測試 Call 和 Put 的 Vega 對稱性:")
        print(f"  Call Vega: {call_result.vega:.8f}")
        print(f"  Put Vega: {put_result.vega:.8f}")
        print(f"  差異: {abs(call_result.vega - put_result.vega):.10f}")
        
        # 驗證 Vega 相同（允許極小的浮點誤差）
        assert abs(call_result.vega - put_result.vega) < 1e-6, \
            f"Call 和 Put 的 Vega 應該相同"
    
    def test_vega_always_positive(self):
        """測試 Vega 總是正數"""
        test_cases = [
            # (stock_price, strike_price, description)
            (100, 100, "ATM"),
            (110, 100, "ITM Call / OTM Put"),
            (90, 100, "OTM Call / ITM Put"),
            (120, 100, "Deep ITM Call"),
            (80, 100, "Deep OTM Call"),
        ]
        
        print(f"\n測試 Vega 總是正數:")
        
        for stock_price, strike_price, desc in test_cases:
            vega = self.calc.calculate_vega(
                stock_price=stock_price,
                strike_price=strike_price,
                risk_free_rate=0.05,
                time_to_expiration=1.0,
                volatility=0.20
            )
            
            print(f"  {desc}: S=${stock_price}, K=${strike_price}, Vega={vega:.6f}")
            
            assert vega > 0, f"Vega 應該總是正數，但得到 {vega}"


class TestVegaProperties:
    """測試 Vega 的特性"""
    
    def setup_method(self):
        """測試前準備"""
        self.calc = GreeksCalculator()
    
    def test_atm_vega_maximum(self):
        """測試 ATM 期權的 Vega 接近最大"""
        strike_price = 100
        
        # 計算不同股價下的 Vega
        stock_prices = [90, 95, 100, 105, 110]
        vegas = []
        
        print(f"\n測試 ATM 期權的 Vega 接近最大:")
        
        for stock_price in stock_prices:
            vega = self.calc.calculate_vega(
                stock_price=stock_price,
                strike_price=strike_price,
                risk_free_rate=0.05,
                time_to_expiration=1.0,
                volatility=0.20
            )
            vegas.append(vega)
            
            moneyness = "ATM" if stock_price == strike_price else \
                       ("ITM" if stock_price > strike_price else "OTM")
            print(f"  S=${stock_price}, K=${strike_price} ({moneyness}): Vega={vega:.6f}")
        
        # 找到最大 Vega
        max_vega = max(vegas)
        max_index = vegas.index(max_vega)
        
        print(f"\n  最大 Vega: {max_vega:.6f} (S=${stock_prices[max_index]})")
        
        # 驗證 ATM (S=100) 的 Vega 接近最大值（在 95% 以上）
        atm_index = stock_prices.index(100)
        atm_vega = vegas[atm_index]
        
        ratio = atm_vega / max_vega
        print(f"  ATM Vega / 最大 Vega: {ratio*100:.2f}%")
        
        assert ratio > 0.95, \
            f"ATM Vega 應該接近最大值，但只有最大值的 {ratio*100:.2f}%"
        
        # 驗證深度實值和虛值的 Vega 明顯小於 ATM
        assert vegas[0] < atm_vega, "深度虛值期權的 Vega 應該小於 ATM"
        assert vegas[-1] < atm_vega, "深度實值期權的 Vega 應該小於 ATM"
    
    def test_vega_increases_with_time(self):
        """測試 Vega 隨到期時間增加而增加"""
        times = [0.25, 0.5, 1.0, 2.0]  # 3個月, 6個月, 1年, 2年
        vegas = []
        
        print(f"\n測試 Vega 隨到期時間增加:")
        
        for time in times:
            vega = self.calc.calculate_vega(
                stock_price=100,
                strike_price=100,
                risk_free_rate=0.05,
                time_to_expiration=time,
                volatility=0.20
            )
            vegas.append(vega)
            
            print(f"  T={time:.2f}年: Vega={vega:.6f}")
        
        # 驗證 Vega 遞增
        for i in range(len(vegas) - 1):
            assert vegas[i+1] > vegas[i], \
                f"Vega 應該隨時間增加，但 T={times[i+1]} 的 Vega ({vegas[i+1]:.6f}) <= T={times[i]} 的 Vega ({vegas[i]:.6f})"
    
    def test_vega_reasonable_range(self):
        """測試 Vega 在合理範圍內"""
        # ATM 1年期期權的 Vega 通常在 0.1 到 0.5 之間
        vega = self.calc.calculate_vega(
            stock_price=100,
            strike_price=100,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.20
        )
        
        print(f"\n測試 Vega 在合理範圍內:")
        print(f"  ATM 1年期 Vega: {vega:.6f}")
        print(f"  預期範圍: 0.1 到 0.5")
        
        assert 0.1 < vega < 0.5, \
            f"ATM 1年期期權的 Vega ({vega:.6f}) 超出預期範圍 (0.1, 0.5)"


class TestVegaEdgeCases:
    """測試 Vega 的邊界條件"""
    
    def setup_method(self):
        """測試前準備"""
        self.calc = GreeksCalculator()
    
    def test_vega_near_expiration(self):
        """測試接近到期時的 Vega"""
        # 接近到期時，Vega 應該接近 0
        vega = self.calc.calculate_vega(
            stock_price=100,
            strike_price=100,
            risk_free_rate=0.05,
            time_to_expiration=0.01,  # 約 3.65 天
            volatility=0.20
        )
        
        print(f"\n測試接近到期時的 Vega:")
        print(f"  T=0.01年 (約3.65天): Vega={vega:.6f}")
        
        # Vega 應該很小
        assert vega < 0.05, f"接近到期時 Vega 應該很小，但得到 {vega:.6f}"
    
    def test_vega_deep_itm(self):
        """測試深度實值期權的 Vega"""
        # 深度實值期權的 Vega 應該較小
        vega_deep_itm = self.calc.calculate_vega(
            stock_price=150,
            strike_price=100,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.20
        )
        
        # ATM 期權的 Vega
        vega_atm = self.calc.calculate_vega(
            stock_price=100,
            strike_price=100,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.20
        )
        
        print(f"\n測試深度實值期權的 Vega:")
        print(f"  Deep ITM (S=150, K=100): Vega={vega_deep_itm:.6f}")
        print(f"  ATM (S=100, K=100): Vega={vega_atm:.6f}")
        
        assert vega_deep_itm < vega_atm, \
            f"深度實值期權的 Vega 應該小於 ATM 期權"
    
    def test_vega_deep_otm(self):
        """測試深度虛值期權的 Vega"""
        # 深度虛值期權的 Vega 應該較小
        vega_deep_otm = self.calc.calculate_vega(
            stock_price=50,
            strike_price=100,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.20
        )
        
        # ATM 期權的 Vega
        vega_atm = self.calc.calculate_vega(
            stock_price=100,
            strike_price=100,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.20
        )
        
        print(f"\n測試深度虛值期權的 Vega:")
        print(f"  Deep OTM (S=50, K=100): Vega={vega_deep_otm:.6f}")
        print(f"  ATM (S=100, K=100): Vega={vega_atm:.6f}")
        
        assert vega_deep_otm < vega_atm, \
            f"深度虛值期權的 Vega 應該小於 ATM 期權"


if __name__ == "__main__":
    # 運行測試
    pytest.main([__file__, "-v", "-s"])
