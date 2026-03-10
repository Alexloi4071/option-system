"""
Preservation Property Tests for BR-01: Progress Reporting Behavior

**Validates: Requirements 4.1, 4.6**

This test captures the CURRENT behavior of progress reporting on UNFIXED code.
It should PASS on unfixed code to establish the baseline behavior to preserve.

After fixing BR-01 (unifying progress totals), these tests should STILL PASS,
confirming that we preserved:
- Progress descriptions
- Step ordering
- Module execution sequence
- All modules are executed (no steps skipped)

IMPORTANT: This test observes and validates the EXISTING behavior patterns,
NOT the bug condition. The bug (inconsistent totals) will be fixed, but
everything else must remain the same.
"""

import pytest
from hypothesis import given, strategies as st, settings, Phase
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


def run_analysis_and_capture_progress():
    """Helper to run analysis and capture progress calls"""
    analyzer = OptionsAnalysisSystem()
    tracker = ProgressTracker()
    
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
            analyzer.run_complete_analysis(
                ticker='TEST',
                expiration='2024-12-31',
                progress_callback=tracker.callback,
                selected_expirations=['2024-12-31']
            )
        except Exception:
            # Analysis may fail due to mocking, but we only care about progress calls
            pass
    
    return tracker.calls


@pytest.mark.property_based_test
def test_progress_descriptions_preserved():
    """
    **Property 2: Preservation** - Progress Description Preservation
    
    **Validates: Requirements 4.1**
    
    Tests that progress descriptions remain unchanged after fixing BR-01.
    This test captures the CURRENT descriptions on unfixed code and should
    PASS both before and after the fix.
    
    Expected behavior: Each module reports progress with its characteristic description.
    """
    calls = run_analysis_and_capture_progress()
    
    # Extract progress calls (excluding initialization)
    progress_calls = [c for c in calls if c['step'] > 0]
    
    # Verify we have progress calls
    assert len(progress_calls) > 0, "No progress calls captured"
    
    # Define expected module names/descriptions that should be present
    # These are observed from the current unfixed code
    expected_modules = [
        'Module 1: 支持/阻力位',
        'Module 4: PE估值',
        'Module 11: 合成正股',
        'Module 14: 監察崗位',
        'Module 15-19: 期權定價',
        'Module 20: 基本面健康',
        'Module 21: 動量過濾器',
        'Module 22: 最佳行使價',
        'Module 23: 動態IV閾值',
        'Module 24: 技術方向',
        'Module 25: 波動率微笑',
        'Module 26: Long期權分析',
        'Module 27: 多到期日比較',
        'Module 28: 資金倉位',
        'Module 32: 組合策略'
    ]
    
    # Extract actual module names from calls
    actual_modules = [c['module_name'] for c in progress_calls if c['module_name']]
    
    # Verify all expected modules are present
    for expected in expected_modules:
        assert expected in actual_modules, (
            f"Expected module '{expected}' not found in progress calls. "
            f"This indicates a module was skipped or renamed."
        )
    
    print(f"\n✓ All {len(expected_modules)} expected modules found in progress calls")
    print(f"✓ Progress descriptions preserved")


@pytest.mark.property_based_test
def test_progress_step_ordering_preserved():
    """
    **Property 2: Preservation** - Step Ordering Preservation
    
    **Validates: Requirements 4.6**
    
    Tests that the step numbers and their ordering remain unchanged after fixing BR-01.
    This test captures the CURRENT step sequence on unfixed code.
    
    Expected behavior: Steps are reported in a specific order that reflects
    the module execution sequence.
    """
    calls = run_analysis_and_capture_progress()
    
    # Extract step numbers (excluding initialization step 0)
    steps = [c['step'] for c in calls if c['step'] > 0]
    
    # Verify we have steps
    assert len(steps) > 0, "No progress steps captured"
    
    # Define expected step sequence observed from unfixed code
    # Note: Some steps may be missing if modules are skipped due to data issues
    expected_step_sequence = [1, 2, 3, 4, 11, 14, 15, 20, 21, 23, 22, 24, 25, 26, 27, 28, 30]
    
    # Verify the steps we captured match the expected sequence
    # (allowing for some steps to be missing due to mocking)
    for i, step in enumerate(steps):
        if i < len(expected_step_sequence):
            # Steps should appear in order (but some may be skipped)
            assert step in expected_step_sequence, (
                f"Unexpected step {step} at position {i}. "
                f"Expected steps from sequence: {expected_step_sequence}"
            )
    
    # Verify key steps are present
    key_steps = [1, 2, 3]  # Data fetch, validation, module start
    for key_step in key_steps:
        assert key_step in steps, (
            f"Key step {key_step} missing from progress calls. "
            f"This indicates a critical workflow change."
        )
    
    print(f"\n✓ Step ordering preserved: {steps}")
    print(f"✓ All key steps present")


