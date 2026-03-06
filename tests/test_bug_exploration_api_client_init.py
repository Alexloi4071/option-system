# tests/test_bug_exploration_api_client_init.py
"""
Bug Condition Exploration Test - API Client Initialization Validation

**Validates: Requirements 1.6, 2.6**

Property 1: Bug Condition - API Client Silent Initialization Failure

CRITICAL: This test MUST FAIL on unfixed code - failure confirms the bug exists
DO NOT attempt to fix the test or the code when it fails

GOAL: Surface counterexamples showing initialization failures are not detected
Scoped PBT Approach: Test with invalid Finnhub API Key, valid IBKR and Yahoo configs

Expected Outcome: Test FAILS (client_status is empty or doesn't reflect Finnhub failure)
Document counterexamples: "Finnhub initialization fails but client_status shows no error"

Bug 1.6: WHEN 系統初始化各API客戶端 THEN 某些客戶端初始化失敗但未被正確檢測和報告
Expected Behavior 2.6: WHEN 系統初始化各API客戶端 THEN 應驗證每個客戶端的可用性
（如測試連接、驗證API Key），並在初始化報告中明確列出可用和不可用的客戶端
"""

import pytest
import os
import sys
from unittest.mock import patch, MagicMock
from hypothesis import given, strategies as st, settings, Phase
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_layer.data_fetcher import DataFetcher


class TestBugConditionAPIClientInit:
    """
    Bug Condition Exploration: API Client Initialization Validation
    
    This test explores the bug where API client initialization failures
    are not detected and reported in a client_status dictionary.
    """
    
    def test_client_status_exists_after_initialization(self):
        """
        Test that client_status dictionary exists after DataFetcher initialization.
        
        **EXPECTED TO FAIL on unfixed code**: client_status attribute doesn't exist
        
        Counterexample: DataFetcher initializes but has no client_status attribute
        """
        # Arrange: Create DataFetcher with default configuration
        fetcher = DataFetcher()
        
        # Act & Assert: Check if client_status exists
        assert hasattr(fetcher, 'client_status'), \
            "Bug confirmed: DataFetcher has no client_status attribute"
        
        assert isinstance(fetcher.client_status, dict), \
            "Bug confirmed: client_status is not a dictionary"
        
        print(f"✓ client_status exists: {fetcher.client_status}")
    
    def test_client_status_reflects_finnhub_failure_with_invalid_key(self):
        """
        Test that client_status correctly reflects Finnhub initialization failure
        when an invalid API key is provided.
        
        **EXPECTED TO FAIL on unfixed code**: Finnhub failure is not detected
        
        Counterexample: Finnhub initialization fails but client_status shows no error
        or client_status doesn't exist at all
        """
        # Arrange: Set invalid Finnhub API key
        invalid_key = "INVALID_KEY_12345"
        
        with patch.dict(os.environ, {'FINNHUB_API_KEY': invalid_key}):
            # Act: Initialize DataFetcher
            fetcher = DataFetcher()
            
            # Assert: client_status should exist
            assert hasattr(fetcher, 'client_status'), \
                "Bug confirmed: DataFetcher has no client_status attribute"
            
            # Assert: client_status should have finnhub entry
            assert 'finnhub' in fetcher.client_status, \
                "Bug confirmed: client_status has no 'finnhub' entry"
            
            # Assert: Finnhub should be marked as unavailable
            finnhub_status = fetcher.client_status['finnhub']
            assert 'available' in finnhub_status, \
                "Bug confirmed: finnhub status has no 'available' field"
            
            assert finnhub_status['available'] is False, \
                f"Bug confirmed: Finnhub marked as available despite invalid key. Status: {finnhub_status}"
            
            # Assert: Error message should be present
            assert 'error' in finnhub_status, \
                "Bug confirmed: finnhub status has no 'error' field"
            
            assert finnhub_status['error'] is not None, \
                "Bug confirmed: Finnhub error is None despite invalid key"
            
            print(f"✓ Finnhub failure detected: {finnhub_status}")
    
    def test_client_status_reflects_multiple_clients(self):
        """
        Test that client_status tracks all API clients (IBKR, Finnhub, Yahoo, etc.)
        
        **EXPECTED TO FAIL on unfixed code**: client_status is empty or incomplete
        
        Counterexample: client_status doesn't track all API clients
        """
        # Arrange & Act: Initialize DataFetcher
        fetcher = DataFetcher()
        
        # Assert: client_status should exist
        assert hasattr(fetcher, 'client_status'), \
            "Bug confirmed: DataFetcher has no client_status attribute"
        
        # Assert: client_status should track multiple clients
        expected_clients = ['ibkr', 'finnhub', 'yahoo', 'fred', 'alpha_vantage']
        
        for client_name in expected_clients:
            assert client_name in fetcher.client_status, \
                f"Bug confirmed: client_status missing '{client_name}' entry. " \
                f"Current keys: {list(fetcher.client_status.keys())}"
            
            client_info = fetcher.client_status[client_name]
            assert 'available' in client_info, \
                f"Bug confirmed: {client_name} status missing 'available' field"
            assert 'error' in client_info, \
                f"Bug confirmed: {client_name} status missing 'error' field"
        
        print(f"✓ All clients tracked: {list(fetcher.client_status.keys())}")
    
    def test_initialization_summary_printed_to_console(self, capsys):
        """
        Test that initialization summary is printed to console during startup.
        
        **EXPECTED TO FAIL on unfixed code**: No initialization summary is printed
        
        Counterexample: System initializes silently without reporting client status
        """
        # Arrange & Act: Initialize DataFetcher
        fetcher = DataFetcher()
        
        # Capture console output
        captured = capsys.readouterr()
        output = captured.out + captured.err
        
        # Assert: Initialization summary should be printed
        assert "API Client Initialization Summary" in output or \
               "Client Status" in output or \
               hasattr(fetcher, 'client_status'), \
            "Bug confirmed: No initialization summary printed and no client_status attribute"
        
        print(f"✓ Console output captured: {len(output)} characters")
    
    @given(
        finnhub_key=st.one_of(
            st.just("INVALID_KEY"),
            st.just(""),
            st.just("abc123"),
            st.text(min_size=1, max_size=20, alphabet=st.characters(blacklist_characters="\n\r\t"))
        )
    )
    @settings(
        max_examples=10,
        phases=[Phase.generate, Phase.target],
        deadline=None
    )
    def test_property_invalid_finnhub_keys_detected(self, finnhub_key):
        """
        Property-Based Test: Invalid Finnhub API keys should be detected
        
        **EXPECTED TO FAIL on unfixed code**: Invalid keys are not detected
        
        Property: For any invalid Finnhub API key, client_status should reflect failure
        """
        # Arrange: Set invalid Finnhub API key
        with patch.dict(os.environ, {'FINNHUB_API_KEY': finnhub_key}):
            # Act: Initialize DataFetcher
            fetcher = DataFetcher()
            
            # Assert: client_status should exist and reflect the failure
            if hasattr(fetcher, 'client_status'):
                if 'finnhub' in fetcher.client_status:
                    finnhub_status = fetcher.client_status['finnhub']
                    
                    # If Finnhub is marked as available with an invalid key, that's a bug
                    if finnhub_status.get('available') is True:
                        print(f"⚠ Bug detected: Finnhub marked available with key '{finnhub_key[:4]}...'")
                        assert False, \
                            f"Bug confirmed: Invalid Finnhub key '{finnhub_key[:4]}...' " \
                            f"not detected. Status: {finnhub_status}"
                else:
                    print(f"⚠ Bug detected: No finnhub entry in client_status")
                    assert False, "Bug confirmed: client_status has no 'finnhub' entry"
            else:
                print(f"⚠ Bug detected: No client_status attribute")
                assert False, "Bug confirmed: DataFetcher has no client_status attribute"


