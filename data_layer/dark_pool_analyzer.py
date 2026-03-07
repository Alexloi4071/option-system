# data_layer/dark_pool_analyzer.py
"""
Dark Pool Analyzer — Layer 3

職責：
  接收 Layer 2 DarkPoolSnapshot，輸出標準化 DarkPoolSignal
  供 module22 (options flow) / module29 (order flow) / module30 (market structure) 消費

Field Authority Map（只讀，不寫入原始數據）：
  dp_ratio       來自 ibkr_dp（不可覆蓋）
  signal_type    本層計算（downstream 只讀）
  confidence     本層計算
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# ── 訊號閾值（可透過 config 覆蓋） ─────────────────────────────
DP_RATIO_ALERT   = 35.0   # DP ratio > 35% = 異動警示
DP_RATIO_STRONG  = 50.0   # DP ratio > 50% = 強訊號
DP_BLOCK_ALERT   = 5      # 大單筆數 > 5 = 機構佈局跡象
VWAP_DEVIATION   = 0.005  # 股價偏離 VWAP 0.5% 以上 = 可交易偏差


@dataclass
class DarkPoolSignal:
    """
    下游模組消費的統一 Dark Pool 訊號格式

    Ref: option-data-review.md Section IV.3
    """
    ticker:            str
    signal_type:       str          # 'neutral' | 'accumulation' | 'distribution' | 'block_alert'
    confidence:        float        # 0.0 - 1.0
    dp_ratio:          float        # 最佳 DP ratio (%)
    dp_volume:         int
    block_count:       int
    block_volume:      int
    vwap:              Optional[float]
    vwap_deviation:    Optional[float]  # (current_price - vwap) / vwap
    methods_agree:     Optional[bool]
    data_quality:      str
    timestamp:         str
    warnings:          List[str] = field(default_factory=list)
    raw_snapshot:      Optional[Dict[str, Any]] = field(default=None, repr=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'ticker':         self.ticker,
            'signal_type':    self.signal_type,
            'confidence':     self.confidence,
            'dp_ratio':       self.dp_ratio,
            'dp_volume':      self.dp_volume,
            'block_count':    self.block_count,
            'block_volume':   self.block_volume,
            'vwap':           self.vwap,
            'vwap_deviation': self.vwap_deviation,
            'methods_agree':  self.methods_agree,
            'data_quality':   self.data_quality,
            'timestamp':      self.timestamp,
            'warnings':       self.warnings,
        }


class DarkPoolAnalyzer:
    """
    Dark Pool 訊號分析器

    使用方式：
        analyzer = DarkPoolAnalyzer()
        signal = analyzer.analyze(dp_snapshot, current_price=450.0)
        if signal.signal_type == 'accumulation':
            # ... 下游邏輯
    """

    def __init__(
        self,
        dp_ratio_alert:  float = DP_RATIO_ALERT,
        dp_ratio_strong: float = DP_RATIO_STRONG,
        dp_block_alert:  int   = DP_BLOCK_ALERT,
        vwap_deviation:  float = VWAP_DEVIATION,
    ):
        self.dp_ratio_alert  = dp_ratio_alert
        self.dp_ratio_strong = dp_ratio_strong
        self.dp_block_alert  = dp_block_alert
        self.vwap_deviation  = vwap_deviation

    def analyze(
        self,
        snapshot:      Dict[str, Any],
        current_price: Optional[float] = None,
    ) -> DarkPoolSignal:
        """
        分析 DarkPoolSnapshot，返回 DarkPoolSignal

        訊號邏輯（可調整）：
          accumulation  ← dp_ratio > alert 且 block_count > threshold
          distribution  ← dp_ratio > alert 且 current_price > vwap（賣壓）
          block_alert   ← block_count > dp_block_alert（不論 dp_ratio）
          neutral       ← 以上皆否

        Confidence 計算：
          基礎分 = dp_ratio / 100
          加分項：
            + 0.1  若兩方法 agree
            + 0.1  若 data_quality == 'complete'
            + 0.1  若 block_count > dp_block_alert
          上限 = 1.0
        """
        warnings = list(snapshot.get('warnings', []))
        dp_ratio    = snapshot.get('dp_ratio', 0.0)
        block_count = snapshot.get('block_count', 0)
        block_vol   = snapshot.get('block_volume', 0)
        vwap        = snapshot.get('vwap')
        quality     = snapshot.get('data_quality', 'unavailable')
        agree       = snapshot.get('methods_agree')

        if quality == 'unavailable':
            warnings.append("數據質量 unavailable，訊號不可靠")

        # ── VWAP 偏差計算 ───────────────────────────────────
        vwap_dev = None
        if vwap and current_price and vwap > 0:
            vwap_dev = (current_price - vwap) / vwap

        # ── 訊號類型決策 ─────────────────────────────────────
        signal_type = 'neutral'

        if dp_ratio >= self.dp_ratio_alert:
            if vwap_dev is not None and vwap_dev > self.vwap_deviation:
                # 股價在 VWAP 之上且大量 DP → 可能賣壓暗流
                signal_type = 'distribution'
            elif block_count >= self.dp_block_alert:
                # 大量 DP + 大單 → 機構累積
                signal_type = 'accumulation'
            else:
                # DP 比例高但無大單
                signal_type = 'accumulation' if dp_ratio >= self.dp_ratio_strong else 'neutral'

        if block_count >= self.dp_block_alert and signal_type == 'neutral':
            # 即使 dp_ratio 不高，大單本身也是訊號
            signal_type = 'block_alert'

        # ── Confidence 計算 ───────────────────────────────────
        confidence = min(dp_ratio / 100.0, 0.7)  # 基礎分上限 0.7
        if agree is True:
            confidence += 0.1
        if quality == 'complete':
            confidence += 0.1
        if block_count >= self.dp_block_alert:
            confidence += 0.1
        confidence = min(round(confidence, 2), 1.0)

        signal = DarkPoolSignal(
            ticker=snapshot.get('ticker', ''),
            signal_type=signal_type,
            confidence=confidence,
            dp_ratio=dp_ratio,
            dp_volume=snapshot.get('dp_volume', 0),
            block_count=block_count,
            block_volume=block_vol,
            vwap=vwap,
            vwap_deviation=round(vwap_dev, 4) if vwap_dev is not None else None,
            methods_agree=agree,
            data_quality=quality,
            timestamp=snapshot.get('timestamp', datetime.utcnow().isoformat()),
            warnings=warnings,
            raw_snapshot=snapshot,
        )

        logger.info(
            f"DarkPoolAnalyzer: {signal.ticker} → "
            f"signal={signal.signal_type}, confidence={signal.confidence}, "
            f"dp_ratio={signal.dp_ratio}%, blocks={signal.block_count}"
        )
        return signal

    def batch_analyze(
        self,
        snapshots: List[Dict[str, Any]],
        prices:    Optional[Dict[str, float]] = None,
    ) -> List[DarkPoolSignal]:
        """批量分析多個 ticker"""
        prices = prices or {}
        return [
            self.analyze(snap, current_price=prices.get(snap.get('ticker', '')))
            for snap in snapshots
            if snap is not None
        ]
