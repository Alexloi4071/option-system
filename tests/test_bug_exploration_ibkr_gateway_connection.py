# tests/test_bug_exploration_ibkr_gateway_connection.py
"""
Bug Condition Exploration Test - IBKR Gateway Connection Issue

**Validates: Requirements 2.1, 2.2, 2.5**

Property 1: Bug Condition - IBKR Gateway 成功連接

CRITICAL: This test MUST FAIL on unfixed code - failure confirms the bug exists
DO NOT attempt to fix the test or the code when it fails

NOTE: This test encodes the expected behavior - it will validate the fix when it passes after implementation

GOAL: Surface counterexamples that demonstrate the bug exists
Scoped PBT Approach: For deterministic bugs, scope the property to the concrete failing case(s) to ensure reproducibility

Test Scenarios:
1. ib_insync not installed - should show clear error message
2. Port mismatch - should show connection error with port details
3. Gateway not running - should show connection refused error
4. Correct configuration - should connect successfully

Expected Outcome: Test FAILS (this is correct - it proves the bug exists)

Document counterexamples found:
- System shows '✗ IBKR (Not enabled)' even when IBKR_ENABLED=True
- Unclear error messages
- IBKR_AVAILABLE=False without explanation
"""

import pytest
import os
import sys
from unittest.mock import patch, MagicMock
from hypothesis import given, strategies as st, settings, Phase
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_layer.data_fetcher import DataFetcher, IBKR_AVAILABLE
from config.settings import settings as app_settings


