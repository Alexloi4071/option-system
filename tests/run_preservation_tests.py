#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Simple test runner for preservation tests
Runs tests without pytest.main() to avoid version conflicts
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from test_preservation_core_behaviors import (
    TestPreservation_IBKRDataPriority,
    TestPreservation_AutonomousCalculations,
    TestPreservation_IVNormalizer,
    TestPreservation_ExponentialBackoff,
    TestPreservation_APIFailureRecordLimit,
    TestPreservation_TickerValidation,
    TestPreservation_ManualInputMode,
    TestPreservation_GenericTickTags,
    TestPreservation_MarketDataTypeSwitching,
    TestPreservation_CacheMechanism,
    TestPreservation_RateLimitCompliance,
    TestPreservation_CompleteReportGeneration,
    TestPreservation_DataSourceSummary,
    TestPreservation_ValidAPIKeys,
)


def run_test_class(test_class, class_name):
    """Run all test methods in a test class"""
    print(f"\n{'='*80}")
    print(f"Running {class_name}")
    print(f"{'='*80}")
    
    instance = test_class()
    test_methods = [m for m in dir(instance) if m.startswith('test_')]
    
    passed = 0
    failed = 0
    skipped = 0
    
    for method_name in test_methods:
        try:
            print(f"\n  Running {method_name}...")
            method = getattr(instance, method_name)
            method()
            print(f"  ✓ PASSED: {method_name}")
            passed += 1
        except Exception as e:
            if "skip" in str(e).lower():
                print(f"  ⊘ SKIPPED: {method_name} - {str(e)}")
                skipped += 1
            else:
                print(f"  ✗ FAILED: {method_name}")
                print(f"    Error: {str(e)}")
                failed += 1
    
    return passed, failed, skipped


def main():
    """Run all preservation tests"""
    print("\n" + "="*80)
    print("PRESERVATION PROPERTY TESTS - CORE SYSTEM BEHAVIORS")
    print("Task 14: Establish baseline behavior to preserve")
    print("="*80)
    print("\nThese tests run on UNFIXED code to document current behavior.")
    print("After fixes, these same tests must PASS to ensure no regressions.\n")
    
    test_classes = [
        (TestPreservation_IBKRDataPriority, "IBKR Data Priority"),
        (TestPreservation_AutonomousCalculations, "Autonomous Calculations"),
        (TestPreservation_IVNormalizer, "IV Normalizer"),
        (TestPreservation_ExponentialBackoff, "Exponential Backoff"),
        (TestPreservation_APIFailureRecordLimit, "API Failure Record Limit"),
        (TestPreservation_TickerValidation, "Ticker Validation"),
        (TestPreservation_ManualInputMode, "Manual Input Mode"),
        (TestPreservation_GenericTickTags, "Generic Tick Tags"),
        (TestPreservation_MarketDataTypeSwitching, "Market Data Type Switching"),
        (TestPreservation_CacheMechanism, "Cache Mechanism"),
        (TestPreservation_RateLimitCompliance, "Rate Limit Compliance"),
        (TestPreservation_CompleteReportGeneration, "Complete Report Generation"),
        (TestPreservation_DataSourceSummary, "Data Source Summary"),
        (TestPreservation_ValidAPIKeys, "Valid API Keys"),
    ]
    
    total_passed = 0
    total_failed = 0
    total_skipped = 0
    
    for test_class, class_name in test_classes:
        passed, failed, skipped = run_test_class(test_class, class_name)
        total_passed += passed
        total_failed += failed
        total_skipped += skipped
    
    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"\nTotal tests run: {total_passed + total_failed + total_skipped}")
    print(f"  ✓ Passed:  {total_passed}")
    print(f"  ✗ Failed:  {total_failed}")
    print(f"  ⊘ Skipped: {total_skipped}")
    
    if total_failed == 0:
        print(f"\n✓ ALL PRESERVATION TESTS PASSED!")
        print(f"  Baseline behavior documented successfully.")
        print(f"  After fixes, these tests must continue to pass.")
    else:
        print(f"\n⚠ Some tests failed - review failures above")
    
    print("="*80 + "\n")
    
    return 0 if total_failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
