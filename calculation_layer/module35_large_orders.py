#!/usr/bin/env python3
"""
Module 35: Large Order Detector

Purpose:
- Identify institutional block trades (>10K shares or >$250K value)
- Track consecutive large orders within 5-minute window
- Calculate VWAP deviation for each large order
- Detect institutional footprints

Data Sources:
- Tick-by-tick data stream
- VWAP (Volume-weighted average price)
- Real-time price and size

Thresholds:
- Block trade: >10,000 shares
- Institutional footprint: >$250,000 value
- Consecutive window: 5 minutes (300 seconds)
- VWAP deviation: (order_price - vwap) / vwap * 100
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from collections import deque

logger = logging.getLogger(__name__)

# Large order detection thresholds
BLOCK_THRESHOLD = 10000  # 10K shares
VALUE_THRESHOLD = 250000.0  # $250K
CONSECUTIVE_WINDOW = 300  # 5 minutes in seconds
VWAP_DEVIATION_SIGNIFICANT = 0.5  # 0.5% deviation


@dataclass
class LargeOrderSignal:
    """
    Large order signal data structure
    
    Attributes:
        ticker: Stock symbol
        timestamp: Order timestamp
        order_size: Number of shares
        order_value: Dollar value of order
        price: Order execution price
        consecutive_count: Number of consecutive large orders in window
        institutional_footprint: Whether this is institutional-sized (>$250K)
        vwap_deviation: Percentage deviation from VWAP
    """
    ticker: str
    timestamp: datetime
    order_size: int
    order_value: float
    price: float
    consecutive_count: int
    institutional_footprint: bool
    vwap_deviation: float
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for storage/serialization"""
        return {
            'ticker': self.ticker,
            'timestamp': self.timestamp.isoformat(),
            'order_size': self.order_size,
            'order_value': self.order_value,
            'price': self.price,
            'consecutive_count': self.consecutive_count,
            'institutional_footprint': self.institutional_footprint,
            'vwap_deviation': self.vwap_deviation
        }
    
    def is_significant(self) -> bool:
        """Check if this is a significant large order"""
        return (self.institutional_footprint or 
                self.consecutive_count >= 3 or
                abs(self.vwap_deviation) > VWAP_DEVIATION_SIGNIFICANT)


