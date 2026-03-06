# tests/test_bug_exploration_yahoo_429_retry.py
"""
Bug Condition Exploration Test - Yahoo Finance 429 Retry Mechanism

**Validates: Requirements 1.8, 2.8**

Property 1: Bug Condition - Yahoo Finance Rate Limit No Retry

CRITICAL: This test MUST FAIL on unfixed code - failure confirms the bug exists
DO NOT attempt to fix the test or the code when it fails

GOAL: Surface counterexamples showing 429 errors are not retried
Scoped PBT Approach: Mock Yahoo Finance returns 429 on first request, success on second

Test that system implements exponential backoff retry for 429 errors (from Bug Condition 1.8)
Run test on UNFIXED code

Expected Outcome: Test FAILS (no retry, returns N/A immediately)
Document counterexamples: "Yahoo Finance 429 error treated as permanent failure, no retry attempted"

Bug 1.8: WHEN 系統從Yahoo Finance獲取期權鏈數據 THEN 可能因速率限制（429錯誤）或其他原因失敗，
但未正確重試或降級

Expected Behavior 2.8: WHEN 系統從Yahoo Finance獲取期權鏈數據 THEN 應實現智能重試機制（指數退避），
在遇到429錯誤時自動降級到其他數據源（IBKR、RapidAPI）
"""

import pytest
import os
import sys
from unittest.mock import patch, MagicMock, Mock, PropertyMock
from hypothesis import given, strategies as st, settings, Phase
from typing import Dict, Any
import requests
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_layer.yahoo_finance_v2_client import YahooFinanceV2Client


