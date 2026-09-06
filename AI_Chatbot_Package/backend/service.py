"""
AI RAG Service — بوت الصيدلية (3-Tier LLM Fallback)

ترتيب الأولوية (متفق عليه بعد قياس السرعة فعلياً):
────────────────────────────────────────────────────────────────────────
1. Gemini 2.5-flash (Cloud API — .env │ GEMINI_API_KEY)    ~0.9ث ✔ [الأسرع]
2. Gemma3:4b  (Ollama محلي)   │ OLLAMA_URL + OLLAMA_MODEL)   ~18-50ث ✔ [بدون نت]
3. Context-Only Fallback                                      فوري  ✔ [لا LLM]

قرار التصميم: Gemini Cloud أسرع 10x → الأولوية الأولى.
              Gemma فالباك فقط لو الإنترنت وقف أو انتهت API KEY.
────────────────────────────────────────────────────────────────────────
"""
import httpx

from app.core.decorators import handle_db_errors
from typing import Optional, Any, Dict, List
import logging
import time
import asyncio
import functools

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domains.ai.nlp_processor import normalize_arabic, expand_colloquial_medical
from app.domains.ai.coreference import CoreferenceResolver
from app.domains.ai.hybrid_search import BM25LexicalRetriever
from app.domains.ai.math_engine import DeterministicMathEngine
from app.domains.ai.escalation import EscalationEngine
from app.domains.ai.security_guard import SecurityGuard
from app.domains.ai.interaction_guard import InteractionGuard
from app.domains.ai.catalog_engine import DeterministicCatalogEngine
from app.domains.ai.intent_classifier import BERTIntentClassifier

# ── الثوابت ───────────────────────────────────────────────────────────────
EMBEDDING_MODEL      = "paraphrase-multilingual-MiniLM-L12-v2"
SIMILARITY_THRESHOLD = 0.65
TOP_K                = 3

MEDICAL_DISCLAIMER = (
    "\n\n⚠️ تنبيه: هذا رد آلي عام. يُرجى استشارة الصيدلي أو الطبيب المختص "
    "قبل أي قرار دوائي. هذه المعلومات لا تُعدّ نصيحة طبية متخصصة."
)

_encoder = None
logger = logging.getLogger(__name__)


def _get_encoder() -> Any:
    global _encoder
    if _encoder is None:
        from sentence_transformers import SentenceTransformer
        try:
            _encoder = SentenceTransformer(EMBEDDING_MODEL, local_files_only=True)
        except Exception:
            _encoder = SentenceTransformer(EMBEDDING_MODEL)
    return _encoder


async def _embed(query: str) -> list[float]:
    """Run CPU-bound embedding in a thread pool to avoid blocking the event loop."""
    loop = asyncio.get_event_loop()
    encode_fn = functools.partial(
        _get_encoder().encode, query, normalize_embeddings=True
    )
    result = await loop.run_in_executor(None, encode_fn)
    return result.tolist()


# ── pgvector Retrieval ────────────────────────────────────────────────────

@handle_db_errors
async def _retrieve_context(db: AsyncSession, query_vec: list[float], limit: int = 10) -> list[dict]:
    sql = text("""
        SELECT content, source_type, (embedding <=> CAST(:vec AS vector)) AS distance
        FROM knowledge_chunks
        ORDER BY distance ASC
        LIMIT :k
    """)
    rows = (await db.execute(sql, {"vec": str(query_vec), "k": limit})).all()
    results = []
    for r in rows:
        dist = float(r.distance)
        results.append({
            "content": r.content,
            "source_type": getattr(r, "source_type", ""),
            "distance": dist,
            "similarity": 1.0 - dist / 2.0,
        })
    return results


def _is_in_scope(results: list[dict]) -> bool:
    if not results:
        return False
    top = results[0]
    similarity = top.get("similarity", 1.0 - top.get("distance", 1.0) / 2.0)
    if top.get("hybrid_score", 0.0) >= 0.50 or top.get("lexical_score", 0.0) >= 0.35:
        return True
    return similarity >= SIMILARITY_THRESHOLD


