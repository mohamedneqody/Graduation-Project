#!/usr/bin/env python3
"""
Cura AI Pharmacy (AI-COS) — Live 5 Intelligent Agents Demo (Sara Abdullah)
==========================================================================
Triggers the 5 core LLM + PostgreSQL decision intelligence agents for
Pharmacy customer 'سارة عبد الله' (30 orders, 12,012.5 EGP, 4 drug interactions)
and sends the 5 clinical/financial/executive cards to Telegram.
"""
import json
import os
import time
import urllib.request
from pathlib import Path
from dotenv import load_dotenv

BACKEND_DIR = Path(r"D:\Graduation Project\AI-COS-Pharmacy\backend")
load_dotenv(BACKEND_DIR / ".env")
TOKEN = os.environ.get("INTERNAL_SERVICE_KEY", "").strip()

for _ in range(15):
    try:
        with urllib.request.urlopen("http://127.0.0.1:5678/healthz", timeout=3) as r:
            if r.status == 200:
                break
    except Exception:
        pass
    time.sleep(2)

cid = "e631c62f-61b1-464a-87d5-73ec865fbf42"
cname = "سارة عبد الله"

tests = [
    ("aicos-customer-success", {
        "customer_id": cid,
        "customer_name": cname,
        "churn_probability": 0.68,
        "last_purchase_days_ago": 34,
        "chronic_drugs": ["protectopril 8 mg 30 tabs", "Diamicron MR 60mg"],
        "order_count": 30,
    }),
    ("aicos-support", {
        "customer_id": cid,
        "customer_name": cname,
        "complaint_text": "تأخر توصيل الطلب الخاص بدواء الضغط والسكري المزمن وأحتاج الدواء اليوم",
        "order_id": None,
        "customer_order_count": 30,
    }),
    ("aicos-patient-health", {
        "customer_id": cid,
        "customer_name": cname,
        "chronic_condition": "ارتفاع ضغط الدم والسكري من النوع الثاني",
    }),
    ("aicos-finance-clv", {
        "customer_id": cid,
        "customer_name": cname,
        "proposed_discount_pct": 15,
    }),
    ("aicos-analytics", {}),
]

print("=" * 78)
print("  Cura AI Pharmacy — Executing 5 Intelligent Decision Agents (سارة عبد الله)")
print("=" * 78)
for path, payload in tests:
    req = urllib.request.Request(
        f"http://127.0.0.1:5678/webhook/{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-Internal-Token": TOKEN},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        body = json.loads(resp.read().decode("utf-8"))
        print(f"  [PASS - HTTP {resp.status}] /webhook/{path} -> store='{body.get('store_name', 'صيدلية كيورا الذكية')}'")
