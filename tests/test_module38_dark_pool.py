#!/usr/bin/env python3
"""
Unit tests for Module 38: Dark Pool Detector (Task 3)

Tests cover:
- 3.2: DarkPoolData data class
- 3.3: detect_dark_pool_activity() function
- 3.4: Historical average calculation
- 3.5: Buy/sell pressure inference using VWAP
- 3.6: Surge detection logic (>40% or 2x average)
"""

import sys
import unittest
from datetime import datetime

sys.path.append('.')

from calculation_layer.module38_dark_pool import (
    DarkPoolDetector,
    DarkPoolData,
    DARK_POOL_SURGE_THRESHOLD,
    DARK_POOL_SURGE_RATIO
)


class TestDarkPoolData(unittest.TestCase):
    """Test DarkPoolData dataclass (Task 3.2)"""
    
    def test_dark_pool_data_creation(self):
        """Test creating DarkPoolData object"""
        data = DarkPoolData(
            ticker='NVDA',
            timestamp=datetime.now(),
            dark_volume=400000,
            total_volume=1000000,
            dark_pool_pct=40.0,
            vwap=500.0,
            price=502.5,
            buy_sell_pressure='buy',
            surge_detected=True,
            surge_ratio=2.5
        )
        
        self.assertEqual(data.ticker, 'NVDA')
        self.assertEqual(data.dark_volume, 400000)
        self.assertEqual(data.total_volume, 1000000)
        self.assertEqual(data.dark_pool_pct, 40.0)
        self.assertEqual(data.buy_sell_pressure, 'buy')
        self.assertTrue(data.surge_detected)
    
    def test_to_dict(self):
        """Test to_dict method"""
        data = DarkPoolData(
            ticker='NVDA',
            timestamp=datetime(2026, 3, 6, 10, 0, 0),
            dark_volume=400000,
            total_volume=1000000,
            dark_pool_pct=40.0,
            vwap=500.0,
            price=502.5,
            buy_sell_pressure='buy',
            surge_detected=True,
            surge_ratio=2.5
        )
        
        result = data.to_dict()
        
        self.assertEqual(result['ticker'], 'NVDA')
        self.assertEqual(result['dark_volume'], 400000)
        self.assertEqual(result['dark_pool_pct'], 40.0)
        self.assertIn('timestamp', result)
    
    def test_is_significant(self):
        """Test is_significant method"""
        # Significant due to surge
        data1 = DarkPoolData(
            ticker='NVDA', timestamp=datetime.now(),
            dark_volume=400000, total_volume=1000000,
            dark_pool_pct=40.0, vwap=500.0, price=502.5,
            buy_sell_pressure='buy', surge_detected=True, surge_ratio=2.5
        )
        self.assertTrue(data1.is_significant())
        
        # Significant due to high percentage
        data2 = DarkPoolData(
            ticker='NVDA', timestamp=datetime.now(),
            dark_volume=350000, total_volume=1000000,
            dark_pool_pct=35.0, vwap=500.0, price=502.5,
            buy_sell_pressure='buy', surge_detected=False, surge_ratio=1.0
        )
        self.assertTrue(data2.is_significant())
        
        # Not significant
        data3 = DarkPoolData(
            ticker='NVDA', timestamp=datetime.now(),
            dark_volume=200000, total_volume=1000000,
            dark_pool_pct=20.0, vwap=500.0, price=502.5,
            buy_sell_pressure='neutral', surge_detected=False, surge_ratio=1.0
        )
        self.assertFalse(data3.is_significant())


