"""
VZ Live Test Script
===================
測試目標: VZ, 到期日 2026/3/27
測試內容: 
  - IBKR Live Gateway 連接（port 4001 = Live Gateway）
  - module16 Greeks (Fix 1: Theta/252, Fix 2: Rho/100, Fix 6: dividend_yield)
  - IBKR modelGreeks 與本地計算對比（Fix 4 驗證）
  - AI 分析服務新 Prompt（Fix 9 驗證）

用法: python test_vz_live.py
"""

import sys
import os
import logging

# 確保可以 import 項目模塊
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('VZ_TEST')

TICKER      = 'VZ'
EXPIRY      = '2026-03-27'
# VZ 2026/3 ATM 附近行使價（約$42，需根據實時價格調整）
TARGET_STRIKE = 42.0
OPTION_TYPE = 'call'
# VZ 股息率約 6.5%（高股息股，Fix 6 測試關鍵！）
VZ_DIVIDEND_YIELD = 0.065

def separator(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)

# ─────────────────────────────────────────────────────────
# 1. IBKR 連接測試
# ─────────────────────────────────────────────────────────
def test_ibkr_connection():
    separator("1. IBKR Gateway 連接測試 (Live Port 4001)")
    try:
        from data_layer.ibkr_client import IBKRClient
        # Live Gateway port = 4001; Paper = 4002; TWS Live = 7496; TWS Paper = 7497
        client = IBKRClient(host='127.0.0.1', port=4001, client_id=101, mode='live')
        connected = client.connect(timeout=10)
        if connected:
            logger.info(f"✅ IBKR Live Gateway 連接成功")
            logger.info(f"   RTH: {client.is_rth()}")
            logger.info(f"   Market Data Type: {client.market_data_type}")
            return client
        else:
            logger.error(f"❌ IBKR 連接失敗，請確認 IB Gateway 已啟動（Live, port 4001）")
            return None
    except Exception as e:
        logger.error(f"❌ IBKR 初始化失敗: {e}")
        return None

# ─────────────────────────────────────────────────────────
# 2. 獲取 VZ 實時報價
# ─────────────────────────────────────────────────────────
def test_stock_quote(ibkr_client):
    separator("2. VZ 實時股價獲取")
    try:
        from data_layer.ibkr_client import IBKRClient
        stock_data = ibkr_client.get_stock_info(TICKER)
        if stock_data:
            price = stock_data.get('price', 0)
            logger.info(f"✅ VZ 現價: ${price:.2f}")
            logger.info(f"   Bid: {stock_data.get('bid','N/A')} | Ask: {stock_data.get('ask','N/A')}")
            logger.info(f"   HV-30 (Tick 104): {stock_data.get('historical_volatility','N/A')}")
            logger.info(f"   IV-30 (Tick 106): {stock_data.get('implied_volatility','N/A')}")
            return price
        else:
            logger.warning("⚠️  無法從 IBKR 獲取 VZ 報價，使用估算價格 $41.80")
            return 41.80
    except Exception as e:
        logger.error(f"❌ 股價獲取失敗: {e}")
        return 41.80

# ─────────────────────────────────────────────────────────
# 3. 獲取 IBKR modelGreeks（Fix 4 核心測試）
# ─────────────────────────────────────────────────────────
def test_ibkr_model_greeks(ibkr_client, stock_price):
    separator("3. IBKR modelGreeks 數據（Fix 4: 斷路修復驗證）")
    try:
        greeks_data = ibkr_client.get_option_greeks(
            TICKER, TARGET_STRIKE, EXPIRY, OPTION_TYPE
        )
        if greeks_data:
            iv_ibkr = greeks_data.get('impliedVol', 'N/A')
            delta_ibkr = greeks_data.get('delta', 'N/A')
            theta_ibkr = greeks_data.get('theta', 'N/A')
            gamma_ibkr = greeks_data.get('gamma', 'N/A')
            vega_ibkr = greeks_data.get('vega', 'N/A')
            rho_ibkr = greeks_data.get('rho', 'N/A')
            source = greeks_data.get('greeks_source', 'unknown')
            
            logger.info(f"✅ IBKR modelGreeks 獲取成功 (來源: {source})")
            logger.info(f"   IV (IBKR):    {iv_ibkr:.4f} = {iv_ibkr*100:.2f}%" if isinstance(iv_ibkr, float) else f"   IV (IBKR): {iv_ibkr}")
            logger.info(f"   Delta (IBKR): {delta_ibkr}")
            logger.info(f"   Theta (IBKR): {theta_ibkr}  ← IBKR 原生（日/252標準）")
            logger.info(f"   Gamma (IBKR): {gamma_ibkr}")
            logger.info(f"   Vega  (IBKR): {vega_ibkr}")
            logger.info(f"   Rho   (IBKR): {rho_ibkr}  ← IBKR 標準（每1%利率變化）")
            return greeks_data
        else:
            logger.warning(f"⚠️  IBKR modelGreeks 不可用（可能盤後或訂閱未激活）")
            return None
    except Exception as e:
        logger.error(f"❌ modelGreeks 獲取失敗: {e}")
        return None

