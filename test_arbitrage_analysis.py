#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
套利機會分析測試

展示 Module 19 Put-Call Parity 的套利識別功能
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from calculation_layer.module15_black_scholes import BlackScholesCalculator
from calculation_layer.module19_put_call_parity import PutCallParityValidator

def test_arbitrage_scenarios():
    """測試不同的套利場景"""
    print("=" * 100)
    print("期權套利機會分析")
    print("=" * 100)
    
    # 基本參數
    ticker = "AAPL"
    stock_price = 271.65
    strike_price = 271.65
    risk_free_rate = 0.045
    time_to_expiration = 38 / 365.0
    volatility = 0.25
    
    print(f"\n【基本參數】")
    print(f"  股票: {ticker}")
    print(f"  股價: ${stock_price:.2f}")
    print(f"  行使價: ${strike_price:.2f}")
    print(f"  到期時間: {time_to_expiration:.4f} 年 (38天)")
    print(f"  無風險利率: {risk_free_rate*100:.2f}%")
    print(f"  波動率: {volatility*100:.2f}%")
    
    # 初始化
    bs_calc = BlackScholesCalculator()
    parity_validator = PutCallParityValidator()
    
    # 計算理論價格
    call_theoretical = bs_calc.calculate_option_price(
        stock_price=stock_price,
        strike_price=strike_price,
        risk_free_rate=risk_free_rate,
        time_to_expiration=time_to_expiration,
        volatility=volatility,
        option_type='call'
    )
    
    put_theoretical = bs_calc.calculate_option_price(
        stock_price=stock_price,
        strike_price=strike_price,
        risk_free_rate=risk_free_rate,
        time_to_expiration=time_to_expiration,
        volatility=volatility,
        option_type='put'
    )
    
    print(f"\n【理論價格】")
    print(f"  Call 理論價格: ${call_theoretical.option_price:.2f}")
    print(f"  Put 理論價格: ${put_theoretical.option_price:.2f}")
    
    # ========== 場景 1: 無套利機會（理論價格）==========
    print("\n" + "=" * 100)
    print("【場景 1: 市場價格 = 理論價格（無套利機會）】")
    print("=" * 100)
    
    result1 = parity_validator.validate_parity(
        call_price=call_theoretical.option_price,
        put_price=put_theoretical.option_price,
        stock_price=stock_price,
        strike_price=strike_price,
        risk_free_rate=risk_free_rate,
        time_to_expiration=time_to_expiration,
        transaction_cost=0.10  # 假設交易成本 $0.10
    )
    
    print(f"\nCall 市場價格: ${result1.call_price:.2f}")
    print(f"Put 市場價格: ${result1.put_price:.2f}")
    print(f"理論差異: ${result1.theoretical_difference:.2f}")
    print(f"實際差異: ${result1.actual_difference:.2f}")
    print(f"偏離: ${result1.deviation:.6f}")
    print(f"套利機會: {result1.arbitrage_opportunity}")
    
    if not result1.arbitrage_opportunity:
        print(f"\n✓ 市場價格合理，無套利機會")
    
    # ========== 場景 2: Call 高估（有套利機會）==========
    print("\n" + "=" * 100)
    print("【場景 2: Call 高估 15%（有套利機會）】")
    print("=" * 100)
    
    call_overpriced = call_theoretical.option_price * 1.15
    
    result2 = parity_validator.validate_parity(
        call_price=call_overpriced,
        put_price=put_theoretical.option_price,
        stock_price=stock_price,
        strike_price=strike_price,
        risk_free_rate=risk_free_rate,
        time_to_expiration=time_to_expiration,
        transaction_cost=0.10
    )
    
    print(f"\nCall 市場價格: ${result2.call_price:.2f} (理論價 ${call_theoretical.option_price:.2f})")
    print(f"Put 市場價格: ${result2.put_price:.2f}")
    print(f"Call 高估: ${call_overpriced - call_theoretical.option_price:.2f} ({((call_overpriced/call_theoretical.option_price - 1)*100):.1f}%)")
    
    print(f"\n偏離分析:")
    print(f"  理論差異: ${result2.theoretical_difference:.2f}")
    print(f"  實際差異: ${result2.actual_difference:.2f}")
    print(f"  偏離: ${result2.deviation:.2f}")
    print(f"  偏離百分比: {result2.deviation_percentage:.2f}%")
    
    print(f"\n套利機會: {result2.arbitrage_opportunity}")
    
    if result2.arbitrage_opportunity:
        print(f"✓ 發現套利機會！")
        print(f"\n理論利潤: ${result2.theoretical_profit:.2f}")
        transaction_cost = 0.10
        net_profit = result2.theoretical_profit - transaction_cost
        print(f"扣除交易成本後利潤: ${net_profit:.2f} (交易成本 ${transaction_cost:.2f})")
        print(f"\n套利策略:")
        print(f"{result2.strategy}")
        
        # 詳細步驟
        print(f"\n具體操作步驟:")
        print(f"  1. 沽出 Call @ ${result2.call_price:.2f}  → 收入 ${result2.call_price:.2f}")
        print(f"  2. 買入 Put @ ${result2.put_price:.2f}   → 支出 ${result2.put_price:.2f}")
        print(f"  3. 買入股票 @ ${stock_price:.2f}  → 支出 ${stock_price:.2f}")
        print(f"  4. 借入現值 @ ${strike_price * np.exp(-risk_free_rate * time_to_expiration):.2f}")
        print(f"  5. 交易成本: ${0.10:.2f}")
        print(f"  ----------------------------------------")
        print(f"  淨利潤: ${(result2.theoretical_profit - 0.10):.2f}")
        
        print(f"\n到期日情境分析:")
        scenarios = [
            (stock_price * 0.9, "股價下跌 10%"),
            (stock_price, "股價持平"),
            (stock_price * 1.1, "股價上漲 10%")
        ]
        
        for price_at_expiry, scenario in scenarios:
            # Call 被執行或作廢
            call_payoff = -max(price_at_expiry - strike_price, 0)  # 沽出 Call
            # Put 執行或作廢
            put_payoff = max(strike_price - price_at_expiry, 0)  # 買入 Put
            # 股票價值
            stock_payoff = price_at_expiry - stock_price
            # 借款償還
            loan_payoff = -(strike_price - strike_price * np.exp(-risk_free_rate * time_to_expiration))
            
            total_payoff = call_payoff + put_payoff + stock_payoff + loan_payoff
            
            print(f"  {scenario} (${price_at_expiry:.2f}): 總收益 ${total_payoff:.2f}")
    
    # ========== 場景 3: Put 高估（有套利機會）==========
    print("\n" + "=" * 100)
    print("【場景 3: Put 高估 20%（有套利機會）】")
    print("=" * 100)
    
    put_overpriced = put_theoretical.option_price * 1.20
    
    result3 = parity_validator.validate_parity(
        call_price=call_theoretical.option_price,
        put_price=put_overpriced,
        stock_price=stock_price,
        strike_price=strike_price,
        risk_free_rate=risk_free_rate,
        time_to_expiration=time_to_expiration,
        transaction_cost=0.10
    )
    
    print(f"\nCall 市場價格: ${result3.call_price:.2f}")
    print(f"Put 市場價格: ${result3.put_price:.2f} (理論價 ${put_theoretical.option_price:.2f})")
    print(f"Put 高估: ${put_overpriced - put_theoretical.option_price:.2f} ({((put_overpriced/put_theoretical.option_price - 1)*100):.1f}%)")
    
    print(f"\n偏離分析:")
    print(f"  理論差異: ${result3.theoretical_difference:.2f}")
    print(f"  實際差異: ${result3.actual_difference:.2f}")
    print(f"  偏離: ${result3.deviation:.2f}")
    
    print(f"\n套利機會: {result3.arbitrage_opportunity}")
    
    if result3.arbitrage_opportunity:
        print(f"✓ 發現套利機會！")
        print(f"\n理論利潤: ${result3.theoretical_profit:.2f}")
        print(f"扣除交易成本後利潤: ${(result3.theoretical_profit - 0.10):.2f}")
        print(f"\n套利策略:")
        print(f"{result3.strategy}")
        
        print(f"\n具體操作步驟:")
        print(f"  1. 買入 Call @ ${result3.call_price:.2f}  → 支出 ${result3.call_price:.2f}")
        print(f"  2. 沽出 Put @ ${result3.put_price:.2f}   → 收入 ${result3.put_price:.2f}")
        print(f"  3. 沽空股票 @ ${stock_price:.2f}  → 收入 ${stock_price:.2f}")
        print(f"  4. 投資現值 @ ${strike_price * np.exp(-risk_free_rate * time_to_expiration):.2f}")
        print(f"  5. 交易成本: ${0.10:.2f}")
        print(f"  ----------------------------------------")
        print(f"  淨利潤: ${(result3.theoretical_profit - 0.10):.2f}")
    
    # ========== 場景 4: 小幅偏離（交易成本大於利潤）==========
    print("\n" + "=" * 100)
    print("【場景 4: Call 小幅高估 2%（交易成本大於利潤）】")
    print("=" * 100)
    
    call_slightly_overpriced = call_theoretical.option_price * 1.02
    
    result4 = parity_validator.validate_parity(
        call_price=call_slightly_overpriced,
        put_price=put_theoretical.option_price,
        stock_price=stock_price,
        strike_price=strike_price,
        risk_free_rate=risk_free_rate,
        time_to_expiration=time_to_expiration,
        transaction_cost=0.10
    )
    
    print(f"\nCall 市場價格: ${result4.call_price:.2f} (理論價 ${call_theoretical.option_price:.2f})")
    print(f"Put 市場價格: ${result4.put_price:.2f}")
    print(f"Call 高估: ${call_slightly_overpriced - call_theoretical.option_price:.2f} ({((call_slightly_overpriced/call_theoretical.option_price - 1)*100):.1f}%)")
    
    print(f"\n偏離: ${result4.deviation:.2f}")
    print(f"交易成本: ${0.10:.2f}")
    print(f"套利機會: {result4.arbitrage_opportunity}")
    
    if not result4.arbitrage_opportunity:
        print(f"\n✗ 雖然有偏離，但交易成本 (${0.10:.2f}) 大於理論利潤 (${abs(result4.deviation):.2f})")
        print(f"   不值得進行套利交易")
    
    # ========== 場景 5: 多個行使價掃描 ==========
    print("\n" + "=" * 100)
    print("【場景 5: 掃描多個行使價尋找套利機會】")
    print("=" * 100)
    
    strikes = [
        stock_price * 0.95,
        stock_price,
        stock_price * 1.05
    ]
    
    print(f"\n假設市場價格普遍高估 10%")
    print(f"\n{'行使價':<12} {'Call理論':<12} {'Call市場':<12} {'Put理論':<12} {'Put市場':<12} {'套利':<8} {'利潤':<10}")
    print("-" * 85)
    
    arbitrage_opportunities = []
    
    for strike in strikes:
        # 計算理論價格
        call_theo = bs_calc.calculate_option_price(
            stock_price=stock_price,
            strike_price=strike,
            risk_free_rate=risk_free_rate,
            time_to_expiration=time_to_expiration,
            volatility=volatility,
            option_type='call'
        )
        
        put_theo = bs_calc.calculate_option_price(
            stock_price=stock_price,
            strike_price=strike,
            risk_free_rate=risk_free_rate,
            time_to_expiration=time_to_expiration,
            volatility=volatility,
            option_type='put'
        )
        
        # 假設市場價格高估 10%
        call_market = call_theo.option_price * 1.10
        put_market = put_theo.option_price * 1.10
        
        # 驗證套利
        result = parity_validator.validate_parity(
            call_price=call_market,
            put_price=put_market,
            stock_price=stock_price,
            strike_price=strike,
            risk_free_rate=risk_free_rate,
            time_to_expiration=time_to_expiration,
            transaction_cost=0.10
        )
        
        arb_status = "✓" if result.arbitrage_opportunity else "✗"
        profit = result.net_profit if result.arbitrage_opportunity else 0
        
        print(f"${strike:<11.2f} ${call_theo.option_price:<11.2f} ${call_market:<11.2f} ${put_theo.option_price:<11.2f} ${put_market:<11.2f} {arb_status:<8} ${profit:<9.2f}")
        
        if result.arbitrage_opportunity:
            arbitrage_opportunities.append({
                'strike': strike,
                'profit': profit,
                'strategy': result.strategy
            })
    
    if arbitrage_opportunities:
        print(f"\n✓ 發現 {len(arbitrage_opportunities)} 個套利機會！")
        print(f"\n最佳套利機會:")
        best_opp = max(arbitrage_opportunities, key=lambda x: x['profit'])
        print(f"  行使價: ${best_opp['strike']:.2f}")
        print(f"  預期利潤: ${best_opp['profit']:.2f}")
        print(f"  策略: {best_opp['strategy']}")
    else:
        print(f"\n✗ 未發現套利機會")
    
    # ========== 總結 ==========
    print("\n" + "=" * 100)
    print("【總結】")
    print("=" * 100)
    
    print(f"\nModule 19 Put-Call Parity 套利功能:")
    print(f"  ✓ 自動識別套利機會")
    print(f"  ✓ 計算理論利潤")
    print(f"  ✓ 考慮交易成本")
    print(f"  ✓ 提供具體套利策略")
    print(f"  ✓ 支持批量掃描")
    
    print(f"\n套利條件:")
    print(f"  1. |偏離| > 交易成本")
    print(f"  2. Call 高估 → 沽出 Call + 買入 Put + 買入股票")
    print(f"  3. Put 高估 → 買入 Call + 沽出 Put + 沽空股票")
    
    print(f"\n風險提示:")
    print(f"  ⚠ 套利需要同時執行多個交易")
    print(f"  ⚠ 實際執行可能有滑點")
    print(f"  ⚠ 需要足夠的保證金")
    print(f"  ⚠ 市場流動性影響")
    
    print("\n" + "=" * 100)
    print("套利分析完成！")
    print("=" * 100)


if __name__ == "__main__":
    try:
        import numpy as np
        test_arbitrage_scenarios()
        print(f"\n✓ 套利分析測試成功！")
    except Exception as e:
        print(f"\n✗ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
