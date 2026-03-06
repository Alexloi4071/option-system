# calculation_layer/module_0dte_filter.py
"""
模塊: 0DTE / 1DTE 期權篩選與分析器
Fix 12 長期升級 - 新增日內核心模塊

功能:
- 識別 0DTE / 1DTE 期權（到期日篩選）
- 評估 0DTE/1DTE 期權的適用性（流動性、Theta 衰減風險）
- 與 VWAP / ORB 信號結合，給出最優到期日建議
- 計算日內盈虧平衡和最大虧損時間

0DTE 特性:
  - Theta 衰減極快（每小時都有顯著衰減）
  - Gamma 極高（對股價移動非常敏感）
  - 適合明確方向且有觸發點的日內交易
  - 不適合持有過夜

到期日選擇邏輯:
  - 0DTE: 今日有 Gap/ORB/重大事件，確定性高
  - 1DTE: 有明確趨勢但需要過一夜確認
  - 本週到期: 中短期趨勢，有 FOMC/財報等催化劑
  - 2-4週到期: 標準波段交易

參考:
  - Sinclair, E. (2013). Volatility Trading
  - CBOE 0DTE 研究報告 (2023)
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime, date, timedelta

logger = logging.getLogger(__name__)


@dataclass
class ExpiryAssessment:
    """單個到期日評估結果"""
    expiration: str          # YYYY-MM-DD
    dte: int                 # 距到期天數
    is_0dte: bool
    is_1dte: bool
    is_this_week: bool
    is_monthly: bool

    # 風險評估
    theta_risk: str          # 'extreme' | 'high' | 'medium' | 'low'
    gamma_risk: str          # 'extreme' | 'high' | 'medium' | 'low'
    liquidity_note: str      # 流動性說明

    # 建議
    suitability: str         # 'ideal' | 'suitable' | 'caution' | 'avoid'
    suitability_reason: str

    def to_dict(self) -> Dict:
        return {
            'expiration': self.expiration,
            'dte': self.dte,
            'is_0dte': self.is_0dte,
            'is_1dte': self.is_1dte,
            'is_this_week': self.is_this_week,
            'theta_risk': self.theta_risk,
            'gamma_risk': self.gamma_risk,
            'liquidity_note': self.liquidity_note,
            'suitability': self.suitability,
            'suitability_reason': self.suitability_reason,
        }


@dataclass
class ZeroDTEResult:
    """0DTE / 1DTE 分析完整結果"""
    ticker: str
    current_price: float
    analysis_date: str

    # 可用到期日評估
    expirations_assessed: List[ExpiryAssessment]

    # 最佳推薦
    recommended_expiry: str
    recommended_dte: int
    recommendation_reason: str

    # 日內時間分析
    current_hour_et: int       # 當前美東時間（小時）
    time_period: str           # 'morning' | 'midday' | 'afternoon'
    time_note: str             # 基於時間的建議

    # 結合外部信號
    vwap_signal: Optional[str] = None   # 結合 VWAP 信號
    orb_signal: Optional[str] = None    # 結合 ORB 信號
    combined_signal: str = 'neutral'

    def to_dict(self) -> Dict:
        return {
            'ticker': self.ticker,
            'current_price': round(self.current_price, 4),
            'analysis_date': self.analysis_date,
            'recommended_expiry': self.recommended_expiry,
            'recommended_dte': self.recommended_dte,
            'recommendation_reason': self.recommendation_reason,
            'time_analysis': {
                'current_hour_et': self.current_hour_et,
                'time_period': self.time_period,
                'note': self.time_note,
            },
            'signals': {
                'vwap': self.vwap_signal,
                'orb': self.orb_signal,
                'combined': self.combined_signal,
            },
            'expirations': [e.to_dict() for e in self.expirations_assessed],
        }


class ZeroDTEFilter:
    """
    0DTE / 1DTE 期權分析與篩選器

    適用場景:
    - 日內期權到期日選擇
    - 與 VWAP + ORB 信號整合
    - 評估 0DTE 風險（Theta/Gamma）

    使用示例:
    >>> analyzer = ZeroDTEFilter()
    >>> result = analyzer.analyze(
    ...     ticker='VZ', current_price=41.80,
    ...     available_expirations=['2026-03-02', '2026-03-03', '2026-03-07', '2026-03-27'],
    ...     vwap_signal='bullish', orb_signal='long_call'
    ... )
    >>> print(f"推薦到期日: {result.recommended_expiry} ({result.recommended_dte} DTE)")
    """

    # 日內時間段定義（美東時間）
    MORNING_END   = 11    # 上午: 09:30-11:00
    MIDDAY_START  = 11    # 午市: 11:00-14:00
    MIDDAY_END    = 14
    AFTERNOON_END = 16    # 下午: 14:00-16:00

    def analyze(
        self,
        ticker: str,
        current_price: float,
        available_expirations: List[str],
        vwap_signal: Optional[str] = None,
        orb_signal: Optional[str] = None,
        current_hour_et: Optional[int] = None,
    ) -> ZeroDTEResult:
        """
        分析可用到期日並給出建議

        參數:
            ticker: 股票代碼
            current_price: 當前股價
            available_expirations: 可用到期日列表 (YYYY-MM-DD)
            vwap_signal: VWAP 信號（'bullish' | 'bearish' | 'neutral'）
            orb_signal: ORB 信號（'long_call' | 'long_put' | 'wait'）
            current_hour_et: 當前美東時間（小時），None 則自動判斷

        返回:
            ZeroDTEResult: 完整分析結果
        """
        try:
            logger.info(f"開始分析 {ticker} 0DTE/1DTE 到期日...")

            today = date.today()
            analysis_date = today.strftime('%Y-%m-%d')

            # ── 時間分析 ───────────────────────────────────────
            import pytz
            if current_hour_et is None:
                et_tz = pytz.timezone('America/New_York')
                current_hour_et = datetime.now(et_tz).hour

            if current_hour_et < self.MORNING_END:
                time_period = 'morning'
                time_note = ('開市初期（09:30-11:00）: 震盪較大，ORB 突破是最佳入場機會；'
                             '0DTE 可考慮，需確認 ORB 方向後再入場')
            elif current_hour_et < self.MIDDAY_END:
                time_period = 'midday'
                time_note = ('午市整固期（11:00-14:00）: 方向性較低，0DTE Theta 衰減明顯；'
                             '建議使用 1DTE 或本週到期，避免 0DTE 的時間損耗')
            else:
                time_period = 'afternoon'
                time_note = ('下午強勢期（14:00-16:00）: 15-30 分鐘前的動量往往持續至收盤；'
                             '0DTE 收盤 Gamma 極高，謹慎使用，建議小倉')

            # ── 評估各到期日 ───────────────────────────────────
            assessments: List[ExpiryAssessment] = []
            for exp_str in sorted(available_expirations):
                assessment = self._assess_expiration(exp_str, today, time_period)
                assessments.append(assessment)

            # ── 選擇最佳到期日 ────────────────────────────────
            recommended_expiry, recommended_dte, recommendation_reason = \
                self._select_best_expiry(
                    assessments, time_period, vwap_signal, orb_signal
                )

            # ── 整合外部信號 ───────────────────────────────────
            combined = self._combine_signals(vwap_signal, orb_signal)

            logger.info(f"  推薦到期日: {recommended_expiry} ({recommended_dte} DTE)")
            logger.info(f"  整合信號: {combined}")

            return ZeroDTEResult(
                ticker=ticker,
                current_price=current_price,
                analysis_date=analysis_date,
                expirations_assessed=assessments,
                recommended_expiry=recommended_expiry,
                recommended_dte=recommended_dte,
                recommendation_reason=recommendation_reason,
                current_hour_et=current_hour_et,
                time_period=time_period,
                time_note=time_note,
                vwap_signal=vwap_signal,
                orb_signal=orb_signal,
                combined_signal=combined,
            )

        except Exception as e:
            logger.error(f"x 0DTE 分析失敗: {e}")
            raise

    def _assess_expiration(
        self,
        exp_str: str,
        today: date,
        time_period: str
    ) -> ExpiryAssessment:
        """評估單個到期日"""
        try:
            exp_date = datetime.strptime(exp_str, '%Y-%m-%d').date()
        except ValueError:
            exp_date = today

        dte = (exp_date - today).days
        is_0dte = (dte == 0)
        is_1dte = (dte == 1)

        # 本週到期（週五）
        days_to_week_end = 4 - today.weekday()  # 0=Mon, 4=Fri
        if days_to_week_end < 0:
            days_to_week_end += 7
        is_this_week = (0 <= dte <= days_to_week_end)

        # 月度合約判斷（第 3 個週五 ≈ 15-21 日）
        is_monthly = (exp_date.day >= 15 and exp_date.day <= 21 and
                      exp_date.weekday() == 4)

        # Theta 風險
        if dte == 0:
            theta_risk = 'extreme'
            gamma_risk = 'extreme'
            liquidity_note = '0DTE: 流動性通常良好（SPY/QQQ/大市值股票），小市值股需謹慎'
        elif dte == 1:
            theta_risk = 'high'
            gamma_risk = 'high'
            liquidity_note = '1DTE: 流動性較好，Theta 衰減明顯但可接受'
        elif dte <= 7:
            theta_risk = 'medium'
            gamma_risk = 'medium'
            liquidity_note = '本週到期: 流動性好，適合短線波段'
        elif dte <= 30:
            theta_risk = 'low'
            gamma_risk = 'low'
            liquidity_note = '月度到期: 流動性最好，適合方向性交易'
        else:
            theta_risk = 'low'
            gamma_risk = 'low'
            liquidity_note = '遠期合約: 流動性可能較低，價差可能較大'

        # 適用性評估
        if dte == 0:
            if time_period == 'morning':
                suitability = 'ideal'
                reason = '0DTE 在開市初期 ORB 突破後最有效，快進快出'
            elif time_period == 'midday':
                suitability = 'caution'
                reason = '0DTE 午市 Theta 衰減快，僅在有強烈方向信號下使用'
            else:
                suitability = 'caution'
                reason = '0DTE 下午 Gamma 急速增加，位置大小需謹慎'
        elif dte == 1:
            suitability = 'suitable'
            reason = '1DTE Theta/Gamma 平衡，適合持有至明日或日內交易'
        elif dte <= 7:
            suitability = 'suitable'
            reason = '本週到期適合有明確催化劑的短線交易'
        elif dte <= 21:
            suitability = 'suitable'
            reason = '標準波段交易的最佳選擇'
        else:
            suitability = 'avoid' if dte > 45 else 'caution'
            reason = f'DTE={dte}天，Gamma 偏低，日內效率不佳'

        return ExpiryAssessment(
            expiration=exp_str,
            dte=dte,
            is_0dte=is_0dte,
            is_1dte=is_1dte,
            is_this_week=is_this_week,
            is_monthly=is_monthly,
            theta_risk=theta_risk,
            gamma_risk=gamma_risk,
            liquidity_note=liquidity_note,
            suitability=suitability,
            suitability_reason=reason,
        )

    def _select_best_expiry(
        self,
        assessments: List[ExpiryAssessment],
        time_period: str,
        vwap_signal: Optional[str],
        orb_signal: Optional[str],
    ) -> Tuple[str, int, str]:
        """選擇最佳到期日"""
        if not assessments:
            today_str = date.today().strftime('%Y-%m-%d')
            return today_str, 0, '無可用到期日，使用今日'

        # 信號確定性評分（強信號 → 可用 0DTE，弱信號 → 傾向 1DTE/本週）
        has_strong_signal = (
            (vwap_signal in ('bullish', 'bearish')) and
            (orb_signal in ('long_call', 'long_put'))
        )

        # 優先順序邏輯
        priority_map = {
            'morning':   ['0dte', '1dte', 'this_week'],
            'midday':    ['1dte', 'this_week', '0dte'],
            'afternoon': ['0dte', '1dte', 'this_week'] if has_strong_signal
                         else ['1dte', 'this_week'],
        }
        priority = priority_map.get(time_period, ['1dte', 'this_week'])

        # 按優先順序找最匹配到期日
        for pref in priority:
            for a in assessments:
                if pref == '0dte' and a.is_0dte:
                    reason = (f'0DTE ({time_period} + '
                              f'{"強信號" if has_strong_signal else "一般信號"}): '
                              f'{a.suitability_reason}')
                    return a.expiration, a.dte, reason
                if pref == '1dte' and a.is_1dte:
                    reason = f'1DTE [{time_period}]: {a.suitability_reason}'
                    return a.expiration, a.dte, reason
                if pref == 'this_week' and a.is_this_week and not a.is_0dte and not a.is_1dte:
                    reason = f'本週到期 ({a.dte} DTE): {a.suitability_reason}'
                    return a.expiration, a.dte, reason

        # 降級：使用最近的 "suitable" 到期日
        suitable = [a for a in assessments if a.suitability in ('ideal', 'suitable')]
        if suitable:
            best = min(suitable, key=lambda a: a.dte)
            return best.expiration, best.dte, f'降級選擇 ({best.dte} DTE): {best.suitability_reason}'

        # 最後降級：最近到期日
        nearest = min(assessments, key=lambda a: a.dte)
        return nearest.expiration, nearest.dte, f'無理想選擇，使用最近到期 ({nearest.dte} DTE)'

    def _combine_signals(
        self,
        vwap_signal: Optional[str],
        orb_signal: Optional[str]
    ) -> str:
        """整合 VWAP 和 ORB 信號"""
        bullish_signals = 0
        bearish_signals = 0

        if vwap_signal == 'bullish':
            bullish_signals += 1
        elif vwap_signal == 'bearish':
            bearish_signals += 1

        if orb_signal == 'long_call':
            bullish_signals += 1
        elif orb_signal == 'long_put':
            bearish_signals += 1

        if bullish_signals == 2:
            return 'strong_bullish'
        elif bullish_signals == 1 and bearish_signals == 0:
            return 'bullish'
        elif bearish_signals == 2:
            return 'strong_bearish'
        elif bearish_signals == 1 and bullish_signals == 0:
            return 'bearish'
        elif bullish_signals > 0 and bearish_signals > 0:
            return 'conflicting'
        else:
            return 'neutral'


# ── 模塊單獨測試 ──────────────────────────────────────────
if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)

    analyzer = ZeroDTEFilter()
    result = analyzer.analyze(
        ticker='VZ',
        current_price=41.80,
        available_expirations=[
            '2026-03-02',   # 0DTE (假設今日是 3/2)
            '2026-03-03',   # 1DTE
            '2026-03-06',   # 本週
            '2026-03-27',   # 目標到期日
            '2026-04-17',   # 次月
        ],
        vwap_signal='bullish',
        orb_signal='long_call',
        current_hour_et=10,   # 模擬早上 10 點
    )

    print("\n" + "="*60)
    print("0DTE 篩選器測試 (VZ)")
    print("="*60)
    r = result.to_dict()
    print(f"  分析日期:    {r['analysis_date']}")
    print(f"  時間段:      {r['time_analysis']['time_period']}")
    print(f"  VWAP 信號:   {r['signals']['vwap']}")
    print(f"  ORB 信號:    {r['signals']['orb']}")
    print(f"  整合信號:    {r['signals']['combined']}")
    print(f"\n  推薦到期日:  {r['recommended_expiry']} ({r['recommended_dte']} DTE)")
    print(f"  推薦原因:    {r['recommendation_reason']}")
    print(f"\n  時間建議: {r['time_analysis']['note']}")
    print("\n  各到期日評估:")
    for exp in r['expirations']:
        smiley = '✅' if exp['suitability'] in ('ideal','suitable') else '⚠️'
        print(f"    {smiley} {exp['expiration']} ({exp['dte']} DTE) - "
              f"{exp['suitability']} | Theta: {exp['theta_risk']} | Gamma: {exp['gamma_risk']}")
    print("="*60)
