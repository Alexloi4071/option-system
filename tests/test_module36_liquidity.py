#!/usr/bin/env python3
"""
Unit tests for Module 36: Liquidity Monitor (Task 6)

Tests cover:
- 6.2: LiquidityMetrics data class
- 6.3: calculate_volume_acceleration() function
- 6.4: Breakout confirmation detection
- 6.5: Exhaustion signal detection
- 6.6: Volume monotonicity validation
"""

import sys
import unittest
from datetime import datetime

sys.path.append('.')

from calculation_layer.module36_liquidity import (
    LiquidityMonitor,
    LiquidityMetrics,
    BREAKOUT_ACCELERATION_THRESHOLD,
    EXHAUSTION_ACCELERATION_THRESHOLD
)


class TestLiquidityMetrics(unittest.TestCase):
    """Test LiquidityMetrics dataclass (Task 6.2)"""
    
    def test_liquidity_metrics_creation(self):
        """Test creating LiquidityMetrics object"""
        metrics = LiquidityMetrics(
            ticker='NVDA',
            timestamp=datetime.now(),
            volume_3min=100000,
            volume_5min=150000,
            volume_10min=250000,
            acceleration_ratio=1.33,
            breakout_confirmed=True,
            exhaustion_signal=False,
            avg_volume_baseline=100000,
            volume_monotonic=True
        )
        
        self.assertEqual(metrics.ticker, 'NVDA')
        self.assertEqual(metrics.volume_3min, 100000)
        self.assertEqual(metrics.volume_5min, 150000)
        self.assertEqual(metrics.volume_10min, 250000)
        self.assertTrue(metrics.breakout_confirmed)
        self.assertFalse(metrics.exhaustion_signal)
    
    def test_to_dict(self):
        """Test to_dict method"""
        metrics = LiquidityMetrics(
            ticker='NVDA',
            timestamp=datetime(2026, 3, 6, 10, 0, 0),
            volume_3min=100000,
            volume_5min=150000,
            volume_10min=250000,
            acceleration_ratio=1.33,
            breakout_confirmed=True,
            exhaustion_signal=False,
            avg_volume_baseline=100000,
            volume_monotonic=True
        )
        
        result = metrics.to_dict()
        
        self.assertEqual(result['ticker'], 'NVDA')
        self.assertEqual(result['volume_3min'], 100000)
        self.assertEqual(result['acceleration_ratio'], 1.33)
        self.assertIn('timestamp', result)
    
    def test_is_significant(self):
        """Test is_significant method"""
        # Significant due to breakout
        metrics1 = LiquidityMetrics(
            ticker='NVDA', timestamp=datetime.now(),
            volume_3min=100000, volume_5min=150000, volume_10min=250000,
            acceleration_ratio=2.5, breakout_confirmed=True,
            exhaustion_signal=False, avg_volume_baseline=100000,
            volume_monotonic=True
        )
        self.assertTrue(metrics1.is_significant())
        
        # Significant due to exhaustion
        metrics2 = LiquidityMetrics(
            ticker='NVDA', timestamp=datetime.now(),
            volume_3min=100000, volume_5min=150000, volume_10min=250000,
            acceleration_ratio=0.3, breakout_confirmed=False,
            exhaustion_signal=True, avg_volume_baseline=100000,
            volume_monotonic=True
        )
        self.assertTrue(metrics2.is_significant())
        
        # Not significant
        metrics3 = LiquidityMetrics(
            ticker='NVDA', timestamp=datetime.now(),
            volume_3min=100000, volume_5min=150000, volume_10min=250000,
            acceleration_ratio=1.0, breakout_confirmed=False,
            exhaustion_signal=False, avg_volume_baseline=100000,
            volume_monotonic=True
        )
        self.assertFalse(metrics3.is_significant())


