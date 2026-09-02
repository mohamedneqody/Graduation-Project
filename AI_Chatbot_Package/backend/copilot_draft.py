# -*- coding: utf-8 -*-
"""
Human-in-the-Loop & Copilot Draft Generator Module
AI-COS Pharmacy System 2026
"""

import httpx
from typing import List, Dict, Any, Optional
from app.core.config import settings
from app.domains.agents.model_manager import get_active_model

class CopilotDraftEngine:
    """
    محرك توليد مسودات الرد الذكية للصيدلي وموظف الدعم البشري في الـ Dashboard.
    """

    @staticmethod
    async def generate_pharmacist_draft(
        customer_name: str,
        conversation_history: List[Dict[str, str]],
        escalation_reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        يولد ملخصاً للمحادثة ومسودة رد احترافية جاهزة للصيدلي بضغطة زر واحدة.
        """
        history_text = "\n".join([f"{m.get('role', 'user')}: {m.get('content', '')}" for m in conversation_history[-6:]])
        
        system_prompt = (
            "أنت المساعد الطبي الذكي (Copilot) الخاص بالصيدلي المسؤول في صيدلية AI-COS.\n"
            "مهمتك: قراءة استفسار المريض وسجل المحادثة، ثم توليد:\n"
            "1. ملخص حالة المريض في نقطتين.\n"
            "2. مسودة رد صيدلانية احترافية جاهزة للاعتماد أو التعديل من قبل الصيدلي.\n"
            "3. الإجراء الطبي المقترح (Action Required).\n"
            "أجب بالعربية الفصحى وبصياغة مهنية دقيقة."
        )

        user_prompt = (
            f"اسم المريض/العميل: {customer_name}\n"
            f"سبب التصعيد: {escalation_reason or 'استفسار يتطلب مراجعة صيدلانية'}\n"
            f"سجل المحادثة:\n{history_text}\n\n"
            f"يرجى كتابة مسودة الرد والإجراء المقترح للصيدلي:"
        )

        draft_text = None
        try:
            chat_url = settings.OLLAMA_URL.replace("/api/generate", "/api/chat")
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    chat_url,
                    json={
                        "model": get_active_model(),
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        "stream": False,
                        "options": {"temperature": 0.2, "top_p": 0.8}
                    }
                )
                if resp.status_code == 200:
                    draft_text = resp.json().get("message", {}).get("content", "").strip()
        except Exception:
            pass

        if not draft_text:
            draft_text = (
                f"مرحباً {customer_name}، معك الصيدلي المسؤول من منصة AI-COS.\n"
                f"بخصوص استفسارك، تم فحص الحالة وجاري مراجعة الوصفة والخيارات الدوائية المناسبة لضمان سلامتك التامة. سنوافيكم بالتفاصيل فوراً."
            )

        return {
            "customer_name": customer_name,
            "escalation_reason": escalation_reason,
            "draft_reply": draft_text,
            "status": "ready_for_review"
        }
