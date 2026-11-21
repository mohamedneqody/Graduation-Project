# -*- coding: utf-8 -*-
"""
Cura AI Pharmacy (صيدلية كيورا الذكية) — BIS Academic Defense Demonstration Script
══════════════════════════════════════════════════════════════
Automated verification for the 3 killer live defense scenarios:
  1. Regulatory Recall & Cryptographic WORM Ledger Integrity (EDA / Rogue-DBA)
  2. Clinical CDSS Duplicate Therapy Guard & Generic Substitution (Salt Normalization)
  3. Forensic Accounting Sentinel (Benford's Law, Nigrini MAD, Chi-Square, Smurfing)
"""
import sys
import os

# Add backend directory to sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Load backend/.env if available, or supply fallback mock settings for standalone demo
env_path = os.path.join(backend_dir, ".env")
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

os.environ.setdefault("DATABASE_URL", "postgresql://mock:mock@localhost:5432/mock")
os.environ.setdefault("NEXT_PUBLIC_SUPABASE_URL", "https://mock.supabase.co")
os.environ.setdefault("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY", "mock-publishable-key")

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import json
import hashlib
from datetime import datetime, timezone


def print_banner(title: str):
    print("\n" + "═" * 70)
    print(f" 🏛️ {title}")
    print("═" * 70)


def test_scenario_1_worm_ledger():
    print_banner("سيناريو 1: حوكمة سجل WORM المشفر ومقاومة تلاعب الـ Rogue DBA")
    from app.core.worm_ledger import append_entry, verify_file_integrity, read_ledger

    event_id = f"DEFENSE-DEMO-{datetime.now(timezone.utc).strftime('%H%M%S')}"
    now_iso = datetime.now(timezone.utc).isoformat()
    test_payload = json.dumps({"action": "quarantine_batch", "drug": "Concor 5mg", "batch": "EG-88210"}, sort_keys=True)
    payload_hash = hashlib.sha256(test_payload.encode("utf-8")).hexdigest()

    print(f"1. جاري إلحاق قيد حجر صحي جديد بالسجل الخارجي:")
    print(f"   • Event ID: {event_id}")
    print(f"   • Payload SHA-256: {payload_hash[:32]}...")

    entry = append_entry(event_id, now_iso, payload_hash)
    print(f"   • تم التوليد بنجاح:")
    print(f"     - Prev Hash: {entry['prev'][:24]}...")
    print(f"     - Line Hash: {entry['line_hash'][:24]}...")

    print(f"\n2. جاري التحقق من سلامة السلسلة التشفيرية للملف كاملاً (verify_file_integrity):")
    integrity = verify_file_integrity()
    print(f"   • إجمالي الأسطر بالسجل: {integrity['lines']}")
    print(f"   • هل السلسلة متصلة وسليمة 100%؟ {'✅ نعم (VALID)' if integrity['chain_valid'] else '❌ مكسورة'}")
    assert integrity["chain_valid"] is True, "WORM chain should be valid!"
    print("✅ نجح السيناريو الأول بنسبة 100%!")


def test_scenario_2_clinical_cdss():
    print_banner("سيناريو 2: الذكاء السريري CDSS — منع التكرار العلاجي وتطبيع الأملاح الكيميائية")
    from app.domains.drug.service import _extract_active_ingredients

    # 1. فحص تطبيع الأملاح الكيميائية
    ing1 = "Metformin Hydrochloride"
    ing2 = "Metformin"
    tokens1 = _extract_active_ingredients(ing1)
    tokens2 = _extract_active_ingredients(ing2)
    print(f"1. اختبار تطبيع الأملاح الصيدلانية:")
    print(f"   • المستحضر الأول: '{ing1}' -> بعد المعالجة: {tokens1}")
    print(f"   • المستحضر الثاني: '{ing2}' -> بعد المعالجة: {tokens2}")
    print(f"   • هل يتطابقان كبديلين متكافئين سريرياً؟ {'✅ نعم (متطابقان)' if tokens1 == tokens2 else '❌ غير متطابقين'}")
    assert tokens1 == tokens2, "Salt normalization must equate Metformin Hydrochloride with Metformin"

    # 2. فحص الأدوية المركبة المتعددة (+, /, &)
    combo1 = "Amoxicillin + Clavulanic Acid"
    combo2 = "Clavulanate Potassium / Amoxicillin Trihydrate"
    tokens_combo1 = _extract_active_ingredients(combo1)
    tokens_combo2 = _extract_active_ingredients(combo2)
    print(f"\n2. اختبار الأدوية المركبة مع تباين الأملاح وترتيب الصياغة:")
    print(f"   • المستحضر الأول: '{combo1}' -> {tokens_combo1}")
    print(f"   • المستحضر الثاني: '{combo2}' -> {tokens_combo2}")
    print(f"   • هل تم اكتشاف التكافؤ التام للبديلين؟ {'✅ نعم (متطابقان)' if tokens_combo1 == tokens_combo2 else '❌ غير متطابقين'}")
    assert tokens_combo1 == tokens_combo2, "Compound drugs with varied salt names and order must match!"
    print("✅ نجح السيناريو الثاني بنسبة 100%!")


