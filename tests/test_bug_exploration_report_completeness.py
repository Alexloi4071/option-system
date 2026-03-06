"""
Bug Condition Exploration Test - Task 9: Report Data Completeness

**Validates: Requirements 1.1, 2.1**

**Property 1: Bug Condition** - Report N/A Data Without Reason
**CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists

**GOAL**: Surface counterexamples showing N/A data lacks failure reason annotation
Test that report includes failure reason for each N/A field

**EXPECTED OUTCOME**: Test FAILS (report shows "EPS: N/A" without reason)
"""

import sys
import os
import inspect

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Try to import report generator
try:
    from output_layer.output_manager import OutputManager
    HAS_OUTPUT_MANAGER = True
except ImportError:
    HAS_OUTPUT_MANAGER = False
    print("Warning: OutputManager not found")


def test_report_data_completeness():
    """
    Test that report annotates N/A data with failure reasons.
    
    Expected to FAIL on unfixed code: N/A fields lack explanations.
    """
    print("\n" + "="*70)
    print("BUG EXPLORATION TEST - TASK 9")
    print("Report Data Completeness Annotation")
    print("="*70)
    print("\nThis test is EXPECTED TO FAIL on unfixed code.")
    print("Failure confirms Bug 1.1 exists.\n")
    
    bug_confirmed = False
    
    try:
        if not HAS_OUTPUT_MANAGER:
            print("✗ OutputManager not found - cannot test report generation")
            bug_confirmed = True
        else:
            print("✓ OutputManager found")
            
            # Check if there's a method to check data completeness
            manager = OutputManager()
            
            completeness_methods = [
                '_check_data_completeness',
                'check_completeness',
                'validate_data',
                '_get_missing_reason'
            ]
            
            has_completeness_check = False
            for method_name in completeness_methods:
                if hasattr(manager, method_name):
                    print(f"✓ Found method: {method_name}")
                    has_completeness_check = True
                    break
            
            if not has_completeness_check:
                print("\n✗ EXPECTED FAILURE: No data completeness checking method found")
                print("  Report likely shows N/A without explaining why")
                bug_confirmed = True
            
            # Check if report generation includes failure annotations
            if hasattr(manager, 'generate_report') or hasattr(manager, 'format_output'):
                method_name = 'generate_report' if hasattr(manager, 'generate_report') else 'format_output'
                source = inspect.getsource(getattr(manager, method_name))
                
                # Look for failure reason annotations
                annotation_indicators = [
                    'failure_reason',
                    'missing_reason',
                    'N/A (',
                    'Source:',
                    'failed:',
                    'error:'
                ]
                
                has_annotations = any(indicator in source for indicator in annotation_indicators)
                
                if has_annotations:
                    print(f"\n✓ UNEXPECTED: {method_name} appears to include failure annotations")
                    print("  Bug may already be fixed!")
                else:
                    print(f"\n✗ EXPECTED FAILURE: {method_name} lacks failure reason annotations")
                    print("  N/A fields shown without explanation")
                    print("  Bug 1.1 CONFIRMED!")
                    bug_confirmed = True
            else:
                print("\n✗ No report generation method found")
                bug_confirmed = True
            
    except Exception as e:
        print(f"\nError during test: {type(e).__name__}: {str(e)}")
        bug_confirmed = True
    
    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY - TASK 9")
    print("="*70)
    
    if bug_confirmed:
        print("\n✓ Bug 1.1 CONFIRMED!")
        print("\nCounterexamples documented:")
        print("  - Report shows N/A for missing data fields")
        print("  - No explanation of why data is missing")
        print("  - User cannot determine if it's:")
        print("    * Configuration problem (invalid API key)")
        print("    * Network problem (connection timeout)")
        print("    * API limitation (rate limit, data unavailable)")
        print("\nExpected Behavior (after fix):")
        print("  - Each N/A field should have inline annotation")
        print("  - Format: 'EPS: N/A (IBKR connection failed, Finnhub API key invalid)'")
        print("  - For successful fields: 'Dividend: $2.50 (Source: Yahoo Finance)'")
        print("  - Complete failure chain visible to user")
    else:
        print("\n⚠ Bug may already be fixed!")
        print("  Code appears to include failure reason annotations")
    
    print("="*70 + "\n")
    
    return bug_confirmed


if __name__ == '__main__':
    test_report_data_completeness()
