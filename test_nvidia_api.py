import requests
import json

def test_nvidia_api(api_key):
    # Endpoint for model listing or a simple completion to test auth
    # Using Llama 3.1 405B Instruct as a test target, or just listing models
    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "meta/llama-3.1-405b-instruct",
        "messages": [{"role": "user", "content": "Hello, are you working?"}],
        "temperature": 0.5,
        "max_tokens": 50,
        "stream": False
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("Response:", response.json())
            return True
        else:
            print("Error:", response.text)
            return False
    except Exception as e:
        print(f"Exception: {e}")
        return False

if __name__ == "__main__":
    key = "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"
    test_nvidia_api(key)
