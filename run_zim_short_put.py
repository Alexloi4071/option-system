#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ZIM Short Put 分析腳本 (混合模式)
使用手動輸入的期權數據 + API 補齊其他數據
包含完整的策略推薦信心度分析
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from datetime import datetime
from data_layer.data_fetcher import DataFetcher
from calculation_layer.module10_short_put import ShortPutCalculator
from calculation_layer.module14_monitoring_posts import MonitoringPostsCalculator
from calculation_layer.module15_black_scholes import BlackScholesCalculator
from calculation_layer.module16_greeks import GreeksCalculator
from calculation_layer.module21_momentum_filter import MomentumFilter
from calculation_layer.strategy_recommendation import StrategyRecommender

print("=" * 70)
print("ZIM Short Put 分析 (混合模式: 手動輸入 + API)")
print(f"分析時間: {datetime.now()}")
print("=" * 70)

# ============================================================
# 手動輸入的期權數據
# ============================================================
MANUAL_OPTION_DATA = {
    'ticker': 'ZIM',
    'expiration': '2026-01-16',
    'option_type': 'put',
    'strategy': 'short_put',
    'strike_price': 13.0,
    'bid': 0.12,
    'ask': 0.25,
    'last_price': 0.19,
    'delta': -0.071,
    'gamma': 0.023,
    'theta': -0.009,
    'vega': 0.009,
    'implied_volatility': 85.9,  # 百分比
    'open_interest': 5620,
    'volume': 53
}

print("\n" + "=" * 70)
print("手動輸入的期權數據")
print("=" * 70)
print(f"  股票: {MANUAL_OPTION_DATA['ticker']}")
print(f"  到期日: {MANUAL_OPTION_DATA['expiration']}")
print(f"  策略: Short Put")
print(f"  行使價: ${MANUAL_OPTION_DATA['strike_price']}")
print(f"  買價/賣價: ${MANUAL_OPTION_DATA['bid']} / ${MANUAL_OPTION_DATA['ask']}")
print(f"  最後價: ${MANUAL_OPTION_DATA['last_price']}")
print(f"  Delta: {MANUAL_OPTION_DATA['delta']}")
print(f"  Gamma: {MANUAL_OPTION_DATA['gamma']}")
print(f"  Theta: {MANUAL_OPTION_DATA['theta']}")
print(f"  Vega: {MANUAL_OPTION_DATA['vega']}")
print(f"  IV: {MANUAL_OPTION_DATA['implied_volatility']}%")
print(f"  未平倉: {MANUAL_OPTION_DATA['open_interest']}")

# ============================================================
# 從 API 獲取補充數據
# ============================================================
print("\n" + "=" * 70)
print("從 API 獲取補充數據...")
print("=" * 70)

fetcher = DataFetcher()

# 獲取股票當前價格
print("\n[1] 獲取股票當前價格...")
stock_info = fetcher.get_stock_info('ZIM')
current_price = stock_info.get('current_price', 19.30) if stock_info else 19.30
print(f"    當前股價: ${current_price:.2f}")

# 獲取無風險利率
print("\n[2] 獲取無風險利率...")
risk_free_rate = fetcher.get_risk_free_rate()
if risk_free_rate > 1:
    risk_free_rate = risk_free_rate / 100
print(f"    無風險利率: {risk_free_rate*100:.2f}%")

# 獲取 VIX
print("\n[3] 獲取 VIX...")
vix = fetcher.get_vix()
print(f"    VIX: {vix:.2f}%")

# 獲取歷史數據計算 HV
print("\n[4] 獲取歷史數據...")
historical_data = fetcher.get_historical_data('ZIM', period='1y', interval='1d')
if historical_data is not None and not historical_data.empty:
    print(f"    獲取了 {len(historical_data)} 條歷史記錄")
else:
    print("    ! 無法獲取歷史數據")

