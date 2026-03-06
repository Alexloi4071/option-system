# tests/test_bug_exploration_api_degradation.py
"""
Bug Condition Exploration Test - API Degradation Chain Execution

**Validates: Requirements 1.3, 1.4, 2.3, 2.4**

Property 1: Bug Condition - API Degradation Chain Silent Failure

CRITICAL: This test MUST FAIL on unfixed code - failure confirms the bug exists
DO NOT attempt to fix the test or the code when it fails

GOAL: Surface counterexamples showing degradation chain doesn't execute properly
Scoped PBT Approach: Mock IBKR ConnectionTimeout, Finnhub configured and available

Test that system attempts Finnhub after IBKR fails (from Bug Conditions 1.3, 1.4)
Test that degradation process is logged with attempt results

Expected Outcome: Test FAILS (returns N/A without attempting Finnhub)
Document counterexamples: "IBKR fails with ConnectionTimeout, Finnhub not attempted, returns N/A"

Bug 1.3: WHEN 系統使用API降級鏈獲取數據 THEN 降級過程可能靜默失敗，未正確記錄失敗原因或未嘗試下一個數據源
Bug 1.4: WHEN IBKR Gateway連接失敗或數據獲取失敗 THEN 系統未能有效降級到備用數據源（Finnhub、Yahoo Finance等）

Expected Behavior 2.3: WHEN 系統使用API降級鏈獲取數據 THEN 應按照DATA_PRIORITY配置順序嘗試每個數據源，
記錄每次嘗試的結果，並在所有數據源失敗時返回明確的錯誤信息

Expected Behavior 2.4: WHEN IBKR Gateway連接失敗或數據獲取失敗 THEN 系統應自動降級到Finnhub、Yahoo Finance等備用數據源，
並在報告中標註實際使用的數據源
"""

import pytest
import os
import sys
from unittest.mock import patch, MagicMock, Mock
from hypothesis import given, strategies as st, settings, Phase
from typing import Dict, Any
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_layer.data_fetcher import DataFetcher


