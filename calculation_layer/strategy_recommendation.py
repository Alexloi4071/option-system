# calculation_layer/strategy_recommendation.py
"""
策略推薦模塊
基於《期權制勝》核心思想，根據市場狀態推薦最佳期權策略
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

@dataclass
class StrategyRecommendation:
    """策略推薦結果"""
    strategy_name: str
    direction: str  # 'Bullish', 'Bearish', 'Neutral'
    confidence: str # 'High', 'Medium', 'Low'
    reasoning: List[str]
    key_levels: Dict[str, float]
    suggested_strike: Optional[float] = None
    suggested_expiry: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            'strategy_name': self.strategy_name,
            'direction': self.direction,
            'confidence': self.confidence,
            'reasoning': self.reasoning,
            'key_levels': self.key_levels,
            'suggested_strike': self.suggested_strike,
            'suggested_expiry': self.suggested_expiry
        }

class StrategyRecommender:
    """
    策略推薦引擎
    
    綜合分析:
    1. 趨勢 (Trend)
    2. 波動率 (IV Rank / IV vs HV)
    3. 支持/阻力位 (Support/Resistance)
    4. 估值 (Valuation)
    """
    
    def __init__(self):
        pass
    
    def _round_to_strike(self, price: float) -> float:
        """
        將價格四捨五入到最接近的行使價
        規則:
        - 價格 < 25: 0.5
        - 25 <= 價格 < 200: 1.0 (或 2.5) -> 簡化為 1.0
        - 價格 >= 200: 5.0
        """
        if price < 25:
            interval = 0.5
        elif price < 200:
            interval = 1.0
        else:
            interval = 5.0
            
        return round(price / interval) * interval

    def recommend(self,
                 current_price: float,
                 iv_rank: float, # 0-100
                 iv_percentile: float, # 0-100
                 iv_hv_ratio: float,
                 support_level: float,
                 resistance_level: float,
                 trend: str, # 'Up', 'Down', 'Sideways'
                 valuation: str, # 'Undervalued', 'Overvalued', 'Fair'
                 days_to_expiry: int) -> List[StrategyRecommendation]:
        
        recommendations = []
        logger.info(f"* 開始策略推薦分析: Price=${current_price}, IV Rank={iv_rank}, Trend={trend}")
        
        # 1. 判斷波動率狀態
        is_high_iv = iv_rank > 50 or iv_hv_ratio > 1.2
        is_low_iv = iv_rank < 30 or iv_hv_ratio < 0.8
        
        # 2. 判斷價格位置
        dist_to_support = (current_price - support_level) / current_price
        dist_to_resistance = (resistance_level - current_price) / current_price
        
        is_near_support = dist_to_support < 0.03 # 3% 以內
        is_near_resistance = dist_to_resistance < 0.03 # 3% 以內
        
        # ========== 策略邏輯 ==========
        
        # A. 看漲策略 (Bullish)
        if trend == 'Up' or (trend == 'Sideways' and is_near_support) or valuation == 'Undervalued':
            reasoning = []
            if trend == 'Up': reasoning.append("趨勢向上")
            if is_near_support: reasoning.append(f"接近支持位 ${support_level:.2f}")
            if valuation == 'Undervalued': reasoning.append("估值偏低")
            
            if is_low_iv:
                # 低波動率 -> 買入期權 (Long Call)
                rec = StrategyRecommendation(
                    strategy_name="Long Call (買入認購)",
                    direction="Bullish",
                    confidence="High" if len(reasoning) >= 2 else "Medium",
                    reasoning=reasoning + ["IV 偏低，適合買入期權"],
                    key_levels={'stop_loss': support_level * 0.98, 'target': resistance_level},
                    suggested_strike=self._round_to_strike(resistance_level if days_to_expiry > 30 else current_price * 1.02)
                )
                recommendations.append(rec)
                
                # Bull Call Spread
                rec_spread = StrategyRecommendation(
                    strategy_name="Bull Call Spread (牛市價差)",
                    direction="Bullish",
                    confidence="Medium",
                    reasoning=reasoning + ["降低時間值損耗"],
                    key_levels={'stop_loss': support_level, 'target': resistance_level},
                    suggested_strike=self._round_to_strike(current_price)
                )
                recommendations.append(rec_spread)
                
            elif is_high_iv:
                # 高波動率 -> 賣出期權 (Short Put)
                rec = StrategyRecommendation(
                    strategy_name="Short Put (賣出認沽)",
                    direction="Bullish",
                    confidence="High" if is_near_support else "Medium",
                    reasoning=reasoning + ["IV 偏高，適合賣出期權收取期權金"],
                    key_levels={'break_even': support_level},
                    suggested_strike=self._round_to_strike(support_level)
                )
                recommendations.append(rec)
                
                # Bull Put Spread
                rec_spread = StrategyRecommendation(
                    strategy_name="Bull Put Spread (牛市認沽價差)",
                    direction="Bullish",
                    confidence="Medium",
                    reasoning=reasoning + ["風險有限的收租策略"],
                    key_levels={'break_even': support_level},
                    suggested_strike=self._round_to_strike(support_level)
                )
                recommendations.append(rec_spread)

        # B. 看跌策略 (Bearish)
        if trend == 'Down' or (trend == 'Sideways' and is_near_resistance) or valuation == 'Overvalued':
            reasoning = []
            if trend == 'Down': reasoning.append("趨勢向下")
            if is_near_resistance: reasoning.append(f"接近阻力位 ${resistance_level:.2f}")
            if valuation == 'Overvalued': reasoning.append("估值偏高")
            
            if is_low_iv:
                # 低波動率 -> 買入期權 (Long Put)
                rec = StrategyRecommendation(
                    strategy_name="Long Put (買入認沽)",
                    direction="Bearish",
                    confidence="High" if len(reasoning) >= 2 else "Medium",
                    reasoning=reasoning + ["IV 偏低，適合買入期權"],
                    key_levels={'stop_loss': resistance_level * 1.02, 'target': support_level},
                    suggested_strike=self._round_to_strike(support_level if days_to_expiry > 30 else current_price * 0.98)
                )
                recommendations.append(rec)
                
            elif is_high_iv:
                # 高波動率 -> 賣出期權 (Short Call)
                rec = StrategyRecommendation(
                    strategy_name="Short Call (賣出認購)",
                    direction="Bearish",
                    confidence="Medium", # Short Call 風險無限，信心度調低
                    reasoning=reasoning + ["IV 偏高，適合賣出期權"],
                    key_levels={'break_even': resistance_level},
                    suggested_strike=self._round_to_strike(resistance_level)
                )
                recommendations.append(rec)
                
                # Bear Call Spread
                rec_spread = StrategyRecommendation(
                    strategy_name="Bear Call Spread (熊市認購價差)",
                    direction="Bearish",
                    confidence="High" if is_near_resistance else "Medium",
                    reasoning=reasoning + ["風險有限的看跌收租策略"],
                    key_levels={'break_even': resistance_level},
                    suggested_strike=self._round_to_strike(resistance_level)
                )
                recommendations.append(rec_spread)

        # C. 盤整策略 (Neutral)
        if trend == 'Sideways' and not is_near_support and not is_near_resistance:
            reasoning = ["股價處於區間震盪", "未突破關鍵位"]
            
            if is_high_iv:
                # Iron Condor
                rec = StrategyRecommendation(
                    strategy_name="Iron Condor (鐵以此)",
                    direction="Neutral",
                    confidence="High",
                    reasoning=reasoning + ["IV 高，適合區間收租"],
                    key_levels={'upper': resistance_level, 'lower': support_level},
                    suggested_strike=self._round_to_strike(current_price)
                )
                recommendations.append(rec)
            else:
                # Calendar Spread (Long Vega)
                rec = StrategyRecommendation(
                    strategy_name="Calendar Spread (日曆價差)",
                    direction="Neutral",
                    confidence="Medium",
                    reasoning=reasoning + ["IV 低，預期波動率回歸"],
                    key_levels={'pivot': current_price},
                    suggested_strike=self._round_to_strike(current_price)
                )
                recommendations.append(rec)
                
        # 排序推薦 (按信心度)
        confidence_map = {'High': 3, 'Medium': 2, 'Low': 1}
        recommendations.sort(key=lambda x: confidence_map.get(x.confidence, 0), reverse=True)
        
        return recommendations