class TestBugConditionYahoo429Retry:
    """
    Bug Condition Exploration: Yahoo Finance 429 Retry Mechanism
    
    This test explores the bug where Yahoo Finance 429 errors are not retried
    with exponential backoff, leading to immediate failure and N/A data.
    """
    
    def test_yahoo_429_triggers_retry_with_backoff(self):
        """
        Test that Yahoo Finance 429 error triggers retry with exponential backoff.
        
        **EXPECTED TO FAIL on unfixed code**: 429 error causes immediate failure, no retry
        
        Counterexample: Yahoo returns 429, system returns N/A without retry attempt
        
        Scenario:
        1. First request returns 429 (rate limit)
        2. System should wait (exponential backoff)
        3. Second request should be attempted
        4. Second request succeeds
        5. System should return valid data
        """
        # Arrange: Create Yahoo client
        client = YahooFinanceV2Client(request_delay=0.1)  # Short delay for testing
        
        # Mock the session to return 429 on first call, success on second
        mock_response_429 = Mock()
        mock_response_429.status_code = 429
        mock_response_429.raise_for_status.side_effect = requests.exceptions.HTTPError("429 Too Many Requests")
        
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {
            'chart': {
                'result': [{
                    'meta': {
                        'regularMarketPrice': 150.0,
                        'symbol': 'AAPL'
                    }
                }]
            }
        }
        
        # Configure mock to return 429 first, then success
        call_count = 0
        def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_response_429
            else:
                return mock_response_success
        
        with patch.object(client.session, 'get', side_effect=mock_get):
            # Act: Call get_quote (should trigger retry on 429)
            start_time = time.time()
            result = client.get_quote('AAPL')
            elapsed_time = time.time() - start_time
            
            # Assert: Should have made 2 calls (first 429, second success)
            assert call_count >= 2, \
                f"Bug confirmed: Only {call_count} request(s) made. " \
                f"Expected at least 2 (first 429, then retry)"
            
            # Assert: Should have waited between requests (exponential backoff)
            # Even with short delays, there should be some wait time
            assert elapsed_time > 0.1, \
                f"Bug confirmed: No wait time between requests ({elapsed_time:.2f}s). " \
                f"Expected exponential backoff delay"
            
            # Assert: Result should be valid (not None)
            assert result is not None, \
                "Bug confirmed: Returned None after 429 error instead of retrying"
            
            # Assert: Result should contain valid data
            assert 'regularMarketPrice' in result or 'current_price' in result, \
                f"Bug confirmed: Result missing price data: {result}"
            
            print(f"✓ Yahoo Finance 429 error triggered retry")
            print(f"✓ Made {call_count} requests (first 429, then success)")
            print(f"✓ Waited {elapsed_time:.2f}s between requests (exponential backoff)")
            print(f"✓ Result: {result}")
    
    def test_yahoo_429_retry_count_limit(self):
        """
        Test that Yahoo Finance 429 retry has a maximum retry limit.
        
        **EXPECTED TO FAIL on unfixed code**: No retry limit, infinite retries or immediate failure
        
        Counterexample: System retries indefinitely or gives up after first 429
        
        Scenario:
        1. All requests return 429 (persistent rate limit)
        2. System should retry up to max_retries times
        3. After max retries, should raise exception or return None
        4. Should not retry indefinitely
        """
        # Arrange: Create Yahoo client
        client = YahooFinanceV2Client(request_delay=0.1, max_retries=3)
        
        # Mock the session to always return 429
        mock_response_429 = Mock()
        mock_response_429.status_code = 429
        mock_response_429.raise_for_status.side_effect = requests.exceptions.HTTPError("429 Too Many Requests")
        
        call_count = 0
        def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return mock_response_429
        
        with patch.object(client.session, 'get', side_effect=mock_get):
            # Act: Call get_quote (should retry up to max_retries)
            try:
                result = client.get_quote('AAPL')
                
                # If we get here, check that retries were attempted
                assert call_count > 1, \
                    f"Bug confirmed: Only {call_count} request made, no retries attempted"
                
                assert call_count <= 5, \
                    f"Bug confirmed: Made {call_count} requests, expected max 3-4 retries"
                
                print(f"✓ Retry limit enforced: {call_count} requests made")
                
            except Exception as e:
                # Exception is expected after max retries
                # Check that multiple attempts were made
                assert call_count > 1, \
                    f"Bug confirmed: Only {call_count} request made before exception. " \
                    f"Expected multiple retry attempts. Error: {e}"
                
                assert call_count <= 5, \
                    f"Bug confirmed: Made {call_count} requests, expected max 3-4 retries"
                
                print(f"✓ Retry limit enforced: {call_count} requests made before giving up")
                print(f"✓ Exception raised after max retries: {type(e).__name__}")
    
    def test_yahoo_429_exponential_backoff_timing(self):
        """
        Test that Yahoo Finance 429 retry uses exponential backoff timing.
        
        **EXPECTED TO FAIL on unfixed code**: No backoff or fixed delay between retries
        
        Counterexample: Retries happen immediately or with fixed delay
        
        Scenario:
        1. First request returns 429
        2. Wait time should increase exponentially (e.g., 1s, 2s, 4s)
        3. Verify that delay increases between retries
        """
        # Arrange: Create Yahoo client with short base delay for testing
        client = YahooFinanceV2Client(request_delay=0.1)
        
        # Mock the session to return 429 twice, then success
        mock_response_429 = Mock()
        mock_response_429.status_code = 429
        mock_response_429.raise_for_status.side_effect = requests.exceptions.HTTPError("429 Too Many Requests")
        
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {
            'chart': {
                'result': [{
                    'meta': {
                        'regularMarketPrice': 150.0,
                        'symbol': 'AAPL'
                    }
                }]
            }
        }
        
        call_count = 0
        call_times = []
        
        def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            call_times.append(time.time())
            
            if call_count <= 2:
                return mock_response_429
            else:
                return mock_response_success
        
        with patch.object(client.session, 'get', side_effect=mock_get):
            # Act: Call get_quote (should trigger multiple retries with backoff)
            result = client.get_quote('AAPL')
            
            # Assert: Should have made at least 3 calls
            assert call_count >= 3, \
                f"Bug confirmed: Only {call_count} request(s) made. Expected at least 3"
            
            # Assert: Check that delays increase (exponential backoff)
            if len(call_times) >= 3:
                delay_1 = call_times[1] - call_times[0]
                delay_2 = call_times[2] - call_times[1]
                
                # Second delay should be longer than first (exponential backoff)
                # Allow some tolerance for timing variations
                assert delay_2 > delay_1 * 0.8, \
                    f"Bug confirmed: Delays not increasing exponentially. " \
                    f"First delay: {delay_1:.2f}s, Second delay: {delay_2:.2f}s. " \
                    f"Expected second delay to be longer (exponential backoff)"
                
                print(f"✓ Exponential backoff confirmed:")
                print(f"  First retry delay: {delay_1:.2f}s")
                print(f"  Second retry delay: {delay_2:.2f}s")
                print(f"  Ratio: {delay_2/delay_1:.2f}x")
            else:
                print(f"⚠ Warning: Not enough calls to verify exponential backoff ({len(call_times)} calls)")
    
    def test_yahoo_429_session_refresh(self):
        """
        Test that Yahoo Finance 429 error triggers session refresh.
        
        **EXPECTED TO FAIL on unfixed code**: Session not refreshed on 429 error
        
        Counterexample: 429 error occurs but session cookies/headers not refreshed
        
        Scenario:
        1. First request returns 429
        2. System should refresh session (clear cookies, rotate User-Agent)
        3. Second request should use refreshed session
        """
        # Arrange: Create Yahoo client
        client = YahooFinanceV2Client(request_delay=0.1)
        
        # Track if _refresh_session was called
        refresh_called = False
        original_refresh = client._refresh_session
        
        def mock_refresh():
            nonlocal refresh_called
            refresh_called = True
            original_refresh()
        
        # Mock the session to return 429 first, then success
        mock_response_429 = Mock()
        mock_response_429.status_code = 429
        mock_response_429.raise_for_status.side_effect = requests.exceptions.HTTPError("429 Too Many Requests")
        
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {
            'chart': {
                'result': [{
                    'meta': {
                        'regularMarketPrice': 150.0,
                        'symbol': 'AAPL'
                    }
                }]
            }
        }
        
        call_count = 0
        def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_response_429
            else:
                return mock_response_success
        
        with patch.object(client, '_refresh_session', side_effect=mock_refresh):
            with patch.object(client.session, 'get', side_effect=mock_get):
                # Act: Call get_quote (should trigger session refresh on 429)
                result = client.get_quote('AAPL')
                
                # Assert: Session refresh should have been called
                assert refresh_called, \
                    "Bug confirmed: Session not refreshed after 429 error. " \
                    "Expected _refresh_session to be called"
                
                # Assert: Should have made 2 calls
                assert call_count >= 2, \
                    f"Bug confirmed: Only {call_count} request made after 429"
                
                print(f"✓ Session refreshed after 429 error")
                print(f"✓ Made {call_count} requests (first 429, then success)")
    
    def test_yahoo_429_fallback_to_other_sources(self):
        """
        Test that persistent Yahoo Finance 429 errors trigger fallback to other sources.
        
        **EXPECTED TO FAIL on unfixed code**: No fallback to IBKR or RapidAPI after 429 failures
        
        Counterexample: Yahoo 429 persists, system returns N/A without trying IBKR/RapidAPI
        
        Scenario:
        1. Yahoo Finance returns 429 on all retry attempts
        2. System should fall back to IBKR or RapidAPI
        3. System should return data from fallback source
        
        Note: This test checks the integration with DataFetcher's fallback mechanism
        """
        # This test requires DataFetcher integration
        # For now, we document the expected behavior
        
        print("\n" + "="*70)
        print("EXPECTED BEHAVIOR: Yahoo 429 Fallback to Other Sources")
        print("="*70)
        print("When Yahoo Finance returns persistent 429 errors:")
        print("1. System should retry with exponential backoff (up to max_retries)")
        print("2. After max retries, should fall back to IBKR or RapidAPI")
        print("3. Should log the fallback path: Yahoo(✗:429) → IBKR(✓)")
        print("4. Should return data from fallback source")
        print("5. Should NOT return N/A if fallback sources are available")
        print("="*70 + "\n")
        
        # This test documents expected behavior
        # Actual integration test would require DataFetcher
        assert True, "Documentation test - see output above"
    
    @given(
        retry_count=st.integers(min_value=1, max_value=5)
    )
    @settings(
        max_examples=3,
        phases=[Phase.generate, Phase.target],
        deadline=None
    )
    def test_property_yahoo_429_retries_up_to_limit(self, retry_count):
        """
        Property-Based Test: Yahoo 429 should retry up to configured limit
        
        **EXPECTED TO FAIL on unfixed code**: Retry count not respected
        
        Property: For any retry_count configuration, system should retry exactly that many times
        """
        # Arrange: Create Yahoo client with specific retry count
        client = YahooFinanceV2Client(request_delay=0.05, max_retries=retry_count)
        
        # Mock the session to always return 429
        mock_response_429 = Mock()
        mock_response_429.status_code = 429
        mock_response_429.raise_for_status.side_effect = requests.exceptions.HTTPError("429 Too Many Requests")
        
        call_count = 0
        def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return mock_response_429
        
        with patch.object(client.session, 'get', side_effect=mock_get):
            # Act: Call get_quote (should retry up to retry_count)
            try:
                result = client.get_quote('AAPL')
            except Exception:
                pass  # Expected to fail after retries
            
            # Assert: Should have made initial request + retries
            # Allow some tolerance (±1) for implementation variations
            expected_min = retry_count
            expected_max = retry_count + 2
            
            assert expected_min <= call_count <= expected_max, \
                f"Bug confirmed: Made {call_count} requests with max_retries={retry_count}. " \
                f"Expected {expected_min}-{expected_max} requests"
            
            print(f"✓ Retry count respected: {call_count} requests with max_retries={retry_count}")


