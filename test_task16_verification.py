#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Task 16 Verification Script
Tests the API degradation chain and retry mechanisms
"""

import sys
import os
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_layer.data_fetcher import DataFetcher


def test_fallback_triggers_defined():
    """Test that FALLBACK_TRIGGERS includes all required error types"""
    print("\n" + "="*80)
    print("Test 1: FALLBACK_TRIGGERS Definition")
    print("="*80)
    
    # Check if FALLBACK_TRIGGERS is defined
    assert hasattr(DataFetcher, 'FALLBACK_TRIGGERS'), \
        "FALLBACK_TRIGGERS not defined in DataFetcher"
    
    triggers = DataFetcher.FALLBACK_TRIGGERS
    print(f"✓ FALLBACK_TRIGGERS defined: {triggers}")
    
    # Check if it includes required error types
    assert ConnectionError in triggers, "ConnectionError not in FALLBACK_TRIGGERS"
    assert TimeoutError in triggers, "TimeoutError not in FALLBACK_TRIGGERS"
    
    print("✓ FALLBACK_TRIGGERS includes ConnectionError and TimeoutError")
    print("✓ Test PASSED\n")


def test_retry_with_backoff_exists():
    """Test that _retry_with_backoff method exists"""
    print("\n" + "="*80)
    print("Test 2: _retry_with_backoff Method")
    print("="*80)
    
    with patch('data_layer.data_fetcher.IBKR_AVAILABLE', False):
        fetcher = DataFetcher(use_ibkr=False)
    
    # Check if method exists
    assert hasattr(fetcher, '_retry_with_backoff'), \
        "_retry_with_backoff method not found in DataFetcher"
    
    print("✓ _retry_with_backoff method exists")
    print("✓ Test PASSED\n")


def test_fetch_with_fallback_exists():
    """Test that _fetch_with_fallback method exists"""
    print("\n" + "="*80)
    print("Test 3: _fetch_with_fallback Method")
    print("="*80)
    
    with patch('data_layer.data_fetcher.IBKR_AVAILABLE', False):
        fetcher = DataFetcher(use_ibkr=False)
    
    # Check if method exists
    assert hasattr(fetcher, '_fetch_with_fallback'), \
        "_fetch_with_fallback method not found in DataFetcher"
    
    print("✓ _fetch_with_fallback method exists")
    print("✓ Test PASSED\n")


def test_api_failures_tracking():
    """Test that api_failures dictionary is initialized"""
    print("\n" + "="*80)
    print("Test 4: API Failures Tracking")
    print("="*80)
    
    with patch('data_layer.data_fetcher.IBKR_AVAILABLE', False):
        fetcher = DataFetcher(use_ibkr=False)
    
    # Check if api_failures exists
    assert hasattr(fetcher, 'api_failures'), \
        "api_failures attribute not found in DataFetcher"
    
    assert isinstance(fetcher.api_failures, dict), \
        "api_failures is not a dictionary"
    
    print("✓ api_failures dictionary initialized")
    print("✓ Test PASSED\n")


def test_degradation_chain_basic():
    """Test basic degradation chain functionality"""
    print("\n" + "="*80)
    print("Test 5: Basic Degradation Chain")
    print("="*80)
    
    with patch('data_layer.data_fetcher.IBKR_AVAILABLE', False):
        fetcher = DataFetcher(use_ibkr=False)
    
    # Mock sources
    def source1_fail():
        raise ConnectionError("Source 1 failed")
    
    def source2_success():
        return {"data": "from source 2"}
    
    sources = ['source1', 'source2']
    fetch_map = {
        'source1': source1_fail,
        'source2': source2_success
    }
    
    # Test degradation
    result = fetcher._fetch_with_fallback('test_data', sources, fetch_map)
    
    assert result is not None, "Degradation chain failed to return data"
    assert result['data'] == 'from source 2', "Wrong data returned"
    
    print("✓ Degradation chain successfully fell back to source2")
    print(f"✓ Result: {result}")
    print("✓ Test PASSED\n")


def main():
    """Run all verification tests"""
    print("\n" + "="*80)
    print("TASK 16 VERIFICATION - API Degradation Chain and Retry Mechanisms")
    print("="*80)
    
    tests = [
        ("FALLBACK_TRIGGERS Definition", test_fallback_triggers_defined),
        ("_retry_with_backoff Method", test_retry_with_backoff_exists),
        ("_fetch_with_fallback Method", test_fetch_with_fallback_exists),
        ("API Failures Tracking", test_api_failures_tracking),
        ("Basic Degradation Chain", test_degradation_chain_basic),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"\n✗ Test FAILED: {test_name}")
            print(f"  Error: {e}\n")
            failed += 1
        except Exception as e:
            print(f"\n✗ Test ERROR: {test_name}")
            print(f"  Error: {e}\n")
            failed += 1
    
    print("\n" + "="*80)
    print("VERIFICATION SUMMARY")
    print("="*80)
    print(f"Total Tests: {len(tests)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print("="*80 + "\n")
    
    return failed == 0


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