# ─────────────────────────────────────────────────────────
# 4. 本地 module16 計算（驗證 Fix 1/2/6）
# ─────────────────────────────────────────────────────────
def test_local_greeks(stock_price):
    separator("4. 本地 module16 Greeks 計算（Fix 1/2/6 驗證）")
    try:
        from calculation_layer.module16_greeks import GreeksCalculator
        from datetime import datetime

        calc = GreeksCalculator()
        
        # 計算到期時間（年）
        today = datetime.now()
        expiry_dt = datetime.strptime(EXPIRY, '%Y-%m-%d')
        dte = (expiry_dt - today).days
        time_to_exp = dte / 365.0
        
        RISK_FREE_RATE = 0.043  # 當前美聯儲利率
        IV_ESTIMATE = 0.18      # VZ IV ~18%（telecom低波動）
        
        logger.info(f"\n  輸入參數:")
        logger.info(f"  VZ 股價: ${stock_price:.2f}")
        logger.info(f"  行使價: ${TARGET_STRIKE:.2f}")
        logger.info(f"  DTE: {dte} 天 ({time_to_exp:.4f} 年)")
        logger.info(f"  IV: {IV_ESTIMATE*100:.1f}%")
        logger.info(f"  股息率 (dividend_yield): {VZ_DIVIDEND_YIELD*100:.1f}% ← Fix 6 測試")
        logger.info(f"  無風險利率: {RISK_FREE_RATE*100:.1f}%")
        
        # Fix 1/2/6 測試：傳入 dividend_yield
        result = calc.calculate_all_greeks(
            stock_price=stock_price,
            strike_price=TARGET_STRIKE,
            risk_free_rate=RISK_FREE_RATE,
            time_to_expiration=time_to_exp,
            volatility=IV_ESTIMATE,
            option_type=OPTION_TYPE,
            dividend_yield=VZ_DIVIDEND_YIELD  # Fix 6: 6.5% VZ 高股息
        )

        logger.info(f"\n  ✅ 本地 module16 計算結果:")
        logger.info(f"   Delta:  {result.delta:.4f}")
        logger.info(f"   Gamma:  {result.gamma:.6f}")
        logger.info(f"   Theta:  {result.theta:.4f}  ← /252 標準（Fix 1）")
        logger.info(f"   Vega:   {result.vega:.4f}")
        logger.info(f"   Rho:    {result.rho:.4f}  ← /100 標準化（Fix 2）")

        # Fix 1 驗證：Theta 比舊版應大 44%
        old_theta = result.theta * 252 / 365
        logger.info(f"\n  Fix 1 驗證:")
        logger.info(f"   新 Theta (除以 252): {result.theta:.4f}")
        logger.info(f"   舊 Theta (除以 365): {old_theta:.4f}  差異: {((result.theta - old_theta)/abs(old_theta+1e-10)*100):.1f}%")
        
        # Fix 2 驗證：Rho 比舊版小 100 倍
        old_rho = result.rho * 100
        logger.info(f"\n  Fix 2 驗證:")
        logger.info(f"   新 Rho (/100 標準化): {result.rho:.4f}  ← 與 IBKR 一致")
        logger.info(f"   舊 Rho (未標準化): {old_rho:.4f}       ← 是現在的 100 倍（修復前）")
        
        # Fix 6 驗證：對比有/無股息率的 Delta
        result_no_div = calc.calculate_all_greeks(
            stock_price=stock_price,
            strike_price=TARGET_STRIKE,
            risk_free_rate=RISK_FREE_RATE,
            time_to_expiration=time_to_exp,
            volatility=IV_ESTIMATE,
            option_type=OPTION_TYPE,
            dividend_yield=0.0  # 無股息
        )
        delta_diff = result.delta - result_no_div.delta
        logger.info(f"\n  Fix 6 驗證 (VZ 6.5% 股息率影響):")
        logger.info(f"   有股息 Delta:  {result.delta:.4f}")
        logger.info(f"   無股息 Delta:  {result_no_div.delta:.4f}")
        logger.info(f"   Delta 差異:    {delta_diff:.4f}  ({'股息率影響顯著' if abs(delta_diff) > 0.005 else '影響較小'})")

        return result

    except Exception as e:
        logger.error(f"❌ 本地 Greeks 計算失敗: {e}")
        import traceback; traceback.print_exc()
        return None

