import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.main import app as fastapi_app
from app.database.session import get_db, Base
import app.models  # to ensure models are registered with Base

# Test database connection string (matches docker-compose.test.yml)
TEST_DATABASE_URL = "postgresql+asyncpg://test_user:test_password@localhost:55432/pharmacy_test"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestingSessionLocal() as session:
        yield session

# Override the database dependency
fastapi_app.dependency_overrides[get_db] = override_get_db

@pytest_asyncio.fixture(scope="session", loop_scope="session", autouse=True)
async def setup_test_db():
    # Setup test database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        from sqlalchemy import text
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    # Teardown
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest_asyncio.fixture
async def db_session():
    async with TestingSessionLocal() as session:
        yield session

@pytest.fixture
def client():
    # Synchronous test client (good for testing endpoints without explicit async httpx calls)
    with TestClient(fastapi_app) as c:
        yield c

@pytest_asyncio.fixture
async def async_client():
    # Asynchronous test client using HTTPX
    async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://test") as c:
        yield c
