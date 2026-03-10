"""
Bug Condition Exploration Test for BR-01: Progress Total Inconsistency

**Validates: Requirements 3.1, 3.4, 3.8**

This test is designed to FAIL on unfixed code to confirm the bug exists.
It verifies that all report_progress() calls use inconsistent total values.

CRITICAL: This test MUST FAIL on unfixed code - failure confirms the bug exists.
DO NOT attempt to fix the test or the code when it fails.

Expected counterexample: Module 32 uses total=40 while other modules use total=28
"""

import pytest
from hypothesis import given, strategies as st, settings, assume, Phase
from unittest.mock import Mock, patch
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import OptionsAnalysisSystem


class ProgressTracker:
    """Helper class to track all progress report calls"""
    def __init__(self):
        self.calls = []
    
    def callback(self, step, total, message, module_name=None):
        self.calls.append({
            'step': step,
            'total': total,
            'message': message,
            'module_name': module_name
        })


@pytest.mark.property_based_test
def test_progress_total_inconsistency_detection():
    """
    **Property 1: Bug Condition** - Progress Total Inconsistency Detection
    
    **Validates: Requirements 3.1, 3.4, 3.8**
    
    CRITICAL: This test MUST FAIL on unfixed code.
    
    Tests that all report_progress() calls in the main analysis workflow
    use the same total parameter value. On unfixed code, this will fail
    because Module 32 uses total=40 while other modules use total=28.
    
    Expected counterexample on unfixed code:
    - Most modules: total=28
    - Module 32: total=40 (at step 30)
    """
    # Create analyzer with mocked dependencies
    analyzer = OptionsAnalysisSystem()
    
    # Set up progress tracker
    tracker = ProgressTracker()
    
    # Mock all external dependencies to isolate progress reporting
    with patch.object(analyzer, 'fetcher') as mock_fetcher, \
         patch.object(analyzer, 'validator') as mock_validator, \
         patch('main.logger'):
        
        # Configure mocks to return minimal valid data
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
            # Run analysis with progress tracking
            # This will trigger all report_progress calls
            analyzer.run_complete_analysis(
                ticker='TEST',
                expiration='2024-12-31',
                progress_callback=tracker.callback,
                selected_expirations=['2024-12-31']
            )
        except Exception:
            # Analysis may fail due to mocking, but we only care about progress calls
            pass
    
    # Extract all total values from progress calls
    total_values = [call['total'] for call in tracker.calls if call['total'] is not None]
    
    # Bug Condition: Check if there are inconsistent total values
    unique_totals = set(total_values)
    
    # Document the counterexamples found
    if len(unique_totals) > 1:
        print("\n=== BUG DETECTED: Inconsistent Progress Totals ===")
        print(f"Found {len(unique_totals)} different total values: {sorted(unique_totals)}")
        
        # Group calls by total value to show the inconsistency
        by_total = {}
        for call in tracker.calls:
            total = call['total']
            if total not in by_total:
                by_total[total] = []
            by_total[total].append(call)
        
        for total, calls in sorted(by_total.items()):
            print(f"\nCalls with total={total}:")
            for call in calls[:3]:  # Show first 3 examples
                print(f"  - Step {call['step']}: {call['module_name'] or call['message']}")
            if len(calls) > 3:
                print(f"  ... and {len(calls) - 3} more")
        
        print("\n=== Expected Counterexample ===")
        print("Module 32 should use total=40 while others use total=28")
        print("This confirms the bug exists in the unfixed code.")
    
    # ASSERTION: All progress calls should use the same total
    # This will FAIL on unfixed code (which is correct - it proves the bug exists)
    assert len(unique_totals) == 1, (
        f"Progress total inconsistency detected! "
        f"Found {len(unique_totals)} different total values: {sorted(unique_totals)}. "
        f"All report_progress() calls should use the same total value. "
        f"Counterexample: {by_total if len(unique_totals) > 1 else 'N/A'}"
    )
    
    # If we reach here on unfixed code, something is wrong with the test
    print("WARNING: Test passed on unfixed code - bug may not exist or test needs adjustment")


@pytest.mark.property_based_test
@given(
    ticker=st.sampled_from(['AAPL', 'MSFT', 'GOOGL', 'TEST']),
    expiration=st.sampled_from(['2024-12-31', '2025-01-31', '2025-03-31'])
)
@settings(
    max_examples=5,  # Run a few examples to confirm consistency
    phases=[Phase.generate, Phase.target],  # Skip shrinking for exploration
    deadline=None  # No time limit for this exploration test
)
def test_progress_total_consistency_property(ticker, expiration):
    """
    **Property 1: Bug Condition** - Progress Total Inconsistency (Property-Based)
    
    **Validates: Requirements 3.1, 3.4, 3.8**
    
    Property-based version that tests with multiple ticker/expiration combinations.
    This should fail consistently on unfixed code regardless of input.
    """
    analyzer = OptionsAnalysisSystem()
    tracker = ProgressTracker()
    
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
                ticker=ticker,
                expiration=expiration,
                progress_callback=tracker.callback,
                selected_expirations=[expiration]
            )
        except Exception:
            pass
    
    total_values = [call['total'] for call in tracker.calls if call['total'] is not None]
    unique_totals = set(total_values)
    
    # Expected behavior: All calls should use the same total
    # This will FAIL on unfixed code
    assert len(unique_totals) == 1, (
        f"Progress total inconsistency for {ticker}/{expiration}! "
        f"Found totals: {sorted(unique_totals)}"
    )


if __name__ == '__main__':
    # Run the exploration test directly
    print("Running Bug Condition Exploration Test for BR-01...")
    print("=" * 70)
    test_progress_total_inconsistency_detection()
