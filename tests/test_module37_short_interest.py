#!/usr/bin/env python3
"""
Unit tests for Module 37: Short Interest Analyzer (Task 7)

Tests cover:
- 7.2: ShortInterestData data class
- 7.3: analyze_short_interest() function
- 7.4: Squeeze score calculation (0-100)
- 7.5: Difficulty change tracking
- 7.6: Short squeeze potential detection
"""

import sys
import unittest
from datetime import datetime

sys.path.append('.')

from calculation_layer.module37_short_interest import (
    ShortInterestAnalyzer,
    ShortInterestData,
    SQUEEZE_SHARES_THRESHOLD,
    SQUEEZE_SHARES_BASELINE
)


class TestShortInterestData(unittest.TestCase):
    """Test ShortInterestData dataclass (Task 7.2)"""
    
    def test_short_interest_data_creation(self):
        """Test creating ShortInterestData object"""
        data = ShortInterestData(
            ticker='GME',
            timestamp=datetime.now(),
            shortable_difficulty='hard',
            shortable_shares=50000,
            difficulty_change='harder',
            short_squeeze_potential=True,
            squeeze_score=95.0,
            price_trend='rising'
        )
        
        self.assertEqual(data.ticker, 'GME')
        self.assertEqual(data.shortable_difficulty, 'hard')
        self.assertEqual(data.shortable_shares, 50000)
        self.assertTrue(data.short_squeeze_potential)
        self.assertEqual(data.squeeze_score, 95.0)
    
    def test_to_dict(self):
        """Test to_dict method"""
        data = ShortInterestData(
            ticker='GME',
            timestamp=datetime(2026, 3, 6, 10, 0, 0),
            shortable_difficulty='hard',
            shortable_shares=50000,
            difficulty_change='harder',
            short_squeeze_potential=True,
            squeeze_score=95.0,
            price_trend='rising'
        )
        
        result = data.to_dict()
        
        self.assertEqual(result['ticker'], 'GME')
        self.assertEqual(result['shortable_difficulty'], 'hard')
        self.assertEqual(result['squeeze_score'], 95.0)
        self.assertIn('timestamp', result)
    
    def test_is_significant(self):
        """Test is_significant method"""
        # Significant due to squeeze potential
        data1 = ShortInterestData(
            ticker='GME', timestamp=datetime.now(),
            shortable_difficulty='hard', shortable_shares=50000,
            difficulty_change='harder', short_squeeze_potential=True,
            squeeze_score=95.0, price_trend='rising'
        )
        self.assertTrue(data1.is_significant())
        
        # Significant due to high score
        data2 = ShortInterestData(
            ticker='GME', timestamp=datetime.now(),
            shortable_difficulty='moderate', shortable_shares=200000,
            difficulty_change='unchanged', short_squeeze_potential=False,
            squeeze_score=80.0, price_trend='flat'
        )
        self.assertTrue(data2.is_significant())
        
        # Not significant
        data3 = ShortInterestData(
            ticker='GME', timestamp=datetime.now(),
            shortable_difficulty='easy', shortable_shares=500000,
            difficulty_change='unchanged', short_squeeze_potential=False,
            squeeze_score=50.0, price_trend='flat'
        )
        self.assertFalse(data3.is_significant())


