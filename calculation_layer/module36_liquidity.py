#!/usr/bin/env python3
"""
Module 36: Short-Term Liquidity Monitor

Purpose:
- Calculate volume acceleration across multiple time windows
- Detect breakout confirmation signals
- Identify exhaustion signals (new high with declining volume)
- Validate volume monotonicity

Data Sources:
- Tick 63: 3-minute volume
- Tick 64: 5-minute volume
- Tick 65: 10-minute volume
- Average volume baseline (historical)
- Current price and price trend

Thresholds:
- Breakout confirmation: acceleration_ratio > 2.0 AND price breakout
- Exhaustion signal: new high AND acceleration_ratio < 0.5
- Volume monotonicity: volume_3min <= volume_5min <= volume_10min
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Liquidity detection thresholds
BREAKOUT_ACCELERATION_THRESHOLD = 2.0  # 2x acceleration
EXHAUSTION_ACCELERATION_THRESHOLD = 0.5  # 0.5x deceleration
VOLUME_SPIKE_THRESHOLD = 1.5  # 1.5x average volume


@dataclass
class LiquidityMetrics:
    """
    Short-term liquidity metrics data structure
    
    Attributes:
        ticker: Stock symbol
        timestamp: Data timestamp
        volume_3min: 3-minute cumulative volume
        volume_5min: 5-minute cumulative volume
        volume_10min: 10-minute cumulative volume
        acceleration_ratio: Volume acceleration (3min rate vs 10min rate)
        breakout_confirmed: Whether breakout is confirmed by volume
        exhaustion_signal: Whether exhaustion signal detected
        avg_volume_baseline: Historical average volume baseline
        volume_monotonic: Whether volumes follow monotonic property
    """
    ticker: str
    timestamp: datetime
    volume_3min: int
    volume_5min: int
    volume_10min: int
    acceleration_ratio: float
    breakout_confirmed: bool
    exhaustion_signal: bool
    avg_volume_baseline: int
    volume_monotonic: bool
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for storage/serialization"""
        return {
            'ticker': self.ticker,
            'timestamp': self.timestamp.isoformat(),
            'volume_3min': self.volume_3min,
            'volume_5min': self.volume_5min,
            'volume_10min': self.volume_10min,
            'acceleration_ratio': self.acceleration_ratio,
            'breakout_confirmed': self.breakout_confirmed,
            'exhaustion_signal': self.exhaustion_signal,
            'avg_volume_baseline': self.avg_volume_baseline,
            'volume_monotonic': self.volume_monotonic
        }
    
    def is_significant(self) -> bool:
        """Check if this is a significant liquidity event"""
        return self.breakout_confirmed or self.exhaustion_signal


