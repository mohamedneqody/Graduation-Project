# -*- coding: utf-8 -*-
"""
Deterministic Math and Dosage Calculator Module
AI-COS Pharmacy System
"""

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
        drug_name = None
        q_lower = query.lower()

        # Clean leading numbers/bullets like "7. " or "7 - "
        clean_q = re.sub(r'^\s*\d+[\.\-\)]\s*', '', query)

        # 1. Prioritize chunk matching the specific drug mentioned in query
        for chunk in context_chunks:
            c_text = chunk.get('content', '')
            price_match = re.search(r'السعر الأساسي:\s*([\d\.]+)', c_text)
            name_match = re.search(r'اسم الدواء:\s*([^\n]+)', c_text)
            if price_match and name_match:
                d_name = name_match.group(1).strip()
                d_lower = d_name.lower()
                first_word = d_lower.split()[0] if d_lower.split() else ""
                if d_lower in q_lower or (len(first_word) >= 3 and first_word in q_lower):
                    base_price = float(price_match.group(1))
                    drug_name = d_name
                    break

        # 2. Fallback to first chunk with price if no drug name matched
        if base_price is None:
            for chunk in context_chunks:
                c_text = chunk.get('content', '')
                price_match = re.search(r'السعر الأساسي:\s*([\d\.]+)', c_text)
                name_match = re.search(r'اسم الدواء:\s*([^\n]+)', c_text)
                if price_match:
                    base_price = float(price_match.group(1))
                    if name_match:
                        drug_name = name_match.group(1).strip()
                    break

        # 3. Extract quantity
        qty = 1
        qty_match = re.search(r'(\d+)\s*(?:علب|علبة|شريط|شرايط|قطع|قطعة|عبوة|عبوات|منه|باكت)', clean_q)
        if not qty_match:
            qty_match = re.search(r'(?:عايز|عاوز|محتاج|شراء|كمية|احسبلي|سعر|تكلفة|احسب|عدد)\s*(\d+)', clean_q)
        if qty_match:
            qty = int(qty_match.group(1))

        # 4. Extract discount code or percentage
        discount = 0.0
        code_label = ""
        code_match = re.search(r'\b(care\s*(\d+))\b', q_lower)
        if code_match:
            code_str = code_match.group(1).upper().replace(" ", "")
            discount = float(code_match.group(2))
            code_label = f" (كود الخصم: {code_str} بنسبة {int(discount)}%)"
        else:
            pct_match = re.search(r'(?:خصم|نسبة)?\s*(\d+)\s*(?:%|في\s*الم[يإا]ه)', query)
            if pct_match:
                discount = float(pct_match.group(1))
                code_label = f" (خصم بنسبة {int(discount)}%)"

        if base_price is not None and (qty > 1 or discount > 0):
            res = cls.calculate_price_with_discount(base_price, qty, discount)
            med_header = f" لدواء ({drug_name})" if drug_name else ""
            discount_line = ""
            qty_unit = "عبوات" if 3 <= res['quantity'] <= 10 else "عبوة"
            if discount > 0:
                discount_line = f"• **قيمة الخصم المطبق{code_label}:** {res['discount_amount']:.2f} {res['currency']} (خصم {res['discount_percent']}%)\n"
            
            total_label = "الإجمالي النهائي للدفع بعد الخصم:" if discount > 0 else "الإجمالي النهائي للدفع:"
            return (
                f"🧾 **تفاصيل حساب الفاتورة الرسمية{med_header}:**\n\n"
                f"• **سعر العبوة الواحدة:** {res['base_price']:.2f} {res['currency']}\n"
                f"• **الكمية المطلوبة:** {res['quantity']} {qty_unit}\n"
                f"• **الإجمالي قبل الخصم:** {res['subtotal']:.2f} {res['currency']}\n"
                f"{discount_line}"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"💰 **{total_label}** **{res['total']:.2f} {res['currency']}**"
            )
        return None

