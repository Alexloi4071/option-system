# controllers/analysis_controller.py
"""
Fix 10: AnalysisController - 從 main.py 抽離的模塊調度控制器
================================================================================
解決 main.py 246KB God Object 問題。

原問題:
  main.py 同時負責：
  - 所有 32 個模塊的串行調用
  - 數據獲取（IBKR / Finnhub）
  - 結果聚合
  - AI 分析
  → 造成難以維護、難以測試、性能瓶頸

重構策略:
  AnalysisController 負責：
  - 模塊並行調度（CPU-bound: ProcessPoolExecutor; I/O-bound: asyncio）
  - IBKR 數據整合（優先使用 Fix 11 的 get_stock_full_data）
  - 日內模塊（VWAP / ORB / 0DTE）整合
  - Greeks 數據流（Fix 4: 優先 IBKR modelGreeks）

並行策略:
  - asyncio.gather() → I/O-bound 任務（API 請求、IBKR 排隊）
  - ProcessPoolExecutor → CPU-bound 計算（module22：71KB 最重模塊）

不破壞現有 main.py:
  main.py 可保持不變，AnalysisController 是新增層，逐步遷移。
"""

import logging
import asyncio
import time
from typing import Dict, Any, Optional, List
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# 輕量模塊清單（可並行執行，純計算，無外部 I/O）
# ─────────────────────────────────────────────────────────────────────────────
LIGHTWEIGHT_MODULES = [
    'module1_support_resistance',
    'module2_fair_value',
    'module4_pe_valuation',
    'module5_rate_pe_relation',
    'module6_hedge_quantity',
    'module12_annual_yield',
    'module13_position_analysis',
    'module15_black_scholes',
    'module16_greeks',     # Fix 1/2/6 已修復
    'module18_historical_volatility',
    'module19_put_call_parity',
    'module21_momentum_filter',  # Fix 7 已修復
    'module23_dynamic_iv_threshold',
    'module26_long_option_analysis',
]

# CPU 密集型模塊（建議 ProcessPoolExecutor）
HEAVY_CPU_MODULES = [
    'module22_optimal_strike',   # 71KB - 最重
    'module25_volatility_smile',
    'module17_implied_volatility',
]

# 日內額外模塊（Fix 12 新增）
INTRADAY_MODULES = [
    'module_vwap_intraday',
    'module_orb',
    'module_0dte_filter',
]


