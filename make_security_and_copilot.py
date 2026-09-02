import os

security_code = '''# -*- coding: utf-8 -*-
\"\"\"
Security Guard, Input Truncation, & Prompt Injection Defense Module
AI-COS Pharmacy System 2026
\"\"\"

import re
from typing import Dict, Any, Tuple

MAX_INPUT_CHARS = 1500

ROLE_ASSUMPTION_PATTERNS = [
    r'(?:بصفتك|اعتبر نفسك|تخيل انك)\s+(?:مدير|صاحب|رئيس|طبيب استشاري|مسؤول|ادمن|admin)',
    r'(?:اعفيني من|الغي|تجاوز)\s+(?:السعر|الدفع|الفاتورة|الرسوم|التأمين)',
    r'(?:اصرفلي|اديني|هات)\s+(?:جدول|مخدر|مهدئ|ترامادول|بدون روشتة|بدون وصفة)',
]

SYSTEM_OVERRIDE_PATTERNS = [
    r'(?:ignore\s+previous\s+instructions|تجاهل\s+(?:كل\s+)?التعليمات\s+السابقة)',
    r'(?:you\s+are\s+now\s+in\s+dan\s+mode|dan\s+mode)',
    r'(?:reveal\s+system\s+prompt|كشف\s+البرومت\s+السري|system\s+prompt\s+bypass)',
    r'(?:show\s+me\s+api\s+keys|مفاتيح\s+النظام|كلمات\s+المرور\s+للسيرفر)',
]

class SecurityGuard:
    \"\"\"
    طبقة الحماية المتقدمة لصد هجمات الـ Prompt Injection وتحديد حجم المدخلات.
    \"\"\"

    @staticmethod
    def truncate_input(text: str, max_chars: int = MAX_INPUT_CHARS) -> str:
        if not text:
            return ''
        text = text.strip()
        if len(text) > max_chars:
            return text[:max_chars].strip()
        return text

    @classmethod
    def check_security(cls, text: str) -> Dict[str, Any]:
        truncated = cls.truncate_input(text)
        normalized = truncated.lower()

        is_role_attack = any(re.search(p, normalized, re.IGNORECASE) for p in ROLE_ASSUMPTION_PATTERNS)
        is_override_attack = any(re.search(p, normalized, re.IGNORECASE) for p in SYSTEM_OVERRIDE_PATTERNS)

        is_flagged = is_role_attack or is_override_attack
        blocked_reason = None
        security_reply = None

        if is_role_attack:
            blocked_reason = 'role_assumption_defense'
            security_reply = (
                \"🛡️ تنبيه أمني وسياسة النظام:\\n\"
                \"بصفتي المساعد الذكي لصيدلية AI-COS، ألتزم بسياسات الأمان واللوائح الصيدلانية الصارمة. \"
                \"لا يمكنني اتخاذ قرارات إدارية أو مالية أو تعديل الأسعار، كما يُحظر صرف أي أدوية خاضعة للرقابة الطبية دون وصفة معتمدة وفحص مباشر من الصيدلي المسؤول.\"
            )
        elif is_override_attack:
            blocked_reason = 'prompt_injection_defense'
            security_reply = (
                \"🛡️ تنبيه أمني:\\n\"
                \"تم رصد محاولة غير مصرح بها لتجاوز قواعد النظام أو طلب معلومات داخلية محمية. \"
                \"النظام يعمل وفق معايير الأمان الموثقة ولا يمكن تخطي سياسات الحماية.\"
            )

        return {
            'is_flagged': is_flagged,
            'blocked_reason': blocked_reason,
            'security_reply': security_reply,
            'sanitized_text': truncated,
            'was_truncated': len(text) > len(truncated)
        }
'''