# 計算到期天數
exp_date = datetime.strptime(MANUAL_OPTION_DATA['expiration'], '%Y-%m-%d')
today = datetime.now()
days_to_exp = (exp_date - today).days
time_to_expiration = days_to_exp / 365.0
print(f"\n[5] 到期天數: {days_to_exp} 天")

# ============================================================
# 計算支持位和阻力位 (用於策略推薦)
# ============================================================
print("\n[6] 計算支持位/阻力位...")
from calculation_layer.module1_support_resistance import SupportResistanceCalculator
sr_calc = SupportResistanceCalculator()
sr_result = sr_calc.calculate(
    stock_price=current_price,
    implied_volatility=MANUAL_OPTION_DATA['implied_volatility'],
    days_to_expiration=days_to_exp
)
support_level = sr_result.support_level
resistance_level = sr_result.resistance_level
print(f"    支持位: ${support_level:.2f}")
print(f"    阻力位: ${resistance_level:.2f}")

# ============================================================
# 計算歷史波動率
# ============================================================
print("\n[7] 計算歷史波動率...")
hv_20 = 50.0  # 默認值
if historical_data is not None and not historical_data.empty:
    try:
        from calculation_layer.module18_historical_volatility import HistoricalVolatilityCalculator
        hv_calc = HistoricalVolatilityCalculator()
        hv_result = hv_calc.calculate_multiple_windows(historical_data['Close'])
        hv_20 = hv_result.get('hv_20', 50.0)
        print(f"    HV (20日): {hv_20:.2f}%")
    except Exception as e:
        print(f"    HV 計算失敗: {e}")
        print(f"    HV (20日): {hv_20:.2f}% (默認值)")
else:
    print(f"    HV (20日): {hv_20:.2f}% (默認值)")

# 計算 IV/HV 比率
iv_hv_ratio = MANUAL_OPTION_DATA['implied_volatility'] / hv_20 if hv_20 > 0 else 1.0
print(f"    IV/HV 比率: {iv_hv_ratio:.2f}")

# ============================================================
# 判斷趨勢
# ============================================================
print("\n[8] 判斷趨勢...")
trend = 'Sideways'
if historical_data is not None and not historical_data.empty and len(historical_data) >= 20:
    sma_20 = historical_data['Close'].tail(20).mean()
    sma_50 = historical_data['Close'].tail(50).mean() if len(historical_data) >= 50 else sma_20
    
    if current_price > sma_20 and sma_20 > sma_50:
        trend = 'Up'
    elif current_price < sma_20 and sma_20 < sma_50:
        trend = 'Down'
    else:
        trend = 'Sideways'
    
    print(f"    SMA(20): ${sma_20:.2f}")
    print(f"    SMA(50): ${sma_50:.2f}")
print(f"    趨勢判斷: {trend}")

# ============================================================
# 判斷估值
# ============================================================
print("\n[9] 判斷估值...")
valuation = 'Fair'
if stock_info:
    eps = stock_info.get('eps', 0)
    if eps and eps > 0:
        pe_ratio = current_price / eps
        if pe_ratio < 10:
            valuation = 'Undervalued'
        elif pe_ratio > 25:
            valuation = 'Overvalued'
        print(f"    EPS: ${eps:.2f}")
        print(f"    P/E: {pe_ratio:.2f}")
print(f"    估值判斷: {valuation}")

# ============================================================
# 策略推薦 (含信心度)
# ============================================================
print("\n" + "=" * 70)
print("策略推薦分析 (含信心度)")
print("=" * 70)

recommender = StrategyRecommender()
recommendations = recommender.recommend(
    current_price=current_price,
    iv_rank=50.0,  # 使用中位數
    iv_percentile=50.0,
    iv_hv_ratio=iv_hv_ratio,
    support_level=support_level,
    resistance_level=resistance_level,
    trend=trend,
    valuation=valuation,
    days_to_expiry=days_to_exp
)

