from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from redis import asyncio as aioredis
from app.core.config import settings
from app.core.logging import setup_logging
from app.domains.customer.router import router as customer_router
from app.domains.drug.router import router as drug_router, internal_router as drug_internal_router
from app.domains.order.router import router as order_router
from app.domains.notification.router import router as notification_router
from app.domains.files.router import router as files_router
from app.domains.prescriptions.router import router as prescriptions_router
from app.domains.ai.router import router as ai_router
from app.domains.webhooks.router import router as webhooks_router
from app.domains.customer_cycle.router import router as customer_cycle_router
from app.domains.prediction.router import router as prediction_router
from app.domains.analytics.router import router as analytics_router
from app.domains.governance.router import router as governance_router, internal_router as governance_internal_router
from app.domains.inventory.router import router as inventory_router
from app.domains.agents.router import router as agents_router
from app.domains.auth.router import router as auth_router

setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize InMemory Cache
    FastAPICache.init(InMemoryBackend(), prefix="fastapi-cache")
    yield
    # Clean up can go here

app = FastAPI(title="AI-COS Pharmacy Backend", lifespan=lifespan)

from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from app.core.rate_limit import limiter

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_origin_regex=r"http://.*:3000",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi import Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from app.core.exceptions import AppException

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

@app.exception_handler(IntegrityError)
async def sqlalchemy_integrity_error_handler(request: Request, exc: IntegrityError):
    # This catches Supabase/PostgreSQL Unique Violation errors (e.g. duplicate email)
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": "A database conflict occurred. The resource might already exist."},
    )

app.include_router(customer_router, prefix="/api/v1/customers", tags=["Customers"])
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(drug_router, prefix="/api/v1/drugs", tags=["Drugs"])
app.include_router(drug_internal_router, prefix="/internal/drugs", tags=["Internal Drugs"])
app.include_router(order_router, prefix="/api/v1/orders", tags=["Orders"])
app.include_router(notification_router, prefix="/internal/notifications", tags=["Notifications"])
app.include_router(files_router, prefix="/api/v1/files", tags=["Files"])
app.include_router(prescriptions_router, tags=["Prescriptions"])
app.include_router(ai_router, prefix="/api/v1/ai", tags=["AI Integration"])
app.include_router(webhooks_router, prefix="/api/v1/webhooks", tags=["Webhooks"])
app.include_router(customer_cycle_router, prefix="/internal/cycles", tags=["Internal Cycles"])
app.include_router(prediction_router, prefix="/api/v1/predictions", tags=["ML Predictions"])
app.include_router(analytics_router, prefix="/api/v1/analytics", tags=["Analytics"])
app.include_router(governance_router, prefix="/api/v1/governance", tags=["Governance (FR-07 + FR-08)"])
app.include_router(governance_internal_router, prefix="/internal/governance", tags=["Internal Governance (n8n)"])
app.include_router(agents_router, prefix="/api/v1/agents", tags=["Multi-Agent Platform (Req 13)"])
app.include_router(inventory_router, prefix="/api/v1/inventory", tags=["Inventory"])

from app.domains.tracking.router import events_router, customer_events_router
app.include_router(events_router, prefix="/api/v1/events", tags=["Tracking"])
app.include_router(customer_events_router, prefix="/api/v1/customers", tags=["Tracking (Customers)"])

@app.get("/health")
async def health_check():
    return {"status": "ok", "db_url_configured": bool(settings.DATABASE_URL)}
