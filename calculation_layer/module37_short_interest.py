#!/usr/bin/env python3
"""
Module 37: Short Interest Analyzer

Purpose:
- Analyze shortable difficulty and shares availability
- Calculate short squeeze potential score (0-100)
- Track difficulty changes over time
- Detect short squeeze conditions

Data Sources:
- Tick 46: Shortable difficulty (1=easy, 2=moderate, 3=hard)
- Tick 89: Shortable shares available
- Price trend (rising, falling, flat)
- Historical difficulty tracking

Thresholds:
- Short squeeze potential: shortable_shares < 100,000 AND price rising
- Squeeze score: (1 - shortable_shares/1,000,000) * 100, capped at 100
- Difficulty levels: 1=easy, 2=moderate, 3=hard, 4=unavailable
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional
from collections import deque

logger = logging.getLogger(__name__)

# Short interest thresholds
SQUEEZE_SHARES_THRESHOLD = 100000  # 100K shares
SQUEEZE_SHARES_BASELINE = 1000000  # 1M shares for score calculation
DIFFICULTY_EASY = 1
DIFFICULTY_MODERATE = 2
DIFFICULTY_HARD = 3
DIFFICULTY_UNAVAILABLE = 4


@dataclass
class ShortInterestData:
    """
    Short interest analysis data structure
    
    Attributes:
        ticker: Stock symbol
        timestamp: Data timestamp
        shortable_difficulty: Difficulty level string
        shortable_shares: Number of shares available to short
        difficulty_change: Change from previous ('easier', 'harder', 'unchanged')
        short_squeeze_potential: Whether squeeze conditions are met
        squeeze_score: Squeeze potential score (0-100)
        price_trend: Current price trend ('rising', 'falling', 'flat')
    """
    ticker: str
    timestamp: datetime
    shortable_difficulty: str
    shortable_shares: int
    difficulty_change: str
    short_squeeze_potential: bool
    squeeze_score: float
    price_trend: str
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for storage/serialization"""
        return {
            'ticker': self.ticker,
            'timestamp': self.timestamp.isoformat(),
            'shortable_difficulty': self.shortable_difficulty,
            'shortable_shares': self.shortable_shares,
            'difficulty_change': self.difficulty_change,
            'short_squeeze_potential': self.short_squeeze_potential,
            'squeeze_score': self.squeeze_score,
            'price_trend': self.price_trend
        }
    
    def is_significant(self) -> bool:
        """Check if this is a significant short interest event"""
        return self.short_squeeze_potential or self.squeeze_score > 70.0


