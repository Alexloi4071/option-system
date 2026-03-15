# output_layer/delta_analyzer.py
"""
Delta Analyzer Module.

Compares the latest run against the previous run and produces a clean,
encoding-safe delta summary for reports.
"""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class DeltaAnalyzer:
    """Compare current and previous report outputs."""

    def compare_results(self, current: Dict, previous: Dict) -> Dict:
        """Build a structured delta report between two runs."""
        changes = {
            'timestamp_current': current['metadata']['generated_at'],
            'timestamp_previous': previous['metadata']['generated_at'],
            'price_change': self._compare_price(current, previous),
            'iv_change': self._compare_iv(current, previous),
            'strategy_change': self._compare_strategy(current, previous),
            'direction_change': self._compare_direction(current, previous),
            'opportunity_alert': [],
        }
        changes['opportunity_alert'] = self._generate_alerts(changes)
        return changes

    def _compare_price(self, cur: Dict, prev: Dict) -> Dict:
        """Compare underlying price between runs."""
        try:
            p1 = cur['raw_data']['current_price']
            p2 = prev['raw_data']['current_price']
            if p1 is None or p2 is None:
                return {}

            diff = p1 - p2
            pct = (diff / p2) * 100 if p2 != 0 else 0
            return {
                'current': p1,
                'previous': p2,
                'diff': diff,
                'pct': pct,
                'significant': abs(pct) > 1.0,
            }
        except Exception:
            return {}

    def _compare_iv(self, cur: Dict, prev: Dict) -> Dict:
        """Compare IV and IV Rank between runs."""
        try:
            iv1 = cur['raw_data']['implied_volatility']
            iv2 = prev['raw_data']['implied_volatility']
            rank1 = cur['calculations'].get('module18_historical_volatility', {}).get('iv_rank')
            rank2 = prev['calculations'].get('module18_historical_volatility', {}).get('iv_rank')
            return {
                'current_iv': iv1,
                'previous_iv': iv2,
                'iv_diff': iv1 - iv2 if iv1 is not None and iv2 is not None else None,
                'current_rank': rank1,
                'previous_rank': rank2,
                'rank_diff': rank1 - rank2 if rank1 is not None and rank2 is not None else None,
            }
        except Exception:
            return {}

    def _compare_direction(self, cur: Dict, prev: Dict) -> Dict:
        """Compare technical direction between runs."""
        try:
            d1 = cur['calculations']['module24_technical_direction']['combined_direction']
            d2 = prev['calculations']['module24_technical_direction']['combined_direction']
            return {
                'current': d1,
                'previous': d2,
                'changed': d1 != d2,
            }
        except Exception:
            return {'changed': False}

    def _compare_strategy(self, cur: Dict, prev: Dict) -> Dict:
        """Compare final recommended strategy between runs."""
        try:
            rec1 = cur['calculations']['strategy_recommendations']
            rec2 = prev['calculations']['strategy_recommendations']
            top1 = self._normalize_strategy_name(rec1[0].get('strategy_name') if rec1 else 'None')
            top2 = self._normalize_strategy_name(rec2[0].get('strategy_name') if rec2 else 'None')
            return {
                'current_top': top1,
                'previous_top': top2,
                'changed': top1 != top2,
            }
        except Exception:
            return {'changed': False}

    def _generate_alerts(self, changes: Dict) -> List[str]:
        """Generate clean alert strings for the delta section."""
        alerts = []

        dir_chg = changes['direction_change']
        if dir_chg.get('changed'):
            alerts.append(f"Direction changed: {dir_chg['previous']} -> {dir_chg['current']}")

        px = changes['price_change']
        if px.get('significant'):
            alerts.append(f"Price changed: {px['pct']:+.2f}% (now ${px['current']:.2f})")

        iv = changes['iv_change']
        if iv.get('rank_diff') is not None and abs(iv['rank_diff']) > 10:
            alerts.append(f"IV Rank changed sharply: {iv['previous_rank']:.0f} -> {iv['current_rank']:.0f}")

        strat = changes['strategy_change']
        if strat.get('changed'):
            alerts.append(f"Strategy changed: [{strat['previous_top']}] -> [{strat['current_top']}]")

        return alerts

    def _normalize_strategy_name(self, strategy_name: str) -> str:
        """Collapse legacy polluted labels into stable strategy names."""
        if not strategy_name:
            return 'None'

        normalized = str(strategy_name).strip()
        upper_name = normalized.upper()

        if 'OBSERVE' in upper_name or 'WAIT' in upper_name:
            return 'Observe / Wait'
        if 'LONG CALL' in upper_name:
            return 'Long Call'
        if 'LONG PUT' in upper_name:
            return 'Long Put'
        if 'SHORT CALL' in upper_name:
            return 'Short Call'
        if 'SHORT PUT' in upper_name:
            return 'Short Put'
        if 'BULL CALL SPREAD' in upper_name:
            return 'Bull Call Spread'
        if 'BEAR PUT SPREAD' in upper_name:
            return 'Bear Put Spread'
        if 'BULL PUT SPREAD' in upper_name:
            return 'Bull Put Spread'
        if 'BEAR CALL SPREAD' in upper_name:
            return 'Bear Call Spread'
        if 'IRON CONDOR' in upper_name:
            return 'Iron Condor'
        if 'CALENDAR' in upper_name:
            return 'Calendar Spread'

        return normalized
