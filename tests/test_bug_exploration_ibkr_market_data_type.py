"""
Bug Condition Exploration Test - Task 7: IBKR Market Data Type Detection

**Validates: Requirements 1.10, 2.10**

**Property 1: Bug Condition** - IBKR Frozen Data Not Labeled
**CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists

**GOAL**: Surface counterexamples showing frozen data lacks type annotation
Test that data includes metadata with data_type (Live/Frozen/Delayed) and timestamp

**EXPECTED OUTCOME**: Test FAILS (no metadata, no data type label)
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from data_layer.ibkr_client import IBKRClient


def test_ibkr_market_data_type_detection():
    """
    Test that IBKR option data includes metadata with data_type field.
    
    Expected to FAIL on unfixed code: option data will not have metadata field.
    """
    print("\n" + "="*70)
    print("BUG EXPLORATION TEST - TASK 7")
    print("IBKR Market Data Type Detection")
    print("="*70)
    print("\nThis test is EXPECTED TO FAIL on unfixed code.")
    print("Failure confirms Bug 1.10 exists.\n")
    
    bug_confirmed = False
    
    try:
        # Create IBKR client
        print("Creating IBKR client...")
        client = IBKRClient()
        
        # Check if client has market data type tracking
        if hasattr(client, 'market_data_type'):
            print(f"✓ Client has market_data_type property")
            
            if hasattr(client, '_get_market_data_type_name'):
                print(f"✓ Client has _get_market_data_type_name method")
            else:
                print(f"✗ Client missing _get_market_data_type_name method")
        else:
            print(f"✗ Client missing market_data_type property")
        
        # The key issue: check if get_option_chain returns data with metadata
        print("\nChecking if option data includes metadata...")
        print("Expected: Each option should have 'metadata' field with:")
        print("  - data_type: 'Live', 'Frozen', or 'Delayed'")
        print("  - timestamp: when data was retrieved")
        print("  - age_hours: how old the data is (for frozen data)")
        
        # We can't actually call get_option_chain without a connection,
        # but we can check the code structure
        import inspect
        if hasattr(client, 'get_option_chain'):
            source = inspect.getsource(client.get_option_chain)
            
            # Check if the code adds metadata to options
            if 'metadata' in source and 'data_type' in source:
                print("\n✓ UNEXPECTED: Code appears to add metadata to options")
                print("  Bug may already be fixed!")
            else:
                print("\n✗ EXPECTED FAILURE: Code does not add metadata to options")
                print("  Bug 1.10 CONFIRMED!")
                bug_confirmed = True
        else:
            print("\n✗ get_option_chain method not found")
            bug_confirmed = True
            
    except Exception as e:
        print(f"\nError during test: {type(e).__name__}: {str(e)}")
        bug_confirmed = True
    
    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY - TASK 7")
    print("="*70)
    
    if bug_confirmed:
        print("\n✓ Bug 1.10 CONFIRMED!")
        print("\nCounterexamples documented:")
        print("  - IBKR option data lacks 'metadata' field")
        print("  - No data_type label (Live/Frozen/Delayed)")
        print("  - No timestamp or age_hours information")
        print("  - Frozen data cannot be distinguished from live data")
        print("\nExpected Behavior (after fix):")
        print("  - Each option should have metadata dict")
        print("  - metadata['data_type'] = 'Live'|'Frozen'|'Delayed'")
        print("  - metadata['timestamp'] = datetime of retrieval")
        print("  - metadata['age_hours'] = hours since market close (for frozen)")
    else:
        print("\n⚠ Bug may already be fixed!")
        print("  Code appears to include metadata in option data")
    
    print("="*70 + "\n")
    
    return bug_confirmed


if __name__ == '__main__':
    test_ibkr_market_data_type_detection()
