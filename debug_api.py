import requests
import json
import sys

BASE_URL = "http://127.0.0.1:5000"

def test_system_status():
    print(f"Testing {BASE_URL}/api/system_status...")
    try:
        res = requests.get(f"{BASE_URL}/api/system_status")
        print(f"Status Code: {res.status_code}")
        print(f"Response: {res.json()}")
    except Exception as e:
        print(f"FAILED: {e}")

def test_expirations(ticker="MSFT"):
    print(f"\nTesting {BASE_URL}/api/expirations?ticker={ticker}...")
    try:
        res = requests.get(f"{BASE_URL}/api/expirations", params={"ticker": ticker})
        print(f"Status Code: {res.status_code}")
        data = res.json()
        print(f"Response Keys: {list(data.keys())}")
        if data.get('status') == 'success':
            exps = data.get('expirations', [])
            print(f"Found {len(exps)} expirations: {exps[:3]}...")
            return exps[0] if exps else None
        else:
            print(f"Error Message: {data.get('message')}")
            return None
    except Exception as e:
        print(f"FAILED: {e}")
        return None

def test_analyze(ticker, date):
    print(f"\nTesting {BASE_URL}/api/analyze for {ticker} on {date}...")
    payload = {
        "ticker": ticker,
        "target_date": date,
        "task_id": "debug_test_001"
    }
    try:
        res = requests.post(f"{BASE_URL}/api/analyze", json=payload)
        print(f"Status Code: {res.status_code}")
        if res.status_code == 200:
            data = res.json()
            print(f"Response Status: {data.get('status')}")
            if data.get('status') == 'success':
                calcs = data.get('calculations')
                if calcs:
                    print(f"Calculations present! Keys: {list(calcs.keys())}")
                    # Check for NaNs or Nulls in Module 1
                    m1 = calcs.get('module1_iv_price_range')
                    print(f"Module 1 Data: {json.dumps(m1, indent=2)[:200]}...")
                else:
                    print("CRITICAL: 'calculations' key is MISSING or EMPTY!")
            else:
                print(f"API returned error status: {data.get('message')}")
        else:
            print(f"Server Error: {res.text[:500]}")
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    test_system_status()
    first_exp = test_expirations("MSFT")
    if first_exp:
        test_analyze("MSFT", first_exp)
    else:
        print("\nSkipping analysis test due to missing expiration date.")
