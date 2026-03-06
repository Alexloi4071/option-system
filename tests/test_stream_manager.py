#!/usr/bin/env python3
"""
Unit tests for StreamManager (Task 2)

Tests cover:
- 2.1: StreamManager creation
- 2.2: Concurrent stream tracking (max 15)
- 2.3: Stream queuing mechanism
- 2.4: Automatic stream cleanup
- 2.5: Stream health monitoring
"""

import sys
import unittest
import time
from datetime import datetime, timedelta

sys.path.append('.')

from data_layer.stream_manager import StreamManager, Stream


class TestStream(unittest.TestCase):
    """Test Stream dataclass"""
    
    def test_stream_creation(self):
        """Test creating Stream object"""
        stream = Stream(
            ticker='NVDA',
            stream_type='tick_by_tick',
            req_id=12345
        )
        
        self.assertEqual(stream.ticker, 'NVDA')
        self.assertEqual(stream.stream_type, 'tick_by_tick')
        self.assertEqual(stream.status, 'active')
        self.assertEqual(stream.req_id, 12345)
        self.assertIsInstance(stream.start_time, datetime)
    
    def test_stream_equality(self):
        """Test Stream equality"""
        stream1 = Stream('NVDA', 'tick_by_tick', req_id=123)
        stream2 = Stream('NVDA', 'tick_by_tick', req_id=123)
        stream3 = Stream('AAPL', 'tick_by_tick', req_id=123)
        
        self.assertEqual(stream1, stream2)
        self.assertNotEqual(stream1, stream3)


class TestStreamManagerBasic(unittest.TestCase):
    """Test basic StreamManager functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.manager = StreamManager(max_concurrent=15)
    
    def test_manager_initialization(self):
        """Test StreamManager initialization (Task 2.1)"""
        self.assertEqual(self.manager.max_concurrent, 15)
        self.assertEqual(self.manager.get_concurrent_count(), 0)
        self.assertEqual(len(self.manager), 0)
    
    def test_add_stream(self):
        """Test adding a stream (Task 2.2)"""
        stream = self.manager.add_stream('NVDA', 'tick_by_tick', req_id=123)
        
        self.assertIsNotNone(stream)
        self.assertEqual(stream.ticker, 'NVDA')
        self.assertEqual(stream.stream_type, 'tick_by_tick')
        self.assertEqual(self.manager.get_concurrent_count(), 1)
    
    def test_add_duplicate_stream_raises_error(self):
        """Test that adding duplicate stream raises ValueError"""
        self.manager.add_stream('NVDA', 'tick_by_tick')
        
        with self.assertRaises(ValueError):
            self.manager.add_stream('NVDA', 'tick_by_tick')
    
    def test_remove_stream(self):
        """Test removing a stream (Task 2.4)"""
        self.manager.add_stream('NVDA', 'tick_by_tick')
        self.assertEqual(self.manager.get_concurrent_count(), 1)
        
        result = self.manager.remove_stream('NVDA')
        
        self.assertTrue(result)
        self.assertEqual(self.manager.get_concurrent_count(), 0)
    
    def test_remove_nonexistent_stream(self):
        """Test removing non-existent stream"""
        result = self.manager.remove_stream('NVDA')
        self.assertFalse(result)
    
    def test_get_stream(self):
        """Test getting a specific stream"""
        self.manager.add_stream('NVDA', 'tick_by_tick', req_id=123)
        
        stream = self.manager.get_stream('NVDA')
        
        self.assertIsNotNone(stream)
        self.assertEqual(stream.ticker, 'NVDA')
        self.assertEqual(stream.req_id, 123)
    
    def test_has_stream(self):
        """Test checking if stream exists"""
        self.assertFalse(self.manager.has_stream('NVDA'))
        
        self.manager.add_stream('NVDA', 'tick_by_tick')
        
        self.assertTrue(self.manager.has_stream('NVDA'))


class TestStreamManagerCapacity(unittest.TestCase):
    """Test StreamManager capacity limits (Task 2.2)"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.manager = StreamManager(max_concurrent=5)  # Use smaller limit for testing
    
    def test_max_concurrent_limit(self):
        """Test that manager enforces max concurrent limit"""
        # Add streams up to capacity
        for i in range(5):
            stream = self.manager.add_stream(f'TICKER{i}', 'tick_by_tick')
            self.assertIsNotNone(stream)
        
        self.assertEqual(self.manager.get_concurrent_count(), 5)
        
        # Try to add one more (should fail)
        stream = self.manager.add_stream('TICKER6', 'tick_by_tick')
        self.assertIsNone(stream)
        self.assertEqual(self.manager.get_concurrent_count(), 5)
    
    def test_capacity_freed_after_removal(self):
        """Test that capacity is freed after removing streams"""
        # Fill to capacity
        for i in range(5):
            self.manager.add_stream(f'TICKER{i}', 'tick_by_tick')
        
        # Remove one
        self.manager.remove_stream('TICKER0')
        self.assertEqual(self.manager.get_concurrent_count(), 4)
        
        # Should be able to add another
        stream = self.manager.add_stream('TICKER5', 'tick_by_tick')
        self.assertIsNotNone(stream)
        self.assertEqual(self.manager.get_concurrent_count(), 5)