async def _query_live_database_catalog(db: AsyncSession, query: str) -> Optional[dict]:
    """
    محرك ربط حي عام وشامل بجدول الأدوية (drugs) في قاعدة بيانات PostgreSQL:
    1. يستعلم عن التصنيفات الحقيقية ديناميكياً من قاعدة البيانات (SELECT DISTINCT category FROM drugs).
    2. يطابق الاستعلام مع التصنيفات والأعراض والمرادفات باللغة العربية المعيارية.
    3. يسترجع قائمة الأدوية، والعدد الإجمالي الحقيقي، والأسعار الحية دون الحاجة لأي جداول ثابتة.
    """
    import re
    # تطبيع الحروف العربية
    q_norm = re.sub(r'[إأآا]', 'ا', query.lower())
    q_norm = q_norm.replace('ة', 'ه').replace('ى', 'ي').strip()

    # خريطة مرادفات عامية للأقسام الطبية
    SYMPTOM_CATEGORY_MAP = {
        'برد': 'نزلات برد',
        'انفلونزا': 'نزلات برد',
        'رشح': 'نزلات برد',
        'زكام': 'نزلات برد',
        'سخونيه': 'نزلات برد',
        'كحه': 'نزلات برد',
        'سعال': 'نزلات برد',
        'حساسيه': 'حساسية',
        'هرش': 'حساسية',
        'عطس': 'حساسية',
        'ارتكاريا': 'حساسية',
        'مسكن': 'مسكنات',
        'وجع': 'مسكنات',
        'الم': 'مسكنات',
        'صداع': 'مسكنات',
        'فيتامين': 'فيتامينات',
        'مكمل': 'فيتامينات',
        'حديد': 'فيتامينات',
        'كالسيوم': 'فيتامينات',
        'مضاد': 'مضاد حيوي',
        'معده': 'جهاز هضمي',
        'حموضه': 'جهاز هضمي',
        'هضمي': 'جهاز هضمي',
        'قولون': 'جهاز هضمي',
        'مغص': 'جهاز هضمي',
        'اسهال': 'جهاز هضمي',
        'امساك': 'جهاز هضمي',
        'سكر': 'مزمن - سكر',
        'سكري': 'مزمن - سكر',
        'ضغط': 'مزمن - ضغط',
        'كوليسترول': 'مزمن - كوليسترول',
        'غده': 'مزمن - غدة درقية',
    }

    matched_cat = None
    # 1. فحص الكلمات الطبية والأعراض
    for term, cat in SYMPTOM_CATEGORY_MAP.items():
        if term in q_norm:
            matched_cat = cat
            break

    # 2. فحص التصنيفات الحقيقية ديناميكياً من جدول الأدوية
    if not matched_cat:
        cats_res = await db.execute(text("SELECT DISTINCT category FROM drugs"))
        for (cat_name,) in cats_res.all():
            cat_norm = re.sub(r'[إأآا]', 'ا', cat_name.lower()).replace('ة', 'ه').replace('ى', 'ي')
            for part in cat_norm.split(' - '):
                for w in part.split():
                    if len(w) >= 3 and w in q_norm:
                        matched_cat = cat_name
                        break
                if matched_cat:
                    break
            if matched_cat:
                break

    if not matched_cat:
        return None

    sql = text("""
        SELECT name, base_price, is_chronic, active_ingredient
        FROM drugs 
        WHERE category = :cat 
        ORDER BY name ASC
    """)
    rows = (await db.execute(sql, {"cat": matched_cat})).all()
    if not rows:
        return None

    items = [f"{i}. {r.name} (السعر: {r.base_price} ج.م)" for i, r in enumerate(rows, 1)]
    content = (
        f"[بيانات رسمية مباشرة من جدول الأدوية (drugs) في قاعدة بيانات PostgreSQL صيدلية AI-COS]:\n"
        f"- القسم الطبي المطلوب: ({matched_cat})\n"
        f"- إجمالي الأدوية المسجلة المتوفرة في هذا القسم: {len(rows)} دواء ومستحضر.\n"
        f"- قائمة الأدوية المتوفرة وأسعارها بالجنيه المصري:\n"
        + "\n".join(items)
        + f"\n(أجب بذكر العدد الإجمالي {len(rows)} دواء واسرد الأدوية بوضوح وأسعارها دون أي اعتذار)."
    )
    return {"content": content, "source_type": "database_catalog"}


