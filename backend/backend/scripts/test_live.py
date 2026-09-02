"""
سكريبت اختبار حي شامل — A1 + B (RAG)
يُشغَّل بعد seed_knowledge.py
"""
import asyncio
import sys
import os
import json
import httpx

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings
from app.models.customer import Customer
from app.models.drug import Drug
from app.models.tracking import CustomerCycle
from app.models.knowledge import KnowledgeChunk

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

BASE_URL = "http://localhost:8000"


async def test_predictions(client: httpx.AsyncClient, db: AsyncSession):
    print("\n" + "="*60)
    print("اختبار A1 — ML Predictions")
    print("="*60)

    # جلب أول عميل وأول دواء لديه cycle
    cycle_res = await db.execute(
        select(CustomerCycle).limit(1)
    )
    cycle = cycle_res.scalars().first()
    if not cycle:
        print("⚠️  لا يوجد customer_cycle في DB — تشغيل seed_data أولاً")
        return

    cid = str(cycle.customer_id)
    did = str(cycle.drug_id)
    print(f"\n📌 العميل: {cid}")
    print(f"📌 الدواء: {did}")

    # ── Cycle Prediction ──────────────────────────────────────────────────
    print("\n▶ POST /api/v1/predictions/cycle")
    r = await client.post(
        f"{BASE_URL}/api/v1/predictions/cycle",
        json={"customer_id": cid, "drug_id": did},
    )
    if r.status_code == 200:
        data = r.json()
        print(f"  ✅ predicted_days:       {data['predicted_days']}")
        print(f"  ✅ predicted_next_date:  {data['predicted_next_date']}")
        print(f"  ✅ confidence:           {data['confidence']}")
        print(f"  ✅ confidence_formula:   {data['confidence_formula']}")
        print(f"  ✅ is_cold_start:        {data['is_cold_start']}")
        print(f"  ✅ shap_top_features:")
        for s in data.get("shap_top_features", []):
            print(f"       {s['feature']}: {s['shap_value']}")
    else:
        print(f"  ❌ Error {r.status_code}: {r.text[:200]}")

    # ── Churn Prediction ──────────────────────────────────────────────────
    print("\n▶ POST /api/v1/predictions/churn")
    r = await client.post(
        f"{BASE_URL}/api/v1/predictions/churn",
        json={"customer_id": cid, "drug_id": did},
    )
    if r.status_code == 200:
        data = r.json()
        print(f"  ✅ churn_probability:    {data['churn_probability']}")
        print(f"  ✅ churn_risk:           {data['churn_risk']}")
        print(f"  ✅ will_churn:           {data['will_churn']}")
        print(f"  ✅ confidence:           {data['confidence']}")
        print(f"  ✅ optimal_threshold:    {data['optimal_threshold']}")
        print(f"  ✅ message:              {data['message']}")
        print(f"  ✅ shap_top_features:")
        for s in data.get("shap_top_features", []):
            print(f"       {s['feature']}: {s['shap_value']}")
    else:
        print(f"  ❌ Error {r.status_code}: {r.text[:200]}")


async def test_rag(client: httpx.AsyncClient, db: AsyncSession):
    print("\n" + "="*60)
    print("اختبار B — RAG Bot")
    print("="*60)

    # عدد الـ chunks
    count = (await db.execute(
        select(KnowledgeChunk)
    )).scalars().all()
    print(f"\n📊 عدد knowledge_chunks في DB: {len(count)}")

    tests = [
        {
            "label": "سؤال في النطاق (دواء معروف)",
            "q": "ما هو دواء جلوكوفاج وهل هو مزمن؟",
        },
        {
            "label": "سؤال في النطاق (سياسة متجر)",
            "q": "ما هي سياسة الإرجاع في الصيدلية؟",
        },
        {
            "label": "سؤال خارج النطاق تماماً",
            "q": "ما رأيك في الطقس اليوم؟",
        },
    ]

    for t in tests:
        print(f"\n▶ [{t['label']}]")
        print(f"  السؤال: {t['q']}")
        r = await client.post(
            f"{BASE_URL}/api/v1/ai/chat",
            json={"message": t["q"]},
            timeout=60.0,
        )
        if r.status_code == 200:
            reply = r.json()["reply"]
            print(f"  الرد: {reply[:400]}")
            has_disclaimer = "استشارة الصيدلي" in reply or "رد آلي" in reply
            print(f"  {'✅' if has_disclaimer else '❌'} التنويه الطبي: {'موجود' if has_disclaimer else 'مفقود!'}")
        else:
            print(f"  ❌ Error {r.status_code}: {r.text[:200]}")


async def test_analytics(client: httpx.AsyncClient):
    print("\n" + "="*60)
    print("اختبار Analytics")
    print("="*60)
    r = await client.get(f"{BASE_URL}/api/v1/analytics/summary")
    if r.status_code == 200:
        data = r.json()
        print(f"  ✅ total_customers:      {data['total_customers']}")
        print(f"  ✅ active_customers_30d: {data['active_customers_30d']}")
        print(f"  ✅ total_orders:         {data['total_orders']}")
        print(f"  ✅ total_revenue:        {data['total_revenue']}")
        print(f"  ✅ model_mae_days:       {data['regression_model_mae_days']}")
        print(f"  ✅ top_categories:")
        for c in data.get("top_drug_categories", []):
            print(f"       {c['category']}: {c['order_count']} طلب ({c['percentage']}%)")
    else:
        print(f"  ❌ Error {r.status_code}: {r.text[:200]}")


async def main():
    async with AsyncSessionLocal() as db:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # تحقق الخادم يعمل
            try:
                health = await client.get(f"{BASE_URL}/health")
                print(f"✅ Server: {health.json()}")
            except Exception:
                print("❌ الخادم لا يعمل — شغّل: uvicorn app.main:app --reload")
                return

            await test_predictions(client, db)
            await test_rag(client, db)
            await test_analytics(client)

    print("\n" + "="*60)
    print("✅ انتهى الاختبار")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
