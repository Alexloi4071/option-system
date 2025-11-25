# calculation_layer/module18_historical_volatility.py
"""
模塊18: 歷史波動率計算器 (Historical Volatility Calculator)
書籍來源: 金融工程標準模型

功能:
- 計算歷史波動率 (HV)
- 支持多種回溯期間
- 提供 IV/HV 比率分析
- 識別波動率套利機會

歷史波動率 (HV) 說明:
─────────────────────────────────────
歷史波動率衡量股價在過去一段時間內的實際波動程度。
它基於歷史價格數據計算，反映已經發生的波動。

與隱含波動率 (IV) 的對比:
- HV: 基於歷史數據，反映過去的波動
- IV: 基於期權價格，反映市場對未來波動的預期

IV/HV 比率分析:
- 比率 > 1.2: IV 高估（市場預期波動大於歷史）→ 賣出期權
- 比率 < 0.8: IV 低估（市場預期波動小於歷史）→ 買入期權
- 0.8 ≤ 比率 ≤ 1.2: 合理範圍

計算公式:
  對數收益率: r(i) = ln(P(i) / P(i-1))
  
  歷史波動率: HV = √[Σ(r(i) - r̄)² / (n-1)] × √252
  
  其中:
  - P(i) 是第 i 天的收盤價
  - r̄ 是平均對數收益率
  - n 是數據點數量
  - 252 是美股年交易日數
─────────────────────────────────────

參考文獻:
- Hull, J. C. (2018). Options, Futures, and Other Derivatives (10th ed.). Pearson.
- Natenberg, S. (1994). Option Volatility and Pricing. McGraw-Hill.
"""

import logging
import math
import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Dict, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class HVResult:
    """歷史波動率計算結果"""
    historical_volatility: float
    window_days: int
    data_points: int
    start_date: str
    end_date: str
    mean_return: float
    std_return: float
    calculation_date: str
    
    def to_dict(self) -> Dict:
        """轉換為字典"""
        return {
            'historical_volatility': round(self.historical_volatility, 6),
            'historical_volatility_percent': round(self.historical_volatility * 100, 2),
            'window_days': self.window_days,
            'data_points': self.data_points,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'mean_return': round(self.mean_return, 8),
            'std_return': round(self.std_return, 8),
            'calculation_date': self.calculation_date
        }


@dataclass
class IVHVRatioResult:
    """IV/HV 比率分析結果"""
    implied_volatility: float
    historical_volatility: float
    iv_hv_ratio: float
    assessment: str
    recommendation: str
    calculation_date: str
    
    def to_dict(self) -> Dict:
        """轉換為字典"""
        return {
            'implied_volatility': round(self.implied_volatility, 6),
            'implied_volatility_percent': round(self.implied_volatility * 100, 2),
            'historical_volatility': round(self.historical_volatility, 6),
            'historical_volatility_percent': round(self.historical_volatility * 100, 2),
            'iv_hv_ratio': round(self.iv_hv_ratio, 4),
            'assessment': self.assessment,
            'recommendation': self.recommendation,
            'calculation_date': self.calculation_date
        }


