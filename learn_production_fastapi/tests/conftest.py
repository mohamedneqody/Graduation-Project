import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database.session import get_db
from app.models.base import Base

# إعداد قاعدة بيانات منفصلة للاختبار (في الذاكرة - SQLite)
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    """ينشئ الجداول قبل الاختبار، ويمسحها بعده لضمان بيئة نظيفة"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db_session):
    """
    يقوم بإنشاء TestClient واستبدال اتصال الداتابيز الرئيسي
    باتصال قاعدة البيانات الخاصة بالاختبار.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    # استبدال الـ Dependency
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as c:
        yield c