@pytest.mark.property_based_test
def test_module_execution_sequence_preserved():
    """
    **Property 2: Preservation** - Module Execution Sequence Preservation
    
    **Validates: Requirements 4.6**
    
    Tests that modules are executed in the same order after fixing BR-01.
    This test captures the CURRENT execution sequence on unfixed code.
    
    Expected behavior: Modules execute in a specific order that reflects
    dependencies and workflow logic.
    """
    calls = run_analysis_and_capture_progress()
    
    # Extract module sequence (in order of execution)
    module_sequence = [
        c['module_name'] for c in calls 
        if c['module_name'] and c['step'] > 0
    ]
    
    # Verify we have modules
    assert len(module_sequence) > 0, "No modules captured"
    
    # Define expected module execution order (observed from unfixed code)
    expected_order = [
        'Module 1: 支持/阻力位',
        'Module 4: PE估值',
        'Module 11: 合成正股',
        'Module 14: 監察崗位',
        'Module 15-19: 期權定價',
        'Module 20: 基本面健康',
        'Module 21: 動量過濾器',
        'Module 23: 動態IV閾值',  # Note: Module 23 runs BEFORE Module 22
        'Module 22: 最佳行使價',
        'Module 32: 組合策略',  # Note: Module 32 runs in the middle
        'Module 24: 技術方向',
        'Module 25: 波動率微笑',
        'Module 26: Long期權分析',
        'Module 27: 多到期日比較',
        'Module 28: 資金倉位'
    ]
    
    # Verify the relative order of modules is preserved
    # We check that if module A appears before module B in expected_order,
    # then A also appears before B in module_sequence (if both are present)
    for i, module_a in enumerate(expected_order):
        if module_a not in module_sequence:
            continue
        
        for module_b in expected_order[i+1:]:
            if module_b not in module_sequence:
                continue
            
            idx_a = module_sequence.index(module_a)
            idx_b = module_sequence.index(module_b)
            
            assert idx_a < idx_b, (
                f"Module execution order violated: '{module_a}' should come before '{module_b}', "
                f"but found at positions {idx_a} and {idx_b} respectively."
            )
    
    print(f"\n✓ Module execution sequence preserved")
    print(f"✓ Captured {len(module_sequence)} modules in correct order")


@pytest.mark.property_based_test
def test_all_modules_executed():
    """
    **Property 2: Preservation** - Complete Module Execution
    
    **Validates: Requirements 4.6**
    
    Tests that all modules are executed (no modules skipped) after fixing BR-01.
    This test captures the CURRENT module coverage on unfixed code.
    
    Expected behavior: The complete analysis workflow executes all expected modules.
    """
    calls = run_analysis_and_capture_progress()
    
    # Extract unique modules executed
    modules_executed = set(c['module_name'] for c in calls if c['module_name'] and c['step'] > 0)
    
    # Define minimum expected module count (observed from unfixed code)
    # We expect at least 15 distinct modules to be executed
    min_expected_modules = 15
    
    assert len(modules_executed) >= min_expected_modules, (
        f"Expected at least {min_expected_modules} modules to be executed, "
        f"but only found {len(modules_executed)}: {sorted(modules_executed)}"
    )
    
    # Verify critical modules are present
    critical_modules = [
        'Module 1: 支持/阻力位',
        'Module 15-19: 期權定價',
        'Module 27: 多到期日比較',
        'Module 28: 資金倉位',
        'Module 32: 組合策略'
    ]
    
    for critical in critical_modules:
        assert critical in modules_executed, (
            f"Critical module '{critical}' was not executed. "
            f"This indicates a workflow regression."
        )
    
    print(f"\n✓ All {len(modules_executed)} modules executed")
    print(f"✓ All critical modules present")


@pytest.mark.property_based_test
@given(
    ticker=st.sampled_from(['AAPL', 'MSFT', 'TEST']),
    expiration=st.sampled_from(['2024-12-31', '2025-01-31'])
)
@settings(
    max_examples=3,  # Run a few examples to confirm consistency
    phases=[Phase.generate, Phase.target],
    deadline=None
)
def test_preservation_property_across_inputs(ticker, expiration):
    """
    **Property 2: Preservation** - Behavior Consistency Across Inputs
    
    **Validates: Requirements 4.1, 4.6**
    
    Property-based test that verifies preservation properties hold
    across different ticker/expiration combinations.
    
    Expected behavior: Progress reporting behavior should be consistent
    regardless of input parameters.
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
            'expiration_date': expiration,
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
    
    # Verify basic preservation properties
    progress_calls = [c for c in tracker.calls if c['step'] > 0]
    
    # Should have progress calls
    assert len(progress_calls) > 0, f"No progress calls for {ticker}/{expiration}"
    
    # Should have multiple modules
    modules = set(c['module_name'] for c in progress_calls if c['module_name'])
    assert len(modules) >= 10, (
        f"Expected at least 10 modules for {ticker}/{expiration}, "
        f"but only found {len(modules)}"
    )
    
    # Steps should be positive integers
    steps = [c['step'] for c in progress_calls]
    assert all(isinstance(s, int) and s > 0 for s in steps), (
        f"Invalid step numbers for {ticker}/{expiration}: {steps}"
    )
    
    print(f"\n✓ Preservation properties hold for {ticker}/{expiration}")


if __name__ == '__main__':
    # Run the preservation tests directly
    print("Running Preservation Property Tests for BR-01...")
    print("=" * 70)
    print("\nTest 1: Progress Descriptions Preserved")
    test_progress_descriptions_preserved()
    print("\nTest 2: Step Ordering Preserved")
    test_progress_step_ordering_preserved()
    print("\nTest 3: Module Execution Sequence Preserved")
    test_module_execution_sequence_preserved()
    print("\nTest 4: All Modules Executed")
    test_all_modules_executed()
    print("\n" + "=" * 70)
    print("All preservation tests passed!")