if recommendations:
    for i, rec in enumerate(recommendations, 1):
        confidence_emoji = {
            'High': '🟢',
            'Medium': '🟡',
            'Low': '🔴'
        }.get(rec.confidence, '⚪')
        
        print(f"\n┌─ 推薦 {i}: {rec.strategy_name} ─────────────────────┐")
        print(f"│")
        print(f"│  方向: {rec.direction}")
        print(f"│  信心度: {confidence_emoji} {rec.confidence}")
        print(f"│")
        print(f"│  推薦理由:")
        for reason in rec.reasoning:
            print(f"│    - {reason}")
        print(f"│")
        if rec.suggested_strike:
            print(f"│  建議行使價: ${rec.suggested_strike:.2f}")
        print(f"│  關鍵價位: {rec.key_levels}")
        print(f"└{'─' * 50}┘")
else:
    print("\n  無明確策略推薦")

# ============================================================
# Short Put 損益分析
# ============================================================
print("\n" + "=" * 70)
print("Short Put 損益分析")
print("=" * 70)

short_put_calc = ShortPutCalculator()
scenarios = [
    ('下跌 10%', current_price * 0.9),
    ('持平', current_price),
    ('上漲 10%', current_price * 1.1),
    ('跌至行使價', MANUAL_OPTION_DATA['strike_price']),
]

print(f"\n行使價: ${MANUAL_OPTION_DATA['strike_price']}")
print(f"權利金: ${MANUAL_OPTION_DATA['last_price']}")
print(f"盈虧平衡: ${MANUAL_OPTION_DATA['strike_price'] - MANUAL_OPTION_DATA['last_price']:.2f}")
print()
print(f"{'場景':<12} | {'到期股價':>10} | {'損益':>10} | {'回報率':>10}")
print("-" * 50)

for scenario_name, scenario_price in scenarios:
    result = short_put_calc.calculate(
        strike_price=MANUAL_OPTION_DATA['strike_price'],
        option_premium=MANUAL_OPTION_DATA['last_price'],
        stock_price_at_expiry=scenario_price
    )
    print(f"{scenario_name:<12} | ${scenario_price:>8.2f} | ${result.profit_loss:>8.2f} | {result.return_percentage:>8.1f}%")

# ============================================================
# 動量分析
# ============================================================
print("\n" + "=" * 70)
print("動量分析")
print("=" * 70)

momentum_score = 0.5  # 默認值
momentum_recommendation = '中性'
momentum_confidence = 'Medium'

if historical_data is not None and not historical_data.empty:
    try:
        momentum_filter = MomentumFilter()
        momentum_result = momentum_filter.calculate(
            ticker='ZIM',
            historical_data=historical_data
        )
        
        # MomentumResult 是 dataclass，直接訪問屬性
        score = momentum_result.momentum_score
        momentum_score = score
        momentum_recommendation = momentum_result.recommendation
        momentum_confidence = momentum_result.confidence
        
        bar_length = int(score * 20)
        bar = '█' * bar_length + '░' * (20 - bar_length)
        
        print(f"\n  動量得分: {score:.4f}")
        print(f"  [{bar}] {score*100:.1f}%")
        print(f"  建議: {momentum_result.recommendation}")
        print(f"  信心度: {momentum_result.confidence}")
    except Exception as e:
        print(f"\n  動量計算失敗: {e}")
else:
    print("\n  ! 無法計算動量（缺少歷史數據）")

# ============================================================
# 監察崗位分析
# ============================================================
print("\n" + "=" * 70)
print("12+1 監察崗位分析")
print("=" * 70)

# 計算 ATR
atr = 1.0  # 默認值
if historical_data is not None and not historical_data.empty and len(historical_data) >= 14:
    high = historical_data['High'].values
    low = historical_data['Low'].values
    close = historical_data['Close'].values
    
    tr_list = []
    for i in range(1, len(historical_data)):
        tr = max(
            high[i] - low[i],
            abs(high[i] - close[i-1]),
            abs(low[i] - close[i-1])
        )
        tr_list.append(tr)
    
    if len(tr_list) >= 14:
        atr = sum(tr_list[-14:]) / 14

