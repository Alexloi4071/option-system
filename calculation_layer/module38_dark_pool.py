#!/usr/bin/env python3
"""
Module 38: Dark Pool Activity Detector

Purpose:
- Detect and analyze institutional dark pool trading activity
- Calculate dark pool volume percentage
- Detect surge conditions (>40% or 2x historical average)
- Infer buy/sell pressure using VWAP
- Maintain historical baseline for comparison

Data Sources:
- Tick 48: RT Volume (total volume including dark pools)
- Tick 77: RT Trade Volume (lit exchanges only)
- VWAP: Volume-weighted average price
- Current Price: Real-time price

Formula:
    dark_pool_volume = rt_volume - rt_trade_volume
    dark_pool_pct = (dark_pool_volume / rt_volume) * 100
    
    surge_detected = dark_pool_pct > 40 OR dark_pool_volume > 2 * historical_avg
    
    buy_sell_pressure:
        - 'buy' if current_price > vwap * 1.005 (0.5% above VWAP)
        - 'sell' if current_price < vwap * 0.995 (0.5% below VWAP)
        - 'neutral' otherwise
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional
from collections import deque

logger = logging.getLogger(__name__)

# Dark pool detection thresholds
DARK_POOL_SURGE_THRESHOLD = 40.0  # 40% dark pool percentage
DARK_POOL_SURGE_RATIO = 2.0  # 2x historical average
VWAP_BUY_THRESHOLD = 1.005  # 0.5% above VWAP
VWAP_SELL_THRESHOLD = 0.995  # 0.5% below VWAP
HISTORICAL_WINDOW = 20  # 20-day rolling average


@dataclass
class DarkPoolData:
    """
    Dark pool activity data structure
    
    Attributes:
        ticker: Stock symbol
        timestamp: Data timestamp
        dark_volume: Volume traded in dark pools
        total_volume: Total volume (including dark pools)
        dark_pool_pct: Dark pool percentage (0-100)
        vwap: Volume-weighted average price
        price: Current price
        buy_sell_pressure: Institutional pressure ('buy', 'sell', 'neutral')
        surge_detected: Whether surge condition detected
        surge_ratio: Current vs historical average ratio
    """
    ticker: str
    timestamp: datetime
    dark_volume: int
    total_volume: int
    dark_pool_pct: float
    vwap: float
    price: float
    buy_sell_pressure: str
    surge_detected: bool
    surge_ratio: float
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for storage/serialization"""
        return {
            'ticker': self.ticker,
            'timestamp': self.timestamp.isoformat(),
            'dark_volume': self.dark_volume,
            'total_volume': self.total_volume,
            'dark_pool_pct': self.dark_pool_pct,
            'vwap': self.vwap,
            'price': self.price,
            'buy_sell_pressure': self.buy_sell_pressure,
            'surge_detected': self.surge_detected,
            'surge_ratio': self.surge_ratio
        }
    
    def is_significant(self) -> bool:
        """Check if this is a significant dark pool event"""
        return self.surge_detected or self.dark_pool_pct > 30.0


