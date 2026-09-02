# ==========================================
# 1. مرحلة البناء (Builder Stage)
# ==========================================
# نستخدم نسخة python صغيرة كبداية
FROM python:3.12-slim AS builder

# إيقاف كتابة ملفات بايثون المترجمة (.pyc) وتفعيل عرض الأخطاء فوراً
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# تثبيت الأدوات اللازمة لبناء الحزم (إن وجدت)
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

# نقوم بإنشاء بيئة وهمية (Virtual Environment) داخل الحاوية لعزل المكاتب
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# نسخ ملف requirements.txt فقط لتثبيت المكاتب أولاً (للاستفادة من Docker Cache)
# (بفرض أن لديك ملف requirements.txt جاهز)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# ==========================================
# 2. مرحلة التشغيل (Production Stage)
# ==========================================
FROM python:3.12-slim

WORKDIR /app

# نسخ البيئة الوهمية (venv) الجاهزة من مرحلة البناء (Builder Stage)
# هذا يوفر المساحة ويمنع انتقال أدوات البناء الثقيلة للنسخة النهائية
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# نسخ الكود المصدري للمشروع
COPY . .

# فتح البورت 8000 لكي يتمكن العالم الخارجي من الاتصال
EXPOSE 8000

# أمر التشغيل الأساسي
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