def _build_prompt(question: str, context_chunks: list[dict]) -> str:
    if context_chunks:
        context_text = "\n---\n".join(c["content"] for c in context_chunks)
    else:
        context_text = "لا يوجد سياق دوائي إضافي مخصص. أجب بناءً على معلومات وهوية المشروع الموثقة."

    return (
        f"أنت المساعد الصيدلي الذكي الافتراضي لمنصة AI-COS Pharmacy (روبوت ومساعد آلي).\n"
        f"قاعدة اللغة الصارمة: يجب أن تطابق لغة إجابتك لغة سؤال المستخدم دائماً 100% (إذا كان السؤال بالعربية أجب بالعربية الفصحى فقط، وإذا كان بالإنجليزية أجب بالإنجليزية).\n"
        f"قاعدة الهوية الصارمة: إياك نهائياً أن تدعي أنك عضو بشري في الفريق أو تقول 'including myself' أو 'أنا محمد ياسر' لأنك روبوت ولست بشراً! بل قل دائماً بدقة: "
        f"'أنا المساعد الصيدلي الذكي لمنصة AI-COS، طورني وبرمجني مهندس الذكاء الاصطناعي: محمد ياسر سعد نقودي، بمشاركة فريق العمل المساعد (يوسف نوفل، زياد جودة، محمود طنطاوي، حسن حسين، مصطفى هاشم) بكلية تكنولوجيا الإدارة ونظم المعلومات (BIS / MTIS) بجامعة بورسعيد. دوري هو مساعدتك في الاستفسار عن الأدوية، فحص الروشتات، والتذكير بمواعيد العلاج.'\n\n"
        f"السياق الموثق من قاعدة البيانات:\n{context_text}\n\n"
        f"سؤال العميل: {question}\n\n"
        f"أجب باحترافية ووضوح بنفس لغة السؤال بإيجاز على قدر السؤال فقط."
    )


_session_history: dict[str, list[dict]] = {}


def _clean_reply(reply: str) -> str:
    import re
    if not reply:
        return ""
    # إزالة وسوم التفكير
    reply = re.sub(r'<think>.*?</think>', '', reply, flags=re.DOTALL)
    # استبدال المصطلحات الصينية
    reply = reply.replace("药师", "الصيدلي")
    # إزالة أي حروف صينية متسربة
    reply = re.sub(r'[\u4e00-\u9fff]+', '', reply)
    # منع المودل من ادعاء اسم العميل
    reply = re.sub(r'أنا (?:أسمى|اسمي) محمد[،\.\s]*', '', reply)
    # منع المودل من ادعاء أنه عضو بشري في الفريق
    reply = re.sub(r'\b(?:including\s+myself|and\s+myself|myself\s+and)\b', '', reply, flags=re.IGNORECASE)
    reply = re.sub(r'\b(?:بما\s+في\s+ذلك\s+أنا|وأنا\s+معهم)\b', '', reply)
    return reply.strip()


