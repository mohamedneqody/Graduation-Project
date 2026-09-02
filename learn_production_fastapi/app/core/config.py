"""
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
