#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Property-based tests for Yahoo Data Parser
使用 Hypothesis 进行属性测试
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from data_layer.yahoo_finance_v2_client import YahooDataParser


class TestYahooDataParserProperties:
    """Yahoo Data Parser 属性测试"""
    
    @given(
        symbol=st.text(min_size=1, max_size=10),
        has_price=st.booleans(),
        has_open=st.booleans(),
        has_high=st.booleans(),
        has_low=st.booleans(),
        has_volume=st.booleans(),
        price=st.floats(min_value=0.01, max_value=10000, allow_nan=False, allow_infinity=False),
        open_price=st.floats(min_value=0.01, max_value=10000, allow_nan=False, allow_infinity=False),
        high_price=st.floats(min_value=0.01, max_value=10000, allow_nan=False, allow_infinity=False),
        low_price=st.floats(min_value=0.01, max_value=10000, allow_nan=False, allow_infinity=False),
        volume=st.integers(min_value=0, max_value=1000000000)
    )
    @settings(max_examples=100)
    def test_parse_quote_default_values(
        self, symbol, has_price, has_open, has_high, has_low, has_volume,
        price, open_price, high_price, low_price, volume
    ):
        """
        **Feature: yahoo-api-rate-limit-handling, Property 9: Default values for missing fields**
        **Validates: Requirements 7.3**
        
        Property: For any API response with missing optional fields, the system 
        should use appropriate default values (0 for numeric fields, None for optional fields).
        """
        # 构建响应，随机缺失某些字段
        meta = {'symbol': symbol}
        
        if has_price:
            meta['regularMarketPrice'] = price
        if has_open:
            meta['regularMarketOpen'] = open_price
        if has_high:
            meta['regularMarketDayHigh'] = high_price
        if has_low:
            meta['regularMarketDayLow'] = low_price
        if has_volume:
            meta['regularMarketVolume'] = volume
        
        response = {
            'chart': {
                'result': [{
                    'meta': meta
                }]
            }
        }
        
        # 解析响应
        result = YahooDataParser.parse_quote(response)
        
        # 验证结果不为 None
        assert result is not None, "Parser should return a dict, not None"
        
        # 验证所有字段都存在
        assert 'symbol' in result
        assert 'current_price' in result
        assert 'open' in result
        assert 'high' in result
        assert 'low' in result
        assert 'volume' in result
        
        # 验证缺失字段使用默认值 0
        assert result['current_price'] == (price if has_price else 0)
        assert result['open'] == (open_price if has_open else 0)
        assert result['high'] == (high_price if has_high else 0)
        assert result['low'] == (low_price if has_low else 0)
        assert result['volume'] == (volume if has_volume else 0)
        
        # 验证 symbol 总是存在
        assert result['symbol'] == symbol
        assert result['data_source'] == 'yahoo_finance'
    
    @given(
        has_calls=st.booleans(),
        has_puts=st.booleans(),
        has_expiration=st.booleans(),
        num_calls=st.integers(min_value=0, max_value=10),
        num_puts=st.integers(min_value=0, max_value=10),
        expiration=st.integers(min_value=1000000000, max_value=2000000000)
    )
    @settings(max_examples=100)
    def test_parse_option_chain_default_values(
        self, has_calls, has_puts, has_expiration, num_calls, num_puts, expiration
    ):
        """
        **Feature: yahoo-api-rate-limit-handling, Property 9: Default values for missing fields**
        **Validates: Requirements 7.3**
        
        Property: For any option chain response with missing optional fields, 
        the system should use appropriate default values (empty lists for calls/puts).
        """
        # 构建期权数据
        option_data = {}
        
        if has_calls:
            option_data['calls'] = [{'strike': i * 10} for i in range(num_calls)]
        if has_puts:
            option_data['puts'] = [{'strike': i * 10} for i in range(num_puts)]
        if has_expiration:
            option_data['expirationDate'] = expiration
        
        response = {
            'optionChain': {
                'result': [{
                    'options': [option_data]
                }]
            }
        }
        
        # 解析响应
        result = YahooDataParser.parse_option_chain(response)
        
        # 验证结果不为 None
        assert result is not None, "Parser should return a dict, not None"
        
        # 验证所有字段都存在
        assert 'calls' in result
        assert 'puts' in result
        assert 'expiration' in result
        
        # 验证缺失字段使用默认值
        expected_calls = [{'strike': i * 10} for i in range(num_calls)] if has_calls else []
        expected_puts = [{'strike': i * 10} for i in range(num_puts)] if has_puts else []
        
        assert result['calls'] == expected_calls
        assert result['puts'] == expected_puts
        assert result['expiration'] == (expiration if has_expiration else '')
        assert result['data_source'] == 'yahoo_finance'
    
    @given(
        has_timestamps=st.booleans(),
        has_open=st.booleans(),
        has_high=st.booleans(),
        has_low=st.booleans(),
        has_close=st.booleans(),
        has_volume=st.booleans(),
        num_points=st.integers(min_value=0, max_value=10)
    )
    @settings(max_examples=100)
    def test_parse_historical_data_default_values(
        self, has_timestamps, has_open, has_high, has_low, has_close, has_volume, num_points
    ):
        """
        **Feature: yahoo-api-rate-limit-handling, Property 9: Default values for missing fields**
        **Validates: Requirements 7.3**
        
        Property: For any historical data response with missing optional fields, 
        the system should use appropriate default values (empty lists).
        """
        # 构建历史数据
        data = {}
        quote_data = {}
        
        if has_timestamps:
            data['timestamp'] = list(range(1000000000, 1000000000 + num_points))
        if has_open:
            quote_data['open'] = [100.0 + i for i in range(num_points)]
        if has_high:
            quote_data['high'] = [110.0 + i for i in range(num_points)]
        if has_low:
            quote_data['low'] = [90.0 + i for i in range(num_points)]
        if has_close:
            quote_data['close'] = [105.0 + i for i in range(num_points)]
        if has_volume:
            quote_data['volume'] = [1000000 + i * 1000 for i in range(num_points)]
        
        data['indicators'] = {'quote': [quote_data]}
        
        response = {
            'chart': {
                'result': [data]
            }
        }
        
        # 解析响应
        result = YahooDataParser.parse_historical_data(response)
        
        # 验证结果不为 None
        assert result is not None, "Parser should return a dict, not None"
        
        # 验证所有字段都存在
        assert 'timestamps' in result
        assert 'open' in result
        assert 'high' in result
        assert 'low' in result
        assert 'close' in result
        assert 'volume' in result
        
        # 验证缺失字段使用默认值（空列表）
        expected_timestamps = list(range(1000000000, 1000000000 + num_points)) if has_timestamps else []
        expected_open = [100.0 + i for i in range(num_points)] if has_open else []
        expected_high = [110.0 + i for i in range(num_points)] if has_high else []
        expected_low = [90.0 + i for i in range(num_points)] if has_low else []
        expected_close = [105.0 + i for i in range(num_points)] if has_close else []
        expected_volume = [1000000 + i * 1000 for i in range(num_points)] if has_volume else []
        
        assert result['timestamps'] == expected_timestamps
        assert result['open'] == expected_open
        assert result['high'] == expected_high
        assert result['low'] == expected_low
        assert result['close'] == expected_close
        assert result['volume'] == expected_volume
        assert result['data_source'] == 'yahoo_finance'


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


