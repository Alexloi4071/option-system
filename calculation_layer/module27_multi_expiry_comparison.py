"""
Module 27: 多到期日比較分析
比較不同到期日的期權，找出最佳「到期日 + 行使價」組合

功能：
1. 列出所有可用到期日
2. 每個到期日的 ATM 權利金、IV、Theta
3. 計算年化收益率比較
4. 推薦最佳到期日（性價比最高）
5. Theta 衰減曲線分析
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import math

logger = logging.getLogger(__name__)


class MultiExpiryAnalyzer:
    """多到期日比較分析器"""
    
    def __init__(self):
        self.analysis_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def analyze_expirations(
        self,
        ticker: str,
        current_price: float,
        expiration_data: List[Dict[str, Any]],
        strategy_type: str = 'long_call',  # long_call, long_put, short_put, short_call
        max_expirations: int = 10  # 最多分析 10 個最近的到期日
    ) -> Dict[str, Any]:
        """
        分析多個到期日的期權數據
        
        Args:
            ticker: 股票代碼
            current_price: 當前股價
            expiration_data: 各到期日的期權數據列表
                [{'expiration': '2026-01-17', 'days': 5, 'atm_call': {...}, 'atm_put': {...}}, ...]
            strategy_type: 策略類型
            max_expirations: 最多分析的到期日數量（默認 10）
        
        Returns:
            Dict: 多到期日比較分析結果
        """
        try:
            if not expiration_data:
                return {
                    'status': 'error',
                    'reason': '無可用到期日數據'
                }
            
            # 限制到期日數量：按日期排序，選擇最近的 max_expirations 個
            if len(expiration_data) > max_expirations:
                logger.info(f"  到期日限制: 從 {len(expiration_data)} 個到期日中選擇最近的 {max_expirations} 個")
                # 按 days 排序（最近的在前）
                sorted_data = sorted(expiration_data, key=lambda x: x.get('days', 999))
                expiration_data = sorted_data[:max_expirations]
                logger.info(f"  選擇的到期日範圍: {expiration_data[0].get('days')} - {expiration_data[-1].get('days')} 天")
            
            result = {
                'status': 'success',
                'ticker': ticker,
                'current_price': current_price,
                'strategy_type': strategy_type,
                'analysis_date': self.analysis_date,
                'expirations_analyzed': len(expiration_data),
                'expiration_details': [],
                'comparison_table': [],
                'recommendation': None
            }
            
            # 分析每個到期日（使用批處理以優化內存）
            batch_size = 5  # 每批處理 5 個到期日
            total_expirations = len(expiration_data)
            
            logger.info(f"  開始批處理分析: 總共 {total_expirations} 個到期日，每批 {batch_size} 個")
            
            for batch_start in range(0, total_expirations, batch_size):
                batch_end = min(batch_start + batch_size, total_expirations)
                batch_data = expiration_data[batch_start:batch_end]
                
                logger.info(f"  處理批次 {batch_start//batch_size + 1}/{(total_expirations + batch_size - 1)//batch_size}: 到期日 {batch_start+1}-{batch_end}")
                
                for exp_data in batch_data:
                    exp_analysis = self._analyze_single_expiration(
                        exp_data, current_price, strategy_type
                    )
                    if exp_analysis:
                        result['expiration_details'].append(exp_analysis)
                        result['comparison_table'].append({
                            'expiration': exp_data.get('expiration'),
                            'days': exp_data.get('days'),
                            'premium': exp_analysis.get('premium'),
                            'iv': exp_analysis.get('iv'),
                            'theta_daily': exp_analysis.get('theta_daily'),
                            'theta_pct': exp_analysis.get('theta_pct'),
                            'annualized_return': exp_analysis.get('annualized_return'),
                            'score': exp_analysis.get('score'),
                            'grade': exp_analysis.get('grade')
                        })
                
                # 批處理後清理內存
                del batch_data
                import gc
                gc.collect()
            
            # 找出最佳到期日
            if result['comparison_table']:
                result['recommendation'] = self._find_best_expiration(
                    result['comparison_table'], strategy_type
                )
            
            # 生成 Theta 衰減分析
            result['theta_analysis'] = self._analyze_theta_curve(result['comparison_table'])
            
            # 清理大型中間數據結構
            del expiration_data
            import gc
            gc.collect()
            
            return result
            
        except Exception as e:
            logger.error(f"多到期日分析錯誤: {e}")
            return {
                'status': 'error',
                'reason': str(e)
            }
    
    def _analyze_single_expiration(
        self,
        exp_data: Dict,
        current_price: float,
        strategy_type: str
    ) -> Optional[Dict[str, Any]]:
        """分析單個到期日"""
        try:
            expiration = exp_data.get('expiration')
            days = exp_data.get('days', 0)
            
            if days <= 0:
                return None
            
            # 根據策略類型選擇期權數據
            if strategy_type in ['long_call', 'short_call']:
                option_data = exp_data.get('atm_call', {})
            else:
                option_data = exp_data.get('atm_put', {})
            
            if not option_data:
                return None
            
            # 提取數據
            premium = option_data.get('lastPrice') or option_data.get('last') or \
                      ((option_data.get('bid', 0) + option_data.get('ask', 0)) / 2)
            strike = option_data.get('strike', current_price)
            iv = option_data.get('impliedVolatility', None)  # Use None instead of 0
            
            # Check IV validity and standardize format
            if iv is None or iv == 0:
                logger.warning(f"到期日 {expiration} 的 IV 數據缺失或為零")
                # Continue processing but mark IV as unavailable
                iv = None
            elif iv < 1:  # Only check if iv is not None - decimal format, convert to percentage
                iv = iv * 100
            
            theta = option_data.get('theta', 0)
            delta = option_data.get('delta', 0.5)
            
            if not premium or premium <= 0:
                return None
            
            # 計算指標
            # Theta 每日衰減百分比
            theta_daily = abs(theta) if theta else 0
            theta_pct = (theta_daily / premium) * 100 if premium > 0 else 0
            
            # 年化收益率（對於 Short 策略）
            if strategy_type.startswith('short'):
                annualized_return = (premium / strike) * (365 / days) * 100
            else:
                # Long 策略：計算槓桿效益
                annualized_return = (abs(delta) * current_price / premium) * 100 if premium > 0 else 0
            
            # 評分
            score, grade = self._calculate_expiry_score(
                days, premium, iv, theta_pct, annualized_return, strategy_type
            )
            
            return {
                'expiration': expiration,
                'days': days,
                'strike': strike,
                'premium': round(premium, 2),
                'iv': round(iv, 2) if iv is not None else None,
                'iv_available': iv is not None,  # Add flag to track IV availability
                'delta': round(abs(delta), 4),
                'theta': round(theta, 4),
                'theta_daily': round(theta_daily, 4),
                'theta_pct': round(theta_pct, 2),
                'annualized_return': round(annualized_return, 2),
                'total_cost': round(premium * 100, 2),
                'score': score,
                'grade': grade,
                'category': self._categorize_expiry(days)
            }
            
        except Exception as e:
            logger.warning(f"分析到期日 {exp_data.get('expiration')} 失敗: {e}")
            return None
    
    def _categorize_expiry(self, days: int) -> str:
        """分類到期日"""
        if days <= 7:
            return "極短期 (<7天)"
        elif days <= 14:
            return "短期 (7-14天)"
        elif days <= 30:
            return "中短期 (14-30天)"
        elif days <= 60:
            return "中期 (30-60天)"
        elif days <= 90:
            return "中長期 (60-90天)"
        else:
            return "長期 (>90天)"
    
    def _calculate_expiry_score(
        self,
        days: int,
        premium: float,
        iv: Optional[float],
        theta_pct: float,
        annualized_return: float,
        strategy_type: str
    ) -> tuple:
        """計算到期日評分"""
        score = 50  # 基礎分
        
        if strategy_type.startswith('long'):
            # Long 策略評分邏輯
            # 1. 到期天數 (30-60天最佳)
            if 30 <= days <= 60:
                score += 25
            elif 14 <= days < 30 or 60 < days <= 90:
                score += 15
            elif 7 <= days < 14:
                score += 5
            elif days < 7:
                score -= 15
            else:
                score += 10
            
            # 2. Theta 衰減 (越低越好)
            if theta_pct < 1:
                score += 15
            elif theta_pct < 2:
                score += 10
            elif theta_pct < 3:
                score += 5
            elif theta_pct > 5:
                score -= 10
            
            # 3. IV 水平 (Long 策略偏好低 IV) - Add None check
            if iv is not None:
                if iv < 25:
                    score += 10
                elif iv < 35:
                    score += 5
                elif iv > 50:
                    score -= 10
            else:
                # IV 數據缺失，不調整分數但記錄警告
                logger.warning("IV 數據缺失，評分可能不準確")
            
        else:
            # Short 策略評分邏輯
            # 1. 到期天數 (30-45天最佳)
            if 30 <= days <= 45:
                score += 25
            elif 21 <= days < 30 or 45 < days <= 60:
                score += 15
            elif 14 <= days < 21:
                score += 10
            elif days < 14:
                score -= 5
            else:
                score += 5
            
            # 2. 年化收益率
            if annualized_return > 50:
                score += 15
            elif annualized_return > 30:
                score += 10
            elif annualized_return > 20:
                score += 5
            
            # 3. IV 水平 (Short 策略偏好高 IV) - Add None check
            if iv is not None:
                if iv > 50:
                    score += 10
                elif iv > 35:
                    score += 5
                elif iv < 20:
                    score -= 10
            else:
                # IV 數據缺失，不調整分數但記錄警告
                logger.warning("IV 數據缺失，評分可能不準確")
        
        # 確保分數在 0-100 範圍內
        score = max(0, min(100, score))
        
        # 評級
        if score >= 80:
            grade = 'A'
        elif score >= 65:
            grade = 'B'
        elif score >= 50:
            grade = 'C'
        elif score >= 35:
            grade = 'D'
        else:
            grade = 'F'
        
        return score, grade

    
    def _find_best_expiration(
        self,
        comparison_table: List[Dict],
        strategy_type: str
    ) -> Dict[str, Any]:
        """找出最佳到期日"""
        if not comparison_table:
            return {'best': None, 'reason': '無可用數據'}
        
        # Check data completeness - count missing IV data
        missing_iv_count = sum(1 for exp in comparison_table if exp.get('iv') is None)
        
        if missing_iv_count > 0:
            logger.warning(f"{missing_iv_count}/{len(comparison_table)} 個到期日缺少 IV 數據")
        
        # 按評分排序
        sorted_exps = sorted(comparison_table, key=lambda x: x.get('score', 0), reverse=True)
        best = sorted_exps[0]
        
        # 生成推薦理由
        reasons = []
        
        if best['grade'] in ['A', 'B']:
            reasons.append(f"評分 {best['score']} ({best['grade']}) 為最高")
        
        days = best.get('days', 0)
        if strategy_type.startswith('long'):
            if 30 <= days <= 60:
                reasons.append(f"{days} 天到期，時間充裕且 Theta 衰減適中")
            elif days < 14:
                reasons.append(f"⚠️ {days} 天到期較短，注意 Theta 加速衰減")
        else:
            if 30 <= days <= 45:
                reasons.append(f"{days} 天到期，Theta 衰減最佳收益期")
        
        theta_pct = best.get('theta_pct', 0)
        if theta_pct < 2:
            reasons.append(f"Theta 衰減 {theta_pct:.1f}%/天，時間價值流失可控")
        
        # 次優選擇
        alternatives = []
        for exp in sorted_exps[1:3]:  # 取第2、3名
            if exp.get('score', 0) >= 50:
                alternatives.append({
                    'expiration': exp.get('expiration'),
                    'days': exp.get('days'),
                    'score': exp.get('score'),
                    'grade': exp.get('grade')
                })
        
        result = {
            'best_expiration': best.get('expiration'),
            'best_days': best.get('days'),
            'best_score': best.get('score'),
            'best_grade': best.get('grade'),
            'best_premium': best.get('premium'),
            'best_category': self._categorize_expiry(best.get('days', 0)),
            'reasons': reasons,
            'alternatives': alternatives,
            'strategy_type': strategy_type
        }
        
        # Add data quality warning if IV data is missing
        if missing_iv_count > 0:
            result['data_quality_warning'] = f"{missing_iv_count} 個到期日缺少 IV 數據"
        
        return result
    
    def _analyze_theta_curve(self, comparison_table: List[Dict]) -> Dict[str, Any]:
        """分析 Theta 衰減曲線"""
        if not comparison_table:
            return {'status': 'no_data'}
        
        # 按天數排序
        sorted_by_days = sorted(comparison_table, key=lambda x: x.get('days', 0))
        
        theta_curve = []
        for exp in sorted_by_days:
            theta_curve.append({
                'days': exp.get('days'),
                'theta_pct': exp.get('theta_pct'),
                'premium': exp.get('premium')
            })
        
        # 找出 Theta 衰減加速點
        acceleration_point = None
        for i, exp in enumerate(sorted_by_days):
            if exp.get('theta_pct', 0) > 3:  # Theta > 3%/天 視為加速
                acceleration_point = exp.get('days')
                break
        
        # 計算平均 Theta
        avg_theta = sum(e.get('theta_pct', 0) for e in sorted_by_days) / len(sorted_by_days) if sorted_by_days else 0
        
        return {
            'theta_curve': theta_curve,
            'acceleration_point': acceleration_point,
            'avg_theta_pct': round(avg_theta, 2),
            'warning': f"⚠️ {acceleration_point} 天後 Theta 加速衰減" if acceleration_point else None,
            'suggestion': self._theta_suggestion(acceleration_point)
        }
    
    def _theta_suggestion(self, acceleration_point: Optional[int]) -> str:
        """根據 Theta 加速點給出建議"""
        if acceleration_point is None:
            return "Theta 衰減平穩，可根據其他因素選擇到期日"
        elif acceleration_point <= 7:
            return "極短期期權 Theta 衰減劇烈，Long 策略應避免"
        elif acceleration_point <= 14:
            return "短期期權 Theta 開始加速，建議選擇 30 天以上到期日"
        else:
            return f"建議選擇 {acceleration_point + 7} 天以上到期日以避免 Theta 加速衰減"
    
    def compare_for_long_strategy(
        self,
        ticker: str,
        current_price: float,
        expiration_data: List[Dict],
        direction: str = 'bullish'  # bullish or bearish
    ) -> Dict[str, Any]:
        """
        專為 Long 策略比較到期日
        
        Args:
            ticker: 股票代碼
            current_price: 當前股價
            expiration_data: 各到期日數據
            direction: 方向判斷 (bullish/bearish)
        """
        strategy_type = 'long_call' if direction == 'bullish' else 'long_put'
        
        result = self.analyze_expirations(
            ticker=ticker,
            current_price=current_price,
            expiration_data=expiration_data,
            strategy_type=strategy_type
        )
        
        if result.get('status') == 'success':
            # 添加 Long 策略專用建議
            result['long_strategy_advice'] = self._generate_long_advice(
                result.get('recommendation', {}),
                result.get('theta_analysis', {}),
                direction
            )
        
        return result
    
    def _generate_long_advice(
        self,
        recommendation: Dict,
        theta_analysis: Dict,
        direction: str
    ) -> Dict[str, Any]:
        """生成 Long 策略專用建議"""
        advice = {
            'direction': direction,
            'recommended_expiry_range': '30-60 天',
            'avoid_expiry_range': '<14 天',
            'key_points': []
        }
        
        best_days = recommendation.get('best_days', 0)
        
        if best_days:
            if best_days < 14:
                advice['key_points'].append("⚠️ 推薦到期日較短，Theta 風險高")
                advice['key_points'].append("建議考慮更長到期日或減少倉位")
            elif 14 <= best_days < 30:
                advice['key_points'].append("🟡 中短期到期日，注意時間價值流失")
            elif 30 <= best_days <= 60:
                advice['key_points'].append("✅ 最佳到期日範圍，時間充裕")
            else:
                advice['key_points'].append("🟢 長期到期日，Theta 影響小但權利金較高")
        
        # Theta 建議
        if theta_analysis.get('warning'):
            advice['key_points'].append(theta_analysis['warning'])
        
        advice['key_points'].append(f"方向: {'看漲 Long Call' if direction == 'bullish' else '看跌 Long Put'}")
        
        return advice


# 測試代碼
if __name__ == "__main__":
    analyzer = MultiExpiryAnalyzer()
    
    # 模擬數據
    test_data = [
        {'expiration': '2026-01-17', 'days': 5, 'atm_call': {'strike': 200, 'lastPrice': 3.5, 'impliedVolatility': 0.55, 'theta': -0.8, 'delta': 0.5}},
        {'expiration': '2026-01-24', 'days': 12, 'atm_call': {'strike': 200, 'lastPrice': 5.2, 'impliedVolatility': 0.52, 'theta': -0.5, 'delta': 0.52}},
        {'expiration': '2026-02-21', 'days': 40, 'atm_call': {'strike': 200, 'lastPrice': 9.8, 'impliedVolatility': 0.48, 'theta': -0.25, 'delta': 0.55}},
    ]
    
    result = analyzer.analyze_expirations(
        ticker='TEST',
        current_price=200,
        expiration_data=test_data,
        strategy_type='long_call'
    )
    
    print("=== 多到期日比較 ===")
    if result.get('recommendation'):
        rec = result['recommendation']
        print(f"最佳到期日: {rec.get('best_expiration')} ({rec.get('best_days')}天)")
        print(f"評分: {rec.get('best_score')} ({rec.get('best_grade')})")
