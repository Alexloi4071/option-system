#!/usr/bin/env python3
"""
Test the WebUI application directly
"""

import requests
import json
import time

def test_webui():
    """Test the WebUI endpoints"""
    base_url = "http://127.0.0.1:5000"
    
    print("🔍 Testing WebUI Application...")
    
    try:
        # Test 1: System Status
        print("\n1. Testing /api/system_status...")
        response = requests.get(f"{base_url}/api/system_status", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ System Status: {data}")
        else:
            print(f"   ❌ System Status failed: {response.status_code}")
            
        # Test 2: Expirations endpoint
        print("\n2. Testing /api/expirations...")
        response = requests.get(f"{base_url}/api/expirations?ticker=AAPL", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Expirations: {data}")
        else:
            print(f"   ❌ Expirations failed: {response.status_code}")
            
        # Test 3: Simple Analysis
        print("\n3. Testing /api/analyze...")
        test_data = {
            "ticker": "AAPL",
            "target_date": "2025-06-20",
            "confidence_level": 0.68
        }
        response = requests.post(f"{base_url}/api/analyze", 
                               json=test_data, timeout=30)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Analysis: {data.get('status', 'Unknown')}")
            if data.get('calculations'):
                calc_modules = list(data['calculations'].keys())
                print(f"   📊 Modules calculated: {len(calc_modules)}")
                print(f"   📊 Module names: {calc_modules[:5]}...")  # Show first 5
        else:
            print(f"   ❌ Analysis failed: {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Error details: {error_data}")
            except:
                pass
                
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to WebUI. Make sure the Flask app is running on http://127.0.0.1:5000")
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    print("WebUI Test Script")
    print("=================")
    print("Make sure to start the WebUI first:")
    print("  python web_layer/app.py")
    print()
    
    # Wait a moment for user to start server
    input("Press Enter after starting the WebUI server...")
    
    test_webui()