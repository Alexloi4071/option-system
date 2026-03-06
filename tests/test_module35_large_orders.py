#!/usr/bin/env python3
"""
Unit tests for Module 35: Large Order Detector (Task 4)

Tests cover:
- 4.2: LargeOrderSignal data class
- 4.3: detect_large_orders() function
- 4.4: Consecutive order tracking (5-minute window)
- 4.5: VWAP deviation calculation
- 4.6: Institutional footprint identification (>$250K)
"""

import sys
import unittest
from datetime import datetime, timedelta

sys.path.append('.')

from calculation_layer.module35_large_orders import (
    LargeOrderDetector,
    LargeOrderSignal,
    BLOCK_THRESHOLD,
    VALUE_THRESHOLD
)
from data_layer.ibkr_client import TickByTickData


class TestLargeOrderSignal(unittest.TestCase):
    """Test LargeOrderSignal dataclass (Task 4.2)"""
    
    def test_large_order_signal_creation(self):
        """Test creating LargeOrderSignal object"""
        signal = LargeOrderSignal(
            ticker='NVDA',
            timestamp=datetime.now(),
            order_size=15000,
            order_value=300000.0,
            price=20.0,
            consecutive_count=3,
            institutional_footprint=True,
            vwap_deviation=0.75
        )
        
        self.assertEqual(signal.ticker, 'NVDA')
        self.assertEqual(signal.order_size, 15000)
        self.assertEqual(signal.order_value, 300000.0)
        self.assertTrue(signal.institutional_footprint)
    
    def test_to_dict(self):
        """Test to_dict method"""
        signal = LargeOrderSignal(
            ticker='NVDA',
            timestamp=datetime(2026, 3, 6, 10, 0, 0),
            order_size=15000,
            order_value=300000.0,
            price=20.0,
            consecutive_count=3,
            institutional_footprint=True,
            vwap_deviation=0.75
        )
        
        result = signal.to_dict()
        
        self.assertEqual(result['ticker'], 'NVDA')
        self.assertEqual(result['order_size'], 15000)
        self.assertEqual(result['order_value'], 300000.0)
        self.assertIn('timestamp', result)
    
    def test_is_significant(self):
        """Test is_significant method"""
        # Significant due to institutional footprint
        signal1 = LargeOrderSignal(
            ticker='NVDA', timestamp=datetime.now(),
            order_size=15000, order_value=300000.0, price=20.0,
            consecutive_count=1, institutional_footprint=True, vwap_deviation=0.2
        )
        self.assertTrue(signal1.is_significant())
        
        # Significant due to consecutive count
        signal2 = LargeOrderSignal(
            ticker='NVDA', timestamp=datetime.now(),
            order_size=11000, order_value=220000.0, price=20.0,
            consecutive_count=3, institutional_footprint=False, vwap_deviation=0.2
        )
        self.assertTrue(signal2.is_significant())
        
        # Significant due to VWAP deviation
        signal3 = LargeOrderSignal(
            ticker='NVDA', timestamp=datetime.now(),
            order_size=11000, order_value=220000.0, price=20.0,
            consecutive_count=1, institutional_footprint=False, vwap_deviation=0.8
        )
        self.assertTrue(signal3.is_significant())
        
        # Not significant
        signal4 = LargeOrderSignal(
            ticker='NVDA', timestamp=datetime.now(),
            order_size=11000, order_value=220000.0, price=20.0,
            consecutive_count=1, institutional_footprint=False, vwap_deviation=0.2
        )
        self.assertFalse(signal4.is_significant())


