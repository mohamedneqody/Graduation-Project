import requests
import json
import sys

# Fix encoding for Windows console
sys.stdout.reconfigure(encoding='utf-8')

TENANT_ID = "62712616-be1e-4129-986f-4131877e63b8"
HEADERS = {"X-N8N-Service-Key": "dev-secret-key"}
BASE_URL = "http://127.0.0.1:8000"

def run_workflow_simulation():
    print("Starting workflow simulation...")
    
    print(f"\n[1] Fetching due reminders for tenant: {TENANT_ID}")
    resp = requests.get(f"{BASE_URL}/internal/cycles/due-reminders?tenant_id={TENANT_ID}", headers=HEADERS)
    if resp.status_code != 200:
        print(f"Error fetching reminders: {resp.text}")
        return
    
    reminders = resp.json()
    print(f"Found {len(reminders)} customers needing reminders.")
    
    test_limit = min(3, len(reminders))
    print(f"Testing the flow for the first {test_limit} customers...\n")
    
    for i, customer in enumerate(reminders[:test_limit], 1):
        customer_id = customer['customer_id']
        due_drugs = customer.get('due_drugs', [])
        
        # Message
        message = f"تذكير: الأدوية دي قربت تخلص: {json.dumps(due_drugs, ensure_ascii=False)}"
        print(f"--- Customer {i} ---")
        print(f"Message generated: {message}")
        
        # Record Notification
        payload = {
            "customer_id": customer_id,
            "notification_type": "reminder",
            "channel": "whatsapp",
            "status": "sent"
        }
        print(f"Sending POST to /internal/notifications/record...")
        record_resp = requests.post(f"{BASE_URL}/internal/notifications/record", json=payload, headers=HEADERS)
        
        if record_resp.status_code in [200, 201]:
            print(f"Notification recorded successfully! (Status: {record_resp.status_code})")
        else:
            print(f"Failed to record notification: {record_resp.text}")
        print("-" * 20)
        
    print("\nSimulation complete!")

if __name__ == "__main__":
    run_workflow_simulation()