class TestYahooDataParserErrorHandling:
    """Yahoo Data Parser 错误处理属性测试"""
    
    @given(
        malformed_type=st.sampled_from([
            'empty_dict',
            'missing_chart',
            'missing_result',
            'empty_result',
            'none_value',
            'string_instead_of_dict',
            'list_instead_of_dict'
        ])
    )
    @settings(max_examples=100)
    def test_parse_quote_error_handling(self, malformed_type):
        """
        **Feature: yahoo-api-rate-limit-handling, Property 10: Error handling for malformed responses**
        **Validates: Requirements 7.4**
        
        Property: For any API response that cannot be parsed as valid JSON or has 
        incorrect structure, the system should log the error and return None.
        
        Note: This tests structural errors (missing chart/result), not missing fields.
        Missing fields are handled by default values (Requirement 7.3).
        """
        # 构建各种格式错误的响应（结构性错误）
        if malformed_type == 'empty_dict':
            response = {}
        elif malformed_type == 'missing_chart':
            response = {'data': {}}
        elif malformed_type == 'missing_result':
            response = {'chart': {}}
        elif malformed_type == 'empty_result':
            response = {'chart': {'result': []}}
        elif malformed_type == 'none_value':
            response = None
        elif malformed_type == 'string_instead_of_dict':
            response = "invalid string response"
        elif malformed_type == 'list_instead_of_dict':
            response = [1, 2, 3]
        
        # 解析响应 - 应该返回 None 而不是抛出异常
        result = YahooDataParser.parse_quote(response)
        
        # 验证返回 None（表示解析失败）
        assert result is None, f"Parser should return None for malformed response type: {malformed_type}"
    
    @given(
        malformed_type=st.sampled_from([
            'empty_dict',
            'missing_option_chain',
            'missing_result',
            'empty_result',
            'missing_options',
            'empty_options',
            'invalid_structure',
            'none_value',
            'string_instead_of_dict',
            'list_instead_of_dict'
        ])
    )
    @settings(max_examples=100)
    def test_parse_option_chain_error_handling(self, malformed_type):
        """
        **Feature: yahoo-api-rate-limit-handling, Property 10: Error handling for malformed responses**
        **Validates: Requirements 7.4**
        
        Property: For any option chain response with incorrect structure, 
        the system should log the error and return None.
        """
        # 构建各种格式错误的响应
        if malformed_type == 'empty_dict':
            response = {}
        elif malformed_type == 'missing_option_chain':
            response = {'data': {}}
        elif malformed_type == 'missing_result':
            response = {'optionChain': {}}
        elif malformed_type == 'empty_result':
            response = {'optionChain': {'result': []}}
        elif malformed_type == 'missing_options':
            response = {'optionChain': {'result': [{}]}}
        elif malformed_type == 'empty_options':
            response = {'optionChain': {'result': [{'options': []}]}}
        elif malformed_type == 'invalid_structure':
            response = {'optionChain': {'result': [{'wrong_key': 'value'}]}}
        elif malformed_type == 'none_value':
            response = None
        elif malformed_type == 'string_instead_of_dict':
            response = "invalid string response"
        elif malformed_type == 'list_instead_of_dict':
            response = [1, 2, 3]
        
        # 解析响应 - 应该返回 None 而不是抛出异常
        result = YahooDataParser.parse_option_chain(response)
        
        # 验证返回 None（表示解析失败）
        assert result is None, f"Parser should return None for malformed response type: {malformed_type}"
    
    @given(
        malformed_type=st.sampled_from([
            'empty_dict',
            'missing_chart',
            'missing_result',
            'empty_result',
            'none_value',
            'string_instead_of_dict',
            'list_instead_of_dict'
        ])
    )
    @settings(max_examples=100)
    def test_parse_historical_data_error_handling(self, malformed_type):
        """
        **Feature: yahoo-api-rate-limit-handling, Property 10: Error handling for malformed responses**
        **Validates: Requirements 7.4**
        
        Property: For any historical data response with incorrect structure, 
        the system should log the error and return None.
        
        Note: This tests structural errors (missing chart/result), not missing fields.
        Missing fields are handled by default values (Requirement 7.3).
        """
        # 构建各种格式错误的响应（结构性错误）
        if malformed_type == 'empty_dict':
            response = {}
        elif malformed_type == 'missing_chart':
            response = {'data': {}}
        elif malformed_type == 'missing_result':
            response = {'chart': {}}
        elif malformed_type == 'empty_result':
            response = {'chart': {'result': []}}
        elif malformed_type == 'none_value':
            response = None
        elif malformed_type == 'string_instead_of_dict':
            response = "invalid string response"
        elif malformed_type == 'list_instead_of_dict':
            response = [1, 2, 3]
        
        # 解析响应 - 应该返回 None 而不是抛出异常
        result = YahooDataParser.parse_historical_data(response)
        
        # 验证返回 None（表示解析失败）
        assert result is None, f"Parser should return None for malformed response type: {malformed_type}"
    
    @given(
        response_data=st.one_of(
            st.none(),
            st.integers(),
            st.floats(allow_nan=True, allow_infinity=True),
            st.text(),
            st.lists(st.integers()),
            st.booleans()
        )
    )
    @settings(max_examples=100)
    def test_parse_quote_handles_non_dict_responses(self, response_data):
        """
        **Feature: yahoo-api-rate-limit-handling, Property 10: Error handling for malformed responses**
        **Validates: Requirements 7.4**
        
        Property: For any non-dictionary response, the parser should return None gracefully.
        """
        # 尝试解析非字典类型的响应
        result = YahooDataParser.parse_quote(response_data)
        
        # 验证返回 None（表示解析失败）
        assert result is None, f"Parser should return None for non-dict response: {type(response_data)}"
    
    @given(
        response_data=st.one_of(
            st.none(),
            st.integers(),
            st.floats(allow_nan=True, allow_infinity=True),
            st.text(),
            st.lists(st.integers()),
            st.booleans()
        )
    )
    @settings(max_examples=100)
    def test_parse_option_chain_handles_non_dict_responses(self, response_data):
        """
        **Feature: yahoo-api-rate-limit-handling, Property 10: Error handling for malformed responses**
        **Validates: Requirements 7.4**
        
        Property: For any non-dictionary response, the parser should return None gracefully.
        """
        # 尝试解析非字典类型的响应
        result = YahooDataParser.parse_option_chain(response_data)
        
        # 验证返回 None（表示解析失败）
        assert result is None, f"Parser should return None for non-dict response: {type(response_data)}"
    
    @given(
        response_data=st.one_of(
            st.none(),
            st.integers(),
            st.floats(allow_nan=True, allow_infinity=True),
            st.text(),
            st.lists(st.integers()),
            st.booleans()
        )
    )
    @settings(max_examples=100)
    def test_parse_historical_data_handles_non_dict_responses(self, response_data):
        """
        **Feature: yahoo-api-rate-limit-handling, Property 10: Error handling for malformed responses**
        **Validates: Requirements 7.4**
        
        Property: For any non-dictionary response, the parser should return None gracefully.
        """
        # 尝试解析非字典类型的响应
        result = YahooDataParser.parse_historical_data(response_data)
        
        # 验证返回 None（表示解析失败）
        assert result is None, f"Parser should return None for non-dict response: {type(response_data)}"