class TestLargeOrderDetector(unittest.TestCase):
    """Test LargeOrderDetector class (Task 4.3)"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.detector = LargeOrderDetector()
    
    def test_detector_initialization(self):
        """Test LargeOrderDetector initialization"""
        self.assertEqual(self.detector.block_threshold, BLOCK_THRESHOLD)
        self.assertEqual(self.detector.value_threshold, VALUE_THRESHOLD)
        self.assertEqual(self.detector.consecutive_window, 300)
    
    def test_detect_large_orders_by_size(self):
        """Test detecting large orders by share size (>10K shares)"""
        # Create tick stream with large order
        ticks = [
            TickByTickData(
                ticker='NVDA',
                timestamp=datetime.now(),
                price=500.0,
                size=15000,  # >10K threshold
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
        self.assertEqual(signals[0].order_size, 15000)
        self.assertEqual(signals[0].order_value, 7500000.0)
    
    def test_detect_large_orders_by_value(self):
        """Test detecting large orders by dollar value (>$250K)"""
        # Create tick stream with high-value order
        ticks = [
            TickByTickData(
                ticker='NVDA',
                timestamp=datetime.now(),
                price=500.0,
                size=600,  # <10K shares but >$250K value
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
        self.assertEqual(signals[0].order_value, 300000.0)
        self.assertTrue(signals[0].institutional_footprint)
    
    def test_institutional_footprint(self):
        """Test institutional footprint identification (Task 4.6)"""
        # Institutional order (>$250K)
        ticks = [
            TickByTickData(
                ticker='NVDA',
                timestamp=datetime.now(),
                price=500.0,
                size=600,
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
        
        self.assertTrue(signals[0].institutional_footprint)
        
        # Non-institutional order (<$250K)
        ticks = [
            TickByTickData(
                ticker='NVDA',
                timestamp=datetime.now(),
                price=500.0,
                size=400,  # $200K
                exchange='NASDAQ',
                tick_type='AllLast',
                tick_tags={}
            )
        ]
        
        signals = self.detector.detect_large_orders(
            ticker='NVDA',
            tick_stream=ticks,
            vwap=500.0,
            block_threshold=100  # Lower threshold to catch this order
        )
        
        self.assertFalse(signals[0].institutional_footprint)


class TestVWAPDeviation(unittest.TestCase):
    """Test VWAP deviation calculation (Task 4.5)"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.detector = LargeOrderDetector()
    
    def test_calculate_vwap_deviation_positive(self):
        """Test VWAP deviation when price above VWAP"""
        deviation = self.detector.calculate_vwap_deviation(
            order_price=505.0,
            vwap=500.0
        )
        self.assertEqual(deviation, 1.0)  # 1% above VWAP
    
    def test_calculate_vwap_deviation_negative(self):
        """Test VWAP deviation when price below VWAP"""
        deviation = self.detector.calculate_vwap_deviation(
            order_price=495.0,
            vwap=500.0
        )
        self.assertEqual(deviation, -1.0)  # 1% below VWAP
    
    def test_calculate_vwap_deviation_zero(self):
        """Test VWAP deviation when price equals VWAP"""
        deviation = self.detector.calculate_vwap_deviation(
            order_price=500.0,
            vwap=500.0
        )
        self.assertEqual(deviation, 0.0)


