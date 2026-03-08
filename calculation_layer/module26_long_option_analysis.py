"""
Module 26: Long 期權成本效益分析
專為「以小博大」策略設計，分析 Long Call/Put 的槓桿效益和風險

功能：
1. 槓桿倍數計算（股價變動 vs 期權收益）
2. 盈虧平衡點分析
3. 不同股價情境收益表
4. Theta 時間衰減分析
5. 成本效益評分
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import math

logger = logging.getLogger(__name__)


class LongOptionAnalyzer:
    """Long 期權成本效益分析器"""
    
    def __init__(self):
        self.analysis_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def analyze_long_call(
        self,
        stock_price: float,
        strike_price: float,
        premium: float,
        days_to_expiration: int,
        delta: float = 0.5,
        theta: Optional[float] = None,
        iv: Optional[float] = None,
        contract_size: int = 100
    ) -> Dict[str, Any]:
        """
        分析 Long Call 的成本效益
        
        Args:
            stock_price: 當前股價
            strike_price: 行使價
            premium: 權利金（每股）
            days_to_expiration: 到期天數
            delta: Delta 值
            theta: Theta 值（每日衰減，負數）
            iv: 隱含波動率 (%)
            contract_size: 合約乘數（默認100）
        
        Returns:
            Dict: 完整的 Long Call 分析結果
        """
        try:
            result = {
                'strategy': 'Long Call',
                'status': 'success',
                'input': {
                    'stock_price': stock_price,
                    'strike_price': strike_price,
                    'premium': premium,
                    'days_to_expiration': days_to_expiration,
                    'delta': delta,
                    'theta': theta,
                    'iv': iv,
                    'contract_size': contract_size
                }
            }
            
            # 1. 基本成本計算
            total_cost = premium * contract_size
            result['cost_analysis'] = {
                'premium_per_share': premium,
                'total_cost': total_cost,
                'max_loss': total_cost,  # Long 期權最大虧損 = 權利金
                'max_loss_pct': 100.0  # 最大虧損百分比
            }
            
            # 2. 盈虧平衡點
            breakeven = strike_price + premium
            breakeven_pct = ((breakeven - stock_price) / stock_price) * 100
            result['breakeven'] = {
                'price': breakeven,
                'distance_from_current': breakeven - stock_price,
                'distance_pct': breakeven_pct,
                'interpretation': self._interpret_breakeven(breakeven_pct, 'call')
            }
            
            # 3. 槓桿分析
            result['leverage'] = self._calculate_leverage(
                stock_price, strike_price, premium, delta, 'call'
            )
            
            # 4. 情境分析（股價變動 vs 期權收益）
            result['scenarios'] = self._calculate_scenarios(
                stock_price, strike_price, premium, contract_size, 'call'
            )
            
            # 5. Theta 時間衰減分析
            result['theta_analysis'] = self._analyze_theta(
                theta, premium, days_to_expiration, contract_size
            )
            
            # 6. IV 分析
            result['iv_analysis'] = self._analyze_iv_for_long(iv, 'call')
            
            # 7. 綜合評分
            result['score'] = self._calculate_long_score(result, 'call')
            
            # 8. 交易建議
            result['recommendation'] = self._generate_recommendation(result, 'call')
            
            result['analysis_time'] = self.analysis_date
            
            return result
            
        except Exception as e:
            logger.error(f"Long Call 分析錯誤: {e}")
            return {
                'strategy': 'Long Call',
                'status': 'error',
                'error': str(e)
            }
    
    def analyze_long_put(
        self,
        stock_price: float,
        strike_price: float,
        premium: float,
        days_to_expiration: int,
        delta: float = -0.5,
        theta: Optional[float] = None,
        iv: Optional[float] = None,
        contract_size: int = 100
    ) -> Dict[str, Any]:
        """
        分析 Long Put 的成本效益
        """
        try:
            result = {
                'strategy': 'Long Put',
                'status': 'success',
                'input': {
                    'stock_price': stock_price,
                    'strike_price': strike_price,
                    'premium': premium,
                    'days_to_expiration': days_to_expiration,
                    'delta': delta,
                    'theta': theta,
                    'iv': iv,
                    'contract_size': contract_size
                }
            }
            
            # 1. 基本成本計算
            total_cost = premium * contract_size
            result['cost_analysis'] = {
                'premium_per_share': premium,
                'total_cost': total_cost,
                'max_loss': total_cost,
                'max_loss_pct': 100.0
            }
            
            # 2. 盈虧平衡點
            breakeven = strike_price - premium
            breakeven_pct = ((stock_price - breakeven) / stock_price) * 100
            result['breakeven'] = {
                'price': breakeven,
                'distance_from_current': stock_price - breakeven,
                'distance_pct': breakeven_pct,
                'interpretation': self._interpret_breakeven(breakeven_pct, 'put')
            }
            
            # 3. 槓桿分析
            result['leverage'] = self._calculate_leverage(
                stock_price, strike_price, premium, abs(delta), 'put'
            )
            
            # 4. 情境分析
            result['scenarios'] = self._calculate_scenarios(
                stock_price, strike_price, premium, contract_size, 'put'
            )
            
            # 5. Theta 時間衰減分析
            result['theta_analysis'] = self._analyze_theta(
                theta, premium, days_to_expiration, contract_size
            )
            
            # 6. IV 分析
            result['iv_analysis'] = self._analyze_iv_for_long(iv, 'put')
            
            # 7. 綜合評分
            result['score'] = self._calculate_long_score(result, 'put')
            
            # 8. 交易建議
            result['recommendation'] = self._generate_recommendation(result, 'put')
            
            result['analysis_time'] = self.analysis_date
            
            return result
            
        except Exception as e:
            logger.error(f"Long Put 分析錯誤: {e}")
            return {
                'strategy': 'Long Put',
                'status': 'error',
                'error': str(e)
            }

    
    def _interpret_breakeven(self, breakeven_pct: float, option_type: str) -> str:
        """解讀盈虧平衡點"""
        if option_type == 'call':
            if breakeven_pct <= 3:
                return "✅ 容易達到 - 股價只需小幅上漲"
            elif breakeven_pct <= 7:
                return "🟡 中等難度 - 需要一定漲幅"
            elif breakeven_pct <= 15:
                return "🟠 較難達到 - 需要較大漲幅"
            else:
                return "🔴 困難 - 需要大幅上漲才能獲利"
        else:  # put
            if breakeven_pct <= 3:
                return "✅ 容易達到 - 股價只需小幅下跌"
            elif breakeven_pct <= 7:
                return "🟡 中等難度 - 需要一定跌幅"
            elif breakeven_pct <= 15:
                return "🟠 較難達到 - 需要較大跌幅"
            else:
                return "🔴 困難 - 需要大幅下跌才能獲利"
    
    def _calculate_leverage(
        self,
        stock_price: float,
        strike_price: float,
        premium: float,
        delta: float,
        option_type: str
    ) -> Dict[str, Any]:
        """計算槓桿效益"""
        
        # 有效槓桿 = Delta * (股價 / 權利金)
        if premium > 0:
            effective_leverage = delta * (stock_price / premium)
        else:
            effective_leverage = 0
        
        # 資金效率：用多少錢控制多少股票價值
        capital_efficiency = (stock_price * 100) / (premium * 100) if premium > 0 else 0
        
        # 槓桿倍數解讀
        if effective_leverage >= 10:
            leverage_rating = "🚀 超高槓桿"
            leverage_warning = "⚠️ 高風險高回報，注意倉位控制"
        elif effective_leverage >= 5:
            leverage_rating = "📈 高槓桿"
            leverage_warning = "適合以小博大策略"
        elif effective_leverage >= 3:
            leverage_rating = "📊 中等槓桿"
            leverage_warning = "風險收益較平衡"
        else:
            leverage_rating = "📉 低槓桿"
            leverage_warning = "槓桿效益不明顯"
        
        return {
            'effective_leverage': round(effective_leverage, 2),
            'capital_efficiency': round(capital_efficiency, 2),
            'delta': delta,
            'rating': leverage_rating,
            'warning': leverage_warning,
            'explanation': f"股價每變動1%，期權約變動{effective_leverage:.1f}%"
        }
    
    def _calculate_scenarios(
        self,
        stock_price: float,
        strike_price: float,
        premium: float,
        contract_size: int,
        option_type: str
    ) -> List[Dict[str, Any]]:
        """計算不同股價情境下的收益"""
        
        scenarios = []
        total_cost = premium * contract_size
        
        if option_type == 'call':
            # Call 情境：股價上漲
            price_changes = [-20, -10, -5, 0, 5, 10, 15, 20, 30, 50]
        else:
            # Put 情境：股價下跌
            price_changes = [50, 30, 20, 15, 10, 5, 0, -5, -10, -20]
        
        for pct_change in price_changes:
            new_price = stock_price * (1 + pct_change / 100)
            
            if option_type == 'call':
                # Call 到期價值 = max(0, 股價 - 行使價)
                intrinsic_value = max(0, new_price - strike_price)
            else:
                # Put 到期價值 = max(0, 行使價 - 股價)
                intrinsic_value = max(0, strike_price - new_price)
            
            total_value = intrinsic_value * contract_size
            profit_loss = total_value - total_cost
            profit_loss_pct = (profit_loss / total_cost) * 100 if total_cost > 0 else 0
            
            scenarios.append({
                'stock_change_pct': pct_change,
                'stock_price': round(new_price, 2),
                'intrinsic_value': round(intrinsic_value, 2),
                'total_value': round(total_value, 2),
                'profit_loss': round(profit_loss, 2),
                'profit_loss_pct': round(profit_loss_pct, 1),
                'result': '🟢 獲利' if profit_loss > 0 else ('🔴 虧損' if profit_loss < 0 else '➖ 持平')
            })
        
        return scenarios
    
    def _analyze_theta(
        self,
        theta: Optional[float],
        premium: float,
        days_to_expiration: int,
        contract_size: int
    ) -> Dict[str, Any]:
        """分析 Theta 時間衰減"""
        
        # 添加 None 檢查
        if theta is None:
            return {
                'theta_per_share': None,
                'daily_decay_dollar': None,
                'weekly_decay_dollar': None,
                'daily_decay_pct': None,
                'days_to_expiration': days_to_expiration,
                'estimated_decay_to_expiry': None,
                'risk_level': '⚪ 數據不足',
                'warning': '無 Theta 數據，無法評估時間衰減風險',
                'suggestion': '建議獲取完整的期權 Greeks 數據'
            }
        
        daily_decay = abs(theta) * contract_size
        weekly_decay = daily_decay * 5  # 交易日
        total_cost = premium * contract_size
        
        # 每日衰減佔權利金比例
        daily_decay_pct = (abs(theta) / premium) * 100 if premium > 0 else 0
        
        # 預估到期前總衰減
        estimated_total_decay = daily_decay * min(days_to_expiration, 30)
        
        # Theta 風險評估
        if daily_decay_pct > 5:
            theta_risk = "🔴 高風險"
            theta_warning = "時間衰減嚴重，建議短期持有或選擇更長到期日"
        elif daily_decay_pct > 2:
            theta_risk = "🟠 中等風險"
            theta_warning = "注意時間價值流失，設定明確出場時間"
        elif daily_decay_pct > 1:
            theta_risk = "🟡 低風險"
            theta_warning = "時間衰減可接受"
        else:
            theta_risk = "🟢 極低風險"
            theta_warning = "時間衰減影響小"
        
        return {
            'theta_per_share': theta,
            'daily_decay_dollar': round(daily_decay, 2),
            'weekly_decay_dollar': round(weekly_decay, 2),
            'daily_decay_pct': round(daily_decay_pct, 2),
            'days_to_expiration': days_to_expiration,
            'estimated_decay_to_expiry': round(estimated_total_decay, 2),
            'risk_level': theta_risk,
            'warning': theta_warning,
            'suggestion': self._theta_suggestion(days_to_expiration, daily_decay_pct)
        }
    
    def _theta_suggestion(self, days: int, decay_pct: float) -> str:
        """根據 Theta 給出建議"""
        if days <= 7:
            return "⚠️ 到期日很近，Theta 加速衰減，謹慎持有"
        elif days <= 14:
            return "🟡 接近到期，注意時間價值流失"
        elif days <= 30:
            return "🟢 時間充裕，但仍需關注 Theta"
        else:
            return "✅ 到期日較遠，Theta 影響較小"
    
    def _analyze_iv_for_long(self, iv: Optional[float], option_type: str) -> Dict[str, Any]:
        """分析 IV 對 Long 期權的影響"""
        
        # 添加 None 檢查
        if iv is None:
            return {
                'current_iv': None,
                'iv_level': '⚪ 數據不足',
                'assessment': '無 IV 數據，無法評估期權價格水平',
                'buy_timing': '⚪ 無法判斷',
                'vega_risk': '無法評估 Vega 風險'
            }
        
        # 標準化 IV 格式（統一為百分比）
        iv_pct = iv * 100 if iv <= 1.0 else iv
        
        # IV 水平評估（對於買方）
        if iv_pct < 20:
            iv_level = "🟢 低 IV"
            iv_assessment = "期權便宜，適合買入"
            buy_timing = "✅ 好時機"
        elif iv_pct < 35:
            iv_level = "🟡 中等 IV"
            iv_assessment = "期權價格合理"
            buy_timing = "🟡 可以買入"
        elif iv_pct < 50:
            iv_level = "🟠 較高 IV"
            iv_assessment = "期權較貴，注意 IV 回落風險"
            buy_timing = "⚠️ 謹慎買入"
        else:
            iv_level = "🔴 高 IV"
            iv_assessment = "期權很貴，IV 回落會造成虧損"
            buy_timing = "🔴 不建議買入"
        
        return {
            'current_iv': iv_pct,
            'iv_level': iv_level,
            'assessment': iv_assessment,
            'buy_timing': buy_timing,
            'vega_risk': "IV 下降會導致期權價值下跌" if iv_pct > 30 else "IV 上升會增加期權價值"
        }

    
    def _calculate_long_score(self, result: Dict, option_type: str) -> Dict[str, Any]:
        """計算 Long 期權綜合評分"""
        
        score = 50  # 基礎分
        factors = []
        
        # 1. 盈虧平衡點評分 (最高 25 分)
        breakeven_pct = abs(result['breakeven']['distance_pct'])
        if breakeven_pct <= 3:
            score += 25
            factors.append(('盈虧平衡點', '+25', '容易達到'))
        elif breakeven_pct <= 7:
            score += 15
            factors.append(('盈虧平衡點', '+15', '中等難度'))
        elif breakeven_pct <= 15:
            score += 5
            factors.append(('盈虧平衡點', '+5', '較難達到'))
        else:
            score -= 10
            factors.append(('盈虧平衡點', '-10', '困難'))
        
        # 2. 槓桿評分 (最高 20 分)
        leverage = result['leverage']['effective_leverage']
        if leverage >= 8:
            score += 20
            factors.append(('槓桿倍數', '+20', f'{leverage:.1f}x 超高槓桿'))
        elif leverage >= 5:
            score += 15
            factors.append(('槓桿倍數', '+15', f'{leverage:.1f}x 高槓桿'))
        elif leverage >= 3:
            score += 10
            factors.append(('槓桿倍數', '+10', f'{leverage:.1f}x 中等槓桿'))
        else:
            score += 0
            factors.append(('槓桿倍數', '+0', f'{leverage:.1f}x 低槓桿'))
        
        # 3. Theta 風險評分 (最高 15 分)
        theta_decay_pct = result['theta_analysis']['daily_decay_pct']
        if theta_decay_pct is None:
            # Theta 數據缺失，不調整分數
            factors.append(('Theta 風險', '+0', '數據不足'))
        elif theta_decay_pct < 1:
            score += 15
            factors.append(('Theta 風險', '+15', '極低衰減'))
        elif theta_decay_pct < 2:
            score += 10
            factors.append(('Theta 風險', '+10', '低衰減'))
        elif theta_decay_pct < 5:
            score += 0
            factors.append(('Theta 風險', '+0', '中等衰減'))
        else:
            score -= 15
            factors.append(('Theta 風險', '-15', '高衰減'))
        
        # 4. IV 評分 (最高 15 分)
        iv = result['iv_analysis']['current_iv']
        if iv is None:
            # IV 數據缺失，不調整分數
            factors.append(('IV 水平', '+0', '數據不足'))
        elif iv < 20:
            score += 15
            factors.append(('IV 水平', '+15', '低 IV，期權便宜'))
        elif iv < 35:
            score += 10
            factors.append(('IV 水平', '+10', '中等 IV'))
        elif iv < 50:
            score += 0
            factors.append(('IV 水平', '+0', '較高 IV'))
        else:
            score -= 10
            factors.append(('IV 水平', '-10', '高 IV，期權貴'))
        
        # 5. 到期天數評分 (最高 10 分)
        days = result['theta_analysis']['days_to_expiration']
        if days >= 30:
            score += 10
            factors.append(('到期天數', '+10', f'{days}天，時間充裕'))
        elif days >= 14:
            score += 5
            factors.append(('到期天數', '+5', f'{days}天，時間適中'))
        elif days >= 7:
            score += 0
            factors.append(('到期天數', '+0', f'{days}天，時間緊迫'))
        else:
            score -= 10
            factors.append(('到期天數', '-10', f'{days}天，即將到期'))
        
        # 確保分數在 0-100 範圍內
        score = max(0, min(100, score))
        
        # 評級
        if score >= 80:
            grade = 'A'
            grade_desc = '優秀 - 強烈推薦'
        elif score >= 65:
            grade = 'B'
            grade_desc = '良好 - 可以考慮'
        elif score >= 50:
            grade = 'C'
            grade_desc = '中等 - 謹慎操作'
        elif score >= 35:
            grade = 'D'
            grade_desc = '較差 - 不建議'
        else:
            grade = 'F'
            grade_desc = '差 - 避免交易'
        
        return {
            'total_score': score,
            'grade': grade,
            'grade_description': grade_desc,
            'factors': factors
        }
    
    def _generate_recommendation(self, result: Dict, option_type: str) -> Dict[str, Any]:
        """生成交易建議"""
        
        score = result['score']['total_score']
        grade = result['score']['grade']
        leverage = result['leverage']['effective_leverage']
        breakeven_pct = abs(result['breakeven']['distance_pct'])
        iv = result['iv_analysis']['current_iv']
        days = result['theta_analysis']['days_to_expiration']
        
        recommendations = []
        warnings = []
        
        # 基於評分的主要建議
        if grade in ['A', 'B']:
            recommendations.append(f"✅ {option_type.upper()} 評分 {score} 分，可以考慮買入")
        elif grade == 'C':
            recommendations.append(f"🟡 {option_type.upper()} 評分 {score} 分，謹慎操作")
        else:
            recommendations.append(f"🔴 {option_type.upper()} 評分 {score} 分，不建議買入")
        
        # 槓桿建議
        if leverage >= 5:
            recommendations.append(f"📈 槓桿 {leverage:.1f}x，適合以小博大")
        
        # 盈虧平衡點建議
        if breakeven_pct > 10:
            warnings.append(f"⚠️ 盈虧平衡點需股價變動 {breakeven_pct:.1f}%")
        
        # IV 建議
        if iv is not None:
            if iv > 40:
                warnings.append(f"⚠️ IV {iv:.1f}% 偏高，注意 IV 回落風險")
            elif iv < 25:
                recommendations.append(f"✅ IV {iv:.1f}% 偏低，期權相對便宜")
        else:
            warnings.append("⚠️ IV 數據缺失，無法評估期權價格水平")
        
        # 時間建議
        if days <= 7:
            warnings.append(f"⚠️ 僅剩 {days} 天到期，Theta 加速衰減")
        
        # 倉位建議
        total_cost = result['cost_analysis']['total_cost']
        position_suggestion = self._suggest_position_size(total_cost, score)
        
        return {
            'action': 'BUY' if grade in ['A', 'B'] else ('HOLD' if grade == 'C' else 'AVOID'),
            'confidence': 'HIGH' if grade == 'A' else ('MEDIUM' if grade in ['B', 'C'] else 'LOW'),
            'recommendations': recommendations,
            'warnings': warnings,
            'position_suggestion': position_suggestion
        }
    
    def _suggest_position_size(self, cost_per_contract: float, score: int) -> str:
        """建議倉位大小"""
        
        # 假設總資金 13萬 HKD ≈ $16,700 USD
        # 單筆建議 5-10% = $835-$1,670
        
        if score >= 80:
            return f"建議倉位: 1-2 張 (成本 ${cost_per_contract:.0f}-${cost_per_contract*2:.0f})"
        elif score >= 65:
            return f"建議倉位: 1 張 (成本 ${cost_per_contract:.0f})"
        elif score >= 50:
            return f"建議倉位: 0.5-1 張 (謹慎)"
        else:
            return "不建議開倉"
    
    def analyze_both(
        self,
        stock_price: float,
        call_strike: float,
        call_premium: float,
        put_strike: float,
        put_premium: float,
        days_to_expiration: int,
        call_delta: float = 0.5,
        put_delta: float = -0.5,
        call_theta: float = 0.0,
        put_theta: float = 0.0,
        iv: float = 0.0
    ) -> Dict[str, Any]:
        """同時分析 Long Call 和 Long Put，比較哪個更適合"""
        
        call_result = self.analyze_long_call(
            stock_price=stock_price,
            strike_price=call_strike,
            premium=call_premium,
            days_to_expiration=days_to_expiration,
            delta=call_delta,
            theta=call_theta,
            iv=iv
        )
        
        put_result = self.analyze_long_put(
            stock_price=stock_price,
            strike_price=put_strike,
            premium=put_premium,
            days_to_expiration=days_to_expiration,
            delta=put_delta,
            theta=put_theta,
            iv=iv
        )
        
        # 比較兩者
        call_score = call_result.get('score', {}).get('total_score', 0)
        put_score = put_result.get('score', {}).get('total_score', 0)
        
        if call_score > put_score + 10:
            better_choice = 'Long Call'
            reason = f"Long Call 評分 ({call_score}) 明顯高於 Long Put ({put_score})"
        elif put_score > call_score + 10:
            better_choice = 'Long Put'
            reason = f"Long Put 評分 ({put_score}) 明顯高於 Long Call ({call_score})"
        else:
            better_choice = '兩者相近'
            reason = f"Long Call ({call_score}) 和 Long Put ({put_score}) 評分接近，根據方向判斷選擇"
        
        return {
            'long_call': call_result,
            'long_put': put_result,
            'comparison': {
                'call_score': call_score,
                'put_score': put_score,
                'better_choice': better_choice,
                'reason': reason
            },
            'analysis_time': self.analysis_date
        }


# 測試代碼
if __name__ == "__main__":
    analyzer = LongOptionAnalyzer()
    
    # 測試 Long Call
    result = analyzer.analyze_long_call(
        stock_price=198.52,
        strike_price=200.00,
        premium=5.50,
        days_to_expiration=14,
        delta=0.45,
        theta=-0.65,
        iv=55.0
    )
    
    print("=== Long Call 分析 ===")
    print(f"評分: {result['score']['total_score']} ({result['score']['grade']})")
    print(f"盈虧平衡點: ${result['breakeven']['price']:.2f}")
    print(f"槓桿倍數: {result['leverage']['effective_leverage']}x")
