import json
from app.domains.ai.service import _call_gemini, _call_ollama
from app.core.config import settings

async def calculate_pricing_discount(customer_name: str, churn_probability: float, order_count: int) -> dict:
    """
    Pricing Agent: Decides the discount percentage based on churn risk and loyalty.
    """
    prompt = f"""
    أنت خبير مالي وتسعير في 'صيدلية AI-COS'.
    بيانات العميل الحالية:
    - اسم العميل: {customer_name}
    - احتمالية التوقف عن الشراء (Churn Probability): {churn_probability} (من 0 إلى 1)
    - عدد الطلبات السابقة: {order_count}

    مهمتك:
    حدد نسبة الخصم المناسبة للحفاظ على هذا العميل وتشجيعه على الشراء، مع الحفاظ على أرباح الصيدلية.
    - إذا كانت الاحتمالية عالية (> 0.7) والعميل قديم (عدد الطلبات > 3)، أعطه خصم 15% أو 20%.
    - إذا كانت الاحتمالية متوسطة، أعطه 5% أو 10%.
    - إذا كانت الاحتمالية منخفضة جداً والعميل يشتري بانتظام، أعطه 0%.

    يجب أن يكون الرد بصيغة JSON فقط كالتالي:
    {{
        "discount_percentage": 10,
        "rationale": "مبرر الخصم هنا في جملة واحدة"
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
            "discount_percentage": 0,
            "rationale": "Fallback mode - no discount applied.",
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
            "discount_percentage": 0,
            "rationale": "Failed to parse LLM response.",
            "llm_source": llm_source
        }
