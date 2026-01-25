#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module 31: 高級期權指標分析 (Advanced Metrics)

功能:
1. Put/Call Ratio (PCR) - 情緒指標
2. Max Pain (最大痛點) - 莊家結算目標
3. Gamma Exposure (GEX) - 做市商避險需求

作者: Antigravity
日期: 2026-01-24
版本: 1.0.0
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class MarketMetrics:
    """市場情緒綜合指標"""
    pcr_volume: float = 0.0      # 成交量 PCR
    pcr_oi: float = 0.0          # 持倉量 PCR
    max_pain: float = 0.0        # 最大痛點價格
    total_gex: float = 0.0       # 總 Gamma Exposure ($)
    gex_profile: Dict[float, float] = None # 各行使價的 GEX 分布
    
    def to_dict(self) -> Dict:
        return {
            'pcr_volume': round(self.pcr_volume, 2),
            'pcr_oi': round(self.pcr_oi, 2),
            'max_pain': round(self.max_pain, 2),
            'total_gex': round(self.total_gex, 0),
            'gex_profile': self.gex_profile
        }

class AdvancedMetricsAnalyzer:
    """高級指標分析器"""
    
    def __init__(self):
        logger.info("* 高級指標分析器 (Advanced Metrics) 已初始化")
        
    def calculate_metrics(self, calls_df: pd.DataFrame, puts_df: pd.DataFrame, current_price: float) -> MarketMetrics:
        """計算所有高級指標"""
        try:
            metrics = MarketMetrics()
            
            # 1. 計算 PCR (Put/Call Ratio)
            metrics.pcr_volume = self._calculate_pcr(calls_df, puts_df, metric='volume')
            metrics.pcr_oi = self._calculate_pcr(calls_df, puts_df, metric='openInterest')
            
            # 2. 計算 Max Pain (最大痛點)
            metrics.max_pain = self._calculate_max_pain(calls_df, puts_df)
            
            # 3. 計算 Gamma Exposure (GEX)
            metrics.total_gex, metrics.gex_profile = self._calculate_gex(calls_df, puts_df, current_price)
            
            logger.info(f"高級指標計算完成: PCR(Vol)={metrics.pcr_volume:.2f}, Max Pain=${metrics.max_pain:.2f}, Total GEX=${metrics.total_gex/1e6:.1f}M")
            return metrics
            
        except Exception as e:
            logger.error(f"計算高級指標失敗: {e}")
            return MarketMetrics()
            
    def _calculate_pcr(self, calls: pd.DataFrame, puts: pd.DataFrame, metric: str = 'volume') -> float:
        """
        計算 Put/Call Ratio
        
        參數:
            metric: 'volume' 或 'openInterest'
        """
        try:
            call_total = calls[metric].sum() if not calls.empty and metric in calls.columns else 0
            put_total = puts[metric].sum() if not puts.empty and metric in puts.columns else 0
            
            if call_total > 0:
                pcr = put_total / call_total
                return round(pcr, 4)
            return 0.0
        except Exception as e:
            logger.warning(f"PCR 計算失敗 ({metric}): {e}")
            return 0.0
            
    def _calculate_max_pain(self, calls: pd.DataFrame, puts: pd.DataFrame) -> float:
        """
        計算 Max Pain (最大痛點)
        
        定義: 令買方(Option Buyers)總損失最大、賣方(Option Sellers)總收益最大的結算價格。
        假設: 在到期日，期權賣方會盡力將價格推向這個點。
        """
        try:
            # 獲取所有獨特的行使價，並排序
            strikes = sorted(list(set(calls['strike'].tolist() + puts['strike'].tolist())))
            min_pain = float('inf')
            max_pain_price = 0.0
            
            # 緩存 OI 數據
            calls_oi = dict(zip(calls['strike'], calls['openInterest'].fillna(0)))
            puts_oi = dict(zip(puts['strike'], puts['openInterest'].fillna(0)))
            
            # 對每個潛在的到期價格(行使價)計算 "Pain Value"
            # Pain Value = Sum(Intrinsic Value * OI)
            for price in strikes:
                pain = 0.0
                
                # 計算 Call 的痛點 (當價格高於行使價時，Call 買方賺錢，賣方虧損 -> Pain)
                # Intrinsic = max(0, Price - Strike)
                for strike, oi in calls_oi.items():
                    if price > strike:
                        pain += (price - strike) * oi
                        
                # 計算 Put 的痛點 (當價格低於行使價時，Put 買方賺錢，賣方虧損 -> Pain)
                # Intrinsic = max(0, Strike - Price)
                for strike, oi in puts_oi.items():
                    if price < strike:
                        pain += (strike - price) * oi
                        
                if pain < min_pain:
                    min_pain = pain
                    max_pain_price = price
                    
            return max_pain_price
            
        except Exception as e:
            logger.warning(f"Max Pain 計算失敗: {e}")
            return 0.0
            
    def _calculate_gex(self, calls: pd.DataFrame, puts: pd.DataFrame, current_price: float) -> tuple:
        """
        計算 Gamma Exposure (GEX)
        
        GEX = Gamma * Open Interest * 100 * Spot Price
        - Call GEX 是正值 (做市商 Long Gamma)
        - Put GEX 是負值 (做市商 Short Gamma)
        
        解釋:
        - 正 GEX: 作市商會 "高拋低吸" 抑制波動，市場較穩定。
        - 負 GEX: 作市商會 "追漲殺跌" 放大波動，市場易暴漲暴跌。
        """
        try:
            total_gex = 0.0
            gex_profile = {} # Strike -> GEX
            
            # 計算 Call GEX
            if 'gamma' in calls.columns:
                for _, row in calls.iterrows():
                    strike = row['strike']
                    gamma = row.get('gamma', 0) or 0
                    oi = row.get('openInterest', 0) or 0
                    
                    # 每個合約代表 100 股
                    # GEX = Gamma * OI * 100 * Price
                    # 這裡計算的是 "Dollar Gamma Exposure"
                    gex = gamma * oi * 100 * current_price
                    
                    total_gex += gex
                    gex_profile[strike] = gex_profile.get(strike, 0) + gex
            
            # 計算 Put GEX (負值)
            if 'gamma' in puts.columns:
                for _, row in puts.iterrows():
                    strike = row['strike']
                    gamma = row.get('gamma', 0) or 0
                    oi = row.get('openInterest', 0) or 0
                    
                    # Put Gamma 通常視為負數 (從做市商角度)
                    gex = -(gamma * oi * 100 * current_price)
                    
                    total_gex += gex
                    gex_profile[strike] = gex_profile.get(strike, 0) + gex
            
            return total_gex, gex_profile
            
        except Exception as e:
            logger.warning(f"GEX 計算失敗: {e}")
            return 0.0, {}
