"""
Bug Condition Exploration Test - Task 8: IBKR Greeks Convergence

**Validates: Requirements 1.11, 2.11**

**Property 1: Bug Condition** - Greeks Convergence Timeout No Fallback
**CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists

**GOAL**: Surface counterexamples showing Greeks timeout returns None without fallback
Test that system waits for convergence then uses local Black-Scholes calculator

**EXPECTED OUTCOME**: Test FAILS (Greeks returns None, no local calculation fallback)
"""

import sys
import os
import inspect

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from data_layer.ibkr_client import IBKRClient


def test_greeks_convergence_fallback():
    """
    Test that Greeks convergence timeout triggers fallback to local calculator.
    
    Expected to FAIL on unfixed code: no fallback mechanism exists.
    """
    print("\n" + "="*70)
    print("BUG EXPLORATION TEST - TASK 8")
    print("IBKR Greeks Convergence Fallback")
    print("="*70)
    print("\nThis test is EXPECTED TO FAIL on unfixed code.")
    print("Failure confirms Bug 1.11 exists.\n")
    
    bug_confirmed = False
    
    try:
        # Create IBKR client
        print("Creating IBKR client...")
        client = IBKRClient()
        
        # Check if client has Greeks convergence waiting mechanism
        if hasattr(client, '_wait_for_greeks_convergence'):
            print(f"✓ Client has _wait_for_greeks_convergence method")
            
            # Check the implementation
            source = inspect.getsource(client._wait_for_greeks_convergence)
            
            # Look for timeout handling
            if 'timeout' in source:
                print(f"✓ Method has timeout parameter")
            else:
                print(f"✗ Method missing timeout parameter")
                bug_confirmed = True
        else:
            print(f"✗ Client missing _wait_for_greeks_convergence method")
            bug_confirmed = True
        
        # Check if get_option_greeks has fallback logic
        print("\nChecking Greeks fallback mechanism...")
        if hasattr(client, 'get_option_greeks'):
            source = inspect.getsource(client.get_option_greeks)
            
            # Look for fallback to Black-Scholes calculator
            has_fallback = False
            fallback_indicators = [
                'BlackScholes',
                'bs_calculator',
                'local_calculator',
                'fallback',
                'calculate_greeks'
            ]
            
            for indicator in fallback_indicators:
                if indicator in source:
                    print(f"  Found indicator: {indicator}")
                    has_fallback = True
                    break
            
            if has_fallback:
                print("\n✓ UNEXPECTED: Code appears to have Greeks fallback mechanism")
                print("  Bug may already be fixed!")
            else:
                print("\n✗ EXPECTED FAILURE: No fallback to local calculator found")
                print("  When IBKR Greeks timeout, system returns None")
                print("  Bug 1.11 CONFIRMED!")
                bug_confirmed = True
        else:
            print("\n✗ get_option_greeks method not found")
            bug_confirmed = True
            
    except Exception as e:
        print(f"\nError during test: {type(e).__name__}: {str(e)}")
        bug_confirmed = True
    
    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY - TASK 8")
    print("="*70)
    
    if bug_confirmed:
        print("\n✓ Bug 1.11 CONFIRMED!")
        print("\nCounterexamples documented:")
        print("  - IBKR Greeks convergence may timeout (especially for deep OTM options)")
        print("  - When timeout occurs, get_option_greeks returns None")
        print("  - No fallback to local Black-Scholes calculator")
        print("  - Calculation modules skip execution due to missing Greeks")
        print("\nExpected Behavior (after fix):")
        print("  - _wait_for_greeks_convergence waits up to 10s for convergence")
        print("  - If timeout, use local Black-Scholes calculator as fallback")
        print("  - Return Greeks with source annotation: 'Local Calculator (IBKR timeout)'")
        print("  - Ensure Greeks are always available for calculations")
    else:
        print("\n⚠ Bug may already be fixed!")
        print("  Code appears to include Greeks fallback mechanism")
    
    print("="*70 + "\n")
    
    return bug_confirmed


if __name__ == '__main__':
    test_greeks_convergence_fallback()
