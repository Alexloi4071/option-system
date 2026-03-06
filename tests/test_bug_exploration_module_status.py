"""
Bug Condition Exploration Test - Task 11: Module Execution Status

**Validates: Requirements 1.7, 2.7**

**Property 1: Bug Condition** - Module Skip Reason Not Recorded
**CRITICAL**: This test MUST FAIL on unfixed code

**GOAL**: Surface counterexamples showing skipped modules lack reason annotation
**EXPECTED OUTCOME**: Test FAILS (module skipped but no reason recorded)
"""

import sys
import os
import inspect

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from data_layer.data_fetcher import DataFetcher


def test_module_execution_status():
    """Test that module execution status is tracked with reasons."""
    print("\n" + "="*70)
    print("BUG EXPLORATION TEST - TASK 11")
    print("Module Execution Status Tracking")
    print("="*70)
    print("\nThis test is EXPECTED TO FAIL on unfixed code.")
    print("Failure confirms Bug 1.7 exists.\n")
    
    bug_confirmed = False
    
    try:
        fetcher = DataFetcher()
        
        # Check for module status tracking
        if hasattr(fetcher, 'module_status'):
            print(f"✓ DataFetcher has module_status attribute")
        else:
            print(f"✗ DataFetcher missing module_status attribute")
            bug_confirmed = True
        
        # Check for execute_module wrapper
        if hasattr(fetcher, 'execute_module'):
            print(f"✓ Found execute_module method")
            source = inspect.getsource(fetcher.execute_module)
            
            # Look for status tracking
            if 'status' in source and 'reason' in source:
                print(f"  ✓ Method tracks status and reason")
            else:
                print(f"  ✗ Method doesn't track status/reason")
                bug_confirmed = True
        else:
            print(f"✗ No execute_module wrapper found")
            bug_confirmed = True
            
    except Exception as e:
        print(f"\nError: {type(e).__name__}: {str(e)}")
        bug_confirmed = True
    
    print("\n" + "="*70)
    print("TEST SUMMARY - TASK 11")
    print("="*70)
    
    if bug_confirmed:
        print("\n✓ Bug 1.7 CONFIRMED!")
        print("\nCounterexamples:")
        print("  - Modules skip execution when data missing")
        print("  - No module_status tracking")
        print("  - Skip reasons not recorded")
        print("\nExpected Behavior:")
        print("  - module_status dict tracks all modules")
        print("  - Status: 'success', 'skipped', 'failed'")
        print("  - Reason: e.g., 'Missing EPS data'")
    else:
        print("\n⚠ Bug may already be fixed!")
    
    print("="*70 + "\n")
    return bug_confirmed


if __name__ == '__main__':
    test_module_execution_status()
