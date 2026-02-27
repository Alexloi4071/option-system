
import math
import json
from scanner_service import ScannerService

def test_sanitize():
    service = ScannerService()
    
    # Create data with NaNs and Infs
    dirty_data = [
        {
            "ticker": "AAPL",
            "price": 150.0,
            "iv": math.nan,
            "greeks": {
                "delta": 0.5,
                "gamma": math.inf,
                "theta": -0.05
            },
            "history": [1.0, 2.0, math.nan]
        }
    ]
    
    print("Dirty Data:", dirty_data)
    
    # Clean it
    clean_data = service.sanitize_data(dirty_data)
    
    print("Clean Data:", clean_data)
    
    # Try dumping to JSON
    try:
        json_str = json.dumps(clean_data)
        print("JSON Dump Success:", json_str)
    except Exception as e:
        print("JSON Dump Failed:", e)
        
    # Assertions
    assert clean_data[0]['iv'] is None
    assert clean_data[0]['greeks']['gamma'] is None
    assert clean_data[0]['history'][2] is None
    
    print("Test Passed!")

if __name__ == "__main__":
    test_sanitize()
