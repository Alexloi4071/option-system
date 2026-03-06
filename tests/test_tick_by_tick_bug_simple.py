#!/usr/bin/env python3
"""
Simplified Bug Condition Test - Quick verification of infinite loop bug

This test quickly demonstrates the bug without hanging the test suite.
"""

import sys
import unittest
from unittest.mock import MagicMock
import inspect

sys.path.append('.')

from data_layer.ibkr_client import IBKRClient


class TestTickByTickBugExists(unittest.TestCase):
    """Quick tests to verify the bug exists in current code"""
    
    def test_req_tick_by_tick_data_has_no_timeout_parameter(self):
        """
        Verify that req_tick_by_tick_data() lacks timeout parameter
        
        EXPECTED ON UNFIXED CODE: FAIL - no timeout parameter
        EXPECTED ON FIXED CODE: PASS - timeout parameter exists
        """
        # Get the method signature
        method = IBKRClient.req_tick_by_tick_data
        sig = inspect.signature(method)
        params = list(sig.parameters.keys())
        
        # Check if timeout parameter exists
        self.assertIn(
            'timeout',
            params,
            f"req_tick_by_tick_data() missing 'timeout' parameter. Current params: {params}"
        )
    
    def test_req_tick_by_tick_data_has_no_max_ticks_parameter(self):
        """
        Verify that req_tick_by_tick_data() lacks max_ticks parameter
        
        EXPECTED ON UNFIXED CODE: FAIL - no max_ticks parameter
        EXPECTED ON FIXED CODE: PASS - max_ticks parameter exists
        """
        # Get the method signature
        method = IBKRClient.req_tick_by_tick_data
        sig = inspect.signature(method)
        params = list(sig.parameters.keys())
        
        # Check if max_ticks parameter exists
        self.assertIn(
            'max_ticks',
            params,
            f"req_tick_by_tick_data() missing 'max_ticks' parameter. Current params: {params}"
        )
    
    def test_req_tick_by_tick_data_has_while_true_loop(self):
        """
        Verify that req_tick_by_tick_data() contains 'while True' loop
        
        EXPECTED ON UNFIXED CODE: PASS - while True exists
        EXPECTED ON FIXED CODE: FAIL - while True removed
        """
        import inspect
        
        # Get the source code
        source = inspect.getsource(IBKRClient.req_tick_by_tick_data)
        
        # Check for while True
        has_while_true = 'while True:' in source
        
        # On unfixed code, this should be True (bug exists)
        # On fixed code, this should be False (bug fixed)
        self.assertFalse(
            has_while_true,
            "req_tick_by_tick_data() still contains 'while True:' - infinite loop bug exists!"
        )
    
    def test_req_tick_by_tick_data_has_try_finally(self):
        """
        Verify that req_tick_by_tick_data() has try...finally for cleanup
        
        EXPECTED ON UNFIXED CODE: FAIL - no try...finally
        EXPECTED ON FIXED CODE: PASS - try...finally exists
        """
        import inspect
        
        # Get the source code
        source = inspect.getsource(IBKRClient.req_tick_by_tick_data)
        
        # Check for try...finally pattern
        has_try = 'try:' in source
        has_finally = 'finally:' in source
        
        self.assertTrue(
            has_try and has_finally,
            "req_tick_by_tick_data() missing try...finally block for resource cleanup"
        )


if __name__ == '__main__':
    print("=" * 70)
    print("BUG CONDITION EXPLORATION TEST")
    print("=" * 70)
    print("These tests verify the infinite loop bug exists in unfixed code.")
    print("EXPECTED: Tests should FAIL on unfixed code")
    print("=" * 70)
    print()
    
    # Run tests
    unittest.main(verbosity=2)
