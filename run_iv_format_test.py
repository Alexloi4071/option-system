"""
Simple test runner for IV format bug exploration test
"""

import sys
import os

# Add current directory and tests directory to path
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tests'))

from test_bug_exploration_iv_format import TestBugExplorationIVFormatConsistency

def run_test():
    """Run the bug exploration test"""
    print("="*80)
    print("Running Bug Exploration Test: IV Format Consistency")
    print("="*80)
    print()
    
    test_instance = TestBugExplorationIVFormatConsistency()
    test_instance.setup_method()
    
    try:
        # Run the main bug condition test
        print("Running: test_bug_condition_iv_format_inconsistency")
        print("-"*80)
        test_instance.test_bug_condition_iv_format_inconsistency()
        print("\n✓ TEST PASSED: Bug was NOT detected (system may already be fixed)")
        return 0
    except AssertionError as e:
        print(f"\n❌ TEST FAILED (EXPECTED): {str(e)}")
        print("\nThis failure CONFIRMS the bug exists!")
        return 1
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return 2

if __name__ == '__main__':
    exit_code = run_test()
    sys.exit(exit_code)
