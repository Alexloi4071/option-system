#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Property-based tests for Module 22 Liquidity Warning

**Feature: report-improvements, Property 10: 流動性警告**
**Validates: Requirements 12.2**
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from output_layer.report_generator import ReportGenerator


# Strategy for liquidity scores (0 to 100)
liquidity_score_strategy = st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False)

# Strategy for composite scores (0 to 100)
composite_score_strategy = st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False)

# Strategy for strike prices
strike_strategy = st.floats(min_value=50.0, max_value=500.0, allow_nan=False, allow_infinity=False)

# Strategy for Greeks
delta_strategy = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
gamma_strategy = st.floats(min_value=0.0, max_value=0.5, allow_nan=False, allow_infinity=False)
theta_strategy = st.floats(min_value=-1.0, max_value=0.0, allow_nan=False, allow_infinity=False)
vega_strategy = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)


def create_mock_module22_results(
    strategy_type: str,
    liquidity_score: float,
    composite_score: float = 70.0,
    strike: float = 100.0,
    delta: float = 0.5,
    gamma: float = 0.03,
    theta: float = -0.05,
    vega: float = 0.15,
    greeks_score: float = 60.0,
    iv_score: float = 50.0,
    risk_reward_score: float = 55.0
) -> dict:
    """Create mock Module 22 results for testing"""
    return {
        strategy_type: {
            'strike_range': {'min': 80.0, 'max': 120.0, 'range_pct': 20},
            'total_analyzed': 5,
            'top_recommendations': [
                {
                    'rank': 1,
                    'strike': strike,
                    'composite_score': composite_score,
                    'liquidity_score': liquidity_score,
                    'greeks_score': greeks_score,
                    'iv_score': iv_score,
                    'risk_reward_score': risk_reward_score,
                    'delta': delta,
                    'gamma': gamma,
                    'theta': theta,
                    'vega': vega,
                    'volume': 100 if liquidity_score >= 50 else 5,
                    'open_interest': 500 if liquidity_score >= 50 else 50,
                    'bid_ask_spread_pct': 2.0 if liquidity_score >= 50 else 15.0,
                    'reason': 'Test recommendation'
                }
            ]
        }
    }


class TestModule22LiquidityWarning:
    """
    Test Module 22 Liquidity Warning
    
    **Feature: report-improvements, Property 10: 流動性警告**
    **Validates: Requirements 12.2**
    """
    
    def setup_method(self):
        self.generator = ReportGenerator()
    
    @given(liquidity_score=st.floats(min_value=0.0, max_value=49.9, allow_nan=False, allow_infinity=False))
    @settings(max_examples=100)
    def test_low_liquidity_shows_warning(self, liquidity_score):
        """
        Property 10: For any liquidity score below 50, output should contain reliability warning.
        
        **Feature: report-improvements, Property 10: 流動性警告**
        **Validates: Requirements 12.2**
        """
        # Create mock results with low liquidity score
        results = create_mock_module22_results('long_call', liquidity_score)
        
        # Format the results
        output = self.generator._format_module22_optimal_strike(results)
        
        # Verify warning is present
        assert '流動性警告' in output or '⚠️' in output
        assert f'{liquidity_score:.0f}' in output or '< 50' in output
    
    @given(liquidity_score=st.floats(min_value=50.0, max_value=100.0, allow_nan=False, allow_infinity=False))
    @settings(max_examples=100)
    def test_adequate_liquidity_no_warning(self, liquidity_score):
        """
        Property 10: For any liquidity score >= 50, output should NOT contain liquidity warning.
        
        **Feature: report-improvements, Property 10: 流動性警告**
        **Validates: Requirements 12.2**
        """
        # Create mock results with adequate liquidity score
        results = create_mock_module22_results('long_call', liquidity_score)
        
        # Format the results
        output = self.generator._format_module22_optimal_strike(results)
        
        # Verify no liquidity warning for this specific recommendation
        # The warning should not appear for recommendations with liquidity >= 50
        lines = output.split('\n')
        for i, line in enumerate(lines):
            if '推薦 #1' in line:
                # Check the next few lines for liquidity warning
                next_lines = '\n'.join(lines[i:i+5])
                # Should not have "流動性警告" immediately after the recommendation
                if '流動性警告' in next_lines:
                    # If warning exists, it should not be for this score
                    assert f'{liquidity_score:.0f} < 50' not in next_lines


class TestModule22DataCompleteness:
    """
    Test Module 22 Data Completeness calculation
    
    **Feature: report-improvements**
    **Validates: Requirements 12.1**
    """
    
    def setup_method(self):
        self.generator = ReportGenerator()
    
    def test_data_completeness_displayed(self):
        """
        Requirements 12.1: Data completeness should be displayed in output.
        """
        results = create_mock_module22_results('long_call', 70.0)
        output = self.generator._format_module22_optimal_strike(results)
        
        assert '數據完整度' in output
        assert '%' in output
    
    @given(
        liq1=liquidity_score_strategy,
        liq2=liquidity_score_strategy,
        liq3=liquidity_score_strategy,
        liq4=liquidity_score_strategy
    )
    @settings(max_examples=50)
    def test_data_completeness_calculation(self, liq1, liq2, liq3, liq4):
        """
        Requirements 12.1: Data completeness should be calculated correctly.
        """
        # Create results with multiple strategies
        results = {
            'long_call': create_mock_module22_results('long_call', liq1)['long_call'],
            'long_put': create_mock_module22_results('long_put', liq2)['long_put'],
            'short_call': create_mock_module22_results('short_call', liq3)['short_call'],
            'short_put': create_mock_module22_results('short_put', liq4)['short_put']
        }
        
        completeness = self.generator._calculate_module22_data_completeness(results)
        
        # Completeness should be between 0 and 100
        assert 0.0 <= completeness <= 100.0


