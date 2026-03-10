"""
Bug Condition Exploration Test for BR-03: Duplicate Module Numbering

**Validates: Requirements 3.3, 3.7**

This test is designed to FAIL on unfixed code to confirm the bug exists.
It verifies that each module number in calculation_layer has exactly one owner.

CRITICAL: This test MUST FAIL on unfixed code - failure confirms the bug exists.
DO NOT attempt to fix the test or the code when it fails.

Expected counterexample: module32_american_pricing.py and module32_complex_strategies.py
both use module32, creating ambiguity in imports, logs, and requirements traceability.
"""

import pytest
from hypothesis import given, strategies as st, settings, Phase
import os
import re
from pathlib import Path
from collections import defaultdict


def extract_module_number(filename):
    """
    Extract module number from filename.
    
    Examples:
        'module32_american_pricing.py' -> 32
        'module1_support_resistance.py' -> 1
        'strategy_recommendation.py' -> None
    """
    match = re.match(r'module(\d+)_', filename)
    if match:
        return int(match.group(1))
    return None


def scan_calculation_layer_modules():
    """
    Scan calculation_layer directory and return mapping of module numbers to files.
    
    Returns:
        dict: {module_number: [list of files with that number]}
    """
    calculation_layer_path = Path(__file__).parent.parent / 'calculation_layer'
    
    if not calculation_layer_path.exists():
        raise FileNotFoundError(f"calculation_layer directory not found at {calculation_layer_path}")
    
    module_map = defaultdict(list)
    
    for file_path in calculation_layer_path.glob('*.py'):
        filename = file_path.name
        
        # Skip special files
        if filename.startswith('__') or filename in ['workflow_config.py', 'strategy_recommendation.py']:
            continue
        
        module_number = extract_module_number(filename)
        if module_number is not None:
            module_map[module_number].append(filename)
    
    return module_map


@pytest.mark.property_based_test
def test_duplicate_module_numbering_detection():
    """
    **Property 1: Bug Condition** - Duplicate Module Identity Detection
    
    **Validates: Requirements 3.3, 3.7**
    
    CRITICAL: This test MUST FAIL on unfixed code.
    
    Tests that each module number in calculation_layer has exactly one owner.
    On unfixed code, this will fail because module32 is shared by:
    - module32_american_pricing.py
    - module32_complex_strategies.py
    
    Expected counterexample on unfixed code:
    - module32: ['module32_american_pricing.py', 'module32_complex_strategies.py']
    
    This creates ambiguity in:
    - Import statements (which module32 to import?)
    - Log messages (which "Module 32" is executing?)
    - Requirements traceability (which file implements requirement X?)
    - Code review and maintenance (which file to modify?)
    """
    # Scan calculation_layer for module numbering
    module_map = scan_calculation_layer_modules()
    
    # Find all duplicates
    duplicates = {
        module_num: files 
        for module_num, files in module_map.items() 
        if len(files) > 1
    }
    
    # Document the counterexamples found
    if duplicates:
        print("\n=== BUG DETECTED: Duplicate Module Numbering ===")
        print(f"Found {len(duplicates)} module number(s) with multiple files:")
        
        for module_num, files in sorted(duplicates.items()):
            print(f"\nModule {module_num} is used by {len(files)} files:")
            for filename in sorted(files):
                print(f"  - {filename}")
        
        print("\n=== Impact Analysis ===")
        print("This creates ambiguity in:")
        print("  1. Import statements: 'from calculation_layer.module32 import ...' is ambiguous")
        print("  2. Log messages: 'Module 32 executing...' doesn't identify which file")
        print("  3. Requirements traceability: Can't map requirements to unique files")
        print("  4. Code review: Unclear which file to modify for 'Module 32' changes")
        
        print("\n=== Expected Counterexample ===")
        print("module32: ['module32_american_pricing.py', 'module32_complex_strategies.py']")
        print("This confirms the bug exists in the unfixed code.")
    
    # ASSERTION: Each module number should have exactly one file
    # This will FAIL on unfixed code (which is correct - it proves the bug exists)
    assert len(duplicates) == 0, (
        f"Duplicate module numbering detected! "
        f"Found {len(duplicates)} module number(s) with multiple files: "
        f"{dict(duplicates)}. "
        f"Each module number should have exactly one owner file. "
        f"This violates the one-module-one-number principle."
    )
    
    # If we reach here on unfixed code, something is wrong with the test
    print("WARNING: Test passed on unfixed code - bug may not exist or test needs adjustment")


