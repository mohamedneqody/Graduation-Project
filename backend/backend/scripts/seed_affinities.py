"""
seed_affinities.py — بذر جدول drug_affinities ببيانات طبية واقعية

الأزواج الطبية المنطقية (complementary):
- أدوية ضغط + Omega Life 3 / Cal-D-Vita (قلب وضغط + فيتامينات)
- أدوية سكر + Omega Life 3 (سكري + أوميجا - علاقة طبية معروفة)
- مضادات حيوية + Bio Vit-C / Probiotics (دعم مناعة أثناء العلاج)
- Zyrtec/حساسية + Coldrex/Comtrex (حساسية + نزلات برد شائعة التصاحب)
- Nexium/Rani (هضمي) + Brufen/Cataflam (مسكنات تسبب حرقة معدة)
"""
import asyncio
import uuid
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text

import sys, os
sys.path.insert(0, os.getcwd())
from app.core.config import settings

# ── Drug IDs من قاعدة البيانات ──────────────────────────────────────────────

# مزمن - ضغط
AMLOPRES_5MG          = "52ae654f-2232-4950-a090-41d4caf17648"
CAPOTEN_25MG          = "8bc0afe6-13f6-4cd5-b059-a827610b05c2"
CONCOR_5MG            = "9e107dad-9bc0-45da-888d-adfff64d5c2e"
DIOVAN_80MG           = "61239b02-7e72-4600-a5bd-8febcd300db3"
NORVASC_5MG           = "1e6fa617-b52a-42ba-be34-cd88b63488ac"
PROTECTOPRIL_8MG      = "e6116545-fb2b-47e5-b366-0541c8cc5d1f"
SINOPRIL_5MG          = "87c33927-27db-4f6d-a019-8cbbecbeacc1"

# مزمن - سكر
AMARYL_2MG            = "587cfb9b-93b4-42f6-9433-302c4dce09a7"
DIAMICRON_MR          = "942ff7a7-eeb7-4141-9619-0b70651ba8b9"
GLUCOPHAGE_500MG      = "08383335-38d4-48fc-a632-11eeae52ba9b"
GALVUS_MET            = "7089b2c6-100f-4863-8dc8-ab3e9f3a67f1"

# مزمن - كوليسترول
CRESTOR_10MG          = "8983f821-8918-4d47-ad66-63fa67a62d9a"
LIPITOR_20MG          = "a8354562-ef8b-4cb7-860d-7011b37a7c9f"

# مضادات حيوية
AUGMENTIN_1G          = "8eff60b6-387a-429f-b988-88832255dc9b"
AMOCLAN_1G            = "3d4cc3c5-b61d-4414-b75e-01bc09a4fef1"
ZINNAT_500MG          = "70ef0f4d-5a3f-4668-8daf-fa0fadda27fc"
ZATHROTRUE_500MG      = "cae6be63-d55c-44bf-96e1-f543c0d77f53"

# مسكنات
BRUFEN_400MG          = "82117897-0959-480e-b334-1d7af8c6b954"
CATAFLAM_50MG         = "73871daf-c618-466b-ac12-54bc6ff2e70d"
PANADOL_EXTRA         = "4f75b481-742a-4afe-a986-ea8f894cd198"

# جهاز هضمي
NEXIUM_40MG           = "ecb94d4e-1311-4dd5-aaa9-77ffd97ea4cb"
RANI_150MG            = "8a2e2413-1557-4a9a-a67d-bbb01e62acd7"
MOTILIUM_10MG         = "741f5636-b44f-48b4-b6a1-5bd6f879c464"

# حساسية
ZYRTEC_10MG           = "82fb6c84-428d-410f-9f10-849a67106bc2"
ALERID_10MG           = "028a5fb1-b76e-49e9-89d2-670ddff1dd7d"
TELFAST               = "93afb15e-595e-4884-902f-13e67731a89f"

# نزلات برد
COLDREX               = "c56b3e25-f0d4-4b9d-96d0-1395238d6bf1"
COMTREX               = "11a6c1ef-19b0-427e-830d-7886cb008c2a"

# فيتامينات
OMEGA_LIFE_3          = "d9b147bb-eea5-4fa7-a165-b70084a86642"
BIO_VIT_C             = "cb8cea38-3dd5-4562-8412-607156b68653"
CAL_D_VITA            = "ef5b44f3-dadf-454a-ab86-295601817cd1"
ZAMCILLUS_PROBIOTIC   = "4c383950-f106-4de3-80dd-7d0899944d3f"
ZINOBACILLY_DROPS     = "8f7681e1-dd74-4e7b-8daf-8e6270e73de5"
ZINC_ACID             = "84da9567-9da4-4d05-b4fd-a73de86a1fd8"

