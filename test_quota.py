import os
import requests

API_KEY = os.environ.get("GEMINI_API_KEY", "")

url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.7-flash:generateContent?key={API_KEY}"
payload = {
    "contents": [{"parts": [{"text": "Hello, return just the word OK"}]}]
}
resp = requests.post(url, json=payload)
print(resp.status_code)