@pytest.mark.property_based_test
def test_module_identity_uniqueness_comprehensive():
    """
    **Property 1: Bug Condition** - Comprehensive Module Identity Check
    
    **Validates: Requirements 3.3, 3.7**
    
    Comprehensive check that verifies:
    1. No duplicate module numbers exist
    2. All numbered modules follow the moduleXX_name.py pattern
    3. Module numbers are used consistently
    
    This test provides detailed diagnostics about the module numbering scheme.
    """
    module_map = scan_calculation_layer_modules()
    
    # Check 1: No duplicates
    duplicates = {num: files for num, files in module_map.items() if len(files) > 1}
    
    # Check 2: Verify all files follow naming convention
    calculation_layer_path = Path(__file__).parent.parent / 'calculation_layer'
    all_module_files = [
        f.name for f in calculation_layer_path.glob('module*.py')
        if not f.name.startswith('__')
    ]
    
    # Check 3: Identify gaps in numbering sequence
    if module_map:
        max_module = max(module_map.keys())
        expected_range = set(range(1, max_module + 1))
        actual_numbers = set(module_map.keys())
        gaps = expected_range - actual_numbers
    else:
        gaps = set()
    
    # Report findings
    print("\n=== Module Numbering Analysis ===")
    print(f"Total numbered module files: {len(all_module_files)}")
    print(f"Unique module numbers: {len(module_map)}")
    print(f"Module number range: {min(module_map.keys()) if module_map else 'N/A'} to {max(module_map.keys()) if module_map else 'N/A'}")
    
    if gaps:
        print(f"\nGaps in numbering sequence: {sorted(gaps)}")
    
    if duplicates:
        print(f"\n!!! DUPLICATES FOUND !!!")
        for module_num, files in sorted(duplicates.items()):
            print(f"  Module {module_num}: {files}")
    
    # Primary assertion: No duplicates
    assert len(duplicates) == 0, (
        f"Module identity uniqueness violated! "
        f"Duplicates: {dict(duplicates)}"
    )


@pytest.mark.property_based_test
@given(
    # Test with different module number ranges to ensure robustness
    check_range=st.sampled_from([
        (1, 10),   # Early modules
        (20, 30),  # Mid-range modules
        (30, 40),  # Late modules including the problematic module32
    ])
)
@settings(
    max_examples=3,
    phases=[Phase.generate, Phase.target],
    deadline=None
)
def test_module_uniqueness_property_based(check_range):
    """
    **Property 1: Bug Condition** - Module Uniqueness Across Ranges
    
    **Validates: Requirements 3.3, 3.7**
    
    Property-based test that checks module uniqueness across different ranges.
    This ensures the bug is detected regardless of which module range we examine.
    """
    start, end = check_range
    module_map = scan_calculation_layer_modules()
    
    # Filter to the range we're checking
    range_modules = {
        num: files 
        for num, files in module_map.items() 
        if start <= num <= end
    }
    
    # Check for duplicates in this range
    duplicates = {num: files for num, files in range_modules.items() if len(files) > 1}
    
    if duplicates:
        print(f"\nDuplicates found in range {start}-{end}: {dict(duplicates)}")
    
    # Expected behavior: No duplicates in any range
    # This will FAIL on unfixed code when checking range (30, 40) which includes module32
    assert len(duplicates) == 0, (
        f"Duplicate module numbering in range {start}-{end}! "
        f"Found: {dict(duplicates)}"
    )


def test_specific_module32_duplicate():
    """
    **Property 1: Bug Condition** - Specific Test for Module32 Duplicate
    
    **Validates: Requirements 3.3, 3.7**
    
    Focused test specifically checking for the known module32 duplicate issue.
    This test directly validates the bug described in the bugfix requirements.
    """
    calculation_layer_path = Path(__file__).parent.parent / 'calculation_layer'
    
    # Look for all files with module32 in the name
    module32_files = list(calculation_layer_path.glob('module32_*.py'))
    
    print(f"\n=== Module32 Files Found ===")
    print(f"Count: {len(module32_files)}")
    for file_path in sorted(module32_files):
        print(f"  - {file_path.name}")
    
    # Expected on unfixed code: 2 files
    # Expected after fix: 1 file (or 0 if renamed to non-numbered)
    if len(module32_files) > 1:
        print("\n=== BUG CONFIRMED ===")
        print("Multiple files share the module32 identity:")
        for file_path in sorted(module32_files):
            print(f"  - {file_path.name}")
        print("\nThis creates ambiguity in imports, logs, and requirements traceability.")
    
    # ASSERTION: Should have at most one file with module32 prefix
    # This will FAIL on unfixed code (which is correct - it proves the bug exists)
    assert len(module32_files) <= 1, (
        f"Duplicate module32 detected! "
        f"Found {len(module32_files)} files: {[f.name for f in module32_files]}. "
        f"Expected: module32_american_pricing.py and module32_complex_strategies.py. "
        f"Only one file should use the module32 identity."
    )


if __name__ == '__main__':
    # Run the exploration tests directly
    print("Running Bug Condition Exploration Test for BR-03...")
    print("=" * 70)
    
    print("\n1. Testing for duplicate module numbering...")
    try:
        test_duplicate_module_numbering_detection()
        print("✓ No duplicates found")
    except AssertionError as e:
        print(f"✗ Test failed (expected on unfixed code): {e}")
    
    print("\n2. Testing module32 specifically...")
    try:
        test_specific_module32_duplicate()
        print("✓ Module32 is unique")
    except AssertionError as e:
        print(f"✗ Test failed (expected on unfixed code): {e}")
    
    print("\n3. Running comprehensive analysis...")
    try:
        test_module_identity_uniqueness_comprehensive()
        print("✓ All module identities are unique")
    except AssertionError as e:
        print(f"✗ Test failed (expected on unfixed code): {e}")
