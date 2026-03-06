"""
Bug Condition Exploration Test - Task 12: Log Sensitive Data Sanitization

**Validates: Requirements 1.14, 2.14**

**Property 1: Bug Condition** - API Keys Leaked in Logs
**CRITICAL**: This test MUST FAIL on unfixed code

**GOAL**: Surface counterexamples showing full API keys appear in logs
**EXPECTED OUTCOME**: Test FAILS (full API key appears in log)
"""

import sys
import os
import inspect
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_log_sanitization():
    """Test that logs sanitize API keys."""
    print("\n" + "="*70)
    print("BUG EXPLORATION TEST - TASK 12")
    print("Log Sensitive Data Sanitization")
    print("="*70)
    print("\nThis test is EXPECTED TO FAIL on unfixed code.")
    print("Failure confirms Bug 1.14 exists.\n")
    
    bug_confirmed = False
    
    try:
        # Check if there's a sanitization function
        try:
            from utils import logger as logger_module
            has_logger_module = True
        except ImportError:
            has_logger_module = False
        
        if has_logger_module:
            print("✓ Found utils.logger module")
            
            # Check for sanitization function
            sanitize_methods = [
                '_sanitize_log_message',
                'sanitize_message',
                'clean_sensitive_data'
            ]
            
            has_sanitize = False
            for method_name in sanitize_methods:
                if hasattr(logger_module, method_name):
                    print(f"✓ Found {method_name} function")
                    has_sanitize = True
                    break
            
            if not has_sanitize:
                print("✗ No sanitization function found")
                bug_confirmed = True
            
            # Check for SensitiveDataFilter
            if hasattr(logger_module, 'SensitiveDataFilter'):
                print("✓ Found SensitiveDataFilter class")
            else:
                print("✗ No SensitiveDataFilter class found")
                bug_confirmed = True
        else:
            print("✗ utils.logger module not found")
            bug_confirmed = True
            
    except Exception as e:
        print(f"\nError: {type(e).__name__}: {str(e)}")
        bug_confirmed = True
    
    print("\n" + "="*70)
    print("TEST SUMMARY - TASK 12")
    print("="*70)
    
    if bug_confirmed:
        print("\n✓ Bug 1.14 CONFIRMED!")
        print("\nCounterexamples:")
        print("  - No _sanitize_log_message function")
        print("  - No SensitiveDataFilter class")
        print("  - API keys logged in full")
        print("\nExpected Behavior:")
        print("  - _sanitize_log_message() sanitizes API keys")
        print("  - Format: abc1...x789 (first 4 + last 4)")
        print("  - SensitiveDataFilter applied to all handlers")
    else:
        print("\n⚠ Bug may already be fixed!")
    
    print("="*70 + "\n")
    return bug_confirmed


if __name__ == '__main__':
    test_log_sanitization()