# ── تعريف الأزواج (drug_a, drug_b, confidence) ──────────────────────────────
# القيد: drug_id_a < drug_id_b (مقارنة نصية UUID)

RAW_PAIRS = [
    # 1. أدوية ضغط ← Omega Life 3 (أوميجا تدعم صحة القلب والأوعية)
    (CONCOR_5MG,     OMEGA_LIFE_3,  0.85, "complementary", "Omega-3 يدعم صحة القلب مع أدوية الضغط"),
    (NORVASC_5MG,    OMEGA_LIFE_3,  0.82, "complementary", "Omega-3 يدعم صحة القلب مع أدوية الضغط"),
    (SINOPRIL_5MG,   OMEGA_LIFE_3,  0.80, "complementary", "Omega-3 يدعم صحة القلب مع أدوية الضغط"),
    (DIOVAN_80MG,    OMEGA_LIFE_3,  0.83, "complementary", "Omega-3 يدعم صحة القلب مع أدوية الضغط"),
    (AMLOPRES_5MG,   OMEGA_LIFE_3,  0.81, "complementary", "Omega-3 يدعم صحة القلب مع أدوية الضغط"),

    # 2. أدوية ضغط ← Cal-D-Vita (كالسيوم + فيتامين D يدعم القلب والعظام)
    (CONCOR_5MG,     CAL_D_VITA,   0.78, "complementary", "كالسيوم وفيتامين D مع أدوية الضغط"),
    (NORVASC_5MG,    CAL_D_VITA,   0.76, "complementary", "كالسيوم وفيتامين D مع أدوية الضغط"),
    (DIOVAN_80MG,    CAL_D_VITA,   0.75, "complementary", "كالسيوم وفيتامين D مع أدوية الضغط"),

    # 3. أدوية سكر ← Omega Life 3 (الأوميجا يخفف مقاومة الأنسولين)
    (AMARYL_2MG,     OMEGA_LIFE_3,  0.88, "complementary", "Omega-3 يُحسِّن حساسية الأنسولين في السكري"),
    (GLUCOPHAGE_500MG, OMEGA_LIFE_3, 0.90, "complementary", "أعلى ثقة: الميتفورمين + أوميجا يخفض الدهون المرتبطة بالسكري"),
    (DIAMICRON_MR,   OMEGA_LIFE_3,  0.85, "complementary", "Omega-3 يُحسِّن حساسية الأنسولين في السكري"),
    (GALVUS_MET,     OMEGA_LIFE_3,  0.83, "complementary", "Omega-3 يُحسِّن حساسية الأنسولين في السكري"),

    # 4. كوليسترول ← Omega Life 3 (مكمل رئيسي مع الستاتين)
    (CRESTOR_10MG,   OMEGA_LIFE_3,  0.87, "complementary", "الأوميجا يخفض الدهون الثلاثية كمكمل مع الستاتين"),
    (LIPITOR_20MG,   OMEGA_LIFE_3,  0.86, "complementary", "الأوميجا يخفض الدهون الثلاثية كمكمل مع الستاتين"),

    # 5. مضادات حيوية ← Bio Vit-C (فيتامين C يدعم المناعة أثناء العلاج)
    (AUGMENTIN_1G,   BIO_VIT_C,     0.82, "complementary", "فيتامين C يدعم المناعة أثناء العلاج بالمضاد الحيوي"),
    (AMOCLAN_1G,     BIO_VIT_C,     0.80, "complementary", "فيتامين C يدعم المناعة أثناء العلاج بالمضاد الحيوي"),
    (ZINNAT_500MG,   BIO_VIT_C,     0.78, "complementary", "فيتامين C يدعم المناعة أثناء العلاج بالمضاد الحيوي"),
    (ZATHROTRUE_500MG, BIO_VIT_C,   0.79, "complementary", "فيتامين C يدعم المناعة أثناء العلاج بالمضاد الحيوي"),

    # 6. مضادات حيوية ← Probiotics (يستعيد البكتيريا النافعة التي تدمرها المضادات)
    (AUGMENTIN_1G,   ZAMCILLUS_PROBIOTIC, 0.90, "complementary", "Probiotic ضروري مع Augmentin لحماية الفلورا المعوية"),
    (AMOCLAN_1G,     ZINOBACILLY_DROPS,   0.88, "complementary", "Probiotic يحمي الجهاز الهضمي من تأثير المضاد الحيوي"),
    (ZINNAT_500MG,   ZAMCILLUS_PROBIOTIC, 0.85, "complementary", "Probiotic مع المضاد الحيوي يقلل الإسهال الجانبي"),
    (ZATHROTRUE_500MG, ZAMCILLUS_PROBIOTIC, 0.83, "complementary", "Probiotic يستعيد التوازن البكتيري بعد المضاد الحيوي"),

    # 7. Zyrtec/Alerid (حساسية) ← Coldrex/Comtrex (نزلات برد غالباً مصحوبة بأعراض حساسية)
    (COLDREX,        ZYRTEC_10MG,   0.80, "complementary", "Zyrtec يعالج مكوّن الحساسية في نزلات البرد"),
    (COMTREX,        ZYRTEC_10MG,   0.78, "complementary", "Zyrtec يعالج مكوّن الحساسية في نزلات البرد"),
    (ALERID_10MG,    COMTREX,       0.76, "complementary", "مضاد الحساسية مع علاج البرد: تصاحب شائع"),
    (ALERID_10MG,    COLDREX,       0.77, "complementary", "مضاد الحساسية مع علاج البرد: تصاحب شائع"),
    (TELFAST,        COLDREX,       0.75, "complementary", "مضاد الحساسية مع علاج البرد: تصاحب شائع"),

    # 8. Nexium/Rani (هضمي حماية) ← Brufen/Cataflam (NSAIDs تسبب حرقة المعدة)
    (BRUFEN_400MG,   NEXIUM_40MG,   0.92, "complementary", "Nexium ضروري لحماية المعدة عند استخدام Brufen (NSAID)"),
    (BRUFEN_400MG,   RANI_150MG,    0.88, "complementary", "Rani يحمي المعدة من تأثير Brufen الحمضي"),
    (CATAFLAM_50MG,  NEXIUM_40MG,   0.90, "complementary", "Nexium ضروري لحماية المعدة عند استخدام Cataflam"),
    (CATAFLAM_50MG,  RANI_150MG,    0.85, "complementary", "Rani يحمي المعدة من تأثير Cataflam"),

    # 9. مضادات حيوية ← Zinc (الزنك يدعم المناعة والشفاء)
    (AUGMENTIN_1G,   ZINC_ACID,     0.75, "complementary", "الزنك يدعم جهاز المناعة ويُسرِّع الشفاء"),
    (AMOCLAN_1G,     ZINC_ACID,     0.73, "complementary", "الزنك يدعم جهاز المناعة ويُسرِّع الشفاء"),
]


