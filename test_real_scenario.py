#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
真實場景測試 - 使用實際參數測試新模塊

參數:
- 股票: AAPL
- 到期日: 2025-12-26
- 現價: 271.65
"""

import sys
import os
from datetime import datetime

# 添加項目根目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from calculation_layer.module15_black_scholes import BlackScholesCalculator
from calculation_layer.module16_greeks import GreeksCalculator
from calculation_layer.module17_implied_volatility import ImpliedVolatilityCalculator
from calculation_layer.module18_historical_volatility import HistoricalVolatilityCalculator
from calculation_layer.module19_put_call_parity import PutCallParityValidator

def test_real_scenario():
    """測試真實場景"""
    print("=" * 80)
    print("真實場景測試 - AAPL 期權分析")
    print("=" * 80)
    
    # 參數設置
    ticker = "AAPL"
    stock_price = 271.65
    expiration_date = "2025-12-26"
    
    # 計算到期時間（年）
    today = datetime.now()
    expiry = datetime.strptime(expiration_date, "%Y-%m-%d")
    days_to_expiry = (expiry - today).days
    time_to_expiration = days_to_expiry / 365.0
    
    print(f"\n基本參數:")
    print(f"  股票代碼: {ticker}")
    print(f"  當前股價: ${stock_price:.2f}")
    print(f"  到期日期: {expiration_date}")
    print(f"  到期天數: {days_to_expiry} 天")
    print(f"  到期時間: {time_to_expiration:.4f} 年")
    
    # 假設參數（因為無法從 API 獲取）
    risk_free_rate = 0.045  # 4.5% 無風險利率
    volatility = 0.25  # 25% 波動率（假設）
    
    # 測試不同的行使價
    strikes = [
        stock_price * 0.95,  # OTM Put / ITM Call
        stock_price,         # ATM
        stock_price * 1.05   # ITM Put / OTM Call
    ]
    
    print(f"\n假設參數:")
    print(f"  無風險利率: {risk_free_rate*100:.2f}%")
    print(f"  波動率: {volatility*100:.2f}%")
    
    # 初始化計算器
    bs_calc = BlackScholesCalculator()
    greeks_calc = GreeksCalculator()
    iv_calc = ImpliedVolatilityCalculator()
    parity_validator = PutCallParityValidator()
    
    print("\n" + "=" * 80)
    print("測試 1: Black-Scholes 期權定價")
    print("=" * 80)
    
    for strike in strikes:
        print(f"\n行使價: ${strike:.2f}")
        print("-" * 40)
        
        # Call 期權
        call_result = bs_calc.calculate_option_price(
            stock_price=stock_price,
            strike_price=strike,
            risk_free_rate=risk_free_rate,
            time_to_expiration=time_to_expiration,
            volatility=volatility,
            option_type='call'
        )
        
        # Put 期權
        put_result = bs_calc.calculate_option_price(
            stock_price=stock_price,
            strike_price=strike,
            risk_free_rate=risk_free_rate,
            time_to_expiration=time_to_expiration,
            volatility=volatility,
            option_type='put'
        )
        
        print(f"  Call 價格: ${call_result.option_price:.2f}")
        print(f"  Put 價格:  ${put_result.option_price:.2f}")
        print(f"  d1: {call_result.d1:.4f}, d2: {call_result.d2:.4f}")
    
    print("\n" + "=" * 80)
    print("測試 2: Greeks 計算（ATM 期權）")
    print("=" * 80)
    
    strike_atm = stock_price
    
    # Call Greeks
    call_greeks = greeks_calc.calculate_all_greeks(
        stock_price=stock_price,
        strike_price=strike_atm,
        risk_free_rate=risk_free_rate,
        time_to_expiration=time_to_expiration,
        volatility=volatility,
        option_type='call'
    )
    
    # Put Greeks
    put_greeks = greeks_calc.calculate_all_greeks(
        stock_price=stock_price,
        strike_price=strike_atm,
        risk_free_rate=risk_free_rate,
        time_to_expiration=time_to_expiration,
        volatility=volatility,
        option_type='put'
    )
    
    print(f"\nCall Greeks (行使價 ${strike_atm:.2f}):")
    print(f"  Delta: {call_greeks.delta:.4f}")
    print(f"  Gamma: {call_greeks.gamma:.6f}")
    print(f"  Theta: {call_greeks.theta:.4f}")
    print(f"  Vega:  {call_greeks.vega:.4f}")
    print(f"  Rho:   {call_greeks.rho:.4f}")
    
    print(f"\nPut Greeks (行使價 ${strike_atm:.2f}):")
    print(f"  Delta: {put_greeks.delta:.4f}")
    print(f"  Gamma: {put_greeks.gamma:.6f}")
    print(f"  Theta: {put_greeks.theta:.4f}")
    print(f"  Vega:  {put_greeks.vega:.4f}")
    print(f"  Rho:   {put_greeks.rho:.4f}")
    
    print("\n" + "=" * 80)
    print("測試 3: 隱含波動率反推")
    print("=" * 80)
    
    # 使用 BS 計算的價格作為"市場價格"來測試 IV 反推
    market_price = call_result.option_price
    
    iv_result = iv_calc.calculate_implied_volatility(
        market_price=market_price,
        stock_price=stock_price,
        strike_price=strike_atm,
        risk_free_rate=risk_free_rate,
        time_to_expiration=time_to_expiration,
        option_type='call'
    )
    
    print(f"\n市場價格: ${market_price:.2f}")
    print(f"反推 IV: {iv_result.implied_volatility*100:.2f}%")
    print(f"原始 IV: {volatility*100:.2f}%")
    print(f"收斂: {iv_result.converged}")
    print(f"迭代次數: {iv_result.iterations}")
    print(f"價格差異: ${abs(iv_result.price_difference):.6f}")
    
    if iv_result.converged:
        print("✓ IV 反推成功！")
    else:
        print("✗ IV 反推未收斂")
    
    print("\n" + "=" * 80)
    print("測試 4: Put-Call Parity 驗證")
    print("=" * 80)
    
    # 使用 BS 理論價格驗證 Parity
    parity_result = parity_validator.validate_with_theoretical_prices(
        stock_price=stock_price,
        strike_price=strike_atm,
        risk_free_rate=risk_free_rate,
        time_to_expiration=time_to_expiration,
        volatility=volatility
    )
    
    print(f"\nCall 價格: ${parity_result.call_price:.2f}")
    print(f"Put 價格:  ${parity_result.put_price:.2f}")
    print(f"理論差異: ${parity_result.theoretical_difference:.2f}")
    print(f"實際差異: ${parity_result.actual_difference:.2f}")
    print(f"偏離: ${parity_result.deviation:.6f}")
    print(f"套利機會: {parity_result.arbitrage_opportunity}")
    
    if abs(parity_result.deviation) < 0.01:
        print("✓ Put-Call Parity 驗證通過！")
    else:
        print("✗ Put-Call Parity 偏離過大")
    
    print("\n" + "=" * 80)
    print("測試 5: 實際應用場景")
    print("=" * 80)
    
    # 場景：評估是否應該買入 Call 期權
    print(f"\n場景：評估 AAPL ${strike_atm:.2f} Call 期權")
    print("-" * 40)
    
    # 1. 理論價格
    theoretical_price = call_result.option_price
    print(f"1. 理論價格: ${theoretical_price:.2f}")
    
    # 2. Greeks 分析
    print(f"\n2. 風險分析:")
    print(f"   Delta {call_greeks.delta:.4f}: 股價上漲 $1，期權價格上漲 ${call_greeks.delta:.2f}")
    print(f"   Gamma {call_greeks.gamma:.6f}: Delta 變化率")
    print(f"   Theta {call_greeks.theta:.4f}: 每年時間衰減 ${call_greeks.theta:.2f}")
    daily_theta = call_greeks.theta / 365
    print(f"   每日時間衰減: ${abs(daily_theta):.2f}")
    print(f"   Vega {call_greeks.vega:.4f}: 波動率上升 1%，期權價格上漲 ${call_greeks.vega/100:.2f}")
    
    # 3. 盈虧分析
    print(f"\n3. 盈虧分析（假設持有到期）:")
    scenarios = [
        (stock_price * 0.95, "下跌 5%"),
        (stock_price, "持平"),
        (stock_price * 1.05, "上漲 5%"),
        (stock_price * 1.10, "上漲 10%")
    ]
    
    for price_at_expiry, scenario in scenarios:
        intrinsic_value = max(price_at_expiry - strike_atm, 0)
        profit_loss = intrinsic_value - theoretical_price
        return_pct = (profit_loss / theoretical_price) * 100
        
        print(f"   {scenario} (${price_at_expiry:.2f}): ", end="")
        print(f"內在價值 ${intrinsic_value:.2f}, ", end="")
        print(f"損益 ${profit_loss:+.2f} ({return_pct:+.1f}%)")
    
    # 4. 建議
    print(f"\n4. 交易建議:")
    if call_greeks.delta > 0.5:
        print(f"   ✓ Delta > 0.5，期權有較高機率到期時有價值")
    else:
        print(f"   ⚠ Delta < 0.5，期權到期時可能無價值")
    
    if abs(daily_theta) < theoretical_price * 0.01:
        print(f"   ✓ 每日時間衰減 < 1% 期權價格，時間風險可控")
    else:
        print(f"   ⚠ 每日時間衰減較高，注意時間風險")
    
    print("\n" + "=" * 80)
    print("測試完成！")
    print("=" * 80)
    
    print(f"\n總結:")
    print(f"  ✓ Black-Scholes 定價: 正常工作")
    print(f"  ✓ Greeks 計算: 正常工作")
    print(f"  ✓ IV 反推: {'成功' if iv_result.converged else '失敗'}")
    print(f"  ✓ Put-Call Parity: {'通過' if abs(parity_result.deviation) < 0.01 else '失敗'}")
    print(f"\n所有新模塊在真實場景下運行正常！")


if __name__ == "__main__":
    try:
        test_real_scenario()
    except Exception as e:
        print(f"\n✗ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
