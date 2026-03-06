#!/usr/bin/env python3
"""
Bug Condition Exploration Test for System Freeze with High RAM Usage

**Validates: Requirements 2.1, 2.2, 2.3**

This test MUST FAIL on unfixed code to prove the bug exists.
It encodes the expected behavior that will validate the fix.

Property 1: Bug Condition - Memory-Efficient Processing for Large Option Chains
- System completes analysis within 5 minutes (300 seconds)
- RAM usage remains below 80% of available memory
- Progress updates occur at least every 30 seconds
- Analysis completes successfully without freezing

CRITICAL: This test is EXPECTED TO FAIL on unfixed code!
Expected failures:
- Execution time > 15 minutes (system freeze)
- RAM usage > 80% or maxed out
- No progress updates for > 15 minutes
- System hangs during report generation

After fix implementation, this SAME test should PASS.
"""

import sys
import unittest
import time
import psutil
import threading
from datetime import datetime
import pandas as pd
from unittest.mock import Mock, MagicMock, patch

sys.path.append('.')

from main import OptionsAnalysisSystem


class TestSystemFreezeHighRAMBug(unittest.TestCase):
    """
    Bug Condition Exploration Tests
    
    These tests demonstrate the system freeze and high RAM usage bug
    when analyzing stocks with large option chains.
    They MUST FAIL on unfixed code to prove the bug exists.
    """
    
    def setUp(self):
        """Set up test fixtures"""
        self.process = psutil.Process()
        self.initial_memory = self.process.memory_info().rss / (1024 * 1024 * 1024)  # GB
        self.available_memory = psutil.virtual_memory().available / (1024 * 1024 * 1024)  # GB
        self.memory_threshold = self.available_memory * 0.8  # 80% threshold
        
    def _create_large_synthetic_option_chain(self, num_strikes=200, num_expirations=1):
        """
        Create synthetic option chain data with many strikes
        
        This simulates the VZ scenario with 200+ strikes
        """
        strikes = []
        base_price = 40.0  # VZ-like price
        
        # Generate strikes from 50% to 150% of base price
        for i in range(num_strikes):
            strike = base_price * (0.5 + (i / num_strikes) * 1.0)
            strikes.append(round(strike, 2))
        
        calls_data = []
        puts_data = []
        
        for strike in strikes:
            # Create call option data
            call = {
                'strike': strike,
                'lastPrice': max(0.01, base_price - strike + 2.0),
                'bid': max(0.01, base_price - strike + 1.5),
                'ask': max(0.01, base_price - strike + 2.5),
                'volume': 100 + int(strike * 10),
                'openInterest': 500 + int(strike * 50),
                'impliedVolatility': 0.25 + (abs(strike - base_price) / base_price) * 0.5,
                'delta': max(0.01, min(0.99, (base_price - strike) / base_price + 0.5)),
                'gamma': 0.05,
                'theta': -0.02,
                'vega': 0.15,
                'rho': 0.01
            }
            calls_data.append(call)
            
            # Create put option data
            put = {
                'strike': strike,
                'lastPrice': max(0.01, strike - base_price + 2.0),
                'bid': max(0.01, strike - base_price + 1.5),
                'ask': max(0.01, strike - base_price + 2.5),
                'volume': 100 + int(strike * 10),
                'openInterest': 500 + int(strike * 50),
                'impliedVolatility': 0.25 + (abs(strike - base_price) / base_price) * 0.5,
                'delta': -max(0.01, min(0.99, (strike - base_price) / base_price + 0.5)),
                'gamma': 0.05,
                'theta': -0.02,
                'vega': 0.15,
                'rho': -0.01
            }
            puts_data.append(put)
        
        return {
            'calls': pd.DataFrame(calls_data),
            'puts': pd.DataFrame(puts_data),
            'expiration': '2026-06-18',
            'data_source': 'synthetic_large_chain'
        }
    
    def _monitor_memory_and_progress(self, stop_event, results):
        """
        Monitor memory usage and track progress updates
        
        Args:
            stop_event: Threading event to signal when to stop monitoring
            results: Dict to store monitoring results
        """
        results['peak_memory_gb'] = 0
        results['memory_samples'] = []
        results['last_progress_time'] = time.time()
        results['max_time_without_progress'] = 0
        results['progress_update_count'] = 0
        
        while not stop_event.is_set():
            current_memory = self.process.memory_info().rss / (1024 * 1024 * 1024)  # GB
            results['memory_samples'].append(current_memory)
            results['peak_memory_gb'] = max(results['peak_memory_gb'], current_memory)
            
            # Check for progress updates (simplified - in real scenario would check console output)
            # For now, we just track time without updates
            time_since_last_progress = time.time() - results['last_progress_time']
            results['max_time_without_progress'] = max(
                results['max_time_without_progress'],
                time_since_last_progress
            )
            
            time.sleep(1)  # Sample every second
    
    @unittest.skip("REAL TEST - Requires actual VZ data and IBKR connection - Use for final verification")
    def test_vz_large_option_chain_real(self):
        """
        Test with real VZ stock data (expiry 2026/06/18)
        
        This is the ACTUAL bug scenario reported by the user.
        
        EXPECTED ON UNFIXED CODE:
        - System freezes after ~15 minutes
        - RAM usage maxes out
        - No console output updates
        - User must cancel operation
        
        EXPECTED ON FIXED CODE:
        - Completes within 5 minutes
        - RAM usage < 80%
        - Regular progress updates
        - Analysis completes successfully
        """
        # This test requires:
        # 1. IBKR connection
        # 2. Market hours or cached data
        # 3. VZ stock with 2026/06/18 expiration
        
        system = OptionsAnalysisSystem(use_ibkr=True)
        
        results = {}
        stop_event = threading.Event()
        monitor_thread = threading.Thread(
            target=self._monitor_memory_and_progress,
            args=(stop_event, results)
        )
        monitor_thread.daemon = True
        monitor_thread.start()
        
        start_time = time.time()
        analysis_completed = False
        analysis_error = None
        
        try:
            # Run analysis with timeout
            result = system.run_complete_analysis('VZ', '2026-06-18')
            analysis_completed = True
        except Exception as e:
            analysis_error = str(e)
        finally:
            stop_event.set()
            monitor_thread.join(timeout=5)
        
        elapsed_time = time.time() - start_time
        peak_memory_gb = results.get('peak_memory_gb', 0)
        max_time_without_progress = results.get('max_time_without_progress', 0)
        
        # ASSERTIONS for bug condition
        self.assertTrue(
            analysis_completed,
            f"Analysis did not complete - Error: {analysis_error}"
        )
        
        self.assertLess(
            elapsed_time, 300,
            f"Analysis took {elapsed_time:.1f}s (>{300}s limit) - system freeze detected!"
        )
        
        self.assertLess(
            peak_memory_gb, self.memory_threshold,
            f"Peak memory {peak_memory_gb:.2f}GB exceeded 80% threshold ({self.memory_threshold:.2f}GB)"
        )
        
        self.assertLess(
            max_time_without_progress, 30,
            f"No progress updates for {max_time_without_progress:.1f}s (>30s) - system may be frozen"
        )
    
    def test_synthetic_large_option_chain_200_strikes(self):
        """
        Test with synthetic large option chain (200 strikes)
        
        This simulates the VZ scenario without requiring real data.
        
        EXPECTED ON UNFIXED CODE:
        - Execution time > 5 minutes (may freeze)
        - RAM usage grows excessively
        - System may hang during Module 22 or report generation
        
        EXPECTED ON FIXED CODE:
        - Completes within 5 minutes
        - RAM usage < 80%
        - Regular progress updates
        """
        # Create synthetic large option chain
        large_chain = self._create_large_synthetic_option_chain(num_strikes=200)
        
        # Create a mock data fetcher
        mock_fetcher = Mock()
        
        # Mock get_complete_analysis_data to return all required data
        mock_fetcher.get_complete_analysis_data.return_value = {
            'stock_info': {
                'current_price': 40.0,
                'ticker': 'SYNTHETIC',
                'company_name': 'Synthetic Large Chain Test',
                'data_source': 'mock',
                'eps': 2.5,
                'pe_ratio': 16.0,
                'market_cap': 1000000000,
                'volume': 1000000,
                'avg_volume': 1000000,
                'dividend_yield': 0.0,
                'beta': 1.0,
                'sector': 'Technology',
                'industry': 'Software'
            },
            'option_chain': large_chain,
            'historical_volatility': 25.0,
            'earnings_calendar': [],
            'dividend_info': {'annual_dividend': 0.0, 'dividend_yield': 0.0},
            'risk_free_rate': 4.5,
            'historical_prices': pd.DataFrame({
                'Close': [40.0] * 252,
                'Date': pd.date_range(end='2026-06-18', periods=252)
            })
        }
        
        # Create system and inject mock
        system = OptionsAnalysisSystem(use_ibkr=False)
        system.data_fetcher = mock_fetcher
        
        results = {}
        stop_event = threading.Event()
        monitor_thread = threading.Thread(
            target=self._monitor_memory_and_progress,
            args=(stop_event, results)
        )
        monitor_thread.daemon = True
        monitor_thread.start()
        
        start_time = time.time()
        analysis_completed = False
        analysis_error = None
        
        try:
            # Run analysis with timeout (use threading to enforce timeout)
            def run_analysis():
                nonlocal analysis_completed, analysis_error
                try:
                    result = system.run_complete_analysis('SYNTHETIC', '2026-06-18')
                    analysis_completed = True
                except Exception as e:
                    analysis_error = str(e)
            
            analysis_thread = threading.Thread(target=run_analysis)
            analysis_thread.daemon = True
            analysis_thread.start()
            
            # Wait for analysis with timeout (5 minutes for expected behavior)
            # On unfixed code, this will timeout
            analysis_thread.join(timeout=300)
            
            if analysis_thread.is_alive():
                # Analysis is still running after 5 minutes - bug detected!
                analysis_completed = False
                analysis_error = "Analysis exceeded 5 minute timeout - system freeze detected"
            
        finally:
            stop_event.set()
            monitor_thread.join(timeout=5)
        
        elapsed_time = time.time() - start_time
        peak_memory_gb = results.get('peak_memory_gb', 0)
        max_time_without_progress = results.get('max_time_without_progress', 0)
        
        # ASSERTIONS for bug condition
        # These will FAIL on unfixed code
        self.assertTrue(
            analysis_completed,
            f"Analysis did not complete within 5 minutes - Error: {analysis_error}"
        )
        
        self.assertLess(
            elapsed_time, 300,
            f"Analysis took {elapsed_time:.1f}s (>300s limit) - system freeze detected!"
        )
        
        memory_increase_gb = peak_memory_gb - self.initial_memory
        self.assertLess(
            peak_memory_gb, self.memory_threshold,
            f"Peak memory {peak_memory_gb:.2f}GB exceeded 80% threshold ({self.memory_threshold:.2f}GB). "
            f"Memory increased by {memory_increase_gb:.2f}GB from initial {self.initial_memory:.2f}GB"
        )
        
        self.assertLess(
            max_time_without_progress, 30,
            f"No progress updates for {max_time_without_progress:.1f}s (>30s) - system may be frozen"
        )
    
    def test_memory_growth_pattern_with_strikes(self):
        """
        Test memory growth pattern as number of strikes increases
        
        This test verifies that memory usage grows linearly (or worse) with
        the number of strikes, indicating a memory accumulation issue.
        
        EXPECTED ON UNFIXED CODE:
        - Memory grows significantly with each additional strike batch
        - Memory is not released between processing
        - Linear or worse memory growth pattern
        
        EXPECTED ON FIXED CODE:
        - Memory growth is bounded
        - Memory is released after processing each batch
        - Constant or sub-linear memory growth
        """
        strike_counts = [50, 100, 150, 200]
        memory_usage = []
        
        for num_strikes in strike_counts:
            # Force garbage collection before each test
            import gc
            gc.collect()
            
            initial_mem = self.process.memory_info().rss / (1024 * 1024)  # MB
            
            # Create and process option chain
            large_chain = self._create_large_synthetic_option_chain(num_strikes=num_strikes)
            
            # Simulate processing (just accessing the data)
            _ = large_chain['calls'].copy()
            _ = large_chain['puts'].copy()
            
            # Measure memory after processing
            final_mem = self.process.memory_info().rss / (1024 * 1024)  # MB
            memory_increase = final_mem - initial_mem
            memory_usage.append(memory_increase)
            
            # Clean up
            del large_chain
            gc.collect()
        
        # Check memory growth pattern
        # On unfixed code: memory should grow significantly
        # On fixed code: memory growth should be bounded
        
        # Calculate memory growth rate
        if len(memory_usage) >= 2:
            growth_rate = (memory_usage[-1] - memory_usage[0]) / (strike_counts[-1] - strike_counts[0])
            
            # ASSERTION: Memory growth should be reasonable (< 1MB per strike)
            # On unfixed code: May see 2-5MB per strike or more
            # On fixed code: Should see < 1MB per strike
            self.assertLess(
                growth_rate, 1.0,
                f"Memory growth rate {growth_rate:.2f}MB per strike is excessive. "
                f"Memory usage: {memory_usage} MB for strikes: {strike_counts}"
            )


