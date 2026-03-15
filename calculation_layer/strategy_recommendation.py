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
                 iv_rank: Optional[float],
                 iv_percentile: Optional[float],
                 iv_hv_ratio: float,
                 support_level: float,
                 resistance_level: float,
                 trend: str,
                 valuation: str,
                 days_to_expiry: int) -> List[StrategyRecommendation]:
        recommendations = []
        iv_rank_text = f"{iv_rank:.1f}%" if iv_rank is not None else "N/A"
        iv_percentile_text = f"{iv_percentile:.1f}%" if iv_percentile is not None else "N/A"
        logger.info(
            f"* Strategy recommendation analysis: Price=${current_price}, IV Rank={iv_rank_text}, "
            f"IV Percentile={iv_percentile_text}, IV/HV={iv_hv_ratio:.2f}, Trend={trend}"
        )

        iv_rank_high = iv_rank is not None and iv_rank > 50
        iv_rank_low = iv_rank is not None and iv_rank < 30
        iv_percentile_high = iv_percentile is not None and iv_percentile > 70
        iv_percentile_low = iv_percentile is not None and iv_percentile < 30
        is_high_iv = iv_rank_high or iv_percentile_high or iv_hv_ratio > 1.2
        is_low_iv = iv_rank_low or iv_percentile_low or iv_hv_ratio < 0.8
        is_neutral_iv = not is_high_iv and not is_low_iv
        missing_iv_rank = iv_rank is None and iv_percentile is None

        logger.info(f"  IV regime: High={is_high_iv}, Low={is_low_iv}, Neutral={is_neutral_iv}")
        if missing_iv_rank:
            logger.info("  IV Rank/Percentile unavailable, using IV/HV ratio as fallback")

        def iv_reason(level: str) -> str:
            if level == 'high':
                if iv_rank_high:
                    return f"IV Rank {iv_rank:.0f}% is elevated"
                if iv_percentile_high:
                    return f"IV Percentile {iv_percentile:.0f}% is elevated"
                return f"IV/HV ratio {iv_hv_ratio:.2f} is elevated"

            if level == 'low':
                if iv_rank_low:
                    return f"IV Rank {iv_rank:.0f}% is depressed"
                if iv_percentile_low:
                    return f"IV Percentile {iv_percentile:.0f}% is depressed"
                return f"IV/HV ratio {iv_hv_ratio:.2f} is depressed"

            if iv_rank is not None:
                return f"IV Rank {iv_rank:.0f}% is neutral"
            if iv_percentile is not None:
                return f"IV Percentile {iv_percentile:.0f}% is neutral"
            return f"IV Rank missing; IV/HV ratio {iv_hv_ratio:.2f} is near fair value"

        fallback_vol_reasons = []
        if missing_iv_rank:
            fallback_vol_reasons.append("IV Rank/Percentile unavailable; decision falls back to IV/HV ratio")

        has_valid_levels = support_level > 0 and resistance_level > 0 and resistance_level > support_level
        if has_valid_levels:
            is_near_support = (current_price - support_level) / current_price < 0.03
            is_near_resistance = (resistance_level - current_price) / current_price < 0.03
        else:
            is_near_support = False
            is_near_resistance = False
            logger.warning(f"  ! Invalid support/resistance levels: support={support_level}, resistance={resistance_level}")

        bullish_stop = support_level * 0.98 if support_level > 0 else current_price * 0.95
        bullish_target = resistance_level if resistance_level > current_price else current_price * 1.08
        bearish_stop = resistance_level * 1.02 if resistance_level > 0 else current_price * 1.05
        bearish_target = support_level if 0 < support_level < current_price else current_price * 0.92

        if trend == 'Up' or (trend == 'Sideways' and is_near_support) or valuation == 'Undervalued':
            reasoning = []
            if trend == 'Up':
                reasoning.append('Trend is up')
            if is_near_support:
                reasoning.append(f'Price is near support ${support_level:.2f}')
            if valuation == 'Undervalued':
                reasoning.append('Valuation is attractive')

            if is_low_iv:
                recommendations.append(StrategyRecommendation(
                    strategy_name='Long Call',
                    direction='Bullish',
                    confidence='High' if len(reasoning) >= 2 else 'Medium',
                    reasoning=reasoning + [iv_reason('low'), 'Low IV favors long premium exposure'] + fallback_vol_reasons,
                    key_levels={'stop_loss': bullish_stop, 'target': bullish_target},
                    suggested_strike=self._round_to_strike(current_price if days_to_expiry <= 30 else bullish_target)
                ))
                recommendations.append(StrategyRecommendation(
                    strategy_name='Bull Call Spread',
                    direction='Bullish',
                    confidence='Medium',
                    reasoning=reasoning + [iv_reason('low'), 'Use a spread to control cost and theta'] + fallback_vol_reasons,
                    key_levels={'stop_loss': support_level if support_level > 0 else bullish_stop, 'target': bullish_target},
                    suggested_strike=self._round_to_strike(current_price)
                ))
            elif is_high_iv:
                recommendations.append(StrategyRecommendation(
                    strategy_name='Bull Put Spread',
                    direction='Bullish',
                    confidence='High' if is_near_support else 'Medium',
                    reasoning=reasoning + [iv_reason('high'), 'Prefer defined-risk premium selling in high IV'] + fallback_vol_reasons,
                    key_levels={'break_even': support_level if support_level > 0 else current_price * 0.97, 'target': bullish_target},
                    suggested_strike=self._round_to_strike(support_level if support_level > 0 else current_price * 0.97)
                ))

        if trend == 'Down' or (trend == 'Sideways' and is_near_resistance) or valuation == 'Overvalued':
            reasoning = []
            if trend == 'Down':
                reasoning.append('Trend is down')
            if is_near_resistance:
                reasoning.append(f'Price is near resistance ${resistance_level:.2f}')
            if valuation == 'Overvalued':
                reasoning.append('Valuation is stretched')

            if is_low_iv:
                recommendations.append(StrategyRecommendation(
                    strategy_name='Long Put',
                    direction='Bearish',
                    confidence='High' if len(reasoning) >= 2 else 'Medium',
                    reasoning=reasoning + [iv_reason('low'), 'Low IV favors buying downside protection'] + fallback_vol_reasons,
                    key_levels={'stop_loss': bearish_stop, 'target': bearish_target},
                    suggested_strike=self._round_to_strike(current_price if days_to_expiry <= 30 else bearish_target)
                ))
            elif is_high_iv:
                recommendations.append(StrategyRecommendation(
                    strategy_name='Bear Call Spread',
                    direction='Bearish',
                    confidence='High' if is_near_resistance else 'Medium',
                    reasoning=reasoning + [iv_reason('high'), 'Prefer defined-risk bearish premium selling in high IV'] + fallback_vol_reasons,
                    key_levels={'break_even': resistance_level if resistance_level > 0 else current_price * 1.03, 'target': bearish_target},
                    suggested_strike=self._round_to_strike(resistance_level if resistance_level > 0 else current_price * 1.03)
                ))

        if trend == 'Sideways' and not is_near_support and not is_near_resistance:
            reasoning = ['Price is range-bound', 'No clear breakout or breakdown signal']

            if is_high_iv:
                recommendations.append(StrategyRecommendation(
                    strategy_name='Iron Condor',
                    direction='Neutral',
                    confidence='High',
                    reasoning=reasoning + [iv_reason('high'), 'Range plus high IV favors premium-selling range structures'] + fallback_vol_reasons,
                    key_levels={'upper': resistance_level if resistance_level > 0 else current_price * 1.05, 'lower': support_level if support_level > 0 else current_price * 0.95},
                    suggested_strike=self._round_to_strike(current_price)
                ))
                recommendations.append(StrategyRecommendation(
                    strategy_name='Butterfly Spread',
                    direction='Neutral',
                    confidence='Medium',
                    reasoning=reasoning + [iv_reason('high'), 'Butterfly keeps risk defined while targeting a range'] + fallback_vol_reasons,
                    key_levels={'pivot': current_price},
                    suggested_strike=self._round_to_strike(current_price)
                ))
            elif is_low_iv:
                recommendations.append(StrategyRecommendation(
                    strategy_name='Calendar Spread',
                    direction='Neutral',
                    confidence='Medium',
                    reasoning=reasoning + [iv_reason('low'), 'Calendar spread benefits if IV normalizes higher'] + fallback_vol_reasons,
                    key_levels={'pivot': current_price},
                    suggested_strike=self._round_to_strike(current_price)
                ))
                recommendations.append(StrategyRecommendation(
                    strategy_name='Long Straddle',
                    direction='Neutral',
                    confidence='Low',
                    reasoning=reasoning + [iv_reason('low'), 'Only valid if a large move is expected soon'] + fallback_vol_reasons,
                    key_levels={'pivot': current_price},
                    suggested_strike=self._round_to_strike(current_price)
                ))
            else:
                recommendations.append(StrategyRecommendation(
                    strategy_name='Observe / Wait',
                    direction='Neutral',
                    confidence='Low',
                    reasoning=reasoning + [iv_reason('neutral'), 'No clear edge in direction or volatility right now'] + fallback_vol_reasons,
                    key_levels={'upper': resistance_level if resistance_level > 0 else current_price * 1.03, 'lower': support_level if support_level > 0 else current_price * 0.97},
                    suggested_strike=None
                ))

        if not recommendations:
            logger.info('  No strong setup matched; generating conservative fallback recommendation')
            if is_low_iv:
                recommendations.append(StrategyRecommendation(
                    strategy_name='Long Call/Put',
                    direction='Neutral',
                    confidence='Low',
                    reasoning=[iv_reason('low'), 'Low IV favors long premium strategies', 'Choose Call or Put only after direction is clearer'] + fallback_vol_reasons,
                    key_levels={'current': current_price},
                    suggested_strike=self._round_to_strike(current_price)
                ))
            else:
                recommendations.append(StrategyRecommendation(
                    strategy_name='Observe / Wait',
                    direction='Neutral',
                    confidence='Low',
                    reasoning=[iv_reason('neutral' if is_neutral_iv else 'high'), 'Conditions are not strong enough for a high-quality trade setup'] + fallback_vol_reasons,
                    key_levels={'current': current_price},
                    suggested_strike=None
                ))

        confidence_map = {'High': 3, 'Medium': 2, 'Low': 1}

        for rec in recommendations:
            premium = current_price * 0.025
            target_price = rec.key_levels.get('target')
            stop_loss = rec.key_levels.get('stop_loss')

            if rec.suggested_strike:
                rr_result = self._calculate_risk_reward_ratio(
                    strategy_name=rec.strategy_name,
                    current_price=current_price,
                    strike=rec.suggested_strike,
                    premium=premium,
                    target_price=target_price,
                    stop_loss=stop_loss
                )

                rec.risk_reward_ratio = rr_result['risk_reward_ratio']
                rec.max_profit = rr_result['max_profit']
                rec.max_loss = rr_result['max_loss']

                if rec.risk_reward_ratio:
                    if rec.risk_reward_ratio > 2.0 and rec.confidence == 'Medium':
                        rec.confidence = 'High'
                        rec.reasoning.append(f'Risk/reward improved to {rec.risk_reward_ratio:.2f}:1')
                        logger.info(f"  Confidence upgraded: {rec.strategy_name} R/R={rec.risk_reward_ratio:.2f}")
                    elif rec.risk_reward_ratio < 1.0 and rec.confidence == 'High':
                        rec.confidence = 'Medium'
                        rec.reasoning.append(f'Risk/reward weakened to {rec.risk_reward_ratio:.2f}:1')
                        logger.info(f"  Confidence downgraded: {rec.strategy_name} R/R={rec.risk_reward_ratio:.2f}")
                    elif rec.risk_reward_ratio >= 1.0:
                        rec.reasoning.append(f'Risk/reward ratio {rec.risk_reward_ratio:.2f}:1')

        recommendations.sort(key=lambda x: confidence_map.get(x.confidence, 0), reverse=True)
        logger.info(f"* Strategy recommendation complete: {len(recommendations)} recommendations")
        return recommendations
