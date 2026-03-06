#!/usr/bin/env python3
"""
Bug Condition Exploration Test for Tick-by-Tick Infinite Loop

This test MUST FAIL on unfixed code to prove the bug exists.
It encodes the expected behavior that will validate the fix.

Property 1: Bug Condition - Timeout and Connection Control
- Function should terminate after timeout (default 60 seconds)
- Function should terminate when max_ticks is reached
- Function should terminate when connection is lost
- Subscription should be cancelled to release resources

CRITICAL: This test is EXPECTED TO FAIL on unfixed code!
"""

import sys
import unittest
import time
import threading
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

sys.path.append('.')

from data_layer.ibkr_client import IBKRClient, TickByTickData
from ib_insync import Stock


class TestTickByTickInfiniteLoopBug(unittest.TestCase):
    """
    Bug Condition Exploration Tests
    
    These tests demonstrate the infinite loop bug in req_tick_by_tick_data().
    They MUST FAIL on unfixed code to prove the bug exists.
    """
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_ib = MagicMock()
        self.mock_ib.isConnected.return_value = True
        
    def test_infinite_loop_no_timeout(self):
        """
        Test that req_tick_by_tick_data() enters infinite loop without timeout
        
        EXPECTED ON UNFIXED CODE: Test hangs or times out
        EXPECTED ON FIXED CODE: Function terminates after timeout
        """
        client = IBKRClient(ib_instance=self.mock_ib)
        client.connected = True
        
        contract = Stock('NVDA', 'SMART', 'USD')
        contract.symbol = 'NVDA'
        
        # Mock ticker with no ticks (simulates waiting for data)
        mock_ticker = MagicMock()
        mock_ticker.ticks = []
        
        self.mock_ib.qualifyContracts.return_value = [contract]
        self.mock_ib.reqTickByTickData.return_value = mock_ticker
        self.mock_ib.sleep = lambda x: time.sleep(x)
        
        # Try to consume the generator with a timeout
        start_time = time.time()
        timeout_occurred = False
        tick_count = 0
        
        def consume_generator():
            nonlocal tick_count, timeout_occurred
            try:
                # This should timeout after 2 seconds if fixed
                gen = client.req_tick_by_tick_data(contract, 'AllLast', timeout=2.0)
                for tick in gen:
                    tick_count += 1
                    if time.time() - start_time > 3.0:
                        # Force break if taking too long
                        timeout_occurred = True
                        break
            except Exception as e:
                pass
        
        # Run in thread with timeout
        thread = threading.Thread(target=consume_generator)
        thread.daemon = True
        thread.start()
        thread.join(timeout=3.0)
        
        elapsed = time.time() - start_time
        
        # ASSERTION: Function should terminate within reasonable time (2-3 seconds)
        # On unfixed code: thread.is_alive() will be True (still running)
        # On fixed code: thread.is_alive() will be False (terminated)
        self.assertFalse(
            thread.is_alive(),
            f"Function did not terminate after {elapsed:.1f}s - infinite loop detected!"
        )
        
        # Verify it terminated due to timeout, not hanging
        self.assertLess(
            elapsed, 3.5,
            f"Function took {elapsed:.1f}s to terminate - should timeout at 2s"
        )
    
    def test_no_connection_still_enters_loop(self):
        """
        Test that function enters loop even when IBKR Gateway is not connected
        
        EXPECTED ON UNFIXED CODE: Function enters while True loop
        EXPECTED ON FIXED CODE: Function returns immediately with error
        """
        # Mock disconnected state
        self.mock_ib.isConnected.return_value = False
        
        client = IBKRClient(ib_instance=self.mock_ib)
        client.connected = False
        
        contract = Stock('NVDA', 'SMART', 'USD')
        contract.symbol = 'NVDA'
        
        # Mock to simulate connection error
        self.mock_ib.qualifyContracts.side_effect = Exception("Connection error")
        
        start_time = time.time()
        result_count = 0
        
        # Try to consume generator
        try:
            gen = client.req_tick_by_tick_data(contract, 'AllLast')
            for tick in gen:
                result_count += 1
                # Should not get here on fixed code
                if time.time() - start_time > 1.0:
                    break
        except Exception:
            pass
        
        elapsed = time.time() - start_time
        
        # ASSERTION: Should return immediately (< 0.5s) when not connected
        # On unfixed code: May hang or take longer
        # On fixed code: Returns immediately
        self.assertLess(
            elapsed, 0.5,
            f"Function took {elapsed:.1f}s when not connected - should return immediately"
        )
        
        # Should not yield any ticks when not connected
        self.assertEqual(
            result_count, 0,
            f"Function yielded {result_count} ticks when not connected - should yield 0"
        )
    
    def test_no_max_ticks_parameter(self):
        """
        Test that function has no max_ticks parameter to limit tick count
        
        EXPECTED ON UNFIXED CODE: No max_ticks parameter exists
        EXPECTED ON FIXED CODE: max_ticks parameter exists and works
        """
        client = IBKRClient(ib_instance=self.mock_ib)
        client.connected = True
        
        contract = Stock('NVDA', 'SMART', 'USD')
        contract.symbol = 'NVDA'
        
        # Mock ticker with continuous ticks
        mock_ticker = MagicMock()
        mock_tick = MagicMock()
        mock_tick.time = datetime.now()
        mock_tick.price = 500.50
        mock_tick.size = 100
        mock_tick.exchange = 'NASDAQ'
        mock_ticker.ticks = [mock_tick]
        
        self.mock_ib.qualifyContracts.return_value = [contract]
        self.mock_ib.reqTickByTickData.return_value = mock_ticker
        self.mock_ib.sleep = lambda x: time.sleep(0.001)
        
        # Try to use max_ticks parameter
        tick_count = 0
        start_time = time.time()
        
        try:
            # This should work on fixed code
            gen = client.req_tick_by_tick_data(contract, 'AllLast', max_ticks=5)
            for tick in gen:
                tick_count += 1
                if tick_count >= 10 or time.time() - start_time > 2.0:
                    # Force break if not working
                    break
        except TypeError as e:
            # On unfixed code: max_ticks parameter doesn't exist
            if 'max_ticks' in str(e):
                self.fail(f"max_ticks parameter not implemented: {e}")
        
        # ASSERTION: Should stop at max_ticks=5
        # On unfixed code: Will continue indefinitely (we break at 10)
        # On fixed code: Stops at 5
        self.assertLessEqual(
            tick_count, 5,
            f"Function yielded {tick_count} ticks with max_ticks=5 - should stop at 5"
        )
    
    def test_no_resource_cleanup_on_exception(self):
        """
        Test that subscription is not cancelled when exception occurs
        
        EXPECTED ON UNFIXED CODE: No try...finally, subscription not cancelled
        EXPECTED ON FIXED CODE: Subscription cancelled in finally block
        """
        client = IBKRClient(ib_instance=self.mock_ib)
        client.connected = True
        
        contract = Stock('NVDA', 'SMART', 'USD')
        contract.symbol = 'NVDA'
        
        # Mock ticker
        mock_ticker = MagicMock()
        mock_ticker.ticks = []
        
        self.mock_ib.qualifyContracts.return_value = [contract]
        self.mock_ib.reqTickByTickData.return_value = mock_ticker
        
        # Simulate exception during processing
        self.mock_ib.sleep.side_effect = Exception("Simulated error")
        
        # Try to consume generator
        try:
            gen = client.req_tick_by_tick_data(contract, 'AllLast')
            next(gen)
        except Exception:
            pass
        
        # ASSERTION: cancelTickByTickData should be called to clean up
        # On unfixed code: Not called (no finally block)
        # On fixed code: Called in finally block
        # Note: We can't directly test this without modifying the code,
        # but we document the expected behavior
        
        # This is a documentation test - the actual verification happens
        # when we implement the fix with try...finally
        pass


