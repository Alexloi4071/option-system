#!/usr/bin/env python3
"""
StreamManager - Manages concurrent IBKR data streams

Purpose:
- Track active stream count (never exceed 15)
- Queue stream requests when at capacity
- Automatically remove completed streams
- Provide stream health monitoring
- Log stream lifecycle events

IBKR API Limits:
- Maximum concurrent tick-by-tick streams: 5-15 (varies by account)
- We use conservative limit of 15
"""

import logging
import time
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from queue import Queue
from threading import Lock

logger = logging.getLogger(__name__)

# Stream limits
MAX_CONCURRENT_STREAMS = 15
DEFAULT_WAIT_TIMEOUT = 30  # seconds


@dataclass
class Stream:
    """
    Represents an active IBKR data stream
    
    Attributes:
        ticker: Stock symbol
        stream_type: Type of stream ('tick_by_tick', 'market_data', etc.)
        start_time: When the stream was started
        status: Current status ('active', 'completed', 'error')
        req_id: IBKR request ID
        metadata: Additional stream metadata
    """
    ticker: str
    stream_type: str
    start_time: datetime = field(default_factory=datetime.now)
    status: str = 'active'
    req_id: Optional[int] = None
    metadata: Dict = field(default_factory=dict)
    
    def __hash__(self):
        """Make Stream hashable for set operations"""
        return hash((self.ticker, self.stream_type, self.req_id))
    
    def __eq__(self, other):
        """Stream equality based on ticker, type, and req_id"""
        if not isinstance(other, Stream):
            return False
        return (self.ticker == other.ticker and 
                self.stream_type == other.stream_type and
                self.req_id == other.req_id)


