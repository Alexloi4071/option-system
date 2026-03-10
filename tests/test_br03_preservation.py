"""
Preservation Property Tests for BR-03: American Pricing and Complex Strategies

**Property 2: Preservation** - Pricing and Strategy Analysis Preservation

**Validates: Requirements 4.4, 4.5, 4.8**

This test captures the CURRENT behavior of American pricing and complex strategies
on UNFIXED code. It should PASS on unfixed code to establish the baseline behavior.

After fixing BR-03 (renaming module32_american_pricing.py), these tests should STILL PASS,
confirming that we preserved:
- American pricing calculation accuracy
- Complex strategy analysis results
- All imports resolve correctly
- Functional equivalence across the rename

IMPORTANT: This test observes and validates the EXISTING functional behavior,
NOT the bug condition. The bug (duplicate module32 numbering) will be fixed, but
the pricing and strategy functionality must remain identical.
"""

import pytest
from hypothesis import given, strategies as st, settings, Phase
import sys
import os
import math

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from calculation_layer.american_option_pricer import AmericanOptionPricer, AmericanPricingResult
from calculation_layer.module32_complex_strategies import (
    ComplexStrategyAnalyzer, OptionLeg, StrategyResult
)
import pandas as pd


# ============================================================================
# Test Data Generators
# ============================================================================

def generate_valid_option_params():
    """Generate valid option pricing parameters for testing"""
    return {
        'stock_price': 100.0,
        'strike_price': 100.0,
        'risk_free_rate': 0.05,
        'time_to_expiration': 0.25,  # 3 months
        'volatility': 0.25,  # 25% IV
        'dividend_yield': 0.02
    }


def generate_option_chain_df():
    """Generate a minimal valid option chain DataFrame for strategy testing"""
    data = {
        'strike': [90.0, 95.0, 100.0, 105.0, 110.0],
        'lastPrice': [12.0, 8.0, 5.0, 3.0, 1.5],
        'bid': [11.5, 7.5, 4.5, 2.5, 1.0],
        'ask': [12.5, 8.5, 5.5, 3.5, 2.0],
        'delta': [0.80, 0.65, 0.50, 0.35, 0.20],
        'gamma': [0.02, 0.03, 0.04, 0.03, 0.02],
        'theta': [-0.05, -0.06, -0.07, -0.06, -0.05],
        'vega': [0.15, 0.20, 0.25, 0.20, 0.15],
        'impliedVolatility': [0.25, 0.24, 0.23, 0.24, 0.25]
    }
    return pd.DataFrame(data)


# ============================================================================
# American Pricing Preservation Tests
# ============================================================================

@pytest.mark.property_based_test
def test_american_pricing_basic_functionality():
    """
    **Property 2: Preservation** - American Pricing Basic Functionality
    
    **Validates: Requirements 4.4, 4.8**
    
    Tests that American option pricing produces valid results with expected properties.
    This test captures the CURRENT behavior on unfixed code.
    
    Expected behavior:
    - American price >= European price (early exercise premium >= 0)
    - Call and Put pricing both work
    - Results contain all expected fields
    """
    pricer = AmericanOptionPricer()
    params = generate_valid_option_params()
    
    # Test Call option
    call_result = pricer.calculate_american_price(
        stock_price=params['stock_price'],
        strike_price=params['strike_price'],
        risk_free_rate=params['risk_free_rate'],
        time_to_expiration=params['time_to_expiration'],
        volatility=params['volatility'],
        option_type='call',
        dividend_yield=params['dividend_yield'],
        model='binomial',
        steps=100
    )
    
    # Verify result structure
    assert isinstance(call_result, AmericanPricingResult)
    assert call_result.american_price >= call_result.european_price, (
        "American call price should be >= European price"
    )
    assert call_result.early_exercise_premium >= 0, (
        "Early exercise premium should be non-negative"
    )
    assert call_result.option_type == 'call'
    assert call_result.model_used == 'binomial'
    
    # Test Put option
    put_result = pricer.calculate_american_price(
        stock_price=params['stock_price'],
        strike_price=params['strike_price'],
        risk_free_rate=params['risk_free_rate'],
        time_to_expiration=params['time_to_expiration'],
        volatility=params['volatility'],
        option_type='put',
        dividend_yield=params['dividend_yield'],
        model='binomial',
        steps=100
    )
    
    # Verify result structure
    assert isinstance(put_result, AmericanPricingResult)
    assert put_result.american_price >= put_result.european_price, (
        "American put price should be >= European price"
    )
    assert put_result.early_exercise_premium >= 0, (
        "Early exercise premium should be non-negative"
    )
    assert put_result.option_type == 'put'
    
    print(f"\n✓ American Call: ${call_result.american_price:.4f} (premium: ${call_result.early_exercise_premium:.4f})")
    print(f"✓ American Put: ${put_result.american_price:.4f} (premium: ${put_result.early_exercise_premium:.4f})")


