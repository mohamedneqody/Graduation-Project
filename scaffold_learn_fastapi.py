import os

base_path = r"d:\Graduation Project\learn_production_fastapi"

files = {
    "app/main.py": '''"""
# مسؤوليته: 
# هذا الملف هو نقطة الدخول (Entry Point) لتطبيق FastAPI.
# يقوم بتجميع كل الـ Routers، إعداد الـ CORS، وتشغيل إعدادات الـ Logging.
#
# ممنوع أن يحتوي على:
# - أي منطق عمل (Business Logic).
# - أي استعلامات لقواعد البيانات.
# - أي Endpoints باستثناء الـ Health Check البسيط إن لزم الأمر.
"""
from fastapi import FastAPI
from app.core.config import settings
from app.core.logging import setup_logging
from app.routers import products

# تفعيل الـ Logging
setup_logging()

app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG)

# تسجيل الـ Routers
app.include_router(products.router, prefix="/api/v1")
''',
    
    "app/routers/products.py": '''"""
# مسؤوليته:
# تعريف الـ Endpoints (المسارات) الخاصة بالمنتجات (Products).
# يستقبل الـ Requests ويعيد الـ Responses باستخدام الـ Schemas.
# يربط بين الـ Endpoint والـ Service عن طريق استدعاء الدوال من services.
#
# ممنوع أن يحتوي على:
# - أي استعلام مباشر لقاعدة البيانات (لا يوجد Session.query أو session.execute هنا).
# - أي منطق أعمال (Business Logic) معقد.
"""
from fastapi import APIRouter, Depends
from app.schemas.products import ProductOut
from app.services import products as product_service

router = APIRouter(tags=["Products"])

@router.get("/products", response_model=list[ProductOut])
async def get_products():
    # هنا نستدعي הـ Service فقط
    return await product_service.get_all_products()
''',

    "app/schemas/products.py": '''"""
# مسؤوليته:
# تعريف هياكل البيانات (Data Structures) باستخدام Pydantic.
# يستخدم للتحقق من صحة المدخلات (Input Validation) وتشكيل المخرجات (Response Models).
#
# ممنوع أن يحتوي على:
# - أي تعامل مع قاعدة البيانات.
# - استيراد من مجلد models (الـ Schemas يجب أن تكون مستقلة لوصف البيانات فقط).
"""
from pydantic import BaseModel

class ProductBase(BaseModel):
    name: str
    price: float

class ProductOut(ProductBase):
    id: int

    class Config:
        from_attributes = True
''',

    "app/services/products.py": '''"""
# مسؤوليته:
# يحتوي على منطق الأعمال الحقيقي (Business Logic).
# هنا يتم تنفيذ العمليات المطلوبة، الحسابات، واستدعاء عمليات قاعدة البيانات.
#
# ممنوع أن يحتوي على:
# - أي شيء يخص HTTP أو FastAPI (مثل Request, Response, HTTPException).
# - يجب أن يعتمد على الـ Dependencies المحقونة (مثل DB Session) وليس استيرادها مباشرة.
"""

async def get_all_products():
    # في التطبيق الحقيقي، سيتم استقبال db: AsyncSession كبارامتر
    # وإجراء الاستعلام، ثم إرجاع البيانات.
    return [{"id": 1, "name": "Test Product", "price": 100.0}]
''',

    "app/database/session.py": '''"""
# مسؤوليته:
# إعداد الاتصال بقاعدة البيانات وإدارة الجلسات (Sessions).
# يحتوي على إعداد الـ Engine والـ SessionMaker.
#
# ممنوع أن يحتوي على:
# - أي Models لقاعدة البيانات (توضع في مجلد models).
# - أي عمليات CRUD أو Business Logic.
"""
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings

# يتم استخدام DATABASE_URL من إعدادات التطبيق
engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
''',

    "app/models/products.py": '''"""
# مسؤوليته:
# تعريف جداول قاعدة البيانات باستخدام SQLAlchemy ORM.
# يمثل هيكل البيانات الفعلي المخزن في قاعدة البيانات.
#
# ممنوع أن يحتوي على:
# - دوال CRUD أو أي منطق أعمال (Business Logic).
# - Pydantic Schemas (الـ Schemas مكانها في مجلد schemas).
"""
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(index=True)
    price: Mapped[float]
''',

    "app/dependencies/common.py": '''"""
# مسؤوليته:
# تعريف الـ Dependencies (الحقن) المشتركة التي يتم استخدامها في عدة Routers.
# مثل: الحصول على الـ Current User، الـ Pagination Parameters، الخ.
#
# ممنوع أن يحتوي على:
# - Business logic خاص بـ Domain معين (هذا مكانه في services).
"""
from fastapi import Query

class PaginationParams:
    def __init__(self, page: int = Query(1), limit: int = Query(10)):
        self.page = page
        self.limit = limit
''',

    "app/core/config.py": '''"""
# مسؤوليته:
# إدارة إعدادات ومتغيرات البيئة للتطبيق.
# يستخدم pydantic-settings لقراءة القيم من ملف .env وتحويلها للأنواع المناسبة.
#
# ممنوع أن يحتوي على:
# - قيم سرية حقيقية مكتوبة كـ Hardcode.
# - أي منطق لا يتعلق بالإعدادات.
"""
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "Learn Production FastAPI"
    DEBUG: bool = False
    DATABASE_URL: str

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
''',

    "app/core/logging.py": '''"""
# مسؤوليته:
# إعداد نظام تسجيل الأحداث (Logging) للتطبيق بالكامل.
# يضمن أن جميع الرسائل في التطبيق تتبع تنسيقًا موحدًا (وقت + مستوى الخطورة + الرسالة).
#
# ممنوع أن يحتوي على:
# - استدعاءات فعلية للـ logger لإخراج رسائل متعلقة بسير العمل (هذا الملف للـ Configuration فقط).
"""
import logging
import sys

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )
''',

    "app/utils/exceptions.py": '''"""
# مسؤوليته:
# تعريف الأخطاء المخصصة (Custom Exceptions) الخاصة بالتطبيق.
# يساعد في توحيد شكل الأخطاء المرجعة للمستخدم (مثل ValidationError أو NotFoundError).
#
# ممنوع أن يحتوي على:
# - الـ Exception Handlers التي تتعامل مع FastAPI مباشرة (الـ handlers تُسجل في main.py عادة).
"""
class NotFoundException(Exception):
    def __init__(self, item_name: str):
        self.item_name = item_name
        self.message = f"{item_name} not found"
        super().__init__(self.message)
''',

    ".env.example": '''# اسم التطبيق
APP_NAME=Learn Production FastAPI
# وضع التطوير (True/False)
DEBUG=True
# رابط الاتصال بقاعدة البيانات
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/dbname
'''
}

for rel_path, content in files.items():
    full_path = os.path.join(base_path, rel_path.replace("/", os.sep))
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

print("Scaffolding complete.")