class StreamManager:
    """
    Manages concurrent IBKR data streams to respect API limits
    
    Features:
    - Hard limit enforcement (max 15 concurrent streams)
    - Queue-based stream allocation
    - Automatic stream cleanup
    - Health monitoring
    - Thread-safe operations
    
    Example:
        >>> manager = StreamManager(max_concurrent=15)
        >>> stream = manager.add_stream('NVDA', 'tick_by_tick')
        >>> if stream:
        ...     print(f"Stream started: {stream.ticker}")
        >>> manager.remove_stream('NVDA')
    """
    
    def __init__(self, max_concurrent: int = MAX_CONCURRENT_STREAMS):
        """
        Initialize StreamManager
        
        Args:
            max_concurrent: Maximum number of concurrent streams (default: 15)
        """
        self.max_concurrent = max_concurrent
        self._active_streams: Dict[str, Stream] = {}  # ticker -> Stream
        self._stream_queue: Queue = Queue()
        self._lock = Lock()
        
        logger.info(f"StreamManager initialized (max_concurrent={max_concurrent})")
    
    def add_stream(
        self,
        ticker: str,
        stream_type: str,
        req_id: Optional[int] = None,
        metadata: Optional[Dict] = None
    ) -> Optional[Stream]:
        """
        Add a new stream to the manager
        
        Args:
            ticker: Stock symbol
            stream_type: Type of stream ('tick_by_tick', 'market_data', etc.)
            req_id: Optional IBKR request ID
            metadata: Optional additional metadata
        
        Returns:
            Stream object if added successfully, None if at capacity
        
        Raises:
            ValueError: If ticker already has an active stream
        """
        with self._lock:
            # Check if ticker already has a stream
            if ticker in self._active_streams:
                logger.warning(f"Stream already exists for {ticker}")
                raise ValueError(f"Stream already exists for {ticker}")
            
            # Check if at capacity
            if len(self._active_streams) >= self.max_concurrent:
                logger.warning(
                    f"Stream capacity reached ({len(self._active_streams)}/{self.max_concurrent}), "
                    f"cannot add stream for {ticker}"
                )
                return None
            
            # Create and add stream
            stream = Stream(
                ticker=ticker,
                stream_type=stream_type,
                req_id=req_id,
                metadata=metadata or {}
            )
            
            self._active_streams[ticker] = stream
            
            logger.info(
                f"Stream added: {ticker} ({stream_type}) - "
                f"Active: {len(self._active_streams)}/{self.max_concurrent}"
            )
            
            return stream
    
    def remove_stream(self, ticker: str) -> bool:
        """
        Remove a stream from the manager
        
        Args:
            ticker: Stock symbol
        
        Returns:
            bool: True if stream was removed, False if not found
        """
        with self._lock:
            if ticker not in self._active_streams:
                logger.warning(f"No active stream found for {ticker}")
                return False
            
            stream = self._active_streams.pop(ticker)
            stream.status = 'completed'
            
            logger.info(
                f"Stream removed: {ticker} ({stream.stream_type}) - "
                f"Active: {len(self._active_streams)}/{self.max_concurrent}"
            )
            
            return True
    
    def get_concurrent_count(self) -> int:
        """
        Get current number of active streams
        
        Returns:
            int: Number of active streams
        """
        with self._lock:
            return len(self._active_streams)
    
    def wait_for_slot(self, timeout: int = DEFAULT_WAIT_TIMEOUT) -> bool:
        """
        Wait for an available stream slot
        
        Args:
            timeout: Maximum time to wait in seconds (default: 30)
        
        Returns:
            bool: True if slot became available, False if timeout
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            with self._lock:
                if len(self._active_streams) < self.max_concurrent:
                    logger.info(f"Stream slot available ({len(self._active_streams)}/{self.max_concurrent})")
                    return True
            
            # Wait a bit before checking again
            time.sleep(0.1)
        
        logger.warning(f"Timeout waiting for stream slot after {timeout}s")
        return False
    
    def get_active_streams(self) -> List[Stream]:
        """
        Get list of all active streams
        
        Returns:
            List[Stream]: Copy of active streams list
        """
        with self._lock:
            return list(self._active_streams.values())
    
    def get_stream(self, ticker: str) -> Optional[Stream]:
        """
        Get stream for a specific ticker
        
        Args:
            ticker: Stock symbol
        
        Returns:
            Stream object if found, None otherwise
        """
        with self._lock:
            return self._active_streams.get(ticker)
    
    def has_stream(self, ticker: str) -> bool:
        """
        Check if ticker has an active stream
        
        Args:
            ticker: Stock symbol
        
        Returns:
            bool: True if stream exists
        """
        with self._lock:
            return ticker in self._active_streams
    
    def clear_all(self) -> int:
        """
        Remove all active streams
        
        Returns:
            int: Number of streams removed
        """
        with self._lock:
            count = len(self._active_streams)
            self._active_streams.clear()
            logger.info(f"Cleared all streams ({count} removed)")
            return count
    
    def get_health_status(self) -> Dict:
        """
        Get health status of stream manager
        
        Returns:
            dict: Health status including:
                - active_count: Number of active streams
                - capacity: Maximum concurrent streams
                - utilization: Percentage of capacity used
                - streams: List of active stream info
        """
        with self._lock:
            active_count = len(self._active_streams)
            utilization = (active_count / self.max_concurrent) * 100
            
            streams_info = [
                {
                    'ticker': stream.ticker,
                    'type': stream.stream_type,
                    'status': stream.status,
                    'duration': (datetime.now() - stream.start_time).total_seconds(),
                    'req_id': stream.req_id
                }
                for stream in self._active_streams.values()
            ]
            
            return {
                'active_count': active_count,
                'capacity': self.max_concurrent,
                'utilization': utilization,
                'streams': streams_info,
                'timestamp': datetime.now().isoformat()
            }
    
    def cleanup_stale_streams(self, max_age_seconds: int = 300) -> int:
        """
        Remove streams older than max_age_seconds
        
        Args:
            max_age_seconds: Maximum stream age in seconds (default: 300 = 5 minutes)
        
        Returns:
            int: Number of streams removed
        """
        with self._lock:
            now = datetime.now()
            stale_tickers = []
            
            for ticker, stream in self._active_streams.items():
                age = (now - stream.start_time).total_seconds()
                if age > max_age_seconds:
                    stale_tickers.append(ticker)
            
            for ticker in stale_tickers:
                stream = self._active_streams.pop(ticker)
                logger.warning(
                    f"Removed stale stream: {ticker} (age: {(now - stream.start_time).total_seconds():.0f}s)"
                )
            
            if stale_tickers:
                logger.info(f"Cleaned up {len(stale_tickers)} stale streams")
            
            return len(stale_tickers)
    
    def __repr__(self) -> str:
        """String representation"""
        return f"StreamManager(active={len(self._active_streams)}/{self.max_concurrent})"
    
    def __len__(self) -> int:
        """Return number of active streams"""
        return len(self._active_streams)
