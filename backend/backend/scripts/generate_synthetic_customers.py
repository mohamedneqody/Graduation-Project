import asyncio
import uuid
import random
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

# Adjust path for running script from backend folder
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database.session import AsyncSessionLocal
from app.models.tenant import Tenant
from app.models.customer import Customer
from app.models.drug import Drug
from app.models.order import Order, OrderItem
from app.models.tracking import CustomerCycle
from app.domains.customer_cycle.service import recalculate_all_cycles

FIRST_NAMES = ["أحمد", "محمد", "محمود", "علي", "عمر", "حسن", "حسين", "إبراهيم", "طارق", "كريم", "مصطفى", "فاطمة", "مريم", "سارة", "هاجر", "نور", "ياسمين", "زينب", "أميرة", "منى", "دعاء", "عادل", "سامي", "هاني", "سمير", "رانيا", "هبة", "شيماء", "أسماء", "نهى"]
LAST_NAMES = ["عبد الله", "الرحمن", "سعيد", "صالح", "محمد", "أحمد", "حسين", "علي", "محمود", "توفيق", "سعد", "فاروق", "يوسف", "حسن", "سليمان", "إبراهيم", "رمضان", "السيد", "عيسى", "رضوان", "عثمان", "جاد"]

def generate_egyptian_phone():
    prefix = random.choice(["010", "011", "012", "015"])
    suffix = "".join(str(random.randint(0, 9)) for _ in range(8))
    return prefix + suffix

