#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# calculation_layer/module34_volume_profile.py
"""
模塊34: 籌碼分佈分析 (Volume Profile)

功能:
- 計算 Point of Control (POC) - 成交量最密集的價格（最強支撐/阻力）
- 計算 Value Area High/Low (VAH/VAL) - 涵蓋 70% 成交量的價值區間
- 識別 High Volume Nodes (HVN) - 其他次級支撐/阻力
- 提供期權行使價 (Strike Price) 的防禦性選點建議

數據需求:
- pandas DataFrame (需包含 High, Low, Close, Volume)
- 建議最少提供 90 天，最理想 180 天的日K線數據。
"""

import logging
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class VolumeNode:
    """籌碼節點"""
    price_level: float
    volume: float
    is_poc: bool = False
    is_hvn: bool = False

@dataclass
class VolumeProfileResult:
    """籌碼分佈計算結果"""
    ticker: str
    poc: float                       # Point of Control (最密集籌碼區)
    val: float                       # Value Area Low (價值區間下緣)
    vah: float                       # Value Area High (價值區間上緣)
    hvn_levels: List[float]          # 高成交量節點 (次級支撐/阻力)
    current_price: float             # 當前股價
    total_volume: float              # 總成交量
    bins_data: List[VolumeNode] = field(default_factory=list) # 所有價格區間的分佈
    calculation_date: str = ""

    def get_support_levels(self, current_price: float = None) -> List[float]:
        """獲取目前價格下方的所有支撐位 (由近到遠排序)"""
        p = current_price or self.current_price
        levels = [self.poc, self.val, self.vah] + self.hvn_levels
        supports = list(set([lvl for lvl in levels if lvl < p]))
        return sorted(supports, reverse=True)

    def get_resistance_levels(self, current_price: float = None) -> List[float]:
        """獲取目前價格上方的所有阻力位 (由近到遠排序)"""
        p = current_price or self.current_price
        levels = [self.poc, self.val, self.vah] + self.hvn_levels
        resistances = list(set([lvl for lvl in levels if lvl > p]))
        return sorted(resistances)

    def to_dict(self) -> Dict:
        return {
            'ticker': self.ticker,
            'poc': round(self.poc, 2),
            'val': round(self.val, 2),
            'vah': round(self.vah, 2),
            'hvn_levels': [round(x, 2) for x in self.hvn_levels],
            'current_price': round(self.current_price, 2) if self.current_price else None,
            'calculation_date': self.calculation_date
        }