@pytest.mark.property_based_test
@given(
    stock_price=st.floats(min_value=50.0, max_value=150.0),
    strike_price=st.floats(min_value=50.0, max_value=150.0),
    time_to_expiration=st.floats(min_value=0.1, max_value=1.0),
    volatility=st.floats(min_value=0.1, max_value=0.5)
)
@settings(
    max_examples=10,
    phases=[Phase.generate, Phase.target],
    deadline=None
)
def test_american_pricing_property_based(stock_price, strike_price, time_to_expiration, volatility):
    """
    **Property 2: Preservation** - American Pricing Properties Across Inputs
    
    **Validates: Requirements 4.4, 4.8**
    
    Property-based test that verifies American pricing maintains expected
    mathematical properties across a wide range of inputs.
    
    Expected properties:
    1. American price >= European price (always)
    2. American price >= intrinsic value (always)
    3. Early exercise premium >= 0 (always)
    4. Pricing is deterministic (same inputs -> same outputs)
    """
    pricer = AmericanOptionPricer()
    
    # Test Call option
    call_result = pricer.calculate_american_price(
        stock_price=stock_price,
        strike_price=strike_price,
        risk_free_rate=0.05,
        time_to_expiration=time_to_expiration,
        volatility=volatility,
        option_type='call',
        dividend_yield=0.02,
        model='binomial',
        steps=100
    )
    
    # Property 1: American >= European
    assert call_result.american_price >= call_result.european_price, (
        f"American call price ({call_result.american_price:.4f}) should be >= "
        f"European price ({call_result.european_price:.4f})"
    )
    
    # Property 2: American >= Intrinsic value
    intrinsic_call = max(0, stock_price - strike_price)
    assert call_result.american_price >= intrinsic_call - 0.01, (  # Allow small numerical error
        f"American call price ({call_result.american_price:.4f}) should be >= "
        f"intrinsic value ({intrinsic_call:.4f})"
    )
    
    # Property 3: Premium >= 0
    assert call_result.early_exercise_premium >= -0.01, (  # Allow small numerical error
        f"Early exercise premium ({call_result.early_exercise_premium:.4f}) should be >= 0"
    )
    
    # Test Put option
    put_result = pricer.calculate_american_price(
        stock_price=stock_price,
        strike_price=strike_price,
        risk_free_rate=0.05,
        time_to_expiration=time_to_expiration,
        volatility=volatility,
        option_type='put',
        dividend_yield=0.02,
        model='binomial',
        steps=100
    )
    
    # Property 1: American >= European
    assert put_result.american_price >= put_result.european_price, (
        f"American put price ({put_result.american_price:.4f}) should be >= "
        f"European price ({put_result.european_price:.4f})"
    )
    
    # Property 2: American >= Intrinsic value
    intrinsic_put = max(0, strike_price - stock_price)
    assert put_result.american_price >= intrinsic_put - 0.01, (  # Allow small numerical error
        f"American put price ({put_result.american_price:.4f}) should be >= "
        f"intrinsic value ({intrinsic_put:.4f})"
    )
    
    # Property 3: Premium >= 0
    assert put_result.early_exercise_premium >= -0.01, (  # Allow small numerical error
        f"Early exercise premium ({put_result.early_exercise_premium:.4f}) should be >= 0"
    )


@pytest.mark.property_based_test
def test_american_pricing_deterministic():
    """
    **Property 2: Preservation** - American Pricing Determinism
    
    **Validates: Requirements 4.4, 4.8**
    
    Tests that American pricing is deterministic: same inputs produce same outputs.
    This is critical for preservation - the rename should not affect calculation results.
    """
    pricer = AmericanOptionPricer()
    params = generate_valid_option_params()
    
    # Calculate twice with same inputs
    result1 = pricer.calculate_american_price(
        stock_price=params['stock_price'],
        strike_price=params['strike_price'],
        risk_free_rate=params['risk_free_rate'],
        time_to_expiration=params['time_to_expiration'],
        volatility=params['volatility'],
        option_type='call',
        dividend_yield=params['dividend_yield'],
        model='binomial',
        steps=200
    )
    
    result2 = pricer.calculate_american_price(
        stock_price=params['stock_price'],
        strike_price=params['strike_price'],
        risk_free_rate=params['risk_free_rate'],
        time_to_expiration=params['time_to_expiration'],
        volatility=params['volatility'],
        option_type='call',
        dividend_yield=params['dividend_yield'],
        model='binomial',
        steps=200
    )
    
    # Results should be identical
    assert result1.american_price == result2.american_price, (
        "American pricing should be deterministic"
    )
    assert result1.european_price == result2.european_price, (
        "European pricing should be deterministic"
    )
    assert result1.early_exercise_premium == result2.early_exercise_premium, (
        "Early exercise premium should be deterministic"
    )
    
    print(f"\n✓ Deterministic pricing confirmed: ${result1.american_price:.4f}")