class DarkPoolDetector:
    """
    Detects and analyzes dark pool trading activity
    
    Features:
    - Real-time dark pool percentage calculation
    - Surge detection (>40% or 2x average)
    - Buy/sell pressure inference using VWAP
    - Historical baseline tracking
    - Alert generation for significant activity
    
    Example:
        >>> detector = DarkPoolDetector()
        >>> data = detector.detect_dark_pool_activity(
        ...     ticker='NVDA',
        ...     rt_volume=1000000,
        ...     rt_trade_volume=600000,
        ...     vwap=500.0,
        ...     current_price=502.5
        ... )
        >>> print(f"Dark pool: {data.dark_pool_pct:.1f}%, Pressure: {data.buy_sell_pressure}")
    """
    
    def __init__(self, historical_window: int = HISTORICAL_WINDOW):
        """
        Initialize DarkPoolDetector
        
        Args:
            historical_window: Number of days for historical average (default: 20)
        """
        self.historical_window = historical_window
        self._historical_data: Dict[str, deque] = {}  # ticker -> deque of dark_volumes
        
        logger.info(f"DarkPoolDetector initialized (window={historical_window} days)")
    
    def detect_dark_pool_activity(
        self,
        ticker: str,
        rt_volume: int,
        rt_trade_volume: int,
        vwap: float,
        current_price: float,
        historical_avg: Optional[float] = None
    ) -> DarkPoolData:
        """
        Detect dark pool activity from tick data
        
        Args:
            ticker: Stock symbol
            rt_volume: RT Volume (Tick 48) - total volume including dark pools
            rt_trade_volume: RT Trade Volume (Tick 77) - lit exchanges only
            vwap: Volume-weighted average price
            current_price: Current market price
            historical_avg: Optional historical average dark pool volume
        
        Returns:
            DarkPoolData: Dark pool analysis results
        
        Raises:
            ValueError: If inputs are invalid
        """
        # Validate inputs
        if not ticker:
            raise ValueError("ticker must be non-empty string")
        if rt_volume < 0 or rt_trade_volume < 0:
            raise ValueError("Volumes must be non-negative")
        if vwap <= 0 or current_price <= 0:
            raise ValueError("Prices must be positive")
        if rt_trade_volume > rt_volume:
            logger.warning(
                f"{ticker}: rt_trade_volume ({rt_trade_volume}) > rt_volume ({rt_volume}), "
                "setting dark_volume to 0"
            )
            rt_trade_volume = rt_volume
        
        # Calculate dark pool volume
        dark_volume = rt_volume - rt_trade_volume
        
        # Calculate dark pool percentage
        if rt_volume > 0:
            dark_pool_pct = (dark_volume / rt_volume) * 100.0
        else:
            dark_pool_pct = 0.0
        
        # Ensure percentage is in valid range [0, 100]
        dark_pool_pct = max(0.0, min(100.0, dark_pool_pct))
        
        # Get or calculate historical average
        if historical_avg is None:
            historical_avg = self.calculate_historical_average(ticker)
        
        # Detect surge conditions
        surge_detected = False
        surge_ratio = 0.0
        
        if historical_avg > 0:
            surge_ratio = dark_volume / historical_avg
            # Surge if >40% OR >2x historical average
            surge_detected = (dark_pool_pct > DARK_POOL_SURGE_THRESHOLD or 
                            surge_ratio > DARK_POOL_SURGE_RATIO)
        else:
            # No historical data, use percentage threshold only
            surge_detected = dark_pool_pct > DARK_POOL_SURGE_THRESHOLD
        
        # Infer buy/sell pressure
        buy_sell_pressure = self.infer_buy_sell_pressure(current_price, vwap)
        
        # Update historical data
        self._update_historical_data(ticker, dark_volume)
        
        # Create result
        result = DarkPoolData(
            ticker=ticker,
            timestamp=datetime.now(),
            dark_volume=dark_volume,
            total_volume=rt_volume,
            dark_pool_pct=dark_pool_pct,
            vwap=vwap,
            price=current_price,
            buy_sell_pressure=buy_sell_pressure,
            surge_detected=surge_detected,
            surge_ratio=surge_ratio
        )
        
        # Log significant events
        if surge_detected:
            logger.warning(
                f"[ALERT] {ticker} Dark Pool Surge: {dark_pool_pct:.1f}% "
                f"(ratio: {surge_ratio:.2f}x, pressure: {buy_sell_pressure})"
            )
        
        return result
    
    def calculate_historical_average(self, ticker: str, window: int = None) -> float:
        """
        Calculate historical average dark pool volume
        
        Args:
            ticker: Stock symbol
            window: Number of periods to average (default: self.historical_window)
        
        Returns:
            float: Average dark pool volume, or 0.0 if no history
        """
        if window is None:
            window = self.historical_window
        
        if ticker not in self._historical_data or not self._historical_data[ticker]:
            return 0.0
        
        history = list(self._historical_data[ticker])
        if not history:
            return 0.0
        
        # Calculate average
        avg = sum(history) / len(history)
        return avg
    
    def infer_buy_sell_pressure(self, price: float, vwap: float) -> str:
        """
        Infer institutional buy/sell pressure using VWAP
        
        Args:
            price: Current market price
            vwap: Volume-weighted average price
        
        Returns:
            str: 'buy', 'sell', or 'neutral'
        
        Logic:
            - 'buy' if price > vwap * 1.005 (0.5% above VWAP)
            - 'sell' if price < vwap * 0.995 (0.5% below VWAP)
            - 'neutral' otherwise
        """
        if vwap <= 0:
            return 'neutral'
        
        ratio = price / vwap
        
        if ratio > VWAP_BUY_THRESHOLD:
            return 'buy'
        elif ratio < VWAP_SELL_THRESHOLD:
            return 'sell'
        else:
            return 'neutral'
    
    def _update_historical_data(self, ticker: str, dark_volume: int):
        """
        Update historical dark pool volume data
        
        Args:
            ticker: Stock symbol
            dark_volume: Dark pool volume to add
        """
        if ticker not in self._historical_data:
            self._historical_data[ticker] = deque(maxlen=self.historical_window)
        
        self._historical_data[ticker].append(dark_volume)
    
    def get_historical_data(self, ticker: str) -> list:
        """
        Get historical dark pool volume data
        
        Args:
            ticker: Stock symbol
        
        Returns:
            list: Historical dark pool volumes
        """
        if ticker not in self._historical_data:
            return []
        return list(self._historical_data[ticker])
    
    def clear_historical_data(self, ticker: Optional[str] = None):
        """
        Clear historical data
        
        Args:
            ticker: Optional ticker to clear, or None to clear all
        """
        if ticker:
            if ticker in self._historical_data:
                self._historical_data[ticker].clear()
                logger.info(f"Cleared historical data for {ticker}")
        else:
            self._historical_data.clear()
            logger.info("Cleared all historical data")
