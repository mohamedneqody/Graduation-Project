"""
Deterministic Database Catalog Engine for AI-COS Pharmacy.
يوفر ربطاً حتمياً وحياً ومباشراً بجدول الأدوية (drugs) في قاعدة بيانات PostgreSQL.
يعالج استعلامات الكتالوج، الأقسام، العد الإجمالي، والأسعار بدقة 100%
مع الحفاظ على السياق الشخصي للعميل (مثل اسمه) دون أي هلاوس أو اعتذارات مصطنعة.
"""
import re
from typing import Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class DeterministicCatalogEngine:
    """محرك الاستعلام الحتمي عن كتالوج الصيدلية وأقسام الأدوية."""

    CATEGORY_MAPPINGS = {
        'حساسية': ['حساسيه', 'حساسية', 'هرش', 'عطس', 'ارتكاريا', 'اليرجي', 'allergy'],
        'نزلات برد': ['برد', 'نزلات برد', 'انفلونزا', 'رشح', 'زكام', 'سخونيه', 'سخونة', 'كحه', 'سعال', 'احتقان', 'cold', 'flu'],
        'مسكنات': ['مسكن', 'مسكنات', 'تسكين', 'صداع', 'وجع', 'painkiller'],
        'فيتامينات': ['فيتامين', 'فيتامينات', 'مكمل', 'مكملات', 'حديد', 'كالسيوم', 'زنك', 'اوميجا', 'vitamin'],
        'مضاد حيوي': ['مضاد حيوي', 'مضادات حيوية', 'مضاد', 'مضادات', 'antibiotic'],
        'جهاز هضمي': ['معده', 'معدة', 'حموضه', 'حموضة', 'هضمي', 'قولون', 'مغص', 'اسهال', 'امساك', 'انتفاخ', 'عسر هضم'],
        'مزمن - سكر': ['سكر', 'سكري', 'علاج السكر', 'انسولين', 'diabetes'],
        'مزمن - ضغط': ['ضغط', 'الضغط', 'علاج الضغط', 'hypertension'],
        'مزمن - كوليسترول': ['كوليسترول', 'دهون ثلاثية'],
        'مزمن - غدة درقية': ['غده', 'غدة', 'درقيه', 'درقية', 'thyroid'],
    }

    LISTING_INTENT_WORDS = [
        'كل', 'جميع', 'قائمه', 'قائمة', 'عددهم', 'عددهم كام', 'عددهم كم', 'كم عدد', 'كام عدد',
        'ايه هي', 'ايه ادوية', 'ايه أدوية', 'المتوفرة', 'المتوفره', 'موجوده', 'موجودة', 'الموجودة',
        'الموجوده', 'عندك', 'عندكم', 'في الصيدلية', 'في الصيدليه', 'قولي', 'اعرض', 'هات', 'انواع', 'أنواع',
        'ادويه', 'أدوية'
    ]

    @staticmethod
    def normalize_arabic(text_str: str) -> str:
        text_str = re.sub(r'[إأآا]', 'ا', text_str)
        text_str = text_str.replace('ة', 'ه').replace('ى', 'ي')
        return text_str.lower().strip()

    @classmethod
    def extract_customer_name(cls, history: Optional[list[dict]], message: str) -> str:
        pattern = r'(?:أنا\s+)?اسمي\s+([أ-يa-zA-Z]+)'
        if message:
            m = re.search(pattern, message)
            if m:
                return m.group(1)
        if history:
            for turn in reversed(history):
                if turn.get('role') == 'user':
                    m = re.search(pattern, turn.get('content', ''))
                    if m:
                        return m.group(1)
                elif turn.get('role') == 'assistant':
                    m2 = re.search(r'أهلاً بك[،\s]+(?:يا\s+)?([أ-يa-zA-Z]+)', turn.get('content', ''))
                    if m2:
                        return m2.group(1)
        return ""

    @classmethod
    async def match_and_serve_catalog(
        cls,
        query: str,
        history: Optional[list[dict]],
        db: AsyncSession,
    ) -> Optional[dict]:
        qn = cls.normalize_arabic(query)
        words = qn.split()

        matched_category = None
        for canonical_cat, keywords in cls.CATEGORY_MAPPINGS.items():
            for kw in keywords:
                kwn = cls.normalize_arabic(kw)
                if ' ' in kwn:
                    if kwn in qn:
                        matched_category = canonical_cat
                        break
                else:
                    for w in words:
                        clean_w = re.sub(r'^(?:ال|و|ف|ب|ل)', '', w)
                        if clean_w == kwn or w == kwn:
                            matched_category = canonical_cat
                            break
                    if matched_category:
                        break
            if matched_category:
                break

        if not matched_category:
            cats_res = await db.execute(text("SELECT DISTINCT category FROM drugs"))
            for (cat_name,) in cats_res.all():
                cat_norm = cls.normalize_arabic(cat_name)
                for part in cat_norm.split(' - '):
                    for w in part.split():
                        if len(w) >= 3 and (w in words or any(w in bw for bw in words)):
                            matched_category = cat_name
                            break
                    if matched_category:
                        break
                if matched_category:
                    break

        if not matched_category:
            return None

        sql = text("""
            SELECT name, base_price, active_ingredient, is_chronic
            FROM drugs
            WHERE category = :cat
            ORDER BY name ASC
        """)
        rows = (await db.execute(sql, {"cat": matched_category})).all()
        if not rows:
            return None

        total_count = len(rows)
        user_name = cls.extract_customer_name(history, query)
        greeting = f"أهلاً بك يا {user_name}! " if user_name else "أهلاً بك! "

        header = (
            f"{greeting}إجمالي أدوية قسم ({matched_category}) المتوفرة حالياً في صيدلية AI-COS هو "
            f"**{total_count} دواء ومستحضر** مسجل في قاعدة البيانات الحية:\n\n"
        )

        items = []
        for i, r in enumerate(rows, 1):
            act = f" (المادة الفعالة: {r.active_ingredient})" if r.active_ingredient else ""
            items.append(f"{i}. **{r.name}** - السعر: {r.base_price:.2f} ج.م{act}")

        body = "\n".join(items)
        disclaimer = (
            "\n\n⚠️ تنبيه: هذا الرد مسترجع مباشرة وحصرياً من قاعدة بيانات صيدلية AI-COS المحدثة. "
            "يُرجى دائماً استشارة الصيدلي أو الطبيب المختص قبل اتخاذ أي قرار دوائي."
        )

        full_reply = header + body + disclaimer
        return {
            "reply": full_reply,
            "llm_source": "database:deterministic_catalog",
            "category": matched_category,
            "total_count": total_count,
        }