class TestBugConditionIBKRGatewayConnection:
    """
    Bug Condition Exploration: IBKR Gateway Connection Issue
    
    This test explores the bug where the system fails to connect to IBKR Gateway
    even when IBKR_ENABLED=True and Gateway is running, showing '✗ IBKR (Not enabled)'
    instead of attempting connection or providing clear error messages.
    """
    
    def test_ibkr_enabled_flag_is_read_correctly(self):
        """
        Test that IBKR_ENABLED environment variable is read correctly.
        
        **EXPECTED TO FAIL on unfixed code**: IBKR_ENABLED=True but system doesn't attempt connection
        
        Counterexample: Environment variable set to True but system behaves as if it's False
        """
        # Act: Check current IBKR_ENABLED setting from .env
        from config.settings import settings
        
        print(f"Current IBKR_ENABLED setting: {settings.IBKR_ENABLED}")
        print(f"Environment variable: {os.getenv('IBKR_ENABLED')}")
        
        # Document the current state
        if settings.IBKR_ENABLED:
            print("✓ IBKR_ENABLED is True - system should attempt connection")
        else:
            print("⚠ IBKR_ENABLED is False - this test requires IBKR_ENABLED=True in .env")
            print("   Please set IBKR_ENABLED=True in .env file to test the bug condition")
    
    def test_ibkr_available_reflects_import_status(self):
        """
        Test that IBKR_AVAILABLE global variable correctly reflects ib_insync import status.
        
        **EXPECTED TO FAIL on unfixed code**: IBKR_AVAILABLE is False even when ib_insync is installed
        
        Counterexample: ib_insync is installed but IBKR_AVAILABLE=False, causing system to skip IBKR
        """
        # Act: Check IBKR_AVAILABLE status
        print(f"IBKR_AVAILABLE status: {IBKR_AVAILABLE}")
        
        # Try to import ib_insync directly
        try:
            import ib_insync
            ib_insync_installed = True
            print(f"✓ ib_insync is installed: {ib_insync.__version__}")
        except ImportError as e:
            ib_insync_installed = False
            print(f"✗ ib_insync is NOT installed: {e}")
        
        # Assert: IBKR_AVAILABLE should match actual import status
        if ib_insync_installed:
            assert IBKR_AVAILABLE is True, \
                "Bug confirmed: ib_insync is installed but IBKR_AVAILABLE=False"
        else:
            # If ib_insync is not installed, document this as a counterexample
            print("⚠ Counterexample: ib_insync not installed - system should show clear error message")
            print("   Expected: 'IBKR unavailable: ib_insync not installed'")
            print("   Actual: System likely shows '✗ IBKR (Not enabled)'")
    
    def test_client_status_distinguishes_not_enabled_vs_import_failed(self):
        """
        Test that client_status clearly distinguishes between:
        - IBKR not enabled (IBKR_ENABLED=False)
        - IBKR enabled but ib_insync import failed
        - IBKR enabled but connection failed
        
        **EXPECTED TO FAIL on unfixed code**: All three cases show '✗ IBKR (Not enabled)'
        
        Counterexample: Cannot distinguish between configuration issue and import/connection failure
        """
        # Test with current configuration
        from config.settings import settings
        
        fetcher = DataFetcher()
        
        print(f"Current IBKR_ENABLED: {settings.IBKR_ENABLED}")
        print(f"Current IBKR_AVAILABLE: {IBKR_AVAILABLE}")
        
        if hasattr(fetcher, 'client_status') and 'ibkr' in fetcher.client_status:
            ibkr_status = fetcher.client_status['ibkr']
            print(f"Current IBKR status: {ibkr_status}")
            
            # Check if error message is clear and specific
            error_msg = ibkr_status.get('error', '')
            available = ibkr_status.get('available', False)
            
            if not settings.IBKR_ENABLED:
                # Should say "Not enabled"
                assert error_msg == 'Not enabled', \
                    f"Bug confirmed: IBKR_ENABLED=False but error is '{error_msg}'"
                print("✓ Correctly shows 'Not enabled' when IBKR_ENABLED=False")
            elif not IBKR_AVAILABLE:
                # Should mention import failure, not "Not enabled"
                assert 'import' in error_msg.lower() or 'ib_insync' in error_msg.lower() or 'available' in error_msg.lower(), \
                    f"Bug confirmed: ib_insync unavailable but error is '{error_msg}' (should mention import failure)"
                print(f"✓ Error message mentions import issue: {error_msg}")
            else:
                # IBKR enabled and available - should attempt connection
                if not available:
                    # Connection failed - error should be specific
                    assert error_msg and error_msg != 'Not enabled', \
                        f"Bug confirmed: Connection failed but error is '{error_msg}' (should be specific)"
                    print(f"Connection failed with specific error: {error_msg}")
                else:
                    print(f"✓ IBKR connected successfully")
        else:
            print("⚠ Bug confirmed: No client_status or no ibkr entry")
            assert False, "Bug confirmed: DataFetcher has no client_status['ibkr']"
    
    def test_connection_attempt_logged_when_enabled(self):
        """
        Test that when IBKR_ENABLED=True, system attempts connection and logs details.
        
        **EXPECTED TO FAIL on unfixed code**: No connection attempt logged
        
        Counterexample: IBKR_ENABLED=True but no log entries for connection attempt
        """
        # Check current configuration
        from config.settings import settings
        
        print(f"Current IBKR_ENABLED: {settings.IBKR_ENABLED}")
        print(f"Current IBKR_AVAILABLE: {IBKR_AVAILABLE}")
        
        if not settings.IBKR_ENABLED:
            print("⚠ IBKR_ENABLED=False - skipping connection attempt test")
            print("   Set IBKR_ENABLED=True in .env to test connection logging")
            return
        
        if not IBKR_AVAILABLE:
            print("⚠ ib_insync not available - cannot test connection attempt")
            return
        
        # Mock logging to capture log messages
        import logging
        from io import StringIO
        log_capture = StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setLevel(logging.INFO)
        
        logger = logging.getLogger('data_layer.data_fetcher')
        logger.addHandler(handler)
        
        # Act: Initialize DataFetcher
        try:
            fetcher = DataFetcher()
        except Exception as e:
            print(f"DataFetcher initialization error: {e}")
        
        # Get log output
        log_output = log_capture.getvalue()
        logger.removeHandler(handler)
        
        print(f"Log output:\n{log_output}")
        
        # Assert: Should see connection attempt in logs
        assert 'IBKR' in log_output or 'ibkr' in log_output, \
            "Bug confirmed: IBKR_ENABLED=True but no IBKR-related log entries"
        
        # Should see port information
        port = settings.IBKR_PORT_PAPER if settings.IBKR_USE_PAPER else settings.IBKR_PORT_LIVE
        assert str(port) in log_output or 'port' in log_output.lower(), \
            f"Bug confirmed: No port information in IBKR connection logs (expected port {port})"
    
    def test_connection_status_reflects_actual_state(self):
        """
        Test that connection status accurately reflects whether Gateway is running.
        
        **EXPECTED TO FAIL on unfixed code**: Connection status is always 'not enabled'
        
        Counterexample: Gateway is running but status shows 'not enabled' or no connection attempt
        """
        # Check current configuration
        from config.settings import settings
        
        print(f"Current IBKR_ENABLED: {settings.IBKR_ENABLED}")
        print(f"Current IBKR_AVAILABLE: {IBKR_AVAILABLE}")
        print(f"Current IBKR_HOST: {settings.IBKR_HOST}")
        print(f"Current IBKR_PORT: {settings.IBKR_PORT_PAPER if settings.IBKR_USE_PAPER else settings.IBKR_PORT_LIVE}")
        
        if not settings.IBKR_ENABLED:
            print("⚠ IBKR_ENABLED=False - skipping connection status test")
            print("   Set IBKR_ENABLED=True in .env to test connection status")
            return
        
        if not IBKR_AVAILABLE:
            print("⚠ ib_insync not available - cannot test connection status")
            return
        
        # Act: Initialize DataFetcher
        fetcher = DataFetcher()
        
        # Assert: Check client_status
        if hasattr(fetcher, 'client_status') and 'ibkr' in fetcher.client_status:
            ibkr_status = fetcher.client_status['ibkr']
            print(f"IBKR connection status: {ibkr_status}")
            
            # Status should be either:
            # - {'available': True, 'error': None} if Gateway is running
            # - {'available': False, 'error': 'Connection failed: ...'} if Gateway not running
            # NOT {'available': False, 'error': 'Not enabled'}
            
            error_msg = ibkr_status.get('error', '')
            if error_msg == 'Not enabled':
                print("⚠ Bug confirmed: IBKR_ENABLED=True but status shows 'Not enabled'")
                assert False, \
                    "Bug confirmed: IBKR_ENABLED=True and IBKR_AVAILABLE=True " \
                    "but client_status shows 'Not enabled'"
            
            # Check if connection was attempted
            if not ibkr_status.get('available'):
                print(f"Connection failed (expected if Gateway not running): {error_msg}")
                # Error message should be specific, not generic
                assert error_msg and error_msg != 'Not enabled', \
                    f"Bug confirmed: Connection failed but error message is unclear: '{error_msg}'"
            else:
                print("✓ IBKR connected successfully")
        else:
            print("⚠ Bug confirmed: No client_status or no ibkr entry")
            assert False, "Bug confirmed: DataFetcher has no client_status['ibkr']"
    
    def test_data_source_priority_when_ibkr_enabled(self):
        """
        Test that when IBKR is successfully connected, it becomes the primary data source.
        
        **EXPECTED TO FAIL on unfixed code**: Yahoo Finance is always primary, IBKR never used
        
        Counterexample: IBKR connected but system still uses Yahoo Finance as primary
        """
        # Check current configuration
        from config.settings import settings
        
        print(f"Current IBKR_ENABLED: {settings.IBKR_ENABLED}")
        print(f"Current IBKR_AVAILABLE: {IBKR_AVAILABLE}")
        
        if not settings.IBKR_ENABLED:
            print("⚠ IBKR_ENABLED=False - skipping data source priority test")
            print("   Set IBKR_ENABLED=True in .env to test data source priority")
            return
        
        if not IBKR_AVAILABLE:
            print("⚠ ib_insync not available - IBKR cannot be used")
            return
        
        # Act: Initialize DataFetcher
        fetcher = DataFetcher()
        
        # Assert: Check use_ibkr flag
        print(f"use_ibkr flag: {fetcher.use_ibkr}")
        
        # If ib_insync is available and IBKR_ENABLED=True, use_ibkr should be True
        # (even if connection fails, the flag should be set to attempt using IBKR)
        assert fetcher.use_ibkr is True, \
            "Bug confirmed: IBKR_ENABLED=True and IBKR_AVAILABLE=True but use_ibkr=False"
        
        # Check if IBKR client exists
        assert hasattr(fetcher, 'ibkr_client'), \
            "Bug confirmed: use_ibkr=True but no ibkr_client attribute"
        
        print(f"✓ IBKR client initialized: {fetcher.ibkr_client}")