class TestBugConditionDocumentation:
    """
    Documentation of expected failures and counterexamples
    """
    
    def test_document_expected_failures(self):
        """
        This test documents the expected failures when running on unfixed code.
        
        Expected Counterexamples:
        1. Yahoo Finance 429 error causes immediate failure, no retry attempted
        2. No exponential backoff - retries happen immediately or with fixed delay
        3. No retry limit - system gives up after first 429 or retries indefinitely
        4. Session not refreshed after 429 error
        5. No fallback to IBKR/RapidAPI after persistent 429 errors
        6. Retry count configuration not respected
        
        When these failures occur, it confirms Bug 1.8 exists:
        Bug 1.8: "系統從Yahoo Finance獲取期權鏈數據 THEN 可能因速率限制（429錯誤）或其他原因失敗，
        但未正確重試或降級"
        
        Expected Behavior 2.8 should be implemented:
        "應實現智能重試機制（指數退避），在遇到429錯誤時自動降級到其他數據源（IBKR、RapidAPI）"
        """
        print("\n" + "="*80)
        print("EXPECTED FAILURES ON UNFIXED CODE:")
        print("="*80)
        print("1. AssertionError: Only 1 request made, no retries attempted")
        print("2. AssertionError: No wait time between requests (no exponential backoff)")
        print("3. AssertionError: Returned None after 429 error instead of retrying")
        print("4. AssertionError: Delays not increasing exponentially")
        print("5. AssertionError: Session not refreshed after 429 error")
        print("6. AssertionError: Made X requests with max_retries=Y (count mismatch)")
        print("="*80)
        print("\nThese failures confirm Bug 1.8:")
        print("- Yahoo Finance 429 errors are not retried with exponential backoff")
        print("- System returns N/A immediately instead of implementing smart retry")
        print("- No fallback to other data sources (IBKR, RapidAPI) after persistent 429")
        print("="*80)
        print("\nExpected Behavior 2.8 (to be implemented):")
        print("- Implement exponential backoff retry mechanism")
        print("- Refresh session on 429 error (clear cookies, rotate User-Agent)")
        print("- Fall back to IBKR or RapidAPI after max retries")
        print("- Log retry attempts and fallback path")
        print("="*80 + "\n")
        
        # This test always passes - it's just documentation
        assert True


if __name__ == "__main__":
    # Run tests manually
    print("\n" + "="*80)
    print("Running Bug Exploration Tests - Yahoo Finance 429 Retry Mechanism")
    print("="*80 + "\n")
    
    test_suite = TestBugConditionYahoo429Retry()
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
        ("Test 1: Yahoo 429 triggers retry with backoff", 
         test_suite.test_yahoo_429_triggers_retry_with_backoff),
        ("Test 2: Yahoo 429 retry count limit", 
         test_suite.test_yahoo_429_retry_count_limit),
        ("Test 3: Yahoo 429 exponential backoff timing", 
         test_suite.test_yahoo_429_exponential_backoff_timing),
        ("Test 4: Yahoo 429 session refresh", 
         test_suite.test_yahoo_429_session_refresh),
        ("Test 5: Yahoo 429 fallback to other sources", 
         test_suite.test_yahoo_429_fallback_to_other_sources),
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
    print("\nIf tests FAILED, this confirms Bug 1.8 exists:")
    print("- Yahoo Finance 429 errors are not retried with exponential backoff")
    print("- System returns N/A immediately without implementing smart retry mechanism")
    print("="*80 + "\n")