class ShortInterestAnalyzer:
    """
    Analyzes short interest and squeeze potential
    
    Features:
    - Shortable difficulty tracking
    - Squeeze score calculation (0-100)
    - Difficulty change detection
    - Short squeeze potential identification
    - Alert generation for high squeeze risk
    
    Example:
        >>> analyzer = ShortInterestAnalyzer()
        >>> data = analyzer.analyze_short_interest(
        ...     ticker='GME',
        ...     shortable_difficulty=3,
        ...     shortable_shares=50000,
        ...     previous_difficulty=2,
        ...     price_trend='rising'
        ... )
        >>> if data.short_squeeze_potential:
        ...     print(f"Squeeze score: {data.squeeze_score:.0f}/100")
    """
    
    def __init__(self):
        """Initialize ShortInterestAnalyzer"""
        # Track historical difficulty per ticker
        self._difficulty_history: Dict[str, deque] = {}
        
        logger.info("ShortInterestAnalyzer initialized")
    
    def analyze_short_interest(
        self,
        ticker: str,
        shortable_difficulty: int,
        shortable_shares: int,
        previous_difficulty: Optional[int] = None,
        price_trend: str = 'flat'
    ) -> ShortInterestData:
        """
        Analyze short interest and calculate squeeze potential
        
        Args:
            ticker: Stock symbol
            shortable_difficulty: Difficulty level (1=easy, 2=moderate, 3=hard, 4=unavailable)
            shortable_shares: Number of shares available to short
            previous_difficulty: Previous difficulty level (optional)
            price_trend: Price trend ('rising', 'falling', 'flat')
        
        Returns:
            ShortInterestData: Short interest analysis results
        
        Raises:
            ValueError: If inputs are invalid
        """
        # Validate inputs
        if not ticker:
            raise ValueError("ticker must be non-empty string")
        if shortable_difficulty not in {1, 2, 3, 4}:
            raise ValueError("shortable_difficulty must be 1, 2, 3, or 4")
        if shortable_shares < 0:
            raise ValueError("shortable_shares must be non-negative")
        if price_trend not in {'rising', 'falling', 'flat'}:
            raise ValueError("price_trend must be 'rising', 'falling', or 'flat'")
        
        # Convert difficulty to string
        difficulty_str = self.difficulty_to_string(shortable_difficulty)
        
        # Get previous difficulty from history if not provided
        if previous_difficulty is None:
            previous_difficulty = self.get_previous_difficulty(ticker)
        
        # Determine difficulty change
        difficulty_change = self.determine_difficulty_change(
            current=shortable_difficulty,
            previous=previous_difficulty
        )
        
        # Calculate squeeze score
        squeeze_score = self.calculate_squeeze_score(shortable_shares)
        
        # Detect short squeeze potential
        short_squeeze_potential = self.detect_squeeze_potential(
            shortable_shares=shortable_shares,
            price_trend=price_trend
        )
        
        # Update difficulty history
        self._update_difficulty_history(ticker, shortable_difficulty)
        
        # Create result
        result = ShortInterestData(
            ticker=ticker,
            timestamp=datetime.now(),
            shortable_difficulty=difficulty_str,
            shortable_shares=shortable_shares,
            difficulty_change=difficulty_change,
            short_squeeze_potential=short_squeeze_potential,
            squeeze_score=squeeze_score,
            price_trend=price_trend
        )
        
        # Log significant events
        if short_squeeze_potential:
            logger.warning(
                f"[SQUEEZE] {ticker} Short Squeeze Potential: "
                f"score={squeeze_score:.0f}/100, shares={shortable_shares:,}, "
                f"difficulty={difficulty_str}, trend={price_trend}"
            )
        elif difficulty_change == 'harder':
            logger.info(
                f"{ticker} Shorting difficulty increased: {difficulty_str} "
                f"(shares={shortable_shares:,})"
            )
        
        return result
    
    def difficulty_to_string(self, difficulty: int) -> str:
        """
        Convert difficulty code to string
        
        Args:
            difficulty: Difficulty code (1-4)
        
        Returns:
            str: Difficulty string
        """
        mapping = {
            1: 'easy',
            2: 'moderate',
            3: 'hard',
            4: 'unavailable'
        }
        return mapping.get(difficulty, 'unknown')
    
    def determine_difficulty_change(
        self,
        current: int,
        previous: Optional[int]
    ) -> str:
        """
        Determine difficulty change from previous
        
        Args:
            current: Current difficulty level
            previous: Previous difficulty level (or None)
        
        Returns:
            str: 'easier', 'harder', or 'unchanged'
        """
        if previous is None:
            return 'unchanged'
        
        if current < previous:
            return 'easier'
        elif current > previous:
            return 'harder'
        else:
            return 'unchanged'
    
    def calculate_squeeze_score(self, shortable_shares: int) -> float:
        """
        Calculate short squeeze score (0-100)
        
        Args:
            shortable_shares: Number of shares available to short
        
        Returns:
            float: Squeeze score (0-100)
        
        Formula:
            score = (1 - shortable_shares / 1,000,000) * 100
            Capped at [0, 100]
        """
        if shortable_shares >= SQUEEZE_SHARES_BASELINE:
            return 0.0
        
        score = (1.0 - (shortable_shares / SQUEEZE_SHARES_BASELINE)) * 100.0
        
        # Ensure score is in [0, 100]
        score = max(0.0, min(100.0, score))
        
        return score
    
    def detect_squeeze_potential(
        self,
        shortable_shares: int,
        price_trend: str
    ) -> bool:
        """
        Detect short squeeze potential
        
        Args:
            shortable_shares: Number of shares available to short
            price_trend: Price trend ('rising', 'falling', 'flat')
        
        Returns:
            bool: True if squeeze potential detected
        
        Logic:
            Squeeze potential if:
            - shortable_shares < 100,000 (low availability) AND
            - price_trend == 'rising' (price going up)
        """
        return (shortable_shares < SQUEEZE_SHARES_THRESHOLD and
                price_trend == 'rising')
    
    def get_previous_difficulty(self, ticker: str) -> Optional[int]:
        """
        Get previous difficulty from history
        
        Args:
            ticker: Stock symbol
        
        Returns:
            int: Previous difficulty level, or None if no history
        """
        if ticker not in self._difficulty_history:
            return None
        
        history = self._difficulty_history[ticker]
        if len(history) == 0:
            return None
        
        return history[-1]
    
    def _update_difficulty_history(self, ticker: str, difficulty: int):
        """
        Update difficulty history
        
        Args:
            ticker: Stock symbol
            difficulty: Current difficulty level
        """
        if ticker not in self._difficulty_history:
            self._difficulty_history[ticker] = deque(maxlen=20)
        
        self._difficulty_history[ticker].append(difficulty)
    
    def get_difficulty_history(self, ticker: str) -> list:
        """
        Get difficulty history for a ticker
        
        Args:
            ticker: Stock symbol
        
        Returns:
            list: Historical difficulty levels
        """
        if ticker not in self._difficulty_history:
            return []
        return list(self._difficulty_history[ticker])
    
    def clear_history(self, ticker: Optional[str] = None):
        """
        Clear difficulty history
        
        Args:
            ticker: Optional ticker to clear, or None to clear all
        """
        if ticker:
            if ticker in self._difficulty_history:
                self._difficulty_history[ticker].clear()
                logger.info(f"Cleared difficulty history for {ticker}")
        else:
            self._difficulty_history.clear()
            logger.info("Cleared all difficulty history")
