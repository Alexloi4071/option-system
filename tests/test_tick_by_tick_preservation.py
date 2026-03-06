#!/usr/bin/env python3
"""
Preservation Property Tests for Tick-by-Tick Functionality

These tests capture the CORRECT behavior that must be preserved after the fix.
They should PASS on both unfixed and fixed code.

Property 2: Preservation - Data Processing Logic
- Normal tick data reception and yield mechanism
- Exchange filter logic for filtering non-matching exchanges
- rtVolume and rtTradeVolume parsing logic
- Duplicate tick detection (same timestamp) and skipping
- Contract qualification flow
- Error logging to logger and _record_error()
"""

import sys
import unittest
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime
from typing import List

sys.path.append('.')

from data_layer.ibkr_client import IBKRClient, TickByTickData
from ib_insync import Stock


class TestTickByTickPreservation(unittest.TestCase):
    """
    Preservation tests for tick-by-tick data processing
    
    These tests verify that existing functionality is preserved after the fix.
    """
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_ib = MagicMock()
        self.mock_ib.isConnected.return_value = True
        
    def test_preservation_tick_data_reception_and_yield(self):
        """
        Preservation: Normal tick data reception and yield mechanism
        
        Requirement 3.1: WHEN connection is normal and no timeout/limit reached
        THEN system should continue to receive and yield tick data normally
        """
        client = IBKRClient(ib_instance=self.mock_ib)
        client.connected = True
        
        contract = Stock('NVDA', 'SMART', 'USD')
        contract.symbol = 'NVDA'
        
        # Mock ticker with tick data
        mock_ticker = MagicMock()
        mock_tick1 = MagicMock()
        mock_tick1.time = datetime(2026, 3, 6, 10, 0, 0)
        mock_tick1.price = 500.50
        mock_tick1.size = 100
        mock_tick1.exchange = 'NASDAQ'
        
        mock_tick2 = MagicMock()
        mock_tick2.time = datetime(2026, 3, 6, 10, 0, 1)
        mock_tick2.price = 500.55
        mock_tick2.size = 200
        mock_tick2.exchange = 'NASDAQ'
        
        # Simulate ticks arriving
        tick_sequence = [[mock_tick1], [mock_tick1, mock_tick2]]
        call_count = [0]
        
        def get_ticks():
            idx = min(call_count[0], len(tick_sequence) - 1)
            call_count[0] += 1
            return tick_sequence[idx]
        
        mock_ticker.ticks = property(lambda self: get_ticks())
        
        self.mock_ib.qualifyContracts.return_value = [contract]
        self.mock_ib.reqTickByTickData.return_value = mock_ticker
        
        # Collect ticks (limit to 2 to avoid infinite loop)
        ticks_received = []
        gen = client.req_tick_by_tick_data(contract, 'AllLast')
        
        for i, tick in enumerate(gen):
            ticks_received.append(tick)
            if i >= 1:  # Get 2 ticks then break
                break
        
        # Verify ticks were yielded correctly
        self.assertEqual(len(ticks_received), 2)
        self.assertEqual(ticks_received[0].ticker, 'NVDA')
        self.assertEqual(ticks_received[0].price, 500.50)
        self.assertEqual(ticks_received[0].size, 100)
        self.assertEqual(ticks_received[1].price, 500.55)
        self.assertEqual(ticks_received[1].size, 200)
    
    def test_preservation_exchange_filter_logic(self):
        """
        Preservation: Exchange filter logic for filtering non-matching exchanges
        
        Requirement 3.2: WHEN tick data contains exchange info and exchange_filter is specified
        THEN system should correctly filter non-matching exchanges
        """
        client = IBKRClient(ib_instance=self.mock_ib)
        client.connected = True
        
        contract = Stock('NVDA', 'SMART', 'USD')
        contract.symbol = 'NVDA'
        
        # Mock ticker with mixed exchange ticks
        mock_ticker = MagicMock()
        
        dark_pool_tick = MagicMock()
        dark_pool_tick.time = datetime(2026, 3, 6, 10, 0, 0)
        dark_pool_tick.price = 500.50
        dark_pool_tick.size = 100
        dark_pool_tick.exchange = 'D'  # FINRA ADF (dark pool)
        
        nasdaq_tick = MagicMock()
        nasdaq_tick.time = datetime(2026, 3, 6, 10, 0, 1)
        nasdaq_tick.price = 500.55
        nasdaq_tick.size = 50
        nasdaq_tick.exchange = 'NASDAQ'
        
        mock_ticker.ticks = [dark_pool_tick, nasdaq_tick]
        
        self.mock_ib.qualifyContracts.return_value = [contract]
        self.mock_ib.reqTickByTickData.return_value = mock_ticker
        
        # Request with exchange filter 'D' (dark pools only)
        ticks_received = []
        gen = client.req_tick_by_tick_data(contract, 'AllLast', exchange_filter='D')
        
        for i, tick in enumerate(gen):
            ticks_received.append(tick)
            if i >= 1:  # Limit to avoid infinite loop
                break
        
        # Verify only dark pool ticks are yielded
        self.assertGreater(len(ticks_received), 0)
        for tick in ticks_received:
            self.assertEqual(tick.exchange, 'D', 
                           f"Exchange filter failed: got {tick.exchange}, expected 'D'")
    
    def test_preservation_tick_tags_parsing(self):
        """
        Preservation: rtVolume and rtTradeVolume parsing logic
        
        Requirement 3.3: WHEN ticker contains rtVolume or rtTradeVolume info
        THEN system should correctly parse and populate tick_tags
        """
        client = IBKRClient(ib_instance=self.mock_ib)
        client.connected = True
        
        contract = Stock('NVDA', 'SMART', 'USD')
        contract.symbol = 'NVDA'
        
        # Mock ticker with tick tags
        mock_ticker = MagicMock()
        mock_ticker.rtVolume = 1000000  # Tick 48
        mock_ticker.rtTradeVolume = 800000  # Tick 77
        
        mock_tick = MagicMock()
        mock_tick.time = datetime(2026, 3, 6, 10, 0, 0)
        mock_tick.price = 500.50
        mock_tick.size = 100
        mock_tick.exchange = 'NASDAQ'
        
        mock_ticker.ticks = [mock_tick]
        
        self.mock_ib.qualifyContracts.return_value = [contract]
        self.mock_ib.reqTickByTickData.return_value = mock_ticker
        
        # Collect tick
        gen = client.req_tick_by_tick_data(contract, 'AllLast')
        tick = next(gen)
        
        # Verify tick tags are parsed correctly
        self.assertIn(48, tick.tick_tags, "Tick 48 (rtVolume) not parsed")
        self.assertIn(77, tick.tick_tags, "Tick 77 (rtTradeVolume) not parsed")
        self.assertEqual(tick.tick_tags[48], 1000000)
        self.assertEqual(tick.tick_tags[77], 800000)
    
    def test_preservation_duplicate_tick_detection(self):
        """
        Preservation: Duplicate tick detection (same timestamp) and skipping
        
        Requirement 3.4: WHEN receiving duplicate tick (same timestamp)
        THEN system should skip already processed ticks
        """
        client = IBKRClient(ib_instance=self.mock_ib)
        client.connected = True
        
        contract = Stock('NVDA', 'SMART', 'USD')
        contract.symbol = 'NVDA'
        
        # Mock ticker with duplicate timestamps
        mock_ticker = MagicMock()
        
        same_time = datetime(2026, 3, 6, 10, 0, 0)
        
        tick1 = MagicMock()
        tick1.time = same_time
        tick1.price = 500.50
        tick1.size = 100
        tick1.exchange = 'NASDAQ'
        
        tick2_duplicate = MagicMock()
        tick2_duplicate.time = same_time  # Same timestamp
        tick2_duplicate.price = 500.51
        tick2_duplicate.size = 50
        tick2_duplicate.exchange = 'NASDAQ'
        
        tick3_new = MagicMock()
        tick3_new.time = datetime(2026, 3, 6, 10, 0, 1)  # New timestamp
        tick3_new.price = 500.55
        tick3_new.size = 200
        tick3_new.exchange = 'NASDAQ'
        
        # Simulate tick sequence
        tick_sequence = [
            [tick1],
            [tick1, tick2_duplicate],  # tick2 has same timestamp as tick1
            [tick1, tick2_duplicate, tick3_new]
        ]
        call_count = [0]
        
        def get_ticks():
            idx = min(call_count[0], len(tick_sequence) - 1)
            call_count[0] += 1
            return tick_sequence[idx]
        
        type(mock_ticker).ticks = property(lambda self: get_ticks())
        
        self.mock_ib.qualifyContracts.return_value = [contract]
        self.mock_ib.reqTickByTickData.return_value = mock_ticker
        
        # Collect ticks
        ticks_received = []
        gen = client.req_tick_by_tick_data(contract, 'AllLast')
        
        for i, tick in enumerate(gen):
            ticks_received.append(tick)
            if i >= 1:  # Get 2 unique ticks
                break
        
        # Verify duplicate was skipped
        self.assertEqual(len(ticks_received), 2)
        self.assertNotEqual(ticks_received[0].timestamp, ticks_received[1].timestamp,
                          "Duplicate tick was not skipped")
    
    def test_preservation_contract_qualification(self):
        """
        Preservation: Contract qualification flow
        
        Requirement 3.5: WHEN contract needs qualify
        THEN system should qualify contract before requesting data
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
        
        # Start generator (don't consume, just start)
        gen = client.req_tick_by_tick_data(contract, 'AllLast')
        try:
            next(gen)
        except StopIteration:
            pass
        
        # Verify qualifyContracts was called before reqTickByTickData
        self.mock_ib.qualifyContracts.assert_called_once_with(contract)
        self.mock_ib.reqTickByTickData.assert_called_once()
        
        # Verify order: qualify before request
        calls = [call[0] for call in self.mock_ib.method_calls]
        qualify_index = calls.index('qualifyContracts')
        request_index = calls.index('reqTickByTickData')
        self.assertLess(qualify_index, request_index,
                       "Contract should be qualified before requesting tick data")
    
    @patch('data_layer.ibkr_client.logger')
    def test_preservation_error_logging(self, mock_logger):
        """
        Preservation: Error logging to logger and _record_error()
        
        Requirement 3.6: WHEN exception occurs
        THEN system should log error to logger and _record_error()
        """
        client = IBKRClient(ib_instance=self.mock_ib)
        client.connected = True
        
        contract = Stock('NVDA', 'SMART', 'USD')
        contract.symbol = 'NVDA'
        
        # Mock exception during qualification
        self.mock_ib.qualifyContracts.side_effect = Exception("Connection error")
        
        # Try to start generator
        gen = client.req_tick_by_tick_data(contract, 'AllLast')
        try:
            next(gen)
        except StopIteration:
            pass
        
        # Verify error was logged
        mock_logger.error.assert_called()
        error_calls = [str(call) for call in mock_logger.error.call_args_list]
        self.assertTrue(
            any('Connection error' in str(call) for call in error_calls),
            "Error should be logged to logger"
        )
        
        # Verify _record_error was called
        self.assertGreater(len(client._recent_errors), 0,
                          "Error should be recorded in _recent_errors")


class TestTickByTickDataClassPreservation(unittest.TestCase):
    """Preservation tests for TickByTickData dataclass"""
    
    def test_preservation_tick_data_structure(self):
        """
        Preservation: TickByTickData structure and methods
        
        Verify that TickByTickData dataclass maintains its structure
        """
        tick = TickByTickData(
            ticker='NVDA',
            timestamp=datetime.now(),
            price=500.50,
            size=100,
            exchange='D',
            tick_type='AllLast',
            tick_tags={48: 1000000, 77: 800000}
        )
        
        # Verify all fields exist
        self.assertEqual(tick.ticker, 'NVDA')
        self.assertIsInstance(tick.timestamp, datetime)
        self.assertEqual(tick.price, 500.50)
        self.assertEqual(tick.size, 100)
        self.assertEqual(tick.exchange, 'D')
        self.assertEqual(tick.tick_type, 'AllLast')
        self.assertIsInstance(tick.tick_tags, dict)
    
    def test_preservation_tick_data_methods(self):
        """
        Preservation: TickByTickData helper methods
        
        Verify that get_tag(), has_tag(), has_tags() methods work correctly
        """
        tick = TickByTickData(
            ticker='NVDA',
            timestamp=datetime.now(),
            price=500.50,
            size=100,
            exchange='D',
            tick_type='AllLast',
            tick_tags={48: 1000000, 77: 800000, 63: 50000}
        )
        
        # Test get_tag()
        self.assertEqual(tick.get_tag(48), 1000000)
        self.assertIsNone(tick.get_tag(999))
        
        # Test has_tag()
        self.assertTrue(tick.has_tag(48))
        self.assertFalse(tick.has_tag(999))
        
        # Test has_tags()
        self.assertTrue(tick.has_tags(48, 77))
        self.assertTrue(tick.has_tags(48, 77, 63))
        self.assertFalse(tick.has_tags(48, 77, 999))


if __name__ == '__main__':
    print("=" * 70)
    print("PRESERVATION PROPERTY TESTS")
    print("=" * 70)
    print("These tests verify that existing functionality is preserved.")
    print("EXPECTED: Tests should PASS on both unfixed and fixed code")
    print("=" * 70)
    print()
    
    unittest.main(verbosity=2)
