# -*- coding: utf-8 -*-
"""
Security Guard, Input Truncation, & Prompt Injection Defense Module
AI-COS Pharmacy System 2026
"""

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
    """
    طبقة الحماية المتقدمة لصد هجمات الـ Prompt Injection وتحديد حجم المدخلات.
    """

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
                "🛡️ تنبيه أمني وسياسة النظام:\n"
                "بصفتي المساعد الذكي لصيدلية AI-COS، ألتزم بسياسات الأمان واللوائح الصيدلانية الصارمة. "
                "لا يمكنني اتخاذ قرارات إدارية أو مالية أو تعديل الأسعار، كما يُحظر صرف أي أدوية خاضعة للرقابة الطبية دون وصفة معتمدة وفحص مباشر من الصيدلي المسؤول."
            )
        elif is_override_attack:
            blocked_reason = 'prompt_injection_defense'
            security_reply = (
                "🛡️ تنبيه أمني:\n"
                "تم رصد محاولة غير مصرح بها لتجاوز قواعد النظام أو طلب معلومات داخلية محمية. "
                "النظام يعمل وفق معايير الأمان الموثقة ولا يمكن تخطي سياسات الحماية."
            )

        return {
            'is_flagged': is_flagged,
            'blocked_reason': blocked_reason,
            'security_reply': security_reply,
            'sanitized_text': truncated,
            'was_truncated': len(text) > len(truncated)
        }
