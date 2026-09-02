import os

domains = ["customer", "drug", "order", "notification"]
base_dir = r"d:\Graduation Project\backend\backend\app\domains"

schemas_content = """from pydantic import BaseModel

class HealthCheckOut(BaseModel):
    status: str
"""

service_content = """from sqlalchemy.ext.asyncio import AsyncSession

async def check_health(db: AsyncSession) -> dict:
    return {"status": "ok"}
"""

router_content = """from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from . import schemas, service

router = APIRouter()

@router.get("/health", response_model=schemas.HealthCheckOut)
async def health_check(db: AsyncSession = Depends(get_db)):
    return await service.check_health(db)
"""

for domain in domains:
    domain_path = os.path.join(base_dir, domain)
    os.makedirs(domain_path, exist_ok=True)
    
    with open(os.path.join(domain_path, "schemas.py"), "w", encoding="utf-8") as f:
        f.write(schemas_content)
        
    with open(os.path.join(domain_path, "service.py"), "w", encoding="utf-8") as f:
        f.write(service_content)
        
    with open(os.path.join(domain_path, "router.py"), "w", encoding="utf-8") as f:
        f.write(router_content)

print("Domains scaffolded successfully.")
