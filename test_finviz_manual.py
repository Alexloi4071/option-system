#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Manual test for Finviz scraper enhancements (Task 17.1 and 17.2)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_layer.finviz_scraper import FinvizScraper
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_finviz_enhancements():
    """Test Finviz scraper enhancements"""
    print("\n" + "=" * 80)
    print("Testing Finviz Scraper Enhancements (Task 17.1 & 17.2)")
    print("=" * 80)
    
    scraper = FinvizScraper()
    
    # Test 1: Check headers contain required fields
    print("\n[Test 1] Checking HTTP headers...")
    required_headers = ['User-Agent', 'Accept', 'Accept-Language', 'Referer']
    all_present = True
    for header in required_headers:
        if header in scraper.headers:
            print(f"  ✓ {header}: present")
        else:
            print(f"  ✗ {header}: MISSING")
            all_present = False
    
    if all_present:
        print("  ✓ All required headers present")
    else:
        print("  ✗ Some headers missing")
    
    # Test 2: Check Referer is finviz.com
    print("\n[Test 2] Checking Referer header...")
    if 'Referer' in scraper.headers and 'finviz.com' in scraper.headers['Referer']:
        print(f"  ✓ Referer: {scraper.headers['Referer']}")
    else:
        print(f"  ✗ Referer incorrect or missing")
    
    # Test 3: Try to fetch data (will test timeout and error handling)
    print("\n[Test 3] Testing data fetch with enhanced error handling...")
    try:
        data = scraper.get_stock_fundamentals('AAPL')
        if data:
            print(f"  ✓ Successfully fetched AAPL data")
            print(f"    Company: {data.get('company_name', 'N/A')}")
            print(f"    Price: ${data.get('price', 0):.2f}")
            
            # Check data quality logging (Task 17.2)
            key_fields = ['insider_own', 'inst_own', 'short_float', 'avg_volume', 'peg',
                         'roe', 'profit_margin', 'debt_eq', 'atr', 'rsi', 'beta']
            available = sum(1 for f in key_fields if data.get(f) is not None)
            print(f"    Data quality: {available}/11 fields available")
            
            if available >= 9:
                print(f"  ✓ Data quality check passed ({available}/11 fields)")
            else:
                print(f"  ! Data quality warning: only {available}/11 fields")
        else:
            print(f"  ✗ Failed to fetch data")
    except Exception as e:
        print(f"  ✗ Exception: {e}")
    
    print("\n" + "=" * 80)
    print("Test completed")
    print("=" * 80)

if __name__ == "__main__":
    test_finviz_enhancements()