monitoring_calc = MonitoringPostsCalculator()
try:
    monitoring_result = monitoring_calc.calculate(
        stock_price=current_price,
        option_premium=MANUAL_OPTION_DATA['last_price'],
        iv=MANUAL_OPTION_DATA['implied_volatility'],
        delta=abs(MANUAL_OPTION_DATA['delta']),
        open_interest=MANUAL_OPTION_DATA['open_interest'],
        volume=MANUAL_OPTION_DATA.get('volume', 0) or 0,
        bid_ask_spread=MANUAL_OPTION_DATA['ask'] - MANUAL_OPTION_DATA['bid'],
        atr=atr,
        dividend_date="",
        earnings_date="",
        expiration_date=MANUAL_OPTION_DATA['expiration'],
        vix=vix
    )
    
    # MonitoringPostsResult 是 dataclass
    risk_emoji = {
        '低風險': '�',
        '中風險': '�',
        '高風險': '🔴'
    }.get(monitoring_result.risk_level, '⚪')
    
    print(f"\n  總警報數: {monitoring_result.total_alerts}")
    print(f"  風險等級: {risk_emoji} {monitoring_result.risk_level}")
    
    total_alerts = monitoring_result.total_alerts
    risk_level = monitoring_result.risk_level
except Exception as e:
    print(f"\n  監察崗位計算失敗: {e}")
    total_alerts = 0
    risk_level = '未知'
    risk_emoji = '⚪'

# ============================================================
# 綜合信心度評估
# ============================================================
print("\n" + "=" * 70)
print("綜合信心度評估")
print("=" * 70)

# 計算綜合信心度
confidence_factors = []
confidence_reasons = []

# 1. Delta 因素 (深度價外 = 高信心)
delta_abs = abs(MANUAL_OPTION_DATA['delta'])
if delta_abs < 0.10:
    confidence_factors.append(('Delta', 90, '深度價外，勝率高'))
elif delta_abs < 0.20:
    confidence_factors.append(('Delta', 70, '價外，勝率較高'))
elif delta_abs < 0.30:
    confidence_factors.append(('Delta', 50, '輕度價外'))
else:
    confidence_factors.append(('Delta', 30, '接近平價，風險較高'))

# 2. IV 因素 (高 IV = 賣方有利)
iv = MANUAL_OPTION_DATA['implied_volatility']
if iv > 80:
    confidence_factors.append(('IV', 90, 'IV 極高，賣方優勢明顯'))
elif iv > 50:
    confidence_factors.append(('IV', 70, 'IV 較高，賣方有優勢'))
elif iv > 30:
    confidence_factors.append(('IV', 50, 'IV 中等'))
else:
    confidence_factors.append(('IV', 30, 'IV 偏低，賣方優勢不明顯'))

# 3. IV/HV 比率
if iv_hv_ratio > 1.5:
    confidence_factors.append(('IV/HV', 90, 'IV 顯著高於 HV，期權高估'))
elif iv_hv_ratio > 1.2:
    confidence_factors.append(('IV/HV', 70, 'IV 高於 HV'))
elif iv_hv_ratio > 0.8:
    confidence_factors.append(('IV/HV', 50, 'IV 與 HV 相近'))
else:
    confidence_factors.append(('IV/HV', 30, 'IV 低於 HV，期權可能低估'))

# 4. 流動性
oi = MANUAL_OPTION_DATA['open_interest']
if oi > 5000:
    confidence_factors.append(('流動性', 90, '未平倉量充足'))
elif oi > 1000:
    confidence_factors.append(('流動性', 70, '流動性良好'))
elif oi > 500:
    confidence_factors.append(('流動性', 50, '流動性一般'))
else:
    confidence_factors.append(('流動性', 30, '流動性不足'))