async def run():
    async with AsyncSessionLocal() as db:
        print("Starting synthetic data generation...")
        
        # 1. Ensure Tenant
        result = await db.execute(select(Tenant))
        tenant = result.scalar()
        if not tenant:
            print("Creating default test tenant...")
            tenant = Tenant(
                tenant_id=uuid.uuid4(),
                name="صيدلية الاختبار",
                subdomain="test-pharmacy"
            )
            db.add(tenant)
            await db.commit()
            await db.refresh(tenant)
        tenant_id = tenant.tenant_id
        
        # 2. Get Drugs
        result = await db.execute(select(Drug))
        all_drugs = result.scalars().all()
        
        chronic_drugs = [d for d in all_drugs if "مزمن" in (d.category or "") or d.is_chronic]
        regular_drugs = [d for d in all_drugs if d not in chronic_drugs]
        
        if not chronic_drugs:
            print("No chronic drugs found!")
            return
            
        print(f"Loaded {len(all_drugs)} drugs ({len(chronic_drugs)} chronic, {len(regular_drugs)} regular).")
        
        # We will generate 300 customers
        customers = []
        for _ in range(300):
            first = random.choice(FIRST_NAMES)
            last = random.choice(LAST_NAMES)
            full_name = f"{first} {last}"
            eng_prefix = "user" # simplified
            email = f"user_{uuid.uuid4().hex[:8]}@example.com"
            auth_user_id = uuid.uuid4()
            age_group = random.choice(["18-30", "31-45", "46-60", "60+"])
            preferred_channel = random.choices(["whatsapp", "email", "sms"], weights=[60, 25, 15], k=1)[0]
            
            c = Customer(
                customer_id=uuid.uuid4(),
                auth_user_id=auth_user_id,
                tenant_id=tenant_id,
                email=email,
                full_name=full_name,
                phone=generate_egyptian_phone(),
                age_group=age_group,
                preferred_channel=preferred_channel,
                is_active=True
            )
            customers.append(c)
        
        # Insert customers
        db.add_all(customers)
        await db.commit()
        print(f"Inserted {len(customers)} customers.")
        
        # 3. Generate Orders
        # 60% chronic = 180, 40% regular = 120
        chronic_customers = customers[:180]
        regular_customers = customers[180:]
        
        orders = []
        order_items = []
        
        now = datetime.now(timezone.utc)
        one_year_ago = now - timedelta(days=365)
        
        intended_cycles = {} # (cust_id, drug_id) -> int (intended average)
        
        # Process Chronic Customers
        for c in chronic_customers:
            num_chronic = random.choice([1, 2])
            selected_chronic = random.sample(chronic_drugs, min(num_chronic, len(chronic_drugs)))
            
            for d in selected_chronic:
                base_cycle = d.default_cycle_days or 30
                # Personal cycle: default +/- 1 to 4 days
                personal_cycle = base_cycle + random.randint(-4, 4)
                intended_cycles[(c.customer_id, d.drug_id)] = personal_cycle
                
                # Start backwards
                # Start with a date in the last few days
                current_date = now - timedelta(days=random.randint(0, personal_cycle))
                
                while current_date > one_year_ago:
                    order_id = uuid.uuid4()
                    o = Order(
                        order_id=order_id,
                        tenant_id=tenant_id,
                        customer_id=c.customer_id,
                        order_date=current_date,
                        status="completed",
                        channel=random.choice(["web", "whatsapp", "app"])
                    )
                    orders.append(o)
                    
                    qty = random.choices([1, 2], weights=[90, 10], k=1)[0]
                    price = float(d.base_price)
                    oi = OrderItem(
                        order_item_id=uuid.uuid4(),
                        order_id=order_id,
                        drug_id=d.drug_id,
                        quantity=qty,
                        price=price
                    )
                    order_items.append(oi)
                    
                    # Next order (backwards in time)
                    jitter = random.randint(-6, 6) # Jitter 
                    current_date = current_date - timedelta(days=personal_cycle + jitter)
                    
            # Add 1-3 random cross-purchases
            for _ in range(random.randint(1, 3)):
                rand_drug = random.choice(regular_drugs)
                rand_date = one_year_ago + timedelta(days=random.randint(0, 365))
                
                order_id = uuid.uuid4()
                orders.append(Order(
                    order_id=order_id, tenant_id=tenant_id, customer_id=c.customer_id,
                    order_date=rand_date, status="completed", channel=random.choice(["web", "whatsapp", "app"])
                ))
                order_items.append(OrderItem(
                    order_item_id=uuid.uuid4(), order_id=order_id, drug_id=rand_drug.drug_id,
                    quantity=random.choices([1, 2], weights=[80, 20], k=1)[0], price=float(rand_drug.base_price)
                ))
                
        # Process Regular Customers
        for c in regular_customers:
            # 2-5 random non-chronic
            num_orders = random.randint(2, 5)
            # Add 1-3 cross-purchases (as requested, total 3-8 random orders)
            num_orders += random.randint(1, 3)
            
            for _ in range(num_orders):
                rand_drug = random.choice(regular_drugs)
                rand_date = one_year_ago + timedelta(days=random.randint(0, 365))
                
                order_id = uuid.uuid4()
                orders.append(Order(
                    order_id=order_id, tenant_id=tenant_id, customer_id=c.customer_id,
                    order_date=rand_date, status="completed", channel=random.choice(["web", "whatsapp", "app"])
                ))
                order_items.append(OrderItem(
                    order_item_id=uuid.uuid4(), order_id=order_id, drug_id=rand_drug.drug_id,
                    quantity=random.choices([1, 2], weights=[80, 20], k=1)[0], price=float(rand_drug.base_price)
                ))
                
        print(f"Generated {len(orders)} orders and {len(order_items)} order items.")
        print("Saving to DB in bulk...")
        
        # Batch inserting orders and items to avoid memory issues if large
        batch_size = 1000
        for i in range(0, len(orders), batch_size):
            db.add_all(orders[i:i+batch_size])
        await db.commit()
        
        for i in range(0, len(order_items), batch_size):
            db.add_all(order_items[i:i+batch_size])
        await db.commit()
        print("Finished saving orders.")
        
        # 4. Recalculate all cycles
        print("Running recalculate_all_cycles...")
        summary = await recalculate_all_cycles(db)
        print(f"Recalculation Summary: Processed {summary.total_processed} pairs, Updated {summary.updated_count}.")
        
        # 5. Fetch 5 random chronic customers and verify
        print("\n=== Verification Report ===")
        sample_keys = random.sample(list(intended_cycles.keys()), min(5, len(intended_cycles)))
        for cust_id, drug_id in sample_keys:
            intended = intended_cycles[(cust_id, drug_id)]
            
            # Fetch actual calculated
            res = await db.execute(
                select(CustomerCycle)
                .where(CustomerCycle.customer_id == cust_id, CustomerCycle.drug_id == drug_id)
            )
            cycle = res.scalar()
            
            # Fetch names
            cust_name = (await db.execute(select(Customer.full_name).where(Customer.customer_id == cust_id))).scalar()
            drug_name = (await db.execute(select(Drug.name).where(Drug.drug_id == drug_id))).scalar()
            
            actual_avg = round(cycle.avg_cycle_days, 2) if cycle else "Not Calculated"
            
            print(f"Customer: {cust_name} | Drug: {drug_name}")
            print(f"  Intended Personal Cycle: {intended} days")
            print(f"  Calculated Average DB  : {actual_avg} days")
            print("-" * 30)

        print("Done.")

if __name__ == "__main__":
    asyncio.run(run())
