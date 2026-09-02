# -*- coding: utf-8 -*-
"""
Arabic NLP Preprocessing and Medical Colloquial Expansion Module
AI-COS Pharmacy System
"""

import re

TASHKEEL_REGEX = re.compile(r'[ؗ-ًؚ-ْۖ-ۭ]')
TATWEEL_REGEX = re.compile(r'ـ')

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
    text = re.sub(r'(.){2,}', r'', text)
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