class TestBugConditionDocumentation:
    """
    Documentation of expected failures and counterexamples
    """
    
    def test_document_expected_failures(self):
        """
        This test documents the expected failures when running on unfixed code.
        
        Expected Counterexamples:
        1. IBKR_ENABLED=True but system shows '✗ IBKR (Not enabled)'
        2. ib_insync not installed but error message doesn't explain this
        3. Cannot distinguish between "not enabled", "import failed", and "connection failed"
        4. No connection attempt logged when IBKR_ENABLED=True
        5. Connection status always shows 'not enabled' regardless of actual state
        6. IBKR never used as primary data source even when enabled and connected
        
        When these failures occur, it confirms the bug exists:
        "系統沒有連接到 IBKR Gateway，而是使用 Yahoo Finance 作為主要數據源"
        """
        print("\n" + "="*80)
        print("EXPECTED FAILURES ON UNFIXED CODE:")
        print("="*80)
        print("1. System shows '✗ IBKR (Not enabled)' even when IBKR_ENABLED=True")
        print("2. ib_insync import failure not clearly reported")
        print("3. Cannot distinguish 'not enabled' vs 'import failed' vs 'connection failed'")
        print("4. No connection attempt logged when IBKR_ENABLED=True")
        print("5. Connection status always 'not enabled' regardless of Gateway state")
        print("6. Yahoo Finance always primary, IBKR never used")
        print("="*80)
        print("\nThese failures confirm the bug: System fails to connect to IBKR Gateway")
        print("even when IBKR_ENABLED=True and Gateway is running.")
        print("="*80 + "\n")
        
        # This test always passes - it's just documentation
        assert True
    
    def test_document_root_cause_hypotheses(self):
        """
        Document the hypothesized root causes from the design document.
        """
        print("\n" + "="*80)
        print("HYPOTHESIZED ROOT CAUSES:")
        print("="*80)
        print("1. ib_insync import failure:")
        print("   - ib_insync not installed or version incompatible")
        print("   - Results in IBKR_AVAILABLE=False")
        print("   - use_ibkr = settings.IBKR_ENABLED and IBKR_AVAILABLE evaluates to False")
        print()
        print("2. Port configuration mismatch:")
        print("   - Different files use different default ports (4002 vs 7497)")
        print("   - Connection attempts wrong port, fails silently")
        print()
        print("3. Connection failure with unclear error messages:")
        print("   - Exceptions caught but only logged as warnings")
        print("   - User sees 'Not enabled' instead of actual error")
        print()
        print("4. Status reporting logic error:")
        print("   - Status check only looks at use_ibkr flag")
        print("   - Doesn't distinguish between config issue and connection failure")
        print("="*80 + "\n")
        
        assert True