def _build_system_prompt(context_chunks: list[dict]) -> str:
    if context_chunks:
        context_text = "\n---\n".join(c["content"] for c in context_chunks)
    else:
        context_text = "لا يوجد سياق دوائي إضافي مخصص لهذا السؤال."

    return (
        "أنت المساعد الصيدلي الذكي الافتراضي لمنصة AI-COS Pharmacy (روبوت ومساعد آلي).\n\n"
        "قاعدة اللغة الصارمة (Strict Bilingual Language Match):\n"
        "- طابق لغة إجابتك للغة سؤال المستخدم دائماً 100%:\n"
        "  * إذا كتب المستخدم بالعربية: أجب باللغة العربية الفصحى السليمة فقط، وممنوع منعاً باتاً كتابة الرد بالإنجليزية حتى لو كان السياق المرجعي بالإنجليزية (قم بصياغته بالعربية دائماً).\n"
        "  * إذا كتب المستخدم بالإنجليزية: أجب باللغة الإنجليزية بطلاقة واحترافية.\n\n"
        "قاعدة الهوية الصارمة (Identity Rule):\n"
        "- أنت روبوت ومساعد آلي افتراضي ولست إنساناً، وإياك نهائياً أن تدعي أنك 'محمد ياسر' أو 'أستاذ بالجامعة' أو تدعي أنك عضو بشري في الفريق (ممنوع قول 'including myself' أو 'أنا معهم')!\n"
        "- عندما يسألك العميل 'من أنت' أو 'ما هو دورك' أو 'من قام ببرمجتك' أو 'من طورك' أو 'مين فريق العمل': أجب دائماً باحترافية:\n"
        "'أنا المساعد الصيدلي الذكي لمنصة صيدلية AI-COS، قام بتطويري وبرمجتي مهندس الذكاء الاصطناعي: محمد ياسر سعد نقودي، بمشاركة فريق العمل المساعد (يوسف نوفل، زياد جودة، محمود طنطاوي، حسن حسين، مصطفى هاشم) بكلية تكنولوجيا الإدارة ونظم المعلومات (BIS / MTIS) بجامعة بورسعيد. دوري كمساعد ذكي هو الإجابة على استفساراتك المتعلقة بالأدوية، فحص الروشتات، وتقديم الدعم الصيدلي الموثوق.'\n\n"
        f"السياق الموثق من قاعدة البيانات:\n{context_text}\n\n"
        "إرشادات الذاكرة والتفاعل الذكي:\n"
        "1. الذاكرة والتعريف بالاسم: إذا أخبرك العميل باسمه (مثل: 'أنا اسمي محمد وانت' أو 'أنا اسمي أحمد')، فإن هذا الاسم هو اسم العميل البشري وليس اسمك أنت! رحّب به بأدب (مثل: 'أهلاً بك يا محمد! أنا المساعد الصيدلي الذكي لمنصة AI-COS...'). وإياك نهائياً أن تدعي أنك تسمى بهذا الاسم أو تقول 'أنا أسمى محمد'! اسمك أنت هو 'المساعد الصيدلي الذكي'. وإذا سألك لاحقاً 'ما هو اسمي' أجب مباشرة: 'اسمك هو محمد'. وإذا سأل عن دواء سابق بضمير (مثل 'كم سعره') تابع الحديث عن نفس الدواء.\n"
        "2. عند السؤال عن 'حساب' (مثل: 'ازاي اعمل حساب')، فالمقصود هو إنشاء وتفعيل حساب مستخدم جديد على المنصة (Sign Up/Register) وليس عملية حسابية، فاشرح خطوات التسجيل بالبريد أو Google OAuth.\n"
        "3. الخصوصية والأمان: لا تكشف أبداً عن بيانات وسجلات العملاء الشخصية عبر الشات، وأوضح بأدب أن بيانات العملاء محمية ومتاحة فقط عبر لوحة الإدارة (Dashboard).\n"
        "4. الأمان الطبي: أنت نظام ذكاء اصطناعي طبي آمن تماماً وغير مدرب على الاختراق أو الهكر.\n"
        "5. الإيجاز واللغة: أجب دائماً باحترافية على قدر السؤال فقط دون إسهاب، وبأسلوب صيدلي راقٍ وموثوق.\n"
        "6. أسئلة الكلية والجامعة: أجب بدقة بناءً على سياق الكلية الوارد أعلاه (جامعة بورسعيد - كلية تكنولوجيا الإدارة ونظم المعلومات MTIS/BIS).\n"
        "7. قاعدة الربط الحي بكتالوج قاعدة البيانات (Enterprise Database Rule):\n"
        "- أنت متصل مباشرة وبشكل حي بجدول الأدوية (drugs) في قاعدة بيانات PostgreSQL لصيدلية AI-COS.\n"
        "- كل البيانات الواردة في السياق أعلاه هي بيانات حقيقية رسمية مسترجعة في اللحظة الحالية من قاعدة البيانات.\n"
        "- عندما يسأل العميل عن أي قسم علاجي (نزلات برد، حساسية، مسكنات، فيتامينات، سكر، ضغط، مضادات حيوية، جهاز هضمي، كوليسترول، غدة) أو يسأل عن الأدوية المتوفرة أو عددها أو أسعارها: اذكر له فوراً وبثقة تامة العدد الإجمالي كما هو وارد في السياق واسرد الأدوية وأسعارها بالجنيه المصري.\n"
        "- ممنوع منعاً باتاً وحاسماً أن تعتذر أو تقول 'لا أملك قائمة محددة' أو 'غير متاح حالياً' أو 'يرجى التواصل مع الصيدلية للحصول على قائمة'، لأنك تملك الكتالوج الرسمي المعتمد كاملاً أمامك مباشرة في قاعدة البيانات!"
    )


# ── Ollama Local Model (Chat API مع ذاكرة المحادثة) ────────────────────
# النموذج الفعال يمكن تبديله في وقت التشغيل عبر model_manager.switch_model()