class TestLiquidityMonitor(unittest.TestCase):
    """Test LiquidityMonitor class (Task 6.3)"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.monitor = LiquidityMonitor()
    
    def test_monitor_initialization(self):
        """Test LiquidityMonitor initialization"""
        self.assertIsNotNone(self.monitor)
    
    def test_calculate_volume_acceleration_basic(self):
        """Test basic volume acceleration calculation"""
        metrics = self.monitor.calculate_volume_acceleration(
            ticker='NVDA',
            volume_3min=100000,
            volume_5min=150000,
            volume_10min=250000,
            avg_volume_baseline=100000
        )
        
        self.assertEqual(metrics.ticker, 'NVDA')
        self.assertEqual(metrics.volume_3min, 100000)
        self.assertEqual(metrics.volume_5min, 150000)
        self.assertEqual(metrics.volume_10min, 250000)
        self.assertGreater(metrics.acceleration_ratio, 0)


class TestAccelerationRatio(unittest.TestCase):
    """Test acceleration ratio calculation (Task 6.3)"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.monitor = LiquidityMonitor()
    
    def test_calculate_acceleration_ratio_accelerating(self):
        """Test acceleration ratio when volume is accelerating"""
        # 3-min rate: 100000/3 = 33333 per minute
        # 10-min rate: 250000/10 = 25000 per minute
        # Ratio: 33333/25000 = 1.33
        ratio = self.monitor.calculate_acceleration_ratio(
            volume_3min=100000,
            volume_10min=250000
        )
        self.assertAlmostEqual(ratio, 1.33, places=2)
    
    def test_calculate_acceleration_ratio_decelerating(self):
        """Test acceleration ratio when volume is decelerating"""
        # 3-min rate: 50000/3 = 16667 per minute
        # 10-min rate: 250000/10 = 25000 per minute
        # Ratio: 16667/25000 = 0.67
        ratio = self.monitor.calculate_acceleration_ratio(
            volume_3min=50000,
            volume_10min=250000
        )
        self.assertAlmostEqual(ratio, 0.67, places=2)
    
    def test_calculate_acceleration_ratio_steady(self):
        """Test acceleration ratio when volume is steady"""
        # 3-min rate: 75000/3 = 25000 per minute
        # 10-min rate: 250000/10 = 25000 per minute
        # Ratio: 25000/25000 = 1.0
        ratio = self.monitor.calculate_acceleration_ratio(
            volume_3min=75000,
            volume_10min=250000
        )
        self.assertAlmostEqual(ratio, 1.0, places=2)
    
    def test_calculate_acceleration_ratio_zero_volume(self):
        """Test acceleration ratio with zero volume"""
        ratio = self.monitor.calculate_acceleration_ratio(
            volume_3min=0,
            volume_10min=0
        )
        self.assertEqual(ratio, 0.0)


class TestVolumeMonotonicity(unittest.TestCase):
    """Test volume monotonicity validation (Task 6.6)"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.monitor = LiquidityMonitor()
    
    def test_validate_volume_monotonicity_valid(self):
        """Test volume monotonicity with valid volumes"""
        # 3min <= 5min <= 10min
        is_monotonic = self.monitor.validate_volume_monotonicity(
            volume_3min=100000,
            volume_5min=150000,
            volume_10min=250000
        )
        self.assertTrue(is_monotonic)
    
    def test_validate_volume_monotonicity_equal(self):
        """Test volume monotonicity with equal volumes"""
        # All equal is valid
        is_monotonic = self.monitor.validate_volume_monotonicity(
            volume_3min=100000,
            volume_5min=100000,
            volume_10min=100000
        )
        self.assertTrue(is_monotonic)
    
    def test_validate_volume_monotonicity_invalid(self):
        """Test volume monotonicity with invalid volumes"""
        # 3min > 5min (violation)
        is_monotonic = self.monitor.validate_volume_monotonicity(
            volume_3min=200000,
            volume_5min=150000,
            volume_10min=250000
        )
        self.assertFalse(is_monotonic)
        
        # 5min > 10min (violation)
        is_monotonic = self.monitor.validate_volume_monotonicity(
            volume_3min=100000,
            volume_5min=300000,
            volume_10min=250000
        )
        self.assertFalse(is_monotonic)


class TestBreakoutConfirmation(unittest.TestCase):
    """Test breakout confirmation detection (Task 6.4)"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.monitor = LiquidityMonitor()
    
    def test_detect_breakout_confirmation_true(self):
        """Test breakout confirmation when all conditions met"""
        # acceleration_ratio > 2.0, price_breakout = True, volume spike
        confirmed = self.monitor.detect_breakout_confirmation(
            acceleration_ratio=2.5,
            price_breakout=True,
            volume_10min=200000,
            avg_volume_baseline=100000
        )
        self.assertTrue(confirmed)
    
    def test_detect_breakout_confirmation_no_acceleration(self):
        """Test breakout confirmation without acceleration"""
        # acceleration_ratio < 2.0
        confirmed = self.monitor.detect_breakout_confirmation(
            acceleration_ratio=1.5,
            price_breakout=True,
            volume_10min=200000,
            avg_volume_baseline=100000
        )
        self.assertFalse(confirmed)
    
    def test_detect_breakout_confirmation_no_price_breakout(self):
        """Test breakout confirmation without price breakout"""
        # price_breakout = False
        confirmed = self.monitor.detect_breakout_confirmation(
            acceleration_ratio=2.5,
            price_breakout=False,
            volume_10min=200000,
            avg_volume_baseline=100000
        )
        self.assertFalse(confirmed)
    
    def test_detect_breakout_confirmation_no_volume_spike(self):
        """Test breakout confirmation without volume spike"""
        # volume_10min < avg_volume_baseline * 1.5
        confirmed = self.monitor.detect_breakout_confirmation(
            acceleration_ratio=2.5,
            price_breakout=True,
            volume_10min=120000,
            avg_volume_baseline=100000
        )
        self.assertFalse(confirmed)