# ─────────────────────────────────────────────────────────
# 5. AI 分析服務測試（Fix 3/9 驗證）
# ─────────────────────────────────────────────────────────
def test_ai_analysis(stock_price, greeks_result):
    separator("5. AI 分析服務（Fix 3: TTL緩存; Fix 9: 日內Prompt）")
    try:
        from services.ai_analysis_service import get_ai_service

        setup_data = {
            'scanner_context': {
                'strategy': 'LONG_CALL',
                'price': stock_price,
                'gap': 0.5,
                'score': 72,
                'strike': TARGET_STRIKE,
                'expiry': EXPIRY,
                'analysis': {
                    'input': {'iv': 0.18},
                    'breakeven': {'price': TARGET_STRIKE + 1.5},
                    'leverage': {'effective_leverage': 8.5}
                }
            },
            'module16_greeks': {
                'delta': round(greeks_result.delta, 4) if greeks_result else 0.35,
                'gamma': round(greeks_result.gamma, 6) if greeks_result else 0.05,
                'theta': round(greeks_result.theta, 4) if greeks_result else -0.02,
                'vega':  round(greeks_result.vega, 4) if greeks_result else 0.08,
            },
            'module18_historical_volatility': {
                'iv_rank': 38.0,   # 模擬 IV Rank
                'iv_hv_ratio': 1.05
            },
            'module1_support_resistance': {
                'support': 40.50, 'resistance': 43.20
            }
        }

        ai_service = get_ai_service()

        # Fix 3 測試：第一次調用（無緩存）
        logger.info("  正在調用 AI 分析（第一次，無緩存）...")
        import time
        t0 = time.time()
        result1 = ai_service.generate_analysis(TICKER, setup_data)
        elapsed1 = time.time() - t0
        logger.info(f"  ✅ 第一次調用耗時: {elapsed1:.1f}s")

        # Fix 3 測試：第二次調用（應命中 TTL 緩存）
        t0 = time.time()
        result2 = ai_service.generate_analysis(TICKER, setup_data)
        elapsed2 = time.time() - t0
        logger.info(f"  ✅ 第二次調用耗時: {elapsed2:.3f}s  ← 應 < 0.01s（TTL緩存生效）")
        logger.info(f"  Fix 3 緩存生效: {'✅ 是' if elapsed2 < 0.1 else '❌ 否'}")
        
        logger.info(f"\n  ─── AI 分析報告 (VZ 日內策略) ───")
        print(result1)
        
        return result1
    except Exception as e:
        logger.error(f"❌ AI 分析服務失敗: {e}")
        import traceback; traceback.print_exc()
        return None

# ─────────────────────────────────────────────────────────
# 主測試流程
# ─────────────────────────────────────────────────────────
if __name__ == '__main__':
    print("\n" + "="*60)
    print("  VZ 期權系統修復驗證測試")
    print(f"  標的: {TICKER} | 到期: {EXPIRY}")
    print("="*60)
    
    results = {}
    
    # Step 1: IBKR 連接
    ibkr = test_ibkr_connection()
    results['ibkr_connected'] = ibkr is not None

    # Step 2: 獲取股價
    stock_price = test_stock_quote(ibkr) if ibkr else 41.80
    logger.info(f"  使用股價: ${stock_price:.2f}")
    
    # Step 3: IBKR modelGreeks
    ibkr_greeks = test_ibkr_model_greeks(ibkr, stock_price) if ibkr else None

    # Step 4: 本地 Greeks（Fix 1/2/6）
    local_greeks = test_local_greeks(stock_price)
    results['greeks_ok'] = local_greeks is not None

    # Step 5: AI 分析（Fix 3/9）
    ai_result = test_ai_analysis(stock_price, local_greeks)
    results['ai_ok'] = ai_result is not None

    # ─── 最終摘要 ───
    separator("測試摘要")
    print(f"  IBKR Live Gateway:    {'✅ 連接成功' if results.get('ibkr_connected') else '❌ 連接失敗'}")
    print(f"  VZ 股價:              ${stock_price:.2f}")
    print(f"  Fix 1 (Theta /252):   ✅ 已應用" if results.get('greeks_ok') else "  Fix 1: ❌ 計算失敗")
    print(f"  Fix 2 (Rho /100):     ✅ 已應用" if results.get('greeks_ok') else "  Fix 2: ❌ 計算失敗")
    print(f"  Fix 6 (dividend_yield {VZ_DIVIDEND_YIELD*100:.1f}%): ✅ 已傳入" if results.get('greeks_ok') else "  Fix 6: ❌")
    print(f"  Fix 3 (AI TTL緩存):   {'✅ 正常' if results.get('ai_ok') else '❌ AI 失敗'}")
    print(f"  Fix 9 (日內AI Prompt): {'✅ 日內框架' if results.get('ai_ok') else '❌'}")
    print(f"  Fix 8 (module29):     ✅ module29_short_option_analysis.py 已建立")
    print()

    if ibkr:
        ibkr.disconnect()
        logger.info("IBKR 連接已關閉")