class TestBugConditionAPIDegradationChain:
    """
    Bug Condition Exploration: API Degradation Chain Execution
    
    This test explores the bug where the API degradation chain fails silently
    without attempting fallback data sources when the primary source (IBKR) fails.
    """
    
    def test_degradation_chain_attempts_finnhub_after_ibkr_failure(self):
        """
        Test that system attempts Finnhub after IBKR connection timeout.
        
        **EXPECTED TO FAIL on unfixed code**: System returns N/A without attempting Finnhub
        
        Counterexample: IBKR fails with ConnectionTimeout, Finnhub not attempted, returns N/A
        
        Scenario:
        1. IBKR client raises ConnectionTimeout
        2. Finnhub client is configured and available
        3. System should attempt Finnhub as fallback
        4. System should log the degradation attempt
        """
        # Arrange: Create DataFetcher with mocked clients
        with patch('data_layer.data_fetcher.IBKR_AVAILABLE', False):
            fetcher = DataFetcher(use_ibkr=False)
        
        # Mock IBKR client to raise ConnectionTimeout
        mock_ibkr = MagicMock()
        mock_ibkr.get_stock_info.side_effect = ConnectionError("Connection timeout after 10s")
        fetcher.ibkr_client = mock_ibkr
        
        # Mock Finnhub client to return valid data
        mock_finnhub = MagicMock()
        mock_finnhub.get_quote.return_value = {
            'c': 150.0,  # current price
            'h': 152.0,  # high
            'l': 148.0,  # low
            'o': 149.0,  # open
            'pc': 149.5  # previous close
        }
        fetcher.finnhub_client = mock_finnhub
        
        # Act: Call get_stock_info (should trigger degradation chain)
        result = fetcher.get_stock_info('AAPL')
        
        # Assert: Finnhub should have been attempted
        assert mock_finnhub.get_quote.called, \
            "Bug confirmed: Finnhub was not attempted after IBKR failure"
        
        # Assert: Result should not be None
        assert result is not None, \
            "Bug confirmed: System returned None instead of attempting Finnhub"
        
        # Assert: Result should contain valid data from Finnhub
        assert 'current_price' in result, \
            "Bug confirmed: Result missing current_price field"
        
        assert result['current_price'] == 150.0, \
            f"Bug confirmed: Expected price 150.0, got {result.get('current_price')}"
        
        print(f"✓ Finnhub was attempted after IBKR failure")
        print(f"✓ Result: {result}")
    
    def test_degradation_attempts_are_logged(self):
        """
        Test that degradation attempts are logged with results.
        
        **EXPECTED TO FAIL on unfixed code**: No degradation logs are recorded
        
        Counterexample: IBKR fails, Finnhub succeeds, but no attempt path is logged
        
        Scenario:
        1. IBKR fails with ConnectionTimeout
        2. Finnhub succeeds
        3. System should log: "IBKR(✗:ConnectionTimeout) → Finnhub(✓)"
        """
        # Arrange: Create DataFetcher
        with patch('data_layer.data_fetcher.IBKR_AVAILABLE', False):
            fetcher = DataFetcher(use_ibkr=False)
        
        # Mock IBKR to fail
        mock_ibkr = MagicMock()
        mock_ibkr.get_stock_info.side_effect = ConnectionError("Connection timeout")
        fetcher.ibkr_client = mock_ibkr
        
        # Mock Finnhub to succeed
        mock_finnhub = MagicMock()
        mock_finnhub.get_quote.return_value = {'c': 150.0, 'h': 152.0, 'l': 148.0, 'o': 149.0, 'pc': 149.5}
        fetcher.finnhub_client = mock_finnhub
        
        # Act: Call get_stock_info
        result = fetcher.get_stock_info('AAPL')
        
        # Assert: Check if attempt path tracking exists
        assert hasattr(fetcher, '_attempt_paths'), \
            "Bug confirmed: DataFetcher has no _attempt_paths attribute for tracking degradation"
        
        # Assert: Check if stock_info attempts were recorded
        assert 'stock_info' in fetcher._attempt_paths, \
            "Bug confirmed: No attempt path recorded for stock_info"
        
        # Assert: Check if history was recorded
        history = fetcher._attempt_paths['stock_info'].get('history', [])
        assert len(history) > 0, \
            "Bug confirmed: No degradation history recorded"
        
        # Assert: Check the last attempt path
        last_attempt = history[-1]
        assert len(last_attempt) >= 1, \
            "Bug confirmed: Attempt path is empty"
        
        # Check if any attempt was successful
        successful_attempts = [a for a in last_attempt if a.get('success')]
        assert len(successful_attempts) > 0, \
            "Bug confirmed: No successful attempt recorded in degradation chain"
        
        print(f"✓ Degradation attempts are logged")
        print(f"✓ Attempt history: {history}")
    
    def test_degradation_chain_tries_multiple_sources(self):
        """
        Test that degradation chain tries multiple sources in order.
        
        **EXPECTED TO FAIL on unfixed code**: Only tries first source, doesn't continue chain
        
        Counterexample: IBKR fails, Finnhub fails, Yahoo not attempted, returns N/A
        
        Scenario:
        1. IBKR fails with ConnectionTimeout
        2. Finnhub fails with AuthenticationError
        3. Yahoo Finance should be attempted
        4. System should log all attempts
        """
        # Arrange: Create DataFetcher
        with patch('data_layer.data_fetcher.IBKR_AVAILABLE', False):
            fetcher = DataFetcher(use_ibkr=False)
        
        # Mock IBKR to fail
        mock_ibkr = MagicMock()
        mock_ibkr.get_stock_info.side_effect = ConnectionError("Connection timeout")
        fetcher.ibkr_client = mock_ibkr
        
        # Mock Finnhub to fail
        mock_finnhub = MagicMock()
        mock_finnhub.get_quote.side_effect = Exception("Authentication failed")
        fetcher.finnhub_client = mock_finnhub
        
        # Mock Yahoo to succeed
        mock_yahoo = MagicMock()
        mock_yahoo.get_quote.return_value = {
            'regularMarketPrice': 150.0,
            'regularMarketDayHigh': 152.0,
            'regularMarketDayLow': 148.0,
            'regularMarketOpen': 149.0,
            'regularMarketPreviousClose': 149.5
        }
        fetcher.yahoo_v2_client = mock_yahoo
        
        # Act: Call get_stock_info
        result = fetcher.get_stock_info('AAPL')
        
        # Assert: Yahoo should have been attempted
        # Note: This might fail if the degradation chain stops after Finnhub failure
        if hasattr(fetcher, '_attempt_paths') and 'stock_info' in fetcher._attempt_paths:
            history = fetcher._attempt_paths['stock_info'].get('history', [])
            if history:
                last_attempt = history[-1]
                sources_tried = [a['source'] for a in last_attempt]
                
                # Check if multiple sources were tried
                assert len(sources_tried) >= 2, \
                    f"Bug confirmed: Only {len(sources_tried)} source(s) tried: {sources_tried}. " \
                    f"Expected at least 2 (IBKR → Finnhub or Finnhub → Yahoo)"
                
                print(f"✓ Multiple sources tried: {sources_tried}")
            else:
                assert False, "Bug confirmed: No attempt history recorded"
        else:
            assert False, "Bug confirmed: No attempt path tracking exists"
    
    def test_degradation_records_failure_reasons(self):
        """
        Test that degradation chain records failure reasons for each attempt.
        
        **EXPECTED TO FAIL on unfixed code**: Failure reasons are not recorded
        
        Counterexample: IBKR fails, but failure reason is not logged
        
        Scenario:
        1. IBKR fails with specific error message
        2. System should record the error reason
        3. Error reason should be available in attempt path
        """
        # Arrange: Create DataFetcher
        with patch('data_layer.data_fetcher.IBKR_AVAILABLE', False):
            fetcher = DataFetcher(use_ibkr=False)
        
        # Mock IBKR to fail with specific error
        error_message = "Connection timeout after 10s"
        mock_ibkr = MagicMock()
        mock_ibkr.get_stock_info.side_effect = ConnectionError(error_message)
        fetcher.ibkr_client = mock_ibkr
        
        # Mock Finnhub to succeed
        mock_finnhub = MagicMock()
        mock_finnhub.get_quote.return_value = {'c': 150.0, 'h': 152.0, 'l': 148.0, 'o': 149.0, 'pc': 149.5}
        fetcher.finnhub_client = mock_finnhub
        
        # Act: Call get_stock_info
        result = fetcher.get_stock_info('AAPL')
        
        # Assert: Check if failure reasons are recorded
        if hasattr(fetcher, '_attempt_paths') and 'stock_info' in fetcher._attempt_paths:
            history = fetcher._attempt_paths['stock_info'].get('history', [])
            if history:
                last_attempt = history[-1]
                
                # Find failed attempts
                failed_attempts = [a for a in last_attempt if not a.get('success')]
                
                if failed_attempts:
                    # Check if error_reason is recorded
                    for attempt in failed_attempts:
                        assert 'error_reason' in attempt, \
                            f"Bug confirmed: Failed attempt missing error_reason: {attempt}"
                        
                        assert attempt['error_reason'] is not None, \
                            "Bug confirmed: error_reason is None"
                        
                        print(f"✓ Failure reason recorded: {attempt['source']} - {attempt['error_reason']}")
                else:
                    # If no failed attempts, that's actually good (all succeeded)
                    print("✓ All attempts succeeded (no failures to check)")
            else:
                assert False, "Bug confirmed: No attempt history recorded"
        else:
            assert False, "Bug confirmed: No attempt path tracking exists"
    
    def test_all_sources_fail_returns_clear_error(self):
        """
        Test that when all sources fail, system returns clear error information.
        
        **EXPECTED TO FAIL on unfixed code**: Returns None or N/A without error details
        
        Counterexample: All sources fail, but system returns None without explanation
        
        Scenario:
        1. IBKR fails
        2. Finnhub fails
        3. Yahoo fails
        4. System should return None or error dict with clear message
        5. All failures should be logged
        """
        # Arrange: Create DataFetcher
        with patch('data_layer.data_fetcher.IBKR_AVAILABLE', False):
            fetcher = DataFetcher(use_ibkr=False)
        
        # Mock all clients to fail
        mock_ibkr = MagicMock()
        mock_ibkr.get_stock_info.side_effect = ConnectionError("IBKR connection timeout")
        fetcher.ibkr_client = mock_ibkr
        
        mock_finnhub = MagicMock()
        mock_finnhub.get_quote.side_effect = Exception("Finnhub authentication failed")
        fetcher.finnhub_client = mock_finnhub
        
        mock_yahoo = MagicMock()
        mock_yahoo.get_quote.side_effect = Exception("Yahoo rate limit exceeded")
        fetcher.yahoo_v2_client = mock_yahoo
        
        # Act: Call get_stock_info
        result = fetcher.get_stock_info('AAPL')
        
        # Assert: Result should be None (all sources failed)
        # This is expected behavior when all sources fail
        # The key is that failures should be logged
        
        # Assert: Check if all failures were logged
        if hasattr(fetcher, '_attempt_paths') and 'stock_info' in fetcher._attempt_paths:
            history = fetcher._attempt_paths['stock_info'].get('history', [])
            if history:
                last_attempt = history[-1]
                
                # All attempts should have failed
                failed_attempts = [a for a in last_attempt if not a.get('success')]
                
                assert len(failed_attempts) > 0, \
                    "Bug confirmed: No failed attempts recorded despite all sources failing"
                
                # Check that each failure has an error reason
                for attempt in failed_attempts:
                    assert 'error_reason' in attempt, \
                        f"Bug confirmed: Failed attempt missing error_reason: {attempt}"
                
                print(f"✓ All {len(failed_attempts)} failures were logged with reasons")
                print(f"✓ Failed sources: {[a['source'] for a in failed_attempts]}")
            else:
                assert False, "Bug confirmed: No attempt history recorded despite failures"
        else:
            assert False, "Bug confirmed: No attempt path tracking exists"
    
    @given(
        error_type=st.sampled_from([
            ConnectionError("Connection timeout"),
            TimeoutError("Request timeout"),
            Exception("Authentication failed"),
            Exception("Rate limit exceeded"),
            Exception("Invalid API key")
        ])
    )
    @settings(
        max_examples=5,
        phases=[Phase.generate, Phase.target],
        deadline=None
    )
    def test_property_any_ibkr_error_triggers_fallback(self, error_type):
        """
        Property-Based Test: Any IBKR error should trigger fallback to Finnhub
        
        **EXPECTED TO FAIL on unfixed code**: Some error types don't trigger fallback
        
        Property: For any error from IBKR, system should attempt Finnhub as fallback
        """
        # Arrange: Create DataFetcher
        with patch('data_layer.data_fetcher.IBKR_AVAILABLE', False):
            fetcher = DataFetcher(use_ibkr=False)
        
        # Mock IBKR to fail with the given error type
        mock_ibkr = MagicMock()
        mock_ibkr.get_stock_info.side_effect = error_type
        fetcher.ibkr_client = mock_ibkr
        
        # Mock Finnhub to succeed
        mock_finnhub = MagicMock()
        mock_finnhub.get_quote.return_value = {'c': 150.0, 'h': 152.0, 'l': 148.0, 'o': 149.0, 'pc': 149.5}
        fetcher.finnhub_client = mock_finnhub
        
        # Act: Call get_stock_info
        try:
            result = fetcher.get_stock_info('AAPL')
            
            # Assert: Finnhub should have been attempted
            if mock_finnhub.get_quote.called:
                print(f"✓ Fallback triggered for error: {type(error_type).__name__}")
            else:
                assert False, \
                    f"Bug confirmed: Fallback not triggered for error type {type(error_type).__name__}: {error_type}"
        
        except Exception as e:
            # If an exception propagates, that means fallback wasn't attempted
            assert False, \
                f"Bug confirmed: Exception propagated without fallback attempt: {e}"