class HistoricalVolatilityCalculator:
    """
    歷史波動率計算器
    
    功能:
    - 計算歷史波動率 (HV)
    - 支持多種窗口期（10, 20, 30, 60天）
    - IV/HV 比率分析
    - 波動率套利機會識別
    
    使用示例:
    >>> calculator = HistoricalVolatilityCalculator()
    >>> # 假設 price_series 是 pandas Series
    >>> result = calculator.calculate_hv(
    ...     price_series=price_series,
    ...     window=30
    ... )
    >>> print(f"歷史波動率: {result.historical_volatility*100:.2f}%")
    """
    
    # 常用窗口期
    COMMON_WINDOWS = {
        '10天': 10,
        '20天': 20,
        '30天': 30,
        '60天': 60,
        '90天': 90
    }
    
    # IV/HV 比率閾值
    IV_HV_OVERVALUED_THRESHOLD = 1.2
    IV_HV_UNDERVALUED_THRESHOLD = 0.8
    
    def __init__(self, trading_days_per_year: int = 252):
        """
        初始化歷史波動率計算器
        
        參數:
            trading_days_per_year: 每年交易日數（默認 252，美股標準）
        """
        self.trading_days_per_year = trading_days_per_year
        logger.info("* 歷史波動率計算器已初始化")
        logger.info(f"  年交易日數: {trading_days_per_year}")
    
    def calculate_hv(
        self,
        price_series: pd.Series,
        window: int = 30,
        calculation_date: Optional[str] = None
    ) -> HVResult:
        """
        計算歷史波動率
        
        參數:
            price_series: 價格序列（pandas Series，索引為日期）
            window: 回溯窗口期（天數，默認 30）
            calculation_date: 計算日期（YYYY-MM-DD 格式）
        
        返回:
            HVResult: 包含歷史波動率和統計信息的結果對象
        
        公式:
            對數收益率: r(i) = ln(P(i) / P(i-1))
            
            歷史波動率: HV = √[Σ(r(i) - r̄)² / (n-1)] × √252
            
            其中:
            - P(i) 是第 i 天的價格
            - r̄ 是平均對數收益率
            - n 是數據點數量
            - 252 是年交易日數
        
        示例:
            >>> import pandas as pd
            >>> prices = pd.Series([100, 101, 99, 102, 98], 
            ...                    index=pd.date_range('2024-01-01', periods=5))
            >>> calc = HistoricalVolatilityCalculator()
            >>> result = calc.calculate_hv(prices, window=5)
            >>> print(f"HV: {result.historical_volatility*100:.2f}%")
        """
        try:
            logger.info(f"開始計算歷史波動率...")
            logger.info(f"  窗口期: {window} 天")
            logger.info(f"  數據點數: {len(price_series)}")
            
            # 第1步: 輸入驗證
            if not self._validate_inputs(price_series, window):
                raise ValueError("輸入參數無效")
            
            # 第2步: 獲取計算日期
            if calculation_date is None:
                calculation_date = datetime.now().strftime('%Y-%m-%d')
            
            # 第3步: 選取窗口期數據
            if len(price_series) > window:
                price_series = price_series.iloc[-window:]
                logger.info(f"  使用最近 {window} 天數據")
            
            # 第4步: 計算對數收益率
            # r(i) = ln(P(i) / P(i-1))
            log_returns = np.log(price_series / price_series.shift(1))
            
            # 移除 NaN 值（第一個數據點）
            log_returns = log_returns.dropna()
            
            if len(log_returns) < 2:
                raise ValueError(f"數據點不足，需要至少 2 個數據點，實際: {len(log_returns)}")
            
            logger.info(f"  有效對數收益率數據點: {len(log_returns)}")
            
            # 第5步: 計算統計量
            mean_return = log_returns.mean()
            std_return = log_returns.std(ddof=1)  # 使用樣本標準差（n-1）
            
            logger.debug(f"  平均收益率: {mean_return:.8f}")
            logger.debug(f"  收益率標準差: {std_return:.8f}")
            
            # 第6步: 年化波動率
            # HV = std × √(交易日數/年)
            annualization_factor = math.sqrt(self.trading_days_per_year)
            historical_volatility = std_return * annualization_factor
            
            logger.info(f"  計算結果:")
            logger.info(f"    歷史波動率: {historical_volatility*100:.2f}%")
            
            # 第7步: 獲取日期範圍
            start_date = price_series.index[0].strftime('%Y-%m-%d') if hasattr(price_series.index[0], 'strftime') else str(price_series.index[0])
            end_date = price_series.index[-1].strftime('%Y-%m-%d') if hasattr(price_series.index[-1], 'strftime') else str(price_series.index[-1])
            
            # 第8步: 建立結果對象
            result = HVResult(
                historical_volatility=historical_volatility,
                window_days=window,
                data_points=len(log_returns),
                start_date=start_date,
                end_date=end_date,
                mean_return=mean_return,
                std_return=std_return,
                calculation_date=calculation_date
            )
            
            logger.info(f"* 歷史波動率計算完成")
            
            return result
            
        except Exception as e:
            logger.error(f"x 歷史波動率計算失敗: {e}")
            raise
    
    def calculate_iv_hv_ratio(
        self,
        implied_volatility: float,
        historical_volatility: float,
        calculation_date: Optional[str] = None
    ) -> IVHVRatioResult:
        """
        計算 IV/HV 比率並提供分析
        
        參數:
            implied_volatility: 隱含波動率（小數形式，如 0.25 表示 25%）
            historical_volatility: 歷史波動率（小數形式）
            calculation_date: 計算日期（YYYY-MM-DD 格式）
        
        返回:
            IVHVRatioResult: 包含比率分析和交易建議的結果對象
        
        分析邏輯:
            - 比率 > 1.2: IV 高估 → 賣出期權策略
            - 比率 < 0.8: IV 低估 → 買入期權策略
            - 0.8 ≤ 比率 ≤ 1.2: 合理範圍 → 觀望
        
        示例:
            >>> calc = HistoricalVolatilityCalculator()
            >>> result = calc.calculate_iv_hv_ratio(
            ...     implied_volatility=0.30,
            ...     historical_volatility=0.20
            ... )
            >>> print(f"IV/HV 比率: {result.iv_hv_ratio:.2f}")
            >>> print(f"評估: {result.assessment}")
        """
        try:
            logger.info(f"開始計算 IV/HV 比率...")
            logger.info(f"  隱含波動率 (IV): {implied_volatility*100:.2f}%")
            logger.info(f"  歷史波動率 (HV): {historical_volatility*100:.2f}%")
            
            # 第1步: 輸入驗證
            if implied_volatility <= 0 or historical_volatility <= 0:
                raise ValueError("波動率必須大於 0")
            
            # 第2步: 獲取計算日期
            if calculation_date is None:
                calculation_date = datetime.now().strftime('%Y-%m-%d')
            
            # 第3步: 計算比率
            iv_hv_ratio = implied_volatility / historical_volatility
            
            logger.info(f"  IV/HV 比率: {iv_hv_ratio:.4f}")
            
            # 第4步: 評估和建議
            if iv_hv_ratio >= self.IV_HV_OVERVALUED_THRESHOLD:
                assessment = "IV 高估"
                recommendation = "賣出期權策略（如 Covered Call, Credit Spread）"
                logger.info(f"  ! {assessment}: 市場預期波動大於歷史")
            elif iv_hv_ratio <= self.IV_HV_UNDERVALUED_THRESHOLD:
                assessment = "IV 低估"
                recommendation = "買入期權策略（如 Long Straddle, Debit Spread）"
                logger.info(f"  ! {assessment}: 市場預期波動小於歷史")
            else:
                assessment = "合理範圍"
                recommendation = "觀望，IV 與 HV 相符"
                logger.info(f"  * {assessment}: IV 與 HV 基本一致")
            
            # 第5步: 建立結果對象
            result = IVHVRatioResult(
                implied_volatility=implied_volatility,
                historical_volatility=historical_volatility,
                iv_hv_ratio=iv_hv_ratio,
                assessment=assessment,
                recommendation=recommendation,
                calculation_date=calculation_date
            )
            
            logger.info(f"* IV/HV 比率分析完成")
            
            return result
            
        except Exception as e:
            logger.error(f"x IV/HV 比率計算失敗: {e}")
            raise
    
    def calculate_multiple_windows(
        self,
        price_series: pd.Series,
        windows: Optional[List[int]] = None
    ) -> Dict[int, HVResult]:
        """
        計算多個窗口期的歷史波動率
        
        參數:
            price_series: 價格序列
            windows: 窗口期列表（默認 [10, 20, 30, 60]）
        
        返回:
            Dict[int, HVResult]: 窗口期到結果的映射
        
        示例:
            >>> calc = HistoricalVolatilityCalculator()
            >>> results = calc.calculate_multiple_windows(prices)
            >>> for window, result in results.items():
            ...     print(f"{window}天 HV: {result.historical_volatility*100:.2f}%")
        """
        try:
            if windows is None:
                windows = [10, 20, 30, 60]
            
            logger.info(f"開始計算多窗口期歷史波動率...")
            logger.info(f"  窗口期: {windows}")
            
            results = {}
            for window in windows:
                if len(price_series) >= window + 1:  # 需要至少 window+1 個數據點
                    result = self.calculate_hv(price_series, window)
                    results[window] = result
                    logger.info(f"  {window}天 HV: {result.historical_volatility*100:.2f}%")
                else:
                    logger.warning(f"  ! 數據不足，跳過 {window} 天窗口")
            
            logger.info(f"* 多窗口期計算完成: {len(results)} 個窗口")
            
            return results
            
        except Exception as e:
            logger.error(f"x 多窗口期計算失敗: {e}")
            raise
    
    def calculate_iv_rank(
        self,
        current_iv: float,
        historical_iv_series: pd.Series
    ) -> float:
        """
        計算IV Rank（IV在52週範圍內的相對位置）
        
        參數:
            current_iv: 當前IV（小數形式，如 0.25 = 25%）
            historical_iv_series: 過去252天的IV數據（pandas Series）
        
        返回:
            float: IV Rank（0-100之間的百分比）
        
        公式:
            IV Rank = (當前IV - 52週最低IV) / (52週最高IV - 52週最低IV) × 100%
        
        判斷標準:
            - IV Rank > 80%: IV極高，強烈建議賣期權
            - IV Rank > 50%: IV偏高，適合賣期權
            - IV Rank < 20%: IV偏低，適合買期權
        
        示例:
            >>> calc = HistoricalVolatilityCalculator()
            >>> # 假設52週IV範圍：20% ~ 60%
            >>> historical_iv = pd.Series([0.20, 0.25, ..., 0.60])
            >>> current_iv = 0.50
            >>> iv_rank = calc.calculate_iv_rank(current_iv, historical_iv)
            >>> print(f"IV Rank: {iv_rank:.2f}%")
            75.00%
        """
        try:
            logger.info(f"開始計算IV Rank...")
            logger.info(f"  當前IV: {current_iv*100:.2f}%")
            logger.info(f"  歷史數據點數: {len(historical_iv_series)}")
            
            # 驗證輸入
            if len(historical_iv_series) < 2:
                logger.warning("! 歷史IV數據不足，返回50%（中性）")
                return 50.0
            
            # 計算52週範圍
            iv_min = historical_iv_series.min()
            iv_max = historical_iv_series.max()
            
            logger.info(f"  52週IV範圍: {iv_min*100:.2f}% ~ {iv_max*100:.2f}%")
            
            # 避免除以0
            if iv_max == iv_min:
                logger.warning("! IV範圍為0，返回50%（中性）")
                return 50.0
            
            # 計算IV Rank
            iv_rank = (current_iv - iv_min) / (iv_max - iv_min) * 100
            
            # 限制在0-100範圍
            iv_rank = max(0.0, min(100.0, iv_rank))
            
            logger.info(f"  IV Rank: {iv_rank:.2f}%")
            logger.info(f"* IV Rank計算完成")
            
            return round(iv_rank, 2)
            
        except Exception as e:
            logger.error(f"x IV Rank計算失敗: {e}")
            return 50.0  # 返回中性值
    
    def calculate_iv_percentile(
        self,
        current_iv: float,
        historical_iv_series: pd.Series
    ) -> float:
        """
        計算IV Percentile（當前IV在歷史中的百分位）
        
        參數:
            current_iv: 當前IV（小數形式）
            historical_iv_series: 過去252天的IV數據（pandas Series）
        
        返回:
            float: IV Percentile（0-100之間的百分比）
        
        公式:
            IV Percentile = (歷史中IV低於當前IV的天數) / 總天數 × 100%
        
        判斷標準:
            - IV Percentile > 80%: 當前IV高於80%的歷史日子，適合賣期權
            - IV Percentile < 30%: 當前IV低於70%的歷史日子，適合買期權
        
        示例:
            >>> calc = HistoricalVolatilityCalculator()
            >>> # 假設252天中，200天的IV低於當前IV
            >>> iv_percentile = calc.calculate_iv_percentile(0.50, historical_iv)
            >>> print(f"IV Percentile: {iv_percentile:.2f}%")
            79.37%
        """
        try:
            logger.info(f"開始計算IV Percentile...")
            
            # 驗證輸入
            if len(historical_iv_series) < 2:
                logger.warning("! 歷史IV數據不足，返回50%（中性）")
                return 50.0
            
            # 計算低於當前IV的天數
            days_below = (historical_iv_series < current_iv).sum()
            total_days = len(historical_iv_series)
            
            # 計算百分位
            iv_percentile = (days_below / total_days) * 100
            
            logger.info(f"  {days_below}/{total_days} 天的IV低於當前IV")
            logger.info(f"  IV Percentile: {iv_percentile:.2f}%")
            logger.info(f"* IV Percentile計算完成")
            
            return round(iv_percentile, 2)
            
        except Exception as e:
            logger.error(f"x IV Percentile計算失敗: {e}")
            return 50.0  # 返回中性值
    
    def get_iv_recommendation(
        self,
        iv_rank: float,
        iv_percentile: float
    ) -> Dict:
        """
        根據IV Rank和IV Percentile生成交易建議
        
        參數:
            iv_rank: IV Rank（0-100）
            iv_percentile: IV Percentile（0-100）
        
        返回:
            Dict: {
                'action': 'Short' | 'Long' | 'Neutral',
                'reason': 原因說明,
                'confidence': 'High' | 'Medium' | 'Low'
            }
        
        判斷邏輯:
            - IV Rank > 80% 或 IV Percentile > 80%: 強烈建議賣期權
            - IV Rank > 50% 或 IV Percentile > 70%: 建議賣期權
            - IV Rank < 20% 或 IV Percentile < 30%: 建議買期權
            - 其他: 中性
        """
        try:
            logger.info(f"生成IV交易建議...")
            logger.info(f"  IV Rank: {iv_rank:.2f}%")
            logger.info(f"  IV Percentile: {iv_percentile:.2f}%")
            
            # 極高IV（強烈賣出信號）
            if iv_rank >= 80 or iv_percentile >= 80:
                recommendation = {
                    'action': 'Short',
                    'reason': 'IV極高，處於歷史頂部區域，適合賣出期權收取高額權金',
                    'confidence': 'High',
                    'iv_rank': iv_rank,
                    'iv_percentile': iv_percentile
                }
                logger.info(f"  ! 建議: {recommendation['action']} (信心度: {recommendation['confidence']})")
            
            # 偏高IV（賣出信號）
            elif iv_rank >= 50 or iv_percentile >= 70:
                recommendation = {
                    'action': 'Short',
                    'reason': 'IV偏高，高於歷史中位數，適合賣出期權',
                    'confidence': 'Medium',
                    'iv_rank': iv_rank,
                    'iv_percentile': iv_percentile
                }
                logger.info(f"  建議: {recommendation['action']} (信心度: {recommendation['confidence']})")
            
            # 偏低IV（買入信號）
            elif iv_rank <= 20 or iv_percentile <= 30:
                recommendation = {
                    'action': 'Long',
                    'reason': 'IV偏低，低於歷史水平，適合買入期權',
                    'confidence': 'Medium',
                    'iv_rank': iv_rank,
                    'iv_percentile': iv_percentile
                }
                logger.info(f"  建議: {recommendation['action']} (信心度: {recommendation['confidence']})")
            
            # 中性區域
            else:
                recommendation = {
                    'action': 'Neutral',
                    'reason': 'IV處於中性區域，無明顯優勢，建議觀望',
                    'confidence': 'Low',
                    'iv_rank': iv_rank,
                    'iv_percentile': iv_percentile
                }
                logger.info(f"  建議: {recommendation['action']} (信心度: {recommendation['confidence']})")
            
            return recommendation
            
        except Exception as e:
            logger.error(f"x 生成建議失敗: {e}")
            return {
                'action': 'Neutral',
                'reason': '計算錯誤，無法生成建議',
                'confidence': 'Low'
            }
    
    @staticmethod
    def _validate_inputs(price_series: pd.Series, window: int) -> bool:
        """
        驗證輸入參數
        
        參數:
            price_series: 價格序列
            window: 窗口期
        
        返回:
            bool: True 如果所有參數有效
        """
        logger.info("驗證輸入參數...")
        
        # 驗證價格序列類型
        if not isinstance(price_series, pd.Series):
            logger.error("x price_series 必須是 pandas Series")
            return False
        
        # 驗證數據點數量
        if len(price_series) < 2:
            logger.error(f"x 數據點不足: {len(price_series)}，需要至少 2 個")
            return False
        
        # 驗證窗口期
        if not isinstance(window, int) or window < 2:
            logger.error(f"x 窗口期必須是 ≥ 2 的整數: {window}")
            return False
        
        if window > len(price_series):
            logger.warning(f"  ! 窗口期 ({window}) 大於數據點數 ({len(price_series)})，將使用所有數據")
        
        # 驗證價格為正
        if (price_series <= 0).any():
            logger.error("x 價格序列包含非正值")
            return False
        
        logger.info("* 輸入參數驗證通過")
        return True


