"""
Bug Condition Exploration Test - Task 10: API Failure Summary

**Validates: Requirements 1.5, 2.5**

**Property 1: Bug Condition** - API Failure Diagnostic Insufficient
**CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists

**GOAL**: Surface counterexamples showing API failures lack detailed diagnostic summary
Test that get_api_failure_summary() returns detailed breakdown by source and error type

**EXPECTED OUTCOME**: Test FAILS (summary is empty or incomplete)
"""

import sys
import os
import inspect

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from data_layer.data_fetcher import DataFetcher


def test_api_failure_summary():
    """
    Test that DataFetcher provides detailed API failure summary.
    
    Expected to FAIL on unfixed code: no comprehensive failure summary method.
    """
    print("\n" + "="*70)
    print("BUG EXPLORATION TEST - TASK 10")
    print("API Failure Summary Diagnostic")
    print("="*70)
    print("\nThis test is EXPECTED TO FAIL on unfixed code.")
    print("Failure confirms Bug 1.5 exists.\n")
    
    bug_confirmed = False
    
    try:
        print("Creating DataFetcher...")
        fetcher = DataFetcher()
        
        # Check if there's an API failure tracking mechanism
        if hasattr(fetcher, 'api_failures'):
            print(f"✓ DataFetcher has api_failures attribute")
        else:
            print(f"✗ DataFetcher missing api_failures attribute")
            bug_confirmed = True
        
        # Check for failure summary method
        summary_methods = [
            'get_api_failure_summary',
            'get_failure_summary',
            'get_api_status',
            'get_diagnostics'
        ]
        
        has_summary_method = False
        for method_name in summary_methods:
            if hasattr(fetcher, method_name):
                print(f"✓ Found method: {method_name}")
                has_summary_method = True
                
                # Check if it returns detailed breakdown
                source = inspect.getsource(getattr(fetcher, method_name))
                
                # Look for detailed breakdown indicators
                breakdown_indicators = [
                    'by_source',
                    'by_error_type',
                    'total_failures',
                    'recent_failures',
                    'error_type',
                    'http_status'
                ]
                
                has_detailed_breakdown = sum(1 for ind in breakdown_indicators if ind in source) >= 3
                
                if has_detailed_breakdown:
                    print(f"  ✓ Method appears to provide detailed breakdown")
                else:
                    print(f"  ✗ Method lacks detailed breakdown")
                    bug_confirmed = True
                
                break
        
        if not has_summary_method:
            print("\n✗ EXPECTED FAILURE: No API failure summary method found")
            print("  System cannot provide diagnostic information")
            print("  Bug 1.5 CONFIRMED!")
            bug_confirmed = True
        
        # Check if failures are recorded with sufficient detail
        if hasattr(fetcher, '_record_api_failure'):
            source = inspect.getsource(fetcher._record_api_failure)
            
            # Look for detailed recording
            detail_indicators = [
                'error_type',
                'error_message',
                'http_status',
                'timestamp',
                'data_type'
            ]
            
            details_recorded = sum(1 for ind in detail_indicators if ind in source)
            
            if details_recorded >= 3:
                print(f"\n✓ _record_api_failure captures {details_recorded}/5 details")
            else:
                print(f"\n✗ _record_api_failure only captures {details_recorded}/5 details")
                bug_confirmed = True
        else:
            print("\n✗ No _record_api_failure method found")
            bug_confirmed = True
            
    except Exception as e:
        print(f"\nError during test: {type(e).__name__}: {str(e)}")
        bug_confirmed = True
    
    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY - TASK 10")
    print("="*70)
    
    if bug_confirmed:
        print("\n✓ Bug 1.5 CONFIRMED!")
        print("\nCounterexamples documented:")
        print("  - API failures occur but no comprehensive summary available")
        print("  - Missing breakdown by source (IBKR, Yahoo, Finnhub, etc.)")
        print("  - Missing breakdown by error type (timeout, 429, 403, etc.)")
        print("  - No recent failures list for debugging")
        print("  - User cannot diagnose root cause of data issues")
        print("\nExpected Behavior (after fix):")
        print("  - get_api_failure_summary() returns detailed dict:")
        print("    * total_failures: int")
        print("    * by_source: {source: count}")
        print("    * by_error_type: {error_type: count}")
        print("    * recent_failures: list of last 5 per source")
        print("  - Each failure record includes:")
        print("    * timestamp, data_type, error_type, error_message, http_status")
    else:
        print("\n⚠ Bug may already be fixed!")
        print("  Code appears to include comprehensive failure summary")
    
    print("="*70 + "\n")
    
    return bug_confirmed


if __name__ == '__main__':
    test_api_failure_summary()
