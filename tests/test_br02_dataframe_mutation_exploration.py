"""
Bug Condition Exploration Test for BR-02: DataFrame Schema Pollution

**Property 1: Bug Condition** - DataFrame Schema Pollution Detection

**Validates: Requirements 3.2, 3.5, 3.6**

This test is designed to FAIL on unfixed code to confirm the bug exists.
It verifies that Module 27 ATM selection mutates the shared calls_df and puts_df
DataFrames by adding temporary columns like 'strike_diff'.

CRITICAL: This test MUST FAIL on unfixed code - failure confirms the bug exists.
DO NOT attempt to fix the test or the code when it fails.

Expected counterexample: calls_df and puts_df gain 'strike_diff' column after
Module 27 ATM selection logic executes.

NOTE: This test encodes the expected behavior - it will validate the fix when
it passes after implementation.
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

from main import OptionsAnalysisSystem


def create_sample_option_chain(current_price: float, num_strikes: int = 10):
    """
    Create a sample option chain DataFrame for testing.
    
    Args:
        current_price: Current stock price
        num_strikes: Number of strike prices to generate
    
    Returns:
        DataFrame with option chain data
    """
    strikes = [current_price + (i - num_strikes//2) * 5 for i in range(num_strikes)]
    
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


@pytest.mark.property_based_test
def test_dataframe_mutation_detection_concrete():
    """
    **Property 1: Bug Condition** - DataFrame Schema Pollution Detection
    
    **Validates: Requirements 3.2, 3.5, 3.6**
    
    CRITICAL: This test MUST FAIL on unfixed code.
    
    Tests that Module 27 ATM selection logic does NOT mutate the original
    calls_df and puts_df DataFrames. On unfixed code, this will fail because
    the code directly adds 'strike_diff' column to the shared DataFrames.
    
    Expected counterexample on unfixed code:
    - Before: calls_df.columns = ['strike', 'lastPrice', 'bid', 'ask', ...]
    - After: calls_df.columns includes 'strike_diff' (POLLUTION!)
    
    GOAL: Surface counterexamples demonstrating in-place DataFrame mutation.
    SCOPED PBT APPROACH: Test Module 27 ATM selection with any valid option chain.
    """
    # Create analyzer
    analyzer = OptionsAnalysisSystem()
    
    # Test parameters
    ticker = 'TEST'
    current_price = 150.0
    expiration = '2024-12-31'
    
    # Create sample option chains
    calls_df_original = create_sample_option_chain(current_price, num_strikes=10)
    puts_df_original = create_sample_option_chain(current_price, num_strikes=10)
    
    # Capture original schemas
    original_calls_columns = set(calls_df_original.columns)
    original_puts_columns = set(puts_df_original.columns)
    
    print("\n=== Original DataFrame Schemas ===")
    print(f"calls_df columns: {sorted(original_calls_columns)}")
    print(f"puts_df columns: {sorted(original_puts_columns)}")
    
    # Mock the fetcher to return our test DataFrames
    with patch.object(analyzer, 'fetcher') as mock_fetcher, \
         patch.object(analyzer, 'validator') as mock_validator, \
         patch('main.logger'):
        
        # Configure mocks
        mock_fetcher.get_option_expirations.return_value = [expiration]
        
        # Create a mock that returns our DataFrames
        # IMPORTANT: We need to return the SAME DataFrame objects to detect mutation
        mock_fetcher.get_option_chain.return_value = {
            'calls': calls_df_original,
            'puts': puts_df_original
        }
        
        mock_fetcher.get_complete_analysis_data.return_value = {
            'stock_price': current_price,
            'current_price': current_price,
            'eps': 5.0,
            'pe_ratio': 20.0,
            'forward_pe': 18.0,
            'calls': [],
            'puts': [],
            'risk_free_rate': 0.05,
            'dividend_yield': 0.02,
            'implied_volatility': 25.0,
            'option_chain': {'calls': calls_df_original, 'puts': puts_df_original},
            'days_to_expiration': 30,
            'expiration_date': expiration,
            'analysis_date': '2024-01-01'
        }
        
        mock_validator.validate_stock_data.return_value = True
        
        try:
            # Run the analysis - this will trigger Module 27 ATM selection
            analyzer.run_complete_analysis(
                ticker=ticker,
                expiration=expiration,
                selected_expirations=[expiration]
            )
        except Exception as e:
            # Analysis may fail due to mocking, but we only care about DataFrame mutation
            print(f"Analysis failed (expected): {e}")
            pass
    
    # Check if DataFrames were mutated
    current_calls_columns = set(calls_df_original.columns)
    current_puts_columns = set(puts_df_original.columns)
    
    print("\n=== Current DataFrame Schemas (After Module 27) ===")
    print(f"calls_df columns: {sorted(current_calls_columns)}")
    print(f"puts_df columns: {sorted(current_puts_columns)}")
    
    # Detect schema pollution
    calls_added = current_calls_columns - original_calls_columns
    puts_added = current_puts_columns - original_puts_columns
    
    if calls_added or puts_added:
        print("\n=== BUG DETECTED: DataFrame Schema Pollution ===")
        if calls_added:
            print(f"calls_df gained columns: {sorted(calls_added)}")
        if puts_added:
            print(f"puts_df gained columns: {sorted(puts_added)}")
        
        print("\n=== Expected Counterexample ===")
        print("The 'strike_diff' column should appear in both DataFrames.")
        print("This confirms the bug exists in the unfixed code.")
        print("\nRoot cause: main.py lines 3107-3108 mutate DataFrames in-place:")
        print("  calls_df['strike_diff'] = abs(calls_df['strike'] - current_price)")
        print("  puts_df['strike_diff'] = abs(puts_df['strike'] - current_price)")
    
    # ASSERTION: DataFrames should NOT be mutated
    # This will FAIL on unfixed code (which is correct - it proves the bug exists)
    assert current_calls_columns == original_calls_columns, (
        f"DataFrame schema pollution detected in calls_df! "
        f"Added columns: {sorted(calls_added)}. "
        f"The original calls_df should remain unchanged after Module 27 execution. "
        f"Counterexample: 'strike_diff' column was added to shared DataFrame."
    )
    
    assert current_puts_columns == original_puts_columns, (
        f"DataFrame schema pollution detected in puts_df! "
        f"Added columns: {sorted(puts_added)}. "
        f"The original puts_df should remain unchanged after Module 27 execution. "
        f"Counterexample: 'strike_diff' column was added to shared DataFrame."
    )
    
    # Additional assertion: Verify no temporary fields exist
    assert 'strike_diff' not in current_calls_columns, (
        "Temporary field 'strike_diff' found in calls_df! "
        "This field should only exist in working copies, not in the original DataFrame."
    )
    
    assert 'strike_diff' not in current_puts_columns, (
        "Temporary field 'strike_diff' found in puts_df! "
        "This field should only exist in working copies, not in the original DataFrame."
    )
    
    # If we reach here on unfixed code, something is wrong with the test
    print("\nWARNING: Test passed on unfixed code - bug may not exist or test needs adjustment")


@pytest.mark.property_based_test
@given(
    current_price=st.floats(min_value=50.0, max_value=500.0),
    num_strikes=st.integers(min_value=5, max_value=20)
)
@settings(
    max_examples=10,  # Run multiple examples to confirm consistency
    phases=[Phase.generate, Phase.target],  # Skip shrinking for exploration
    deadline=None  # No time limit for this exploration test
)
def test_dataframe_mutation_property_based(current_price, num_strikes):
    """
    **Property 1: Bug Condition** - DataFrame Schema Pollution (Property-Based)
    
    **Validates: Requirements 3.2, 3.5, 3.6**
    
    Property-based version that tests with various stock prices and option chains.
    This should fail consistently on unfixed code regardless of input parameters.
    
    The property being tested: For ANY valid option chain configuration,
    Module 27 ATM selection should NOT mutate the original DataFrames.
    """
    # Create analyzer
    analyzer = OptionsAnalysisSystem()
    
    # Test parameters
    ticker = 'TEST'
    expiration = '2024-12-31'
    
    # Create sample option chains with generated parameters
    calls_df_original = create_sample_option_chain(current_price, num_strikes)
    puts_df_original = create_sample_option_chain(current_price, num_strikes)
    
    # Capture original schemas
    original_calls_columns = set(calls_df_original.columns)
    original_puts_columns = set(puts_df_original.columns)
    
    # Mock the fetcher
    with patch.object(analyzer, 'fetcher') as mock_fetcher, \
         patch.object(analyzer, 'validator') as mock_validator, \
         patch('main.logger'):
        
        mock_fetcher.get_option_expirations.return_value = [expiration]
        mock_fetcher.get_option_chain.return_value = {
            'calls': calls_df_original,
            'puts': puts_df_original
        }
        
        mock_fetcher.get_complete_analysis_data.return_value = {
            'stock_price': current_price,
            'current_price': current_price,
            'eps': 5.0,
            'pe_ratio': 20.0,
            'forward_pe': 18.0,
            'calls': [],
            'puts': [],
            'risk_free_rate': 0.05,
            'dividend_yield': 0.02,
            'implied_volatility': 25.0,
            'option_chain': {'calls': calls_df_original, 'puts': puts_df_original},
            'days_to_expiration': 30,
            'expiration_date': expiration,
            'analysis_date': '2024-01-01'
        }
        
        mock_validator.validate_stock_data.return_value = True
        
        try:
            analyzer.run_complete_analysis(
                ticker=ticker,
                expiration=expiration,
                selected_expirations=[expiration]
            )
        except Exception:
            pass
    
    # Check for mutations
    current_calls_columns = set(calls_df_original.columns)
    current_puts_columns = set(puts_df_original.columns)
    
    # Expected behavior: Schemas should remain unchanged
    # This will FAIL on unfixed code
    assert current_calls_columns == original_calls_columns, (
        f"DataFrame mutation for price={current_price:.2f}, strikes={num_strikes}! "
        f"Added to calls_df: {sorted(current_calls_columns - original_calls_columns)}"
    )
    
    assert current_puts_columns == original_puts_columns, (
        f"DataFrame mutation for price={current_price:.2f}, strikes={num_strikes}! "
        f"Added to puts_df: {sorted(current_puts_columns - original_puts_columns)}"
    )


@pytest.mark.property_based_test
def test_repeated_analysis_no_schema_drift():
    """
    **Property 1: Bug Condition** - No Schema Drift on Repeated Runs
    
    **Validates: Requirements 3.6**
    
    Tests that running the same analysis multiple times does not accumulate
    temporary columns or cause schema drift. This is a critical test for
    detecting in-place mutation bugs.
    
    Expected counterexample on unfixed code:
    - First run: DataFrame gains 'strike_diff'
    - Second run: May fail or accumulate more pollution
    """
    analyzer = OptionsAnalysisSystem()
    
    ticker = 'TEST'
    current_price = 150.0
    expiration = '2024-12-31'
    
    # Create option chains
    calls_df = create_sample_option_chain(current_price, num_strikes=10)
    puts_df = create_sample_option_chain(current_price, num_strikes=10)
    
    original_calls_columns = set(calls_df.columns)
    original_puts_columns = set(puts_df.columns)
    
    schemas_after_each_run = []
    
    # Run analysis multiple times
    for run_num in range(3):
        print(f"\n=== Run {run_num + 1} ===")
        
        with patch.object(analyzer, 'fetcher') as mock_fetcher, \
             patch.object(analyzer, 'validator') as mock_validator, \
             patch('main.logger'):
            
            mock_fetcher.get_option_expirations.return_value = [expiration]
            mock_fetcher.get_option_chain.return_value = {
                'calls': calls_df,
                'puts': puts_df
            }
            
            mock_fetcher.get_complete_analysis_data.return_value = {
                'stock_price': current_price,
                'current_price': current_price,
                'eps': 5.0,
                'pe_ratio': 20.0,
                'forward_pe': 18.0,
                'calls': [],
                'puts': [],
                'risk_free_rate': 0.05,
                'dividend_yield': 0.02,
                'implied_volatility': 25.0,
                'option_chain': {'calls': calls_df, 'puts': puts_df},
                'days_to_expiration': 30,
                'expiration_date': expiration,
                'analysis_date': '2024-01-01'
            }
            
            mock_validator.validate_stock_data.return_value = True
            
            try:
                analyzer.run_complete_analysis(
                    ticker=ticker,
                    expiration=expiration,
                    selected_expirations=[expiration]
                )
            except Exception:
                pass
        
        # Capture schema after this run
        current_schema = {
            'calls': set(calls_df.columns),
            'puts': set(puts_df.columns)
        }
        schemas_after_each_run.append(current_schema)
        
        print(f"calls_df columns: {sorted(current_schema['calls'])}")
        print(f"puts_df columns: {sorted(current_schema['puts'])}")
    
    # Check for schema drift across runs
    print("\n=== Schema Drift Analysis ===")
    for i, schema in enumerate(schemas_after_each_run):
        calls_added = schema['calls'] - original_calls_columns
        puts_added = schema['puts'] - original_puts_columns
        
        if calls_added or puts_added:
            print(f"Run {i+1}: Schema pollution detected!")
            if calls_added:
                print(f"  calls_df gained: {sorted(calls_added)}")
            if puts_added:
                print(f"  puts_df gained: {sorted(puts_added)}")
    
    # ASSERTION: All runs should maintain original schema
    for i, schema in enumerate(schemas_after_each_run):
        assert schema['calls'] == original_calls_columns, (
            f"Run {i+1}: calls_df schema changed! "
            f"Added: {sorted(schema['calls'] - original_calls_columns)}"
        )
        
        assert schema['puts'] == original_puts_columns, (
            f"Run {i+1}: puts_df schema changed! "
            f"Added: {sorted(schema['puts'] - original_puts_columns)}"
        )


if __name__ == '__main__':
    # Run the exploration test directly
    print("Running Bug Condition Exploration Test for BR-02...")
    print("=" * 70)
    test_dataframe_mutation_detection_concrete()
    print("\n" + "=" * 70)
    print("Running repeated analysis test...")
    print("=" * 70)
    test_repeated_analysis_no_schema_drift()
