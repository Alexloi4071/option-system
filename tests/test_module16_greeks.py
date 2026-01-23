#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Module 16 單元測試: Greeks 期權風險指標計算

測試覆蓋:
1. Delta 計算準確性（Call 和 Put）
2. Gamma 計算準確性
3. Theta 計算準確性（Call 和 Put）
4. Vega 計算準確性
5. Rho 計算準確性（Call 和 Put）
6. Greeks 的合理範圍驗證
7. Call 和 Put 的 Greeks 關係
8. 邊界條件測試（ATM, ITM, OTM）
9. Greeks 對稱性驗證
"""

import unittest
import sys
import os
import math

# 添加項目根目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from calculation_layer.module16_greeks import (
    GreeksCalculator,
    GreeksResult
)


class TestGreeksCalculator(unittest.TestCase):
    """Greeks 計算器測試類"""
    
    def setUp(self):
        """測試前準備"""
        self.calculator = GreeksCalculator()
    
    # ========== Delta 測試 ==========
    
    def test_delta_call_range(self):
        """測試 Call Delta 在 0 到 1 之間"""
        # ATM
        delta_atm = self.calculator.calculate_delta(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.2,
            option_type='call'
        )
        self.assertGreater(delta_atm, 0, msg="ATM Call Delta 應該 > 0")
        self.assertLess(delta_atm, 1, msg="ATM Call Delta 應該 < 1")
        # ATM Call Delta 在有正利率時會略大於 0.5
        self.assertGreater(delta_atm, 0.5, msg="ATM Call Delta 應該 > 0.5")
        self.assertLess(delta_atm, 0.7, msg="ATM Call Delta 應該 < 0.7")
        
        # ITM
        delta_itm = self.calculator.calculate_delta(
            stock_price=110.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.2,
            option_type='call'
        )
        self.assertGreater(delta_itm, delta_atm, msg="ITM Call Delta 應該 > ATM")
        self.assertLess(delta_itm, 1, msg="ITM Call Delta 應該 < 1")
        
        # OTM
        delta_otm = self.calculator.calculate_delta(
            stock_price=90.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.2,
            option_type='call'
        )
        self.assertGreater(delta_otm, 0, msg="OTM Call Delta 應該 > 0")
        self.assertLess(delta_otm, delta_atm, msg="OTM Call Delta 應該 < ATM")
    
    def test_delta_put_range(self):
        """測試 Put Delta 在 -1 到 0 之間"""
        # ATM
        delta_atm = self.calculator.calculate_delta(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.2,
            option_type='put'
        )
        self.assertLess(delta_atm, 0, msg="ATM Put Delta 應該 < 0")
        self.assertGreater(delta_atm, -1, msg="ATM Put Delta 應該 > -1")
        # ATM Put Delta 在有正利率時會略大於 -0.5（接近0）
        self.assertGreater(delta_atm, -0.5, msg="ATM Put Delta 應該 > -0.5")
        self.assertLess(delta_atm, -0.3, msg="ATM Put Delta 應該 < -0.3")
        
        # ITM
        delta_itm = self.calculator.calculate_delta(
            stock_price=90.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.2,
            option_type='put'
        )
        self.assertLess(delta_itm, delta_atm, msg="ITM Put Delta 應該 < ATM (更負)")
        self.assertGreater(delta_itm, -1, msg="ITM Put Delta 應該 > -1")
        
        # OTM
        delta_otm = self.calculator.calculate_delta(
            stock_price=110.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.2,
            option_type='put'
        )
        self.assertLess(delta_otm, 0, msg="OTM Put Delta 應該 < 0")
        self.assertGreater(delta_otm, delta_atm, msg="OTM Put Delta 應該 > ATM (接近0)")
    
    def test_delta_call_put_relationship(self):
        """測試 Call 和 Put Delta 的關係: Delta_call - Delta_put = 1"""
        delta_call = self.calculator.calculate_delta(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.2,
            option_type='call'
        )
        
        delta_put = self.calculator.calculate_delta(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.2,
            option_type='put'
        )
        
        delta_difference = delta_call - delta_put
        self.assertAlmostEqual(
            delta_difference,
            1.0,
            places=6,
            msg="Delta_call - Delta_put 應該等於 1"
        )
    
    # ========== Gamma 測試 ==========
    
    def test_gamma_always_positive(self):
        """測試 Gamma 總是正數"""
        # ATM
        gamma_atm = self.calculator.calculate_gamma(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.2
        )
        self.assertGreater(gamma_atm, 0, msg="ATM Gamma 應該 > 0")
        
        # ITM
        gamma_itm = self.calculator.calculate_gamma(
            stock_price=110.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.2
        )
        self.assertGreater(gamma_itm, 0, msg="ITM Gamma 應該 > 0")
        
        # OTM
        gamma_otm = self.calculator.calculate_gamma(
            stock_price=90.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.2
        )
        self.assertGreater(gamma_otm, 0, msg="OTM Gamma 應該 > 0")
    
    def test_gamma_maximum_at_atm(self):
        """測試 ATM 期權的 Gamma 最大"""
        # 使用更接近 ATM 的價格來測試
        gamma_atm = self.calculator.calculate_gamma(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.2
        )
        
        gamma_itm = self.calculator.calculate_gamma(
            stock_price=110.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.2
        )
        
        gamma_deep_otm = self.calculator.calculate_gamma(
            stock_price=80.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.2
        )
        
        # ATM Gamma 應該大於深度 ITM 和深度 OTM
        self.assertGreater(gamma_atm, gamma_itm, msg="ATM Gamma 應該 > ITM Gamma")
        self.assertGreater(gamma_atm, gamma_deep_otm, msg="ATM Gamma 應該 > 深度 OTM Gamma")
    
    def test_gamma_same_for_call_and_put(self):
        """測試 Call 和 Put 的 Gamma 相同"""
        # 通過 calculate_all_greeks 獲取 Gamma
        result_call = self.calculator.calculate_all_greeks(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.2,
            option_type='call'
        )
        
        result_put = self.calculator.calculate_all_greeks(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.2,
            option_type='put'
        )
        
        self.assertAlmostEqual(
            result_call.gamma,
            result_put.gamma,
            places=6,
            msg="Call 和 Put 的 Gamma 應該相同"
        )
    
    # ========== Theta 測試 ==========
    
    def test_theta_usually_negative(self):
        """測試 Theta 通常為負（時間衰減）"""
        # Call Theta
        theta_call = self.calculator.calculate_theta(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.2,
            option_type='call'
        )
        self.assertLess(theta_call, 0, msg="Call Theta 通常為負")
        
        # Put Theta
        theta_put = self.calculator.calculate_theta(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.2,
            option_type='put'
        )
        self.assertLess(theta_put, 0, msg="Put Theta 通常為負")
    
    def test_theta_accelerates_near_expiration(self):
        """測試 Theta 在接近到期時加速"""
        # 長期期權
        theta_long = self.calculator.calculate_theta(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.2,
            option_type='call'
        )
        
        # 短期期權
        theta_short = self.calculator.calculate_theta(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=0.1,
            volatility=0.2,
            option_type='call'
        )
        
        # 短期期權的 Theta（絕對值）應該更大
        self.assertLess(theta_short, theta_long, msg="短期期權的 Theta 應該更負")
    
    # ========== Vega 測試 ==========
    
    def test_vega_always_positive(self):
        """測試 Vega 總是正數"""
        vega = self.calculator.calculate_vega(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.2
        )
        self.assertGreater(vega, 0, msg="Vega 應該 > 0")
    
    def test_vega_maximum_at_atm(self):
        """測試 ATM 期權的 Vega 最大"""
        vega_atm = self.calculator.calculate_vega(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.2
        )
        
        vega_itm = self.calculator.calculate_vega(
            stock_price=110.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.2
        )
        
        vega_otm = self.calculator.calculate_vega(
            stock_price=90.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.2
        )
        
        self.assertGreater(vega_atm, vega_itm, msg="ATM Vega 應該 > ITM Vega")
        self.assertGreater(vega_atm, vega_otm, msg="ATM Vega 應該 > OTM Vega")
    
    def test_vega_same_for_call_and_put(self):
        """測試 Call 和 Put 的 Vega 相同"""
        result_call = self.calculator.calculate_all_greeks(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.2,
            option_type='call'
        )
        
        result_put = self.calculator.calculate_all_greeks(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.2,
            option_type='put'
        )
        
        self.assertAlmostEqual(
            result_call.vega,
            result_put.vega,
            places=6,
            msg="Call 和 Put 的 Vega 應該相同"
        )
    
    def test_vega_increases_with_time(self):
        """測試長期期權的 Vega 更大"""
        vega_long = self.calculator.calculate_vega(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=2.0,
            volatility=0.2
        )
        
        vega_short = self.calculator.calculate_vega(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=0.5,
            volatility=0.2
        )
        
        self.assertGreater(vega_long, vega_short, msg="長期期權的 Vega 應該更大")
    
    # ========== Rho 測試 ==========
    
    def test_rho_call_positive_put_negative(self):
        """測試 Call Rho 為正，Put Rho 為負"""
        rho_call = self.calculator.calculate_rho(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.2,
            option_type='call'
        )
        self.assertGreater(rho_call, 0, msg="Call Rho 應該 > 0")
        
        rho_put = self.calculator.calculate_rho(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.2,
            option_type='put'
        )
        self.assertLess(rho_put, 0, msg="Put Rho 應該 < 0")
    
    def test_rho_increases_with_time(self):
        """測試長期期權的 Rho（絕對值）更大"""
        rho_long = self.calculator.calculate_rho(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=2.0,
            volatility=0.2,
            option_type='call'
        )
        
        rho_short = self.calculator.calculate_rho(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=0.5,
            volatility=0.2,
            option_type='call'
        )
        
        self.assertGreater(rho_long, rho_short, msg="長期期權的 Rho 應該更大")
    
    # ========== calculate_all_greeks 測試 ==========
    
    def test_calculate_all_greeks_returns_complete_result(self):
        """測試 calculate_all_greeks 返回完整結果"""
        result = self.calculator.calculate_all_greeks(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.2,
            option_type='call'
        )
        
        # 驗證結果類型
        self.assertIsInstance(result, GreeksResult)
        
        # 驗證所有 Greeks 都已計算
        self.assertIsNotNone(result.delta)
        self.assertIsNotNone(result.gamma)
        self.assertIsNotNone(result.theta)
        self.assertIsNotNone(result.vega)
        self.assertIsNotNone(result.rho)
        
        # 驗證其他字段
        self.assertEqual(result.stock_price, 100.0)
        self.assertEqual(result.strike_price, 100.0)
        self.assertEqual(result.option_type, 'call')
    
    def test_calculate_all_greeks_consistency(self):
        """測試 calculate_all_greeks 與單獨計算的一致性"""
        result = self.calculator.calculate_all_greeks(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.2,
            option_type='call'
        )
        
        # 單獨計算 Delta
        delta_separate = self.calculator.calculate_delta(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.2,
            option_type='call'
        )
        
        self.assertAlmostEqual(
            result.delta,
            delta_separate,
            places=6,
            msg="calculate_all_greeks 的 Delta 應該與單獨計算一致"
        )
        
        # 單獨計算 Gamma
        gamma_separate = self.calculator.calculate_gamma(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.2
        )
        
        self.assertAlmostEqual(
            result.gamma,
            gamma_separate,
            places=6,
            msg="calculate_all_greeks 的 Gamma 應該與單獨計算一致"
        )
    
    def test_to_dict_method(self):
        """測試 to_dict() 方法"""
        result = self.calculator.calculate_all_greeks(
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
            'delta', 'gamma', 'theta', 'vega', 'rho',
            'calculation_date', 'data_source', 'model'
        ]
        
        for field in required_fields:
            self.assertIn(field, result_dict, msg=f"字典應該包含 {field} 字段")
        
        # 驗證模型名稱
        self.assertEqual(result_dict['model'], 'Black-Scholes Greeks')
        self.assertEqual(result_dict['data_source'], 'Self-Calculated')
    
    # ========== 邊界條件測試 ==========
    
    def test_deep_itm_call_delta_near_one(self):
        """測試深度 ITM Call 的 Delta 接近 1"""
        delta = self.calculator.calculate_delta(
            stock_price=150.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.2,
            option_type='call'
        )
        self.assertGreater(delta, 0.9, msg="深度 ITM Call Delta 應該 > 0.9")
        self.assertLess(delta, 1.0, msg="Delta 應該 < 1")
    
    def test_deep_otm_call_delta_near_zero(self):
        """測試深度 OTM Call 的 Delta 接近 0"""
        delta = self.calculator.calculate_delta(
            stock_price=50.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.2,
            option_type='call'
        )
        self.assertGreater(delta, 0, msg="Delta 應該 > 0")
        self.assertLess(delta, 0.1, msg="深度 OTM Call Delta 應該 < 0.1")
    
    def test_input_validation(self):
        """測試輸入驗證"""
        with self.assertRaises(ValueError):
            self.calculator.calculate_all_greeks(
                stock_price=-100.0,
                strike_price=100.0,
                risk_free_rate=0.05,
                time_to_expiration=1.0,
                volatility=0.2,
                option_type='call'
            )
    
    # ========== 實際數值驗證 ==========
    
    def test_known_values_atm_call(self):
        """測試已知值 - ATM Call"""
        result = self.calculator.calculate_all_greeks(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.2,
            option_type='call'
        )
        
        # Delta 應該接近 0.5-0.6（ATM Call）
        self.assertGreater(result.delta, 0.5, msg="ATM Call Delta 應該 > 0.5")
        self.assertLess(result.delta, 0.7, msg="ATM Call Delta 應該 < 0.7")
        
        # Gamma 應該為正且合理
        self.assertGreater(result.gamma, 0, msg="Gamma 應該 > 0")
        self.assertLess(result.gamma, 0.1, msg="Gamma 應該在合理範圍內")
        
        # Vega 應該為正且合理
        self.assertGreater(result.vega, 0, msg="Vega 應該 > 0")
        self.assertLess(result.vega, 100, msg="Vega 應該在合理範圍內")
    
    # ========== 交叉 Greeks 測試 ==========
    
    def test_vanna_calculation(self):
        """測試 Vanna 計算"""
        vanna = self.calculator.calculate_vanna(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.2
        )
        
        # Vanna 應該是有限值
        self.assertFalse(math.isnan(vanna), msg="Vanna 不應該是 NaN")
        self.assertFalse(math.isinf(vanna), msg="Vanna 不應該是 Inf")
        
        # ATM 期權的 Vanna 應該在合理範圍內
        self.assertLess(abs(vanna), 1.0, msg="ATM Vanna 應該在合理範圍內")
    
    def test_volga_calculation(self):
        """測試 Volga 計算"""
        volga = self.calculator.calculate_volga(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.2
        )
        
        # Volga 應該是正值（Vega 的凸性）
        self.assertGreater(volga, 0, msg="Volga 應該 > 0")
        
        # Volga 應該在合理範圍內
        self.assertLess(volga, 100, msg="Volga 應該在合理範圍內")
    
    def test_charm_calculation(self):
        """測試 Charm 計算"""
        charm_call = self.calculator.calculate_charm(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.2,
            option_type='call'
        )
        
        # Charm 應該是有限值
        self.assertFalse(math.isnan(charm_call), msg="Charm 不應該是 NaN")
        self.assertFalse(math.isinf(charm_call), msg="Charm 不應該是 Inf")
        
        # ATM Call 的 Charm 通常是負值
        self.assertLess(charm_call, 0, msg="ATM Call Charm 通常為負")
    
    def test_calculate_all_cross_greeks(self):
        """測試 calculate_all_cross_greeks 方法"""
        cross_greeks = self.calculator.calculate_all_cross_greeks(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.2,
            option_type='call'
        )
        
        # 驗證返回字典包含所有三個 Greeks
        self.assertIn('vanna', cross_greeks, msg="應該包含 vanna")
        self.assertIn('volga', cross_greeks, msg="應該包含 volga")
        self.assertIn('charm', cross_greeks, msg="應該包含 charm")
        
        # 驗證值與單獨計算一致
        vanna_separate = self.calculator.calculate_vanna(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.2
        )
        
        self.assertAlmostEqual(
            cross_greeks['vanna'],
            vanna_separate,
            places=6,
            msg="批量計算的 Vanna 應該與單獨計算一致"
        )
    
    def test_cross_greeks_itm_otm(self):
        """測試 ITM 和 OTM 期權的交叉 Greeks"""
        # ITM Call
        cross_greeks_itm = self.calculator.calculate_all_cross_greeks(
            stock_price=110.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.2,
            option_type='call'
        )
        
        # OTM Call
        cross_greeks_otm = self.calculator.calculate_all_cross_greeks(
            stock_price=90.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            volatility=0.2,
            option_type='call'
        )
        
        # 驗證所有值都是有限的
        for greek_name, value in cross_greeks_itm.items():
            self.assertFalse(math.isnan(value), msg=f"ITM {greek_name} 不應該是 NaN")
            self.assertFalse(math.isinf(value), msg=f"ITM {greek_name} 不應該是 Inf")
        
        for greek_name, value in cross_greeks_otm.items():
            self.assertFalse(math.isnan(value), msg=f"OTM {greek_name} 不應該是 NaN")
            self.assertFalse(math.isinf(value), msg=f"OTM {greek_name} 不應該是 Inf")


def run_tests():
    """運行所有測試"""
    # 創建測試套件
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestGreeksCalculator)
    
    # 運行測試
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 返回測試結果
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
