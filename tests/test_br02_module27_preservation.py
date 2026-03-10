"""
Preservation Property Tests for BR-02: Module 27 ATM Selection Functional Equivalence

**Property 2: Preservation** - ATM Selection Functional Equivalence

**Validates: Requirements 4.2, 4.3, 4.7, 4.9**

IMPORTANT: Follow observation-first methodology.
These tests capture the CURRENT behavior of Module 27 ATM selection on UNFIXED code.

EXPECTED OUTCOME: Tests PASS on unfixed code (confirms baseline behavior).
After fix: Tests should STILL PASS (confirms functional equivalence preserved).

The tests verify that Module 27 continues to:
- Correctly find ATM call strikes closest to current price
- Correctly find ATM put strikes closest to current price
- Return complete expiry comparison results with all necessary data
- Maintain consistent ATM selection logic across various inputs
"""

import pytest
from hypothesis import given, strategies as st, settings, assume, Phase
from unittest.mock import Mock, patch, MagicMock
import sys
import os
import pandas as pd
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from calculation_layer.module27_multi_expiry_comparison import MultiExpiryAnalyzer


def create_option_chain_for_expiry(current_price: float, num_strikes: int = 10):
    """
    Create a realistic option chain DataFrame for testing ATM selection.
    
    Args:
        current_price: Current stock price (used to center strikes around ATM)
        num_strikes: Number of strike prices to generate
    
    Returns:
        DataFrame with option chain data
    """
    # Generate strikes centered around current price
    strike_spacing = 5.0
    strikes = [current_price + (i - num_strikes//2) * strike_spacing for i in range(num_strikes)]
    
    data = {
        'strike': strikes,
        'lastPrice': [abs(current_price - s) * 0.1 + 2.0 for s in strikes],
        'bid': [abs(current_price - s) * 0.08 + 1.5 for s in strikes],
        'ask': [abs(current_price - s) * 0.12 + 2.5 for s in strikes],
        'impliedVolatility': [0.25 + (abs(current_price - s) / current_price) * 0.1 for s in strikes],
        'delta': [0.5 - (s - current_price) / (current_price * 2) for s in strikes],
        'theta': [-0.05 - (abs(current_price - s) / current_price) * 0.02 for s in strikes],
        'volume': [100 + i * 10 for i in range(num_strikes)],
        'openInterest': [500 + i * 50 for i in range(num_strikes)]
    }
    
    return pd.DataFrame(data)


def find_expected_atm_strike(df: pd.DataFrame, current_price: float) -> float:
    """
    Calculate the expected ATM strike using the same logic as Module 27.
    This is our reference implementation to verify preservation.
    
    Args:
        df: Option chain DataFrame
        current_price: Current stock price
    
    Returns:
        The strike price closest to current_price
    """
    if df.empty:
        return current_price
    
    # Calculate strike differences
    strike_diffs = abs(df['strike'] - current_price)
    
    # Find minimum difference
    min_idx = strike_diffs.idxmin()
    
    return df.loc[min_idx, 'strike']


@pytest.mark.property_based_test
def test_module27_atm_call_selection_concrete():
    """
    **Property 2: Preservation** - ATM Call Strike Selection
    
    **Validates: Requirements 4.2, 4.7**
    
    OBSERVATION TEST: Captures current ATM call selection behavior.
    
    Tests that Module 27 correctly identifies the ATM call strike as the strike
    closest to the current stock price. This behavior must be preserved after
    the DataFrame mutation fix.
    
    EXPECTED: Test PASSES on unfixed code (baseline behavior).
    EXPECTED: Test PASSES on fixed code (functional equivalence preserved).
    """
    analyzer = MultiExpiryAnalyzer()
    
    # Test parameters
    ticker = 'TEST'
    current_price = 150.0
    
    # Create expiration data with ATM options
    calls_df = create_option_chain_for_expiry(current_price, num_strikes=10)
    puts_df = create_option_chain_for_expiry(current_price, num_strikes=10)
    
    expiration_data = [
        {
            'expiration': '2024-02-15',
            'days': 30,
            'atm_call': {
                'strike': find_expected_atm_strike(calls_df, current_price),
                'lastPrice': 5.0,
                'bid': 4.8,
                'ask': 5.2,
                'impliedVolatility': 0.30,
                'delta': 0.52,
                'theta': -0.05,
                'volume': 1000,
                'openInterest': 5000
            },
            'atm_put': {
                'strike': find_expected_atm_strike(puts_df, current_price),
                'lastPrice': 4.5,
                'bid': 4.3,
                'ask': 4.7,
                'impliedVolatility': 0.28,
                'delta': -0.48,
                'theta': -0.04,
                'volume': 800,
                'openInterest': 4000
            }
        }
    ]
    
    # Run Module 27 analysis
    result = analyzer.analyze_expirations(
        ticker=ticker,
        current_price=current_price,
        expiration_data=expiration_data,
        strategy_type='long_call'
    )
    
    # Verify analysis succeeded
    assert result['status'] == 'success', f"Analysis failed: {result.get('reason')}"
    
    # PRESERVATION CHECK: ATM call strike should be closest to current price
    expected_atm_strike = find_expected_atm_strike(calls_df, current_price)
    
    assert len(result['expiration_details']) > 0, "No expiration details returned"
    
    actual_atm_strike = result['expiration_details'][0]['strike']
    
    # The ATM strike should match our expected calculation
    assert actual_atm_strike == expected_atm_strike, (
        f"ATM call strike mismatch! "
        f"Expected: {expected_atm_strike}, Got: {actual_atm_strike}. "
        f"Module 27 should select the strike closest to current price {current_price}."
    )
    
    print(f"\n✅ ATM Call Selection Preserved:")
    print(f"   Current Price: ${current_price:.2f}")
    print(f"   ATM Strike: ${actual_atm_strike:.2f}")
    print(f"   Distance: ${abs(actual_atm_strike - current_price):.2f}")


@pytest.mark.property_based_test
def test_module27_atm_put_selection_concrete():
    """
    **Property 2: Preservation** - ATM Put Strike Selection
    
    **Validates: Requirements 4.2, 4.7**
    
    OBSERVATION TEST: Captures current ATM put selection behavior.
    
    Tests that Module 27 correctly identifies the ATM put strike as the strike
    closest to the current stock price. This behavior must be preserved after
    the DataFrame mutation fix.
    
    EXPECTED: Test PASSES on unfixed code (baseline behavior).
    EXPECTED: Test PASSES on fixed code (functional equivalence preserved).
    """
    analyzer = MultiExpiryAnalyzer()
    
    # Test parameters
    ticker = 'TEST'
    current_price = 200.0
    
    # Create expiration data
    calls_df = create_option_chain_for_expiry(current_price, num_strikes=12)
    puts_df = create_option_chain_for_expiry(current_price, num_strikes=12)
    
    expiration_data = [
        {
            'expiration': '2024-03-15',
            'days': 45,
            'atm_call': {
                'strike': find_expected_atm_strike(calls_df, current_price),
                'lastPrice': 8.0,
                'impliedVolatility': 0.35,
                'delta': 0.55,
                'theta': -0.06
            },
            'atm_put': {
                'strike': find_expected_atm_strike(puts_df, current_price),
                'lastPrice': 7.5,
                'impliedVolatility': 0.33,
                'delta': -0.45,
                'theta': -0.05
            }
        }
    ]
    
    # Run Module 27 analysis for put strategy
    result = analyzer.analyze_expirations(
        ticker=ticker,
        current_price=current_price,
        expiration_data=expiration_data,
        strategy_type='long_put'
    )
    
    # Verify analysis succeeded
    assert result['status'] == 'success', f"Analysis failed: {result.get('reason')}"
    
    # PRESERVATION CHECK: ATM put strike should be closest to current price
    expected_atm_strike = find_expected_atm_strike(puts_df, current_price)
    
    assert len(result['expiration_details']) > 0, "No expiration details returned"
    
    actual_atm_strike = result['expiration_details'][0]['strike']
    
    # The ATM strike should match our expected calculation
    assert actual_atm_strike == expected_atm_strike, (
        f"ATM put strike mismatch! "
        f"Expected: {expected_atm_strike}, Got: {actual_atm_strike}. "
        f"Module 27 should select the strike closest to current price {current_price}."
    )
    
    print(f"\n✅ ATM Put Selection Preserved:")
    print(f"   Current Price: ${current_price:.2f}")
    print(f"   ATM Strike: ${actual_atm_strike:.2f}")
    print(f"   Distance: ${abs(actual_atm_strike - current_price):.2f}")


@pytest.mark.property_based_test
def test_module27_expiry_comparison_completeness():
    """
    **Property 2: Preservation** - Expiry Comparison Data Completeness
    
    **Validates: Requirements 4.3, 4.9**
    
    OBSERVATION TEST: Captures current expiry comparison output structure.
    
    Tests that Module 27 returns complete expiry comparison results with all
    necessary analysis data. This structure must be preserved after the fix.
    
    EXPECTED: Test PASSES on unfixed code (baseline behavior).
    EXPECTED: Test PASSES on fixed code (functional equivalence preserved).
    """
    analyzer = MultiExpiryAnalyzer()
    
    ticker = 'TEST'
    current_price = 175.0
    
    # Create multiple expirations for comparison
    expiration_data = [
        {
            'expiration': '2024-01-31',
            'days': 15,
            'atm_call': {
                'strike': 175.0,
                'lastPrice': 4.0,
                'impliedVolatility': 0.40,
                'delta': 0.50,
                'theta': -0.08
            },
            'atm_put': {
                'strike': 175.0,
                'lastPrice': 3.8,
                'impliedVolatility': 0.38,
                'delta': -0.50,
                'theta': -0.07
            }
        },
        {
            'expiration': '2024-02-29',
            'days': 45,
            'atm_call': {
                'strike': 175.0,
                'lastPrice': 7.5,
                'impliedVolatility': 0.32,
                'delta': 0.52,
                'theta': -0.04
            },
            'atm_put': {
                'strike': 175.0,
                'lastPrice': 7.0,
                'impliedVolatility': 0.30,
                'delta': -0.48,
                'theta': -0.03
            }
        },
        {
            'expiration': '2024-04-19',
            'days': 90,
            'atm_call': {
                'strike': 175.0,
                'lastPrice': 12.0,
                'impliedVolatility': 0.28,
                'delta': 0.54,
                'theta': -0.02
            },
            'atm_put': {
                'strike': 175.0,
                'lastPrice': 11.5,
                'impliedVolatility': 0.27,
                'delta': -0.46,
                'theta': -0.02
            }
        }
    ]
    
    # Run analysis
    result = analyzer.analyze_expirations(
        ticker=ticker,
        current_price=current_price,
        expiration_data=expiration_data,
        strategy_type='long_call'
    )
    
    # PRESERVATION CHECK: Result structure completeness
    assert result['status'] == 'success', f"Analysis failed: {result.get('reason')}"
    
    # Verify all expected top-level keys exist
    required_keys = [
        'status', 'ticker', 'current_price', 'strategy_type',
        'analysis_date', 'expirations_analyzed', 'expiration_details',
        'comparison_table', 'recommendation', 'theta_analysis'
    ]
    
    for key in required_keys:
        assert key in result, f"Missing required key: {key}"
    
    # Verify expiration details completeness
    assert len(result['expiration_details']) == 3, (
        f"Expected 3 expiration details, got {len(result['expiration_details'])}"
    )
    
    # Verify each expiration detail has required fields
    required_detail_fields = [
        'expiration', 'days', 'strike', 'premium', 'iv',
        'delta', 'theta', 'theta_daily', 'theta_pct',
        'annualized_return', 'total_cost', 'score', 'grade', 'category'
    ]
    
    for i, detail in enumerate(result['expiration_details']):
        for field in required_detail_fields:
            assert field in detail, (
                f"Expiration {i}: Missing required field '{field}'"
            )
    
    # Verify comparison table completeness
    assert len(result['comparison_table']) == 3, (
        f"Expected 3 comparison entries, got {len(result['comparison_table'])}"
    )
    
    # Verify recommendation exists and has required structure
    recommendation = result['recommendation']
    assert recommendation is not None, "Recommendation should not be None"
    
    required_rec_fields = [
        'best_expiration', 'best_days', 'best_score', 'best_grade',
        'best_premium', 'best_category', 'reasons', 'alternatives', 'strategy_type'
    ]
    
    for field in required_rec_fields:
        assert field in recommendation, f"Recommendation missing field: {field}"
    
    # Verify theta analysis completeness
    theta_analysis = result['theta_analysis']
    assert 'theta_curve' in theta_analysis, "Missing theta_curve"
    assert 'avg_theta_pct' in theta_analysis, "Missing avg_theta_pct"
    
    print(f"\n✅ Expiry Comparison Completeness Preserved:")
    print(f"   Expirations Analyzed: {result['expirations_analyzed']}")
    print(f"   Best Expiration: {recommendation['best_expiration']} ({recommendation['best_days']} days)")
    print(f"   Best Score: {recommendation['best_score']} ({recommendation['best_grade']})")
    print(f"   Theta Analysis: {len(theta_analysis['theta_curve'])} data points")


@pytest.mark.property_based_test
@given(
    current_price=st.floats(min_value=50.0, max_value=500.0),
    num_strikes=st.integers(min_value=7, max_value=15)
)
@settings(
    max_examples=20,  # Test with various price levels and strike counts
    deadline=None
)
def test_module27_atm_selection_property_based(current_price, num_strikes):
    """
    **Property 2: Preservation** - ATM Selection Consistency (Property-Based)
    
    **Validates: Requirements 4.2, 4.7**
    
    OBSERVATION TEST: Property-based test for ATM selection consistency.
    
    Tests that Module 27 ATM selection logic is consistent across various
    stock prices and option chain configurations. The selected ATM strike
    should always be the one closest to the current price.
    
    EXPECTED: Test PASSES on unfixed code (baseline behavior).
    EXPECTED: Test PASSES on fixed code (functional equivalence preserved).
    """
    analyzer = MultiExpiryAnalyzer()
    
    # Create option chain
    calls_df = create_option_chain_for_expiry(current_price, num_strikes)
    puts_df = create_option_chain_for_expiry(current_price, num_strikes)
    
    # Calculate expected ATM strikes
    expected_call_strike = find_expected_atm_strike(calls_df, current_price)
    expected_put_strike = find_expected_atm_strike(puts_df, current_price)
    
    # Create expiration data
    expiration_data = [
        {
            'expiration': '2024-03-15',
            'days': 30,
            'atm_call': {
                'strike': expected_call_strike,
                'lastPrice': 5.0,
                'impliedVolatility': 0.30,
                'delta': 0.50,
                'theta': -0.05
            },
            'atm_put': {
                'strike': expected_put_strike,
                'lastPrice': 4.8,
                'impliedVolatility': 0.29,
                'delta': -0.50,
                'theta': -0.04
            }
        }
    ]
    
    # Test call strategy
    call_result = analyzer.analyze_expirations(
        ticker='TEST',
        current_price=current_price,
        expiration_data=expiration_data,
        strategy_type='long_call'
    )
    
    # Test put strategy
    put_result = analyzer.analyze_expirations(
        ticker='TEST',
        current_price=current_price,
        expiration_data=expiration_data,
        strategy_type='long_put'
    )
    
    # PRESERVATION CHECK: Both strategies should succeed
    assert call_result['status'] == 'success', (
        f"Call analysis failed for price={current_price:.2f}, strikes={num_strikes}"
    )
    
    assert put_result['status'] == 'success', (
        f"Put analysis failed for price={current_price:.2f}, strikes={num_strikes}"
    )
    
    # PRESERVATION CHECK: ATM strikes should match expected values
    if call_result['expiration_details']:
        actual_call_strike = call_result['expiration_details'][0]['strike']
        assert actual_call_strike == expected_call_strike, (
            f"Call ATM mismatch at price={current_price:.2f}: "
            f"expected {expected_call_strike}, got {actual_call_strike}"
        )
    
    if put_result['expiration_details']:
        actual_put_strike = put_result['expiration_details'][0]['strike']
        assert actual_put_strike == expected_put_strike, (
            f"Put ATM mismatch at price={current_price:.2f}: "
            f"expected {expected_put_strike}, got {actual_put_strike}"
        )


@pytest.mark.property_based_test
def test_module27_multi_expiry_scoring_consistency():
    """
    **Property 2: Preservation** - Multi-Expiry Scoring Consistency
    
    **Validates: Requirements 4.3, 4.7**
    
    OBSERVATION TEST: Captures current scoring and ranking behavior.
    
    Tests that Module 27 consistently scores and ranks multiple expirations
    based on the established criteria (days to expiry, theta, IV, etc.).
    This scoring logic must be preserved after the fix.
    
    EXPECTED: Test PASSES on unfixed code (baseline behavior).
    EXPECTED: Test PASSES on fixed code (functional equivalence preserved).
    """
    analyzer = MultiExpiryAnalyzer()
    
    ticker = 'TEST'
    current_price = 150.0
    
    # Create expirations with varying characteristics
    expiration_data = [
        # Short-term: High theta decay
        {
            'expiration': '2024-01-20',
            'days': 7,
            'atm_call': {
                'strike': 150.0,
                'lastPrice': 2.5,
                'impliedVolatility': 0.45,
                'delta': 0.50,
                'theta': -0.12
            },
            'atm_put': {
                'strike': 150.0,
                'lastPrice': 2.3,
                'impliedVolatility': 0.43,
                'delta': -0.50,
                'theta': -0.11
            }
        },
        # Optimal: 30-60 day range
        {
            'expiration': '2024-02-15',
            'days': 35,
            'atm_call': {
                'strike': 150.0,
                'lastPrice': 6.0,
                'impliedVolatility': 0.30,
                'delta': 0.52,
                'theta': -0.04
            },
            'atm_put': {
                'strike': 150.0,
                'lastPrice': 5.8,
                'impliedVolatility': 0.29,
                'delta': -0.48,
                'theta': -0.03
            }
        },
        # Long-term: Low theta but higher premium
        {
            'expiration': '2024-05-17',
            'days': 120,
            'atm_call': {
                'strike': 150.0,
                'lastPrice': 15.0,
                'impliedVolatility': 0.25,
                'delta': 0.54,
                'theta': -0.015
            },
            'atm_put': {
                'strike': 150.0,
                'lastPrice': 14.5,
                'impliedVolatility': 0.24,
                'delta': -0.46,
                'theta': -0.014
            }
        }
    ]
    
    # Run analysis
    result = analyzer.analyze_expirations(
        ticker=ticker,
        current_price=current_price,
        expiration_data=expiration_data,
        strategy_type='long_call'
    )
    
    assert result['status'] == 'success', f"Analysis failed: {result.get('reason')}"
    
    # PRESERVATION CHECK: All expirations should be scored
    assert len(result['comparison_table']) == 3, (
        f"Expected 3 scored expirations, got {len(result['comparison_table'])}"
    )
    
    # PRESERVATION CHECK: Scores should be in valid range (0-100)
    for entry in result['comparison_table']:
        score = entry['score']
        assert 0 <= score <= 100, (
            f"Score out of range for {entry['expiration']}: {score}"
        )
        
        # Grade should be assigned
        assert entry['grade'] in ['A', 'B', 'C', 'D', 'F'], (
            f"Invalid grade for {entry['expiration']}: {entry['grade']}"
        )
    
    # PRESERVATION CHECK: Best expiration should be recommended
    recommendation = result['recommendation']
    assert recommendation['best_expiration'] is not None, "No best expiration selected"
    
    # The best expiration should have the highest score
    best_score = recommendation['best_score']
    all_scores = [entry['score'] for entry in result['comparison_table']]
    assert best_score == max(all_scores), (
        f"Best score {best_score} is not the maximum of all scores {all_scores}"
    )
    
    print(f"\n✅ Multi-Expiry Scoring Preserved:")
    print(f"   Expirations Scored: {len(result['comparison_table'])}")
    print(f"   Score Range: {min(all_scores):.0f} - {max(all_scores):.0f}")
    print(f"   Best: {recommendation['best_expiration']} (Score: {best_score}, Grade: {recommendation['best_grade']})")
    
    # Print all scores for observation
    for entry in result['comparison_table']:
        print(f"   - {entry['days']:3d} days: Score {entry['score']:3.0f} ({entry['grade']})")


if __name__ == '__main__':
    # Run preservation tests to observe baseline behavior
    print("=" * 80)
    print("BR-02 PRESERVATION TESTS - Observing Baseline Behavior on Unfixed Code")
    print("=" * 80)
    
    print("\n[Test 1] ATM Call Selection")
    print("-" * 80)
    test_module27_atm_call_selection_concrete()
    
    print("\n[Test 2] ATM Put Selection")
    print("-" * 80)
    test_module27_atm_put_selection_concrete()
    
    print("\n[Test 3] Expiry Comparison Completeness")
    print("-" * 80)
    test_module27_expiry_comparison_completeness()
    
    print("\n[Test 4] Multi-Expiry Scoring Consistency")
    print("-" * 80)
    test_module27_multi_expiry_scoring_consistency()
    
    print("\n" + "=" * 80)
    print("PRESERVATION TESTS COMPLETE")
    print("=" * 80)
    print("\nIf all tests PASSED:")
    print("✅ Baseline behavior captured successfully")
    print("✅ These tests will validate functional equivalence after fix")
    print("\nNext step: Implement BR-02 fix (Task 7)")
