import json
from app.domains.ai.service import _call_gemini, _call_ollama
from app.core.config import settings

async def execute_query(query: str, context_data: dict = None) -> dict:
    """
    Executive Agent: Routes a natural language query to the appropriate agent logic.
    """
    prompt = f"""
    أنت المدير التنفيذي (Executive Agent) في نظام الذكاء الاصطناعي لصيدلية AI-COS.
    لديك 3 أقسام رئيسية:
    1. marketing: مسؤول عن العروض والتسويق ورسائل العملاء.
    2. pricing: مسؤول عن تحديد نسب الخصومات للعملاء بناءً على ولائهم.
    3. analytics: مسؤول عن الإحصائيات والمبيعات.
    
    استفسار الصيدلي: {query}
    
    مهمتك:
    قم بتحديد القسم الأنسب للرد على الاستفسار. ثم أجب على الاستفسار بنفسك نيابة عن هذا القسم بشكل مختصر.
    
    يجب أن يكون الرد بصيغة JSON فقط كالتالي:
    {{
        "routed_to": "marketing | pricing | analytics",
        "response_text": "إجابتك المباشرة هنا"
    }}
    لا تضف أي نصوص خارج الـ JSON.
    """

    # Priority 1: Gemini
    reply = await _call_gemini(prompt)
    llm_source = f"gemini:{settings.GEMINI_MODEL}"

    # Priority 2: Ollama Fallback
    if not reply:
        reply = await _call_ollama(prompt)
        llm_source = f"ollama:{settings.OLLAMA_MODEL}"

    if not reply:
        return {
            "routed_to": "unknown",
            "response_text": "عذراً، لم أتمكن من الاتصال بخدمات الذكاء الاصطناعي حالياً.",
            "llm_source": "hard_fallback"
        }

    reply = reply.strip()
    if reply.startswith("```json"):
        reply = reply[7:]
    if reply.startswith("```"):
        reply = reply[3:]
    if reply.endswith("```"):
        reply = reply[:-3]
    reply = reply.strip()

    try:
        data = json.loads(reply)
        data["llm_source"] = llm_source
        return data
    except json.JSONDecodeError:
        return {
            "routed_to": "unknown",
            "response_text": reply,
            "llm_source": llm_source
        }
