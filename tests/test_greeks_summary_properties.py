#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pytest
from hypothesis import given, strategies as st, settings
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from output_layer.report_generator import ReportGenerator

delta_strategy = st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False)
gamma_strategy = st.floats(min_value=0.0, max_value=0.2, allow_nan=False, allow_infinity=False)
theta_strategy = st.floats(min_value=-5.0, max_value=0.0, allow_nan=False, allow_infinity=False)
vega_strategy = st.floats(min_value=0.0, max_value=2.0, allow_nan=False, allow_infinity=False)
rho_strategy = st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False)

class TestDeltaInterpretation:
    def setup_method(self):
        self.generator = ReportGenerator()

    @given(delta=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))
    @settings(max_examples=100)
    def test_call_delta_completeness(self, delta):
        result = self.generator._get_delta_interpretation(delta, 'call')
        assert 'direction' in result
        assert 'probability_hint' in result
        assert 'sensitivity' in result

    @given(delta=st.floats(min_value=-1.0, max_value=0.0, allow_nan=False, allow_infinity=False))
    @settings(max_examples=100)
    def test_put_delta_completeness(self, delta):
        result = self.generator._get_delta_interpretation(delta, 'put')
        assert 'direction' in result
        assert 'probability_hint' in result

    def test_delta_none_handling(self):
        result = self.generator._get_delta_interpretation(None, 'call')
        assert result['direction']

class TestThetaInterpretation:
    def setup_method(self):
        self.generator = ReportGenerator()

    @given(theta=st.floats(min_value=-5.0, max_value=0.0, allow_nan=False, allow_infinity=False))
    @settings(max_examples=100)
    def test_theta_completeness(self, theta):
        result = self.generator._get_theta_interpretation(theta)
        assert 'daily_decay' in result
        assert 'weekly_decay' in result
        assert 'decay_rate' in result
        assert 'strategy_hint' in result

    def test_theta_none_handling(self):
        result = self.generator._get_theta_interpretation(None)
        assert result['daily_decay']

class TestVegaInterpretation:
    def setup_method(self):
        self.generator = ReportGenerator()

    @given(vega=st.floats(min_value=0.0, max_value=2.0, allow_nan=False, allow_infinity=False))
    @settings(max_examples=100)
    def test_vega_completeness(self, vega):
        result = self.generator._get_vega_interpretation(vega)
        assert 'sensitivity' in result
        assert 'iv_impact' in result
        assert 'risk_level' in result
        assert 'strategy_hint' in result

    def test_vega_none_handling(self):
        result = self.generator._get_vega_interpretation(None)
        assert result['sensitivity']

class TestGammaWarning:
    def setup_method(self):
        self.generator = ReportGenerator()

    @given(gamma=st.floats(min_value=0.0, max_value=0.2, allow_nan=False, allow_infinity=False))
    @settings(max_examples=100)
    def test_gamma_completeness(self, gamma):
        result = self.generator._get_gamma_warning(gamma)
        assert 'warning_level' in result
        assert 'delta_change_hint' in result
        assert 'risk_description' in result
        assert 'action_hint' in result

    def test_gamma_none_handling(self):
        result = self.generator._get_gamma_warning(None)
        assert result['warning_level']

class TestOverallGreeksAssessment:
    def setup_method(self):
        self.generator = ReportGenerator()

    @given(
        call_delta=delta_strategy,
        call_gamma=gamma_strategy,
        call_theta=theta_strategy,
        call_vega=vega_strategy
    )
    @settings(max_examples=100)
    def test_overall_assessment_completeness(self, call_delta, call_gamma, call_theta, call_vega):
        call_greeks = {
            'delta': call_delta,
            'gamma': call_gamma,
            'theta': call_theta,
            'vega': call_vega
        }
        result = self.generator._get_overall_greeks_assessment(call_greeks)
        assert 'overall_risk' in result
        assert 'key_risks' in result
        assert 'recommendations' in result
        assert isinstance(result['key_risks'], list)
        assert isinstance(result['recommendations'], list)

    def test_empty_greeks_handling(self):
        result = self.generator._get_overall_greeks_assessment(None, None)
        assert 'overall_risk' in result
        assert 'key_risks' in result
        assert 'recommendations' in result

class TestFormatModule16Greeks:
    def setup_method(self):
        self.generator = ReportGenerator()

    @given(
        call_delta=delta_strategy,
        call_gamma=gamma_strategy,
        call_theta=theta_strategy,
        call_vega=vega_strategy,
        call_rho=rho_strategy
    )
    @settings(max_examples=100)
    def test_format_greeks_contains_all(self, call_delta, call_gamma, call_theta, call_vega, call_rho):
        greeks_data = {
            'call': {
                'delta': call_delta,
                'gamma': call_gamma,
                'theta': call_theta,
                'vega': call_vega,
                'rho': call_rho
            }
        }
        result = self.generator._format_module16_greeks(greeks_data)
        assert 'Delta' in result
        assert 'Theta' in result
        assert 'Vega' in result

if __name__ == '__main__':
    pytest.main([__file__, '-v'])