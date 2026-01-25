#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module 30: 異動期權偵測 (Unusual Options Activity)

功能:
1. 偵測異常成交量 (Volume Spikes)
2. 偵測高成交量/持倉量比率 (Vol/OI Ratio)
3. 識別機構大單 (Smart Money Flow)
4. 分析未平倉合約變化 (OI Change) - 需配合歷史數據

作者: Antigravity
日期: 2026-01-24
版本: 1.0.0
"""

import logging
import pandas as pd
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class UnusualActivitySignal:
    """單個異動信號"""
    strike: float
    option_type: str  # 'call' or 'put'
    signal_type: str  # 'vol_spike', 'high_vol_oi', 'smart_money', 'oi_surge'
    strength: float   # 信號強度 (0-100)
    description: str
    metrics: Dict[str, Any]  # 相關指標 (Vol, OI, Ratio etc.)
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為可 JSON 序列化的字典"""
        return {
            'strike': float(self.strike),
            'option_type': self.option_type,
            'signal_type': self.signal_type,
            'strength': float(self.strength),
            'description': self.description,
            'metrics': {k: (float(v) if isinstance(v, (int, float)) and v != float('inf') else str(v)) 
                       for k, v in self.metrics.items()}
        }

class UnusualActivityAnalyzer:
    """
    異動期權分析器
    
    專注於捕捉機構大戶的踪跡 (Smart Money)。
    """
    
    # 閾值設定
    MIN_VOLUME = 100              # 最低成交量門檻
    MIN_PREMIUM = 100000          # 大單門檻 ($100k)
    HIGH_VOL_OI_RATIO = 2.0       # 成交量是 OI 的 2 倍以上
    VOLUME_SPIKE_RATIO = 3.0      # 相對平均成交量的倍數 (如有)
    
    def __init__(self):
        logger.info("* 異動偵測模塊 (UOA) 已初始化")
        
    def analyze_chain(self, 
                     calls_df: pd.DataFrame, 
                     puts_df: pd.DataFrame,
                     historical_data: Optional[Dict] = None) -> Dict[str, List[UnusualActivitySignal]]:
        """
        分析整個期權鏈的異動情況
        
        參數:
            calls_df: Call 期權數據
            puts_df: Put 期權數據
            historical_data: 歷史數據 (用於計算 OI Change)
            
        返回:
            Dict: {'calls': [signals], 'puts': [signals]}
        """
        logger.info("開始執行異動偵測 (UOA)...")
        
        call_signals = self._analyze_options(calls_df, 'call')
        put_signals = self._analyze_options(puts_df, 'put')
        
        # 如果有歷史數據，進行 OI 變化分析
        if historical_data:
            oi_signals = self._analyze_oi_change(calls_df, puts_df, historical_data)
            call_signals.extend(oi_signals.get('call', []))
            put_signals.extend(oi_signals.get('put', []))
            
        # 按強度排序
        call_signals.sort(key=lambda x: x.strength, reverse=True)
        put_signals.sort(key=lambda x: x.strength, reverse=True)
        
        count = len(call_signals) + len(put_signals)
        if count > 0:
            logger.info(f"  發現 {count} 個異動信號 (Calls: {len(call_signals)}, Puts: {len(put_signals)})")
        
        return {
            'calls': call_signals,
            'puts': put_signals
        }
    
    def _analyze_options(self, df: pd.DataFrame, option_type: str) -> List[UnusualActivitySignal]:
        """分析單邊期權數據"""
        signals = []
        
        if df.empty:
            return signals
            
        # 確保必要的列存在
        required_cols = ['strike', 'volume', 'openInterest', 'lastPrice']
        for col in required_cols:
            if col not in df.columns:
                return signals
                
        for _, row in df.iterrows():
            vol = row.get('volume', 0) or 0
            oi = row.get('openInterest', 0) or 0
            price = row.get('lastPrice', 0) or 0
            strike = row['strike']
            
            # 過濾低流動性
            if vol < self.MIN_VOLUME:
                continue
                
            # 1. 檢查高 Vol/OI 比率 (爆量)
            # Volume > OI 通常意味著大量新開倉 (Aggressive Opening)
            # 尤其是當 OI 不低的時候
            if oi > 0:
                ratio = vol / oi
                if ratio >= self.HIGH_VOL_OI_RATIO and vol > 500:
                    strength = min(100, ratio * 10)  # Ratio 10x = 100分
                    signals.append(UnusualActivitySignal(
                        strike=strike,
                        option_type=option_type,
                        signal_type='high_vol_oi',
                        strength=strength,
                        description=f"成交量爆炸: Vol/OI = {ratio:.1f}x (Vol: {vol}, OI: {oi})",
                        metrics={'volume': vol, 'oi': oi, 'ratio': ratio}
                    ))
            elif oi == 0 and vol > 500:
                # 0 OI 但有大量成交，絕對是新開倉
                signals.append(UnusualActivitySignal(
                    strike=strike,
                    option_type=option_type,
                    signal_type='high_vol_oi',
                    strength=90.0,
                    description=f"全新建倉: Volume {vol} vs 0 OI",
                    metrics={'volume': vol, 'oi': 0, 'ratio': float('inf')}
                ))
                    
            # 2. 檢查大單金額 (Smart Money)
            # 權利金總額 = Price * Volume * 100
            total_premium = price * vol * 100
            if total_premium >= self.MIN_PREMIUM:
                strength = min(100, (total_premium / self.MIN_PREMIUM) * 20 + 50)
                signals.append(UnusualActivitySignal(
                    strike=strike,
                    option_type=option_type,
                    signal_type='smart_money',
                    strength=strength,
                    description=f"機構大單: ${total_premium/1000:.0f}k 權利金流向",
                    metrics={'premium': total_premium, 'volume': vol, 'price': price}
                ))
                
        return signals

    def _analyze_oi_change(self, 
                          current_calls: pd.DataFrame, 
                          current_puts: pd.DataFrame, 
                          history: Dict) -> Dict[str, List[UnusualActivitySignal]]:
        """
        對比歷史數據分析 OI 變化
        (需在主邏輯中傳入昨日數據)
        """
        # 暫時留空，等待 HistoryManager 集成
        return {'call': [], 'put': []}
