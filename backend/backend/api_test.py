import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_endpoint(method, path, **kwargs):
    try:
        url = f"{BASE_URL}{path}"
        response = requests.request(method, url, **kwargs)
        return {
            "status": response.status_code,
            "body": response.text[:200]
        }
    except Exception as e:
        return {"error": str(e)}

results = {}

# Test Auth on protected endpoint
results["GET /api/v1/customers/ (No Auth)"] = test_endpoint("GET", "/api/v1/customers/")
results["GET /api/v1/customers/me (No Auth)"] = test_endpoint("GET", "/api/v1/customers/me")
results["GET /api/v1/settings/ (No Auth)"] = test_endpoint("GET", "/api/v1/settings/")

# Test Pydantic Validation on POST
results["POST /api/v1/customers/ (Empty Body)"] = test_endpoint("POST", "/api/v1/customers/", json={})
results["POST /api/v1/drugs/ (Empty Body)"] = test_endpoint("POST", "/api/v1/drugs/", json={})

# Test Rate Limiting
# We can try to hit an endpoint multiple times to see if slowapi catches it, but the health endpoint might be rate limited.
results["GET /health (first)"] = test_endpoint("GET", "/health")
for _ in range(10):
    test_endpoint("GET", "/health")
results["GET /health (after 10 hits)"] = test_endpoint("GET", "/health")

with open("api_test_results.json", "w") as f:
    json.dump(results, f, indent=4)
print("done")
