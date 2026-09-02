"""
B1 — Seed Knowledge Base (RAG)
=================================
يجلب كل الأدوية من جدول drugs ويُنشئ نصوص معرفة آمنة ومستندة فقط لما في DB.

القاعدة الصارمة:
- لا نخترع معلومات طبية (جرعات، آثار جانبية، تعارضات) غير موجودة في DB.
- كل نص يحتوي فقط: الاسم، الفئة، هل مزمن، دورة الشراء الافتراضية، السعر.
- السياسات مُوضَّحة صراحةً كـ [نص سياسة تجريبي].

يُشغَّل مرة واحدة أو عند إضافة أدوية جديدة.
"""
import asyncio
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
from uuid import uuid4

# أضف مسار backend للـ sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import select, delete, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings
from app.models.drug import Drug
from app.models.knowledge import KnowledgeChunk

# ── إعداد الاتصال ─────────────────────────────────────────────────────────
engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

# Tenant placeholder — في بيئة multi-tenant حقيقية يُمرَّر tenant_id فعلي
DEFAULT_TENANT_ID = "00000000-0000-0000-0000-000000000001"

# Embedding model
from sentence_transformers import SentenceTransformer
print("⏳ تحميل نموذج الـ Embedding...")
encoder = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
print("✅ النموذج جاهز")


def _build_drug_text(drug: Drug) -> str:
    """
    يبني نص معرفة آمناً من بيانات الدواء الموجودة في DB فقط.
    لا يُضاف أي معلومة طبية غير مستندة لجدول drugs.
    """
    chronic_note = (
        "يُصنَّف كدواء مزمن يحتاج التزامًا بالمواعيد ولا يجب التوقف عنه فجأة بدون استشارة طبية."
        if drug.is_chronic
        else "يُصنَّف كدواء غير مزمن."
    )

    return (
        f"اسم الدواء: {drug.name}\n"
        f"الفئة الطبية: {drug.category}\n"
        f"{chronic_note}\n"
        f"دورة الشراء الافتراضية: كل {drug.default_cycle_days} يوم تقريباً.\n"
        f"السعر الأساسي: {float(drug.base_price):.2f} ج.م.\n"
        f"[المعلومات أعلاه مستخرجة من كتالوج الصيدلية الرسمي فقط — "
        f"لا تتضمن جرعات أو آثاراً جانبية أو تعارضات دوائية.]"
    )