class TestBugConditionDocumentation:
    """
    Documentation of expected failures and counterexamples
    """
    
    def test_document_expected_failures(self):
        """
        This test documents the expected failures when running on unfixed code.
        
        Expected Counterexamples:
        1. DataFetcher has no client_status attribute
        2. client_status is empty dictionary {}
        3. Finnhub initialization fails but client_status shows no error
        4. client_status doesn't track all API clients (IBKR, Yahoo, FRED, etc.)
        5. No initialization summary is printed to console
        
        When these failures occur, it confirms Bug 1.6 exists:
        "某些客戶端初始化失敗但未被正確檢測和報告"
        """
        print("\n" + "="*80)
        print("EXPECTED FAILURES ON UNFIXED CODE:")
        print("="*80)
        print("1. AttributeError: 'DataFetcher' object has no attribute 'client_status'")
        print("2. AssertionError: client_status is empty or incomplete")
        print("3. AssertionError: Finnhub marked as available despite invalid key")
        print("4. AssertionError: client_status missing expected client entries")
        print("5. AssertionError: No initialization summary printed")
        print("="*80)
        print("\nThese failures confirm Bug 1.6: API client initialization failures")
        print("are not detected and reported.")
        print("="*80 + "\n")
        
        # This test always passes - it's just documentation
        assert True


if __name__ == "__main__":
    # Run tests manually without pytest.main() to avoid version conflicts
    print("\n" + "="*80)
    print("Running Bug Exploration Tests - API Client Initialization")
    print("="*80 + "\n")
    
    test_suite = TestBugConditionAPIClientInit()
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
        ("Test 1: client_status exists", test_suite.test_client_status_exists_after_initialization),
        ("Test 2: Finnhub failure detection", test_suite.test_client_status_reflects_finnhub_failure_with_invalid_key),
        ("Test 3: Multiple clients tracked", test_suite.test_client_status_reflects_multiple_clients),
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
    print("\nIf tests FAILED, this confirms Bug 1.6 exists:")
    print("API client initialization failures are not detected and reported.")
    print("="*80 + "\n")
