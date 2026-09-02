import json
from app.domains.ai.service import _call_gemini, _call_ollama
from app.core.config import settings

async def generate_marketing_campaign(customer_name: str, drug_name: str, discount: int = None) -> dict:
    """
    Marketing Agent: Generates promotional text and optionally a coupon.
    
    ملاحظة: الكوبون حاليًا نص توضيحي ضمن الرسالة فقط، بدون منطق تحقق أو خصم فعلي عند الشراء — هذا Feature مستقبلي خارج نطاق MVP الحالي، وليس عيبًا يحتاج إصلاحًا فوريًا.
    """
    prompt = f"""
    أنت صيدلي خبير في التسويق الصحي والاحتفاظ بالعملاء (Customer Retention) في 'صيدلية AI-COS'.
    العميل: {customer_name}
    الدواء الذي يوشك على الانتهاء: {drug_name}
    الخصم المتاح: {f'{discount}%' if discount else 'لا يوجد خصم مخصص'}

    هدف المشروع:
    تحسين الالتزام بالعلاج (Medication Adherence) للمرضى أصحاب الأمراض المزمنة، وزيادة مبيعات الصيدلية عبر التذكير الاستباقي (Proactive Reminders) المدعوم بالذكاء الاصطناعي.

    مهمتك:
    كتابة نص رسالة (جملتين فقط، قصيرة ومباشرة جداً) موجهة للعميل، وتطبيق القواعد النفسية التالية:
    1. التعاطف والرعاية (Empathy): ابدأ بالاطمئنان على صحته، وأن رسالتنا هدفها حمايته.
    2. الأهمية الطبية (Urgency): التذكير بلطف بخطورة انقطاع العلاج.
    3. الراحة (Convenience): طمأنته أن إعادة الطلب تتم بضغطة زر.
    4. الكوبون (إن وجد): قدم الخصم كـ "هدية خاصة لدعمه" وليس كمجرد ترويج تجاري.
    5. إذا كان هناك خصم، ولّد كود خصم قصير مكون من 5 أحرف وأرقام (مثل CARE15).

    يجب أن يكون الرد بصيغة JSON فقط كالتالي:
    {{
        "message_text": "نص الرسالة هنا",
        "coupon_code": "الكود هنا أو null إذا لم يوجد خصم"
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
        # Hard fallback
        return {
            "message_text": f"مرحباً {customer_name}، دواء {drug_name} قارب على الانتهاء. نرجو إعادة الطلب.",
            "coupon_code": None,
            "llm_source": "hard_fallback"
        }

    # Clean JSON response (in case the LLM wrapped it in markdown code blocks)
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
        if "coupon_code" not in data or not data["coupon_code"]:
            data["coupon_code"] = "CARE15" if discount else None
        return data
    except json.JSONDecodeError:
        import re
        
        # Aggressive cleaning for ANY JSON-like structure
        msg = reply
        # Try to extract the message text if it's inside quotes after message_text
        msg_match = re.search(r'"message_text"\s*:\s*"([^"]+)"', reply, re.DOTALL)
        if msg_match:
            msg = msg_match.group(1)
        
        # If it still looks like JSON, strip all JSON syntax
        msg = re.sub(r'\{?\s*"?message_text"?\s*:\s*"?', '', msg)
        msg = re.sub(r'\{?\s*"?coupon_code"?\s*:\s*"?', '', msg)
        msg = re.sub(r'["\}]+$', '', msg)
        msg = msg.strip()
            
        coupon_match = re.search(r'"coupon_code"\s*:\s*"([^"]+)"', reply)
        coupon = coupon_match.group(1) if coupon_match and coupon_match.group(1) else ("CARE15" if discount else None)
        
        return {
            "message_text": msg,
            "coupon_code": coupon,
            "llm_source": llm_source
        }