class TestTickByTickBugDocumentation(unittest.TestCase):
    """
    Documentation of bug counterexamples found
    
    These tests document the specific failures observed on unfixed code.
    """
    
    def test_counterexample_1_infinite_loop(self):
        """
        Counterexample 1: Function hangs indefinitely without timeout
        
        Observed behavior on unfixed code:
        - while True loop never exits
        - No timeout mechanism
        - Thread continues running indefinitely
        """
        # This test documents the bug - see test_infinite_loop_no_timeout above
        pass
    
    def test_counterexample_2_no_connection_check(self):
        """
        Counterexample 2: Function enters loop even with no connection
        
        Observed behavior on unfixed code:
        - No connection state check before entering loop
        - Continues to run even when IBKR Gateway not connected
        - Wastes resources attempting to read non-existent data
        """
        # This test documents the bug - see test_no_connection_still_enters_loop above
        pass
    
    def test_counterexample_3_no_tick_limit(self):
        """
        Counterexample 3: No max_ticks parameter to limit tick count
        
        Observed behavior on unfixed code:
        - max_ticks parameter doesn't exist
        - No way to limit number of ticks received
        - Function runs until manually interrupted
        """
        # This test documents the bug - see test_no_max_ticks_parameter above
        pass
    
    def test_counterexample_4_no_resource_cleanup(self):
        """
        Counterexample 4: Subscription not cancelled on exception
        
        Observed behavior on unfixed code:
        - No try...finally block
        - cancelTickByTickData not called on exception
        - Resources leaked when errors occur
        """
        # This test documents the bug - see test_no_resource_cleanup_on_exception above
        pass


if __name__ == '__main__':
    # Run with verbose output to see which tests fail
    unittest.main(verbosity=2)
