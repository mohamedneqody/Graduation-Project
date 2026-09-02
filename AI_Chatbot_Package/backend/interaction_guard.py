# -*- coding: utf-8 -*-
"""
In-Chat Drug-Drug Interaction (DDI) Warning Engine
AI-COS Pharmacy System 2026
"""

import re
from typing import List, Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.drug import Drug, DrugInteraction

class InteractionGuard:
    """
    محرك فحص التعارضات الدوائية التلقائي أثناء المحادثة.
    """
    
    _drugs_cache: List[Dict[str, Any]] = []

    @classmethod
    async def _load_drugs_cache(cls, db: AsyncSession) -> List[Dict[str, Any]]:
        if not cls._drugs_cache:
            stmt = select(Drug)
            result = await db.execute(stmt)
            drugs = result.scalars().all()
            cls._drugs_cache = [
                {"drug_id": d.drug_id, "name": d.name, "category": d.category}
                for d in drugs
            ]
        return cls._drugs_cache

    @classmethod
    async def check_in_chat_interactions(
        cls,
        query: str,
        history: List[Dict[str, str]],
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        if db is None:
            return {"has_interaction": False}

        drugs_list = await cls._load_drugs_cache(db)
        if not drugs_list:
            return {"has_interaction": False}

        # تجميع نص المحادثة الحديثة (السؤال الحالي + آخر 4 رسائل)
        context_text = query.lower() + " " + " ".join([m.get("content", "").lower() for m in history[-4:]])

        # مطابقة الأدوية المذكورة
        mentioned_drugs = []
        for d in drugs_list:
            d_name = d["name"].lower()
            # فحص اسم الدواء الأساسي
            first_word = d_name.split()[0]
            if len(first_word) >= 3 and (d_name in context_text or first_word in context_text):
                if d not in mentioned_drugs:
                    mentioned_drugs.append(d)

        if len(mentioned_drugs) < 2:
            return {"has_interaction": False, "detected_drugs": [d["name"] for d in mentioned_drugs]}

        # فحص التعارض بين أزواج الأدوية
        for i in range(len(mentioned_drugs)):
            for j in range(i + 1, len(mentioned_drugs)):
                da = mentioned_drugs[i]
                db_item = mentioned_drugs[j]

                # ترتيب الـ UUIDs ليتوافق مع قيد قاعدة البيانات ck_interaction_pair_order
                id_a, id_b = (da["drug_id"], db_item["drug_id"]) if str(da["drug_id"]) < str(db_item["drug_id"]) else (db_item["drug_id"], da["drug_id"])

                stmt = select(DrugInteraction).where(
                    DrugInteraction.drug_id_a == id_a,
                    DrugInteraction.drug_id_b == id_b
                )
                res = await db.execute(stmt)
                interaction = res.scalars().first()

                if interaction:
                    severity_ar = "عالي الخطورة (Severe)" if interaction.severity == "high" else "متوسط (Moderate)"
                    note_text = f" التفاصيل: {interaction.note}" if interaction.note else ""
                    warning_banner = (
                        f"⚠️ تحذير سريري - تعارض دوائي ({severity_ar}):\n"
                        f"تم رصد احتمالية تعارض بين دواء ({da['name']}) ودواء ({db_item['name']}).{note_text}\n"
                        f"يُرجى استشارة الصيدلي أو الطبيب قبل الجمع بينهما لتجنب أي آثار جانبية."
                    )
                    return {
                        "has_interaction": True,
                        "drug_a": da["name"],
                        "drug_b": db_item["name"],
                        "severity": interaction.severity,
                        "note": interaction.note,
                        "warning_banner": warning_banner,
                        "detected_drugs": [d["name"] for d in mentioned_drugs]
                    }

        return {"has_interaction": False, "detected_drugs": [d["name"] for d in mentioned_drugs]}