class TestShortInterestAnalyzer(unittest.TestCase):
    """Test ShortInterestAnalyzer class (Task 7.3)"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.analyzer = ShortInterestAnalyzer()
    
    def test_analyzer_initialization(self):
        """Test ShortInterestAnalyzer initialization"""
        self.assertIsNotNone(self.analyzer)
    
    def test_analyze_short_interest_basic(self):
        """Test basic short interest analysis"""
        data = self.analyzer.analyze_short_interest(
            ticker='GME',
            shortable_difficulty=3,
            shortable_shares=50000,
            price_trend='rising'
        )
        
        self.assertEqual(data.ticker, 'GME')
        self.assertEqual(data.shortable_difficulty, 'hard')
        self.assertEqual(data.shortable_shares, 50000)
        self.assertTrue(data.short_squeeze_potential)


class TestSqueezeScore(unittest.TestCase):
    """Test squeeze score calculation (Task 7.4)"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.analyzer = ShortInterestAnalyzer()
    
    def test_calculate_squeeze_score_high(self):
        """Test squeeze score with very low shares"""
        # 50K shares: (1 - 50000/1000000) * 100 = 95
        score = self.analyzer.calculate_squeeze_score(50000)
        self.assertEqual(score, 95.0)
    
    def test_calculate_squeeze_score_medium(self):
        """Test squeeze score with medium shares"""
        # 500K shares: (1 - 500000/1000000) * 100 = 50
        score = self.analyzer.calculate_squeeze_score(500000)
        self.assertEqual(score, 50.0)
    
    def test_calculate_squeeze_score_low(self):
        """Test squeeze score with high shares"""
        # 900K shares: (1 - 900000/1000000) * 100 = 10
        score = self.analyzer.calculate_squeeze_score(900000)
        self.assertAlmostEqual(score, 10.0, places=1)
    
    def test_calculate_squeeze_score_zero(self):
        """Test squeeze score with very high shares"""
        # >= 1M shares: score = 0
        score = self.analyzer.calculate_squeeze_score(1000000)
        self.assertEqual(score, 0.0)
        
        score = self.analyzer.calculate_squeeze_score(2000000)
        self.assertEqual(score, 0.0)
    
    def test_calculate_squeeze_score_bounds(self):
        """Test squeeze score is bounded [0, 100]"""
        # Test lower bound
        score = self.analyzer.calculate_squeeze_score(5000000)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 100.0)
        
        # Test upper bound
        score = self.analyzer.calculate_squeeze_score(0)
        self.assertEqual(score, 100.0)


class TestDifficultyChange(unittest.TestCase):
    """Test difficulty change tracking (Task 7.5)"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.analyzer = ShortInterestAnalyzer()
    
    def test_determine_difficulty_change_harder(self):
        """Test difficulty change when getting harder"""
        change = self.analyzer.determine_difficulty_change(
            current=3,
            previous=2
        )
        self.assertEqual(change, 'harder')
    
    def test_determine_difficulty_change_easier(self):
        """Test difficulty change when getting easier"""
        change = self.analyzer.determine_difficulty_change(
            current=1,
            previous=2
        )
        self.assertEqual(change, 'easier')
    
    def test_determine_difficulty_change_unchanged(self):
        """Test difficulty change when unchanged"""
        change = self.analyzer.determine_difficulty_change(
            current=2,
            previous=2
        )
        self.assertEqual(change, 'unchanged')
    
    def test_determine_difficulty_change_no_previous(self):
        """Test difficulty change with no previous data"""
        change = self.analyzer.determine_difficulty_change(
            current=2,
            previous=None
        )
        self.assertEqual(change, 'unchanged')
    
    def test_difficulty_to_string(self):
        """Test difficulty code to string conversion"""
        self.assertEqual(self.analyzer.difficulty_to_string(1), 'easy')
        self.assertEqual(self.analyzer.difficulty_to_string(2), 'moderate')
        self.assertEqual(self.analyzer.difficulty_to_string(3), 'hard')
        self.assertEqual(self.analyzer.difficulty_to_string(4), 'unavailable')


class TestSqueezePotential(unittest.TestCase):
    """Test short squeeze potential detection (Task 7.6)"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.analyzer = ShortInterestAnalyzer()
    
    def test_detect_squeeze_potential_true(self):
        """Test squeeze potential when conditions met"""
        # Low shares + rising price
        potential = self.analyzer.detect_squeeze_potential(
            shortable_shares=50000,
            price_trend='rising'
        )
        self.assertTrue(potential)
    
    def test_detect_squeeze_potential_high_shares(self):
        """Test squeeze potential with high shares"""
        # High shares + rising price
        potential = self.analyzer.detect_squeeze_potential(
            shortable_shares=200000,
            price_trend='rising'
        )
        self.assertFalse(potential)
    
    def test_detect_squeeze_potential_not_rising(self):
        """Test squeeze potential without rising price"""
        # Low shares + falling price
        potential = self.analyzer.detect_squeeze_potential(
            shortable_shares=50000,
            price_trend='falling'
        )
        self.assertFalse(potential)
        
        # Low shares + flat price
        potential = self.analyzer.detect_squeeze_potential(
            shortable_shares=50000,
            price_trend='flat'
        )
        self.assertFalse(potential)


