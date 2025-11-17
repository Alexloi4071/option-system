#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
完整分析測試 - 包含所有功能和報告生成

參數:
- 股票: AAPL
- 到期日: 2025-12-26
- 現價: 271.65
"""

import sys
import os
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# 添加項目根目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from calculation_layer.module15_black_scholes import BlackScholesCalculator
from calculation_layer.module16_greeks import GreeksCalculator
from calculation_layer.module17_implied_volatility import ImpliedVolatilityCalculator
from calculation_layer.module18_historical_volatility import HistoricalVolatilityCalculator
from calculation_layer.module19_put_call_parity import PutCallParityValidator

def generate_mock_historical_data(current_price, days=60, volatility=0.25):
    """生成模擬歷史價格數據"""
    np.random.seed(42)
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
    
    # 使用幾何布朗運動生成價格
    returns = np.random.normal(0.001, volatility/np.sqrt(252), days)
    prices = current_price * np.exp(np.cumsum(returns - returns.mean()))
    
    return pd.Series(prices, index=dates)

def test_complete_analysis():
    """完整分析測試"""
    print("=" * 100)
    print("AAPL 期權完整分析報告")
    print("=" * 100)
    
    # ========== 基本參數 ==========
    ticker = "AAPL"
    stock_price = 271.65
    expiration_date = "2025-12-26"
    
    today = datetime.now()
    expiry = datetime.strptime(expiration_date, "%Y-%m-%d")
    days_to_expiry = (expiry - today).days
    time_to_expiration = days_to_expiry / 365.0
    
    risk_free_rate = 0.045
    
    print(f"\n【基本信息】")
    print(f"  股票代碼: {ticker}")
    print(f"  分析日期: {today.strftime('%Y-%m-%d')}")
    print(f"  當前股價: ${stock_price:.2f}")
    print(f"  到期日期: {expiration_date}")
    print(f"  剩餘天數: {days_to_expiry} 天 ({time_to_expiration:.4f} 年)")
    print(f"  無風險利率: {risk_free_rate*100:.2f}%")
    
    # ========== 初始化計算器 ==========
    bs_calc = BlackScholesCalculator()
    greeks_calc = GreeksCalculator()
    iv_calc = ImpliedVolatilityCalculator()
    hv_calc = HistoricalVolatilityCalculator()
    parity_validator = PutCallParityValidator()
    
    # ========== 1. 歷史波動率分析 ==========
    print("\n" + "=" * 100)
    print("【1. 歷史波動率分析】")
    print("=" * 100)
    
    # 生成模擬歷史數據
    historical_prices = generate_mock_historical_data(stock_price, days=60)
    
    # 計算多個窗口期的 HV
    hv_results = hv_calc.calculate_multiple_windows(
        historical_prices,
        windows=[10, 20, 30]
    )
    
    print(f"\n歷史波動率（不同窗口期）:")
    for window, result in hv_results.items():
        print(f"  {window:2d} 天 HV: {result.historical_volatility*100:6.2f}% ({result.data_points} 個數據點)")
    
    # 使用 30 天 HV 作為基準
    hv_30 = hv_results[30].historical_volatility
    print(f"\n基準歷史波動率（30天）: {hv_30*100:.2f}%")
    
    # ========== 2. 多信心值股價區間 ==========
    print("\n" + "=" * 100)
    print("【2. 股價預測區間（基於歷史波動率）】")
    print("=" * 100)
    
    # 計算不同信心度的股價區間
    confidence_levels = [
        (1.0, "68%", "1σ"),
        (1.28, "80%", "1.28σ"),
        (1.645, "90%", "1.645σ"),
        (2.0, "95%", "2σ")
    ]
    
    print(f"\n到期日股價預測區間:")
    print(f"{'信心度':<10} {'Z值':<10} {'下限':<15} {'上限':<15} {'區間寬度':<15}")
    print("-" * 70)
    
    price_ranges = {}
    for z_value, confidence, label in confidence_levels:
        # 計算股價區間: S * e^((r - σ²/2)T ± σ√T * Z)
        drift = (risk_free_rate - 0.5 * hv_30**2) * time_to_expiration
        diffusion = hv_30 * np.sqrt(time_to_expiration) * z_value
        
        lower_price = stock_price * np.exp(drift - diffusion)
        upper_price = stock_price * np.exp(drift + diffusion)
        range_width = upper_price - lower_price
        
        price_ranges[confidence] = (lower_price, upper_price)
        
        print(f"{confidence:<10} {label:<10} ${lower_price:<14.2f} ${upper_price:<14.2f} ${range_width:<14.2f}")
    
    # ========== 3. 期權定價（多個行使價）==========
    print("\n" + "=" * 100)
    print("【3. 期權理論定價】")
    print("=" * 100)
    
    # 選擇多個行使價
    strikes = [
        stock_price * 0.90,  # 深度 OTM Put / 深度 ITM Call
        stock_price * 0.95,  # OTM Put / ITM Call
        stock_price,         # ATM
        stock_price * 1.05,  # ITM Put / OTM Call
        stock_price * 1.10   # 深度 ITM Put / 深度 OTM Call
    ]
    
    print(f"\n使用波動率: {hv_30*100:.2f}% (30天歷史波動率)")
    print(f"\n{'行使價':<12} {'狀態':<10} {'Call價格':<12} {'Put價格':<12} {'Call Delta':<12} {'Put Delta':<12}")
    print("-" * 70)
    
    option_data = []
    for strike in strikes:
        # 判斷狀態
        if strike < stock_price * 0.97:
            status = "ITM Call"
        elif strike > stock_price * 1.03:
            status = "ITM Put"
        else:
            status = "ATM"
        
        # 計算 Call
        call_result = bs_calc.calculate_option_price(
            stock_price=stock_price,
            strike_price=strike,
            risk_free_rate=risk_free_rate,
            time_to_expiration=time_to_expiration,
            volatility=hv_30,
            option_type='call'
        )
        
        # 計算 Put
        put_result = bs_calc.calculate_option_price(
            stock_price=stock_price,
            strike_price=strike,
            risk_free_rate=risk_free_rate,
            time_to_expiration=time_to_expiration,
            volatility=hv_30,
            option_type='put'
        )
        
        # 計算 Greeks
        call_greeks = greeks_calc.calculate_all_greeks(
            stock_price=stock_price,
            strike_price=strike,
            risk_free_rate=risk_free_rate,
            time_to_expiration=time_to_expiration,
            volatility=hv_30,
            option_type='call'
        )
        
        put_greeks = greeks_calc.calculate_all_greeks(
            stock_price=stock_price,
            strike_price=strike,
            risk_free_rate=risk_free_rate,
            time_to_expiration=time_to_expiration,
            volatility=hv_30,
            option_type='put'
        )
        
        print(f"${strike:<11.2f} {status:<10} ${call_result.option_price:<11.2f} ${put_result.option_price:<11.2f} {call_greeks.delta:<11.4f} {put_greeks.delta:<11.4f}")
        
        option_data.append({
            'strike': strike,
            'call_price': call_result.option_price,
            'put_price': put_result.option_price,
            'call_greeks': call_greeks,
            'put_greeks': put_greeks
        })
    
    # ========== 4. ATM 期權詳細分析 ==========
    print("\n" + "=" * 100)
    print("【4. ATM 期權詳細分析】")
    print("=" * 100)
    
    atm_strike = stock_price
    atm_data = [d for d in option_data if abs(d['strike'] - atm_strike) < 1][0]
    
    print(f"\n行使價: ${atm_strike:.2f}")
    print(f"\nCall 期權:")
    print(f"  理論價格: ${atm_data['call_price']:.2f}")
    print(f"  Greeks:")
    print(f"    Delta:  {atm_data['call_greeks'].delta:8.4f}  (股價變動 $1 → 期權價格變動 ${atm_data['call_greeks'].delta:.2f})")
    print(f"    Gamma:  {atm_data['call_greeks'].gamma:8.6f}  (Delta 變化率)")
    print(f"    Theta:  {atm_data['call_greeks'].theta:8.2f}  (每年時間衰減 ${abs(atm_data['call_greeks'].theta):.2f})")
    print(f"            每日: ${abs(atm_data['call_greeks'].theta/365):.2f}")
    print(f"    Vega:   {atm_data['call_greeks'].vega:8.2f}  (波動率變動 1% → 期權價格變動 ${atm_data['call_greeks'].vega/100:.2f})")
    print(f"    Rho:    {atm_data['call_greeks'].rho:8.2f}  (利率變動 1% → 期權價格變動 ${atm_data['call_greeks'].rho/100:.2f})")
    
    print(f"\nPut 期權:")
    print(f"  理論價格: ${atm_data['put_price']:.2f}")
    print(f"  Greeks:")
    print(f"    Delta:  {atm_data['put_greeks'].delta:8.4f}  (股價變動 $1 → 期權價格變動 ${atm_data['put_greeks'].delta:.2f})")
    print(f"    Gamma:  {atm_data['put_greeks'].gamma:8.6f}  (Delta 變化率)")
    print(f"    Theta:  {atm_data['put_greeks'].theta:8.2f}  (每年時間衰減 ${abs(atm_data['put_greeks'].theta):.2f})")
    print(f"            每日: ${abs(atm_data['put_greeks'].theta/365):.2f}")
    print(f"    Vega:   {atm_data['put_greeks'].vega:8.2f}  (波動率變動 1% → 期權價格變動 ${atm_data['put_greeks'].vega/100:.2f})")
    print(f"    Rho:    {atm_data['put_greeks'].rho:8.2f}  (利率變動 1% → 期權價格變動 ${atm_data['put_greeks'].rho/100:.2f})")
    
    # ========== 5. Put-Call Parity 驗證 ==========
    print("\n" + "=" * 100)
    print("【5. Put-Call Parity 驗證】")
    print("=" * 100)
    
    print(f"\n驗證所有行使價的 Put-Call Parity:")
    print(f"{'行使價':<12} {'Call價格':<12} {'Put價格':<12} {'理論差異':<12} {'實際差異':<12} {'偏離':<12}")
    print("-" * 75)
    
    for data in option_data:
        parity_result = parity_validator.validate_parity(
            call_price=data['call_price'],
            put_price=data['put_price'],
            stock_price=stock_price,
            strike_price=data['strike'],
            risk_free_rate=risk_free_rate,
            time_to_expiration=time_to_expiration
        )
        
        print(f"${data['strike']:<11.2f} ${data['call_price']:<11.2f} ${data['put_price']:<11.2f} ${parity_result.theoretical_difference:<11.2f} ${parity_result.actual_difference:<11.2f} ${parity_result.deviation:<11.6f}")
    
    # ========== 6. 隱含波動率分析 ==========
    print("\n" + "=" * 100)
    print("【6. 隱含波動率分析（假設市場價格）】")
    print("=" * 100)
    
    # 假設市場價格比理論價格高 10%（模擬 IV 高於 HV 的情況）
    market_iv_multiplier = 1.15
    
    print(f"\n假設市場價格 = 理論價格 × {market_iv_multiplier}")
    print(f"\n{'行使價':<12} {'市場價格':<12} {'反推IV':<12} {'HV(30天)':<12} {'IV/HV比率':<12} {'評估':<15}")
    print("-" * 80)
    
    for data in option_data:
        market_price = data['call_price'] * market_iv_multiplier
        
        # 反推 IV
        iv_result = iv_calc.calculate_implied_volatility(
            market_price=market_price,
            stock_price=stock_price,
            strike_price=data['strike'],
            risk_free_rate=risk_free_rate,
            time_to_expiration=time_to_expiration,
            option_type='call'
        )
        
        if iv_result.converged:
            # 計算 IV/HV 比率
            ratio_result = hv_calc.calculate_iv_hv_ratio(
                implied_volatility=iv_result.implied_volatility,
                historical_volatility=hv_30
            )
            
            print(f"${data['strike']:<11.2f} ${market_price:<11.2f} {iv_result.implied_volatility*100:<11.2f}% {hv_30*100:<11.2f}% {ratio_result.iv_hv_ratio:<11.2f} {ratio_result.assessment:<15}")
        else:
            print(f"${data['strike']:<11.2f} ${market_price:<11.2f} {'未收斂':<11} {hv_30*100:<11.2f}% {'N/A':<11} {'N/A':<15}")
    
    # ========== 7. 盈虧分析 ==========
    print("\n" + "=" * 100)
    print("【7. ATM Call 期權盈虧分析】")
    print("=" * 100)
    
    premium = atm_data['call_price']
    
    # 使用不同信心度的價格區間
    print(f"\n期權成本: ${premium:.2f}")
    print(f"\n到期日股價情境分析:")
    print(f"{'情境':<20} {'股價':<12} {'內在價值':<12} {'損益':<12} {'回報率':<12}")
    print("-" * 70)
    
    scenarios = [
        ("極端下跌", price_ranges["95%"][0]),
        ("下跌 (90%)", price_ranges["90%"][0]),
        ("小幅下跌", stock_price * 0.98),
        ("持平", stock_price),
        ("小幅上漲", stock_price * 1.02),
        ("上漲 (90%)", price_ranges["90%"][1]),
        ("極端上漲", price_ranges["95%"][1])
    ]
    
    for scenario_name, price_at_expiry in scenarios:
        intrinsic_value = max(price_at_expiry - atm_strike, 0)
        profit_loss = intrinsic_value - premium
        return_pct = (profit_loss / premium) * 100
        
        print(f"{scenario_name:<20} ${price_at_expiry:<11.2f} ${intrinsic_value:<11.2f} ${profit_loss:<11.2f} {return_pct:>10.1f}%")
    
    # ========== 8. 交易建議 ==========
    print("\n" + "=" * 100)
    print("【8. 交易建議】")
    print("=" * 100)
    
    print(f"\n基於當前分析:")
    
    # Delta 分析
    if atm_data['call_greeks'].delta > 0.5:
        print(f"  ✓ Delta = {atm_data['call_greeks'].delta:.4f} > 0.5")
        print(f"    ATM Call 期權有較高機率到期時有價值")
    else:
        print(f"  ⚠ Delta = {atm_data['call_greeks'].delta:.4f} < 0.5")
        print(f"    ATM Call 期權到期時可能無價值")
    
    # Theta 分析
    daily_theta = abs(atm_data['call_greeks'].theta / 365)
    theta_pct = (daily_theta / premium) * 100
    if theta_pct < 1:
        print(f"\n  ✓ 每日時間衰減 ${daily_theta:.2f} ({theta_pct:.2f}% 期權價格)")
        print(f"    時間風險可控")
    else:
        print(f"\n  ⚠ 每日時間衰減 ${daily_theta:.2f} ({theta_pct:.2f}% 期權價格)")
        print(f"    時間衰減較快，建議短期持有")
    
    # IV/HV 分析（使用假設的市場價格）
    market_price_atm = premium * market_iv_multiplier
    iv_result_atm = iv_calc.calculate_implied_volatility(
        market_price=market_price_atm,
        stock_price=stock_price,
        strike_price=atm_strike,
        risk_free_rate=risk_free_rate,
        time_to_expiration=time_to_expiration,
        option_type='call'
    )
    
    if iv_result_atm.converged:
        ratio_result_atm = hv_calc.calculate_iv_hv_ratio(
            implied_volatility=iv_result_atm.implied_volatility,
            historical_volatility=hv_30
        )
        
        print(f"\n  IV/HV 比率: {ratio_result_atm.iv_hv_ratio:.2f}")
        print(f"  評估: {ratio_result_atm.assessment}")
        print(f"  建議: {ratio_result_atm.recommendation}")
    
    # 盈虧比分析
    max_loss = premium
    potential_gain_90 = max(price_ranges["90%"][1] - atm_strike, 0) - premium
    risk_reward = potential_gain_90 / max_loss if max_loss > 0 else 0
    
    print(f"\n  風險回報比（90%信心度上限）:")
    print(f"    最大損失: ${max_loss:.2f}")
    print(f"    潛在獲利: ${potential_gain_90:.2f}")
    print(f"    風險回報比: {risk_reward:.2f}:1")
    
    if risk_reward > 2:
        print(f"    ✓ 風險回報比良好")
    elif risk_reward > 1:
        print(f"    ⚠ 風險回報比一般")
    else:
        print(f"    ✗ 風險回報比較差")
    
    # ========== 9. 總結 ==========
    print("\n" + "=" * 100)
    print("【9. 分析總結】")
    print("=" * 100)
    
    print(f"\n本次分析使用了以下新增模塊:")
    print(f"  ✓ Module 15: Black-Scholes 期權定價")
    print(f"  ✓ Module 16: Greeks 風險指標計算")
    print(f"  ✓ Module 17: 隱含波動率計算")
    print(f"  ✓ Module 18: 歷史波動率計算")
    print(f"  ✓ Module 19: Put-Call Parity 驗證")
    
    print(f"\n關鍵數據:")
    print(f"  當前股價: ${stock_price:.2f}")
    print(f"  30天歷史波動率: {hv_30*100:.2f}%")
    print(f"  ATM Call 理論價格: ${premium:.2f}")
    print(f"  ATM Call Delta: {atm_data['call_greeks'].delta:.4f}")
    print(f"  每日時間衰減: ${daily_theta:.2f}")
    print(f"  90%信心度股價區間: ${price_ranges['90%'][0]:.2f} - ${price_ranges['90%'][1]:.2f}")
    
    print("\n" + "=" * 100)
    print("分析完成！")
    print("=" * 100)
    
    return {
        'ticker': ticker,
        'stock_price': stock_price,
        'hv_30': hv_30,
        'atm_call_price': premium,
        'atm_call_delta': atm_data['call_greeks'].delta,
        'price_ranges': price_ranges,
        'option_data': option_data
    }


if __name__ == "__main__":
    try:
        results = test_complete_analysis()
        print(f"\n✓ 完整分析測試成功！")
    except Exception as e:
        print(f"\n✗ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
