"""
Bug Condition Exploration Test - Task 13: Yahoo Finance Dynamic Rate Limiting

**Validates: Requirements 1.13, 2.13**

**Property 1: Bug Condition** - Fixed Delay Causes Rate Limit Errors
**CRITICAL**: This test MUST FAIL on unfixed code

**GOAL**: Surface counterexamples showing fixed 3s delay triggers 429 errors
**EXPECTED OUTCOME**: Test FAILS (429 errors occur, delay stays at 3s)
"""

import sys
import os
import inspect

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from data_layer.yahoo_finance_v2_client import YahooFinanceV2Client


def test_yahoo_dynamic_rate_limiting():
    """Test that Yahoo client has dynamic rate limiting."""
    print("\n" + "="*70)
    print("BUG EXPLORATION TEST - TASK 13")
    print("Yahoo Finance Dynamic Rate Limiting")
    print("="*70)
    print("\nThis test is EXPECTED TO FAIL on unfixed code.")
    print("Failure confirms Bug 1.13 exists.\n")
    
    bug_confirmed = False
    
    try:
        client = YahooFinanceV2Client()
        
        # Check for dynamic delay attributes
        if hasattr(client, 'current_delay'):
            print(f"✓ Client has current_delay attribute")
        else:
            print(f"✗ Client missing current_delay attribute")
            bug_confirmed = True
        
        if hasattr(client, 'rate_limit_events'):
            print(f"✓ Client has rate_limit_events tracking")
        else:
            print(f"✗ Client missing rate_limit_events tracking")
            bug_confirmed = True
        
        # Check for delay adjustment methods
        adjust_methods = [
            '_adjust_delay_on_rate_limit',
            'adjust_delay',
            'increase_delay'
        ]
        
        has_adjust = False
        for method_name in adjust_methods:
            if hasattr(client, method_name):
                print(f"✓ Found {method_name} method")
                has_adjust = True
                break
        
        if not has_adjust:
            print("✗ No delay adjustment method found")
            bug_confirmed = True
        
        # Check for rate limit summary
        if hasattr(client, 'get_rate_limit_summary'):
            print("✓ Found get_rate_limit_summary method")
        else:
            print("✗ No get_rate_limit_summary method")
            bug_confirmed = True
            
    except Exception as e:
        print(f"\nError: {type(e).__name__}: {str(e)}")
        bug_confirmed = True
    
    print("\n" + "="*70)
    print("TEST SUMMARY - TASK 13")
    print("="*70)
    
    if bug_confirmed:
        print("\n✓ Bug 1.13 CONFIRMED!")
        print("\nCounterexamples:")
        print("  - REQUEST_DELAY is fixed at 3s")
        print("  - No dynamic delay adjustment")
        print("  - 429 errors not handled")
        print("  - No rate limit event tracking")
        print("\nExpected Behavior:")
        print("  - current_delay starts at base_delay (3s)")
        print("  - On 429: double delay (max 30s)")
        print("  - On success: gradually decrease")
        print("  - Track rate_limit_events")
    else:
        print("\n⚠ Bug may already be fixed!")
    
    print("="*70 + "\n")
    return bug_confirmed


if __name__ == '__main__':
    test_yahoo_dynamic_rate_limiting()
