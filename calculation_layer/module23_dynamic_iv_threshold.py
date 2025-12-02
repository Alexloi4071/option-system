#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module 23: 動態IV閾值計算

功能:
1. 基於股票52週IV範圍動態調整閾值
2. 計算75th percentile為高閾值，25th percentile為低閾值
3. 數據不足時降級到靜態閾值（VIX ± 10%）
4. 增強金曹12監察崗位的IV判斷能力

來源: 金曹《期權制勝》崗位3 IV監察 + 美股期權市場最佳實踐

作者: Kiro
日期: 2025-11-25
版本: 1.0.0
"""

import logging
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Dict, Optional, Union, List
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class IVThresholdResult:
    """IV閾值計算結果"""
    current_iv: float
    high_threshold: float
    low_threshold: float
    median_iv: float
    status: str  # '高於歷史水平', '低於歷史水平', '正常範圍'
    data_quality: str  # 'sufficient', 'insufficient'
    historical_days: int
    calculation_date: str
    
    # 額外信息
    percentile_75: float = 0.0
    percentile_25: float = 0.0
    iv_min: float = 0.0
    iv_max: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            'current_iv': round(self.current_iv, 2),
            'high_threshold': round(self.high_threshold, 2),
            'low_threshold': round(self.low_threshold, 2),
            'median_iv': round(self.median_iv, 2),
            'status': self.status,
            'data_quality': self.data_quality,
            'historical_days': self.historical_days,
            'calculation_date': self.calculation_date,
            'percentile_75': round(self.percentile_75, 2),
            'percentile_25': round(self.percentile_25, 2),
            'iv_min': round(self.iv_min, 2),
            'iv_max': round(self.iv_max, 2)
        }


class DynamicIVThresholdCalculator:
    """
    動態IV閾值計算器
    
    基於金曹《期權制勝》崗位3 IV監察，整合美股期權市場最佳實踐，
    使用歷史IV數據動態計算閾值，而非使用固定閾值。
    
    判斷標準:
    - 高閾值: 75th percentile of historical IV
    - 低閾值: 25th percentile of historical IV
    - 數據不足時: 使用 VIX ± 10% 作為靜態閾值
    
    最低數據要求: 200個交易日（約10個月）
    推薦數據量: 252個交易日（1年）
    """
    
    # 最低數據要求
    MIN_DATA_POINTS = 200
    RECOMMENDED_DATA_POINTS = 252
    
    # 靜態閾值偏移量
    STATIC_THRESHOLD_OFFSET = 10.0  # VIX ± 10%
    
    def __init__(self):
        logger.info("* 動態IV閾值計算器已初始化")
    
    def calculate_thresholds(
        self,
        current_iv: float,
        historical_iv: Optional[Union[pd.Series, List[float], np.ndarray]] = None,
        vix: float = 20.0
    ) -> IVThresholdResult:
        """
        計算動態IV閾值
        
        參數:
            current_iv: 當前IV（百分比形式，如 25.5 表示 25.5%）
            historical_iv: 歷史IV數據（過去252天）
            vix: VIX指數（用於靜態閾值降級）
        
        返回:
            IVThresholdResult: 閾值計算結果
        """
        try:
            logger.info(f"開始動態IV閾值計算...")
            logger.info(f"  當前IV: {current_iv:.2f}%")
            
            calculation_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 檢查歷史數據是否足夠
            if historical_iv is None or len(historical_iv) < self.MIN_DATA_POINTS:
                logger.info(f"  歷史數據不足 ({len(historical_iv) if historical_iv is not None else 0} < {self.MIN_DATA_POINTS})，使用靜態閾值")
                return self._calculate_static_thresholds(current_iv, vix, calculation_date)
            
            # 轉換為 numpy array
            if isinstance(historical_iv, pd.Series):
                iv_data = historical_iv.dropna().values
            elif isinstance(historical_iv, list):
                iv_data = np.array([x for x in historical_iv if x is not None and not np.isnan(x)])
            else:
                iv_data = historical_iv[~np.isnan(historical_iv)]
            
            # 再次檢查有效數據量
            if len(iv_data) < self.MIN_DATA_POINTS:
                logger.info(f"  有效數據不足 ({len(iv_data)} < {self.MIN_DATA_POINTS})，使用靜態閾值")
                return self._calculate_static_thresholds(current_iv, vix, calculation_date)
            
            # 計算動態閾值
            return self._calculate_dynamic_thresholds(current_iv, iv_data, calculation_date)
            
        except Exception as e:
            logger.error(f"x 動態IV閾值計算失敗: {e}")
            # 降級到靜態閾值
            return self._calculate_static_thresholds(current_iv, vix, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    def _calculate_dynamic_thresholds(
        self,
        current_iv: float,
        iv_data: np.ndarray,
        calculation_date: str
    ) -> IVThresholdResult:
        """計算動態閾值（基於歷史數據）"""
        
        # 計算百分位數
        percentile_75 = float(np.percentile(iv_data, 75))
        percentile_25 = float(np.percentile(iv_data, 25))
        median_iv = float(np.median(iv_data))
        iv_min = float(np.min(iv_data))
        iv_max = float(np.max(iv_data))
        
        # 設定閾值
        high_threshold = percentile_75
        low_threshold = percentile_25
        
        # 判斷當前IV狀態
        if current_iv > high_threshold:
            status = "高於歷史水平"
            logger.info(f"  狀態: {status} (IV {current_iv:.2f}% > 75th {high_threshold:.2f}%)")
        elif current_iv < low_threshold:
            status = "低於歷史水平"
            logger.info(f"  狀態: {status} (IV {current_iv:.2f}% < 25th {low_threshold:.2f}%)")
        else:
            status = "正常範圍"
            logger.info(f"  狀態: {status} (IV {current_iv:.2f}% 在 {low_threshold:.2f}%-{high_threshold:.2f}% 範圍內)")
        
        result = IVThresholdResult(
            current_iv=current_iv,
            high_threshold=high_threshold,
            low_threshold=low_threshold,
            median_iv=median_iv,
            status=status,
            data_quality='sufficient',
            historical_days=len(iv_data),
            calculation_date=calculation_date,
            percentile_75=percentile_75,
            percentile_25=percentile_25,
            iv_min=iv_min,
            iv_max=iv_max
        )
        
        logger.info(f"* 動態IV閾值計算完成")
        logger.info(f"  高閾值 (75th): {high_threshold:.2f}%")
        logger.info(f"  低閾值 (25th): {low_threshold:.2f}%")
        logger.info(f"  歷史數據: {len(iv_data)} 天")
        
        return result
    
    def _calculate_static_thresholds(
        self,
        current_iv: float,
        vix: float,
        calculation_date: str
    ) -> IVThresholdResult:
        """計算靜態閾值（基於VIX）"""
        
        # 使用 VIX ± 10% 作為閾值
        high_threshold = vix + self.STATIC_THRESHOLD_OFFSET
        low_threshold = max(5.0, vix - self.STATIC_THRESHOLD_OFFSET)  # 最低5%
        median_iv = vix
        
        # 判斷當前IV狀態（即使數據不足也要給出狀態）
        if current_iv > high_threshold:
            status = "HIGH (高於VIX基準)"
        elif current_iv < low_threshold:
            status = "LOW (低於VIX基準)"
        else:
            status = "NORMAL (VIX基準範圍內)"
        
        result = IVThresholdResult(
            current_iv=current_iv,
            high_threshold=high_threshold,
            low_threshold=low_threshold,
            median_iv=median_iv,
            status=status,
            data_quality='insufficient',
            historical_days=0,
            calculation_date=calculation_date,
            percentile_75=high_threshold,
            percentile_25=low_threshold,
            iv_min=low_threshold,
            iv_max=high_threshold
        )
        
        logger.info(f"* 靜態IV閾值計算完成 (基於VIX {vix:.2f}%)")
        logger.info(f"  當前IV: {current_iv:.2f}%")
        logger.info(f"  高閾值: {high_threshold:.2f}% (VIX + 10%)")
        logger.info(f"  低閾值: {low_threshold:.2f}% (VIX - 10%)")
        logger.info(f"  狀態: {status}")
        logger.info(f"  注意: 使用VIX靜態閾值（歷史IV數據不足）")
        
        return result
    
    def get_trading_suggestion(self, result: IVThresholdResult) -> Dict:
        """
        根據IV閾值結果獲取交易建議
        
        參數:
            result: IVThresholdResult 閾值計算結果
        
        返回:
            Dict: 交易建議
        """
        if result.status == "高於歷史水平":
            return {
                'action': 'Short',
                'reason': f'當前IV {result.current_iv:.1f}% 高於75th百分位 {result.high_threshold:.1f}%',
                'strategies': ['Iron Condor', 'Short Straddle', 'Credit Spread'],
                'confidence': 'High' if result.data_quality == 'sufficient' else 'Medium'
            }
        elif result.status == "低於歷史水平":
            return {
                'action': 'Long',
                'reason': f'當前IV {result.current_iv:.1f}% 低於25th百分位 {result.low_threshold:.1f}%',
                'strategies': ['Long Straddle', 'Debit Spread', 'Long Options'],
                'confidence': 'High' if result.data_quality == 'sufficient' else 'Medium'
            }
        else:
            return {
                'action': 'Neutral',
                'reason': f'當前IV {result.current_iv:.1f}% 在正常範圍 {result.low_threshold:.1f}%-{result.high_threshold:.1f}%',
                'strategies': ['Calendar Spread', 'Butterfly', '觀望'],
                'confidence': 'Low'
            }
