import requests
url = "http://api.wolframalpha.com/v1/result"
params = {
    "appid": "3HQJ4VY5WT",
    "i": "derivative of x^2"
}
response = requests.get(url, params=params)
print("Status Code:", response.status_code)
print("Response:", response.text)
