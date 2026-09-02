import requests
import json

BASE_URL = "http://127.0.0.1:8000"
headers = {"Content-Type": "application/json"}

# Instead of creating new ones, let's see if we can get a token from signup_test_users.py
import subprocess
out = subprocess.run(["python", "signup_test_users.py"], capture_output=True, text=True)

print("Signup Output:", out.stdout[:500])

# Just trying an IDOR might be hard without knowing the customer_id of another user. 
# But wait, looking at the code for customers endpoint, is there an authorization check that compares the token user_id with the requested customer_id?
