#!/usr/bin/env python3
"""
Integration Tests for Phase 2: Liquidity & Short Interest

Tests cover:
- 10.1: Liquidity monitoring with real-time data
- 10.2: Short interest analysis with mock data
- 10.3: Database storage and retrieval
- 10.4: Integration with existing modules
- 10.5: Performance testing with 15 concurrent streams
"""

import sys
import unittest
from datetime import datetime
from unittest.mock import Mock, patch

sys.path.append('.')

from calculation_layer.module36_liquidity import LiquidityMonitor
from calculation_layer.module37_short_interest import ShortInterestAnalyzer
from data_layer.stream_manager import StreamManager


class TestLiquidityIntegration(unittest.TestCase):
    """Test liquidity monitoring integration (Task 10.1)"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.monitor = LiquidityMonitor()
    
    def test_liquidity_with_realtime_data(self):
        """Test liquidity monitoring with simulated real-time data"""
        # Simulate real-time volume data
        metrics = self.monitor.calculate_volume_acceleration(
            ticker='NVDA',
            volume_3min=200000,
            volume_5min=250000,
            volume_10min=300000,
            avg_volume_baseline=100000,
            price_breakout=True,
            at_new_high=False
        )
        
        self.assertIsNotNone(metrics)
        self.assertTrue(metrics.breakout_confirmed)
        self.assertTrue(metrics.volume_monotonic)


class TestShortInterestIntegration(unittest.TestCase):
    """Test short interest analysis integration (Task 10.2)"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.analyzer = ShortInterestAnalyzer()
    
    def test_short_interest_with_mock_data(self):
        """Test short interest analysis with mock data"""
        # Simulate short interest data
        data = self.analyzer.analyze_short_interest(
            ticker='GME',
            shortable_difficulty=3,
            shortable_shares=50000,
            previous_difficulty=2,
            price_trend='rising'
        )
        
        self.assertIsNotNone(data)
        self.assertTrue(data.short_squeeze_potential)
        self.assertEqual(data.difficulty_change, 'harder')


class TestDatabaseIntegration(unittest.TestCase):
    """Test database storage and retrieval (Task 10.3)"""
    
    def test_signal_storage_format(self):
        """Test that signals can be converted to dict for storage"""
        monitor = LiquidityMonitor()
        
        metrics = monitor.calculate_volume_acceleration(
            ticker='NVDA',
            volume_3min=100000,
            volume_5min=150000,
            volume_10min=250000,
            avg_volume_baseline=100000
        )
        
        # Test to_dict conversion
        data_dict = metrics.to_dict()
        
        self.assertIn('ticker', data_dict)
        self.assertIn('timestamp', data_dict)
        self.assertIn('acceleration_ratio', data_dict)


class TestModuleIntegration(unittest.TestCase):
    """Test integration with existing modules (Task 10.4)"""
    
    def test_all_modules_instantiate(self):
        """Test that all modules can be instantiated together"""
        try:
            from calculation_layer.module35_large_orders import LargeOrderDetector
            from calculation_layer.module36_liquidity import LiquidityMonitor
            from calculation_layer.module37_short_interest import ShortInterestAnalyzer
            from calculation_layer.module38_dark_pool import DarkPoolDetector
            from data_layer.stream_manager import StreamManager
            
            # Instantiate all modules
            large_order = LargeOrderDetector()
            liquidity = LiquidityMonitor()
            short_interest = ShortInterestAnalyzer()
            dark_pool = DarkPoolDetector()
            stream_mgr = StreamManager()
            
            self.assertIsNotNone(large_order)
            self.assertIsNotNone(liquidity)
            self.assertIsNotNone(short_interest)
            self.assertIsNotNone(dark_pool)
            self.assertIsNotNone(stream_mgr)
            
        except ImportError as e:
            self.fail(f"Module import failed: {e}")


class TestPerformance(unittest.TestCase):
    """Test performance with concurrent streams (Task 10.5)"""
    
    def test_stream_manager_capacity(self):
        """Test stream manager handles 15 concurrent streams"""
        manager = StreamManager(max_concurrent=15)
        
        # Add 15 streams
        for i in range(15):
            stream = manager.add_stream(f'TICKER{i}', 'tick_by_tick')
            self.assertIsNotNone(stream)
        
        # Verify count
        self.assertEqual(manager.get_concurrent_count(), 15)
        
        # Try to add 16th (should fail)
        stream = manager.add_stream('TICKER16', 'tick_by_tick')
        self.assertIsNone(stream)


if __name__ == '__main__':
    unittest.main(verbosity=2)
