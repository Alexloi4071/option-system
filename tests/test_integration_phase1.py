#!/usr/bin/env python3
"""
Integration Tests for Phase 1: Dark Pool Infrastructure

Tests cover:
- 5.1: Tick-by-tick data streaming with mock data
- 5.2: StreamManager with multiple concurrent streams
- 5.3: Dark pool detection with historical data
- 5.4: Large order detection with simulated orders
- 5.5: Verify no breaking changes to existing functionality
"""

import sys
import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from threading import Thread
import time

sys.path.append('.')

from data_layer.ibkr_client import IBKRClient, TickByTickData
from data_layer.stream_manager import StreamManager
from calculation_layer.module38_dark_pool import DarkPoolDetector
from calculation_layer.module35_large_orders import LargeOrderDetector


class TestTickByTickStreaming(unittest.TestCase):
    """Test tick-by-tick data streaming with mock data (Task 5.1)"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.client = IBKRClient()
    
    def test_tick_by_tick_method_exists(self):
        """Test that req_tick_by_tick_data method exists"""
        self.assertTrue(hasattr(self.client, 'req_tick_by_tick_data'))
        self.assertTrue(callable(self.client.req_tick_by_tick_data))
    
    def test_tick_by_tick_parameters(self):
        """Test tick-by-tick method accepts correct parameters"""
        import inspect
        sig = inspect.signature(self.client.req_tick_by_tick_data)
        params = list(sig.parameters.keys())
        
        # Check required parameters exist (using actual parameter names)
        self.assertIn('contract', params)  # contract instead of ticker
        self.assertIn('tick_type', params)
        self.assertIn('timeout', params)
        self.assertIn('max_ticks', params)


class TestStreamManagerIntegration(unittest.TestCase):
    """Test StreamManager with multiple concurrent streams (Task 5.2)"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.manager = StreamManager(max_concurrent=15)
    
    def test_concurrent_stream_allocation(self):
        """Test allocating multiple concurrent streams"""
        tickers = [f'TICKER{i}' for i in range(10)]
        
        for ticker in tickers:
            stream = self.manager.add_stream(ticker, 'tick_by_tick')
            self.assertIsNotNone(stream)
        
        # Check active streams
        active = self.manager.get_active_streams()
        self.assertEqual(len(active), 10)
    
    def test_stream_quota_enforcement(self):
        """Test that stream quota is enforced"""
        # Allocate max streams
        for i in range(15):
            stream = self.manager.add_stream(f'TICKER{i}', 'tick_by_tick')
            self.assertIsNotNone(stream)
        
        # Try to allocate one more (should fail)
        stream = self.manager.add_stream('TICKER16', 'tick_by_tick')
        self.assertIsNone(stream)
        
        # Release one stream
        self.manager.remove_stream('TICKER0')
        
        # Now allocation should succeed
        stream = self.manager.add_stream('TICKER16', 'tick_by_tick')
        self.assertIsNotNone(stream)
    
    def test_stream_cleanup(self):
        """Test automatic stream cleanup"""
        # Allocate streams with old timestamps
        old_time = datetime.now() - timedelta(minutes=10)
        
        for i in range(5):
            self.manager.add_stream(f'TICKER{i}', 'tick_by_tick')
            # Manually set old timestamp
            self.manager._active_streams[f'TICKER{i}'].start_time = old_time
        
        # Run cleanup (max_age_seconds = 5 minutes = 300 seconds)
        cleaned = self.manager.cleanup_stale_streams(max_age_seconds=300)
        
        # All 5 streams should be cleaned
        self.assertEqual(cleaned, 5)
        self.assertEqual(len(self.manager.get_active_streams()), 0)
    
    def test_stream_health_monitoring(self):
        """Test stream health monitoring"""
        # Allocate some streams
        for i in range(10):
            self.manager.add_stream(f'TICKER{i}', 'tick_by_tick')
        
        # Get health status
        health = self.manager.get_health_status()
        
        self.assertEqual(health['active_count'], 10)
        self.assertEqual(health['capacity'], 15)
        self.assertGreater(health['utilization'], 0)


