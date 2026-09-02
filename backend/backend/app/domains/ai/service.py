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
from typing import Optional
import logging
import time

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

# ── الثوابت ───────────────────────────────────────────────────────────────
EMBEDDING_MODEL      = "paraphrase-multilingual-MiniLM-L12-v2"
SIMILARITY_THRESHOLD = 0.30
TOP_K                = 3

MEDICAL_DISCLAIMER = (
    "\n\n⚠️ تنبيه: هذا رد آلي عام. يُرجى استشارة الصيدلي أو الطبيب المختص "
    "قبل أي قرار دوائي. هذه المعلومات لا تُعدّ نصيحة طبية متخصصة."
)

_encoder = None
logger = logging.getLogger(__name__)


def _get_encoder():
    global _encoder
    if _encoder is None:
        from sentence_transformers import SentenceTransformer
        _encoder = SentenceTransformer(EMBEDDING_MODEL)
    return _encoder


def _embed(query: str) -> list[float]:
    return _get_encoder().encode(query, normalize_embeddings=True).tolist()


# ── pgvector Retrieval ────────────────────────────────────────────────────

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
    context_text = "\n---\n".join(c["content"] for c in context_chunks)
    return (
        f"أنت مساعد خدمة عملاء ذكي لصيدلية AI-COS — منصة صيدلية إلكترونية ذكية متكاملة.\n"
        f"معلومات المشروع الرسمية:\n"
        f"- الجهة التابع لها: جامعة بورسعيد - كلية تكنولوجيا الإدارة ونظم المعلومات (MTIS / BIS).\n"
        f"- مهندس الذكاء الاصطناعي ومطور النموذج: محمد ياسر سعد نقودي (Mohamed Yasser Saad Nokoudy).\n"
        f"- أعضاء فريق العمل: يوسف نوفل، زياد جودة، محمود طنطاوي، حسن حسين مخلص، مصطفى هاشم.\n"
        f"- وظائف النظام: نظام التذكير الذكي (Refill Reminder)، فحص تعارض وتداخل الأدوية، شات بوت RAG، لوحة تحليلات BIS، وأتمتة سير العمل n8n.\n\n"
        f"السياق الموثق من قاعدة البيانات:\n{context_text}\n\n"
        f"سؤال العميل: {question}\n\n"
        f"أجب باحترافية ووضوح بالعربية بناءً على هوية المشروع والسياق المتاح أعلاه."
        f"{MEDICAL_DISCLAIMER}"
    )


# ── Ollama Local Model (AI-COS-Qwen-2.5) ─────────────────────────────

async def _call_ollama(prompt: str) -> Optional[str]:
    """يستدعي نموذج المشروع المحلي AI-COS-Qwen-2.5 عبر Ollama."""
    try:
        timeout = getattr(settings, "OLLAMA_TIMEOUT", 30.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                settings.OLLAMA_URL,
                json={"model": settings.OLLAMA_MODEL, "prompt": prompt, "stream": False},
            )
            if resp.status_code == 200:
                reply = resp.json().get("response", "").strip()
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
            "temperature": 0.3,
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
                    return reply
                # Candidate returned but empty (e.g. blocked by safety)
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

async def generate_ai_response(message: str, db: Optional[AsyncSession] = None) -> dict:
    """
    RAG Pipeline الكامل:
    1. Embed → pgvector search → out-of-scope check
    2. جرّب Gemini (Cloud) → Gemma (Ollama) → Context-Only
    3. ضمان التنويه الطبي في كل رد
    يُرجع dict يحتوي على reply + llm_source + response_time_ms
    """
    if db is None:
        return {
            "reply": "⚠️ البوت غير مُكوّن بشكل صحيح." + MEDICAL_DISCLAIMER,
            "llm_source": "error",
            "response_time_ms": 0,
        }

    t_start = time.time()
    query_vec = _embed(message)
    chunks    = await _retrieve_context(db, query_vec)

    if not _is_in_scope(chunks):
        return {
            "reply": (
                "عذراً، لا أملك معلومات موثقة كافية للإجابة عن هذا السؤال. "
                "يُرجى التواصل مع الصيدلي مباشرة للحصول على إجابة دقيقة."
                + MEDICAL_DISCLAIMER
            ),
            "llm_source": "out_of_scope",
            "response_time_ms": int((time.time() - t_start) * 1000),
        }

    prompt = _build_prompt(message, chunks)
    llm_source = "context_only"

    # ── Priority 1: AI-COS-Qwen-2.5 (Ollama محلي — نموذج المشروع الخاص) ───────────────
    reply = await _call_ollama(prompt)
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

    # ضمان التنويه الطبي
    if MEDICAL_DISCLAIMER.strip() not in reply:
        reply += MEDICAL_DISCLAIMER

    response_time_ms = int((time.time() - t_start) * 1000)
    return {
        "reply": reply,
        "llm_source": llm_source,
        "response_time_ms": response_time_ms,
    }
