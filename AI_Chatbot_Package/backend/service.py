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
async def _retrieve_context(db: AsyncSession, query_vec: list[float]) -> list[dict]:
    sql = text("""
        SELECT content, (embedding <=> CAST(:vec AS vector)) AS distance
        FROM knowledge_chunks
        ORDER BY distance ASC
        LIMIT :k
    """)
    rows = (await db.execute(sql, {"vec": str(query_vec), "k": TOP_K})).all()
    return [{"content": r.content, "distance": float(r.distance)} for r in rows]


def _is_in_scope(results: list[dict]) -> bool:
    if not results:
        return False
    similarity = 1.0 - results[0]["distance"] / 2.0
    return similarity >= SIMILARITY_THRESHOLD


def _build_prompt(question: str, context_chunks: list[dict]) -> str:
    if context_chunks:
        context_text = "\n---\n".join(c["content"] for c in context_chunks)
    else:
        context_text = "لا يوجد سياق دوائي إضافي مخصص. أجب بناءً على معلومات وهوية المشروع الموثقة."

    return (
        f"أنت مساعد خدمة عملاء ذكي لصيدلية AI-COS — منصة صيدلية إلكترونية ذكية متكاملة.\n\n"
        f"معلومات المشروع الرسمية:\n"
        f"- الجهة التابع لها: جامعة بورسعيد — كلية تكنولوجيا الإدارة ونظم المعلومات — قسم نظم المعلومات الإدارية (BIS / MTIS).\n"
        f"- مهندس الذكاء الاصطناعي ومطور النموذج: محمد ياسر سعد نقودي (Mohamed Yasser Saad Nokoudy).\n"
        f"- أعضاء فريق العمل: يوسف نوفل، زياد جودة، محمود طنطاوي، حسن حسين مخلص، مصطفى هاشم.\n"
        f"- وظائف النظام: نظام التذكير الذكي (Refill Reminder)، فحص تعارض وتداخل الأدوية، شات بوت RAG، لوحة تحليلات BIS، وأتمتة سير العمل n8n.\n\n"
        f"السياق الموثق من قاعدة البيانات:\n{context_text}\n\n"
        f"سؤال العميل: {question}\n\n"
        f"أجب باحترافية ووضوح بالعربية بإيجاز شديد على قدر السؤال فقط."
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
    return reply.strip()


def _build_prompt(question: str, context_chunks: list[dict]) -> str:
    if context_chunks:
        context_text = "\n---\n".join(c["content"] for c in context_chunks)
    else:
        context_text = "لا يوجد سياق دوائي إضافي مخصص. أجب بناءً على معلومات وهوية المشروع الموثقة."

    return (
        f"أنت مساعد خدمة عملاء ذكي لصيدلية AI-COS — منصة صيدلية إلكترونية ذكية متكاملة.\n\n"
        f"معلومات المشروع الرسمية:\n"
        f"- الجهة التابع لها: جامعة بورسعيد — كلية تكنولوجيا الإدارة ونظم المعلومات — قسم نظم المعلومات الإدارية (BIS / MTIS).\n"
        f"- مهندس الذكاء الاصطناعي ومطور النموذج: محمد ياسر سعد نقودي (Mohamed Yasser Saad Nokoudy).\n"
        f"- أعضاء فريق العمل: يوسف نوفل، زياد جودة، محمود طنطاوي، حسن حسين مخلص، مصطفى هاشم.\n"
        f"- وظائف النظام: نظام التذكير الذكي (Refill Reminder)، فحص تعارض وتداخل الأدوية، شات بوت RAG، لوحة تحليلات BIS، وأتمتة سير العمل n8n.\n\n"
        f"السياق الموثق من قاعدة البيانات:\n{context_text}\n\n"
        f"سؤال العميل: {question}\n\n"
        f"أجب باحترافية ووضوح بالعربية بإيجاز شديد على قدر السؤال فقط."
    )


def _build_system_prompt(context_chunks: list[dict]) -> str:
    if context_chunks:
        context_text = "\n---\n".join(c["content"] for c in context_chunks)
    else:
        context_text = "لا يوجد سياق دوائي إضافي مخصص لهذا السؤال."

    return (
        "أنت مساعد خدمة عملاء وذكاء اصطناعي ذكي لصيدلية AI-COS — منصة صيدلية إلكترونية متكاملة.\n\n"
        "هوية المشروع الرسمية:\n"
        "- الجهة: جامعة بورسعيد — كلية تكنولوجيا الإدارة ونظم المعلومات — قسم نظم المعلومات الإدارية (BIS / MTIS).\n"
        "- مهندس الذكاء الاصطناعي ومطور النموذج: محمد ياسر سعد نقودي (Mohamed Yasser Saad Nokoudy).\n"
        "- أعضاء فريق العمل المساعد: يوسف نوفل، زياد جودة، محمود طنطاوي، حسن حسين مخلص، مصطفى هاشم.\n"
        "- وظائف النظام: نظام التذكير الذكي (Refill Reminder)، فحص تعارض وتداخل الأدوية، شات بوت RAG، لوحة تحليلات BIS، وأتمتة سير العمل n8n.\n\n"
        f"السياق الموثق من قاعدة البيانات:\n{context_text}\n\n"
        "إرشادات الذاكرة والتفاعل الذكي:\n"
        "1. الذاكرة وسياق المحادثة: راجع سجل المحادثة (Chat History) بدقة شديدة؛ إذا أخبرك العميل باسمه في رسالة سابقة، تذكره فوراً وأجب به (مثال: إذا قال 'أنا اسمي محمد' ثم سأل 'ما هو اسمي' أجب مباشرة: 'اسمك هو محمد'). وإذا سأل عن دواء سابق بضمير (مثل 'كم سعره') تابع الحديث عن نفس الدواء.\n"
        "2. عند السؤال عن 'حساب' (مثل: 'ازاي اعمل حساب')، فالمقصود هو إنشاء وتفعيل حساب مستخدم جديد على المنصة (Sign Up/Register) وليس عملية حسابية، فاشرح خطوات التسجيل بالبريد أو Google OAuth.\n"
        "3. عند السؤال عن 'خصم' أو 'عروض' أو 'كوبونات'، اشرح كود الخصم الترحيبي (CARE15 بخصم 15%) وعروض التذكير الذكي لمرضى الأمراض المزمنة.\n"
        "4. الخصوصية والأمان: لا تكشف أبداً عن بيانات وسجلات العملاء الشخصية عبر الشات، وأوضح بأدب أن بيانات العملاء محمية ومتاحة فقط عبر لوحة الإدارة (Dashboard).\n"
        "5. الأمان الطبي: أنت نظام ذكاء اصطناعي طبي آمن تماماً وغير مدرب على الاختراق أو الهكر.\n"
        "6. الإيجاز واللغة: أجب دائماً باحترافية ولغة عربية فصحى سليمة 100% على قدر السؤال فقط، ولا تستخدم أي كلمات صينية أو أجنبية مطلقاً.\n"
        "7. النطاق السلبي الصريح (Negative Scope): إذا سأل المستخدم عن دواء غير متوفر في الكتالوج أو غير مناسب، ابدأ الإجابة بالنفي الصريح والمباشر أولاً (مثل: 'لا، دواء X غير متوفر حالياً في الصيدلية' أو 'لا، هذا الدواء غير مخصص لهذا الغرض') قبل تقديم أي نصيحة بديلة لمنع أي لبس دوائي."
    )


# ── Ollama Local Model (Chat API مع ذاكرة المحادثة) ────────────────────
# النموذج الفعال يمكن تبديله في وقت التشغيل عبر model_manager.switch_model()

async def _call_ollama(question: str, system_prompt: str, history: Optional[list[dict]] = None) -> Optional[str]:
    """يستدعي نموذج Ollama المحلي عبر Chat API لدعم الحوار الذكي وتذكر سياق الجلسة."""
    from app.domains.agents.model_manager import get_active_model
    try:
        timeout = getattr(settings, "OLLAMA_TIMEOUT", 30.0)
        chat_url = settings.OLLAMA_URL.replace("/api/generate", "/api/chat")

        messages = [{"role": "system", "content": system_prompt}]
        if history:
            for turn in history[-6:]:
                if turn.get("role") in ("user", "assistant") and turn.get("content"):
                    messages.append({"role": turn["role"], "content": turn["content"]})
        messages.append({"role": "user", "content": question})

        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                chat_url,
                json={
                    "model": get_active_model(), 
                    "messages": messages,
                    "stream": False,
                    "keep_alive": -1,
                    "options": {"temperature": 0.1, "top_p": 0.7}
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

    # 2.1 فحص التعارضات والتفاعلات الدوائية في المحادثة
    interaction = await InteractionGuard.check_in_chat_interactions(resolved_query, active_history, db)

    # 3. معالجة وتطبيع النصوص وتوسيع الاستعلام طبياً
    expanded_query, matched_terms = expand_colloquial_medical(resolved_query)

    # 4. البحث الهجين (Dense BERT + BM25 Lexical)
    query_vec = await _embed(expanded_query)
    raw_chunks = await _retrieve_context(db, query_vec)

    # إعادة الترتيب الهجين
    chunks = BM25LexicalRetriever.hybrid_rerank(resolved_query, raw_chunks)

    if not _is_in_scope(chunks):
        chunks = []  # Clear irrelevant context, but allow LLM to handle chit-chat/identity/general FAQs

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

    # ضمان التنويه الطبي
    if MEDICAL_DISCLAIMER.strip() not in reply:
        reply += MEDICAL_DISCLAIMER

    response_time_ms = int((time.time() - t_start) * 1000)
    return {
        "reply": reply,
        "llm_source": llm_source,
        "response_time_ms": response_time_ms,
        "escalation": escalation,
        "interaction": interaction,
        "resolved_query": resolved_query,
    }
