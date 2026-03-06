#!/usr/bin/env python3
"""
Property-Based Tests for Advanced Data Utilization

Tests cover:
- 15.1: Stream quota compliance
- 15.2: Dark pool percentage bounds
- 15.3: Volume monotonicity
- 15.4: Signal uniqueness
- 15.5: VWAP pressure consistency
"""

import sys
import unittest
from datetime import datetime

sys.path.append('.')

from data_layer.stream_manager import StreamManager
from calculation_layer.module38_dark_pool import DarkPoolDetector
from calculation_layer.module36_liquidity import LiquidityMonitor


class TestStreamQuotaProperty(unittest.TestCase):
    """Test stream quota compliance property (Task 15.1)"""
    
    def test_stream_quota_never_exceeded(self):
        """Property: Stream count never exceeds max_concurrent"""
        manager = StreamManager(max_concurrent=15)
        
        # Try to add 20 streams
        for i in range(20):
            manager.add_stream(f'TICKER{i}', 'tick_by_tick')
            
            # Property: count <= max_concurrent
            self.assertLessEqual(
                manager.get_concurrent_count(),
                15,
                f"Stream count exceeded limit at iteration {i}"
            )


class TestDarkPoolPercentageProperty(unittest.TestCase):
    """Test dark pool percentage bounds property (Task 15.2)"""
    
    def test_dark_pool_percentage_bounds(self):
        """Property: 0 <= dark_pool_pct <= 100"""
        detector = DarkPoolDetector()
        
        # Test various volume combinations
        test_cases = [
            (1000000, 600000),  # 40% dark pool
            (1000000, 0),       # 100% dark pool
            (1000000, 1000000), # 0% dark pool
            (500000, 250000),   # 50% dark pool
        ]
        
        for rt_volume, rt_trade_volume in test_cases:
            data = detector.detect_dark_pool_activity(
                ticker='TEST',
                rt_volume=rt_volume,
                rt_trade_volume=rt_trade_volume,
                vwap=100.0,
                current_price=100.0
            )
            
            # Property: 0 <= dark_pool_pct <= 100
            self.assertGreaterEqual(data.dark_pool_pct, 0.0)
            self.assertLessEqual(data.dark_pool_pct, 100.0)


class TestVolumeMonotonicityProperty(unittest.TestCase):
    """Test volume monotonicity property (Task 15.3)"""
    
    def test_volume_monotonicity_validation(self):
        """Property: volume_3min <= volume_5min <= volume_10min"""
        monitor = LiquidityMonitor()
        
        # Valid monotonic volumes
        valid_cases = [
            (100000, 150000, 250000),
            (100000, 100000, 100000),
            (50000, 100000, 200000),
        ]
        
        for v3, v5, v10 in valid_cases:
            is_monotonic = monitor.validate_volume_monotonicity(v3, v5, v10)
            self.assertTrue(is_monotonic, f"Failed for {v3}, {v5}, {v10}")
        
        # Invalid non-monotonic volumes
        invalid_cases = [
            (200000, 150000, 250000),  # v3 > v5
            (100000, 300000, 250000),  # v5 > v10
        ]
        
        for v3, v5, v10 in invalid_cases:
            is_monotonic = monitor.validate_volume_monotonicity(v3, v5, v10)
            self.assertFalse(is_monotonic, f"Should fail for {v3}, {v5}, {v10}")


class TestSignalUniquenessProperty(unittest.TestCase):
    """Test signal uniqueness property (Task 15.4)"""
    
    def test_signal_timestamps_unique(self):
        """Property: Signals have unique timestamps per ticker"""
        from calculation_layer.module35_large_orders import LargeOrderDetector
        from data_layer.ibkr_client import TickByTickData
        
        detector = LargeOrderDetector()
        
        # Create ticks with different timestamps
        ticks = [
            TickByTickData(
                ticker='NVDA',
                timestamp=datetime(2026, 3, 6, 10, 0, i),
                price=500.0,
                size=15000,
                exchange='NASDAQ',
                tick_type='AllLast',
                tick_tags={}
            )
            for i in range(5)
        ]
        
        signals = detector.detect_large_orders(
            ticker='NVDA',
            tick_stream=ticks,
            vwap=500.0
        )
        
        # Property: All timestamps are unique
        timestamps = [s.timestamp for s in signals]
        self.assertEqual(len(timestamps), len(set(timestamps)))


class TestVWAPPressureProperty(unittest.TestCase):
    """Test VWAP pressure consistency property (Task 15.5)"""
    
    def test_vwap_pressure_consistency(self):
        """Property: VWAP pressure is consistent with price/vwap ratio"""
        detector = DarkPoolDetector()
        
        # Test cases: (price, vwap, expected_pressure)
        test_cases = [
            (503.0, 500.0, 'buy'),     # >0.5% above
            (497.0, 500.0, 'sell'),    # >0.5% below
            (500.0, 500.0, 'neutral'), # at VWAP
            (501.0, 500.0, 'neutral'), # <0.5% above
        ]
        
        for price, vwap, expected in test_cases:
            pressure = detector.infer_buy_sell_pressure(price, vwap)
            self.assertEqual(
                pressure,
                expected,
                f"Failed for price={price}, vwap={vwap}"
            )


if __name__ == '__main__':
    unittest.main(verbosity=2)
