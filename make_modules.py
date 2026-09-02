import os

nlp_code = '''# -*- coding: utf-8 -*-
\"\"\"
Arabic NLP Preprocessing and Medical Colloquial Expansion Module
AI-COS Pharmacy System
\"\"\"

import re

TASHKEEL_REGEX = re.compile(r'[\u0617-\u061A\u064B-\u0652\u06D6-\u06ED]')
TATWEEL_REGEX = re.compile(r'\u0640')

COLLOQUIAL_MEDICAL_THESAURUS = {
    'سخونية': 'خافض حرارة مسكن antipyretic',
    'حرارة': 'خافض حرارة مسكن antipyretic',
    'سخن': 'خافض حرارة مسكن',
    'كحة ناشفة': 'سعال جاف مهدئ كحة',
    'كحة ببلغم': 'مذيب بلغم طارد للبلغم',
    'كحة': 'سعال كحة كحه',
    'بلغم': 'مذيب بلغم طارد للبلغم',
    'مغص': 'مضاد للتقلصات مسكن للمعدة مغص',
    'بطني': 'مغص جهاز هضمي معدة تقلصات',
    'تقلصات': 'مضاد تقلصات سبازمو',
    'حموضة': 'مضاد حموضة فوار antacid معدة',
    'حرقان': 'مضاد حموضة فوار معدة',
    'فوار': 'فوار أملاح مسكن حموضة',
    'رشح': 'نزلات برد زكام رشح cold flu',
    'زكام': 'نزلات برد زكام احتقان',
    'برد': 'نزلات برد cold flu خافض حرارة',
    'انفلونزا': 'نزلات برد خافض حرارة مسكن',
    'صداع': 'مسكن آلام صداع analgesic paracetamol',
    'صداعي': 'مسكن آلام صداع',
    'راسي': 'صداع مسكن آلام',
    'حساسية': 'مضاد حساسية antihistamine alerid',
    'هرش': 'مضاد حساسية حكة',
    'عطس': 'مضاد حساسية نزلات برد',
    'ضغط': 'ضغط دم أدوية مزمنة chronic',
    'سكر': 'سكر داء السكري أدوية مزمنة',
    'كوليسترول': 'دهون كوليسترول أدوية مزمنة',
    'حنين': 'أقل سعر اقتصادي رخيص',
    'رخيص': 'أقل سعر اقتصادي رخيص',
    'بكام': 'سعر تكلفة ج.م',
    'تمنه': 'سعر تكلفة ج.م',
    'سعره': 'سعر تكلفة ج.م',
    'خصم': 'كود خصم تخفيض CARE15 كوبون',
    'كوبون': 'كود خصم تخفيض CARE15',
    'حساب': 'إنشاء حساب جديد تسجيل مستخدم Google OAuth',
}

def normalize_arabic(text: str) -> str:
    if not text:
        return ''
    text = TASHKEEL_REGEX.sub('', text)
    text = TATWEEL_REGEX.sub('', text)
    text = re.sub(r'[إأآا]', 'ا', text)
    text = re.sub(r'ة', 'ه', text)
    text = re.sub(r'ى', 'ي', text)
    text = re.sub(r'ؤ', 'و', text)
    text = re.sub(r'ئ', 'ي', text)
    text = re.sub(r'(.)\1{2,}', r'\1\1', text)
    return text.strip()

def light_stem(word: str) -> str:
    if len(word) <= 3:
        return word
    for prefix in ['وال', 'فال', 'كال', 'بال', 'لل', 'ال']:
        if word.startswith(prefix) and len(word) - len(prefix) >= 3:
            word = word[len(prefix):]
            break
    for suffix in ['ات', 'ين', 'ون', 'ها', 'هم', 'هن', 'كم', 'نا', 'يه', 'ية']:
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            word = word[:-len(suffix)]
            break
    return word

def expand_colloquial_medical(query: str) -> tuple[str, list[str]]:
    normalized = normalize_arabic(query.lower())
    matched_expansions = []
    for term, expansion in COLLOQUIAL_MEDICAL_THESAURUS.items():
        norm_term = normalize_arabic(term)
        if norm_term in normalized:
            matched_expansions.append(expansion)
    expanded_text = query
    if matched_expansions:
        expanded_text = f'{query} ' + ' '.join(set(matched_expansions))
    return expanded_text, matched_expansions
'''

