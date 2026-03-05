# calculation_layer/module_orb.py
"""
模塊: 開盤區間突破分析器 (Opening Range Breakout - ORB)
Fix 12 長期升級 - 新增日內核心模塊

功能:
- 計算開盤區間（前 N 分鐘的 High/Low）
- 偵測突破方向（上突破/下突破）
- 計算突破目標價位和止損位
- 提供期權策略建議（0DTE/1DTE）

ORB 理論（基於 ORB 之父 Toby Crabel）:
  - 開盤 N 分鐘（通常 15 或 30 分鐘）形成交易區間
  - 收盤前的主要趨勢方向通常與突破方向一致
  - 突破上軌 → 看漲信號 → Long Call
  - 突破下軌 → 看跌信號 → Long Put

目標計算:
  - Target 1: 突破點 + 1× 開盤區間寬度
  - Target 2: 突破點 + 2× 開盤區間寬度
  - Stop Loss: 突破點 - 0.5× 開盤區間寬度（回撤入區間）

參考:
  - Crabel, T. (1990). Day Trading with Short Term Price Patterns and Opening Range Breakout
  - 現代日內交易實務（ORB 15/30 分鐘版）
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime, time as dt_time, date

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ORBResult:
    """開盤區間突破分析結果"""
    ticker: str
    orb_minutes: int              # 使用的開盤區間分鐘數

    # 開盤區間
    opening_high: float
    opening_low: float
    opening_range: float          # High - Low
    opening_range_pct: float      # 佔股價百分比

    # 當前狀態
    current_price: float
    status: str                   # 'above_orb' | 'below_orb' | 'inside_orb'
    breakout_direction: str       # 'bullish' | 'bearish' | 'none'
    breakout_pct: float           # 突破幅度（佔開盤區間的%）

    # 價位目標（突破時才有意義）
    target_1: float
    target_2: float
    stop_loss: float

    # 信號
    signal: str           # 'long_call' | 'long_put' | 'wait'
    confidence: str       # 'high' | 'medium' | 'low'
    reasoning: str

    # 期權建議
    option_suggestion: str

    calculation_time: str

    def to_dict(self) -> Dict:
        return {
            'ticker': self.ticker,
            'orb_minutes': self.orb_minutes,
            'opening_range': {
                'high': round(self.opening_high, 4),
                'low': round(self.opening_low, 4),
                'range': round(self.opening_range, 4),
                'range_pct': round(self.opening_range_pct, 4),
            },
            'current_price': round(self.current_price, 4),
            'status': self.status,
            'breakout_direction': self.breakout_direction,
            'breakout_pct': round(self.breakout_pct, 4),
            'targets': {
                'target_1': round(self.target_1, 4),
                'target_2': round(self.target_2, 4),
                'stop_loss': round(self.stop_loss, 4),
            },
            'signal': self.signal,
            'confidence': self.confidence,
            'reasoning': self.reasoning,
            'option_suggestion': self.option_suggestion,
            'calculation_time': self.calculation_time,
        }


class ORBAnalyzer:
    """
    開盤區間突破分析器

    適用場景:
    - 0DTE 期權日內入場（最常用）
    - 確認突破方向後入場
    - 設定明確的目標價和止損

    使用示例:
    >>> analyzer = ORBAnalyzer(orb_minutes=15)
    >>> result = analyzer.calculate(ticker='VZ', intraday_df=df, current_price=41.80)
    >>> print(f"ORB: {result.signal} | Target: ${result.target_1:.2f}")
    """

    # 支援的開盤區間分鐘數
    VALID_ORB_MINUTES = [5, 10, 15, 30]

    # 突破確認閾值（過濾假突破）
    BREAKOUT_THRESHOLD_PCT = 0.001  # 0.1% 突破才算有效

    def __init__(self, orb_minutes: int = 15):
        """
        初始化 ORB 分析器

        參數:
            orb_minutes: 開盤區間分鐘數（5/10/15/30）
        """
        if orb_minutes not in self.VALID_ORB_MINUTES:
            logger.warning(f"! ORB 分鐘數 {orb_minutes} 不標準，建議使用 {self.VALID_ORB_MINUTES}")
        self.orb_minutes = orb_minutes
        logger.info(f"* ORB 分析器初始化 (區間: 前 {orb_minutes} 分鐘)")

    def calculate(
        self,
        ticker: str,
        intraday_df: pd.DataFrame,
        current_price: float,
        market_open: dt_time = dt_time(9, 30),
    ) -> ORBResult:
        """
        計算 ORB 並生成交易信號

        參數:
            ticker: 股票代碼
            intraday_df: 1分鐘 OHLCV DataFrame，索引為 DatetimeIndex
            current_price: 當前股價
            market_open: 市場開盤時間（默認 09:30 ET）

        返回:
            ORBResult: 完整 ORB 分析結果
        """
        try:
            logger.info(f"開始計算 {ticker} ORB ({self.orb_minutes} 分鐘)...")

            required_cols = ['High', 'Low', 'Close']
            missing = [c for c in required_cols if c not in intraday_df.columns]
            if missing:
                raise ValueError(f"DataFrame 缺少欄位: {missing}")

            df = intraday_df.copy()

            # ── 過濾今日數據 ───────────────────────────────────
            if hasattr(df.index, 'date'):
                today = date.today()
                df = df[df.index.date == today]

            if df.empty:
                logger.warning(f"! {ticker}: 無今日數據，使用全部數據")
                df = intraday_df.copy()

            # ── 取開盤區間數據 ─────────────────────────────────
            # 篩選 09:30 至 09:30+N 的數據
            open_cutoff_time = dt_time(
                market_open.hour,
                market_open.minute + self.orb_minutes
            ) if market_open.minute + self.orb_minutes < 60 else dt_time(
                market_open.hour + (market_open.minute + self.orb_minutes) // 60,
                (market_open.minute + self.orb_minutes) % 60
            )

            if hasattr(df.index, 'time'):
                orb_slice = df[
                    (df.index.time >= market_open) &
                    (df.index.time <= open_cutoff_time)
                ]
            else:
                # 如果索引沒有 time 屬性，取前 N 行
                orb_slice = df.head(self.orb_minutes)

            if orb_slice.empty:
                logger.warning(f"! {ticker}: 開盤區間數據為空，使用前 {min(self.orb_minutes, len(df))} 行")
                orb_slice = df.head(self.orb_minutes)

            # ── 計算開盤區間 ───────────────────────────────────
            opening_high = float(orb_slice['High'].max())
            opening_low  = float(orb_slice['Low'].min())
            opening_range = opening_high - opening_low
            opening_range_pct = (opening_range / current_price) * 100 if current_price > 0 else 0

            logger.info(f"  開盤區間: High=${opening_high:.2f} / Low=${opening_low:.2f} / "
                        f"Range=${opening_range:.2f} ({opening_range_pct:.2f}%)")

            # ── 突破分析 ───────────────────────────────────────
            breakout_threshold = opening_range * self.BREAKOUT_THRESHOLD_PCT

            if current_price > opening_high + breakout_threshold:
                status = 'above_orb'
                breakout_direction = 'bullish'
                breakout_pct = (current_price - opening_high) / opening_range * 100

                # 看漲目標
                target_1 = opening_high + opening_range
                target_2 = opening_high + 2 * opening_range
                stop_loss = opening_high - 0.5 * opening_range  # 回到區間內即止損

            elif current_price < opening_low - breakout_threshold:
                status = 'below_orb'
                breakout_direction = 'bearish'
                breakout_pct = (opening_low - current_price) / opening_range * 100

                # 看跌目標
                target_1 = opening_low - opening_range
                target_2 = opening_low - 2 * opening_range
                stop_loss = opening_low + 0.5 * opening_range  # 回到區間內即止損

            else:
                status = 'inside_orb'
                breakout_direction = 'none'
                breakout_pct = 0.0
                # 使用開盤區間邊界作為潛在突破目標
                target_1 = opening_high
                target_2 = opening_high + opening_range
                stop_loss = opening_low

            # ── 生成信號 ───────────────────────────────────────
            signal, confidence, reasoning, option_suggestion = self._generate_signal(
                breakout_direction, breakout_pct, opening_range_pct,
                current_price, opening_high, opening_low, target_1, stop_loss
            )

            logger.info(f"  突破方向: {breakout_direction} | 信號: {signal} ({confidence})")

            return ORBResult(
                ticker=ticker,
                orb_minutes=self.orb_minutes,
                opening_high=opening_high,
                opening_low=opening_low,
                opening_range=opening_range,
                opening_range_pct=opening_range_pct,
                current_price=current_price,
                status=status,
                breakout_direction=breakout_direction,
                breakout_pct=breakout_pct,
                target_1=target_1,
                target_2=target_2,
                stop_loss=stop_loss,
                signal=signal,
                confidence=confidence,
                reasoning=reasoning,
                option_suggestion=option_suggestion,
                calculation_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            )

        except Exception as e:
            logger.error(f"x ORB 計算失敗: {e}")
            raise

    def _generate_signal(
        self,
        direction: str,
        breakout_pct: float,
        range_pct: float,
        current_price: float,
        orb_high: float,
        orb_low: float,
        target: float,
        stop: float,
    ) -> Tuple[str, str, str, str]:
        """
        生成 ORB 期權交易信號

        信心度邏輯:
          High:   突破 > 50% 開盤區間寬度 + 開盤區間 > 0.5%（有波動性）
          Medium: 突破 0-50% 開盤區間寬度
          Low:    未突破（在區間內等待）
        """
        if direction == 'bullish':
            if breakout_pct > 50 and range_pct > 0.5:
                confidence = 'high'
            elif breakout_pct > 20:
                confidence = 'medium'
            else:
                confidence = 'low'

            reward = target - current_price
            risk   = current_price - stop
            rr     = reward / risk if risk > 0 else 0

            reasoning = (
                f"ORB 上方突破確認 ({self.orb_minutes}分鐘開盤區間: ${orb_low:.2f}-${orb_high:.2f})；"
                f"突破幅度: {breakout_pct:.1f}% 開盤區間；"
                f"風報比: {rr:.1f}R"
            )
            suggestion = (
                f"買入 0DTE/1DTE Call，行使價選 ATM 或輕微 OTM；"
                f"目標 ${target:.2f}，止損回到 ORB 上軌 ${stop:.2f}"
            )
            return 'long_call', confidence, reasoning, suggestion

        elif direction == 'bearish':
            if breakout_pct > 50 and range_pct > 0.5:
                confidence = 'high'
            elif breakout_pct > 20:
                confidence = 'medium'
            else:
                confidence = 'low'

            reward = current_price - target
            risk   = stop - current_price
            rr     = reward / risk if risk > 0 else 0

            reasoning = (
                f"ORB 下方突破確認 ({self.orb_minutes}分鐘開盤區間: ${orb_low:.2f}-${orb_high:.2f})；"
                f"突破幅度: {breakout_pct:.1f}% 開盤區間；"
                f"風報比: {rr:.1f}R"
            )
            suggestion = (
                f"買入 0DTE/1DTE Put，行使價選 ATM 或輕微 OTM；"
                f"目標 ${target:.2f}，止損回到 ORB 下軌 ${stop:.2f}"
            )
            return 'long_put', confidence, reasoning, suggestion

        else:
            # 在區間內 - 等待突破
            reasoning = (
                f"現價 ${current_price:.2f} 在開盤區間內 (${orb_low:.2f}-${orb_high:.2f})；"
                f"開盤區間寬度: {range_pct:.2f}%；等待突破方向確認"
            )
            suggestion = (
                f"持觀望態度；突破 ${orb_high:.2f} → Long Call；跌破 ${orb_low:.2f} → Long Put"
            )
            return 'wait', 'low', reasoning, suggestion


# ── 模塊單獨測試 ──────────────────────────────────────────
if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)

    np.random.seed(42)
    times = pd.date_range('2026-03-02 09:30', periods=60, freq='1min')

    # 模擬 VZ 上突破場景
    base = 41.80
    prices = [base + i * 0.02 + np.random.normal(0, 0.03) for i in range(60)]

    df = pd.DataFrame({
        'Open':  [p - 0.02 for p in prices],
        'High':  [p + 0.08 for p in prices],
        'Low':   [p - 0.08 for p in prices],
        'Close': prices,
        'Volume': np.random.randint(50000, 200000, 60),
    }, index=times)

    analyzer = ORBAnalyzer(orb_minutes=15)
    result = analyzer.calculate('VZ', df, current_price=prices[-1])

    print("\n" + "="*60)
    print("ORB 分析器測試 - VZ (模擬上突破)")
    print("="*60)
    r = result.to_dict()
    print(f"  開盤區間:  ${r['opening_range']['low']:.2f} - ${r['opening_range']['high']:.2f}")
    print(f"  區間寬度:  ${r['opening_range']['range']:.2f} ({r['opening_range']['range_pct']:.2f}%)")
    print(f"  現價:      ${r['current_price']:.2f}")
    print(f"  狀態:      {r['status']}")
    print(f"  方向:      {r['breakout_direction']}")
    print(f"  Target 1:  ${r['targets']['target_1']:.2f}")
    print(f"  Target 2:  ${r['targets']['target_2']:.2f}")
    print(f"  止損:      ${r['targets']['stop_loss']:.2f}")
    print(f"  信號:      {r['signal']} ({r['confidence']})")
    print(f"  建議:      {r['option_suggestion']}")
    print("="*60)