async def _call_ollama(question: str, system_prompt: str, history: Optional[list[dict]] = None) -> Optional[str]:
    """يستدعي نموذج Ollama المحلي عبر Chat API لدعم الحوار الذكي وتذكر سياق الجلسة."""
    from app.domains.agents.model_manager import get_active_model
    try:
        timeout = getattr(settings, "OLLAMA_TIMEOUT", 45.0)
        chat_url = settings.OLLAMA_URL.replace("/api/generate", "/api/chat")

        messages = [{"role": "system", "content": system_prompt}]
        if history:
            for turn in history[-6:]:
                if turn.get("role") in ("user", "assistant") and turn.get("content"):
                    cont = turn["content"]
                    # تنقية التاريخ من أي اعتذارات سابقة حتى لا يكررها الموديل بالخطأ
                    if turn.get("role") == "assistant" and ("لا أملك قائمة" in cont or "لا يمكنني تقديم قائمة" in cont):
                        continue
                    messages.append({"role": turn["role"], "content": cont})
        messages.append({"role": "user", "content": question})

        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                chat_url,
                json={
                    "model": get_active_model(), 
                    "messages": messages,
                    "stream": False,
                    "keep_alive": -1,
                    "options": {"temperature": 0.1, "top_p": 0.7, "num_predict": 450}
                },
            )
            if resp.status_code == 200:
                reply = resp.json().get("message", {}).get("content", "")
                reply = _clean_reply(reply)
                if reply:
                    return reply
    except (httpx.ConnectError, httpx.TimeoutException, httpx.RequestError):
        pass
    return None


# ── Priority 1: Gemini API (Cloud — الأسرع) ──────────────────────────

async def _call_gemini(prompt: str) -> Optional[str]:
    """
    يستدعي Gemini عبر Google AI REST API.
    النموذج: gemini-2.5-flash (من GEMINI_MODEL في .env)
    مطلوب: GEMINI_API_KEY في .env
    """
    if not settings.GEMINI_API_KEY:
        return None

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.GEMINI_MODEL}:generateContent"
        f"?key={settings.GEMINI_API_KEY}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 512,
        },
        "safetySettings": [
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HARASSMENT",        "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH",       "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        ],
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                reply = (
                    data.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text", "")
                    .strip()
                )
                if reply:
                    return _clean_reply(reply)
                logger.warning(f"🟡 Gemini رد فارغ — candidates: {data.get('candidates','?')[:200]}")
            else:
                logger.warning(f"🟡 Gemini HTTP {resp.status_code}: {resp.text[:200]}")
    except (httpx.ConnectError, httpx.TimeoutException, httpx.RequestError) as e:
        logger.warning(f"🟡 Gemini connection error: {e}")
    return None


# ── Priority 3: Context-Only Fallback ────────────────────────────────────

def _context_only_reply(chunks: list[dict]) -> str:
    context_text = "\n\n".join(f"• {c['content']}" for c in chunks)
    return (
        f"بناءً على المعلومات المتاحة:\n\n{context_text}"
        f"{MEDICAL_DISCLAIMER}"
    )


# ── Public API ────────────────────────────────────────────────────────────

