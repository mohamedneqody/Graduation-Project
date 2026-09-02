import os

base_path = r"d:\Graduation Project\backend\backend\app\domains\auth"

files = {
    "__init__.py": "",
    "schemas.py": '''from pydantic import BaseModel, EmailStr
from typing import Optional

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
''',
    "service.py": '''from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.exceptions import UnauthorizedError, BadRequestError
from . import schemas

# Mock user database since we don't have a real users table defined yet in Supabase for auth
# (Usually Supabase handles Auth externally, but we are doing local JWT mapping as an example)
FAKE_USER_DB = {}

async def register_user(user: schemas.UserCreate, db: AsyncSession):
    if user.email in FAKE_USER_DB:
        raise BadRequestError("Email already registered")
        
    hashed_password = get_password_hash(user.password)
    FAKE_USER_DB[user.email] = {
        "email": user.email,
        "hashed_password": hashed_password,
        "id": "1234-5678-uuid"
    }
    return {"message": "User registered successfully"}

async def authenticate_user(user: schemas.UserCreate, db: AsyncSession):
    db_user = FAKE_USER_DB.get(user.email)
    if not db_user:
        raise UnauthorizedError("Incorrect email or password")
        
    if not verify_password(user.password, db_user["hashed_password"]):
        raise UnauthorizedError("Incorrect email or password")
        
    access_token = create_access_token(subject=db_user["id"])
    return {"access_token": access_token, "token_type": "bearer"}
''',
    "router.py": '''from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.dependencies.auth import get_current_user
from . import schemas, service

router = APIRouter()

@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(user: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    return await service.register_user(user, db)

@router.post("/login", response_model=schemas.Token)
async def login(user: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    return await service.authenticate_user(user, db)

@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return {"current_user": current_user}
'''
}

for name, content in files.items():
    with open(os.path.join(base_path, name), "w", encoding="utf-8") as f:
        f.write(content)