class TestExhaustionSignal(unittest.TestCase):
    """Test exhaustion signal detection (Task 6.5)"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.monitor = LiquidityMonitor()
    
    def test_detect_exhaustion_signal_true(self):
        """Test exhaustion signal when conditions met"""
        # at_new_high = True, acceleration_ratio < 0.5
        exhaustion = self.monitor.detect_exhaustion_signal(
            acceleration_ratio=0.3,
            at_new_high=True
        )
        self.assertTrue(exhaustion)
    
    def test_detect_exhaustion_signal_no_new_high(self):
        """Test exhaustion signal without new high"""
        # at_new_high = False
        exhaustion = self.monitor.detect_exhaustion_signal(
            acceleration_ratio=0.3,
            at_new_high=False
        )
        self.assertFalse(exhaustion)
    
    def test_detect_exhaustion_signal_no_deceleration(self):
        """Test exhaustion signal without deceleration"""
        # acceleration_ratio >= 0.5
        exhaustion = self.monitor.detect_exhaustion_signal(
            acceleration_ratio=0.8,
            at_new_high=True
        )
        self.assertFalse(exhaustion)


class TestLiquidityIntegration(unittest.TestCase):
    """Integration tests for liquidity monitoring"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.monitor = LiquidityMonitor()
    
    def test_complete_workflow_breakout(self):
        """Test complete workflow with breakout confirmation"""
        metrics = self.monitor.calculate_volume_acceleration(
            ticker='NVDA',
            volume_3min=150000,  # High recent volume
            volume_5min=200000,
            volume_10min=300000,
            avg_volume_baseline=100000,
            price_breakout=True,
            at_new_high=False
        )
        
        # Check acceleration ratio
        # 3-min rate: 150000/3 = 50000 per minute
        # 10-min rate: 300000/10 = 30000 per minute
        # Ratio: 50000/30000 = 1.67 (< 2.0, so no breakout)
        
        # Should NOT detect breakout (ratio < 2.0)
        self.assertFalse(metrics.breakout_confirmed)
        self.assertFalse(metrics.exhaustion_signal)
        self.assertTrue(metrics.volume_monotonic)
        self.assertGreater(metrics.acceleration_ratio, 1.0)
    
    def test_complete_workflow_strong_breakout(self):
        """Test complete workflow with strong breakout confirmation"""
        metrics = self.monitor.calculate_volume_acceleration(
            ticker='NVDA',
            volume_3min=200000,  # Very high recent volume
            volume_5min=250000,
            volume_10min=300000,
            avg_volume_baseline=100000,
            price_breakout=True,
            at_new_high=False
        )
        
        # Check acceleration ratio
        # 3-min rate: 200000/3 = 66667 per minute
        # 10-min rate: 300000/10 = 30000 per minute
        # Ratio: 66667/30000 = 2.22 (> 2.0, breakout!)
        
        # Should detect breakout
        self.assertTrue(metrics.breakout_confirmed)
        self.assertFalse(metrics.exhaustion_signal)
        self.assertTrue(metrics.volume_monotonic)
        self.assertGreater(metrics.acceleration_ratio, BREAKOUT_ACCELERATION_THRESHOLD)
    
    def test_complete_workflow_exhaustion(self):
        """Test complete workflow with exhaustion signal"""
        metrics = self.monitor.calculate_volume_acceleration(
            ticker='NVDA',
            volume_3min=30000,  # Low recent volume
            volume_5min=75000,
            volume_10min=250000,
            avg_volume_baseline=100000,
            price_breakout=False,
            at_new_high=True
        )
        
        # Should detect exhaustion
        self.assertFalse(metrics.breakout_confirmed)
        self.assertTrue(metrics.exhaustion_signal)
        self.assertTrue(metrics.volume_monotonic)
        self.assertLess(metrics.acceleration_ratio, EXHAUSTION_ACCELERATION_THRESHOLD)
    
    def test_complete_workflow_normal(self):
        """Test complete workflow with normal conditions"""
        metrics = self.monitor.calculate_volume_acceleration(
            ticker='NVDA',
            volume_3min=75000,  # Steady volume
            volume_5min=125000,
            volume_10min=250000,
            avg_volume_baseline=100000,
            price_breakout=False,
            at_new_high=False
        )
        
        # Should not detect any signals
        self.assertFalse(metrics.breakout_confirmed)
        self.assertFalse(metrics.exhaustion_signal)
        self.assertTrue(metrics.volume_monotonic)


class TestLiquidityValidation(unittest.TestCase):
    """Test input validation and error handling"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.monitor = LiquidityMonitor()
    
    def test_invalid_ticker(self):
        """Test that empty ticker raises ValueError"""
        with self.assertRaises(ValueError):
            self.monitor.calculate_volume_acceleration(
                ticker='',
                volume_3min=100000,
                volume_5min=150000,
                volume_10min=250000,
                avg_volume_baseline=100000
            )
    
    def test_invalid_volumes(self):
        """Test that negative volumes raise ValueError"""
        with self.assertRaises(ValueError):
            self.monitor.calculate_volume_acceleration(
                ticker='NVDA',
                volume_3min=-100,
                volume_5min=150000,
                volume_10min=250000,
                avg_volume_baseline=100000
            )
    
    def test_invalid_baseline(self):
        """Test that invalid baseline raises ValueError"""
        with self.assertRaises(ValueError):
            self.monitor.calculate_volume_acceleration(
                ticker='NVDA',
                volume_3min=100000,
                volume_5min=150000,
                volume_10min=250000,
                avg_volume_baseline=0
            )


if __name__ == '__main__':
    unittest.main(verbosity=2)