# ── سياسات عامة للمتجر (placeholder واضح) ───────────────────────────────
STORE_POLICIES = [
    {
        "source_type": "policy",
        "content": (
            "[نص سياسة تجريبي — غير مُلزم ولا يمثل سياسة حقيقية]\n"
            "سياسة التوصيل: يتم التوصيل خلال 1-3 أيام عمل داخل المدينة. "
            "للطلبات خارج المحافظة قد تصل مدة التوصيل 3-5 أيام. "
            "الحد الأدنى للطلب المجاني التوصيل: 200 ج.م."
        ),
    },
    {
        "source_type": "policy",
        "content": (
            "[نص سياسة تجريبي — غير مُلزم ولا يمثل سياسة حقيقية]\n"
            "سياسة الإرجاع: يُقبَل إرجاع المنتجات غير المستخدمة خلال 7 أيام من الاستلام. "
            "لا يُقبَل إرجاع الأدوية المخصصة للتبريد أو المفتوحة. "
            "للمزيد تواصل مع خدمة العملاء."
        ),
    },
    {
        "source_type": "faq",
        "content": (
            "سؤال شائع: كيف أجدد وصفتي الدوائية؟\n"
            "الإجابة: يمكنك إعادة الطلب مباشرة من سجل طلباتك في التطبيق. "
            "سيُرسَل لك تذكير تلقائي قبل موعد انتهاء دورتك الدوائية المعتادة."
        ),
    },
    {
        "source_type": "faq",
        "content": (
            "سؤال شائع: هل الأدوية المزمنة تحتاج وصفة طبية في كل مرة؟\n"
            "الإجابة: [نص سياسة تجريبي] يختلف ذلك حسب اللوائح المحلية ونوع الدواء. "
            "يُنصح دائماً بمراجعة الطبيب أو الصيدلي لتحديد ما إذا كانت الوصفة ضرورية."
        ),
    },
    {
        "source_type": "faq",
        "content": (
            "سؤال شائع: ازاي اعمل حساب جديد في صيدلية AI-COS؟ (إنشاء وتفعيل الحساب)\n"
            "الإجابة: لإنشاء حساب جديد، اضغط على زر 'تسجيل الدخول / إنشاء حساب' أعلى الصفحة، "
            "ثم أدخل بريدك الإلكتروني والاسم وكلمة المرور، أو سجل بضغطة واحدة عبر حساب Google OAuth. "
            "سيصلك بريد للتأكيد لتفعيل حسابك والبدء في طلب الأدوية واستقبال التذكيرات الذكية."
        ),
    },
    {
        "source_type": "faq",
        "content": (
            "سؤال شائع: ازاي اخد خصم أو كوبون تخفيض في الصيدلية؟ (العروض والخصومات)\n"
            "الإجابة: يمكنك الحصول على خصم 15% على أول طلب لك باستخدام كود الخصم الترحيبي (CARE15). "
            "كما يوفر النظام خصومات دورية وتلقائية لمرضى الأمراض المزمنة عند تجديد طلبياتهم عبر نظام التذكير الذكي (Refill Reminder)."
        ),
    },
    {
        "source_type": "faq",
        "content": (
            "سؤال شائع: ماذا أفعل لو نسيت جرعة دوائي؟\n"
            "الإجابة: يُرجى استشارة الصيدلي أو الطبيب مباشرة. لا تأخذ جرعة مضاعفة "
            "دون توجيه طبي. هذا رد عام ولا يُعدّ نصيحة طبية متخصصة."
        ),
    },
    {
        "source_type": "project_info",
        "content": (
            "معلومات المشروع وفريق العمل:\n"
            "مشروع منصة وصيدلية AI-COS هو مشروع تخرج رائد تابع لـ جامعة بورسعيد - كلية تكنولوجيا الإدارة ونظم المعلومات (MTIS / BIS).\n"
            "مطور ومهندس الذكاء الاصطناعي وباني النموذج هو المهندس: محمد ياسر سعد نقودي (AI Engineer & Lead).\n"
            "أعضاء فريق العمل المتميزين:\n"
            "1. محمد ياسر سعد نقودي (AI Engineer)\n"
            "2. يوسف نوفل\n"
            "3. زياد جودة\n"
            "4. محمود طنطاوي\n"
            "5. حسن حسين مخلص\n"
            "6. مصطفى هاشم."
        ),
    },
]


async def seed():
    async with AsyncSessionLocal() as db:
        # جلب جميع الأدوية
        rows = (await db.execute(select(Drug))).scalars().all()
        print(f"📦 عدد الأدوية في DB: {len(rows)}")

        # حذف الـ chunks الموجودة (idempotent re-seed)
        deleted = await db.execute(delete(KnowledgeChunk))
        print(f"🗑️  حُذف {deleted.rowcount} chunk قديم")

        chunks_to_insert = []

        # ── Chunks الأدوية ───────────────────────────────────────────────
        texts = [_build_drug_text(d) for d in rows]
        print(f"⏳ Embedding {len(texts)} نص دواء...")
        embeddings = encoder.encode(texts, normalize_embeddings=True, show_progress_bar=True)

        for drug, vec, text_content in zip(rows, embeddings, texts):
            chunks_to_insert.append(
                KnowledgeChunk(
                    chunk_id=uuid4(),
                    tenant_id=DEFAULT_TENANT_ID,
                    source_type="drug_info",
                    content=text_content,
                    embedding=vec.tolist(),
                )
            )

        # ── Chunks السياسات والـ FAQs ─────────────────────────────────────
        policy_texts = [p["content"] for p in STORE_POLICIES]
        print(f"⏳ Embedding {len(policy_texts)} سياسة/FAQ...")
        policy_embeddings = encoder.encode(policy_texts, normalize_embeddings=True)

        for policy, vec in zip(STORE_POLICIES, policy_embeddings):
            chunks_to_insert.append(
                KnowledgeChunk(
                    chunk_id=uuid4(),
                    tenant_id=DEFAULT_TENANT_ID,
                    source_type=policy["source_type"],
                    content=policy["content"],
                    embedding=vec.tolist(),
                )
            )

        # إدراج الكل
        db.add_all(chunks_to_insert)
        await db.commit()

        total = len(chunks_to_insert)
        drug_count = len(rows)
        policy_count = len(STORE_POLICIES)
        print(f"\n✅ تم إدراج {total} chunk:")
        print(f"   - {drug_count} chunk معلومات أدوية")
        print(f"   - {policy_count} chunk سياسات وFAQs")
        print(f"\nمثال على chunk دواء:\n{chunks_to_insert[0].content[:300]}...")


if __name__ == "__main__":
    asyncio.run(seed())
