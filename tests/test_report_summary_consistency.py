import codecs
from pathlib import Path

from output_layer.delta_analyzer import DeltaAnalyzer
from output_layer.report_generator import ReportGenerator



def _build_generator(tmp_path):
    generator = ReportGenerator(output_dir=str(tmp_path))
    generator._get_direction_judgment = lambda calculation_results: ('Neutral', 'Low', 'direction unavailable')
    generator._get_iv_environment = lambda calculation_results: ('NORMAL', 'wait for clearer volatility signal')
    generator._get_recommended_strike = lambda strategy, calculation_results: None
    generator._get_risk_analysis = lambda strategy, calculation_results, raw_data: None
    generator._get_trade_recommendation = lambda direction, confidence, iv_env, calculation_results: ('NO_TRADE', 'conditions are not actionable')
    generator._format_consolidated_recommendation = lambda calculation_results: 'Consolidated recommendation\n'
    generator._format_module1_multi_confidence = lambda ticker, results: 'Module 1 multi confidence\n'
    generator._format_data_source_summary = lambda raw_data, calculation_results, api_status: 'Data source summary\n'
    return generator



def _build_inputs():
    raw_data = {
        'current_price': 210.0,
        'implied_volatility': 35.0,
        'days_to_expiration': 30,
        'eps': 1.0,
        'annual_dividend': 0.0,
        'risk_free_rate': 4.5,
        'vix': 18.0,
    }
    calculation_results = {
        'strategy_recommendations': [
            {
                'strategy_name': 'OBSERVE',
                'confidence': 'Low',
                'reasoning': ['IV Rank unavailable; IV/HV 0.94 is not extreme'],
            }
        ],
        'module18_historical_volatility': {
            'iv_rank': None,
            'iv_percentile': None,
            'iv_rank_details': {'error': 'Historical IV data is insufficient'},
        },
        'module1_support_resistance_multi': {
            'results': {'68%': {'support': 200.0, 'resistance': 220.0}},
            'days_to_expiration': 30,
        },
    }
    return raw_data, calculation_results



def test_report_summary_uses_final_strategy_recommendation(tmp_path):
    generator = _build_generator(tmp_path)
    raw_data, calculation_results = _build_inputs()

    report = generator._generate_json_report('TSLA', '2026-03-14', raw_data, calculation_results)
    summary = report['report_summary']

    assert summary['recommended_strategy'] == 'OBSERVE'
    assert summary['trade_recommendation'] == 'NO_TRADE'
    assert report['report_consistency']['status'] == 'PASS'
    assert 'Summary strategy matches final strategy_recommendations output' in report['report_consistency']['passed_checks']

    text_summary = generator._format_decision_summary('TSLA', raw_data, calculation_results)
    assert 'Recommended Strategy: OBSERVE' in text_summary
    assert 'Summary Consistency Check:' in text_summary
    assert 'Status: PASS' in text_summary



def test_text_report_uses_utf8_sig_and_marks_missing_iv_fields(tmp_path):
    generator = _build_generator(tmp_path)
    raw_data, calculation_results = _build_inputs()
    filepath = Path(tmp_path) / 'report_TSLA_test.txt'

    generator._write_text_report(str(filepath), 'TSLA', '2026-03-14', raw_data, calculation_results)

    assert filepath.read_bytes().startswith(codecs.BOM_UTF8)
    text = filepath.read_text(encoding='utf-8-sig')
    assert 'IV Rank: N/A (Historical IV data is insufficient)' in text
    assert 'IV Percentile: N/A' in text

def test_delta_analyzer_preserves_missing_iv_rank_and_cleans_alert_text():
    analyzer = DeltaAnalyzer()
    current = {
        'metadata': {'generated_at': '2026-03-14T18:20:04'},
        'raw_data': {'current_price': 391.20, 'implied_volatility': 0.42},
        'calculations': {
            'module18_historical_volatility': {'iv_rank': None},
            'module24_technical_direction': {'combined_direction': 'Put'},
            'strategy_recommendations': [{'strategy_name': 'Observe / Wait'}],
        },
    }
    previous = {
        'metadata': {'generated_at': '2026-03-14T17:35:56'},
        'raw_data': {'current_price': 384.00, 'implied_volatility': 0.38},
        'calculations': {
            'module18_historical_volatility': {'iv_rank': None},
            'module24_technical_direction': {'combined_direction': 'Call'},
            'strategy_recommendations': [{'strategy_name': 'Long Call'}],
        },
    }

    delta = analyzer.compare_results(current, previous)

    assert delta['iv_change']['current_rank'] is None
    assert delta['iv_change']['previous_rank'] is None
    assert delta['iv_change']['rank_diff'] is None
    assert 'Direction changed: Call -> Put' in delta['opportunity_alert']
    assert 'Strategy changed: [Long Call] -> [Observe / Wait]' in delta['opportunity_alert']
    assert all('?' not in alert for alert in delta['opportunity_alert'])


def test_text_report_delta_section_uses_clean_labels_and_na_for_missing_iv_rank(tmp_path):
    generator = _build_generator(tmp_path)
    raw_data, calculation_results = _build_inputs()
    filepath = Path(tmp_path) / 'report_TSLA_delta.txt'
    delta_report = {
        'opportunity_alert': ['Strategy changed: [Long Call] -> [Observe / Wait]'],
        'price_change': {'previous': 384.0, 'current': 391.2, 'pct': 1.875},
        'iv_change': {'previous_rank': None, 'current_rank': None, 'rank_diff': None},
        'strategy_change': {
            'changed': True,
            'previous_top': 'Long Call',
            'current_top': 'Observe / Wait',
        },
    }

    generator._write_text_report(
        str(filepath),
        'TSLA',
        '2026-03-14',
        raw_data,
        calculation_results,
        delta_report=delta_report,
    )

    text = filepath.read_text(encoding='utf-8-sig')
    assert 'Changes vs Last Run' in text
    assert 'Strategy changed: [Long Call] -> [Observe / Wait]' in text
    assert 'Price Change: $384.00 -> $391.20 (+1.88%)' in text
    assert 'IV Rank Change: N/A -> N/A (delta N/A)' in text
    assert 'Strategy Change: Long Call -> Observe / Wait' in text
    assert '?▽' not in text