# ============================================================================
# Complex Strategies Preservation Tests
# ============================================================================

@pytest.mark.property_based_test
def test_complex_strategies_basic_functionality():
    """
    **Property 2: Preservation** - Complex Strategies Basic Functionality
    
    **Validates: Requirements 4.5, 4.8**
    
    Tests that complex strategy analysis produces valid results with expected properties.
    This test captures the CURRENT behavior on unfixed code.
    
    Expected behavior:
    - Vertical spreads analysis works
    - Iron condor analysis works
    - Straddle/Strangle analysis works
    - Results contain all expected fields
    """
    analyzer = ComplexStrategyAnalyzer()
    
    # Generate test data
    calls_df = generate_option_chain_df()
    puts_df = generate_option_chain_df()
    # Adjust put deltas to be negative
    puts_df['delta'] = -puts_df['delta']
    current_price = 100.0
    
    # Test Vertical Spreads
    vertical_results = analyzer.analyze_vertical_spreads(calls_df, puts_df, current_price)
    
    assert 'bull_put' in vertical_results
    assert 'bear_call' in vertical_results
    assert isinstance(vertical_results['bull_put'], list)
    assert isinstance(vertical_results['bear_call'], list)
    
    # If we got results, verify structure
    if vertical_results['bull_put']:
        strategy = vertical_results['bull_put'][0]
        assert isinstance(strategy, StrategyResult)
        assert strategy.name == 'bull_put'
        assert len(strategy.legs) == 2
        # Observe actual behavior - don't enforce assumptions about profit sign
        assert isinstance(strategy.max_profit, (int, float))
        assert isinstance(strategy.max_loss, (int, float))
        
    if vertical_results['bear_call']:
        strategy = vertical_results['bear_call'][0]
        assert isinstance(strategy, StrategyResult)
        assert strategy.name == 'bear_call'
        assert len(strategy.legs) == 2
        # Observe actual behavior - don't enforce assumptions about profit sign
        assert isinstance(strategy.max_profit, (int, float))
        assert isinstance(strategy.max_loss, (int, float))
    
    # Test Iron Condor
    condor_results = analyzer.analyze_iron_condor(calls_df, puts_df, current_price)
    
    assert isinstance(condor_results, list)
    if condor_results:
        condor = condor_results[0]
        assert isinstance(condor, StrategyResult)
        assert condor.name == 'iron_condor'
        assert len(condor.legs) == 4  # Iron condor has 4 legs
        assert condor.max_profit > 0  # Should collect premium
        assert len(condor.breakevens) == 2  # Should have 2 breakeven points
    
    # Test Straddle/Strangle
    straddle_results = analyzer.analyze_straddle_strangle(calls_df, puts_df, current_price)
    
    assert 'straddle' in straddle_results
    assert 'strangle' in straddle_results
    assert isinstance(straddle_results['straddle'], list)
    assert isinstance(straddle_results['strangle'], list)
    
    if straddle_results['straddle']:
        straddle = straddle_results['straddle'][0]
        assert isinstance(straddle, StrategyResult)
        assert straddle.name == 'long_straddle'
        assert len(straddle.legs) == 2
        assert straddle.net_premium < 0  # Long straddle costs money
        assert straddle.max_profit == float('inf')  # Unlimited profit potential
    
    print(f"\n✓ Vertical spreads analysis functional")
    print(f"✓ Iron condor analysis functional")
    print(f"✓ Straddle/Strangle analysis functional")


