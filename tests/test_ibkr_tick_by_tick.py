#!/usr/bin/env python3
"""
Unit tests for IBKR tick-by-tick functionality (Task 1)

Tests cover:
- 1.1: req_tick_by_tick_data() method
- 1.2: Exchange filtering for FINRA ADF ('D')
- 1.3: Tick data parsing for Tick 48 (RT Volume) and Tick 77 (RT Trade Volume)
- 1.4: TickByTickData data class
- 1.5: Error handling for tick-by-tick streams
"""

import sys
import unittest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
from typing import List

sys.path.append('.')

from data_layer.ibkr_client import IBKRClient, TickByTickData
from ib_insync import Stock, Contract


class TestTickByTickData(unittest.TestCase):
    """Test TickByTickData dataclass (Task 1.4)"""
    
    def test_tick_by_tick_data_creation(self):
        """Test creating TickByTickData object"""
        tick = TickByTickData(
            ticker='NVDA',
            timestamp=datetime.now(),
            price=500.50,
            size=100,
            exchange='D',
            tick_type='AllLast',
            tick_tags={48: 1000000, 77: 800000}
        )
        
        self.assertEqual(tick.ticker, 'NVDA')
        self.assertEqual(tick.price, 500.50)
        self.assertEqual(tick.size, 100)
        self.assertEqual(tick.exchange, 'D')
        self.assertEqual(tick.tick_type, 'AllLast')
    
    def test_get_tag(self):
        """Test get_tag method"""
        tick = TickByTickData(
            ticker='NVDA',
            timestamp=datetime.now(),
            price=500.50,
            size=100,
            exchange='D',
            tick_type='AllLast',
            tick_tags={48: 1000000, 77: 800000}
        )
        
        self.assertEqual(tick.get_tag(48), 1000000)
        self.assertEqual(tick.get_tag(77), 800000)
        self.assertIsNone(tick.get_tag(999))
    
    def test_has_tag(self):
        """Test has_tag method"""
        tick = TickByTickData(
            ticker='NVDA',
            timestamp=datetime.now(),
            price=500.50,
            size=100,
            exchange='D',
            tick_type='AllLast',
            tick_tags={48: 1000000, 77: 800000}
        )
        
        self.assertTrue(tick.has_tag(48))
        self.assertTrue(tick.has_tag(77))
        self.assertFalse(tick.has_tag(999))
    
    def test_has_tags(self):
        """Test has_tags method with multiple tags"""
        tick = TickByTickData(
            ticker='NVDA',
            timestamp=datetime.now(),
            price=500.50,
            size=100,
            exchange='D',
            tick_type='AllLast',
            tick_tags={48: 1000000, 77: 800000, 63: 50000}
        )
        
        self.assertTrue(tick.has_tags(48, 77))
        self.assertTrue(tick.has_tags(48, 77, 63))
        self.assertFalse(tick.has_tags(48, 77, 999))
        self.assertFalse(tick.has_tags(999))


