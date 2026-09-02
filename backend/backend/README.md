# AI-COS Pharmacy — Backend Skeleton

## الإعداد لأول مرة

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# افتح .env واملأ DATABASE_URL من Supabase:
# Project Settings > Database > Connection String > Session pooler (URI)
# غيّر بادئة postgresql:// إلى postgresql+asyncpg://
```

## تشغيل أول Migration (إنشاء كل الجداول)

```bash
alembic upgrade head
```

هيعمل الآتي بالترتيب:
1. يفعّل `pgvector` extension داخل Supabase.
2. ينشئ الـ 12 جدول بالكامل (customers, drugs, sessions, events, orders...) بنفس ترتيب الـ Foreign Keys الصحيح.

## التحقق من النجاح

روح على Supabase Dashboard → Table Editor، المفروض تلاقي كل الجداول الـ 12 ظاهرة.

## أي تعديل على الـ Schema بعد كده

1. عدّل الـ Model في `app/models/`.
2. شغّل: `alembic revision --autogenerate -m "وصف التعديل"`.
3. راجع الملف اللي اتولّد في `alembic/versions/` قبل ما تطبّقه.
4. `alembic upgrade head`.

## الخطوة الجاية

بعد ما الجداول تتظبط على Supabase، الخطوة التالية: كتابة سكريبت توليد Synthetic Data (`scripts/generate_synthetic_data.py`) اللي هيملأ الجداول دي ببيانات واقعية للتدريب والاختبار.
