# -*- coding: utf-8 -*-
"""
Sentiment Analysis and Emergency Medical Escalation Module
AI-COS Pharmacy System
"""

import re
from typing import Dict, Any

EMERGENCY_KEYWORDS = [
    'ضيق تنفس', 'مش قادر اتنفس', 'اغماء', 'تسمم', 'بلع شريط', 'جرعة زايدة',
    'جرعة مفرطة', 'حساسية حادة', 'نزيف', 'تورم في الوجه', 'ضربات قلب سريعة',
    'غيبوبة', 'الم شديد في الصدر', 'جلطة'
]

ANGER_KEYWORDS = [
    'نصب', 'خدمة زفت', 'خدمة سيئة', 'اتأخرتوا', 'هرفع شكوى', 'اشتكيكم',
    'فلوسي', 'زعلان', 'فاشلين', 'نصابين'
]

class EscalationEngine:
    @staticmethod
    def analyze(query: str) -> Dict[str, Any]:
        normalized = query.lower()
        is_emergency = any(kw in normalized for kw in EMERGENCY_KEYWORDS)
        is_angry = any(kw in normalized for kw in ANGER_KEYWORDS)
        
        priority = 'normal'
        status = 'automated'
        alert_message = None
        
        if is_emergency:
            priority = 'critical_emergency'
            status = 'escalated_to_doctor'
            alert_message = (
                "🚨 حالة طوارئ طبية عاجلة:\n"
                "يُرجى التوجه فوراً إلى أقرب مستشفى أو الاتصال بالإسعاف (123). "
                "تم إرسال تنبيه عاجل للصيدلي المناوب وفريق الرعاية الطبية."
            )
        elif is_angry:
            priority = 'high_priority'
            status = 'escalated_to_support'
            alert_message = (
                "نعتذر جداً عن أي إزعاج. تم فتح تذكرة دعم ذات أولوية قصوى "
                "وتحويل شكواك إلى مسؤول خدمة العملاء للتواصل معك فوراً."
            )
            
        return {
            'is_emergency': is_emergency,
            'is_angry': is_angry,
            'priority': priority,
            'status': status,
            'alert_message': alert_message
        }
