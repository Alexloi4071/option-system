#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Module 16 Theta 修復屬性測試

測試 Theta 每日轉換正確性
**Feature: option-calculation-fixes, Property 1: Theta 每日轉換正確性**
**Validates: Requirements 1.1, 1.3**
"""

import sys
import os
import math

# 添加項目根目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hypothesis import given, strategies as st, settings, assume
from calculation_layer.module16_greeks import GreeksCalculator


class TestThetaDailyConversion:
    """Theta 每日轉換屬性測試類"""
    
    def setup_method(self):
        """測試前準備"""
        self.calculator = GreeksCalculator()
    
    @settings(max_examples=100)
    @given(
        stock_price=st.floats(min_value=10.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
        strike_price=st.floats(min_value=10.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
        volatility=st.floats(min_value=0.05, max_value=1.0, allow_nan=False, allow_infinity=False),
        time_to_expiration=st.floats(min_value=0.01, max_value=2.0, allow_nan=False, allow_infinity=False),
        risk_free_rate=st.floats(min_value=0.0, max_value=0.15, allow_nan=False, allow_infinity=False),
        option_type=st.sampled_from(['call', 'put'])
    )
    def test_theta_daily_conversion_property(
        self, 
        stock_price: float, 
        strike_price: float, 
        volatility: float,
        time_to_expiration: float, 
        risk_free_rate: float,
        option_type: str
    ):
        """
        **Feature: option-calculation-fixes, Property 1: Theta 每日轉換正確性**
        **Validates: Requirements 1.1, 1.3**
        
        For any valid option parameters, the daily Theta returned by calculate_theta
        should equal the annual Theta divided by 365.
        """
        # 計算每日 Theta（通過公開方法）
        theta_daily = self.calculator.calculate_theta(
            stock_price=stock_price,
            strike_price=strike_price,
            risk_free_rate=risk_free_rate,
            time_to_expiration=time_to_expiration,
            volatility=volatility,
            option_type=option_type
        )
        
        # 計算年化 Theta（通過內部方法）
        theta_annual = self.calculator._calculate_theta_annual(
            stock_price=stock_price,
            strike_price=strike_price,
            risk_free_rate=risk_free_rate,
            time_to_expiration=time_to_expiration,
            volatility=volatility,
            option_type=option_type
        )
        
        # 驗證轉換正確性: daily = annual / 365
        expected_daily = theta_annual / 365.0
        
        # 使用相對誤差檢查，允許浮點數精度誤差
        if abs(expected_daily) > 1e-10:
            relative_error = abs(theta_daily - expected_daily) / abs(expected_daily)
            assert relative_error < 1e-10, (
                f"Theta 轉換不正確: daily={theta_daily}, expected={expected_daily}, "
                f"annual={theta_annual}, relative_error={relative_error}"
            )
        else:
            # 對於非常小的值，使用絕對誤差
            assert abs(theta_daily - expected_daily) < 1e-15, (
                f"Theta 轉換不正確: daily={theta_daily}, expected={expected_daily}"
            )
    
    @settings(max_examples=100)
    @given(
        stock_price=st.floats(min_value=50.0, max_value=500.0, allow_nan=False, allow_infinity=False),
        volatility=st.floats(min_value=0.15, max_value=0.50, allow_nan=False, allow_infinity=False),
        risk_free_rate=st.floats(min_value=0.01, max_value=0.10, allow_nan=False, allow_infinity=False),
        option_type=st.sampled_from(['call', 'put'])
    )
    def test_atm_theta_reasonable_range(
        self, 
        stock_price: float, 
        volatility: float,
        risk_free_rate: float,
        option_type: str
    ):
        """
        **Feature: option-calculation-fixes, Property 1: Theta 每日轉換正確性**
        **Validates: Requirements 1.1, 1.3**
        
        For ATM options with ~28 days to expiration, daily Theta should be
        in a reasonable range (approximately -$0.10 to -$1.00 for typical stock prices).
        
        This validates that the conversion produces sensible real-world values.
        """
        # ATM 期權（行使價 = 股價）
        strike_price = stock_price
        # 約 28 天到期
        time_to_expiration = 28.0 / 365.0
        
        theta_daily = self.calculator.calculate_theta(
            stock_price=stock_price,
            strike_price=strike_price,
            risk_free_rate=risk_free_rate,
            time_to_expiration=time_to_expiration,
            volatility=volatility,
            option_type=option_type
        )
        
        # Theta 應該為負（時間衰減）
        assert theta_daily < 0, f"ATM Theta 應該為負，但得到 {theta_daily}"
        
        # 對於 $50-$500 的股票，28天 ATM 期權的每日 Theta 
        # 應該在合理範圍內（根據股價調整）
        # 大約是股價的 0.01% 到 0.5% 每天
        min_theta = -stock_price * 0.005  # 最大衰減約 0.5%/天
        max_theta = -stock_price * 0.0001  # 最小衰減約 0.01%/天
        
        assert min_theta <= theta_daily <= max_theta, (
            f"ATM Theta 超出合理範圍: {theta_daily}, "
            f"預期範圍: [{min_theta}, {max_theta}], "
            f"股價: {stock_price}, 波動率: {volatility}"
        )


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
