#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Performance tests for Module 22: Optimal Strike Calculator

測試 LRU 緩存性能提升
"""

import pytest
import time
import sys
import os

# 添加項目根目錄到路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from calculation_layer.module22_optimal_strike import OptimalStrikeCalculator


def generate_test_option_chain(current_price: float, num_strikes: int = 50):
    """
    生成測試用期權鏈（使用 Black-Scholes 生成合理價格）
    
    參數:
        current_price: 當前股價
        num_strikes: 行使價數量
    """
    import math
    from scipy.stats import norm
    
    calls = []
    puts = []
    
    # 參數設置
    time_to_expiry = 30 / 365.0  # 30 天
    risk_free_rate = 0.045
    volatility = 0.25  # 25% IV
    
    # 生成 ATM ± 15% 的行使價
    min_strike = current_price * 0.85
    max_strike = current_price * 1.15
    strike_step = (max_strike - min_strike) / (num_strikes - 1) if num_strikes > 1 else 0
    
    def black_scholes_price(S, K, T, r, sigma, option_type='call'):
        """計算 Black-Scholes 期權價格"""
        if T <= 0:
            if option_type == 'call':
                return max(S - K, 0)
            else:
                return max(K - S, 0)
        
        d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)
        
        if option_type == 'call':
            price = S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
        else:
            price = K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
        
        return max(price, 0.01)  # 最小價格 0.01
    
    for i in range(num_strikes):
        strike = min_strike + i * strike_step
        
        # 計算理論價格
        call_price = black_scholes_price(current_price, strike, time_to_expiry, risk_free_rate, volatility, 'call')
        put_price = black_scholes_price(current_price, strike, time_to_expiry, risk_free_rate, volatility, 'put')
        
        # 添加 Bid-Ask Spread（約 2-3%）
        call_spread = call_price * 0.025
        put_spread = put_price * 0.025
        
        # 生成 Call 數據
        calls.append({
            'strike': strike,
            'bid': round(call_price - call_spread / 2, 2),
            'ask': round(call_price + call_spread / 2, 2),
            'lastPrice': round(call_price, 2),
            'volume': 100,
            'openInterest': 500,
            'impliedVolatility': volatility  # 使用小數形式
        })
        
        # 生成 Put 數據
        puts.append({
            'strike': strike,
            'bid': round(put_price - put_spread / 2, 2),
            'ask': round(put_price + put_spread / 2, 2),
            'lastPrice': round(put_price, 2),
            'volume': 100,
            'openInterest': 500,
            'impliedVolatility': volatility  # 使用小數形式
        })
    
    return {'calls': calls, 'puts': puts}


class TestModule22Performance:
    """Module 22 性能測試"""
    
    def test_50_strikes_cold_start(self):
        """測試 50 個行使價的冷啟動性能"""
        calc = OptimalStrikeCalculator()
        option_chain = generate_test_option_chain(100, 50)
        
        start_time = time.time()
        result = calc.analyze_strikes(
            current_price=100,
            option_chain=option_chain,
            strategy_type='short_put',
            days_to_expiration=30,
            iv_rank=50.0
        )
        elapsed_time = (time.time() - start_time) * 1000  # 轉換為毫秒
        
        print(f"\n冷啟動性能 (50 strikes): {elapsed_time:.2f}ms")
        
        # 驗證結果正確性
        assert result['total_analyzed'] > 0
        assert result['best_strike'] > 0
        
        # 性能要求：< 500ms（放寬要求，因為包含 IV 計算）
        assert elapsed_time < 500, f"冷啟動耗時 {elapsed_time:.2f}ms，超過 500ms"
    
    def test_50_strikes_warm_cache(self):
        """測試 50 個行使價的緩存命中性能"""
        calc = OptimalStrikeCalculator()
        option_chain = generate_test_option_chain(100, 50)
        
        # 第一次計算（冷啟動）
        start_time = time.time()
        calc.analyze_strikes(
            current_price=100,
            option_chain=option_chain,
            strategy_type='short_put',
            days_to_expiration=30,
            iv_rank=50.0
        )
        cold_time = (time.time() - start_time) * 1000
        
        # 第二次計算（應該命中緩存）
        start_time = time.time()
        result = calc.analyze_strikes(
            current_price=100,
            option_chain=option_chain,
            strategy_type='short_put',
            days_to_expiration=30,
            iv_rank=50.0
        )
        warm_time = (time.time() - start_time) * 1000
        
        print(f"\n冷啟動: {cold_time:.2f}ms")
        print(f"熱啟動: {warm_time:.2f}ms")
        
        # 獲取緩存統計
        cache_stats = calc.get_cache_stats()
        print(f"緩存統計: {cache_stats}")
        
        # 驗證緩存命中率 > 0（證明緩存在工作）
        assert cache_stats['hit_rate'] > 0, "緩存命中率應該 > 0%"
        
        # 驗證熱啟動比冷啟動快（或至少不慢）
        assert warm_time <= cold_time * 1.1, f"熱啟動 ({warm_time:.2f}ms) 不應該比冷啟動 ({cold_time:.2f}ms) 慢超過 10%"
        
        # 性能要求：熱啟動 < 400ms
        assert warm_time < 400, f"熱啟動耗時 {warm_time:.2f}ms，超過 400ms"
    
    def test_100_strikes_performance(self):
        """測試 100 個行使價的性能"""
        calc = OptimalStrikeCalculator()
        option_chain = generate_test_option_chain(100, 100)
        
        start_time = time.time()
        result = calc.analyze_strikes(
            current_price=100,
            option_chain=option_chain,
            strategy_type='short_put',
            days_to_expiration=30,
            iv_rank=50.0
        )
        elapsed_time = (time.time() - start_time) * 1000
        
        print(f"\n100 strikes 性能: {elapsed_time:.2f}ms")
        
        # 驗證結果正確性
        assert result['total_analyzed'] > 0
        
        # 性能要求：< 500ms（優化前的基準）
        assert elapsed_time < 500, f"耗時 {elapsed_time:.2f}ms，超過 500ms"
    
    def test_cache_hit_rate(self):
        """測試緩存命中率"""
        calc = OptimalStrikeCalculator()
        option_chain = generate_test_option_chain(100, 50)
        
        # 運行多次分析
        for _ in range(3):
            calc.analyze_strikes(
                current_price=100,
                option_chain=option_chain,
                strategy_type='short_put',
                days_to_expiration=30,
                iv_rank=50.0
            )
        
        # 獲取緩存統計
        cache_stats = calc.get_cache_stats()
        print(f"\n緩存統計（3次運行）: {cache_stats}")
        
        # 驗證緩存命中率 > 60%（放寬要求）
        assert cache_stats['hit_rate'] > 60, \
            f"緩存命中率 {cache_stats['hit_rate']:.1f}% 低於 60%"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])