class TestStreamManagerWaiting(unittest.TestCase):
    """Test StreamManager wait_for_slot functionality (Task 2.3)"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.manager = StreamManager(max_concurrent=2)
    
    def test_wait_for_slot_immediate(self):
        """Test wait_for_slot returns immediately when slot available"""
        start_time = time.time()
        result = self.manager.wait_for_slot(timeout=5)
        elapsed = time.time() - start_time
        
        self.assertTrue(result)
        self.assertLess(elapsed, 0.5)  # Should be immediate
    
    def test_wait_for_slot_timeout(self):
        """Test wait_for_slot times out when no slot available"""
        # Fill to capacity
        self.manager.add_stream('TICKER1', 'tick_by_tick')
        self.manager.add_stream('TICKER2', 'tick_by_tick')
        
        start_time = time.time()
        result = self.manager.wait_for_slot(timeout=1)
        elapsed = time.time() - start_time
        
        self.assertFalse(result)
        self.assertGreaterEqual(elapsed, 1.0)
        self.assertLess(elapsed, 1.5)


class TestStreamManagerHealthMonitoring(unittest.TestCase):
    """Test StreamManager health monitoring (Task 2.5)"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.manager = StreamManager(max_concurrent=10)
    
    def test_get_health_status(self):
        """Test get_health_status method"""
        # Add some streams
        self.manager.add_stream('NVDA', 'tick_by_tick', req_id=123)
        self.manager.add_stream('AAPL', 'tick_by_tick', req_id=124)
        
        health = self.manager.get_health_status()
        
        self.assertEqual(health['active_count'], 2)
        self.assertEqual(health['capacity'], 10)
        self.assertEqual(health['utilization'], 20.0)
        self.assertEqual(len(health['streams']), 2)
        self.assertIn('timestamp', health)
    
    def test_get_active_streams(self):
        """Test get_active_streams method"""
        self.manager.add_stream('NVDA', 'tick_by_tick')
        self.manager.add_stream('AAPL', 'market_data')
        
        streams = self.manager.get_active_streams()
        
        self.assertEqual(len(streams), 2)
        tickers = [s.ticker for s in streams]
        self.assertIn('NVDA', tickers)
        self.assertIn('AAPL', tickers)


class TestStreamManagerCleanup(unittest.TestCase):
    """Test StreamManager cleanup functionality (Task 2.4)"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.manager = StreamManager(max_concurrent=10)
    
    def test_clear_all(self):
        """Test clearing all streams"""
        # Add multiple streams
        for i in range(5):
            self.manager.add_stream(f'TICKER{i}', 'tick_by_tick')
        
        self.assertEqual(self.manager.get_concurrent_count(), 5)
        
        # Clear all
        count = self.manager.clear_all()
        
        self.assertEqual(count, 5)
        self.assertEqual(self.manager.get_concurrent_count(), 0)
    
    def test_cleanup_stale_streams(self):
        """Test cleanup of stale streams"""
        # Add streams with different ages
        stream1 = self.manager.add_stream('TICKER1', 'tick_by_tick')
        stream2 = self.manager.add_stream('TICKER2', 'tick_by_tick')
        
        # Make stream1 appear old
        stream1.start_time = datetime.now() - timedelta(seconds=400)
        
        # Cleanup streams older than 300 seconds
        removed = self.manager.cleanup_stale_streams(max_age_seconds=300)
        
        self.assertEqual(removed, 1)
        self.assertEqual(self.manager.get_concurrent_count(), 1)
        self.assertFalse(self.manager.has_stream('TICKER1'))
        self.assertTrue(self.manager.has_stream('TICKER2'))


class TestStreamManagerThreadSafety(unittest.TestCase):
    """Test StreamManager thread safety"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.manager = StreamManager(max_concurrent=10)
    
    def test_concurrent_operations(self):
        """Test that operations are thread-safe"""
        import threading
        
        errors = []
        
        def add_streams():
            try:
                for i in range(5):
                    self.manager.add_stream(f'THREAD1_TICKER{i}', 'tick_by_tick')
                    time.sleep(0.01)
            except Exception as e:
                errors.append(e)
        
        def remove_streams():
            try:
                time.sleep(0.05)  # Let some streams be added first
                for i in range(3):
                    self.manager.remove_stream(f'THREAD1_TICKER{i}')
                    time.sleep(0.01)
            except Exception as e:
                errors.append(e)
        
        # Run operations in parallel
        thread1 = threading.Thread(target=add_streams)
        thread2 = threading.Thread(target=remove_streams)
        
        thread1.start()
        thread2.start()
        
        thread1.join()
        thread2.join()
        
        # Should not have any errors
        self.assertEqual(len(errors), 0)
        
        # Final count should be 2 (5 added - 3 removed)
        self.assertEqual(self.manager.get_concurrent_count(), 2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