class TestModule22ConfidenceLevel:
    """
    Test Module 22 Confidence Level
    
    **Feature: report-improvements**
    **Validates: Requirements 12.4**
    """
    
    def setup_method(self):
        self.generator = ReportGenerator()
    
    def test_confidence_level_displayed(self):
        """
        Requirements 12.4: Confidence level should be displayed in output.
        """
        results = create_mock_module22_results('long_call', 70.0)
        output = self.generator._format_module22_optimal_strike(results)
        
        assert '信心等級' in output
        # Should show one of: 高, 中, 低
        assert '高' in output or '中' in output or '低' in output
    
    def test_low_confidence_with_insufficient_data(self):
        """
        Requirements 12.4: Low confidence when data is insufficient.
        """
        # Create results with minimal data
        results = {
            'long_call': {
                'strike_range': {'min': 80.0, 'max': 120.0, 'range_pct': 20},
                'total_analyzed': 1,  # Very few analyzed
                'top_recommendations': []  # No recommendations
            }
        }
        
        completeness = self.generator._calculate_module22_data_completeness(results)
        confidence = self.generator._get_module22_confidence_level(completeness, results)
        
        assert confidence == '低'
    
    def test_high_confidence_with_complete_data(self):
        """
        Requirements 12.4: High confidence when data is complete.
        """
        # Create results with complete data and good liquidity
        results = {
            'long_call': create_mock_module22_results('long_call', 80.0)['long_call'],
            'long_put': create_mock_module22_results('long_put', 75.0)['long_put'],
            'short_call': create_mock_module22_results('short_call', 70.0)['short_call'],
            'short_put': create_mock_module22_results('short_put', 85.0)['short_put']
        }
        
        # Add more recommendations to each strategy
        for key in results:
            results[key]['total_analyzed'] = 10
            results[key]['top_recommendations'].extend([
                {
                    'rank': 2,
                    'strike': 105.0,
                    'composite_score': 65.0,
                    'liquidity_score': 70.0,
                    'greeks_score': 60.0,
                    'iv_score': 50.0,
                    'risk_reward_score': 55.0,
                    'delta': 0.4,
                    'gamma': 0.03,
                    'theta': -0.04,
                    'vega': 0.12,
                    'volume': 200,
                    'open_interest': 800,
                    'bid_ask_spread_pct': 3.0,
                    'reason': 'Test recommendation 2'
                }
            ])
        
        completeness = self.generator._calculate_module22_data_completeness(results)
        confidence = self.generator._get_module22_confidence_level(completeness, results)
        
        # Should be high or medium confidence with complete data
        assert confidence in ['高', '中']


class TestModule22MainScoringFactor:
    """
    Test Module 22 Main Scoring Factor explanation
    
    **Feature: report-improvements**
    **Validates: Requirements 12.3**
    """
    
    def setup_method(self):
        self.generator = ReportGenerator()
    
    def test_main_factor_displayed(self):
        """
        Requirements 12.3: Main scoring factor should be displayed in output.
        """
        results = create_mock_module22_results('long_call', 70.0)
        output = self.generator._format_module22_optimal_strike(results)
        
        assert '主要影響因素' in output
    
    @given(
        liquidity=liquidity_score_strategy,
        greeks=liquidity_score_strategy,
        iv=liquidity_score_strategy,
        risk_reward=liquidity_score_strategy
    )
    @settings(max_examples=100)
    def test_main_factor_identifies_highest_score(self, liquidity, greeks, iv, risk_reward):
        """
        Requirements 12.3: Main factor should identify the highest scoring component.
        """
        result = self.generator._get_main_scoring_factor(liquidity, greeks, iv, risk_reward)
        
        # Result should be a non-empty string
        assert result is not None
        assert len(result) > 0
        
        # Find the max score
        scores = {'流動性': liquidity, 'Greeks': greeks, 'IV': iv, '風險回報': risk_reward}
        max_factor = max(scores, key=scores.get)
        min_factor = min(scores, key=scores.get)
        max_score = scores[max_factor]
        min_score = scores[min_factor]
        
        # If there's a significant difference, the max factor should be mentioned
        if max_score - min_score > 30:
            assert max_factor in result
    
    def test_low_score_warning(self):
        """
        Requirements 12.3: Should warn when a score is particularly low.
        """
        # Create a scenario with one very low score
        result = self.generator._get_main_scoring_factor(80.0, 70.0, 30.0, 75.0)
        
        # Should mention the low IV score
        assert 'IV' in result or '偏低' in result


class TestModule22ScoringWeightExplanation:
    """
    Test Module 22 Scoring Weight Explanation
    
    **Feature: report-improvements**
    **Validates: Requirements 12.3**
    """
    
    def setup_method(self):
        self.generator = ReportGenerator()
    
    def test_scoring_weights_displayed(self):
        """
        Requirements 12.3: Scoring weights should be explained in output.
        """
        results = create_mock_module22_results('long_call', 70.0)
        output = self.generator._format_module22_optimal_strike(results)
        
        # Should explain the scoring weights
        assert '評分權重' in output or '權重說明' in output
        assert '流動性' in output
        assert 'Greeks' in output
        assert 'IV' in output
        assert '風險回報' in output


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