class LiquidityMonitor:
    """
    Monitors short-term liquidity and volume acceleration
    
    Features:
    - Volume acceleration calculation across 3/5/10 minute windows
    - Breakout confirmation detection (high volume + price breakout)
    - Exhaustion signal detection (new high + declining volume)
    - Volume monotonicity validation
    - Alert generation for significant events
    
    Example:
        >>> monitor = LiquidityMonitor()
        >>> metrics = monitor.calculate_volume_acceleration(
        ...     ticker='NVDA',
        ...     volume_3min=100000,
        ...     volume_5min=150000,
        ...     volume_10min=250000,
        ...     avg_volume_baseline=100000
        ... )
        >>> if metrics.breakout_confirmed:
        ...     print(f"Breakout confirmed: {metrics.acceleration_ratio:.2f}x")
    """
    
    def __init__(self):
        """Initialize LiquidityMonitor"""
        logger.info("LiquidityMonitor initialized")
    
    def calculate_volume_acceleration(
        self,
        ticker: str,
        volume_3min: int,
        volume_5min: int,
        volume_10min: int,
        avg_volume_baseline: int,
        price_breakout: bool = False,
        at_new_high: bool = False
    ) -> LiquidityMetrics:
        """
        Calculate volume acceleration and detect liquidity signals
        
        Args:
            ticker: Stock symbol
            volume_3min: 3-minute cumulative volume (Tick 63)
            volume_5min: 5-minute cumulative volume (Tick 64)
            volume_10min: 10-minute cumulative volume (Tick 65)
            avg_volume_baseline: Historical average volume baseline
            price_breakout: Whether price has broken out (optional)
            at_new_high: Whether price is at new high (optional)
        
        Returns:
            LiquidityMetrics: Liquidity analysis results
        
        Raises:
            ValueError: If inputs are invalid
        """
        # Validate inputs
        if not ticker:
            raise ValueError("ticker must be non-empty string")
        if volume_3min < 0 or volume_5min < 0 or volume_10min < 0:
            raise ValueError("Volumes must be non-negative")
        if avg_volume_baseline <= 0:
            raise ValueError("avg_volume_baseline must be positive")
        
        # Check volume monotonicity
        volume_monotonic = self.validate_volume_monotonicity(
            volume_3min, volume_5min, volume_10min
        )
        
        if not volume_monotonic:
            logger.warning(
                f"{ticker}: Volume monotonicity violated "
                f"(3min={volume_3min}, 5min={volume_5min}, 10min={volume_10min})"
            )
        
        # Calculate acceleration ratio
        # acceleration_ratio = (volume_3min / 3) / (volume_10min / 10)
        # This measures if recent 3-min volume rate is higher than 10-min average rate
        acceleration_ratio = self.calculate_acceleration_ratio(
            volume_3min, volume_10min
        )
        
        # Detect breakout confirmation
        breakout_confirmed = self.detect_breakout_confirmation(
            acceleration_ratio=acceleration_ratio,
            price_breakout=price_breakout,
            volume_10min=volume_10min,
            avg_volume_baseline=avg_volume_baseline
        )
        
        # Detect exhaustion signal
        exhaustion_signal = self.detect_exhaustion_signal(
            acceleration_ratio=acceleration_ratio,
            at_new_high=at_new_high
        )
        
        # Create result
        result = LiquidityMetrics(
            ticker=ticker,
            timestamp=datetime.now(),
            volume_3min=volume_3min,
            volume_5min=volume_5min,
            volume_10min=volume_10min,
            acceleration_ratio=acceleration_ratio,
            breakout_confirmed=breakout_confirmed,
            exhaustion_signal=exhaustion_signal,
            avg_volume_baseline=avg_volume_baseline,
            volume_monotonic=volume_monotonic
        )
        
        # Log significant events
        if breakout_confirmed:
            logger.warning(
                f"[BREAKOUT] {ticker} Breakout Confirmed: "
                f"{acceleration_ratio:.2f}x acceleration, volume={volume_10min:,}"
            )
        
        if exhaustion_signal:
            logger.warning(
                f"[EXHAUSTION] {ticker} Exhaustion Signal: "
                f"{acceleration_ratio:.2f}x deceleration at new high"
            )
        
        return result
    
    def calculate_acceleration_ratio(
        self,
        volume_3min: int,
        volume_10min: int
    ) -> float:
        """
        Calculate volume acceleration ratio
        
        Args:
            volume_3min: 3-minute cumulative volume
            volume_10min: 10-minute cumulative volume
        
        Returns:
            float: Acceleration ratio (3min rate / 10min rate)
        
        Formula:
            acceleration_ratio = (volume_3min / 3) / (volume_10min / 10)
                               = (volume_3min * 10) / (volume_10min * 3)
        """
        if volume_10min == 0:
            return 0.0
        
        # Calculate per-minute rates
        rate_3min = volume_3min / 3.0
        rate_10min = volume_10min / 10.0
        
        if rate_10min == 0:
            return 0.0
        
        acceleration_ratio = rate_3min / rate_10min
        return acceleration_ratio
    
    def validate_volume_monotonicity(
        self,
        volume_3min: int,
        volume_5min: int,
        volume_10min: int
    ) -> bool:
        """
        Validate volume monotonicity property
        
        Args:
            volume_3min: 3-minute cumulative volume
            volume_5min: 5-minute cumulative volume
            volume_10min: 10-minute cumulative volume
        
        Returns:
            bool: True if volumes are monotonic (3min <= 5min <= 10min)
        
        Property:
            volume_3min <= volume_5min <= volume_10min
        """
        return volume_3min <= volume_5min <= volume_10min
    
    def detect_breakout_confirmation(
        self,
        acceleration_ratio: float,
        price_breakout: bool,
        volume_10min: int,
        avg_volume_baseline: int
    ) -> bool:
        """
        Detect breakout confirmation signal
        
        Args:
            acceleration_ratio: Volume acceleration ratio
            price_breakout: Whether price has broken out
            volume_10min: 10-minute cumulative volume
            avg_volume_baseline: Historical average volume
        
        Returns:
            bool: True if breakout is confirmed
        
        Logic:
            Breakout confirmed if:
            - acceleration_ratio > 2.0 (strong acceleration) AND
            - price_breakout = True (price has broken resistance) AND
            - volume_10min > avg_volume_baseline * 1.5 (volume spike)
        """
        volume_spike = volume_10min > (avg_volume_baseline * VOLUME_SPIKE_THRESHOLD)
        
        return (acceleration_ratio > BREAKOUT_ACCELERATION_THRESHOLD and
                price_breakout and
                volume_spike)
    
    def detect_exhaustion_signal(
        self,
        acceleration_ratio: float,
        at_new_high: bool
    ) -> bool:
        """
        Detect exhaustion signal
        
        Args:
            acceleration_ratio: Volume acceleration ratio
            at_new_high: Whether price is at new high
        
        Returns:
            bool: True if exhaustion signal detected
        
        Logic:
            Exhaustion signal if:
            - at_new_high = True (price at new high) AND
            - acceleration_ratio < 0.5 (volume declining)
        """
        return at_new_high and acceleration_ratio < EXHAUSTION_ACCELERATION_THRESHOLD