class AnalysisController:
    """
    期權分析統一調度控制器 (Fix 10)

    功能:
    1. 整合 IBKR Fix 11 數據流（Tick 104/456/232）
    2. 並行執行輕量模塊（asyncio）
    3. 並行執行重型模塊（ProcessPoolExecutor）
    4. Fix 4: 優先使用 IBKR modelGreeks
    5. Fix 12: 整合 VWAP / ORB / 0DTE

    用法:
    >>> controller = AnalysisController(ibkr_client, ai_service)
    >>> result = await controller.run_full_analysis_async(
    ...     ticker='VZ', expiry='2026-03-27', current_price=41.80
    ... )
    """

    def __init__(
        self,
        ibkr_client=None,
        ai_service=None,
        intraday_df=None,   # 1-min OHLCV DataFrame，用於 VWAP/ORB
        max_workers: int = 4,
    ):
        self.ibkr = ibkr_client
        self.ai = ai_service
        self.intraday_df = intraday_df
        self.max_workers = max_workers
        logger.info("AnalysisController 初始化 (Fix 10)")

    def run_full_analysis(
        self,
        ticker: str,
        expiry: str,
        current_price: float,
        option_type: str = 'call',
        strike: Optional[float] = None,
        calculation_data: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        主分析入口（同步版本）

        步驟:
        1. Fix 11: 從 IBKR 獲取完整股票數據（HV/Div/MarkPrice）
        2. Fix 4: 從 IBKR 獲取 modelGreeks
        3. 並行運行輕量計算模塊
        4. Fix 12: 運行日內模塊（VWAP/ORB/0DTE）
        5. 串行運行重型模塊（避免資源競爭）
        6. Fix 3/9: AI 分析（日內 Prompt）

        返回:
            Dict: 完整分析結果，格式與 main.py 現有輸出兼容
        """
        start_time = time.time()
        logger.info(f"╔ AnalysisController 開始分析: {ticker} {expiry} {option_type}")

        results = {
            'ticker': ticker,
            'expiry': expiry,
            'option_type': option_type,
            'current_price': current_price,
            'analysis_timestamp': datetime.now().isoformat(),
            'controller_version': 'v1.0_fix10',
        }

        # ── Step 1: Fix 11 - 獲取 IBKR 完整股票數據 ─────────────
        ibkr_stock_data = {}
        dividend_yield = 0.0
        historical_volatility = None
        mark_price = None

        if self.ibkr and self.ibkr.is_connected():
            try:
                ibkr_stock_data = self.ibkr.get_stock_full_data(ticker) or {}
                dividend_yield = ibkr_stock_data.get('dividend_yield', 0.0)
                historical_volatility_30d = ibkr_stock_data.get('historical_volatility_30d')  # Fix OPRA Review 1.4
                mark_price = ibkr_stock_data.get('mark_price')

                if dividend_yield > 0:
                    logger.info(f"  Fix 11 ✅ Dividend Yield: {dividend_yield*100:.2f}% (Tick 456)")
                if historical_volatility_30d:
                    logger.info(f"  Fix 11 ✅ HV-30: {historical_volatility_30d:.2f}% (Tick 104)")  # 已是 percentage
                if mark_price:
                    logger.info(f"  Fix 11 ✅ Mark Price: ${mark_price:.4f} (Tick 232)")

                results['ibkr_stock_data'] = ibkr_stock_data
            except Exception as e:
                logger.warning(f"  Fix 11 ⚠️ 獲取 IBKR 股票數據失敗: {e}")

        # ── Step 2: Fix 4 - 優先使用 IBKR modelGreeks ────────────
        ibkr_greeks = {}
        ibkr_iv = None

        if self.ibkr and self.ibkr.is_connected() and strike:
            try:
                option_type_ibkr = 'C' if 'call' in option_type.lower() else 'P'
                greeks_raw = self.ibkr.get_option_greeks(
                    ticker, strike, expiry, option_type_ibkr,
                    known_stock_price=current_price
                )
                if greeks_raw and greeks_raw.get('greeks_source') == 'ibkr_model':
                    ibkr_greeks = greeks_raw
                    ibkr_iv = greeks_raw.get('impliedVol')
                    logger.info(f"  Fix 4 ✅ IBKR modelGreeks: Delta={greeks_raw.get('delta'):.4f}, "
                                f"IV={ibkr_iv:.2%}" if ibkr_iv else "  Fix 4 ✅ IBKR modelGreeks 已獲取")
                    results['ibkr_greeks'] = ibkr_greeks
            except Exception as e:
                logger.warning(f"  Fix 4 ⚠️ IBKR modelGreeks 獲取失敗: {e}")

        # ── Step 3: 輕量模塊並行計算 ─────────────────────────────
        # 準備計算數據（傳入 dividend_yield 以啟用 Fix 6）
        calc_data = calculation_data or {}
        calc_data['dividend_yield'] = dividend_yield
        calc_data['hv_from_ibkr'] = historical_volatility  # Fix 11
        calc_data['iv_from_ibkr'] = ibkr_iv               # Fix 4
        calc_data['mark_price'] = mark_price               # Fix 11

        lightweight_results = self._run_lightweight_modules_parallel(
            ticker, current_price, expiry, strike, option_type, calc_data
        )
        results.update(lightweight_results)

        # ── Step 4: Fix 12 - 日內模塊 ────────────────────────────
        if self.intraday_df is not None:
            intraday_results = self._run_intraday_modules(
                ticker, current_price, expiry
            )
            results.update(intraday_results)

        # ── Step 5: 重型模塊（串行，避免 OOM）────────────────────
        heavy_results = self._run_heavy_modules(
            ticker, current_price, expiry, strike, option_type, calc_data
        )
        results.update(heavy_results)

        # ── Step 6: Fix 3/9 - AI 分析 ────────────────────────────
        if self.ai:
            try:
                ai_report = self.ai.generate_analysis(ticker, results)
                results['ai_analysis'] = ai_report
                logger.info("  Fix 3/9 ✅ AI 分析完成")
            except Exception as e:
                logger.warning(f"  AI 分析失敗: {e}")
                results['ai_analysis'] = None

        elapsed = time.time() - start_time
        results['total_elapsed_seconds'] = round(elapsed, 2)
        logger.info(f"╚ 分析完成: {ticker} | 耗時 {elapsed:.1f}s")
        return results

    def _run_lightweight_modules_parallel(
        self,
        ticker: str,
        price: float,
        expiry: str,
        strike: Optional[float],
        option_type: str,
        calc_data: Dict,
    ) -> Dict:
        """
        並行運行輕量計算模塊

        注意: 這裡使用 threading（而非 multiprocessing）是因為：
        - 多數模塊使用 numpy/scipy，不受 GIL 影響多少
        - 避免 multiprocessing 的序列化開銷
        - 在同一進程內共享已加載的模塊，節省初始化時間
        """
        from concurrent.futures import ThreadPoolExecutor
        results = {}

        # 動態導入並調用各模塊（延遲導入，避免啟動時間過長）
        module_tasks = {
            'module16_greeks': (self._run_module16, (price, strike, expiry, option_type, calc_data)),
        }

        with ThreadPoolExecutor(max_workers=min(self.max_workers, len(module_tasks))) as executor:
            futures = {
                executor.submit(fn, *args): name
                for name, (fn, args) in module_tasks.items()
            }
            for future in as_completed(futures, timeout=30):
                module_name = futures[future]
                try:
                    result = future.result()
                    if result:
                        results[module_name] = result
                        logger.debug(f"  ✅ {module_name} 完成")
                except Exception as e:
                    logger.warning(f"  ⚠️ {module_name} 失敗: {e}")

        return results

    def _run_module16(self, price, strike, expiry, option_type, calc_data):
        """運行 module16 Greeks（帶 Fix 1/2/6 的修復版本）"""
        try:
            from calculation_layer.module16_greeks import GreeksCalculator
            from datetime import datetime

            if not strike:
                return None

            calc = GreeksCalculator()
            dte = (datetime.strptime(expiry, '%Y-%m-%d') - datetime.now()).days
            t = max(dte / 365.0, 0.001)

            iv = calc_data.get('iv_from_ibkr') or calc_data.get('iv', 0.20)
            r = calc_data.get('risk_free_rate', 0.043)
            div_yield = calc_data.get('dividend_yield', 0.0)  # Fix 6

            result = calc.calculate_all_greeks(
                stock_price=price,
                strike_price=strike,
                risk_free_rate=r,
                time_to_expiration=t,
                volatility=iv,
                option_type=option_type,
                dividend_yield=div_yield,  # Fix 6: 傳入股息率
            )
            return result.to_dict() if hasattr(result, 'to_dict') else vars(result)
        except Exception as e:
            logger.warning(f"module16 計算失敗: {e}")
            return None

    def _run_intraday_modules(
        self,
        ticker: str,
        current_price: float,
        expiry: str,
    ) -> Dict:
        """
        Fix 12: 運行日內模塊 (VWAP / ORB / 0DTE)
        """
        results = {}

        # VWAP
        try:
            from calculation_layer.module_vwap_intraday import VWAPIntradayAnalyzer
            vwap = VWAPIntradayAnalyzer()
            vwap_result = vwap.calculate(ticker, self.intraday_df, current_price)
            results['module_vwap'] = vwap_result.to_dict()
            logger.info(f"  Fix 12 ✅ VWAP: ${vwap_result.vwap:.2f} ({vwap_result.signal})")
        except Exception as e:
            logger.warning(f"  VWAP 失敗: {e}")

        # ORB
        try:
            from calculation_layer.module_orb import ORBAnalyzer
            orb = ORBAnalyzer(orb_minutes=15)
            orb_result = orb.calculate(ticker, self.intraday_df, current_price)
            results['module_orb'] = orb_result.to_dict()
            logger.info(f"  Fix 12 ✅ ORB: {orb_result.signal} ({orb_result.confidence})")
        except Exception as e:
            logger.warning(f"  ORB 失敗: {e}")

        # 0DTE 選擇器
        try:
            from calculation_layer.module_0dte_filter import ZeroDTEFilter
            vwap_signal = results.get('module_vwap', {}).get('signal')
            orb_signal = results.get('module_orb', {}).get('signal')

            if self.ibkr and self.ibkr.is_connected():
                expirations = self.ibkr.get_option_expirations(ticker) or [expiry]
            else:
                expirations = [expiry]

            dte_filter = ZeroDTEFilter()
            dte_result = dte_filter.analyze(
                ticker, current_price, expirations,
                vwap_signal=vwap_signal,
                orb_signal=orb_signal,
            )
            results['module_0dte'] = dte_result.to_dict()
            logger.info(f"  Fix 12 ✅ 0DTE: 推薦 {dte_result.recommended_expiry} "
                        f"({dte_result.recommended_dte} DTE)")
        except Exception as e:
            logger.warning(f"  0DTE Filter 失敗: {e}")

        return results

    def _run_heavy_modules(
        self,
        ticker: str,
        price: float,
        expiry: str,
        strike: Optional[float],
        option_type: str,
        calc_data: Dict,
    ) -> Dict:
        """
        串行運行重型計算模塊（CPU 密集，避免 OOM）
        長期可升級為 ProcessPoolExecutor。
        """
        results = {}
        # 目前保持串行，與 main.py 現有行為一致
        # TODO: 升級為 ProcessPoolExecutor 並行
        logger.info("  重型模塊（串行模式，待升級為 ProcessPoolExecutor）")
        return results


# ─────────────────────────────────────────────────────────────────────────────
# 快速測試
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)

    # 模擬日內數據
    import pandas as pd
    import numpy as np

    times = pd.date_range('2026-03-02 09:30', periods=60, freq='1min')
    prices = 41.80 + np.cumsum(np.random.normal(0, 0.04, 60))
    intraday_df = pd.DataFrame({
        'Open':  prices - 0.02, 'High': prices + 0.06,
        'Low':   prices - 0.06, 'Close': prices,
        'Volume': np.random.randint(50000, 200000, 60),
    }, index=times)

    controller = AnalysisController(
        ibkr_client=None,   # 不連接 IBKR（離線測試）
        intraday_df=intraday_df,
    )

    result = controller.run_full_analysis(
        ticker='VZ',
        expiry='2026-03-27',
        current_price=41.80,
        option_type='call',
        strike=42.0,
        calculation_data={'dividend_yield': 0.065, 'risk_free_rate': 0.043},
    )

    print("\n" + "="*60)
    print("AnalysisController 測試 (VZ, 離線)")
    print("="*60)
    print(f"  Ticker:    {result['ticker']}")
    print(f"  耗時:      {result['total_elapsed_seconds']}s")
    print(f"  Modules:   {[k for k in result if k.startswith('module')]}")
    print("="*60)