math_code = '''# -*- coding: utf-8 -*-
\"\"\"
Deterministic Math and Dosage Calculator Module
AI-COS Pharmacy System
\"\"\"

import re
import math
from typing import Optional, Dict, Any

class DeterministicMathEngine:
    @staticmethod
    def calculate_price_with_discount(base_price: float, quantity: int = 1, discount_percent: float = 0.0) -> Dict[str, Any]:
        subtotal = base_price * quantity
        discount_amount = subtotal * (discount_percent / 100.0)
        total = subtotal - discount_amount
        return {
            'base_price': round(base_price, 2),
            'quantity': quantity,
            'subtotal': round(subtotal, 2),
            'discount_percent': discount_percent,
            'discount_amount': round(discount_amount, 2),
            'total': round(total, 2),
            'currency': 'ج.م'
        }

    @staticmethod
    def calculate_dosage_consumption(pills_per_day: float, duration_days: int, pills_per_box: int = 10) -> Dict[str, Any]:
        total_pills_needed = pills_per_day * duration_days
        boxes_needed = math.ceil(total_pills_needed / max(1, pills_per_box))
        return {
            'pills_per_day': pills_per_day,
            'duration_days': duration_days,
            'total_pills_needed': total_pills_needed,
            'pills_per_box': pills_per_box,
            'boxes_needed': boxes_needed
        }

    @classmethod
    def extract_and_solve_math(cls, query: str, context_chunks: list[dict]) -> Optional[str]:
        base_price = None
        for chunk in context_chunks:
            price_match = re.search(r'السعر الأساسي:\s*([\d\.]+)', chunk.get('content', ''))
            if price_match:
                base_price = float(price_match.group(1))
                break
                
        qty_match = re.search(r'(?:عايز|عاوز|محتاج|شراء|كمية|احسبلي|سعر)\s*(\d+)\s*(?:علب|علبة|شريط|قطع|عبوة|منه)?', query)
        qty = int(qty_match.group(1)) if qty_match else 1
        
        discount_match = re.search(r'خصم\s*(\d+)%', query)
        discount = float(discount_match.group(1)) if discount_match else 0.0
        
        if 'care15' in query.lower():
            discount = 15.0

        if base_price is not None and (qty > 1 or discount > 0):
            res = cls.calculate_price_with_discount(base_price, qty, discount)
            return (
                f\"[بيان حسابي موثق ومحسوب بدقة 100%:\\n\"
                f\"- سعر العبوة: {res['base_price']} {res['currency']}\\n\"
                f\"- الكمية المطلوبة: {res['quantity']} علبة\\n\"
                f\"- الإجمالي قبل الخصم: {res['subtotal']} {res['currency']}\\n\"
                f\"- نسبة الخصم: {res['discount_percent']}% (قيمة الخصم: {res['discount_amount']} {res['currency']})\\n\"
                f\"- الإجمالي النهائي للدفع: {res['total']} {res['currency']}]\"
            )
        return None
'''

coreference_code = '''# -*- coding: utf-8 -*-
\"\"\"
Coreference Resolution and Stateful Contextual RAG Module
AI-COS Pharmacy System
\"\"\"

import re
from typing import Optional, List, Dict

PRONOUN_PATTERNS = [
    r'^(?:طب\s+)?(?:كم\s+)?(?:سعره|سعرها|تمنه|تمنها|بكام|ثمنه)\??$',
    r'^(?:هل\s+)?(?:متوفر|متاح|موجود|فيه\s+منه)\??$',
    r'^(?:ما\s+هي\s+)?(?:جرعته|جرعتها|بيتاخد\s+ازاي)\??$',
    r'^(?:ما\s+هي\s+)?(?:بدائله|بديله|بديلها)\??$',
    r'^(?:هل\s+فيه\s+)?(?:تعارض\s+معه|تداخل\s+معه)\??$',
    r'^(?:ما\s+هو\s+)?اسمي\??$',
]

class CoreferenceResolver:
    @staticmethod
    def extract_last_entity(history: List[Dict[str, str]]) -> Optional[str]:
        for msg in reversed(history):
            content = msg.get('content', '')
            drug_match = re.search(r'([A-Za-z0-9\-\s]{3,30}(?:mg|tabs|caps|syrup)?)', content, re.IGNORECASE)
            if drug_match and len(drug_match.group(1).strip()) > 2:
                candidate = drug_match.group(1).strip()
                if candidate.lower() not in ('ai-cos', 'qwen', 'ollama', 'gemini', 'care15'):
                    return candidate
        return None

    @staticmethod
    def extract_user_name(history: List[Dict[str, str]]) -> Optional[str]:
        for msg in history:
            if msg.get('role') == 'user':
                content = msg.get('content', '')
                name_match = re.search(r'(?:انا اسمي|اسمي هو|اسمي)\s+([^\s\?\.!،]+)', content)
                if name_match:
                    return name_match.group(1).strip()
        return None

    @classmethod
    def resolve_query(cls, query: str, history: List[Dict[str, str]]) -> str:
        trimmed = query.strip()
        if re.search(r'^(?:ما\s+هو\s+)?اسمي\??$', trimmed):
            name = cls.extract_user_name(history)
            if name:
                return f\"ما هو اسمي (اسم المستخدم المذكور سابقاً: {name})\"
                
        for pattern in PRONOUN_PATTERNS:
            if re.search(pattern, trimmed, re.IGNORECASE):
                last_drug = cls.extract_last_entity(history)
                if last_drug:
                    return f\"{query} بخصوص دواء {last_drug}\"
                    
        return query
'''

