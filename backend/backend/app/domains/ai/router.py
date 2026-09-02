from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from . import schemas, service

router = APIRouter()


@router.post(
    "/chat",
    response_model=schemas.AIChatResponse,
    summary="Chat with the pharmacy AI bot (RAG)",
)
async def chat_with_ai(
    request: schemas.AIChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    بوت الصيدلية الذكي — RAG Pipeline (3-Tier LLM):

    **الأولوية:**
    1. **Gemini 2.5-flash** (Cloud API — `GEMINI_API_KEY` في `.env`) — ~0.9ث
    2. **Gemma3:4b** (Ollama محلي — احتياط بدون إنترنت) — ~18-60ث
    3. **Context-Only** (بدون LLM — يعمل دائماً)

    **الرد يحتوي على:**
    - `reply`: الإجابة
    - `llm_source`: من أجاب (`gemini:*` | `ollama:*` | `context_only`)
    - `response_time_ms`: وقت الرد الكامل بالميلي ثانية
    """
    result = await service.generate_ai_response(request.message, db)
    return result
