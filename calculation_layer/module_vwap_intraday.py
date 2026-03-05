# calculation_layer/module_vwap_intraday.py
"""
模塊: VWAP 日內分析器 (Volume Weighted Average Price)
Fix 12 長期升級 - 新增日內核心模塊

功能:
- VWAP 計算（基於成交量加權）
- 價格與 VWAP 的相對位置分析
- VWAP Bands（標準差）
- 日內交易信號生成

VWAP 公式:
  VWAP = Σ(Price × Volume) / Σ(Volume)
  Price = (High + Low + Close) / 3  (典型價格)

交易信號:
  - 多頭信號: 當前價格 > VWAP 且回落至 VWAP 附近反彈
  - 空頭信號: 當前價格 < VWAP 且反彈至 VWAP 附近回落

VWAP Band:
  - Upper Band 1: VWAP + 1× 標準差
  - Lower Band 1: VWAP - 1× 標準差
  - Upper Band 2: VWAP + 2× 標準差
  - Lower Band 2: VWAP - 2× 標準差

參考:
  - Kroll, S. (1993). The Professional Commodity Trader
  - 標準日內交易實務
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime, date

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class VWAPResult:
    """VWAP 計算結果"""
    ticker: str
    current_price: float
    vwap: float
    price_vs_vwap_pct: float      # 當前價格相對 VWAP 的百分比偏差
    position: str                   # 'above_vwap' | 'below_vwap' | 'at_vwap'

    # VWAP Bands
    upper_band_1: float
    lower_band_1: float
    upper_band_2: float
    lower_band_2: float

    # 信號
    signal: str           # 'bullish' | 'bearish' | 'neutral'
    signal_strength: str  # 'strong' | 'moderate' | 'weak'
    entry_condition: str  # 日內入場描述

    # 統計
    total_volume: int
    data_points: int
    calculation_time: str

    def to_dict(self) -> Dict:
        return {
            'ticker': self.ticker,
            'vwap': round(self.vwap, 4),
            'current_price': round(self.current_price, 4),
            'price_vs_vwap_pct': round(self.price_vs_vwap_pct, 4),
            'position': self.position,
            'bands': {
                'upper_2': round(self.upper_band_2, 4),
                'upper_1': round(self.upper_band_1, 4),
                'vwap': round(self.vwap, 4),
                'lower_1': round(self.lower_band_1, 4),
                'lower_2': round(self.lower_band_2, 4),
            },
            'signal': self.signal,
            'signal_strength': self.signal_strength,
            'entry_condition': self.entry_condition,
            'total_volume': self.total_volume,
            'data_points': self.data_points,
            'calculation_time': self.calculation_time,
        }


class VWAPIntradayAnalyzer:
    """
    VWAP 日內分析器

    適用場景:
    - 0DTE / 1DTE 期權日內入場判斷
    - 確認趨勢方向（多空）
    - 提供動態支撐/阻力位

    使用示例:
    >>> analyzer = VWAPIntradayAnalyzer()
    >>> result = analyzer.calculate(ticker='VZ', intraday_df=df, current_price=41.80)
    >>> print(f"VWAP: ${result.vwap:.2f}, Signal: {result.signal}")
    """

    # VWAP 寬容區域（±0.2% 視為 "AT 位置"）
    AT_VWAP_TOLERANCE_PCT = 0.002

    def calculate(
        self,
        ticker: str,
        intraday_df: pd.DataFrame,
        current_price: float,
    ) -> VWAPResult:
        """
        計算 VWAP 及相關分析

        參數:
            ticker: 股票代碼
            intraday_df: 日內 OHLCV DataFrame，需包含 High, Low, Close, Volume 列
                         索引為時間戳（pandas DatetimeIndex）
            current_price: 當前股價

        返回:
            VWAPResult: 包含 VWAP、Bands、信號等全套結果
        """
        try:
            logger.info(f"開始計算 {ticker} VWAP...")

            # ── 驗證輸入 ──────────────────────────────────────
            required_cols = ['High', 'Low', 'Close', 'Volume']
            missing = [c for c in required_cols if c not in intraday_df.columns]
            if missing:
                raise ValueError(f"DataFrame 缺少必要欄位: {missing}")

            df = intraday_df.copy()

            # 只取今日數據
            if hasattr(df.index, 'date'):
                today = date.today()
                df = df[df.index.date == today]
                if df.empty:
                    logger.warning(f"! {ticker}: 今日無日內數據，使用全部數據")
                    df = intraday_df.copy()

            if len(df) < 2:
                raise ValueError(f"數據點不足: {len(df)} 行（需要至少 2 行）")

            # ── 計算典型價格 ───────────────────────────────────
            # Typical Price = (High + Low + Close) / 3
            df['typical_price'] = (df['High'] + df['Low'] + df['Close']) / 3

            # ── 計算 VWAP ──────────────────────────────────────
            # VWAP = Σ(TP × Volume) / Σ(Volume)
            df['tp_volume'] = df['typical_price'] * df['Volume']
            cumulative_tp_vol = df['tp_volume'].cumsum()
            cumulative_vol = df['Volume'].cumsum()
            df['vwap'] = cumulative_tp_vol / cumulative_vol.replace(0, np.nan)

            vwap = float(df['vwap'].iloc[-1])
            total_volume = int(df['Volume'].sum())

            # ── 計算 VWAP 標準差 Bands ────────────────────────
            # 使用滾動標準差方法計算 VWAP Band
            df['deviation_sq'] = (df['typical_price'] - df['vwap']) ** 2
            df['variance_cumsum'] = (df['deviation_sq'] * df['Volume']).cumsum() / cumulative_vol.replace(0, np.nan)
            df['std_dev'] = np.sqrt(df['variance_cumsum'].clip(lower=0))

            std_dev = float(df['std_dev'].iloc[-1])

            upper_band_1 = vwap + 1 * std_dev
            lower_band_1 = vwap - 1 * std_dev
            upper_band_2 = vwap + 2 * std_dev
            lower_band_2 = vwap - 2 * std_dev

            # ── 價格位置分析 ───────────────────────────────────
            price_vs_vwap_pct = (current_price - vwap) / vwap * 100
            tolerance = vwap * self.AT_VWAP_TOLERANCE_PCT

            if abs(current_price - vwap) <= tolerance:
                position = 'at_vwap'
            elif current_price > vwap:
                position = 'above_vwap'
            else:
                position = 'below_vwap'

            # ── 信號生成 ───────────────────────────────────────
            signal, signal_strength, entry_condition = self._generate_signal(
                current_price, vwap, price_vs_vwap_pct,
                upper_band_1, lower_band_1, upper_band_2, lower_band_2, position
            )

            logger.info(f"  VWAP: ${vwap:.2f} | 現價: ${current_price:.2f} | "
                        f"偏差: {price_vs_vwap_pct:+.2f}% | 信號: {signal} ({signal_strength})")

            return VWAPResult(
                ticker=ticker,
                current_price=current_price,
                vwap=vwap,
                price_vs_vwap_pct=price_vs_vwap_pct,
                position=position,
                upper_band_1=upper_band_1,
                lower_band_1=lower_band_1,
                upper_band_2=upper_band_2,
                lower_band_2=lower_band_2,
                signal=signal,
                signal_strength=signal_strength,
                entry_condition=entry_condition,
                total_volume=total_volume,
                data_points=len(df),
                calculation_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            )

        except Exception as e:
            logger.error(f"x VWAP 計算失敗: {e}")
            raise

    def _generate_signal(
        self,
        current_price: float,
        vwap: float,
        pct: float,
        upper1: float,
        lower1: float,
        upper2: float,
        lower2: float,
        position: str
    ) -> Tuple[str, str, str]:
        """
        生成 VWAP 交易信號

        信號邏輯:
          多頭 (Bullish):
            - 強: 價格在 VWAP 上方 > 0.5% 且未超過 Upper Band 2 (未過熱)
            - 中: 價格從 Lower Band 1 反彈向 VWAP（回調找支撐）
          空頭 (Bearish):
            - 強: 價格在 VWAP 下方 < -0.5% 且未跌破 Lower Band 2
            - 中: 價格從 Upper Band 1 回落向 VWAP
          中性:
            - 價格在 VWAP ±0.2% 內（整固）
        """
        # === 超強趨勢區域（Band 2 以外）===
        if current_price >= upper2:
            return ('bullish', 'strong',
                    f'強烈看漲區（現價超越 VWAP Upper Band 2 ${upper2:.2f}），但注意過熱回調風險')

        if current_price <= lower2:
            return ('bearish', 'strong',
                    f'強烈看跌區（現價跌破 VWAP Lower Band 2 ${lower2:.2f}），反彈前謹慎做多')

        # === Band 1 至 Band 2 之間 ===
        if upper1 <= current_price < upper2:
            return ('bullish', 'moderate',
                    f'看漲: 現價 ${current_price:.2f} 在 VWAP 上方 Band 1-2 間 (${upper1:.2f}-${upper2:.2f})')

        if lower2 < current_price <= lower1:
            return ('bearish', 'moderate',
                    f'看跌: 現價 ${current_price:.2f} 在 VWAP 下方 Band 1-2 間 (${lower2:.2f}-${lower1:.2f})')

        # === VWAP 核心區域 ===
        if position == 'at_vwap':
            return ('neutral', 'weak',
                    f'中性整固: 現價 ${current_price:.2f} ≈ VWAP ${vwap:.2f}，等待方向確認')

        if position == 'above_vwap':
            return ('bullish', 'moderate',
                    f'看漲: 現價 ${current_price:.2f} 在 VWAP ${vwap:.2f} 上方 ({pct:+.2f}%)；'
                    f'入場條件: 回調至 VWAP 附近 (${vwap:.2f}-${upper1:.2f}) 時買入 Call')
        else:
            return ('bearish', 'moderate',
                    f'看跌: 現價 ${current_price:.2f} 在 VWAP ${vwap:.2f} 下方 ({pct:+.2f}%)；'
                    f'入場條件: 反彈至 VWAP 附近 (${lower1:.2f}-${vwap:.2f}) 時買入 Put')

    def calculate_from_ibkr_ticks(
        self,
        ticker: str,
        tick_data: List[Dict],
        current_price: float
    ) -> Optional[VWAPResult]:
        """
        從 IBKR Tick-by-Tick 數據計算 VWAP

        參數:
            ticker: 股票代碼
            tick_data: list of {'time': datetime, 'price': float, 'size': int}
            current_price: 當前股價

        返回:
            VWAPResult，失敗返回 None
        """
        if not tick_data:
            logger.warning(f"! {ticker}: 無 Tick 數據")
            return None

        try:
            df = pd.DataFrame(tick_data)
            df['time'] = pd.to_datetime(df['time'])
            df = df.set_index('time').sort_index()

            # 模擬 OHLCV（tick 轉 1min bar）
            ohlcv = df['price'].resample('1min').ohlc()
            ohlcv['Volume'] = df['size'].resample('1min').sum()
            ohlcv.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            ohlcv = ohlcv.dropna()

            return self.calculate(ticker, ohlcv, current_price)
        except Exception as e:
            logger.error(f"x 從 Tick 數據計算 VWAP 失敗: {e}")
            return None


# ── 模塊單獨測試 ──────────────────────────────────────────
if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)

    # 模擬 VZ 日內數據
    np.random.seed(42)
    times = pd.date_range('2026-03-02 09:30', periods=60, freq='1min')

    base_price = 41.80
    prices = base_price + np.cumsum(np.random.normal(0, 0.05, 60))
    volumes = np.random.randint(50000, 200000, 60)

    df = pd.DataFrame({
        'Open':  prices - 0.02,
        'High':  prices + 0.05,
        'Low':   prices - 0.05,
        'Close': prices,
        'Volume': volumes,
    }, index=times)

    analyzer = VWAPIntradayAnalyzer()
    result = analyzer.calculate('VZ', df, current_price=prices[-1])

    print("\n" + "="*60)
    print("VWAP 日內分析器測試 (VZ)")
    print("="*60)
    r = result.to_dict()
    print(f"  VWAP:           ${r['vwap']:.4f}")
    print(f"  現價:           ${r['current_price']:.4f}")
    print(f"  偏差:           {r['price_vs_vwap_pct']:+.2f}%")
    print(f"  位置:           {r['position']}")
    print(f"  Upper Band 2:   ${r['bands']['upper_2']:.4f}")
    print(f"  Upper Band 1:   ${r['bands']['upper_1']:.4f}")
    print(f"  Lower Band 1:   ${r['bands']['lower_1']:.4f}")
    print(f"  Lower Band 2:   ${r['bands']['lower_2']:.4f}")
    print(f"  信號:           {r['signal']} ({r['signal_strength']})")
    print(f"  入場條件:       {r['entry_condition']}")
    print("="*60)
