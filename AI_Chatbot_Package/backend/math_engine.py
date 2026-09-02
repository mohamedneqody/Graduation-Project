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
                f"[بيان حسابي موثق ومحسوب بدقة 100%:\n"
                f"- سعر العبوة: {res['base_price']} {res['currency']}\n"
                f"- الكمية المطلوبة: {res['quantity']} علبة\n"
                f"- الإجمالي قبل الخصم: {res['subtotal']} {res['currency']}\n"
                f"- نسبة الخصم: {res['discount_percent']}% (قيمة الخصم: {res['discount_amount']} {res['currency']})\n"
                f"- الإجمالي النهائي للدفع: {res['total']} {res['currency']}]"
            )
        return None
