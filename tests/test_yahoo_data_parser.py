#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
YahooDataParser 單元測試

測試 Yahoo Finance V2 數據解析器的所有方法。
"""

import pytest
import sys
import os

# 添加項目根目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_layer.yahoo_finance_v2_client import YahooDataParser


class TestYahooDataParserQuote:
    """測試 parse_quote() 方法"""
    
    def test_parse_valid_quote_response(self):
        """測試解析有效的 quote 響應"""
        # 模擬 Yahoo Finance Chart API 響應
        mock_response = {
            'chart': {
                'result': [{
                    'meta': {
                        'symbol': 'AAPL',
                        'regularMarketPrice': 150.25,
                        'regularMarketOpen': 149.50,
                        'regularMarketDayHigh': 151.00,
                        'regularMarketDayLow': 149.00,
                        'regularMarketVolume': 50000000,
                        'previousClose': 148.75
                    }
                }]
            }
        }
        
        result = YahooDataParser.parse_quote(mock_response)
        
        assert result is not None
        assert result['symbol'] == 'AAPL'
        assert result['current_price'] == 150.25
        assert result['open'] == 149.50
        assert result['high'] == 151.00
        assert result['low'] == 149.00
        assert result['volume'] == 50000000
        assert result['previous_close'] == 148.75
        assert result['data_source'] == 'yahoo_finance'
    
    def test_parse_quote_with_missing_optional_fields(self):
        """測試解析缺少可選字段的響應"""
        mock_response = {
            'chart': {
                'result': [{
                    'meta': {
                        'symbol': 'AAPL',
                        'regularMarketPrice': 150.25
                        # 缺少其他字段
                    }
                }]
            }
        }
        
        result = YahooDataParser.parse_quote(mock_response)
        
        assert result is not None
        assert result['symbol'] == 'AAPL'
        assert result['current_price'] == 150.25
        # 缺失字段應該有默認值
        assert result['open'] == 0
        assert result['volume'] == 0
    
    def test_parse_quote_empty_result(self):
        """測試解析空結果"""
        mock_response = {
            'chart': {
                'result': []
            }
        }
        
        result = YahooDataParser.parse_quote(mock_response)
        
        assert result is None
    
    def test_parse_quote_missing_chart_key(self):
        """測試缺少 chart 鍵的響應"""
        mock_response = {
            'error': 'Invalid symbol'
        }
        
        result = YahooDataParser.parse_quote(mock_response)
        
        assert result is None
    
    def test_parse_quote_invalid_response_type(self):
        """測試無效的響應類型"""
        result = YahooDataParser.parse_quote(None)
        assert result is None
        
        result = YahooDataParser.parse_quote("invalid")
        assert result is None
        
        result = YahooDataParser.parse_quote([])
        assert result is None
    
    def test_parse_quote_missing_meta(self):
        """測試缺少 meta 的響應"""
        mock_response = {
            'chart': {
                'result': [{}]  # 沒有 meta
            }
        }
        
        result = YahooDataParser.parse_quote(mock_response)
        
        # 應該返回結果，但字段為默認值
        assert result is not None
        assert result['symbol'] == ''
        assert result['current_price'] == 0


class TestYahooDataParserOptionChain:
    """測試 parse_option_chain() 方法"""
    
    def test_parse_valid_option_chain(self):
        """測試解析有效的期權鏈響應"""
        mock_response = {
            'optionChain': {
                'result': [{
                    'options': [{
                        'expirationDate': 1704067200,
                        'calls': [
                            {
                                'contractSymbol': 'AAPL250101C00150000',
                                'strike': 150.0,
                                'lastPrice': 5.25,
                                'bid': 5.20,
                                'ask': 5.30,
                                'volume': 1000,
                                'openInterest': 5000,
                                'impliedVolatility': 0.25
                            }
                        ],
                        'puts': [
                            {
                                'contractSymbol': 'AAPL250101P00150000',
                                'strike': 150.0,
                                'lastPrice': 4.75,
                                'bid': 4.70,
                                'ask': 4.80,
                                'volume': 800,
                                'openInterest': 4000,
                                'impliedVolatility': 0.23
                            }
                        ]
                    }]
                }]
            }
        }
        
        result = YahooDataParser.parse_option_chain(mock_response)
        
        assert result is not None
        assert len(result['calls']) == 1
        assert len(result['puts']) == 1
        assert result['expiration'] == 1704067200
        assert result['data_source'] == 'yahoo_finance'
        
        # 驗證 call 數據
        call = result['calls'][0]
        assert call['contractSymbol'] == 'AAPL250101C00150000'
        assert call['strike'] == 150.0
        assert call['lastPrice'] == 5.25
        
        # 驗證 put 數據
        put = result['puts'][0]
        assert put['contractSymbol'] == 'AAPL250101P00150000'
        assert put['strike'] == 150.0
        assert put['lastPrice'] == 4.75
    
    def test_parse_option_chain_empty_result(self):
        """測試解析空結果"""
        mock_response = {
            'optionChain': {
                'result': []
            }
        }
        
        result = YahooDataParser.parse_option_chain(mock_response)
        
        assert result is None
    
    def test_parse_option_chain_no_options(self):
        """測試沒有期權數據的響應"""
        mock_response = {
            'optionChain': {
                'result': [{
                    'options': []
                }]
            }
        }
        
        result = YahooDataParser.parse_option_chain(mock_response)
        
        assert result is None
    
    def test_parse_option_chain_missing_key(self):
        """測試缺少關鍵字段的響應"""
        mock_response = {
            'error': 'No options available'
        }
        
        result = YahooDataParser.parse_option_chain(mock_response)
        
        assert result is None
    
    def test_parse_option_chain_empty_calls_and_puts(self):
        """測試 calls 和 puts 都為空的情況"""
        mock_response = {
            'optionChain': {
                'result': [{
                    'options': [{
                        'expirationDate': 1704067200,
                        'calls': [],
                        'puts': []
                    }]
                }]
            }
        }
        
        result = YahooDataParser.parse_option_chain(mock_response)
        
        # 應該返回結果，但 calls 和 puts 為空列表
        assert result is not None
        assert result['calls'] == []
        assert result['puts'] == []


class TestYahooDataParserHistoricalData:
    """測試 parse_historical_data() 方法"""
    
    def test_parse_valid_historical_data(self):
        """測試解析有效的歷史數據響應"""
        mock_response = {
            'chart': {
                'result': [{
                    'timestamp': [1700000000, 1700086400, 1700172800],
                    'indicators': {
                        'quote': [{
                            'open': [150.0, 151.0, 152.0],
                            'high': [151.5, 152.5, 153.5],
                            'low': [149.5, 150.5, 151.5],
                            'close': [151.0, 152.0, 153.0],
                            'volume': [50000000, 55000000, 60000000]
                        }]
                    }
                }]
            }
        }
        
        result = YahooDataParser.parse_historical_data(mock_response)
        
        assert result is not None
        assert len(result['timestamps']) == 3
        assert len(result['open']) == 3
        assert len(result['high']) == 3
        assert len(result['low']) == 3
        assert len(result['close']) == 3
        assert len(result['volume']) == 3
        assert result['data_source'] == 'yahoo_finance'
        
        # 驗證數據值
        assert result['timestamps'][0] == 1700000000
        assert result['open'][0] == 150.0
        assert result['close'][2] == 153.0
    
    def test_parse_historical_data_empty_result(self):
        """測試解析空結果"""
        mock_response = {
            'chart': {
                'result': []
            }
        }
        
        result = YahooDataParser.parse_historical_data(mock_response)
        
        assert result is None
    
    def test_parse_historical_data_no_timestamps(self):
        """測試沒有時間戳的響應"""
        mock_response = {
            'chart': {
                'result': [{
                    'timestamp': [],
                    'indicators': {
                        'quote': [{
                            'open': [],
                            'high': [],
                            'low': [],
                            'close': [],
                            'volume': []
                        }]
                    }
                }]
            }
        }
        
        result = YahooDataParser.parse_historical_data(mock_response)
        
        assert result is None
    
    def test_parse_historical_data_missing_indicators(self):
        """測試缺少 indicators 的響應"""
        mock_response = {
            'chart': {
                'result': [{
                    'timestamp': [1700000000]
                }]
            }
        }
        
        result = YahooDataParser.parse_historical_data(mock_response)
        
        assert result is None
    
    def test_parse_historical_data_length_mismatch(self):
        """測試數據長度不一致的情況"""
        mock_response = {
            'chart': {
                'result': [{
                    'timestamp': [1700000000, 1700086400, 1700172800],
                    'indicators': {
                        'quote': [{
                            'open': [150.0, 151.0],  # 只有 2 個元素
                            'high': [151.5, 152.5, 153.5],
                            'low': [149.5, 150.5, 151.5],
                            'close': [151.0, 152.0, 153.0],
                            'volume': [50000000, 55000000, 60000000]
                        }]
                    }
                }]
            }
        }
        
        result = YahooDataParser.parse_historical_data(mock_response)
        
        # 應該返回結果，但會記錄警告
        assert result is not None
        assert len(result['timestamps']) == 3
        assert len(result['open']) == 2  # 長度不匹配


class TestYahooDataParserEdgeCases:
    """測試邊界情況和錯誤處理"""
    
    def test_parse_with_none_response(self):
        """測試 None 響應"""
        assert YahooDataParser.parse_quote(None) is None
        assert YahooDataParser.parse_option_chain(None) is None
        assert YahooDataParser.parse_historical_data(None) is None
    
    def test_parse_with_empty_dict(self):
        """測試空字典響應"""
        assert YahooDataParser.parse_quote({}) is None
        assert YahooDataParser.parse_option_chain({}) is None
        assert YahooDataParser.parse_historical_data({}) is None
    
    def test_parse_with_malformed_data(self):
        """測試格式錯誤的數據"""
        malformed = {
            'chart': {
                'result': [
                    {
                        'meta': 'not_a_dict'  # 應該是字典
                    }
                ]
            }
        }
        
        # 應該優雅地處理錯誤
        result = YahooDataParser.parse_quote(malformed)
        # 可能返回 None 或部分數據，取決於實現


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
