import asyncio
from sqlalchemy import select, func, text
from app.database.session import AsyncSessionLocal
from app.models.drug import Drug, DrugInteraction, DrugAffinity
from app.models.order import OrderItem, Order
from app.models.customer import Customer
from app.models.tracking import CustomerCycle, Notification, PendingReminder
from app.models.ab_test import ABTest, ABTestResult
from app.models.session import Session, Event

async def verify_all():
    async with AsyncSessionLocal() as session:
        print("=" * 60)
        print("  LIVE DATABASE VERIFICATION REPORT")
        print("  AI-COS Pharmacy — Generated:", __import__('datetime').datetime.now())
        print("=" * 60)

        # 1. Drugs
        drugs_total = await session.scalar(select(func.count(Drug.drug_id)))
        drugs_test = await session.scalar(
            select(func.count(Drug.drug_id)).where(Drug.name.like('Test Drug%'))
        )
        print(f"\n[DRUGS]")
        print(f"  Total drugs in DB          : {drugs_total}")
        print(f"  'Test Drug%' remaining     : {drugs_test}")

        # 2. Customers
        cust_total = await session.scalar(select(func.count(Customer.customer_id)))
        cust_synthetic = await session.scalar(
            select(func.count(Customer.customer_id))
            .where(Customer.email.like('%@example.com'))
        )
        cust_test = cust_total - cust_synthetic
        print(f"\n[CUSTOMERS]")
        print(f"  Total customers in DB      : {cust_total}")
        print(f"  Synthetic (@example.com)   : {cust_synthetic}")
        print(f"  E2E Test accounts (est.)   : {cust_test}")

        # 3. Drug Affinities
        affinities_count = await session.scalar(select(func.count(DrugAffinity.affinity_id)))
        print(f"\n[DRUG AFFINITIES (Cross-Sell)]")
        print(f"  Total affinity records     : {affinities_count}")

        # 4. Drug Interactions
        interactions_count = await session.scalar(select(func.count(DrugInteraction.interaction_id)))
        print(f"\n[DRUG INTERACTIONS]")
        print(f"  Total interaction records  : {interactions_count}")

        # 5. Orders & Order Items
        orders_total = await session.scalar(select(func.count(Order.order_id)))
        items_total = await session.scalar(select(func.count(OrderItem.order_item_id)))
        print(f"\n[ORDERS]")
        print(f"  Total orders               : {orders_total}")
        print(f"  Total order items          : {items_total}")

        # 6. Customer Cycles (composite PK — count via raw SQL)
        cycles_total = await session.scalar(
            select(func.count()).select_from(CustomerCycle)
        )
        print(f"\n[CUSTOMER CYCLES]")
        print(f"  Total cycle records        : {cycles_total}")

        # 7. Notifications
        notifs_total = await session.scalar(select(func.count(Notification.notification_id)))
        print(f"\n[NOTIFICATIONS]")
        print(f"  Total notification records : {notifs_total}")

        # 8. Pending Reminders
        reminders_total = await session.scalar(select(func.count(PendingReminder.reminder_id)))
        print(f"\n[PENDING REMINDERS]")
        print(f"  Total pending reminders    : {reminders_total}")

        # 9. ALL Drug names
        all_names = (await session.execute(select(Drug.name).order_by(Drug.name))).scalars().all()
        print(f"\n[DRUG NAMES — Full List ({len(all_names)} drugs)]")
        for i, name in enumerate(all_names, 1):
            print(f"  {i:3}. {name}")

        print("\n" + "=" * 60)
        print("  END OF VERIFICATION REPORT")
        print("=" * 60)

if __name__ == "__main__":
    asyncio.run(verify_all())