async def generate_ai_response(
    message: str,
    db: Optional[AsyncSession] = None,
    session_id: Optional[str] = None,
    history: Optional[list[dict]] = None,
) -> dict:
    """
    RAG Pipeline المتقدم الشامل:
    1. فحص وتحليل الطوارئ الطبية ومشاعر الغضب والتصعيد الفوري (Escalation Engine).
    2. حل الضمائر التتابعية وإدارة الذاكرة السياقية (Stateful Coreference Resolution).
    3. معالجة وتطبيع النصوص وتوسيع الاستعلام بالمرادفات الطبية العامية (Arabic NLP Expansion).
    4. البحث الهجين ثنائي المرحلة: دلالي بالـ BERT + معجمي بالـ BM25 مع دمج الدرجات (Hybrid Reranking).
    5. المساعد الحسابي الحتمي لحساب الأسعار والخصومات والجرعات بدقة 100% (Deterministic Math).
    6. التوليد الذكي عبر Ollama Chat API مع fallback سحابي لـ Gemini وتنظيف المخرجات.
    """
    if db is None:
        return {
            "reply": "⚠️ البوت غير مُكوّن بشكل صحيح." + MEDICAL_DISCLAIMER,
            "llm_source": "error",
            "response_time_ms": 0,
        }

    t_start = time.time()

    # 0. طبقة الحماية وتحديد طول المدخلات وصد الـ Prompt Injection
    security = SecurityGuard.check_security(message)
    if security["is_flagged"]:
        # توثيق هجوم الأمان فوراً في audit_logs و ai_chat_logs
        try:
            r_time = int((time.time() - t_start) * 1000)
            # جلب معرف الصيدلية النشطة ديناميكياً من قاعدة البيانات (بدون أي هاردكود)
            tid_res = await db.execute(text("SELECT tenant_id FROM tenants WHERE is_active = true ORDER BY created_at ASC LIMIT 1"))
            tenant_id = tid_res.scalar()
            if tenant_id:
                await db.execute(text("""
                    INSERT INTO audit_logs (log_id, tenant_id, actor_id, action_type, target_entity)
                    VALUES (gen_random_uuid(), :tid, :actor, :action, 'ai_security_guard')
                """), {
                    "tid": tenant_id,
                    "actor": session_id or "anonymous_attacker",
                    "action": f"sec_block_{security.get('blocked_reason', 'attack')[:30]}"
                })
            await db.execute(text("""
                INSERT INTO ai_chat_logs (session_id, user_prompt, ai_response, engines_used,
                    ddi_detected, security_flagged, escalation_status, response_time_ms)
                VALUES (:sid, :prompt, :resp, ARRAY['security_guard'], FALSE, TRUE, 'blocked', :rtime)
            """), {
                "sid": session_id or "security_blocked",
                "prompt": message[:500],
                "resp": security["security_reply"][:500],
                "rtime": r_time
            })
            await db.commit()
        except Exception as e:
            logger.warning(f"[Security Audit] Could not log security event: {e}")
            await db.rollback()

        return {
            "reply": security["security_reply"] + MEDICAL_DISCLAIMER,
            "llm_source": "security_guard",
            "response_time_ms": int((time.time() - t_start) * 1000),
            "security": security,
        }

    sanitized_message = security["sanitized_text"]

    # 1. تحليل المشاعر والطوارئ الطبية
    escalation = EscalationEngine.analyze(sanitized_message)

    # 2. إدارة الذاكرة وحل الضمائر التتابعية
    active_history = history
    if active_history is None and session_id:
        active_history = _session_history.setdefault(session_id, [])
    elif active_history is None:
        active_history = _session_history.setdefault("default_session", [])

    resolved_query = CoreferenceResolver.resolve_query(sanitized_message, active_history)

    # 1.1 تصنيف نية المستخدم آلياً بنموذج BERT الدلالي
    try:
        intent_data = BERTIntentClassifier.classify(resolved_query, encoder=_get_encoder())
    except Exception as e:
        logger.warning(f"[BERT Intent] Fallback: {e}")
        intent_data = {
            "predicted_intent": "general_qa",
            "confidence": 0.5,
            "margin": 0.0,
            "all_scores": {},
            "model_name": "paraphrase-multilingual-MiniLM-L12-v2 (BERT)",
            "latency_ms": 0
        }
    predicted_intent = intent_data["predicted_intent"]

    # 2.0 محرك الكتالوج الحتمي المباشر من قاعدة بيانات PostgreSQL للأقسام والكميات
    catalog_reply = await DeterministicCatalogEngine.match_and_serve_catalog(
        resolved_query, active_history, db
    )
    if catalog_reply:
        r_ms = int((time.time() - t_start) * 1000)
        conf_badge = {
            "level": "high",
            "score": 0.98,
            "badge": "🟢 ثقة مؤكدة (قاعدة البيانات)",
            "source": "live_catalog_db",
            "hallucination_risk": "none"
        }
        q_metrics = {
            "source": "database",
            "confidence": 0.98,
            "intent": predicted_intent,
            "intent_confidence": intent_data.get("confidence", 0.98),
            "intent_model": intent_data.get("model_name", "BERT"),
            "engines_activated": ["catalog_engine"],
            "response_time_ms": r_ms,
            "hallucination_risk": "none"
        }
        try:
            await db.execute(text("""
                INSERT INTO ai_chat_logs (
                    session_id, user_prompt, ai_response, engines_used,
                    ddi_detected, security_flagged, escalation_status, response_time_ms, intent
                ) VALUES (
                    :sid, :prompt, :resp, ARRAY['catalog_engine'],
                    FALSE, FALSE, 'normal', :rtime, :intent
                )
            """), {
                "sid": session_id or "default_session",
                "prompt": message[:500],
                "resp": catalog_reply["reply"][:1000],
                "rtime": r_ms,
                "intent": predicted_intent
            })
            await db.commit()
        except Exception as e:
            logger.warning(f"[Chat Audit Log - Catalog] {e}")

        if session_id and active_history is not None:
            active_history.append({"role": "user", "content": sanitized_message})
            active_history.append({"role": "assistant", "content": catalog_reply["reply"]})

        return {
            "reply": catalog_reply["reply"],
            "llm_source": catalog_reply["llm_source"],
            "response_time_ms": r_ms,
            "category": catalog_reply.get("category"),
            "total_count": catalog_reply.get("total_count"),
            "confidence_badge": conf_badge,
            "quality_metrics": q_metrics,
            "intent_classification": intent_data,
        }

    # 2.1 فحص التعارضات والتفاعلات الدوائية في المحادثة
    interaction = await InteractionGuard.check_in_chat_interactions(resolved_query, active_history, db)

    # 3. معالجة وتطبيع النصوص وتوسيع الاستعلام طبياً
    expanded_query, matched_terms = expand_colloquial_medical(resolved_query)

    # 4. البحث الهجين (Dense BERT + BM25 Lexical)
    query_vec = await _embed(expanded_query)
    raw_chunks = await _retrieve_context(db, query_vec, limit=10)

    # إعادة الترتيب الهجين واختيار أفضل المقاطع الموثقة
    reranked = BM25LexicalRetriever.hybrid_rerank(resolved_query, raw_chunks)
    chunks = reranked[:TOP_K]

    if not _is_in_scope(chunks):
        chunks = []  # Clear irrelevant context, but allow LLM to handle chit-chat/identity/general FAQs

    # 4.1 استرجاع كتالوج الأدوية المباشر من قاعدة بيانات PostgreSQL عند السؤال عن فئة معينة
    cat_catalog = await _query_live_database_catalog(db, resolved_query)
    if cat_catalog:
        chunks.insert(0, cat_catalog)

    # 5. المساعد الحسابي الحتمي
    math_proof = DeterministicMathEngine.extract_and_solve_math(resolved_query, chunks)
    if math_proof:
        chunks.insert(0, {"content": math_proof, "source_type": "math_proof"})

    system_prompt = _build_system_prompt(chunks)
    prompt = _build_prompt(resolved_query, chunks)
    llm_source = "context_only"

    # ── Priority 1: AI-COS-Qwen-2.5 (Ollama محلي — نموذج المشروع الخاص) ───────────────
    reply = await _call_ollama(resolved_query, system_prompt, active_history)
    if reply:
        llm_source = f"ollama:{settings.OLLAMA_MODEL}"
        logger.info("🟢 RAG تم عبر Ollama (AI-COS-Qwen-2.5)")

    # ── Priority 2: Gemini (Cloud — احتياطي سحابي سريع) ─────────────────────────
    if not reply:
        logger.warning("🟡 Ollama لم يستجب — جاري تجربة Gemini")
        reply = await _call_gemini(prompt)
        if reply:
            llm_source = f"gemini:{settings.GEMINI_MODEL}"
            logger.info("🟢 RAG تم عبر Gemini")

    # ── Priority 3: Context-Only ─────────────────────────────────
    if not reply:
        logger.warning("🔴 كل LLM فشل — Context-Only")
        reply = _context_only_reply(chunks)
        llm_source = "context_only"

    # إرفاق تحذير التعارض الدوائي إن وجد
    if interaction.get("has_interaction") and interaction.get("warning_banner"):
        reply = f"{interaction['warning_banner']}\n\n{reply}"

    # إرفاق تنبيه الطوارئ أو الشكاوى إن وجد
    if escalation.get("alert_message"):
        reply = f"{escalation['alert_message']}\n\n{reply}"

    # تحديث سجل الجلسة
    if reply and active_history is not None:
        active_history.append({"role": "user", "content": message})
        active_history.append({"role": "assistant", "content": reply})
        if len(active_history) > 10:
            active_history[:] = active_history[-10:]

    # ضمان التنويه الطبي للأسئلة الدوائية فقط وعدم إرفاقه في الأسئلة الأكاديمية والتقنية الخاصة بالمشروع والكلية
    is_faculty_query = any(c.get("source_type") in ("faculty_info", "project_architecture", "project_info") for c in chunks)
    college_keywords = [
        "كلية", "جامعة", "عميد", "وكيل", "شؤون طلاب", "تنسيق", "ساعات معتمدة", "bis", "mtis",
        "مشروع تخرج", "دكتور", "دبلوم", "معمارية", "rag", "n8n", "وكلاء", "trocr", "rfm", "dss", "saas", "rls"
    ]
    if any(kw in resolved_query.lower() for kw in college_keywords):
        is_faculty_query = True

    if not is_faculty_query and MEDICAL_DISCLAIMER.strip() not in reply:
        reply += MEDICAL_DISCLAIMER

    # تسجيل حالات الطوارئ الطبية والتصعيد في audit_logs
    if escalation.get("is_emergency") or escalation.get("is_angry"):
        try:
            await EscalationEngine.log_escalation(
                db, message, escalation.get("priority", "normal"), escalation.get("status", "automated")
            )
        except Exception as e:
            logger.warning(f"[Escalation Audit] Failed to log escalation: {e}")

    response_time_ms = int((time.time() - t_start) * 1000)

    # ── AI Chat Audit Log: توثيق المحادثة كاملة في قاعدة البيانات ──────────────
    try:
        engines_used = []
        if cat_catalog:
            engines_used.append("catalog_engine")
        if interaction.get("has_interaction"):
            engines_used.append("interaction_guard")
        if escalation.get("is_emergency") or escalation.get("is_angry"):
            engines_used.append("escalation_engine")
        if math_proof:
            engines_used.append("math_engine")
        if chunks:
            engines_used.append("hybrid_search_rag")
        if llm_source.startswith("ollama"):
            engines_used.append("ollama_llm")
        elif llm_source.startswith("gemini"):
            engines_used.append("gemini_llm")

        # حساب شارة الثقة وجودة الرد
        if math_proof:
            conf_badge = {
                "level": "high", "score": 0.99,
                "badge": "🟢 ثقة حسابية مؤكدة 100%",
                "source": "deterministic_math", "hallucination_risk": "none"
            }
        elif interaction.get("has_interaction"):
            conf_badge = {
                "level": "high", "score": 0.96,
                "badge": "🟢 تنبيه طبي حاسم وموثق",
                "source": "clinical_interaction_guard", "hallucination_risk": "none"
            }
        elif chunks and any(c.get("hybrid_score", 0.0) >= 0.70 for c in chunks):
            conf_badge = {
                "level": "high", "score": 0.88,
                "badge": "🟢 ثقة عالية (مصادر موثقة)",
                "source": "hybrid_rag_verified", "hallucination_risk": "low"
            }
        elif chunks:
            conf_badge = {
                "level": "medium", "score": 0.72,
                "badge": "🟡 ثقة متوسطة (استرجاع ذكي)",
                "source": "hybrid_rag", "hallucination_risk": "low"
            }
        else:
            conf_badge = {
                "level": "low", "score": 0.60,
                "badge": "🔴 رد استرشادي عام",
                "source": "llm_generative", "hallucination_risk": "medium"
            }

        quality_metrics = {
            "source": conf_badge["source"],
            "confidence": conf_badge["score"],
            "intent": predicted_intent,
            "intent_confidence": intent_data.get("confidence", 0.75),
            "intent_model": intent_data.get("model_name", "BERT"),
            "engines_activated": engines_used,
            "response_time_ms": response_time_ms,
            "hallucination_risk": conf_badge["hallucination_risk"]
        }

        await db.execute(text("""
            INSERT INTO ai_chat_logs (
                session_id, user_prompt, ai_response, engines_used,
                ddi_detected, security_flagged, escalation_status, response_time_ms, intent
            ) VALUES (
                :sid, :prompt, :resp, :engines,
                :ddi, FALSE, :esc, :rtime, :intent
            )
        """), {
            "sid": session_id or "default_session",
            "prompt": message[:500],
            "resp": reply[:1000] if reply else None,
            "engines": engines_used,
            "ddi": bool(interaction.get("has_interaction")),
            "esc": escalation.get("priority", "normal"),
            "rtime": response_time_ms,
            "intent": predicted_intent,
        })
        await db.commit()
    except Exception as e:
        logger.warning(f"[Chat Audit Log] Failed to save log: {e}")

    # fallback values for conf_badge and quality_metrics if logging block had exception
    if 'conf_badge' not in locals():
        conf_badge = {"level": "medium", "score": 0.75, "badge": "🟡 استجابة موثقة", "source": llm_source, "hallucination_risk": "low"}
    if 'quality_metrics' not in locals():
        quality_metrics = {"source": llm_source, "confidence": 0.75, "intent": predicted_intent, "intent_confidence": intent_data.get("confidence", 0.75), "intent_model": intent_data.get("model_name", "BERT"), "engines_activated": engines_used, "response_time_ms": response_time_ms, "hallucination_risk": "low"}

    return {
        "reply": reply,
        "llm_source": llm_source,
        "response_time_ms": response_time_ms,
        "escalation": escalation,
        "interaction": interaction,
        "resolved_query": resolved_query,
        "confidence_badge": conf_badge,
        "quality_metrics": quality_metrics,
        "intent_classification": intent_data,
    }