class TestConsecutiveOrders(unittest.TestCase):
    """Test consecutive order tracking (Task 4.4)"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.detector = LargeOrderDetector(consecutive_window=300)
    
    def test_track_consecutive_orders(self):
        """Test tracking consecutive orders within 5-minute window"""
        base_time = datetime.now()
        
        # Add 3 orders within 5 minutes
        count1 = self.detector.track_consecutive_orders('NVDA', base_time)
        self.assertEqual(count1, 1)
        
        count2 = self.detector.track_consecutive_orders('NVDA', base_time + timedelta(seconds=60))
        self.assertEqual(count2, 2)
        
        count3 = self.detector.track_consecutive_orders('NVDA', base_time + timedelta(seconds=120))
        self.assertEqual(count3, 3)
    
    def test_consecutive_orders_window_expiry(self):
        """Test that orders outside window are removed"""
        base_time = datetime.now()
        
        # Add order at t=0
        self.detector.track_consecutive_orders('NVDA', base_time)
        
        # Add order at t=400s (outside 300s window)
        count = self.detector.track_consecutive_orders('NVDA', base_time + timedelta(seconds=400))
        
        # First order should be removed, count should be 1
        self.assertEqual(count, 1)
    
    def test_consecutive_orders_per_ticker(self):
        """Test that consecutive orders are tracked per ticker"""
        base_time = datetime.now()
        
        # Add orders for different tickers
        count_nvda = self.detector.track_consecutive_orders('NVDA', base_time)
        count_aapl = self.detector.track_consecutive_orders('AAPL', base_time)
        
        self.assertEqual(count_nvda, 1)
        self.assertEqual(count_aapl, 1)
        
        # Add another NVDA order
        count_nvda2 = self.detector.track_consecutive_orders('NVDA', base_time + timedelta(seconds=60))
        
        self.assertEqual(count_nvda2, 2)
        
        # AAPL should still be 1
        aapl_history = self.detector.get_recent_orders('AAPL')
        self.assertEqual(len(aapl_history), 1)


class TestLargeOrderIntegration(unittest.TestCase):
    """Integration tests for large order detection"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.detector = LargeOrderDetector()
    
    def test_complete_workflow(self):
        """Test complete large order detection workflow"""
        base_time = datetime.now()
        
        # Create tick stream with multiple large orders
        ticks = [
            TickByTickData(
                ticker='NVDA',
                timestamp=base_time,
                price=500.0,
                size=15000,  # Block trade
                exchange='NASDAQ',
                tick_type='AllLast',
                tick_tags={}
            ),
            TickByTickData(
                ticker='NVDA',
                timestamp=base_time + timedelta(seconds=60),
                price=501.0,
                size=12000,  # Another block trade
                exchange='NASDAQ',
                tick_type='AllLast',
                tick_tags={}
            ),
            TickByTickData(
                ticker='NVDA',
                timestamp=base_time + timedelta(seconds=120),
                price=502.0,
                size=600,  # Institutional value
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
        
        # Should detect all 3 orders
        self.assertEqual(len(signals), 3)
        
        # Check consecutive counts
        self.assertEqual(signals[0].consecutive_count, 1)
        self.assertEqual(signals[1].consecutive_count, 2)
        self.assertEqual(signals[2].consecutive_count, 3)
        
        # Check institutional footprints
        self.assertTrue(signals[0].institutional_footprint)  # $7.5M
        self.assertTrue(signals[1].institutional_footprint)  # $6.0M
        self.assertTrue(signals[2].institutional_footprint)  # $301K
    
    def test_filter_small_orders(self):
        """Test that small orders are not detected"""
        ticks = [
            TickByTickData(
                ticker='NVDA',
                timestamp=datetime.now(),
                price=500.0,
                size=100,  # Small order
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
        
        # Should not detect small orders
        self.assertEqual(len(signals), 0)
    
    def test_vwap_deviation_in_signals(self):
        """Test VWAP deviation is calculated correctly in signals"""
        ticks = [
            TickByTickData(
                ticker='NVDA',
                timestamp=datetime.now(),
                price=505.0,  # 1% above VWAP
                size=15000,
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
        self.assertEqual(signals[0].vwap_deviation, 1.0)


class TestLargeOrderValidation(unittest.TestCase):
    """Test input validation and error handling"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.detector = LargeOrderDetector()
    
    def test_invalid_ticker(self):
        """Test that empty ticker raises ValueError"""
        with self.assertRaises(ValueError):
            self.detector.detect_large_orders(
                ticker='',
                tick_stream=[],
                vwap=500.0
            )
    
    def test_invalid_vwap(self):
        """Test that invalid VWAP raises ValueError"""
        with self.assertRaises(ValueError):
            self.detector.detect_large_orders(
                ticker='NVDA',
                tick_stream=[],
                vwap=0.0
            )


if __name__ == '__main__':
    unittest.main(verbosity=2)