# 使用示例和測試
if __name__ == "__main__":
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    import logging
    logging.basicConfig(level=logging.INFO)
    
    calculator = HistoricalVolatilityCalculator()
    
    print("\n" + "=" * 70)
    print("模塊18: 歷史波動率計算器")
    print("=" * 70)
    
    # 例子1: 計算 HV
    print("\n【例子1】計算歷史波動率")
    print("-" * 70)
    
    # 創建模擬價格數據
    dates = pd.date_range('2024-01-01', periods=60, freq='D')
    # 模擬股價：起始 100，隨機波動
    np.random.seed(42)
    returns = np.random.normal(0.001, 0.02, 60)  # 平均 0.1%，標準差 2%
    prices = 100 * np.exp(np.cumsum(returns))
    price_series = pd.Series(prices, index=dates)
    
    result_30d = calculator.calculate_hv(price_series, window=30)
    
    print(f"\n計算結果 (30天窗口):")
    print(f"  歷史波動率: {result_30d.historical_volatility*100:.2f}%")
    print(f"  數據點數: {result_30d.data_points}")
    print(f"  日期範圍: {result_30d.start_date} 至 {result_30d.end_date}")
    
    # 例子2: 多窗口期計算
    print("\n【例子2】多窗口期 HV 計算")
    print("-" * 70)
    
    results_multi = calculator.calculate_multiple_windows(
        price_series,
        windows=[10, 20, 30, 60]
    )
    
    print(f"\n多窗口期結果:")
    for window, result in sorted(results_multi.items()):
        print(f"  {window}天 HV: {result.historical_volatility*100:.2f}%")
    
    # 例子3: IV/HV 比率分析
    print("\n【例子3】IV/HV 比率分析")
    print("-" * 70)
    
    # 假設隱含波動率為 35%
    implied_vol = 0.35
    historical_vol = result_30d.historical_volatility
    
    ratio_result = calculator.calculate_iv_hv_ratio(
        implied_volatility=implied_vol,
        historical_volatility=historical_vol
    )
    
    print(f"\n比率分析:")
    print(f"  隱含波動率 (IV): {ratio_result.implied_volatility*100:.2f}%")
    print(f"  歷史波動率 (HV): {ratio_result.historical_volatility*100:.2f}%")
    print(f"  IV/HV 比率: {ratio_result.iv_hv_ratio:.4f}")
    print(f"  評估: {ratio_result.assessment}")
    print(f"  建議: {ratio_result.recommendation}")
    
    print("\n" + "=" * 70)
    print("注: HV 用於評估 IV 是否合理，識別波動率套利機會")
    print("=" * 70)
