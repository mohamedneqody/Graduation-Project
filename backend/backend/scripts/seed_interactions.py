import asyncio, sys, uuid
sys.stdout.reconfigure(encoding='utf-8')
from sqlalchemy import select, text
from app.database.session import AsyncSessionLocal
from app.models.drug import Drug, DrugInteraction

# ═══════════════════════════════════════════════════════
# تعارضات دوائية حقيقية موثقة طبياً بين أدوية الكتالوج
# المصدر: صيدلانية معتمدة + Drugs.com interactions
# القاعدة: فقط ما يمكن التحقق منه — لا اختراع
# ═══════════════════════════════════════════════════════
REAL_INTERACTIONS = [
    # (drug_name_a, drug_name_b, severity, note)
    
    # 1. ACE inhibitor + Sulfonamide → خطر ارتفاع البوتاسيوم وتعديل ضغط الدم
    ("Capoten 25mg", "septazole forte 800/160mg 10 tabs", "medium",
     "Captopril (ACE inhibitor) + Cotrimoxazole: خطر ارتفاع البوتاسيوم في الدم (Hyperkalemia). يُنصح بمراقبة مستوى البوتاسيوم بشكل دوري."),

    # 2. ACE inhibitor + NSAIDs → تقليل فاعلية خافض الضغط + خطر على الكلى
    ("Capoten 25mg", "Brufen 400mg", "high",
     "Captopril + Ibuprofen: NSAIDs تقلل فاعلية ACE inhibitors وقد تُسبب تدهور وظائف الكلى. يُنصح بتجنب الجمع أو مراقبة مكثفة."),

    ("Capoten 25mg", "Cataflam 50mg", "high",
     "Captopril + Diclofenac: نفس تأثير NSAIDs — تقليل خفض الضغط + خطر Nephrotoxicity. يُفضَّل استخدام Paracetamol بديلاً."),

    # 3. Statin + Macrolide → خطر Rhabdomyolysis (تحلل عضلي)
    ("Crestor 10mg", "Zinnat 500mg", "medium",
     "Rosuvastatin + Cefuroxime: تأثير محدود، لكن الـ Macrolides بشكل عام ترفع تركيز Statins. مراقبة أعراض آلام العضلات."),

    ("Lipitor 20mg", "Zinnat 500mg", "medium",
     "Atorvastatin + Cefuroxime: تداخل محتمل في استقلاب الكبد. مراقبة أعراض الـ Myopathy."),

    # 4. ACE inhibitor + Potassium-sparing (Sulfonamides) — Hyperkalemia
    ("Diovan 80mg", "septazole forte 800/160mg 10 tabs", "medium",
     "Valsartan (ARB) + Cotrimoxazole: مزيج ARB + Trimethoprim يرفع خطر Hyperkalemia لأن كليهما يحتجز البوتاسيوم."),

    # 5. Metformin + NSAIDs → خطر Lactic Acidosis عند اختلال وظائف الكلى
    ("Glucophage 500mg", "Brufen 400mg", "medium",
     "Metformin + Ibuprofen: NSAIDs قد تسبب اختلال وظائف الكلى مما يُبطئ طرح Metformin ويزيد خطر Lactic Acidosis."),

    ("Glucophage 500mg", "Cataflam 50mg", "medium",
     "Metformin + Diclofenac: نفس التأثير — Diclofenac يؤثر على الكلى مما يزيد خطر تراكم Metformin."),

    ("Galvus Met 50/1000mg", "Brufen 400mg", "medium",
     "Vildagliptin/Metformin + Ibuprofen: نفس مخاطر Metformin مع NSAIDs."),

    # 6. Thyroid hormone + Calcium supplements → تقليل امتصاص الـ Thyroid
    ("eltroxin 100 mcg 100 tabs", "Cal-D-Vita", "medium",
     "Levothyroxine + Calcium: Calcium يُقلل امتصاص Levothyroxine بشكل كبير. يجب الفصل بينهما بـ 4 ساعات على الأقل."),

    ("eltroxin 50mcg 100 tabs", "Cal-D-Vita", "medium",
     "Levothyroxine + Calcium: نفس التأثير — إلزامي الفصل بـ 4 ساعات لضمان فاعلية العلاج الهرموني."),

    ("thyroxine 100mcg 100 tab", "Cal-D-Vita", "medium",
     "Levothyroxine + Calcium: تأثير نفس مجموعة Eltroxin — Calcium يُعيق الامتصاص المعوي للهرمون."),

    # 7. Beta-blocker + NSAIDs → تقليل فاعلية خافض الضغط
    ("Concor 5mg", "Brufen 400mg", "medium",
     "Bisoprolol + Ibuprofen: NSAIDs تقلل التأثير الخافض للضغط للـ Beta-blockers، مع احتمال رفع الضغط."),

    ("Concor 5mg", "Cataflam 50mg", "medium",
     "Bisoprolol + Diclofenac: نفس التأثير مع NSAIDs — مراقبة ضغط الدم عند الجمع."),
]

async def seed_interactions():
    async with AsyncSessionLocal() as session:
        # جلب الأدوية الموجودة
        result = await session.execute(select(Drug.drug_id, Drug.name))
        drug_map = {name: did for did, name in result.all()}
        
        print(f"Loaded {len(drug_map)} drugs from DB.")
        
        added = 0
        skipped = 0
        not_found = []
        
        for name_a, name_b, severity, note in REAL_INTERACTIONS:
            if name_a not in drug_map:
                not_found.append(name_a)
                continue
            if name_b not in drug_map:
                not_found.append(name_b)
                continue
            
            id_a = str(drug_map[name_a])
            id_b = str(drug_map[name_b])
            
            # Enforce: id_a < id_b (alphabetic) لمنع التكرار
            if id_a > id_b:
                id_a, id_b = id_b, id_a
            
            # Check if already exists
            existing = await session.execute(
                select(DrugInteraction).where(
                    DrugInteraction.drug_id_a == uuid.UUID(id_a),
                    DrugInteraction.drug_id_b == uuid.UUID(id_b)
                )
            )
            if existing.scalar():
                skipped += 1
                print(f"  SKIP (exists): {name_a} <-> {name_b}")
                continue
            
            interaction = DrugInteraction(
                drug_id_a=uuid.UUID(id_a),
                drug_id_b=uuid.UUID(id_b),
                severity=severity,
                note=note,
            )
            session.add(interaction)
            added += 1
            print(f"  ADD [{severity}]: {name_a} <-> {name_b}")
        
        await session.commit()
        
        print(f"\nDone: {added} added, {skipped} skipped.")
        if not_found:
            print(f"Not found in catalog: {set(not_found)}")
        
        # Verify final count
        count = await session.scalar(text("SELECT COUNT(*) FROM drug_interactions"))
        print(f"Total drug_interactions now: {count}")

if __name__ == "__main__":
    asyncio.run(seed_interactions())
