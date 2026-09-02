import os
import requests

API_KEY = os.environ.get("GEMINI_API_KEY", "")

models = ["gemini-3.7-pro", "gemini-3.6-pro"]
for model in models:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": "Hello, return just the word OK"}]}]
    }
    resp = requests.post(url, json=payload)
    if resp.status_code == 200:
        print(f"{model}: SUCCESS")
    else:
        print(f"{model}: FAILED {resp.status_code} - {resp.text}")