class VolumeProfileAnalyzer:
    """
    籌碼分佈分析器 (Volume Profile)
    用來計算 POC, Value Area (70%) 與 HVN。
    """

    def __init__(self, bins: int = 50, value_area_pct: float = 0.7):
        """
        初始化籌碼分析器
        :param bins: 價格區間的分割數 (越多越細緻，但也更容易碎片化，建議 50-100)
        :param value_area_pct: 價值區間涵蓋的總成交量百分比，通常為 70% (0.7)
        """
        self.bins = bins
        self.value_area_pct = value_area_pct
        logger.info(f"* Module 34 籌碼分佈分析器已初始化 (bins={bins})")

    def analyze(self, ticker: str, daily_data: pd.DataFrame, current_price: float = None) -> Optional[VolumeProfileResult]:
        """
        執行籌碼分析
        :param ticker: 股票代碼
        :param daily_data: 至少包含 'High', 'Low', 'Close', 'Volume' 的 DataFrame
        :param current_price: 當前最新價格
        :return: VolumeProfileResult 對象
        """
        try:
            logger.info(f"開始 {ticker} 籌碼分佈分析 (Volume Profile)...")

            if daily_data is None or len(daily_data) < 20:
                logger.warning(f"! {ticker} 歷史數據不足，無法計算籌碼分佈")
                return None

            # 確保必要欄位存在
            required_cols = ['High', 'Low', 'Close', 'Volume']
            if not all(col in daily_data.columns for col in required_cols):
                logger.error(f"x DataFrame 缺少必要欄位: {required_cols}")
                return None

            # 清除 NaN
            df = daily_data[required_cols].dropna().copy()
            if len(df) == 0:
                return None

            curr_price = current_price or df['Close'].iloc[-1]
            min_price = df['Low'].min()
            max_price = df['High'].max()
            
            # 如果數據異常，沒有波動
            if max_price == min_price:
                logger.warning(f"! {ticker} 價格無波動，無法建立籌碼層")
                return None

            # 1. 建立 Bins
            step = (max_price - min_price) / self.bins
            bin_edges = np.linspace(min_price, max_price, self.bins + 1)
            bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
            volume_profile = np.zeros(self.bins)

            # 2. 分配成交量到 Bins
            # 更精確的方法: 將每天的成交量均勻分佈在當天的 Low 到 High 之間對應的 Bins 裡。
            for _, row in df.iterrows():
                high = row['High']
                low = row['Low']
                vol = row['Volume']
                
                # 處理沒有波動的日子 (High == Low)
                if high == low:
                    idx = np.digitize(high, bin_edges) - 1
                    idx = min(max(idx, 0), self.bins - 1)
                    volume_profile[idx] += vol
                    continue
                
                # 計算每天價格範圍覆蓋到的 bin index
                start_idx = np.digitize(low, bin_edges) - 1
                end_idx = np.digitize(high, bin_edges) - 1
                
                # 邊界防護
                start_idx = min(max(start_idx, 0), self.bins - 1)
                end_idx = min(max(end_idx, 0), self.bins - 1)
                
                bins_covered = end_idx - start_idx + 1
                if bins_covered > 0:
                    vol_per_bin = vol / bins_covered
                    for i in range(start_idx, end_idx + 1):
                        volume_profile[i] += vol_per_bin

            total_vol = volume_profile.sum()
            if total_vol == 0:
                return None

            # 3. 找出 POC (Point of Control)
            poc_index = np.argmax(volume_profile)
            poc_price = bin_centers[poc_index]

            # 4. 找出 Value Area (VAH & VAL)
            va_volume_target = total_vol * self.value_area_pct
            current_va_volume = volume_profile[poc_index]
            
            up_idx = poc_index + 1
            down_idx = poc_index - 1
            
            while current_va_volume < va_volume_target:
                # 檢查上下兩邊的量，把較大的一邊納入 Value Area
                up_vol = volume_profile[up_idx] if up_idx < self.bins else 0
                down_vol = volume_profile[down_idx] if down_idx >= 0 else 0
                
                if up_vol == 0 and down_vol == 0:
                    break
                    
                if up_vol >= down_vol:
                    current_va_volume += up_vol
                    up_idx += 1
                else:
                    current_va_volume += down_vol
                    down_idx -= 1

            # Value Area 範圍 (確保不越界)
            val_idx = max(0, down_idx + 1)
            vah_idx = min(self.bins - 1, up_idx - 1)
            
            val = bin_centers[val_idx]
            vah = bin_centers[vah_idx]

            # 5. 找出 High Volume Nodes (HVNs)
            # 尋找局部峰值，且成交量大於平均的 1.2 倍
            hvn_levels = []
            avg_vol_per_bin = total_vol / self.bins
            hvn_threshold = avg_vol_per_bin * 1.2
            
            for i in range(1, self.bins - 1):
                # 判斷是否為局部最高點 (峰值)
                if volume_profile[i] > volume_profile[i-1] and volume_profile[i] > volume_profile[i+1]:
                    if volume_profile[i] > hvn_threshold:
                        # 排除掉剛好等於 POC 的點
                        if i != poc_index:
                            hvn_levels.append(float(bin_centers[i]))

            # 6. 建構結果集
            nodes = []
            for i in range(self.bins):
                is_poc = (i == poc_index)
                is_hvn = (float(bin_centers[i]) in hvn_levels)
                nodes.append(VolumeNode(
                    price_level=float(bin_centers[i]),
                    volume=float(volume_profile[i]),
                    is_poc=is_poc,
                    is_hvn=is_hvn
                ))

            result = VolumeProfileResult(
                ticker=ticker,
                poc=float(poc_price),
                val=float(val),
                vah=float(vah),
                hvn_levels=hvn_levels,
                current_price=float(curr_price),
                total_volume=float(total_vol),
                bins_data=nodes,
                calculation_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            )

            logger.info(f"  POC: {result.poc:.2f} | VAL: {result.val:.2f} | VAH: {result.vah:.2f}")
            logger.info(f"  HVNs 數量: {len(hvn_levels)}")
            
            return result

        except Exception as e:
            logger.error(f"x 籌碼分佈分析失敗: {e}", exc_info=True)
            return None


if __name__ == "__main__":
    # 基本測試
    logging.basicConfig(level=logging.INFO)
    np.random.seed(42)
    
    dates = pd.date_range('2024-01-01', periods=100, freq='D')
    
    # 模擬在 $150 附近有很多橫盤成交 (POC)，然後漲到 $180
    prices = np.concatenate([
        np.random.normal(150, 2, 50), # 橫盤在 150
        np.linspace(150, 180, 10),    # 上漲
        np.random.normal(180, 2, 40)  # 橫盤在 180
    ])
    volumes = np.random.randint(1000, 5000, 100)
    
    df = pd.DataFrame({
        'Open': prices * 0.99,
        'High': prices * 1.01,
        'Low': prices * 0.98,
        'Close': prices,
        'Volume': volumes
    }, index=dates)

    analyzer = VolumeProfileAnalyzer(bins=30)
    res = analyzer.analyze("TEST", df, current_price=178.0)
    
    print("\n=== 籌碼分佈測試 ===")
    print(res.to_dict())
    print("Supports:", res.get_support_levels())
    print("Resistances:", res.get_resistance_levels())