copilot_code = '''# -*- coding: utf-8 -*-
\"\"\"
Human-in-the-Loop & Copilot Draft Generator Module
AI-COS Pharmacy System 2026
\"\"\"

import httpx
from typing import List, Dict, Any, Optional
from app.core.config import settings
from app.domains.agents.model_manager import get_active_model

class CopilotDraftEngine:
    \"\"\"
    محرك توليد مسودات الرد الذكية للصيدلي وموظف الدعم البشري في الـ Dashboard.
    \"\"\"

    @staticmethod
    async def generate_pharmacist_draft(
        customer_name: str,
        conversation_history: List[Dict[str, str]],
        escalation_reason: Optional[str] = None
    ) -> Dict[str, Any]:
        \"\"\"
        يولد ملخصاً للمحادثة ومسودة رد احترافية جاهزة للصيدلي بضغطة زر واحدة.
        \"\"\"
        history_text = \"\\n\".join([f\"{m.get('role', 'user')}: {m.get('content', '')}\" for m in conversation_history[-6:]])
        
        system_prompt = (
            \"أنت المساعد الطبي الذكي (Copilot) الخاص بالصيدلي المسؤول في صيدلية AI-COS.\\n\"
            \"مهمتك: قراءة استفسار المريض وسجل المحادثة، ثم توليد:\\n\"
            \"1. ملخص حالة المريض في نقطتين.\\n\"
            \"2. مسودة رد صيدلانية احترافية جاهزة للاعتماد أو التعديل من قبل الصيدلي.\\n\"
            \"3. الإجراء الطبي المقترح (Action Required).\\n\"
            \"أجب بالعربية الفصحى وبصياغة مهنية دقيقة.\"
        )

        user_prompt = (
            f\"اسم المريض/العميل: {customer_name}\\n\"
            f\"سبب التصعيد: {escalation_reason or 'استفسار يتطلب مراجعة صيدلانية'}\\n\"
            f\"سجل المحادثة:\\n{history_text}\\n\\n\"
            f\"يرجى كتابة مسودة الرد والإجراء المقترح للصيدلي:\"
        )

        draft_text = None
        try:
            chat_url = settings.OLLAMA_URL.replace(\"/api/generate\", \"/api/chat\")
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    chat_url,
                    json={
                        \"model\": get_active_model(),
                        \"messages\": [
                            {\"role\": \"system\", \"content\": system_prompt},
                            {\"role\": \"user\", \"content\": user_prompt}
                        ],
                        \"stream\": False,
                        \"options\": {\"temperature\": 0.2, \"top_p\": 0.8}
                    }
                )
                if resp.status_code == 200:
                    draft_text = resp.json().get(\"message\", {}).get(\"content\", \"\").strip()
        except Exception:
            pass

        if not draft_text:
            draft_text = (
                f\"مرحباً {customer_name}، معك الصيدلي المسؤول من منصة AI-COS.\\n\"
                f\"بخصوص استفسارك، تم فحص الحالة وجاري مراجعة الوصفة والخيارات الدوائية المناسبة لضمان سلامتك التامة. سنوافيكم بالتفاصيل فوراً.\"
            )

        return {
            \"customer_name\": customer_name,
            \"escalation_reason\": escalation_reason,
            \"draft_reply\": draft_text,
            \"status\": \"ready_for_review\"
        }
'''

base_dir = r'D:\Graduation Project\AI-COS-Pharmacy\backend\app\domains\ai'
pkg_dir = r'D:\Graduation Project\AI_Chatbot_Package\backend'

with open(os.path.join(base_dir, 'security_guard.py'), 'w', encoding='utf-8') as f:
    f.write(security_code)

with open(os.path.join(pkg_dir, 'security_guard.py'), 'w', encoding='utf-8') as f:
    f.write(security_code)

with open(os.path.join(base_dir, 'copilot_draft.py'), 'w', encoding='utf-8') as f:
    f.write(copilot_code)

with open(os.path.join(pkg_dir, 'copilot_draft.py'), 'w', encoding='utf-8') as f:
    f.write(copilot_code)

print('security_guard.py and copilot_draft.py created and synced successfully!')