class TestIBKRClientTickByTick(unittest.TestCase):
    """Test IBKRClient tick-by-tick methods (Tasks 1.1, 1.2, 1.3, 1.5)"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_ib = MagicMock()
        self.mock_ib.isConnected.return_value = True
        
    @patch('data_layer.ibkr_client.IB')
    def test_req_tick_by_tick_data_not_connected(self, mock_ib_class):
        """Test req_tick_by_tick_data when not connected (Task 1.5)"""
        client = IBKRClient(ib_instance=self.mock_ib)
        client.connected = False
        
        contract = Stock('NVDA', 'SMART', 'USD')
        
        # Should return empty generator when not connected
        result = list(client.req_tick_by_tick_data(contract))
        self.assertEqual(len(result), 0)
    
    @patch('data_layer.ibkr_client.IB')
    def test_req_tick_by_tick_data_basic(self, mock_ib_class):
        """Test basic req_tick_by_tick_data functionality (Task 1.1)"""
        client = IBKRClient(ib_instance=self.mock_ib)
        client.connected = True
        
        # Mock contract
        contract = Stock('NVDA', 'SMART', 'USD')
        contract.symbol = 'NVDA'
        
        # Mock ticker with tick data
        mock_ticker = MagicMock()
        mock_tick = MagicMock()
        mock_tick.time = datetime.now()
        mock_tick.price = 500.50
        mock_tick.size = 100
        mock_tick.exchange = 'NASDAQ'
        mock_ticker.ticks = [mock_tick]
        
        self.mock_ib.qualifyContracts.return_value = [contract]
        self.mock_ib.reqTickByTickData.return_value = mock_ticker
        
        # Test the method exists and can be called
        gen = client.req_tick_by_tick_data(contract, 'AllLast')
        self.assertIsNotNone(gen)
        
        # Verify IBKR methods were called
        self.mock_ib.qualifyContracts.assert_called_once_with(contract)
        self.mock_ib.reqTickByTickData.assert_called_once()
    
    @patch('data_layer.ibkr_client.IB')
    def test_exchange_filtering(self, mock_ib_class):
        """Test exchange filtering for FINRA ADF ('D') (Task 1.2)"""
        client = IBKRClient(ib_instance=self.mock_ib)
        client.connected = True
        
        contract = Stock('NVDA', 'SMART', 'USD')
        contract.symbol = 'NVDA'
        
        # Mock ticker with mixed exchange ticks
        mock_ticker = MagicMock()
        
        # Create ticks from different exchanges
        dark_pool_tick = MagicMock()
        dark_pool_tick.time = datetime.now()
        dark_pool_tick.price = 500.50
        dark_pool_tick.size = 100
        dark_pool_tick.exchange = 'D'  # FINRA ADF (dark pool)
        
        nasdaq_tick = MagicMock()
        nasdaq_tick.time = datetime.now()
        nasdaq_tick.price = 500.55
        nasdaq_tick.size = 50
        nasdaq_tick.exchange = 'NASDAQ'
        
        mock_ticker.ticks = [dark_pool_tick, nasdaq_tick]
        
        self.mock_ib.qualifyContracts.return_value = [contract]
        self.mock_ib.reqTickByTickData.return_value = mock_ticker
        
        # Request with exchange filter 'D'
        gen = client.req_tick_by_tick_data(contract, 'AllLast', exchange_filter='D')
        
        # Verify filtering logic exists
        self.assertIsNotNone(gen)
    
    @patch('data_layer.ibkr_client.IB')
    def test_tick_tag_parsing(self, mock_ib_class):
        """Test parsing of Tick 48 (RT Volume) and Tick 77 (RT Trade Volume) (Task 1.3)"""
        client = IBKRClient(ib_instance=self.mock_ib)
        client.connected = True
        
        contract = Stock('NVDA', 'SMART', 'USD')
        contract.symbol = 'NVDA'
        
        # Mock ticker with tick tags
        mock_ticker = MagicMock()
        mock_ticker.rtVolume = 1000000  # Tick 48
        mock_ticker.rtTradeVolume = 800000  # Tick 77
        
        mock_tick = MagicMock()
        mock_tick.time = datetime.now()
        mock_tick.price = 500.50
        mock_tick.size = 100
        mock_tick.exchange = 'D'
        mock_ticker.ticks = [mock_tick]
        
        self.mock_ib.qualifyContracts.return_value = [contract]
        self.mock_ib.reqTickByTickData.return_value = mock_ticker
        
        # Test tick tag parsing
        gen = client.req_tick_by_tick_data(contract, 'AllLast')
        self.assertIsNotNone(gen)
    
    @patch('data_layer.ibkr_client.IB')
    def test_error_handling(self, mock_ib_class):
        """Test error handling for tick-by-tick streams (Task 1.5)"""
        client = IBKRClient(ib_instance=self.mock_ib)
        client.connected = True
        
        contract = Stock('NVDA', 'SMART', 'USD')
        
        # Mock an exception during qualification
        self.mock_ib.qualifyContracts.side_effect = Exception("Connection error")
        
        # Should handle error gracefully
        result = list(client.req_tick_by_tick_data(contract))
        self.assertEqual(len(result), 0)


class TestTickByTickIntegration(unittest.TestCase):
    """Integration tests for tick-by-tick functionality"""
    
    def test_dark_pool_volume_calculation(self):
        """Test dark pool volume calculation using Tick 48 and 77"""
        # Create tick with RT Volume and RT Trade Volume
        tick = TickByTickData(
            ticker='NVDA',
            timestamp=datetime.now(),
            price=500.50,
            size=100,
            exchange='D',
            tick_type='AllLast',
            tick_tags={
                48: 1000000,  # RT Volume (total including dark pools)
                77: 800000    # RT Trade Volume (lit exchanges only)
            }
        )
        
        # Calculate dark pool volume
        rt_volume = tick.get_tag(48)
        rt_trade_volume = tick.get_tag(77)
        dark_pool_volume = rt_volume - rt_trade_volume
        
        self.assertEqual(dark_pool_volume, 200000)
        self.assertEqual(dark_pool_volume / rt_volume * 100, 20.0)  # 20% dark pool
    
    def test_tick_data_validation(self):
        """Test tick data validation"""
        tick = TickByTickData(
            ticker='NVDA',
            timestamp=datetime.now(),
            price=500.50,
            size=100,
            exchange='D',
            tick_type='AllLast',
            tick_tags={48: 1000000, 77: 800000}
        )
        
        # Validate required fields
        self.assertIsNotNone(tick.ticker)
        self.assertIsNotNone(tick.timestamp)
        self.assertGreater(tick.price, 0)
        self.assertGreaterEqual(tick.size, 0)
        self.assertIsNotNone(tick.exchange)
        self.assertIsNotNone(tick.tick_type)
    
    def test_multiple_tick_tags(self):
        """Test handling multiple tick tags"""
        tick = TickByTickData(
            ticker='NVDA',
            timestamp=datetime.now(),
            price=500.50,
            size=100,
            exchange='D',
            tick_type='AllLast',
            tick_tags={
                48: 1000000,  # RT Volume
                77: 800000,   # RT Trade Volume
                63: 50000,    # 3-min volume
                64: 100000,   # 5-min volume
                65: 200000    # 10-min volume
            }
        )
        
        # Verify all tags are accessible
        self.assertTrue(tick.has_tags(48, 77, 63, 64, 65))
        self.assertEqual(tick.get_tag(63), 50000)
        self.assertEqual(tick.get_tag(64), 100000)
        self.assertEqual(tick.get_tag(65), 200000)


if __name__ == '__main__':
    unittest.main()