def test_scenario_3_forensic_accounting():
    print_banner("سيناريو 3: المحاسبة الجنائية الرقابية — قانون بنفورد وتجزئة الاعتمادات")
    from app.domains.accounting.forensics import (
        calculate_benford_metrics,
        detect_threshold_avoidance,
        detect_round_number_clustering
    )

    # توليد عينة طبيعية طبقاً لقانون بنفورد (120 رقم مع فحص كوتشران N >= 110)
    import numpy as np
    np.random.seed(42)
    # توليد أرقام متوافقة مع التوزيع اللوغاريتمي
    benford_amounts = (10 ** np.random.uniform(1.0, 5.0, 150)).tolist()

    print("1. اختبار فحص قانون بنفورد (First-Digit Law):")
    res_benford = calculate_benford_metrics(benford_amounts)
    print(f"   • حجم العينة: {res_benford['sample_size']} عملية")
    print(f"   • كفاية العينة الإحصائية: {res_benford['sample_adequate']}")
    print(f"   • صلاحية كاي-تربيع (Cochran Criterion N >= 110): {res_benford['chi2_valid']}")
    print(f"   • انحراف نيجريني (Nigrini MAD): {res_benford['mad']}")
    print(f"   • الحكم الجنائي: {res_benford['conformity_status']} ({res_benford['message_ar']})")
    assert res_benford["sample_adequate"] is True
    assert res_benford["chi2_valid"] is True

    # 2. فحص كشف تجزئة المعاملات للتحايل على سقف الاعتماد (Structuring / Smurfing)
    # إنشاء مصفوفة ملوثة بـ 20 عملية بقيمة 4950 ج.م تحت سقف 5000 ج.م
    suspicious_amounts = [4950.0] * 20 + [150.0, 220.0, 850.0, 1200.0, 3400.0]
    res_avoid = detect_threshold_avoidance(suspicious_amounts, limits=[5000.0])
    print(f"\n2. اختبار كشف التجزئة والتحايل (Smurfing Sentinel):")
    print(f"   • المعاملات المشتبه بها قرب سقف 5000 ج.م: {res_avoid['total_clustered_transactions']}")
    print(f"   • نسبة العمليات المشبوهة: {res_avoid['cluster_pct']}%")
    print(f"   • هل تم إطلاق الإنذار الجنائي؟ {'🚨 نعم (شبهة احتيال)' if res_avoid['is_anomalous'] else 'طبيعي'}")
    print(f"   • تقرير المدقق: {res_avoid['message_ar']}")
    assert res_avoid["is_anomalous"] is True

    print("✅ نجح السيناريو الثالث بنسبة 100%!")


if __name__ == "__main__":
    print("\n🚀 بدء الفحص التجريبي لسيناريوهات مناقشة التخرج لـ صيدلية كيورا الذكية (Cura AI Pharmacy)...")
    try:
        test_scenario_1_worm_ledger()
        test_scenario_2_clinical_cdss()
        test_scenario_3_forensic_accounting()
        print("\n" + "🌟" * 35)
        print(" 🎯 النتيجة النهائية: كافة السيناريوهات الثلاثة ناجحة ومطابقة لأعلى معايير الـ BIS والـ CDSS!")
        print(" 🏆 النظام جاهز بالكامل للعرض الحي أمام لجنة التحكيم الأكاديمية للحصول على 100 / 100.")
        print("🌟" * 35 + "\n")
    except Exception as e:
        print(f"\n❌ حدث خطأ أثناء تشغيل السيناريوهات: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