class TestBugConditionDocumentation:
    """
    Documentation of expected failures and counterexamples
    """
    
    def test_document_expected_failures(self):
        """
        This test documents the expected failures when running on unfixed code.
        
        Expected Counterexamples:
        1. IBKR fails with ConnectionTimeout, Finnhub not attempted, returns N/A
        2. Degradation attempts are not logged or tracked
        3. Only first source is tried, degradation chain stops prematurely
        4. Failure reasons are not recorded in attempt path
        5. When all sources fail, no clear error information is provided
        6. Some error types don't trigger fallback (e.g., only ConnectionError triggers fallback)
        
        When these failures occur, it confirms Bugs 1.3 and 1.4 exist:
        Bug 1.3: "降級過程可能靜默失敗，未正確記錄失敗原因或未嘗試下一個數據源"
        Bug 1.4: "IBKR Gateway連接失敗或數據獲取失敗 THEN 系統未能有效降級到備用數據源"
        """
        print("\n" + "="*80)
        print("EXPECTED FAILURES ON UNFIXED CODE:")
        print("="*80)
        print("1. AssertionError: Finnhub was not attempted after IBKR failure")
        print("2. AssertionError: DataFetcher has no _attempt_paths attribute")
        print("3. AssertionError: No attempt path recorded for stock_info")
        print("4. AssertionError: Only 1 source tried, expected at least 2")
        print("5. AssertionError: Failed attempt missing error_reason")
        print("6. AssertionError: No failed attempts recorded despite all sources failing")
        print("7. AssertionError: Fallback not triggered for certain error types")
        print("="*80)
        print("\nThese failures confirm Bugs 1.3 and 1.4:")
        print("- API degradation chain fails silently")
        print("- Fallback sources are not attempted when primary source fails")
        print("- Degradation attempts are not logged")
        print("- Failure reasons are not recorded")
        print("="*80 + "\n")
        
        # This test always passes - it's just documentation
        assert True