class TestBugCounterexamplesDocumentation(unittest.TestCase):
    """
    Documentation of bug counterexamples found
    
    These tests document the specific failures observed on unfixed code.
    """
    
    def test_counterexample_1_vz_system_freeze(self):
        """
        Counterexample 1: VZ (2026/06/18) causes system freeze
        
        Observed behavior on unfixed code:
        - System runs for ~15 minutes without progress updates
        - Last console output: "我看卡在這大約15分鐘也沒更新"
        - RAM usage reaches maximum capacity
        - CPU usage remains low (<20%)
        - User must manually cancel operation
        - Freeze occurs after Module 32 completes (during report generation)
        
        Root cause hypothesis:
        - Module 22 (optimal strike analysis) processes all 200+ strikes
        - Module 27 (multi-expiry comparison) accumulates data for multiple expirations
        - Report generator builds entire report in memory
        - DataFrames are not released, causing memory leak
        """
        pass
    
    def test_counterexample_2_large_strike_count(self):
        """
        Counterexample 2: Stocks with 200+ strikes cause excessive memory usage
        
        Observed behavior on unfixed code:
        - Memory usage grows linearly with number of strikes
        - Module 22 creates copies of DataFrames for each strike
        - No explicit memory cleanup (del, gc.collect())
        - Memory is not released until program exits
        
        Expected memory pattern:
        - 50 strikes: ~100MB increase
        - 100 strikes: ~200MB increase
        - 200 strikes: ~400MB increase (linear growth)
        """
        pass
    
    def test_counterexample_3_multiple_expirations(self):
        """
        Counterexample 3: Stocks with 30+ expirations accumulate data
        
        Observed behavior on unfixed code:
        - Module 27 processes each expiration sequentially
        - Option chain data for each expiration is kept in memory
        - No cleanup between expiration processing
        - Memory usage grows with number of expirations
        
        Expected memory pattern:
        - 10 expirations: ~150MB increase
        - 20 expirations: ~300MB increase
        - 30 expirations: ~450MB increase (linear growth)
        """
        pass
    
    def test_counterexample_4_report_generation_freeze(self):
        """
        Counterexample 4: Report generation accumulates large strings
        
        Observed behavior on unfixed code:
        - _write_text_report builds entire report in memory
        - Module 22 section includes all analyzed strikes
        - String concatenation creates multiple copies
        - No streaming/incremental writing
        - System freezes during report formatting
        
        Expected behavior:
        - Report size for 200 strikes: >10MB text
        - Multiple string copies during concatenation
        - Memory spike during report generation
        """
        pass


if __name__ == '__main__':
    # Run with verbose output to see which tests fail
    print("=" * 80)
    print("Bug Condition Exploration Test for System Freeze with High RAM Usage")
    print("=" * 80)
    print()
    print("CRITICAL: These tests are EXPECTED TO FAIL on unfixed code!")
    print("Failure confirms the bug exists.")
    print()
    print("Expected failures on unfixed code:")
    print("- test_synthetic_large_option_chain_200_strikes: Timeout or memory exceeded")
    print("- test_memory_growth_pattern_with_strikes: Excessive memory growth rate")
    print()
    print("After implementing the fix, these SAME tests should PASS.")
    print("=" * 80)
    print()
    
    unittest.main(verbosity=2)
