# calculation_layer/module21_momentum_filter.py
"""
模塊21: 動量過濾器 (Momentum Filter)
目的: 避免在強勢股票上逆勢做空，防止虧損

理論基礎:
- 2024年牛津大學研究：動量效應集中在高估股票中
- 被高估的股票反而產生最強的動量收益
- 市場追漲情緒可持續6-12個月

使用場景:
- 在Module 3套戥水位中，判斷是否應該Short Call
- 即使期權被高估，如果動量強勁，也不應該逆勢做空
"""

import logging
from dataclasses import dataclass
from typing import Dict, Optional
from datetime import datetime, timedelta
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class MomentumResult:
    """動量分析結果"""
    ticker: str
    momentum_score: float  # 0-1之間，越高表示動量越強
    price_momentum: float  # 價格動量得分
    volume_momentum: float  # 成交量動量得分
    relative_strength: float  # 相對強度得分
    recommendation: str  # 建議
    confidence: str  # 信心度
    calculation_date: str
    
    # 詳細數據
    price_change_1m: Optional[float] = None
    price_change_3m: Optional[float] = None
    volume_trend: Optional[float] = None
    rs_vs_spy: Optional[float] = None
    
    def to_dict(self) -> Dict:
        """轉換為字典"""
        return {
            'ticker': self.ticker,
            'momentum_score': round(self.momentum_score, 4),
            'price_momentum': round(self.price_momentum, 4),
            'volume_momentum': round(self.volume_momentum, 4),
            'relative_strength': round(self.relative_strength, 4),
            'recommendation': self.recommendation,
            'confidence': self.confidence,
            'calculation_date': self.calculation_date,
            'details': {
                'price_change_1m': round(self.price_change_1m, 2) if self.price_change_1m else None,
                'price_change_3m': round(self.price_change_3m, 2) if self.price_change_3m else None,
                'volume_trend': round(self.volume_trend, 2) if self.volume_trend else None,
                'rs_vs_spy': round(self.rs_vs_spy, 2) if self.rs_vs_spy else None
            }
        }