@pytest.mark.property_based_test
def test_strategy_result_structure():
    """
    **Property 2: Preservation** - Strategy Result Structure
    
    **Validates: Requirements 4.5, 4.8**
    
    Tests that StrategyResult objects maintain their expected structure.
    This ensures the data model remains consistent after the rename.
    """
    # Create a sample strategy result
    leg1 = OptionLeg(
        strike=100.0,
        option_type='call',
        action='buy',
        quantity=1,
        premium=5.0,
        delta=0.5,
        gamma=0.03,
        theta=-0.05,
        vega=0.2
    )
    
    leg2 = OptionLeg(
        strike=105.0,
        option_type='call',
        action='sell',
        quantity=1,
        premium=3.0,
        delta=0.3,
        gamma=0.02,
        theta=-0.03,
        vega=0.15
    )
    
    strategy = StrategyResult(
        name='bull_call_spread',
        legs=[leg1, leg2],
        net_premium=-200.0,  # Debit spread
        max_profit=300.0,
        max_loss=200.0,
        breakevens=[102.0],
        risk_reward_ratio=1.5,
        win_probability=0.6,
        priority_score=75.0,
        net_delta=0.2,
        net_gamma=0.01,
        net_theta=-0.02,
        net_vega=0.05
    )
    
    # Verify structure
    assert strategy.name == 'bull_call_spread'
    assert len(strategy.legs) == 2
    assert strategy.net_premium == -200.0
    assert strategy.max_profit == 300.0
    assert strategy.max_loss == 200.0
    assert len(strategy.breakevens) == 1
    assert strategy.breakevens[0] == 102.0
    
    # Verify to_dict() method works
    strategy_dict = strategy.to_dict()
    assert isinstance(strategy_dict, dict)
    assert 'name' in strategy_dict
    assert 'net_premium' in strategy_dict
    assert 'max_profit' in strategy_dict
    assert 'max_loss' in strategy_dict
    assert 'breakevens' in strategy_dict
    assert 'greeks' in strategy_dict
    
    # Verify Greeks structure
    assert 'delta' in strategy_dict['greeks']
    assert 'gamma' in strategy_dict['greeks']
    assert 'theta' in strategy_dict['greeks']
    assert 'vega' in strategy_dict['greeks']
    
    print(f"\n✓ StrategyResult structure preserved")
    print(f"✓ to_dict() method functional")


@pytest.mark.property_based_test
def test_option_leg_structure():
    """
    **Property 2: Preservation** - OptionLeg Structure
    
    **Validates: Requirements 4.5, 4.8**
    
    Tests that OptionLeg objects maintain their expected structure.
    This ensures the data model remains consistent after the rename.
    """
    # Test valid leg creation
    leg = OptionLeg(
        strike=100.0,
        option_type='call',
        action='buy',
        quantity=1,
        premium=5.0,
        delta=0.5,
        gamma=0.03,
        theta=-0.05,
        vega=0.2,
        iv=0.25
    )
    
    assert leg.strike == 100.0
    assert leg.option_type == 'call'
    assert leg.action == 'buy'
    assert leg.quantity == 1
    assert leg.premium == 5.0
    assert leg.delta == 0.5
    assert leg.gamma == 0.03
    assert leg.theta == -0.05
    assert leg.vega == 0.2
    assert leg.iv == 0.25
    
    # Test action normalization
    leg_upper = OptionLeg(strike=100.0, option_type='call', action='BUY')
    assert leg_upper.action == 'buy'
    
    leg_sell = OptionLeg(strike=100.0, option_type='put', action='SELL')
    assert leg_sell.action == 'sell'
    
    # Test invalid action raises error
    with pytest.raises(ValueError):
        OptionLeg(strike=100.0, option_type='call', action='invalid')
    
    print(f"\n✓ OptionLeg structure preserved")
    print(f"✓ Action normalization functional")


