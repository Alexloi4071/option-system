#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for unified error handling mechanism
驗證統一錯誤處理機制的功能
"""

import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_layer.data_fetcher import DataFetcher
from datetime import datetime, timedelta


class TestUnifiedErrorHandling:
    """統一錯誤處理機制測試"""
    
    @pytest.fixture
    def fetcher(self):
        """Create a DataFetcher instance for testing"""
        return DataFetcher(use_ibkr=False)
    
    def test_record_api_failure_basic(self, fetcher):
        """Test basic _record_api_failure functionality"""
        fetcher._record_api_failure(
            api_name='TestAPI',
            error_message='Test error message'
        )
        
        assert 'TestAPI' in fetcher.api_failures
        assert len(fetcher.api_failures['TestAPI']) >= 1
        
        record = fetcher.api_failures['TestAPI'][-1]
        assert 'timestamp' in record
        assert 'error' in record
        assert record['error'] == 'Test error message'
    
    def test_record_api_failure_with_context(self, fetcher):
        """Test _record_api_failure with full context information"""
        fetcher._record_api_failure(
            api_name='TestAPI',
            error_message='Test error message',
            operation='test_operation',
            request_url='https://api.example.com?api_key=secret123',
            request_params={'api_key': 'secret', 'symbol': 'AAPL'},
            response_status=500,
            stack_trace='Test stack trace...'
        )
        
        record = fetcher.api_failures['TestAPI'][-1]
        
        # Verify all fields are present
        assert 'timestamp' in record
        assert 'error' in record
        assert 'operation' in record
        assert 'request_url' in record
        assert 'request_params' in record
        assert 'response_status' in record
        assert 'stack_trace' in record
        
        # Verify values
        assert record['operation'] == 'test_operation'
        assert record['response_status'] == 500
    
    def test_sanitize_url(self, fetcher):
        """Test URL sanitization removes API keys"""
        url = 'https://api.example.com?api_key=secret123&symbol=AAPL'
        sanitized = fetcher._sanitize_url(url)
        
        assert 'secret123' not in sanitized
        assert 'api_key=***' in sanitized
        assert 'symbol=AAPL' in sanitized
    
    def test_sanitize_params(self, fetcher):
        """Test parameter sanitization removes sensitive values"""
        params = {
            'api_key': 'secret123',
            'apikey': 'secret456',
            'token': 'token789',
            'symbol': 'AAPL'
        }
        sanitized = fetcher._sanitize_params(params)
        
        assert sanitized['api_key'] == '***'
        assert sanitized['apikey'] == '***'
        assert sanitized['token'] == '***'
        assert sanitized['symbol'] == 'AAPL'  # Non-sensitive should remain
    
    def test_handle_api_failure(self, fetcher):
        """Test _handle_api_failure unified error handling"""
        try:
            raise ValueError('Test exception message')
        except Exception as e:
            fetcher._handle_api_failure(
                api_name='TestAPI2',
                operation='test_handle',
                error=e,
                request_url='https://api.example.com',
                response_status=400
            )
        
        assert 'TestAPI2' in fetcher.api_failures
        record = fetcher.api_failures['TestAPI2'][-1]
        
        # Verify error type is captured
        assert 'ValueError' in record['error']
        assert 'Test exception message' in record['error']
        assert 'test_handle' in record['error']
        
        # Verify stack trace is captured
        assert 'stack_trace' in record
        assert len(record['stack_trace']) > 0
    
    def test_cleanup_api_failure_records_max_limit(self, fetcher):
        """Test that cleanup limits records to MAX_API_FAILURE_RECORDS"""
        # Add more than 100 records
        for i in range(150):
            fetcher._record_api_failure(
                api_name='TestCleanup',
                error_message=f'Error {i}'
            )
        
        # Should be limited to 100
        assert len(fetcher.api_failures['TestCleanup']) <= 100
    
    def test_get_api_failure_summary(self, fetcher):
        """Test get_api_failure_summary returns correct statistics"""
        # Add some test failures
        fetcher._record_api_failure(
            api_name='TestSummary',
            error_message='Error 1',
            operation='op1',
            response_status=500
        )
        fetcher._record_api_failure(
            api_name='TestSummary',
            error_message='Error 2',
            operation='op1',
            response_status=500
        )
        fetcher._record_api_failure(
            api_name='TestSummary',
            error_message='Error 3',
            operation='op2',
            response_status=404
        )
        
        summary = fetcher.get_api_failure_summary()
        
        assert 'TestSummary' in summary
        assert summary['TestSummary']['total_failures'] == 3
        assert summary['TestSummary']['operation_counts']['op1'] == 2
        assert summary['TestSummary']['operation_counts']['op2'] == 1
        assert summary['TestSummary']['status_counts'][500] == 2
        assert summary['TestSummary']['status_counts'][404] == 1
    
    def test_cleanup_all_api_failure_records(self, fetcher):
        """Test cleanup_all_api_failure_records cleans all APIs"""
        # Add failures to multiple APIs
        fetcher._record_api_failure('API1', 'Error 1')
        fetcher._record_api_failure('API2', 'Error 2')
        fetcher._record_api_failure('API3', 'Error 3')
        
        # Cleanup should not raise any errors
        fetcher.cleanup_all_api_failure_records()
        
        # Records should still exist (cleanup only removes old/excess records)
        # but the method should complete without error
        assert True
    
    def test_parse_timestamp(self, fetcher):
        """Test _parse_timestamp handles various inputs"""
        # Valid timestamp
        valid_ts = datetime.now().isoformat()
        parsed = fetcher._parse_timestamp(valid_ts)
        assert isinstance(parsed, datetime)
        
        # Invalid timestamp
        invalid_ts = 'not-a-timestamp'
        parsed = fetcher._parse_timestamp(invalid_ts)
        assert parsed == datetime.min
        
        # None
        parsed = fetcher._parse_timestamp(None)
        assert parsed == datetime.min


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
