import asyncio
import os
import uuid
from datetime import datetime, timedelta, timezone
import sys
import traceback
sys.path.append(r"D:\Graduation Project\backend\backend")

from app.database.session import AsyncSessionLocal
from app.models.prescription import Prescription, PrescriptionAnalysis, PrescriptionItem
from app.models.tracking import AuditLog
from app.domains.prescriptions.router import execute_prescription_retention_cleanup
from sqlalchemy import select, text

async def main():
    try:
        test_user_id = uuid.uuid4()
        test_file_id = "test_delete_me_8932.jpg"
        test_file_path = f"uploads/{test_file_id}"
        
        os.makedirs("uploads", exist_ok=True)
        with open(test_file_path, "w") as f:
            f.write("dummy image data")
            
        print(f"Created dummy file: {test_file_path}", flush=True)

        # 1. Ensure tenant exists
        async with AsyncSessionLocal() as db:
            res = await db.execute(text("SELECT tenant_id FROM tenants LIMIT 1"))
            tenant_row = res.fetchone()
            
            if not tenant_row:
                print("Creating dummy tenant...", flush=True)
                test_tenant_id = uuid.uuid4()
                await db.execute(text(f"INSERT INTO tenants (tenant_id, name) VALUES ('{test_tenant_id}', 'Test')"))
                await db.commit()
            else:
                test_tenant_id = uuid.UUID(str(tenant_row[0]))
                
        print(f"Using tenant_id: {test_tenant_id}", flush=True)
                
        # 2. Insert dummy data > 30 days old
        async with AsyncSessionLocal() as db:
            old_date = datetime.now(timezone.utc) - timedelta(days=32)
            
            p = Prescription(
                file_id=test_file_id,
                tenant_id=test_tenant_id,
                uploaded_by=test_user_id,
                status="uploaded",
                created_at=old_date
            )
            db.add(p)
            await db.flush()
            
            analysis = PrescriptionAnalysis(
                prescription_id=p.id,
                provider="gemini",
                model="gemini-3.7-flash",
                status="completed",
                created_at=old_date
            )
            db.add(analysis)
            await db.flush()
            
            item = PrescriptionItem(
                analysis_id=analysis.id,
                raw_name="Test Drug 500mg",
                match_status="not_found",
                pharmacist_decision="pending"
            )
            db.add(item)
            await db.commit()
            
            presc_id = p.id
            print(f"Inserted Prescription ID: {presc_id} with created_at: {old_date}", flush=True)

        # 3. Run the deletion task
        async with AsyncSessionLocal() as db:
            result = await execute_prescription_retention_cleanup(db)
            print(f"Cleanup Result: {result}", flush=True)

        # 4. Verify DB and AuditLog
        async with AsyncSessionLocal() as db:
            # Check prescription
            res_p = await db.execute(select(Prescription).where(Prescription.id == presc_id))
            is_p_deleted = res_p.scalars().first() is None
            print(f"Prescription row deleted: {is_p_deleted}", flush=True)
            
            # Check file
            is_file_deleted = not os.path.exists(test_file_path)
            print(f"Physical file deleted: {is_file_deleted}", flush=True)
            
            # Check Audit Log
            res_a = await db.execute(select(AuditLog).where(AuditLog.target_entity == f"prescription:{presc_id}"))
            audit = res_a.scalars().first()
            
            if audit:
                print(f"AuditLog found! Action: {audit.action_type}, Tenant ID: {audit.tenant_id}, Actor: {audit.actor_id}, Entity: {audit.target_entity}", flush=True)
            else:
                print("AuditLog NOT found!", flush=True)
    except Exception as e:
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
