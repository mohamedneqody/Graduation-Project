import os

base_path = r"d:\Graduation Project\learn_production_fastapi"

files = {
    "Dockerfile": '''# ==========================================
# 1. مرحلة البناء (Builder Stage)
# ==========================================
# نستخدم نسخة python صغيرة كبداية
FROM python:3.12-slim AS builder

# إيقاف كتابة ملفات بايثون المترجمة (.pyc) وتفعيل عرض الأخطاء فوراً
ENV PYTHONDONTWRITEBYTECODE=1 \\
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
''',

    "docker-compose.yml": '''version: "3.9"

services:
  # خدمة واجهة برمجة التطبيقات (FastAPI)
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:password123@db:5432/fastapidb
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    # سيقوم Docker بإعادة تشغيل الخدمة تلقائياً إذا توقفت عن العمل
    restart: always

  # خدمة قاعدة بيانات PostgreSQL
  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password123
      - POSTGRES_DB=fastapidb
    ports:
      - "5432:5432"
    # حفظ بيانات قاعدة البيانات محلياً لكي لا تضيع عند إيقاف الـ Docker
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: always

  # خدمة Redis (للتخزين المؤقت أو مهام Celery)
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    restart: always

# تعريف المساحات التخزينية (Volumes)
volumes:
  postgres_data:
''',

    "nginx.conf": '''events {
    # الحد الأقصى للاتصالات المتزامنة
    worker_connections 1024;
}

http {
    # خوادم FastAPI التي سيوجه Nginx الطلبات إليها (Reverse Proxy)
    upstream fastapi_app {
        server api:8000;
    }

    server {
        # المنفذ الأساسي لاستقبال الطلبات من المستخدمين
        listen 80;
        server_name api.yourdomain.com;

        # توجيه جميع الطلبات إلى خادم FastAPI الداخلي
        location / {
            proxy_pass http://fastapi_app;
            
            # تمرير معلومات العميل الأصلية (IP) لكي لا يظهر الـ Request كأنه من Nginx
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
''',

    "railway.json": '''{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile"
  },
  "deploy": {
    "startCommand": "uvicorn app.main:app --host 0.0.0.0 --port $PORT",
    "healthcheckPath": "/api/v1/health",
    "healthcheckTimeout": 100
  }
}
''',

    "render.yaml": '''services:
  - type: web
    name: fastapi-backend
    env: docker
    region: frankfurt
    plan: free
    dockerfilePath: ./Dockerfile
    startCommand: "uvicorn app.main:app --host 0.0.0.0 --port $PORT"
    healthCheckPath: /api/v1/health
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: postgres-db
          property: connectionString
      - key: REDIS_URL
        sync: false

  - type: psql
    name: postgres-db
    region: frankfurt
    plan: free
    postgresMajorVersion: 15
'''
}

for rel_path, content in files.items():
    full_path = os.path.join(base_path, rel_path.replace("/", os.sep))
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

# Update main.py to add /api/v1/health
main_py_path = os.path.join(base_path, "app/main.py")
with open(main_py_path, "r", encoding="utf-8") as f:
    main_content = f.read()

# Add a health check endpoint
health_check_code = '''
from fastapi import APIRouter
from sqlalchemy.orm import Session
from fastapi import Depends
from app.database.session import get_db

health_router = APIRouter(prefix="/api/v1", tags=["Monitoring"])

@health_router.get("/health")
def health_check(db: Session = Depends(get_db)):
    """
    Endpoint لفحص حالة السيرفر وقاعدة البيانات.
    أنظمة الـ Monitoring تحتاجه لتعرف متى يكون السيرفر جاهزاً للعمل (Ready) ومتى يموت (Dead) لتعيد تشغيله.
    """
    db_status = "ok"
    try:
        # فحص فعلي لقاعدة البيانات
        db.execute("SELECT 1")
    except Exception:
        db_status = "down"
    
    status_code = 200 if db_status == "ok" else 503
    
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=status_code, content={"status": "up", "database": db_status})

app.include_router(health_router)
'''
if "def health_check" not in main_content:
    with open(main_py_path, "a", encoding="utf-8") as f:
        f.write(health_check_code)

# Create a dummy requirements.txt for the dockerfile
requirements_path = os.path.join(base_path, "requirements.txt")
if not os.path.exists(requirements_path):
    with open(requirements_path, "w", encoding="utf-8") as f:
        f.write("fastapi\nuvicorn[standard]\npydantic\npydantic-settings\nsQLAlchemy\naiosqlite\npytest\nhttpx\n")

print("Deployment files generated successfully.")
