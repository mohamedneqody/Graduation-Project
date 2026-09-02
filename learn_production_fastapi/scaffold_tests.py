import os

base_path = r"d:\Graduation Project\learn_production_fastapi"

files = {
    # ------------------
    # SCHEMAS
    # ------------------
    "app/schemas/products.py": '''from pydantic import BaseModel

class ProductBase(BaseModel):
    name: str
    price: float

class ProductCreate(ProductBase):
    pass

class ProductOut(ProductBase):
    id: int
    class Config:
        from_attributes = True
''',
    
    "app/schemas/auth.py": '''from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    email: EmailStr
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
''',

    # ------------------
    # MODELS
    # ------------------
    "app/models/base.py": '''from sqlalchemy.orm import DeclarativeBase
class Base(DeclarativeBase):
    pass
''',
    
    "app/models/products.py": '''from sqlalchemy.orm import Mapped, mapped_column
from .base import Base

class Product(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(index=True)
    price: Mapped[float]
''',
    
    "app/models/users.py": '''from sqlalchemy.orm import Mapped, mapped_column
from .base import Base

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(unique=True, index=True)
    hashed_password: Mapped[str]
''',

    # ------------------
    # DATABASE
    # ------------------
    "app/database/session.py": '''from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# For simplicity in this sync test environment, we use sync engine
engine = create_engine("sqlite:///./dev.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
''',

    # ------------------
    # ROUTERS
    # ------------------
    "app/routers/products.py": '''from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas.products import ProductOut, ProductCreate
from app.models.products import Product
from app.database.session import get_db

router = APIRouter(prefix="/api/v1/products", tags=["Products"])

@router.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    db_product = Product(name=product.name, price=product.price)
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    return db_product

@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(db_product)
    db.commit()
    return None
''',

    "app/routers/auth.py": '''from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from app.schemas.auth import UserCreate, UserOut, Token
from app.models.users import User
from app.database.session import get_db

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])

@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def signup(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Fake hashing
    new_user = User(email=user.email, hashed_password=user.password + "_hashed")
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.post("/login", response_model=Token)
def login(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or db_user.hashed_password != user.password + "_hashed":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    
    return {"access_token": f"fake-token-for-{db_user.id}", "token_type": "bearer"}

def get_current_user(authorization: str = Header(None), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer fake-token-for-"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    
    user_id = int(authorization.split("-")[-1])
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return db_user

@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
''',

    "app/main.py": '''from fastapi import FastAPI
from app.core.config import settings
from app.routers import products, auth
from app.database.session import engine
from app.models.base import Base

# Create tables in dev db
Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.APP_NAME)

app.include_router(products.router)
app.include_router(auth.router)
''',

    # ------------------
    # TESTS
    # ------------------
    "tests/conftest.py": '''import pytest
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
''',

    "tests/test_products.py": '''def test_create_product_success(client):
    response = client.post("/api/v1/products", json={"name": "Test Laptop", "price": 1500.0})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Laptop"
    assert data["price"] == 1500.0
    assert "id" in data

def test_create_product_invalid_data(client):
    # إرسال price كنص بدلاً من رقم (أو فقدان حقل مطلوب)
    response = client.post("/api/v1/products", json={"name": "Test Laptop"})
    assert response.status_code == 422 # Unprocessable Entity

def test_get_non_existent_product(client):
    response = client.get("/api/v1/products/999")
    assert response.status_code == 404

def test_delete_product(client):
    # إنشاء منتج أولاً
    create_res = client.post("/api/v1/products", json={"name": "To Delete", "price": 10.0})
    product_id = create_res.json()["id"]
    
    # حذف المنتج
    delete_res = client.delete(f"/api/v1/products/{product_id}")
    assert delete_res.status_code == 204
    
    # التأكد من أنه غير موجود
    get_res = client.get(f"/api/v1/products/{product_id}")
    assert get_res.status_code == 404
''',

    "tests/test_auth.py": '''def test_signup_success(client):
    response = client.post("/api/v1/auth/signup", json={"email": "test@test.com", "password": "pass"})
    assert response.status_code == 201
    assert response.json()["email"] == "test@test.com"
    assert "id" in response.json()

def test_signup_duplicate_email(client):
    client.post("/api/v1/auth/signup", json={"email": "test@test.com", "password": "pass"})
    response = client.post("/api/v1/auth/signup", json={"email": "test@test.com", "password": "newpass"})
    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered"

def test_login_wrong_password(client):
    client.post("/api/v1/auth/signup", json={"email": "test@test.com", "password": "pass"})
    response = client.post("/api/v1/auth/login", json={"email": "test@test.com", "password": "wrong"})
    assert response.status_code == 401

def test_access_me_without_token(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"

def test_access_me_with_valid_token(client):
    client.post("/api/v1/auth/signup", json={"email": "user@test.com", "password": "123"})
    login_res = client.post("/api/v1/auth/login", json={"email": "user@test.com", "password": "123"})
    token = login_res.json()["access_token"]
    
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "user@test.com"
'''
}

for rel_path, content in files.items():
    full_path = os.path.join(base_path, rel_path.replace("/", os.sep))
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

print("Tests and mock endpoints configured.")
