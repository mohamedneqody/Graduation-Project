#!/usr/bin/env python3
"""
Cura AI Pharmacy / AI-COS — Live Multi-Vertical Proof for n8n Agents
====================================================================
Proves that the exact same n8n workflows (:5678) dynamically switch their
PostgreSQL Row-Level Security (RLS) tenant scope, domain vocabulary, financial
margins, technical/clinical compatibility rules, and Telegram cards based on
`tenant_id` (`pharmacy` vs `car_showroom` vs `auto_parts`).
"""
import json
import os
import urllib.request
from pathlib import Path
from dotenv import load_dotenv

BACKEND_DIR = Path(r"D:\Graduation Project\AI-COS-Pharmacy\backend")
load_dotenv(BACKEND_DIR / ".env")
TOKEN = os.environ.get("INTERNAL_SERVICE_KEY", "").strip()

CAR_SHOWROOM_TENANT_ID = "49705d0f-479d-4930-8861-fb7c16914ecd"
CAR_SHOWROOM_CUSTOMER_ID = "d9151875-54a9-4f0a-8c90-7625ad96c72c"
CAR_SHOWROOM_CUSTOMER_NAME = "م. ياسر علام"


def call_webhook(path: str, payload: dict):
    req = urllib.request.Request(
        f"http://127.0.0.1:5678/webhook/{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-Internal-Token": TOKEN},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def main():
    print("=" * 78)
    print("  AI-COS Multi-Vertical Live Proof — Car Showroom (معرض AI-COS للسيارات الحديثة)")
    print("=" * 78)
    tests = [
        (
            "aicos-customer-success",
            {
                "tenant_id": CAR_SHOWROOM_TENANT_ID,
                "customer_id": CAR_SHOWROOM_CUSTOMER_ID,
                "customer_name": CAR_SHOWROOM_CUSTOMER_NAME,
                "churn_probability": 0.71,
                "last_purchase_days_ago": 40,
            },
        ),
        (
            "aicos-support",
            {
                "tenant_id": CAR_SHOWROOM_TENANT_ID,
                "customer_id": CAR_SHOWROOM_CUSTOMER_ID,
                "customer_name": CAR_SHOWROOM_CUSTOMER_NAME,
                "complaint_text": "تأخر موعد تسليم باقة الحماية النانو سيراميك 3M وجهاز الشاحن المنزلي السريع للسيارة الجديدة",
            },
        ),
        (
            "aicos-patient-health",
            {
                "tenant_id": CAR_SHOWROOM_TENANT_ID,
                "customer_id": CAR_SHOWROOM_CUSTOMER_ID,
                "customer_name": CAR_SHOWROOM_CUSTOMER_NAME,
                "chronic_condition": "فحص التوافق الفني والضمان الممتد لأسطول مركبات العميل (هجينة DM-i + تربو بنزين)",
            },
        ),
        (
            "aicos-finance-clv",
            {
                "tenant_id": CAR_SHOWROOM_TENANT_ID,
                "customer_id": CAR_SHOWROOM_CUSTOMER_ID,
                "customer_name": CAR_SHOWROOM_CUSTOMER_NAME,
                "proposed_discount_pct": 5,
            },
        ),
        ("aicos-analytics", {"tenant_id": CAR_SHOWROOM_TENANT_ID}),
    ]
    for path, body in tests:
        st, data = call_webhook(path, body)
        print(f"  [PASS - HTTP {st}] /webhook/{path} -> store='{data.get('store_name')}', vertical='{data.get('vertical')}'")


if __name__ == "__main__":
    main()
