# output_layer/delta_analyzer.py
"""
Delta Analyzer Module - 分析兩次運行的差異
功能:
1. 比較主要指標變化 (價格, IV, 策略)
2. 生成異動報告
3. 檢測交易機會

Requirements: New Requirement - History Tracking & Comparison
"""

import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

class DeltaAnalyzer:
    """差異分析器"""
    
    def compare_results(self, current: Dict, previous: Dict) -> Dict:
        """
        比較當前和之前的結果
        
        參數:
            current: 當前運行的完整 JSON 數據
            previous: 之前運行的完整 JSON 數據
            
        返回:
            Dict: 差異分析報告
        """
        changes = {
            'timestamp_current': current['metadata']['generated_at'],
            'timestamp_previous': previous['metadata']['generated_at'],
            'price_change': self._compare_price(current, previous),
            'iv_change': self._compare_iv(current, previous),
            'strategy_change': self._compare_strategy(current, previous),
            'direction_change': self._compare_direction(current, previous),
            'opportunity_alert': []
        }
        
        # 生成機會警報
        changes['opportunity_alert'] = self._generate_alerts(changes)
        
        return changes
    
    def _compare_price(self, cur: Dict, prev: Dict) -> Dict:
        """比較價格變化"""
        try:
            p1 = cur['raw_data']['current_price']
            p2 = prev['raw_data']['current_price']
            if p1 is None or p2 is None: return {}
            
            diff = p1 - p2
            pct = (diff / p2) * 100 if p2 != 0 else 0
            
            return {
                'current': p1,
                'previous': p2,
                'diff': diff,
                'pct': pct,
                'significant': abs(pct) > 1.0  # 1% 以上視為顯著
            }
        except:
            return {}
            
    def _compare_iv(self, cur: Dict, prev: Dict) -> Dict:
        """比較 IV 變化"""
        try:
            iv1 = cur['raw_data']['implied_volatility']
            iv2 = prev['raw_data']['implied_volatility']
            
            # 嘗試獲取 IV Rank
            rank1 = cur['calculations'].get('module18_historical_volatility', {}).get('iv_rank')
            rank2 = prev['calculations'].get('module18_historical_volatility', {}).get('iv_rank')
            
            return {
                'current_iv': iv1,
                'previous_iv': iv2,
                'iv_diff': iv1 - iv2 if iv1 and iv2 else 0,
                'current_rank': rank1,
                'previous_rank': rank2,
                'rank_diff': rank1 - rank2 if rank1 and rank2 else 0
            }
        except:
            return {}

    def _compare_direction(self, cur: Dict, prev: Dict) -> Dict:
        """比較方向判斷變化"""
        try:
            d1 = cur['calculations']['module24_technical_direction']['combined_direction']
            d2 = prev['calculations']['module24_technical_direction']['combined_direction']
            
            return {
                'current': d1,
                'previous': d2,
                'changed': d1 != d2
            }
        except:
            return {'changed': False}

    def _compare_strategy(self, cur: Dict, prev: Dict) -> Dict:
        """比較推薦策略變化"""
        try:
            rec1 = cur['calculations']['strategy_recommendations']
            rec2 = prev['calculations']['strategy_recommendations']
            
            top1 = rec1[0]['strategy_name'] if rec1 else "None"
            top2 = rec2[0]['strategy_name'] if rec2 else "None"
            
            return {
                'current_top': top1,
                'previous_top': top2,
                'changed': top1 != top2
            }
        except:
            return {'changed': False}
            
    def _generate_alerts(self, changes: Dict) -> List[str]:
        """基於變化生成警報"""
        alerts = []
        
        # 1. 方向反轉
        dir_chg = changes['direction_change']
        if dir_chg.get('changed'):
            alerts.append(f"⚠️ 方向反轉: {dir_chg['previous']} -> {dir_chg['current']}")
            
        # 2. 價格劇烈波動
        px = changes['price_change']
        if px.get('significant'):
            alerts.append(f"⚠️ 價格異動: {px['pct']:.2f}% (現價 ${px['current']})")
            
        # 3. IV 劇烈變化
        iv = changes['iv_change']
        if iv.get('rank_diff') and abs(iv['rank_diff']) > 10:
            alerts.append(f"⚠️ IV Rank 強烈變化: {iv['previous_rank']:.0f} -> {iv['current_rank']:.0f}")

        # 4. 策略變化
        strat = changes['strategy_change']
        if strat.get('changed'):
            alerts.append(f"💡 策略改變: 建議從 [{strat['previous_top']}] 改為 [{strat['current_top']}]")
            
        return alerts