escalation_code = '''# -*- coding: utf-8 -*-
\"\"\"
Sentiment Analysis and Emergency Medical Escalation Module
AI-COS Pharmacy System
\"\"\"

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
                \"🚨 حالة طوارئ طبية عاجلة:\\n\"
                \"يُرجى التوجه فوراً إلى أقرب مستشفى أو الاتصال بالإسعاف (123). \"
                \"تم إرسال تنبيه عاجل للصيدلي المناوب وفريق الرعاية الطبية.\"
            )
        elif is_angry:
            priority = 'high_priority'
            status = 'escalated_to_support'
            alert_message = (
                \"نعتذر جداً عن أي إزعاج. تم فتح تذكرة دعم ذات أولوية قصوى \"
                \"وتحويل شكواك إلى مسؤول خدمة العملاء للتواصل معك فوراً.\"
            )
            
        return {
            'is_emergency': is_emergency,
            'is_angry': is_angry,
            'priority': priority,
            'status': status,
            'alert_message': alert_message
        }
'''

hybrid_code = '''# -*- coding: utf-8 -*-
\"\"\"
Two-Stage Hybrid Retrieval (BM25 Lexical + BERT Dense) Module
AI-COS Pharmacy System
\"\"\"

import re
from typing import List, Dict, Any
from app.domains.ai.nlp_processor import normalize_arabic, light_stem

class BM25LexicalRetriever:
    @classmethod
    def score_chunk(cls, query: str, chunk_content: str) -> float:
        norm_query = normalize_arabic(query.lower())
        norm_chunk = normalize_arabic(chunk_content.lower())
        
        query_words = [light_stem(w) for w in norm_query.split() if len(w) > 1]
        chunk_words = [light_stem(w) for w in norm_chunk.split() if len(w) > 1]
        
        if not query_words or not chunk_words:
            return 0.0
            
        exact_boost = 0.0
        query_numbers = re.findall(r'\\d+', query)
        chunk_numbers = re.findall(r'\\d+', chunk_content)
        common_numbers = set(query_numbers).intersection(set(chunk_numbers))
        if common_numbers:
            exact_boost += 0.3 * len(common_numbers)
            
        matched_count = 0
        for qw in query_words:
            if qw in chunk_words or any(qw in cw for cw in chunk_words):
                matched_count += 1
                
        lexical_score = (matched_count / len(query_words)) + exact_boost
        return min(1.0, lexical_score)

    @classmethod
    def hybrid_rerank(
        cls,
        query: str,
        dense_chunks: List[Dict[str, Any]],
        weight_dense: float = 0.6,
        weight_lexical: float = 0.4
    ) -> List[Dict[str, Any]]:
        reranked = []
        for chunk in dense_chunks:
            content = chunk.get('content', '')
            dense_sim = float(chunk.get('similarity', 0.5))
            lex_score = cls.score_chunk(query, content)
            
            hybrid_score = (weight_dense * dense_sim) + (weight_lexical * lex_score)
            
            item = dict(chunk)
            item['dense_similarity'] = dense_sim
            item['lexical_score'] = lex_score
            item['hybrid_score'] = hybrid_score
            reranked.append(item)
            
        reranked.sort(key=lambda x: x['hybrid_score'], reverse=True)
        return reranked
'''

base_dir = r'D:\Graduation Project\AI-COS-Pharmacy\backend\app\domains\ai'
pkg_dir = r'D:\Graduation Project\AI_Chatbot_Package\backend'

modules = {
    'nlp_processor.py': nlp_code,
    'math_engine.py': math_code,
    'coreference.py': coreference_code,
    'escalation.py': escalation_code,
    'hybrid_search.py': hybrid_code
}

for name, content in modules.items():
    p1 = os.path.join(base_dir, name)
    p2 = os.path.join(pkg_dir, name)
    with open(p1, 'w', encoding='utf-8') as f:
        f.write(content)
    with open(p2, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'Created: {name}')

print('All 5 advanced modules successfully created and synced!')
