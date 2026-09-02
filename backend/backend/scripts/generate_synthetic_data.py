import asyncio
import sys
import os
import uuid
from datetime import datetime, timedelta, date
from dotenv import load_dotenv

# إضافة المجلد الرئيسي للـ sys.path عشان نقدر نعمل import من app
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from app.database.session import AsyncSessionLocal
from app.models.tenant import Tenant
from app.models.customer import Customer
from app.models.drug import Drug
from app.models.order import Order, OrderItem
from app.models.tracking import CustomerCycle
from sqlalchemy import select

async def generate_data():
    async with AsyncSessionLocal() as session:
        # 1. إنشاء Tenant
        tenant_id = uuid.uuid4()
        tenant = Tenant(
            tenant_id=tenant_id,
            name="صيدلية الشفاء التجريبية",
            subdomain="alshifa-demo"
        )
        session.add(tenant)
        await session.flush()
        print("Tenant created.")

        # 2. إنشاء الأدوية
        drugs_data = [
            {"name": "Panadol Advance 500mg", "category": "مسكنات", "is_chronic": False, "base_price": 30.00, "default_cycle_days": 0},
            {"name": "Augmentin 1g", "category": "مضادات حيوية", "is_chronic": False, "base_price": 120.50, "default_cycle_days": 0},
            {"name": "Concor 5mg", "category": "أدوية الضغط", "is_chronic": True, "base_price": 55.00, "default_cycle_days": 30},
            {"name": "Lipitor 20mg", "category": "كوليسترول", "is_chronic": True, "base_price": 140.00, "default_cycle_days": 30},
            {"name": "Glucophage 1000mg", "category": "سكر", "is_chronic": True, "base_price": 45.00, "default_cycle_days": 30},
        ]
        
        drugs = []
        for d in drugs_data:
            drug = Drug(
                drug_id=uuid.uuid4(),
                name=d["name"],
                category=d["category"],
                is_chronic=d["is_chronic"],
                base_price=d["base_price"],
                default_cycle_days=d["default_cycle_days"]
            )
            drugs.append(drug)
            session.add(drug)
        await session.flush()
        print("Drugs created.")

        # 3. إنشاء عملاء
        customers_data = [
            {"email": "ahmed@example.com", "full_name": "أحمد محمود", "phone": "01000000001", "age_group": "30-45"},
            {"email": "sara@example.com", "full_name": "سارة علي", "phone": "01100000002", "age_group": "18-30"},
            {"email": "mohamed@example.com", "full_name": "محمد إبراهيم", "phone": "01200000003", "age_group": "45-60"},
        ]
        
        customers = []
        for c in customers_data:
            customer = Customer(
                customer_id=uuid.uuid4(),
                auth_user_id=uuid.uuid4(), # عشوائي للتجربة فقط
                tenant_id=tenant_id,
                email=c["email"],
                full_name=c["full_name"],
                phone=c["phone"],
                age_group=c["age_group"]
            )
            customers.append(customer)
            session.add(customer)
        print("Customers created.")

        await session.flush() # للحصول على الـ IDs
        
        # 4. إنشاء طلبات ودورات شراء (Customer Cycles)
        
        # طلب لأحمد (مسكن ومضاد حيوي)
        order1 = Order(order_id=uuid.uuid4(), tenant_id=tenant_id, customer_id=customers[0].customer_id)
        session.add(order1)
        session.add(OrderItem(order_item_id=uuid.uuid4(), order_id=order1.order_id, drug_id=drugs[0].drug_id, quantity=2, price=drugs[0].base_price))
        session.add(OrderItem(order_item_id=uuid.uuid4(), order_id=order1.order_id, drug_id=drugs[1].drug_id, quantity=1, price=drugs[1].base_price))

        # طلب لمحمد (أدوية ضغط وسكر مزمنة)
        order2 = Order(order_id=uuid.uuid4(), tenant_id=tenant_id, customer_id=customers[2].customer_id)
        session.add(order2)
        session.add(OrderItem(order_item_id=uuid.uuid4(), order_id=order2.order_id, drug_id=drugs[2].drug_id, quantity=1, price=drugs[2].base_price)) # Concor
        session.add(OrderItem(order_item_id=uuid.uuid4(), order_id=order2.order_id, drug_id=drugs[4].drug_id, quantity=2, price=drugs[4].base_price)) # Glucophage

        # دورة شراء لمحمد عشان الأدوية المزمنة
        cycle1 = CustomerCycle(
            customer_id=customers[2].customer_id,
            drug_id=drugs[2].drug_id,
            avg_cycle_days=30.0,
            last_purchase_date=date.today() - timedelta(days=5),
            reminder_day=date.today() + timedelta(days=23)
        )
        cycle2 = CustomerCycle(
            customer_id=customers[2].customer_id,
            drug_id=drugs[4].drug_id,
            avg_cycle_days=25.0,
            last_purchase_date=date.today() - timedelta(days=10),
            reminder_day=date.today() + timedelta(days=13)
        )
        session.add(cycle1)
        session.add(cycle2)
        print("Orders and Cycles created.")

        # حفظ كل التغييرات
        await session.commit()
        print("All data successfully committed to the database!")

if __name__ == "__main__":
    asyncio.run(generate_data())