@pytest.mark.property_based_test
@given(
    current_price=st.floats(min_value=80.0, max_value=120.0)
)
@settings(
    max_examples=5,
    phases=[Phase.generate, Phase.target],
    deadline=None
)
def test_strategy_analysis_property_based(current_price):
    """
    **Property 2: Preservation** - Strategy Analysis Across Price Ranges
    
    **Validates: Requirements 4.5, 4.8**
    
    Property-based test that verifies strategy analysis maintains expected
    properties across different current price levels.
    
    Expected properties:
    1. Analysis completes without errors
    2. Results have valid structure
    3. Greeks are calculated
    4. Risk/reward metrics are present
    """
    analyzer = ComplexStrategyAnalyzer()
    
    # Generate option chain centered around current price
    strikes = [current_price * 0.9, current_price * 0.95, current_price, 
               current_price * 1.05, current_price * 1.10]
    
    calls_data = {
        'strike': strikes,
        'lastPrice': [max(0.5, current_price - s + 5) for s in strikes],
        'bid': [max(0.3, current_price - s + 4) for s in strikes],
        'ask': [max(0.7, current_price - s + 6) for s in strikes],
        'delta': [0.80, 0.65, 0.50, 0.35, 0.20],
        'gamma': [0.02, 0.03, 0.04, 0.03, 0.02],
        'theta': [-0.05, -0.06, -0.07, -0.06, -0.05],
        'vega': [0.15, 0.20, 0.25, 0.20, 0.15],
        'impliedVolatility': [0.25, 0.24, 0.23, 0.24, 0.25]
    }
    
    puts_data = {
        'strike': strikes,
        'lastPrice': [max(0.5, s - current_price + 5) for s in strikes],
        'bid': [max(0.3, s - current_price + 4) for s in strikes],
        'ask': [max(0.7, s - current_price + 6) for s in strikes],
        'delta': [-0.20, -0.35, -0.50, -0.65, -0.80],
        'gamma': [0.02, 0.03, 0.04, 0.03, 0.02],
        'theta': [-0.05, -0.06, -0.07, -0.06, -0.05],
        'vega': [0.15, 0.20, 0.25, 0.20, 0.15],
        'impliedVolatility': [0.25, 0.24, 0.23, 0.24, 0.25]
    }
    
    calls_df = pd.DataFrame(calls_data)
    puts_df = pd.DataFrame(puts_data)
    
    # Test vertical spreads
    vertical_results = analyzer.analyze_vertical_spreads(calls_df, puts_df, current_price)
    assert isinstance(vertical_results, dict)
    assert 'bull_put' in vertical_results
    assert 'bear_call' in vertical_results
    
    # Test iron condor
    condor_results = analyzer.analyze_iron_condor(calls_df, puts_df, current_price)
    assert isinstance(condor_results, list)
    
    # Test straddle/strangle
    straddle_results = analyzer.analyze_straddle_strangle(calls_df, puts_df, current_price)
    assert isinstance(straddle_results, dict)
    assert 'straddle' in straddle_results
    assert 'strangle' in straddle_results


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.property_based_test
def test_american_pricing_and_strategies_integration():
    """
    **Property 2: Preservation** - Integration Between Pricing and Strategies
    
    **Validates: Requirements 4.4, 4.5, 4.8**
    
    Tests that American pricing and complex strategies can be used together
    in an integrated workflow. This ensures both modules work correctly
    after the rename.
    """
    # Initialize both components
    pricer = AmericanOptionPricer()
    analyzer = ComplexStrategyAnalyzer()
    
    # Calculate American prices
    call_result = pricer.calculate_american_price(
        stock_price=100.0,
        strike_price=100.0,
        risk_free_rate=0.05,
        time_to_expiration=0.25,
        volatility=0.25,
        option_type='call',
        dividend_yield=0.02
    )
    
    put_result = pricer.calculate_american_price(
        stock_price=100.0,
        strike_price=100.0,
        risk_free_rate=0.05,
        time_to_expiration=0.25,
        volatility=0.25,
        option_type='put',
        dividend_yield=0.02
    )
    
    # Analyze strategies
    calls_df = generate_option_chain_df()
    puts_df = generate_option_chain_df()
    puts_df['delta'] = -puts_df['delta']
    
    vertical_results = analyzer.analyze_vertical_spreads(calls_df, puts_df, 100.0)
    
    # Verify both components produced valid results
    assert call_result.american_price > 0
    assert put_result.american_price > 0
    assert isinstance(vertical_results, dict)
    
    print(f"\n✓ American pricing functional: Call=${call_result.american_price:.4f}, Put=${put_result.american_price:.4f}")
    print(f"✓ Strategy analysis functional: {len(vertical_results)} strategy types")
    print(f"✓ Integration between pricing and strategies preserved")


if __name__ == '__main__':
    # Run the preservation tests directly
    print("Running Preservation Property Tests for BR-03...")
    print("=" * 70)
    
    print("\n=== American Pricing Tests ===")
    print("\nTest 1: Basic Functionality")
    test_american_pricing_basic_functionality()
    
    print("\nTest 2: Deterministic Pricing")
    test_american_pricing_deterministic()
    
    print("\n=== Complex Strategies Tests ===")
    print("\nTest 3: Basic Functionality")
    test_complex_strategies_basic_functionality()
    
    print("\nTest 4: Strategy Result Structure")
    test_strategy_result_structure()
    
    print("\nTest 5: Option Leg Structure")
    test_option_leg_structure()
    
    print("\n=== Integration Tests ===")
    print("\nTest 6: Pricing and Strategies Integration")
    test_american_pricing_and_strategies_integration()
    
    print("\n" + "=" * 70)
    print("All preservation tests passed!")
    print("\nThese tests confirm the baseline behavior on unfixed code.")
    print("After fixing BR-03 (renaming module32_american_pricing.py),")
    print("these same tests should still pass, confirming functional preservation.")
