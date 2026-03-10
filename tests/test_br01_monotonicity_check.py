"""
Checkpoint Test for BR-01: Verify Progress Monotonicity

This test verifies that progress output is monotonic (1/28 to 28/28)
and that all progress calls use the unified TOTAL_ANALYSIS_STEPS constant.
"""

import pytest
from unittest.mock import patch
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import OptionsAnalysisSystem
from calculation_layer.workflow_config import TOTAL_ANALYSIS_STEPS


class ProgressMonotonicityTracker:
    """Helper class to track progress monotonicity"""
    def __init__(self):
        self.calls = []
        self.percentages = []
    
    def callback(self, step, total, message, module_name=None):
        self.calls.append({
            'step': step,
            'total': total,
            'message': message,
            'module_name': module_name
        })
        if total and total > 0:
            percentage = (step / total) * 100
            self.percentages.append(percentage)


def test_progress_monotonicity():
    """
    Verify that progress percentages are monotonically increasing.
    
    Expected behavior after BR-01 fix:
    - All progress calls use TOTAL_ANALYSIS_STEPS (28)
    - Progress goes from 0/28 (0%) to 28/28 (100%)
    - Percentages never decrease
    """
    analyzer = OptionsAnalysisSystem()
    tracker = ProgressMonotonicityTracker()
    
    with patch.object(analyzer, 'fetcher') as mock_fetcher, \
         patch.object(analyzer, 'validator') as mock_validator, \
         patch('main.logger'):
        
        mock_fetcher.get_complete_analysis_data.return_value = {
            'stock_price': 100.0,
            'current_price': 100.0,
            'eps': 5.0,
            'pe_ratio': 20.0,
            'forward_pe': 18.0,
            'calls': [],
            'puts': [],
            'risk_free_rate': 0.05,
            'dividend_yield': 0.02,
            'implied_volatility': 25.0,
            'option_chain': {'calls': [], 'puts': []},
            'days_to_expiration': 30,
            'expiration_date': '2024-12-31',
            'analysis_date': '2024-01-01'
        }
        mock_validator.validate_stock_data.return_value = True
        
        try:
            analyzer.run_complete_analysis(
                ticker='TEST',
                expiration='2024-12-31',
                progress_callback=tracker.callback,
                selected_expirations=['2024-12-31']
            )
        except Exception:
            pass
    
    # Verify all calls use TOTAL_ANALYSIS_STEPS
    total_values = [call['total'] for call in tracker.calls if call['total'] is not None]
    unique_totals = set(total_values)
    
    print(f"\n=== Progress Monotonicity Check ===")
    print(f"TOTAL_ANALYSIS_STEPS: {TOTAL_ANALYSIS_STEPS}")
    print(f"Unique total values found: {sorted(unique_totals)}")
    print(f"Total progress calls: {len(tracker.calls)}")
    
    assert len(unique_totals) == 1, f"Expected all calls to use same total, found: {sorted(unique_totals)}"
    assert TOTAL_ANALYSIS_STEPS in unique_totals, f"Expected total={TOTAL_ANALYSIS_STEPS}, found: {sorted(unique_totals)}"
    
    # Verify monotonicity
    print(f"\n=== Monotonicity Verification ===")
    print(f"First 5 percentages: {tracker.percentages[:5]}")
    print(f"Last 5 percentages: {tracker.percentages[-5:]}")
    
    for i in range(1, len(tracker.percentages)):
        prev_pct = tracker.percentages[i-1]
        curr_pct = tracker.percentages[i]
        
        if curr_pct < prev_pct:
            print(f"\n❌ NON-MONOTONIC: Progress decreased from {prev_pct:.1f}% to {curr_pct:.1f}%")
            print(f"   Call {i-1}: step={tracker.calls[i-1]['step']}, total={tracker.calls[i-1]['total']}")
            print(f"   Call {i}: step={tracker.calls[i]['step']}, total={tracker.calls[i]['total']}")
            assert False, f"Progress is not monotonic: {prev_pct:.1f}% -> {curr_pct:.1f}%"
    
    print(f"\n✅ Progress is monotonic: {tracker.percentages[0]:.1f}% to {tracker.percentages[-1]:.1f}%")
    
    # Verify range
    assert tracker.percentages[0] >= 0, "Progress should start at or above 0%"
    assert tracker.percentages[-1] <= 100, "Progress should not exceed 100%"
    
    print(f"✅ All checks passed!")


if __name__ == '__main__':
    test_progress_monotonicity()