class LargeOrderDetector:
    """
    Detects institutional block trades and large orders
    
    Features:
    - Real-time block trade detection (>10K shares)
    - Institutional footprint identification (>$250K)
    - Consecutive order tracking (5-minute window)
    - VWAP deviation calculation
    - Alert generation for unusual patterns
    
    Example:
        >>> detector = LargeOrderDetector()
        >>> signals = detector.detect_large_orders(
        ...     ticker='NVDA',
        ...     tick_stream=[...],
        ...     vwap=500.0
        ... )
        >>> for signal in signals:
        ...     if signal.institutional_footprint:
        ...         print(f"Institutional order: ${signal.order_value:,.0f}")
    """
    
    def __init__(
        self,
        block_threshold: int = BLOCK_THRESHOLD,
        value_threshold: float = VALUE_THRESHOLD,
        consecutive_window: int = CONSECUTIVE_WINDOW
    ):
        """
        Initialize LargeOrderDetector
        
        Args:
            block_threshold: Minimum shares for block trade (default: 10000)
            value_threshold: Minimum value for institutional footprint (default: 250000)
            consecutive_window: Time window for consecutive orders in seconds (default: 300)
        """
        self.block_threshold = block_threshold
        self.value_threshold = value_threshold
        self.consecutive_window = consecutive_window
        
        # Track recent large orders per ticker
        self._recent_orders: Dict[str, deque] = {}
        
        logger.info(
            f"LargeOrderDetector initialized "
            f"(block={block_threshold}, value=${value_threshold:,.0f}, window={consecutive_window}s)"
        )
    
    def detect_large_orders(
        self,
        ticker: str,
        tick_stream: List,
        vwap: float,
        block_threshold: Optional[int] = None,
        value_threshold: Optional[float] = None
    ) -> List[LargeOrderSignal]:
        """
        Detect large orders from tick-by-tick stream
        
        Args:
            ticker: Stock symbol
            tick_stream: List of TickByTickData objects
            vwap: Volume-weighted average price
            block_threshold: Optional override for block threshold
            value_threshold: Optional override for value threshold
        
        Returns:
            List[LargeOrderSignal]: List of detected large orders
        
        Raises:
            ValueError: If inputs are invalid
        """
        # Validate inputs
        if not ticker:
            raise ValueError("ticker must be non-empty string")
        if vwap <= 0:
            raise ValueError("vwap must be positive")
        
        # Use instance thresholds if not overridden
        if block_threshold is None:
            block_threshold = self.block_threshold
        if value_threshold is None:
            value_threshold = self.value_threshold
        
        signals = []
        
        for tick in tick_stream:
            # Check if this is a large order
            order_value = tick.price * tick.size
            
            if tick.size >= block_threshold or order_value >= value_threshold:
                # Calculate VWAP deviation
                vwap_deviation = self.calculate_vwap_deviation(tick.price, vwap)
                
                # Check if institutional footprint
                institutional_footprint = order_value >= value_threshold
                
                # Track consecutive orders
                consecutive_count = self.track_consecutive_orders(ticker, tick.timestamp)
                
                # Create signal
                signal = LargeOrderSignal(
                    ticker=ticker,
                    timestamp=tick.timestamp,
                    order_size=tick.size,
                    order_value=order_value,
                    price=tick.price,
                    consecutive_count=consecutive_count,
                    institutional_footprint=institutional_footprint,
                    vwap_deviation=vwap_deviation
                )
                
                signals.append(signal)
                
                # Log significant orders
                if institutional_footprint:
                    logger.warning(
                        f"[WHALE] {ticker} Institutional Order: {tick.size:,} shares @ ${tick.price:.2f} "
                        f"(${order_value:,.0f}, VWAP dev: {vwap_deviation:+.2f}%)"
                    )
        
        return signals
    
    def track_consecutive_orders(
        self,
        ticker: str,
        timestamp: datetime,
        time_window: Optional[int] = None
    ) -> int:
        """
        Track consecutive large orders within time window
        
        Args:
            ticker: Stock symbol
            timestamp: Current order timestamp
            time_window: Time window in seconds (default: self.consecutive_window)
        
        Returns:
            int: Number of consecutive large orders in window (including current)
        """
        if time_window is None:
            time_window = self.consecutive_window
        
        # Initialize deque for ticker if not exists
        if ticker not in self._recent_orders:
            self._recent_orders[ticker] = deque()
        
        # Add current order
        self._recent_orders[ticker].append(timestamp)
        
        # Remove orders outside time window
        cutoff_time = timestamp - timedelta(seconds=time_window)
        while (self._recent_orders[ticker] and 
               self._recent_orders[ticker][0] < cutoff_time):
            self._recent_orders[ticker].popleft()
        
        # Return count of orders in window
        return len(self._recent_orders[ticker])
    
    def calculate_vwap_deviation(
        self,
        order_price: float,
        vwap: float
    ) -> float:
        """
        Calculate price deviation from VWAP
        
        Args:
            order_price: Order execution price
            vwap: Volume-weighted average price
        
        Returns:
            float: Percentage deviation from VWAP
        
        Formula:
            deviation = (order_price - vwap) / vwap * 100
        """
        if vwap <= 0:
            return 0.0
        
        deviation = ((order_price - vwap) / vwap) * 100.0
        return deviation
    
    def get_recent_orders(self, ticker: str) -> List[datetime]:
        """
        Get recent large order timestamps for a ticker
        
        Args:
            ticker: Stock symbol
        
        Returns:
            List[datetime]: List of recent order timestamps
        """
        if ticker not in self._recent_orders:
            return []
        return list(self._recent_orders[ticker])
    
    def clear_history(self, ticker: Optional[str] = None):
        """
        Clear order history
        
        Args:
            ticker: Optional ticker to clear, or None to clear all
        """
        if ticker:
            if ticker in self._recent_orders:
                self._recent_orders[ticker].clear()
                logger.info(f"Cleared order history for {ticker}")
        else:
            self._recent_orders.clear()
            logger.info("Cleared all order history")