class TestDarkPoolDetector(unittest.TestCase):
    """Test DarkPoolDetector class (Task 3.3)"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.detector = DarkPoolDetector(historical_window=20)
    
    def test_detector_initialization(self):
        """Test DarkPoolDetector initialization"""
        self.assertEqual(self.detector.historical_window, 20)
        self.assertEqual(len(self.detector._historical_data), 0)
    
    def test_detect_dark_pool_activity_basic(self):
        """Test basic dark pool detection (Task 3.3)"""
        result = self.detector.detect_dark_pool_activity(
            ticker='NVDA',
            rt_volume=1000000,
            rt_trade_volume=600000,
            vwap=500.0,
            current_price=502.5
        )
        
        self.assertEqual(result.ticker, 'NVDA')
        self.assertEqual(result.dark_volume, 400000)
        self.assertEqual(result.total_volume, 1000000)
        self.assertEqual(result.dark_pool_pct, 40.0)
        self.assertEqual(result.vwap, 500.0)
        self.assertEqual(result.price, 502.5)
    
    def test_dark_pool_percentage_calculation(self):
        """Test dark pool percentage calculation formula"""
        # 40% dark pool
        result = self.detector.detect_dark_pool_activity(
            ticker='TEST1',
            rt_volume=1000000,
            rt_trade_volume=600000,
            vwap=100.0,
            current_price=100.0
        )
        self.assertEqual(result.dark_pool_pct, 40.0)
        
        # 20% dark pool
        result = self.detector.detect_dark_pool_activity(
            ticker='TEST2',
            rt_volume=1000000,
            rt_trade_volume=800000,
            vwap=100.0,
            current_price=100.0
        )
        self.assertEqual(result.dark_pool_pct, 20.0)
        
        # 0% dark pool (all lit exchanges)
        result = self.detector.detect_dark_pool_activity(
            ticker='TEST3',
            rt_volume=1000000,
            rt_trade_volume=1000000,
            vwap=100.0,
            current_price=100.0
        )
        self.assertEqual(result.dark_pool_pct, 0.0)
    
    def test_dark_pool_percentage_bounds(self):
        """Test that dark_pool_pct is always in range [0, 100]"""
        # Edge case: rt_trade_volume > rt_volume (should be capped at 0%)
        result = self.detector.detect_dark_pool_activity(
            ticker='TEST',
            rt_volume=1000000,
            rt_trade_volume=1200000,  # Invalid: larger than total
            vwap=100.0,
            current_price=100.0
        )
        self.assertGreaterEqual(result.dark_pool_pct, 0.0)
        self.assertLessEqual(result.dark_pool_pct, 100.0)


class TestBuySellPressure(unittest.TestCase):
    """Test buy/sell pressure inference (Task 3.5)"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.detector = DarkPoolDetector()
    
    def test_buy_pressure(self):
        """Test buy pressure detection (price > vwap * 1.005)"""
        pressure = self.detector.infer_buy_sell_pressure(
            price=503.0,  # 0.6% above VWAP (clearly above threshold)
            vwap=500.0
        )
        self.assertEqual(pressure, 'buy')
    
    def test_sell_pressure(self):
        """Test sell pressure detection (price < vwap * 0.995)"""
        pressure = self.detector.infer_buy_sell_pressure(
            price=497.0,  # 0.6% below VWAP (clearly below threshold)
            vwap=500.0
        )
        self.assertEqual(pressure, 'sell')
    
    def test_neutral_pressure(self):
        """Test neutral pressure (price near VWAP)"""
        pressure = self.detector.infer_buy_sell_pressure(
            price=500.0,  # At VWAP
            vwap=500.0
        )
        self.assertEqual(pressure, 'neutral')
        
        pressure = self.detector.infer_buy_sell_pressure(
            price=501.0,  # 0.2% above VWAP (within neutral range)
            vwap=500.0
        )
        self.assertEqual(pressure, 'neutral')