# 5. 買賣價差
spread_pct = (MANUAL_OPTION_DATA['ask'] - MANUAL_OPTION_DATA['bid']) / MANUAL_OPTION_DATA['last_price'] * 100
if spread_pct < 10:
    confidence_factors.append(('價差', 90, '買賣價差小'))
elif spread_pct < 20:
    confidence_factors.append(('價差', 70, '買賣價差可接受'))
elif spread_pct < 50:
    confidence_factors.append(('價差', 50, '買賣價差較大'))
else:
    confidence_factors.append(('價差', 30, '買賣價差過大'))

# 6. 趨勢因素 (Short Put 需要看漲或盤整)
if trend == 'Up':
    confidence_factors.append(('趨勢', 90, '上升趨勢，有利 Short Put'))
elif trend == 'Sideways':
    confidence_factors.append(('趨勢', 70, '盤整，適合 Short Put'))
else:
    confidence_factors.append(('趨勢', 30, '下降趨勢，不利 Short Put'))

# 計算加權平均信心度
weights = {'Delta': 25, 'IV': 20, 'IV/HV': 15, '流動性': 15, '價差': 10, '趨勢': 15}
total_weight = sum(weights.values())
weighted_score = sum(score * weights[name] for name, score, _ in confidence_factors) / total_weight

# 確定信心度等級
if weighted_score >= 75:
    overall_confidence = 'High'
    confidence_emoji = '🟢'
elif weighted_score >= 50:
    overall_confidence = 'Medium'
    confidence_emoji = '🟡'
else:
    overall_confidence = 'Low'
    confidence_emoji = '🔴'

print(f"\n┌─ Short Put ${MANUAL_OPTION_DATA['strike_price']} 信心度分析 ─────────────┐")
print(f"│")
print(f"│  綜合信心度: {confidence_emoji} {overall_confidence} ({weighted_score:.1f}/100)")
print(f"│")
print(f"│  各因素評分:")
for name, score, reason in confidence_factors:
    bar = '█' * (score // 10) + '░' * (10 - score // 10)
    print(f"│    {name:<8}: [{bar}] {score:>3} - {reason}")
print(f"│")
print(f"│  勝率估計: {(1 - delta_abs) * 100:.1f}% (基於 Delta)")
print(f"│")
print(f"└{'─' * 50}┘")

# ============================================================
# 總結
# ============================================================
print("\n" + "=" * 70)
print("Short Put 策略總結")
print("=" * 70)
print(f"\n股票: ZIM @ ${current_price:.2f}")
print(f"策略: Short Put ${MANUAL_OPTION_DATA['strike_price']} @ ${MANUAL_OPTION_DATA['last_price']}")
print(f"到期: {MANUAL_OPTION_DATA['expiration']} ({days_to_exp} 天)")
print(f"\n關鍵指標:")
print(f"  - Delta: {MANUAL_OPTION_DATA['delta']} (深度價外)")
print(f"  - IV: {MANUAL_OPTION_DATA['implied_volatility']}% (較高)")
print(f"  - 盈虧平衡: ${MANUAL_OPTION_DATA['strike_price'] - MANUAL_OPTION_DATA['last_price']:.2f}")
print(f"  - 最大利潤: ${MANUAL_OPTION_DATA['last_price'] * 100:.2f} (每張合約)")
print(f"  - 最大虧損: ${(MANUAL_OPTION_DATA['strike_price'] - MANUAL_OPTION_DATA['last_price']) * 100:.2f} (每張合約)")
print(f"\n綜合評估:")
print(f"  - 信心度: {confidence_emoji} {overall_confidence} ({weighted_score:.1f}/100)")
print(f"  - 勝率估計: {(1 - delta_abs) * 100:.1f}%")
print(f"  - 風險等級: {risk_emoji} {risk_level}")

print("\n" + "=" * 70)
print("分析完成")
print("=" * 70)

# 斷開 IBKR 連接
if hasattr(fetcher, 'ibkr_client') and fetcher.ibkr_client:
    fetcher.ibkr_client.disconnect()
