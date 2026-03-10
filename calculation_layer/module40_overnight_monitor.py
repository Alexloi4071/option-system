"""
calculation_layer/module40_overnight_monitor.py
------------------------------------------------
Module 40: Overnight IV Monitor

職責：
  - 計算夜盤 (overnight) 與日盤 (primary) 的 Implied Volatility 差值
    (Night Volatility Spread = overnight_iv - day_iv)
  - 如果差值顯著（>2%），作為隔日開盤波動率飆升的領先指標
  - 也提供 Gamma / Delta 簡易夜盤風控快照
  - 注意：此模組不做交易決策；它只產出「觀察信號」供日盤策略模組使用

使用方法：
    from calculation_layer.module40_overnight_monitor import OvernightMonitor
    monitor = OvernightMonitor()
    result = monitor.run(ticker='VZ', option_chain=chain_data, session_iv_history=iv_hist)
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ───────────────────────────────────────────────────────────────────────────
# Thresholds (configurable)
# ───────────────────────────────────────────────────────────────────────────
# If the overnight IV diverges from the last-known day IV by more than this
# percentage, we flag it as a significant signal.
SIGNIFICANT_IV_SPREAD_PCT = 2.0   # percentage points (e.g. 30% → 32%)

# If the overnight put-call IV skew ratio deviates by more than this from
# neutral (1.0), it might indicate directional overnight positioning.
SIGNIFICANT_SKEW_RATIO = 1.20    # 20% higher put IV vs call IV


class NightVolatilitySignal:
    """Result container for overnight IV monitoring."""

    def __init__(
        self,
        ticker: str,
        timestamp: str,
        session_type: str,
        overnight_iv: Optional[float],
        last_day_iv: Optional[float],
        iv_spread: Optional[float],
        iv_spread_significant: bool,
        put_call_iv_skew: Optional[float],
        skew_signal: str,
        position_risk_alerts: List[str],
        recommendation: str,
        data_quality: str,
    ):
        self.ticker = ticker
        self.timestamp = timestamp
        self.session_type = session_type
        self.overnight_iv = overnight_iv
        self.last_day_iv = last_day_iv
        self.iv_spread = iv_spread
        self.iv_spread_significant = iv_spread_significant
        self.put_call_iv_skew = put_call_iv_skew
        self.skew_signal = skew_signal
        self.position_risk_alerts = position_risk_alerts
        self.recommendation = recommendation
        self.data_quality = data_quality

    def to_dict(self) -> Dict[str, Any]:
        return {
            'ticker': self.ticker,
            'timestamp': self.timestamp,
            'session_type': self.session_type,
            'overnight_iv': self.overnight_iv,
            'last_day_iv': self.last_day_iv,
            'iv_spread': self.iv_spread,
            'iv_spread_pct': f"{self.iv_spread:+.2f}%" if self.iv_spread is not None else 'N/A',
            'iv_spread_significant': self.iv_spread_significant,
            'put_call_iv_skew': self.put_call_iv_skew,
            'skew_signal': self.skew_signal,
            'position_risk_alerts': self.position_risk_alerts,
            'recommendation': self.recommendation,
            'data_quality': self.data_quality,
        }


class OvernightMonitor:
    """
    Module 40: Overnight Volatility Monitor

    Primary use-cases:
    1. Run during overnight / premarket to track if IV is drifting from the
       last known primary-session value.
    2. Flag if put/call IV skew is worsening (bearish overnight positioning).
    3. Provide lightweight risk alerts for existing positions (e.g. VZ Long Put).
    """

    def __init__(self):
        self.module_name = "module40_overnight_monitor"

    # ─────────────────────────────────────────────────────────────────────
    def run(
        self,
        ticker: str,
        option_chain: Optional[Dict[str, Any]] = None,
        session_iv_history: Optional[Dict[str, float]] = None,
        positions: Optional[List[Dict[str, Any]]] = None,
    ) -> NightVolatilitySignal:
        """
        Run overnight IV monitoring.

        Parameters
        ----------
        ticker : str
            Stock symbol.
        option_chain : dict, optional
            The current option chain snapshot (from data_fetcher).
            Expected keys: 'calls' (DataFrame or list), 'puts' (DataFrame or list).
        session_iv_history : dict, optional
            Historical IV per session, e.g.::
                {'last_primary_iv': 28.5, 'previous_day_iv': 27.1}
        positions : list, optional
            Current open positions. Each position dict should have keys:
                ticker, strategy, strike, expiration, quantity
            Used to generate position-specific risk alerts.

        Returns
        -------
        NightVolatilitySignal
        """
        import pytz
        from datetime import datetime

        try:
            from data_layer.session_utils import get_session_type
            current_session = get_session_type()
        except ImportError:
            current_session = 'unknown'

        timestamp = datetime.now(pytz.timezone('America/New_York')).strftime('%Y-%m-%d %H:%M:%S ET')

        # ── Extract ATM IV from option chain ──────────────────────────────
        overnight_iv = None
        put_call_skew_ratio = None
        data_quality = 'unavailable'

        if option_chain:
            atm_call_iv, atm_put_iv = self._extract_atm_ivs(option_chain)
            if atm_call_iv is not None or atm_put_iv is not None:
                overnight_iv = ((atm_call_iv or 0) + (atm_put_iv or 0)) / max(
                    int(atm_call_iv is not None) + int(atm_put_iv is not None), 1
                )
                if atm_call_iv and atm_put_iv and atm_call_iv > 0:
                    put_call_skew_ratio = atm_put_iv / atm_call_iv
                data_quality = 'partial' if (atm_call_iv is None or atm_put_iv is None) else 'complete'

        # ── Compute IV spread vs last known day IV ────────────────────────
        last_day_iv = None
        iv_spread = None
        iv_spread_significant = False

        if session_iv_history:
            last_day_iv = session_iv_history.get('last_primary_iv')

        if overnight_iv is not None and last_day_iv is not None and last_day_iv > 0:
            iv_spread = overnight_iv - last_day_iv
            iv_spread_significant = abs(iv_spread) >= SIGNIFICANT_IV_SPREAD_PCT

        # ── Skew signal ───────────────────────────────────────────────────
        skew_signal = 'neutral'
        if put_call_skew_ratio is not None:
            if put_call_skew_ratio > SIGNIFICANT_SKEW_RATIO:
                skew_signal = 'bearish_skew'   # Put IV >> Call IV → market fearing downside
            elif put_call_skew_ratio < (1.0 / SIGNIFICANT_SKEW_RATIO):
                skew_signal = 'bullish_skew'   # Call IV >> Put IV (rare)

        # ── Position risk alerts ──────────────────────────────────────────
        position_risk_alerts = self._check_position_risks(
            positions=positions or [],
            iv_spread=iv_spread,
            iv_spread_significant=iv_spread_significant,
            skew_signal=skew_signal,
        )

        # ── Overall recommendation ────────────────────────────────────────
        recommendation = self._build_recommendation(
            iv_spread=iv_spread,
            iv_spread_significant=iv_spread_significant,
            skew_signal=skew_signal,
            position_risk_alerts=position_risk_alerts,
            data_quality=data_quality,
        )

        result = NightVolatilitySignal(
            ticker=ticker,
            timestamp=timestamp,
            session_type=current_session,
            overnight_iv=round(overnight_iv, 2) if overnight_iv is not None else None,
            last_day_iv=round(last_day_iv, 2) if last_day_iv is not None else None,
            iv_spread=round(iv_spread, 2) if iv_spread is not None else None,
            iv_spread_significant=iv_spread_significant,
            put_call_iv_skew=round(put_call_skew_ratio, 3) if put_call_skew_ratio is not None else None,
            skew_signal=skew_signal,
            position_risk_alerts=position_risk_alerts,
            recommendation=recommendation,
            data_quality=data_quality,
        )

        logger.info(
            f"[Module 40] {ticker} overnight monitor @ {timestamp} | "
            f"Session={current_session} | "
            f"Night IV={result.overnight_iv} | Day IV={result.last_day_iv} | "
            f"Spread={result.iv_spread} | Significant={iv_spread_significant} | "
            f"Skew={skew_signal}"
        )
        return result

    # ─────────────────────────────────────────────────────────────────────
    def _extract_atm_ivs(
        self, option_chain: Dict[str, Any]
    ) -> tuple[Optional[float], Optional[float]]:
        """
        Extract ATM implied volatility for calls and puts from option_chain.
        Handles both DataFrame and list-of-dicts formats.
        """
        import pandas as pd

        def _to_df(raw) -> pd.DataFrame:
            if raw is None:
                return pd.DataFrame()
            if isinstance(raw, pd.DataFrame):
                return raw
            if isinstance(raw, list) and raw:
                return pd.DataFrame(raw)
            return pd.DataFrame()

        calls_df = _to_df(option_chain.get('calls'))
        puts_df = _to_df(option_chain.get('puts'))

        def _get_atm_iv(df: pd.DataFrame) -> Optional[float]:
            if df.empty:
                return None
            iv_col = next(
                (c for c in ['impliedVolatility', 'iv', 'implied_volatility'] if c in df.columns),
                None,
            )
            if iv_col is None:
                return None
            # Prefer rows NOT marked as low_quality
            if 'data_quality' in df.columns:
                good = df[df['data_quality'] != 'low_liquidity']
                if good.empty:
                    good = df   # fall back to all rows if all are flagged

                # Filter to ATM strikes if mid info is available
                if not good.empty:
                    df = good

            iv_series = pd.to_numeric(df[iv_col], errors='coerce').dropna()
            if iv_series.empty:
                return None
            # Take median of top-5 closest-to-ATM rows (already filtered by range)
            sample = iv_series.head(min(5, len(iv_series)))
            iv_val = float(sample.median())
            # Convert to percentage if value is a small fraction (<1.0)
            if 0 < iv_val < 1.0:
                iv_val *= 100.0
            return iv_val if iv_val > 0 else None

        return _get_atm_iv(calls_df), _get_atm_iv(puts_df)

    # ─────────────────────────────────────────────────────────────────────
    def _check_position_risks(
        self,
        positions: List[Dict[str, Any]],
        iv_spread: Optional[float],
        iv_spread_significant: bool,
        skew_signal: str,
    ) -> List[str]:
        """Generate risk alerts for open positions based on overnight signals."""
        alerts: List[str] = []

        for pos in positions:
            ticker_p   = pos.get('ticker', '')
            strategy   = pos.get('strategy', '').lower()
            expiration = pos.get('expiration', '')
            strike     = pos.get('strike', 0.0)

            # Long Put position risk checks
            if 'long_put' in strategy or ('long' in strategy and 'put' in strategy):
                if iv_spread_significant and iv_spread is not None and iv_spread > 0:
                    alerts.append(
                        f"✅ {ticker_p} Long Put ({strike}-{expiration}): "
                        f"夜盤 IV 上升 {iv_spread:+.1f}% → Long Put 獲益，持倉有利。"
                    )
                elif iv_spread_significant and iv_spread is not None and iv_spread < 0:
                    alerts.append(
                        f"⚠️  {ticker_p} Long Put ({strike}-{expiration}): "
                        f"夜盤 IV 下降 {iv_spread:+.1f}% → Vega 損耗，考慮明日盤初評估轉倉時機。"
                    )
                if skew_signal == 'bearish_skew':
                    alerts.append(
                        f"📊 {ticker_p}: 夜盤 Put/Call IV Skew 偏空，看跌期權溢價升高，"
                        f"對你的 Long Put 有利。"
                    )

            # Long Call position risk checks
            if 'long_call' in strategy or ('long' in strategy and 'call' in strategy):
                if iv_spread_significant and iv_spread is not None and iv_spread > 0:
                    alerts.append(
                        f"✅ {ticker_p} Long Call ({strike}-{expiration}): "
                        f"夜盤 IV 上升 {iv_spread:+.1f}% → Vega 獲益，暫時持有。"
                    )
                if skew_signal == 'bearish_skew':
                    alerts.append(
                        f"⚠️  {ticker_p}: 夜盤 Skew 偏空，市場預期下行，Long Call 面臨逆風。"
                    )

        return alerts

    # ─────────────────────────────────────────────────────────────────────
    def _build_recommendation(
        self,
        iv_spread: Optional[float],
        iv_spread_significant: bool,
        skew_signal: str,
        position_risk_alerts: List[str],
        data_quality: str,
    ) -> str:
        if data_quality == 'unavailable':
            return "⚪ 夜盤數據不可用 (無 IBKR 連接或非交易時段)。監控中，無操作建議。"

        parts: List[str] = []

        if iv_spread_significant and iv_spread is not None:
            direction = "飆升" if iv_spread > 0 else "下降"
            parts.append(
                f"🔴 夜盤 IV {direction} {iv_spread:+.1f}%（顯著差異 ≥ {SIGNIFICANT_IV_SPREAD_PCT}%），"
                f"預計隔日開盤波動率{'增大' if iv_spread > 0 else '收縮'}。"
            )
        else:
            parts.append("🟢 夜盤 IV 與日盤基線差異不顯著，波動率環境穩定。")

        if skew_signal == 'bearish_skew':
            parts.append("📉 夜盤 Put IV 顯著高於 Call IV (偏空定位)，留意隔日開盤方向。")
        elif skew_signal == 'bullish_skew':
            parts.append("📈 夜盤 Call IV 顯著高於 Put IV (偏多定位)。")

        if position_risk_alerts:
            parts.append("部位風控提示：" + " | ".join(position_risk_alerts[:2]))

        parts.append("建議: 夜盤不追倉，等候主要交易時段確認信號後再決策。")

        return " ".join(parts)