def _sort_pair(a: str, b: str):
    """يضمن أن drug_id_a < drug_id_b دائماً (نفس قيد CheckConstraint)."""
    return (a, b) if a < b else (b, a)


async def seed():
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = async_sessionmaker(engine)

    async with async_session() as s:
        # احذف أي بيانات قديمة قبل البذر
        await s.execute(text("DELETE FROM drug_affinities"))

        inserted = 0
        for raw in RAW_PAIRS:
            a_raw, b_raw, score, atype, _desc = raw
            a, b = _sort_pair(a_raw, b_raw)

            # تحقق من وجود الدواءين في DB قبل الإدراج
            check = await s.execute(
                text("SELECT COUNT(*) FROM drugs WHERE drug_id IN (:a, :b)"),
                {"a": a, "b": b},
            )
            if check.scalar() < 2:
                print(f"⚠️  تجاوز — أحد الأدوية غير موجود: {a[:8]}...  {b[:8]}...")
                continue

            await s.execute(
                text("""
                    INSERT INTO drug_affinities
                        (affinity_id, drug_id_a, drug_id_b, affinity_type, confidence_score)
                    VALUES
                        (:id, :a, :b, :atype, :score)
                    ON CONFLICT ON CONSTRAINT uq_affinity_pair DO NOTHING
                """),
                {
                    "id": str(uuid.uuid4()),
                    "a": a,
                    "b": b,
                    "atype": atype,
                    "score": score,
                },
            )
            inserted += 1
            print(f"✅  {_desc[:55]:55s}  conf={score}")

        await s.commit()

        count = (await s.execute(text("SELECT COUNT(*) FROM drug_affinities"))).scalar()
        print(f"\n═══════════════════════════════════════════")
        print(f"  إجمالي الأزواج المُدرَجة: {count}")
        print(f"═══════════════════════════════════════════")


if __name__ == "__main__":
    asyncio.run(seed())
