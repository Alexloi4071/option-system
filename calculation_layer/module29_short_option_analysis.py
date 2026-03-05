"""
Module 28: Short 期權策略分析
專為「賣方收租」策略設計，分析 Short Call/Put 的勝率、回報率和風險

功能：
1. 獲勝機率 (Probability of Profit)
2. 權利金回報率 (ROC)
3. 盈虧平衡點分析
4. Theta 收益分析
5. IV Rank 評估
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import math

logger = logging.getLogger(__name__)

class ShortOptionAnalyzer:
    """Short 期權策略分析器"""
    
    def __init__(self):
        self.analysis_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def analyze_short_call(
        self,
        stock_price: float,
        strike_price: float,
        premium: float,
        days_to_expiration: int,
        delta: float,
        theta: float,
        iv: float,
        margin_requirement: float = 0.0 # 預估保證金
    ) -> Dict[str, Any]:
        """分析 Short Call (看跌/盤整)"""
        return self._analyze_short(
            stock_price, strike_price, premium, days_to_expiration, 
            delta, theta, iv, 'call', margin_requirement
        )

    def analyze_short_put(
        self,
        stock_price: float,
        strike_price: float,
        premium: float,
        days_to_expiration: int,
        delta: float,
        theta: float,
        iv: float,
        margin_requirement: float = 0.0
    ) -> Dict[str, Any]:
        """分析 Short Put (看漲/盤整)"""
        return self._analyze_short(
            stock_price, strike_price, premium, days_to_expiration, 
            delta, theta, iv, 'put', margin_requirement
        )

    def _analyze_short(
        self,
        stock_price: float,
        strike_price: float,
        premium: float,
        days_to_expiration: int,
        delta: float,
        theta: float,
        iv: float,
        option_type: str,
        margin_requirement: float
    ) -> Dict[str, Any]:
        
        try:
            # 1. 基礎計算
            contract_size = 100
            max_profit = premium * contract_size
            
            # 簡單保證金估算 (若未提供): 20% 股價 - OTM + Premium (Reg T Standard)
            if margin_requirement <= 0:
                otm_amount = max(0, strike_price - stock_price) if option_type == 'call' else max(0, stock_price - strike_price)
                margin_requirement = ((0.2 * stock_price) - otm_amount + premium) * contract_size
                # 最低要求
                margin_requirement = max(margin_requirement, 0.1 * stock_price * contract_size)

            # 回報率 (Return on Capital)
            roc = (max_profit / margin_requirement) * 100 if margin_requirement > 0 else 0
            
            # 年化回報率
            annualized_roc = roc * (365 / days_to_expiration) if days_to_expiration > 0 else 0

            # 2. 盈虧平衡點
            if option_type == 'call':
                breakeven = strike_price + premium
                safety_cushion_pct = (breakeven - stock_price) / stock_price * 100
            else:
                breakeven = strike_price - premium
                safety_cushion_pct = (stock_price - breakeven) / stock_price * 100

            # 3. 勝率估算 (基於 Delta)
            # Short 的勝率大約是 1 - abs(Delta)
            pop = (1 - abs(delta)) * 100

            # 4. Theta 收益 (每日)
            daily_theta_income = abs(theta) * contract_size

            # 5. 評分
            score_result = self._calculate_score(pop, annualized_roc, iv, safety_cushion_pct)

            return {
                'strategy': f"Short {option_type.capitalize()}",
                'status': 'success',
                'input': { 'price': stock_price, 'strike': strike_price, 'iv': iv },
                'financials': {
                    'max_profit': round(max_profit, 2),
                    'margin_est': round(margin_requirement, 2),
                    'roc_pct': round(roc, 2),
                    'annualized_roc_pct': round(annualized_roc, 2)
                },
                'risk_profile': {
                    'breakeven': round(breakeven, 2),
                    'safety_cushion_pct': round(safety_cushion_pct, 2),
                    'pop_pct': round(pop, 1),
                    'delta': delta,
                    'theta_income_day': round(daily_theta_income, 2)
                },
                'score': score_result,
                'analysis_time': self.analysis_date
            }

        except Exception as e:
            logger.error(f"Short Option Analysis Error: {e}")
            return {'status': 'error', 'error': str(e)}

    def _calculate_score(self, pop, annualized_roc, iv, safety_buffer) -> Dict:
        score = 50
        factors = []

        # 1. 勝率 (PoP) - 權重高
        if pop > 85: 
            score += 20
            factors.append(('PoP', '+20', '極高勝率'))
        elif pop > 70:
            score += 15
            factors.append(('PoP', '+15', '高勝率'))
        elif pop < 60:
            score -= 10
            factors.append(('PoP', '-10', '勝率偏低'))

        # 2. 年化回報
        if annualized_roc > 50:
            score += 15
            factors.append(('ROC', '+15', '回報極高'))
        elif annualized_roc > 20:
            score += 10
            factors.append(('ROC', '+10', '回報不錯'))
        elif annualized_roc < 5:
            score -= 10
            factors.append(('ROC', '-10', '回報太低'))

        # 3. 安全邊際
        if safety_buffer > 10:
            score += 15
            factors.append(('Safety', '+15', '緩衝區大'))
        elif safety_buffer > 5:
            score += 5
            factors.append(('Safety', '+5', '緩衝區適中'))
        else:
            score -= 10
            factors.append(('Safety', '-10', '緩衝區太小'))

        # 4. IV (賣方喜歡高 IV)
        if iv > 50:
            score += 10
            factors.append(('IV', '+10', 'IV 高，權利金肥'))
        elif iv < 20:
            score -= 5
            factors.append(('IV', '-5', 'IV 低，肉少'))

        score = max(0, min(100, score))
        
        return {
            'total_score': score,
            'grade': 'A' if score >= 80 else ('B' if score >= 65 else 'C'),
            'factors': factors
        }