class TestSurgeDetection(unittest.TestCase):
    """Test surge detection logic (Task 3.6)"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.detector = DarkPoolDetector()
    
    def test_surge_by_percentage(self):
        """Test surge detection by percentage (>40%)"""
        result = self.detector.detect_dark_pool_activity(
            ticker='NVDA',
            rt_volume=1000000,
            rt_trade_volume=500000,  # 50% dark pool
            vwap=500.0,
            current_price=500.0
        )
        
        self.assertTrue(result.surge_detected)
        self.assertEqual(result.dark_pool_pct, 50.0)
    
    def test_surge_by_historical_ratio(self):
        """Test surge detection by historical ratio (>2x average)"""
        # Build historical baseline (average ~100K)
        for i in range(10):
            self.detector.detect_dark_pool_activity(
                ticker='NVDA',
                rt_volume=1000000,
                rt_trade_volume=900000,  # 100K dark pool
                vwap=500.0,
                current_price=500.0
            )
        
        # Now send 2.5x average (250K dark pool, but only 25% percentage)
        result = self.detector.detect_dark_pool_activity(
            ticker='NVDA',
            rt_volume=1000000,
            rt_trade_volume=750000,  # 250K dark pool
            vwap=500.0,
            current_price=500.0
        )
        
        self.assertTrue(result.surge_detected)
        self.assertGreater(result.surge_ratio, DARK_POOL_SURGE_RATIO)
    
    def test_no_surge(self):
        """Test no surge detection when below thresholds"""
        result = self.detector.detect_dark_pool_activity(
            ticker='NVDA',
            rt_volume=1000000,
            rt_trade_volume=800000,  # 20% dark pool
            vwap=500.0,
            current_price=500.0
        )
        
        self.assertFalse(result.surge_detected)
        self.assertLess(result.dark_pool_pct, DARK_POOL_SURGE_THRESHOLD)


class TestHistoricalAverage(unittest.TestCase):
    """Test historical average calculation (Task 3.4)"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.detector = DarkPoolDetector(historical_window=5)
    
    def test_calculate_historical_average(self):
        """Test historical average calculation"""
        # Add some historical data
        for i in range(5):
            self.detector._update_historical_data('NVDA', 100000 + i * 10000)
        
        avg = self.detector.calculate_historical_average('NVDA')
        
        # Average of [100000, 110000, 120000, 130000, 140000] = 120000
        self.assertEqual(avg, 120000.0)
    
    def test_historical_average_no_data(self):
        """Test historical average with no data"""
        avg = self.detector.calculate_historical_average('UNKNOWN')
        self.assertEqual(avg, 0.0)
    
    def test_historical_window_limit(self):
        """Test that historical data respects window limit"""
        # Add more data than window size
        for i in range(10):
            self.detector._update_historical_data('NVDA', i * 10000)
        
        history = self.detector.get_historical_data('NVDA')
        
        # Should only keep last 5 entries
        self.assertEqual(len(history), 5)
        self.assertEqual(history, [50000, 60000, 70000, 80000, 90000])


class TestDarkPoolValidation(unittest.TestCase):
    """Test input validation and error handling"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.detector = DarkPoolDetector()
    
    def test_invalid_ticker(self):
        """Test that empty ticker raises ValueError"""
        with self.assertRaises(ValueError):
            self.detector.detect_dark_pool_activity(
                ticker='',
                rt_volume=1000000,
                rt_trade_volume=600000,
                vwap=500.0,
                current_price=500.0
            )
    
    def test_negative_volumes(self):
        """Test that negative volumes raise ValueError"""
        with self.assertRaises(ValueError):
            self.detector.detect_dark_pool_activity(
                ticker='NVDA',
                rt_volume=-1000000,
                rt_trade_volume=600000,
                vwap=500.0,
                current_price=500.0
            )
    
    def test_invalid_prices(self):
        """Test that invalid prices raise ValueError"""
        with self.assertRaises(ValueError):
            self.detector.detect_dark_pool_activity(
                ticker='NVDA',
                rt_volume=1000000,
                rt_trade_volume=600000,
                vwap=0.0,  # Invalid
                current_price=500.0
            )


class TestDarkPoolIntegration(unittest.TestCase):
    """Integration tests for dark pool detection"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.detector = DarkPoolDetector()
    
    def test_complete_workflow(self):
        """Test complete dark pool detection workflow"""
        # Scenario: NVDA with 45% dark pool activity, buying pressure
        result = self.detector.detect_dark_pool_activity(
            ticker='NVDA',
            rt_volume=1000000,
            rt_trade_volume=550000,
            vwap=500.0,
            current_price=503.0  # 0.6% above VWAP
        )
        
        # Verify calculations
        self.assertEqual(result.dark_volume, 450000)
        self.assertEqual(result.dark_pool_pct, 45.0)
        self.assertEqual(result.buy_sell_pressure, 'buy')
        self.assertTrue(result.surge_detected)  # >40% threshold
    
    def test_dark_pool_with_historical_context(self):
        """Test dark pool detection with historical baseline"""
        # Build baseline (average 100K dark pool)
        for i in range(10):
            self.detector.detect_dark_pool_activity(
                ticker='AAPL',
                rt_volume=1000000,
                rt_trade_volume=900000,
                vwap=150.0,
                current_price=150.0
            )
        
        # Test with 2.5x surge (250K dark pool, 25% percentage)
        result = self.detector.detect_dark_pool_activity(
            ticker='AAPL',
            rt_volume=1000000,
            rt_trade_volume=750000,
            vwap=150.0,
            current_price=149.0  # Selling pressure
        )
        
        self.assertEqual(result.dark_pool_pct, 25.0)
        self.assertEqual(result.buy_sell_pressure, 'sell')
        self.assertTrue(result.surge_detected)  # 2.5x > 2.0x threshold
        self.assertGreater(result.surge_ratio, 2.0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
