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
    risk_reward_ratio: Optional[float] = None  # 風險回報比 (R/R Ratio)
    max_profit: Optional[float] = None         # 最大利潤
    max_loss: Optional[float] = None           # 最大損失
    
    def to_dict(self) -> Dict:
        return {
            'strategy_name': self.strategy_name,
            'direction': self.direction,
            'confidence': self.confidence,
            'reasoning': self.reasoning,
            'key_levels': self.key_levels,
            'suggested_strike': self.suggested_strike,
            'suggested_expiry': self.suggested_expiry,
            'risk_reward_ratio': self.risk_reward_ratio,
            'max_profit': self.max_profit,
            'max_loss': self.max_loss
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

    def _calculate_risk_reward_ratio(
        self,
        strategy_name: str,
        current_price: float,
        strike: float,
        premium: float,
        target_price: Optional[float] = None,
        stop_loss: Optional[float] = None
    ) -> Dict:
        """
        計算風險回報比
        
        參數:
            strategy_name: 策略名稱
            current_price: 當前股價
            strike: 行使價
            premium: 期權金（估算值，使用 ATM 期權金的 2-3%）
            target_price: 目標價格
            stop_loss: 止損價格
        
        返回:
            dict: {
                'risk_reward_ratio': float,  # R/R 比率
                'max_profit': float,         # 最大利潤
                'max_loss': float,           # 最大損失
                'break_even': float          # 盈虧平衡點
            }
        """
        # 估算期權金（如果未提供）
        # 使用簡化估算：ATM 期權金約為股價的 2-3%
        if premium is None or premium <= 0:
            premium = current_price * 0.025  # 2.5% 作為默認值
        
        # 根據策略類型計算 R/R
        if 'Long Call' in strategy_name:
            # Long Call: 最大損失 = 期權金，潛在利潤 = 目標價 - 行使價 - 期權金
            max_loss = premium
            if target_price and target_price > strike:
                potential_profit = max(0, target_price - strike - premium)
            else:
                # 如果沒有目標價或目標價不高於行使價，假設上漲 10%
                potential_profit = max(0, current_price * 1.10 - strike - premium)
            break_even = strike + premium
            
        elif 'Long Put' in strategy_name:
            # Long Put: 最大損失 = 期權金，潛在利潤 = 行使價 - 目標價 - 期權金
            max_loss = premium
            if target_price and target_price < strike:
                potential_profit = max(0, strike - target_price - premium)
            else:
                # 如果沒有目標價或目標價不低於行使價，假設下跌 10%
                potential_profit = max(0, strike - current_price * 0.90 - premium)
            break_even = strike - premium
            
        elif 'Short Put' in strategy_name:
            # Short Put: 最大利潤 = 期權金，最大損失 = 行使價 - 期權金
            max_loss = strike - premium
            potential_profit = premium
            break_even = strike - premium
            
        elif 'Short Call' in strategy_name:
            # Short Call: 最大利潤 = 期權金，最大損失 = 無限（用 inf 表示）
            max_loss = float('inf')
            potential_profit = premium
            break_even = strike + premium
            
        elif 'Spread' in strategy_name or 'Iron Condor' in strategy_name:
            # 價差策略：使用簡化計算
            # 假設價差寬度為 5% 的股價
            spread_width = current_price * 0.05
            if 'Bull' in strategy_name or 'Bear' in strategy_name:
                # 垂直價差
                max_loss = spread_width - premium
                potential_profit = premium
            else:
                # Iron Condor 或其他複雜策略
                max_loss = spread_width * 0.5
                potential_profit = premium
            break_even = current_price
            
        elif 'Straddle' in strategy_name:
            # Straddle 策略
            if 'Long' in strategy_name:
                # Long Straddle: 最大損失 = 2 * 期權金
                max_loss = 2 * premium
                # 潛在利潤：假設波動 15%
                potential_profit = current_price * 0.15 - 2 * premium
            else:
                # Short Straddle: 最大利潤 = 2 * 期權金，最大損失 = 無限
                max_loss = float('inf')
                potential_profit = 2 * premium
            break_even = current_price
            
        else:
            # 其他策略：使用目標價和止損價
            if target_price and stop_loss:
                max_loss = abs(stop_loss - current_price)
                potential_profit = abs(target_price - current_price)
            else:
                # 默認值
                max_loss = current_price * 0.05  # 5% 損失
                potential_profit = current_price * 0.10  # 10% 利潤
            break_even = current_price
        
        # 計算 R/R 比率
        if max_loss > 0 and max_loss != float('inf'):
            risk_reward_ratio = potential_profit / max_loss
        else:
            risk_reward_ratio = None
        
        return {
            'risk_reward_ratio': risk_reward_ratio,
            'max_profit': potential_profit,
            'max_loss': max_loss,
            'break_even': break_even
        }

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
        logger.info(f"* 開始策略推薦分析: Price=${current_price}, IV Rank={iv_rank:.1f}, IV/HV={iv_hv_ratio:.2f}, Trend={trend}")
        
        # 1. 判斷波動率狀態
        is_high_iv = iv_rank > 50 or iv_hv_ratio > 1.2
        is_low_iv = iv_rank < 30 or iv_hv_ratio < 0.8
        is_neutral_iv = not is_high_iv and not is_low_iv  # IV 在中性區間
        
        logger.info(f"  IV狀態: High={is_high_iv}, Low={is_low_iv}, Neutral={is_neutral_iv}")
        
        # 2. 判斷價格位置（處理無效的支持/阻力位）
        has_valid_levels = support_level > 0 and resistance_level > 0 and resistance_level > support_level
        
        if has_valid_levels:
            dist_to_support = (current_price - support_level) / current_price
            dist_to_resistance = (resistance_level - current_price) / current_price
            is_near_support = dist_to_support < 0.03  # 3% 以內
            is_near_resistance = dist_to_resistance < 0.03  # 3% 以內
        else:
            dist_to_support = 1.0
            dist_to_resistance = 1.0
            is_near_support = False
            is_near_resistance = False
            logger.warning(f"  ! 支持/阻力位無效: support={support_level}, resistance={resistance_level}")
        
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
                    strategy_name="Iron Condor (鐵鷹)",
                    direction="Neutral",
                    confidence="High",
                    reasoning=reasoning + ["IV 高，適合區間收租"],
                    key_levels={'upper': resistance_level, 'lower': support_level},
                    suggested_strike=self._round_to_strike(current_price)
                )
                recommendations.append(rec)
                
                # Short Straddle (高風險)
                rec_straddle = StrategyRecommendation(
                    strategy_name="Short Straddle (賣出跨式)",
                    direction="Neutral",
                    confidence="Medium",
                    reasoning=reasoning + ["IV 高，收取高額期權金", "⚠️ 風險無限"],
                    key_levels={'pivot': current_price},
                    suggested_strike=self._round_to_strike(current_price)
                )
                recommendations.append(rec_straddle)
                
            elif is_low_iv:
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
                
                # Long Straddle (預期波動)
                rec_straddle = StrategyRecommendation(
                    strategy_name="Long Straddle (買入跨式)",
                    direction="Neutral",
                    confidence="Low",
                    reasoning=reasoning + ["IV 低，預期波動率上升", "需要大幅波動才能獲利"],
                    key_levels={'pivot': current_price},
                    suggested_strike=self._round_to_strike(current_price)
                )
                recommendations.append(rec_straddle)
                
            else:
                # IV 中性 - 提供觀望建議
                rec = StrategyRecommendation(
                    strategy_name="觀望 / 等待機會",
                    direction="Neutral",
                    confidence="Low",
                    reasoning=reasoning + [f"IV Rank {iv_rank:.0f}% 處於中性區間", "建議等待更明確的方向或波動率信號"],
                    key_levels={'upper': resistance_level, 'lower': support_level},
                    suggested_strike=self._round_to_strike(current_price)
                )
                recommendations.append(rec)
        
        # D. 如果沒有任何推薦，提供基於 IV 的默認建議
        if not recommendations:
            logger.info("  未匹配任何策略條件，生成基於 IV 的默認建議")
            if is_low_iv:
                rec = StrategyRecommendation(
                    strategy_name="Long Call/Put (買入期權)",
                    direction="Neutral",
                    confidence="Low",
                    reasoning=[f"IV Rank {iv_rank:.0f}% 偏低", "適合買入期權", "需配合方向判斷選擇 Call 或 Put"],
                    key_levels={'current': current_price},
                    suggested_strike=self._round_to_strike(current_price)
                )
                recommendations.append(rec)
            elif is_high_iv:
                rec = StrategyRecommendation(
                    strategy_name="Short Put (賣出認沽)",
                    direction="Bullish",
                    confidence="Low",
                    reasoning=[f"IV Rank {iv_rank:.0f}% 偏高", "適合賣出期權收取期權金", "需確認支持位"],
                    key_levels={'current': current_price},
                    suggested_strike=self._round_to_strike(current_price * 0.95)
                )
                recommendations.append(rec)
            else:
                rec = StrategyRecommendation(
                    strategy_name="觀望 / 等待機會",
                    direction="Neutral",
                    confidence="Low",
                    reasoning=["趨勢不明確", f"IV Rank {iv_rank:.0f}% 處於中性區間", "建議等待更明確的信號"],
                    key_levels={'current': current_price},
                    suggested_strike=None
                )
                recommendations.append(rec)
                
        # 排序推薦 (按信心度)
        confidence_map = {'High': 3, 'Medium': 2, 'Low': 1}
        
        # 為每個推薦計算 R/R 比率並調整信心度
        for rec in recommendations:
            # 估算期權金（使用股價的 2.5%）
            premium = current_price * 0.025
            
            # 獲取目標價和止損價
            target_price = rec.key_levels.get('target', None)
            stop_loss = rec.key_levels.get('stop_loss', None)
            
            # 計算 R/R 比率
            if rec.suggested_strike:
                rr_result = self._calculate_risk_reward_ratio(
                    strategy_name=rec.strategy_name,
                    current_price=current_price,
                    strike=rec.suggested_strike,
                    premium=premium,
                    target_price=target_price,
                    stop_loss=stop_loss
                )
                
                # 更新推薦結果
                rec.risk_reward_ratio = rr_result['risk_reward_ratio']
                rec.max_profit = rr_result['max_profit']
                rec.max_loss = rr_result['max_loss']
                
                # 根據 R/R 比率調整信心度
                if rec.risk_reward_ratio:
                    if rec.risk_reward_ratio > 2.0 and rec.confidence == 'Medium':
                        rec.confidence = 'High'
                        rec.reasoning.append(f"風險回報比優秀 ({rec.risk_reward_ratio:.2f}:1)")
                        logger.info(f"  提升信心度: {rec.strategy_name} R/R={rec.risk_reward_ratio:.2f}")
                    elif rec.risk_reward_ratio < 1.0 and rec.confidence == 'High':
                        rec.confidence = 'Medium'
                        rec.reasoning.append(f"風險回報比偏低 ({rec.risk_reward_ratio:.2f}:1)")
                        logger.info(f"  降低信心度: {rec.strategy_name} R/R={rec.risk_reward_ratio:.2f}")
                    elif rec.risk_reward_ratio >= 1.0:
                        rec.reasoning.append(f"風險回報比 {rec.risk_reward_ratio:.2f}:1")
        
        recommendations.sort(key=lambda x: confidence_map.get(x.confidence, 0), reverse=True)
        
        logger.info(f"* 策略推薦完成: 生成 {len(recommendations)} 個建議")
        
        return recommendations