class MomentumFilter:
    """
    動量過濾器
    
    計算公式:
    ────────────────────────────────
    動量得分 = 價格動量(50%) + 成交量動量(30%) + 相對強度(20%)
    
    其中:
    - 價格動量 = 1個月變化(30%) + 3個月變化(20%)
    - 成交量動量 = 成交量趨勢(30%)
    - 相對強度 = 相對SPY的表現(20%)
    
    判斷標準:
    - 動量得分 > 0.7: 強動量，不要逆勢
    - 動量得分 0.4-0.7: 中等動量，謹慎
    - 動量得分 < 0.4: 弱動量，可以逆勢
    ────────────────────────────────
    """
    
    # 動量閾值
    STRONG_MOMENTUM_THRESHOLD = 0.7
    MODERATE_MOMENTUM_THRESHOLD = 0.4
    
    # 權重配置
    WEIGHTS = {
        'price_1m': 0.30,
        'price_3m': 0.20,
        'volume': 0.30,
        'relative_strength': 0.20
    }
    
    def __init__(self, data_fetcher=None):
        """
        初始化動量過濾器
        
        參數:
            data_fetcher: 數據獲取器（用於獲取歷史價格和成交量）
        """
        self.data_fetcher = data_fetcher
        logger.info("* 動量過濾器已初始化")
    
    def calculate(self,
                  ticker: str,
                  historical_data: Optional[pd.DataFrame] = None,
                  benchmark_data: Optional[pd.DataFrame] = None,
                  calculation_date: str = None) -> MomentumResult:
        """
        計算動量得分
        
        參數:
            ticker: 股票代碼
            historical_data: 歷史價格數據（包含Close和Volume列）
            benchmark_data: 基準指數數據（默認SPY）
            calculation_date: 計算日期
        
        返回:
            MomentumResult: 動量分析結果
        """
        try:
            logger.info(f"開始計算 {ticker} 的動量得分...")
            
            if calculation_date is None:
                calculation_date = datetime.now().strftime('%Y-%m-%d')
            
            # 如果沒有提供歷史數據，嘗試從data_fetcher獲取
            if historical_data is None:
                if self.data_fetcher is None:
                    raise ValueError("需要提供historical_data或data_fetcher")
                historical_data = self._fetch_historical_data(ticker, days=90)
            
            # 驗證數據
            if historical_data is None or len(historical_data) < 30:
                logger.warning(f"! {ticker} 歷史數據不足，使用默認中性動量")
                return self._create_neutral_result(ticker, calculation_date)
            
            # 計算各個組成部分
            price_momentum = self._calculate_price_momentum(historical_data)
            volume_momentum = self._calculate_volume_momentum(historical_data)
            relative_strength = self._calculate_relative_strength(
                historical_data, benchmark_data
            )
            
            # 計算總動量得分
            momentum_score = (
                price_momentum['score'] * (self.WEIGHTS['price_1m'] + self.WEIGHTS['price_3m']) +
                volume_momentum['score'] * self.WEIGHTS['volume'] +
                relative_strength['score'] * self.WEIGHTS['relative_strength']
            )
            
            # 限制在0-1範圍
            momentum_score = max(0.0, min(1.0, momentum_score))
            
            # 生成建議
            recommendation, confidence = self._generate_recommendation(momentum_score)
            
            logger.info(f"  動量得分: {momentum_score:.4f}")
            logger.info(f"  建議: {recommendation}")
            
            result = MomentumResult(
                ticker=ticker,
                momentum_score=momentum_score,
                price_momentum=price_momentum['score'],
                volume_momentum=volume_momentum['score'],
                relative_strength=relative_strength['score'],
                recommendation=recommendation,
                confidence=confidence,
                calculation_date=calculation_date,
                price_change_1m=price_momentum.get('change_1m'),
                price_change_3m=price_momentum.get('change_3m'),
                volume_trend=volume_momentum.get('trend'),
                rs_vs_spy=relative_strength.get('rs_value')
            )
            
            logger.info(f"* 動量計算完成")
            return result
            
        except Exception as e:
            logger.error(f"x 動量計算失敗: {e}")
            # 返回中性結果而不是拋出異常
            return self._create_neutral_result(ticker, calculation_date)
    
    def _calculate_price_momentum(self, data: pd.DataFrame) -> Dict:
        """
        計算價格動量
        
        返回:
            {
                'score': 0-1之間的得分,
                'change_1m': 1個月變化百分比,
                'change_3m': 3個月變化百分比
            }
        """
        try:
            prices = data['Close']
            
            # 1個月變化（約21個交易日）
            if len(prices) >= 21:
                price_1m_ago = prices.iloc[-21]
                price_now = prices.iloc[-1]
                change_1m = ((price_now - price_1m_ago) / price_1m_ago) * 100
            else:
                change_1m = 0.0
            
            # 3個月變化（約63個交易日）
            if len(prices) >= 63:
                price_3m_ago = prices.iloc[-63]
                change_3m = ((price_now - price_3m_ago) / price_3m_ago) * 100
            else:
                change_3m = change_1m  # 降級使用1個月數據
            
            # 轉換為0-1得分
            # 假設±30%為極端值
            score_1m = self._normalize_percentage(change_1m, max_value=30.0)
            score_3m = self._normalize_percentage(change_3m, max_value=30.0)
            
            # 加權平均
            score = score_1m * 0.6 + score_3m * 0.4
            
            logger.debug(f"  價格動量: 1M={change_1m:.2f}%, 3M={change_3m:.2f}%, 得分={score:.4f}")
            
            return {
                'score': score,
                'change_1m': change_1m,
                'change_3m': change_3m
            }
            
        except Exception as e:
            logger.warning(f"! 價格動量計算失敗: {e}")
            return {'score': 0.5, 'change_1m': 0.0, 'change_3m': 0.0}
    
    def _calculate_volume_momentum(self, data: pd.DataFrame) -> Dict:
        """
        計算成交量動量
        
        返回:
            {
                'score': 0-1之間的得分,
                'trend': 成交量趨勢百分比
            }
        """
        try:
            volumes = data['Volume']
            
            # 計算最近10天vs前20天的平均成交量比率
            if len(volumes) >= 30:
                recent_avg = volumes.iloc[-10:].mean()
                previous_avg = volumes.iloc[-30:-10].mean()
                
                if previous_avg > 0:
                    volume_ratio = (recent_avg / previous_avg - 1) * 100
                else:
                    volume_ratio = 0.0
            else:
                volume_ratio = 0.0
            
            # 轉換為0-1得分
            # 假設±50%為極端值
            score = self._normalize_percentage(volume_ratio, max_value=50.0)
            
            logger.debug(f"  成交量動量: 趨勢={volume_ratio:.2f}%, 得分={score:.4f}")
            
            return {
                'score': score,
                'trend': volume_ratio
            }
            
        except Exception as e:
            logger.warning(f"! 成交量動量計算失敗: {e}")
            return {'score': 0.5, 'trend': 0.0}
    
    def _calculate_relative_strength(self,
                                     data: pd.DataFrame,
                                     benchmark_data: Optional[pd.DataFrame] = None) -> Dict:
        """
        計算相對強度（相對於SPY）
        
        返回:
            {
                'score': 0-1之間的得分,
                'rs_value': 相對強度值
            }
        """
        try:
            # 如果沒有基準數據，返回中性得分
            if benchmark_data is None or len(benchmark_data) < 63:
                logger.debug("  相對強度: 無基準數據，使用中性得分")
                return {'score': 0.5, 'rs_value': 0.0}
            
            # 計算3個月收益率
            stock_prices = data['Close']
            benchmark_prices = benchmark_data['Close']
            
            if len(stock_prices) >= 63 and len(benchmark_prices) >= 63:
                stock_return = ((stock_prices.iloc[-1] - stock_prices.iloc[-63]) / 
                               stock_prices.iloc[-63]) * 100
                benchmark_return = ((benchmark_prices.iloc[-1] - benchmark_prices.iloc[-63]) / 
                                   benchmark_prices.iloc[-63]) * 100
                
                # 相對強度 = 股票收益 - 基準收益
                rs_value = stock_return - benchmark_return
            else:
                rs_value = 0.0
            
            # 轉換為0-1得分
            # 假設±20%為極端值
            score = self._normalize_percentage(rs_value, max_value=20.0)
            
            logger.debug(f"  相對強度: RS={rs_value:.2f}%, 得分={score:.4f}")
            
            return {
                'score': score,
                'rs_value': rs_value
            }
            
        except Exception as e:
            logger.warning(f"! 相對強度計算失敗: {e}")
            return {'score': 0.5, 'rs_value': 0.0}
    
    def _normalize_percentage(self, value: float, max_value: float) -> float:
        """
        將百分比值標準化到0-1範圍
        
        參數:
            value: 百分比值（可以是正或負）
            max_value: 最大絕對值（用於標準化）
        
        返回:
            0-1之間的得分（0.5為中性）
        """
        # 限制在[-max_value, +max_value]範圍
        normalized = max(-max_value, min(max_value, value))
        
        # 轉換到0-1範圍（0.5為中性）
        score = (normalized / max_value + 1) / 2
        
        return score
    
    def _generate_recommendation(self, momentum_score: float) -> tuple:
        """
        根據動量得分生成建議
        
        返回:
            (recommendation, confidence)
        """
        if momentum_score >= self.STRONG_MOMENTUM_THRESHOLD:
            return (
                "強動量 - 不建議逆勢做空",
                "High"
            )
        elif momentum_score >= self.MODERATE_MOMENTUM_THRESHOLD:
            return (
                "中等動量 - 謹慎做空",
                "Medium"
            )
        else:
            return (
                "弱動量 - 可以考慮做空",
                "Medium"
            )
    
    def _create_neutral_result(self, ticker: str, calculation_date: str) -> MomentumResult:
        """創建中性結果（當數據不足時）"""
        return MomentumResult(
            ticker=ticker,
            momentum_score=0.5,
            price_momentum=0.5,
            volume_momentum=0.5,
            relative_strength=0.5,
            recommendation="數據不足 - 無法判斷動量",
            confidence="Low",
            calculation_date=calculation_date
        )
    
    def _fetch_historical_data(self, ticker: str, days: int) -> Optional[pd.DataFrame]:
        """從data_fetcher獲取歷史數據"""
        try:
            if self.data_fetcher is None:
                return None
            
            # 調用data_fetcher的方法
            # 注意：這需要data_fetcher有get_historical_data方法
            return self.data_fetcher.get_historical_data(ticker, days=days)
            
        except Exception as e:
            logger.warning(f"! 獲取歷史數據失敗: {e}")
            return None


# 使用示例
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # 創建測試數據
    import numpy as np
    dates = pd.date_range('2024-01-01', periods=90, freq='D')
    
    # 模擬強動量股票（持續上漲）
    prices_strong = 100 * np.exp(np.linspace(0, 0.3, 90))  # 30%漲幅
    volumes_strong = np.random.randint(1000000, 2000000, 90)
    
    data_strong = pd.DataFrame({
        'Close': prices_strong,
        'Volume': volumes_strong
    }, index=dates)
    
    # 測試
    momentum_filter = MomentumFilter()
    result = momentum_filter.calculate(
        ticker='NVDA',
        historical_data=data_strong
    )
    
    print("\n" + "=" * 70)
    print("動量過濾器測試結果")
    print("=" * 70)
    print(f"股票: {result.ticker}")
    print(f"動量得分: {result.momentum_score:.4f}")
    print(f"建議: {result.recommendation}")
    print(f"信心度: {result.confidence}")
    print("=" * 70)
