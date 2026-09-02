# -*- coding: utf-8 -*-
"""
Coreference Resolution and Stateful Contextual RAG Module
AI-COS Pharmacy System
"""

import re
from typing import Optional, List, Dict

PRONOUN_PATTERNS = [
    r'^(?:طب\s+)?(?:كم\s+)?(?:سعره|سعرها|تمنه|تمنها|بكام|ثمنه)',
    r'^(?:هل\s+)?(?:متوفر|متاح|موجود|فيه\s+منه)',
    r'^(?:ما\s+هي\s+)?(?:جرعته|جرعتها|بيتاخد\s+ازاي)',
    r'^(?:ما\s+هي\s+)?(?:بدائله|بديله|بديلها)',
    r'^(?:هل\s+فيه\s+)?(?:تعارض\s+معه|تداخل\s+معه)',
    r'^(?:ما\s+هو\s+)?اسمي',
]

class CoreferenceResolver:
    @staticmethod
    def extract_last_entity(history: List[Dict[str, str]]) -> Optional[str]:
        for msg in reversed(history):
            content = msg.get('content', '')
            ar_match = re.search(r'(?:دواء|علاج|مستحضر|اسم الدواء:?)\s+([A-Za-z0-9\-\s\u0600-\u06FF]{3,40})', content)
            if ar_match:
                cand = ar_match.group(1).strip()
                cand = re.sub(r'(?:متوفر|غير مزمن|سعر|ج\.م).*', '', cand).strip()
                if len(cand) > 2:
                    return cand

            drug_match = re.search(r'\b([A-Za-z][A-Za-z0-9\-\s]{2,35}(?:mg|tabs|caps|syrup|forte|plus)?)\b', content, re.IGNORECASE)
            if drug_match:
                candidate = drug_match.group(1).strip()
                if candidate.lower() not in ('ai-cos', 'qwen', 'ollama', 'gemini', 'care15', 'http', 'https', 'none', 'error'):
                    return candidate
        return None

    @staticmethod
    def extract_user_name(history: List[Dict[str, str]]) -> Optional[str]:
        for msg in history:
            if msg.get('role') == 'user':
                content = msg.get('content', '')
                name_match = re.search(r'(?:انا اسمي|اسمي هو|اسمي)\s+([^\s\?\.!،؟]+)', content)
                if name_match:
                    return name_match.group(1).strip()
        return None

    @classmethod
    def resolve_query(cls, query: str, history: List[Dict[str, str]]) -> str:
        trimmed = query.strip().rstrip('?!؟., ')
        if re.search(r'^(?:ما\s+هو\s+)?اسمي$', trimmed):
            name = cls.extract_user_name(history)
            if name:
                return f"ما هو اسمي (اسم المستخدم المذكور سابقاً: {name})"
                
        for pattern in PRONOUN_PATTERNS:
            if re.search(pattern, trimmed, re.IGNORECASE):
                last_drug = cls.extract_last_entity(history)
                if last_drug:
                    return f"{query} بخصوص دواء {last_drug}"
                    
        return query