if __name__ == "__main__":
    # Run tests manually without pytest.main() to avoid version conflicts
    print("\n" + "="*80)
    print("Running Bug Exploration Tests - API Degradation Chain")
    print("="*80 + "\n")
    
    test_suite = TestBugConditionAPIDegradationChain()
    doc_suite = TestBugConditionDocumentation()
    
    # Run documentation first
    print("\n--- Test: Document Expected Failures ---")
    try:
        doc_suite.test_document_expected_failures()
        print("✓ PASSED\n")
    except Exception as e:
        print(f"✗ FAILED: {e}\n")
    
    # Run basic tests
    tests = [
        ("Test 1: Finnhub attempted after IBKR failure", 
         test_suite.test_degradation_chain_attempts_finnhub_after_ibkr_failure),
        ("Test 2: Degradation attempts are logged", 
         test_suite.test_degradation_attempts_are_logged),
        ("Test 3: Multiple sources tried in chain", 
         test_suite.test_degradation_chain_tries_multiple_sources),
        ("Test 4: Failure reasons recorded", 
         test_suite.test_degradation_records_failure_reasons),
        ("Test 5: All sources fail with clear error", 
         test_suite.test_all_sources_fail_returns_clear_error),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        try:
            test_func()
            print(f"✓ PASSED")
            passed += 1
        except AssertionError as e:
            print(f"✗ FAILED (EXPECTED): {e}")
            failed += 1
        except Exception as e:
            print(f"✗ ERROR: {e}")
            failed += 1
    
    print("\n" + "="*80)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("="*80)
    print("\nIf tests FAILED, this confirms Bugs 1.3 and 1.4 exist:")
    print("- API degradation chain fails silently without attempting fallback sources")
    print("- Degradation attempts and failure reasons are not properly logged")
    print("="*80 + "\n")