class TestShortInterestIntegration(unittest.TestCase):
    """Integration tests for short interest analysis"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.analyzer = ShortInterestAnalyzer()
    
    def test_complete_workflow_squeeze(self):
        """Test complete workflow with squeeze potential"""
        data = self.analyzer.analyze_short_interest(
            ticker='GME',
            shortable_difficulty=3,
            shortable_shares=50000,
            previous_difficulty=2,
            price_trend='rising'
        )
        
        # Should detect squeeze
        self.assertTrue(data.short_squeeze_potential)
        self.assertEqual(data.shortable_difficulty, 'hard')
        self.assertEqual(data.difficulty_change, 'harder')
        self.assertEqual(data.squeeze_score, 95.0)
        self.assertTrue(data.is_significant())
    
    def test_complete_workflow_no_squeeze(self):
        """Test complete workflow without squeeze potential"""
        data = self.analyzer.analyze_short_interest(
            ticker='AAPL',
            shortable_difficulty=1,
            shortable_shares=500000,
            previous_difficulty=1,
            price_trend='flat'
        )
        
        # Should not detect squeeze
        self.assertFalse(data.short_squeeze_potential)
        self.assertEqual(data.shortable_difficulty, 'easy')
        self.assertEqual(data.difficulty_change, 'unchanged')
        self.assertEqual(data.squeeze_score, 50.0)
    
    def test_difficulty_history_tracking(self):
        """Test difficulty history tracking"""
        # First analysis
        self.analyzer.analyze_short_interest(
            ticker='GME',
            shortable_difficulty=1,
            shortable_shares=500000,
            price_trend='flat'
        )
        
        # Second analysis (should use history)
        data = self.analyzer.analyze_short_interest(
            ticker='GME',
            shortable_difficulty=3,
            shortable_shares=50000,
            price_trend='rising'
        )
        
        # Should detect difficulty change
        self.assertEqual(data.difficulty_change, 'harder')
        
        # Check history
        history = self.analyzer.get_difficulty_history('GME')
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0], 1)
        self.assertEqual(history[1], 3)


class TestShortInterestValidation(unittest.TestCase):
    """Test input validation and error handling"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.analyzer = ShortInterestAnalyzer()
    
    def test_invalid_ticker(self):
        """Test that empty ticker raises ValueError"""
        with self.assertRaises(ValueError):
            self.analyzer.analyze_short_interest(
                ticker='',
                shortable_difficulty=2,
                shortable_shares=100000,
                price_trend='flat'
            )
    
    def test_invalid_difficulty(self):
        """Test that invalid difficulty raises ValueError"""
        with self.assertRaises(ValueError):
            self.analyzer.analyze_short_interest(
                ticker='GME',
                shortable_difficulty=5,
                shortable_shares=100000,
                price_trend='flat'
            )
    
    def test_invalid_shares(self):
        """Test that negative shares raise ValueError"""
        with self.assertRaises(ValueError):
            self.analyzer.analyze_short_interest(
                ticker='GME',
                shortable_difficulty=2,
                shortable_shares=-1000,
                price_trend='flat'
            )
    
    def test_invalid_price_trend(self):
        """Test that invalid price trend raises ValueError"""
        with self.assertRaises(ValueError):
            self.analyzer.analyze_short_interest(
                ticker='GME',
                shortable_difficulty=2,
                shortable_shares=100000,
                price_trend='invalid'
            )


if __name__ == '__main__':
    unittest.main(verbosity=2)