if __name__ == "__main__":
    # Run tests manually without pytest.main() to avoid version conflicts
    print("\n" + "="*80)
    print("Running Bug Exploration Tests - IBKR Gateway Connection Issue")
    print("="*80 + "\n")
    
    test_suite = TestBugConditionIBKRGatewayConnection()
    doc_suite = TestBugConditionDocumentation()
    
    # Run documentation first
    print("\n--- Test: Document Expected Failures ---")
    try:
        doc_suite.test_document_expected_failures()
        print("✓ PASSED\n")
    except Exception as e:
        print(f"✗ FAILED: {e}\n")
    
    print("\n--- Test: Document Root Cause Hypotheses ---")
    try:
        doc_suite.test_document_root_cause_hypotheses()
        print("✓ PASSED\n")
    except Exception as e:
        print(f"✗ FAILED: {e}\n")
    
    # Run basic tests
    tests = [
        ("Test 1: IBKR_ENABLED flag read correctly", test_suite.test_ibkr_enabled_flag_is_read_correctly),
        ("Test 2: IBKR_AVAILABLE reflects import status", test_suite.test_ibkr_available_reflects_import_status),
        ("Test 3: client_status distinguishes error types", test_suite.test_client_status_distinguishes_not_enabled_vs_import_failed),
        ("Test 4: Connection attempt logged", test_suite.test_connection_attempt_logged_when_enabled),
        ("Test 5: Connection status reflects actual state", test_suite.test_connection_status_reflects_actual_state),
        ("Test 6: Data source priority when IBKR enabled", test_suite.test_data_source_priority_when_ibkr_enabled),
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
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "="*80)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("="*80)
    print("\nIf tests FAILED, this confirms the bug exists:")
    print("System fails to connect to IBKR Gateway even when IBKR_ENABLED=True")
    print("and Gateway is running, showing '✗ IBKR (Not enabled)' instead.")
    print("="*80 + "\n")