class TestDarkPoolIntegration(unittest.TestCase):
    """Test dark pool detection with historical data (Task 5.3)"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.detector = DarkPoolDetector()
    
    def test_dark_pool_detection_with_history(self):
        """Test dark pool detection with historical average"""
        # Simulate RT Volume and RT Trade Volume
        rt_volume = 1000000  # Total volume
        rt_trade_volume = 600000  # Lit exchange volume
        # Dark pool volume = 400000 (40%)
        
        # Detect dark pool activity
        signal = self.detector.detect_dark_pool_activity(
            ticker='NVDA',
            rt_volume=rt_volume,
            rt_trade_volume=rt_trade_volume,
            vwap=500.0,
            current_price=502.5,
            historical_avg=300000  # Historical average
        )
        
        self.assertIsNotNone(signal)
        self.assertGreater(signal.dark_pool_pct, 0)
        self.assertEqual(signal.dark_volume, 400000)
    
    def test_dark_pool_surge_detection(self):
        """Test dark pool surge detection"""
        # Current: 70% dark pool (surge!)
        rt_volume = 1000000
        rt_trade_volume = 300000  # Only 30% lit
        # Dark pool = 700000 (70%)
        
        signal = self.detector.detect_dark_pool_activity(
            ticker='NVDA',
            rt_volume=rt_volume,
            rt_trade_volume=rt_trade_volume,
            vwap=500.0,
            current_price=502.5,
            historical_avg=300000  # Historical average
        )
        
        self.assertIsNotNone(signal)
        self.assertTrue(signal.surge_detected)
        self.assertGreater(signal.dark_pool_pct, 60)


class TestLargeOrderIntegration(unittest.TestCase):
    """Test large order detection with simulated orders (Task 5.4)"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.detector = LargeOrderDetector()
    
    def test_large_order_detection_workflow(self):
        """Test complete large order detection workflow"""
        # Simulate tick stream with large orders
        base_time = datetime.now()
        ticks = []
        
        # Add 3 consecutive large orders
        for i in range(3):
            ticks.append(TickByTickData(
                ticker='NVDA',
                timestamp=base_time + timedelta(seconds=i*60),
                price=500.0 + i,
                size=15000,  # Block trade
                exchange='NASDAQ',
                tick_type='AllLast',
                tick_tags={}
            ))
        
        # Detect large orders
        signals = self.detector.detect_large_orders(
            ticker='NVDA',
            tick_stream=ticks,
            vwap=500.0
        )
        
        self.assertEqual(len(signals), 3)
        
        # Check consecutive counts
        self.assertEqual(signals[0].consecutive_count, 1)
        self.assertEqual(signals[1].consecutive_count, 2)
        self.assertEqual(signals[2].consecutive_count, 3)
        
        # All should be institutional
        for signal in signals:
            self.assertTrue(signal.institutional_footprint)
    
    def test_institutional_footprint_detection(self):
        """Test institutional footprint identification"""
        # Create tick with >$250K value
        ticks = [
            TickByTickData(
                ticker='NVDA',
                timestamp=datetime.now(),
                price=500.0,
                size=600,  # $300K
                exchange='NASDAQ',
                tick_type='AllLast',
                tick_tags={}
            )
        ]
        
        signals = self.detector.detect_large_orders(
            ticker='NVDA',
            tick_stream=ticks,
            vwap=500.0
        )
        
        self.assertEqual(len(signals), 1)
        self.assertTrue(signals[0].institutional_footprint)
        self.assertEqual(signals[0].order_value, 300000.0)


class TestBackwardCompatibility(unittest.TestCase):
    """Verify no breaking changes to existing functionality (Task 5.5)"""
    
    def test_ibkr_client_existing_methods(self):
        """Test that existing IBKRClient methods still work"""
        client = IBKRClient()
        
        # Check that existing methods exist
        self.assertTrue(hasattr(client, 'connect'))
        self.assertTrue(hasattr(client, 'disconnect'))
        self.assertTrue(hasattr(client, 'is_connected'))
        
        # Check new method exists
        self.assertTrue(hasattr(client, 'req_tick_by_tick_data'))
    
    def test_tick_by_tick_data_structure(self):
        """Test TickByTickData structure"""
        tick = TickByTickData(
            ticker='NVDA',
            timestamp=datetime.now(),
            price=500.0,
            size=100,
            exchange='NASDAQ',
            tick_type='AllLast',
            tick_tags={}
        )
        
        # Check all required fields
        self.assertEqual(tick.ticker, 'NVDA')
        self.assertIsInstance(tick.timestamp, datetime)
        self.assertEqual(tick.price, 500.0)
        self.assertEqual(tick.size, 100)
        self.assertEqual(tick.exchange, 'NASDAQ')
    
    def test_module_imports(self):
        """Test that all new modules can be imported"""
        try:
            from data_layer.stream_manager import StreamManager
            from calculation_layer.module38_dark_pool import DarkPoolDetector
            from calculation_layer.module35_large_orders import LargeOrderDetector
            
            # Instantiate to verify no import errors
            StreamManager()
            DarkPoolDetector()
            LargeOrderDetector()
            
        except ImportError as e:
            self.fail(f"Import failed: {e}")


class TestEndToEndWorkflow(unittest.TestCase):
    """End-to-end integration test"""
    
    def test_complete_phase1_workflow(self):
        """Test complete Phase 1 workflow"""
        # 1. Initialize components
        stream_manager = StreamManager(max_concurrent=15)
        dark_pool_detector = DarkPoolDetector()
        large_order_detector = LargeOrderDetector()
        
        # 2. Allocate stream
        stream = stream_manager.add_stream('NVDA', 'tick_by_tick')
        self.assertIsNotNone(stream)
        
        # 3. Simulate tick data
        ticks = [
            TickByTickData(
                ticker='NVDA',
                timestamp=datetime.now(),
                price=500.0,
                size=15000,
                exchange='D',  # Dark pool
                tick_type='AllLast',
                tick_tags={}
            )
        ]
        
        # 4. Detect large orders
        large_order_signals = large_order_detector.detect_large_orders(
            ticker='NVDA',
            tick_stream=ticks,
            vwap=500.0
        )
        
        self.assertGreater(len(large_order_signals), 0)
        
        # 5. Detect dark pool activity
        dark_pool_signal = dark_pool_detector.detect_dark_pool_activity(
            ticker='NVDA',
            rt_volume=1000000,
            rt_trade_volume=600000,
            vwap=500.0,
            current_price=502.5,
            historical_avg=300000
        )
        
        self.assertIsNotNone(dark_pool_signal)
        
        # 6. Release stream
        stream_manager.remove_stream('NVDA')
        
        # 7. Verify stream released
        active = stream_manager.get_active_streams()
        self.assertEqual(len(active), 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
