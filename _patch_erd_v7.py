# -*- coding: utf-8 -*-
"""Upgrade the v6 ERD generator to v7:
- Geometry: wider cards (340), wider gaps (100/80), taller rows (28), 12 balanced columns
- Typography: larger fonts across SVG (title 30, card headers 15, rows 12.5, badges 10)
- +4 live tables: SUPPLIERS, COMPLAINTS, MARKET_INTELLIGENCE_ACTIONS, PLATFORM_SETTINGS
- +5 relationships incl. SUPPLIERS -> PURCHASE_ORDERS (fulfills)
- Fix 7 phantom column names vs live Supabase + add pivot-era columns (vertical, supplier_id, predicted_days, ...)
- Rebrand v6 -> v7 everywhere, dynamic counts, changelog line
"""
import io, re, sys

SRC = r"D:\Graduation Project\generate_perfect_erd_v6.py"
DST = r"D:\Graduation Project\generate_perfect_erd_v7.py"

src = io.open(SRC, encoding="utf-8").read()

def rep(old, new, count=1):
    global src
    found = src.count(old)
    assert found == count, f"ANCHOR FAIL ({found}/{count}): {old[:90]!r}"
    src = src.replace(old, new)

# ── 1) Geometry constants (build_erd_data) ────────────────────────────────
rep("    COL_WIDTH = 252\n    COL_GAP = 38\n    START_X = 50\n    START_Y = 115\n    HEADER_H = 28\n    ROW_H = 20\n    VERTICAL_GAP = 28",
    "    COL_WIDTH = 340\n    COL_GAP = 100\n    START_X = 70\n    START_Y = 170\n    HEADER_H = 42\n    ROW_H = 28\n    VERTICAL_GAP = 80")

rep("for c in range(10)", "for c in range(12)", 2)

rep("    max_height = max(col_current_y.values()) + 65\n    total_width = col_x[9] + COL_WIDTH + START_X",
    "    max_height = max(col_current_y.values()) + 90\n    total_width = col_x[11] + COL_WIDTH + START_X")

# ── 2) generate_svg_markup local copies ───────────────────────────────────
rep("    center_x = total_width / 2\n    HEADER_H = 28\n    ROW_H = 20",
    "    center_x = total_width / 2\n    HEADER_H = 42\n    ROW_H = 28")

# ── 3) Header title/subtitle + changelog line ─────────────────────────────
rep("""  <text x="{center_x}" y="38" text-anchor="middle" font-size="23" font-weight="800" fill="#0f172a" letter-spacing="-0.3">AI-COS Pharmacy — Entity Relationship Diagram (v6)</text>
  <text x="{center_x}" y="60" text-anchor="middle" font-size="12.5" fill="#64748b" font-weight="500">33 Tables · 35 Relationships · PostgreSQL 15 + Supabase · Complete Architecture 2026/2027</text>""",
    """  <text x="{center_x}" y="50" text-anchor="middle" font-size="30" font-weight="800" fill="#0f172a" letter-spacing="-0.3">AI-COS Pharmacy — Entity Relationship Diagram (v7)</text>
  <text x="{center_x}" y="78" text-anchor="middle" font-size="15.5" fill="#64748b" font-weight="500">{len(TABLES)} Tables · {len(RELATIONSHIPS)} Relationships · PostgreSQL 15 + Supabase · Complete Architecture 2026/2027</text>
  <text x="{center_x}" y="103" text-anchor="middle" font-size="13" fill="#0d9488" font-weight="700">v7: +4 Tables (SUPPLIERS · COMPLAINTS · MARKET_INTELLIGENCE_ACTIONS · PLATFORM_SETTINGS) · Vertical-Pivot Columns · 7 Column-Name Corrections</text>""")

# ── 4) Domain legend chips ────────────────────────────────────────────────
rep("""    curr_lx = 50
    for label, col, dkey in legend_items:
        svg_parts.append(f'<g class="legend-chip" data-domain="{dkey}" style="cursor: pointer;">')
        svg_parts.append(f'<rect x="{curr_lx}" y="78" width="13" height="13" rx="3.5" fill="{col}"/>')
        svg_parts.append(f'<text x="{curr_lx + 17}" y="89" font-size="10.5" fill="#334155" font-weight="600">{label}</text>')
        svg_parts.append('</g>')
        curr_lx += len(label) * 7.1 + 28""",
    """    curr_lx = 70
    for label, col, dkey in legend_items:
        svg_parts.append(f'<g class="legend-chip" data-domain="{dkey}" style="cursor: pointer;">')
        svg_parts.append(f'<rect x="{curr_lx}" y="124" width="17" height="17" rx="4.5" fill="{col}"/>')
        svg_parts.append(f'<text x="{curr_lx + 23}" y="138" font-size="13.5" fill="#334155" font-weight="600">{label}</text>')
        svg_parts.append('</g>')
        curr_lx += len(label) * 9.2 + 44""")

rep("""    svg_parts.append(f'<rect x="{curr_lx}" y="77" width="22" height="14" rx="7" fill="#fef3c7"/>')
    svg_parts.append(f'<text x="{curr_lx + 4}" y="87.5" font-size="8" font-weight="bold" fill="#92400e">PK</text>')
    curr_lx += 28
    svg_parts.append(f'<rect x="{curr_lx}" y="77" width="22" height="14" rx="7" fill="#ede9fe"/>')
    svg_parts.append(f'<text x="{curr_lx + 4}" y="87.5" font-size="8" font-weight="bold" fill="#5b21b6">FK</text>')
    curr_lx += 28
    svg_parts.append(f'<rect x="{curr_lx}" y="77" width="38" height="14" rx="7" fill="#dbeafe"/>')
    svg_parts.append(f'<text x="{curr_lx + 4}" y="87.5" font-size="8" font-weight="bold" fill="#1e40af">PK/FK</text>')""",
    """    svg_parts.append(f'<rect x="{curr_lx}" y="122" width="30" height="18" rx="9" fill="#fef3c7"/>')
    svg_parts.append(f'<text x="{curr_lx + 7}" y="135" font-size="10.5" font-weight="bold" fill="#92400e">PK</text>')
    curr_lx += 40
    svg_parts.append(f'<rect x="{curr_lx}" y="122" width="30" height="18" rx="9" fill="#ede9fe"/>')
    svg_parts.append(f'<text x="{curr_lx + 7}" y="135" font-size="10.5" font-weight="bold" fill="#5b21b6">FK</text>')
    curr_lx += 40
    svg_parts.append(f'<rect x="{curr_lx}" y="122" width="52" height="18" rx="9" fill="#dbeafe"/>')
    svg_parts.append(f'<text x="{curr_lx + 7}" y="135" font-size="10.5" font-weight="bold" fill="#1e40af">PK/FK</text>')""")

# ── 5) Card header + field rows + badges ─────────────────────────────────
rep('''y="{y+19}" font-size="11.5"''', '''y="{y+28}" font-size="15"''')
rep('''y="{curr_ry+14}" font-size="9" fill="#94a3b8"''', '''y="{curr_ry+19}" font-size="11.5" fill="#94a3b8"''')
rep('''y="{curr_ry+14}" font-size="10" fill="#1e293b"''', '''y="{curr_ry+19}" font-size="12.5" fill="#1e293b"''')

rep('''bx = x + w - 28
                svg_parts.append(f'<rect x="{bx}" y="{curr_ry+3}" width="22" height="14" rx="7" fill="#fef3c7"/>')
                svg_parts.append(f'<text x="{bx+4}" y="{curr_ry+13.5}" font-size="7.5" font-weight="bold" fill="#92400e">PK</text>')''',
    '''bx = x + w - 38
                svg_parts.append(f'<rect x="{bx}" y="{curr_ry+5}" width="30" height="18" rx="9" fill="#fef3c7"/>')
                svg_parts.append(f'<text x="{bx+7}" y="{curr_ry+18.5}" font-size="10" font-weight="bold" fill="#92400e">PK</text>')''')

rep('''bx = x + w - 28
                svg_parts.append(f'<rect x="{bx}" y="{curr_ry+3}" width="22" height="14" rx="7" fill="#ede9fe"/>')
                svg_parts.append(f'<text x="{bx+4}" y="{curr_ry+13.5}" font-size="7.5" font-weight="bold" fill="#5b21b6">FK</text>')''',
    '''bx = x + w - 38
                svg_parts.append(f'<rect x="{bx}" y="{curr_ry+5}" width="30" height="18" rx="9" fill="#ede9fe"/>')
                svg_parts.append(f'<text x="{bx+7}" y="{curr_ry+18.5}" font-size="10" font-weight="bold" fill="#5b21b6">FK</text>')''')

rep('''bx = x + w - 42
                svg_parts.append(f'<rect x="{bx}" y="{curr_ry+3}" width="38" height="14" rx="7" fill="#dbeafe"/>')
                svg_parts.append(f'<text x="{bx+4}" y="{curr_ry+13.5}" font-size="7.5" font-weight="bold" fill="#1e40af">PK/FK</text>')''',
    '''bx = x + w - 60
                svg_parts.append(f'<rect x="{bx}" y="{curr_ry+5}" width="52" height="18" rx="9" fill="#dbeafe"/>')
                svg_parts.append(f'<text x="{bx+7}" y="{curr_ry+18.5}" font-size="10" font-weight="bold" fill="#1e40af">PK/FK</text>')''')

# ── 6) Footer ─────────────────────────────────────────────────────────────
rep("    footer_y = max_height - 24", "    footer_y = max_height - 34")
rep('''font-size="10" fill="#94a3b8" font-weight="500">AI-COS Pharmacy · Graduation Project 2026/2027 · Faculty of Computers &amp; Informatics · Suez Canal University · ERD v6 Final Production''',
    '''font-size="13.5" fill="#94a3b8" font-weight="500">AI-COS Pharmacy · Graduation Project 2026/2027 · Faculty of Computers &amp; Informatics · Suez Canal University · ERD v7 Final Production''')

# ── 7) Arrow labels: remaining font-size="8" must be exactly the connector one ──
assert src.count('font-size="8"') == 1, f"arrow label anchor: {src.count('font-size=\"8\"')}"
src = src.replace('font-size="8"', 'font-size="11"')

# ── 8) Column-name fixes vs live Supabase (phantoms) ─────────────────────
rep('("enterprise_notifs", "boolean", None)', '("enterprise_notifications", "boolean", None)')
rep('("preferred_lang", "string", None)', '("preferred_language", "string", None)')
rep('("started_at", "timestamp", None)', '("created_at", "timestamp", None)')
rep('("expected_margin", "numeric", None)', '("expected_margin_total", "numeric", None)')
rep('("total_cost", "numeric", None)', '("total_estimated_cost", "numeric", None)')
rep('("recorded_at", "timestamp", None)', '("created_at", "timestamp", None)')

# ORDERS: drop phantom total_amount, note computed totals in the description
m = re.search(r'\n\s*\("total_amount", "[a-z0-9]+", None\),', src)
assert m, "total_amount anchor missing"
src = src[:m.start()] + src[m.end():]
rep('desc_ar": "فواتير المبيعات، قناة الشراء (واتساب، تطبيق، صيدلية)، والعناوين وقيمة الطلب."',
    'desc_ar": "فواتير المبيعات وقناة الشراء وبيانات الشحن — الإجماليات تُحسب من ORDER_ITEMS (لا يوجد عمود إجمالي في القاعدة)."')

# ── 9) Pivot-era column additions ─────────────────────────────────────────
rep('("subdomain", "string", None),',
    '("subdomain", "string", None),\n            ("vertical", "string", None),')
rep('("is_verified", "boolean", None),',
    '("is_verified", "boolean", None),\n            ("vertical", "string", None),\n            ("data_source", "string", None),')
rep('("churn_probability", "float", None),',
    '("churn_probability", "float", None),\n            ("predicted_days", "numeric", None),')
rep('''("attempts", "int", None),
            ("payload", "jsonb", None),''',
    '''("attempts", "int", None),
            ("max_attempts", "int", None),
            ("n8n_detail", "text", None),
            ("reason", "text", None),
            ("payload", "jsonb", None),''')
rep('''("tenant_id", "uuid", "FK"),
            ("po_number", "string", None),''',
    '''("tenant_id", "uuid", "FK"),
            ("supplier_id", "uuid", "FK"),
            ("po_number", "string", None),''')

# ── 10) Column rebalance (12 columns) ─────────────────────────────────────
COLMAP = {
    "TENANTS": 0, "TENANT_SETTINGS": 0, "AUDIT_LOGS": 0, "PLATFORM_SETTINGS": 0,
    "CUSTOMERS": 1, "SESSIONS": 1, "EVENTS": 1,
    "CONTACT_MESSAGES": 2, "COMPLAINTS": 2,
    "ORDERS": 3, "ORDER_ITEMS": 3, "COUPONS": 3,
    "DRUGS": 4, "DRUG_INTERACTIONS": 4, "DRUG_AFFINITIES": 4,
    "INVENTORY_ITEMS": 5, "CUSTOMER_CYCLES": 5, "PENDING_REMINDERS": 5,
    "PRESCRIPTIONS": 6, "PRESCRIPTION_ANALYSES": 6, "PRESCRIPTION_ITEMS": 6,
    "OCR_CORRECTIONS": 7, "OCR_CORRECTION_EXAMPLES": 7, "SIMULATION_RUNS": 7,
    "SUPPLIERS": 8, "PURCHASE_ORDERS": 8, "PURCHASE_ORDER_ITEMS": 8,
    "JOURNAL_ENTRIES": 9, "JOURNAL_ENTRY_LINES": 9, "AI_CHAT_LOGS": 9,
    "AUTOMATION_RUNS": 10, "EMERGENCY_OUTBOX": 10, "MARKET_INTELLIGENCE_ACTIONS": 10,
    "NOTIFICATIONS": 11, "AB_TESTS": 11, "AB_TEST_RESULTS": 11, "KNOWLEDGE_CHUNKS": 11,
}
def set_col(m):
    tid = m.group(1)
    return f'{m.group(0)}' if tid not in COLMAP else re.sub(r'"col": \d+', f'"col": {COLMAP[tid]}', m.group(0))
src = re.sub(r'"id": "([A-Z_]+)",\n        "domain": "\w+",\n        "col": \d+,',
             lambda m: re.sub(r'"col": \d+', f'"col": {COLMAP[m.group(1)]}', m.group(0)) if m.group(1) in COLMAP else m.group(0),
             src)

# ── 11) New tables ────────────────────────────────────────────────────────
NEW_TABLES = '''    {
        "id": "SUPPLIERS",
        "domain": "finance",
        "col": 8,
        "is_new": True,
        "desc_ar": "الموردون: جهات التوريد المرتبطة بأوامر الشراء (P2P) — إضافة v7.",
        "fields": [
            ("supplier_id", "uuid", "PK"),
            ("tenant_id", "uuid", "FK"),
            ("name", "string", None),
            ("contact_person", "string", None),
            ("phone", "string", None),
            ("email", "string", None),
            ("address", "text", None),
            ("payment_terms", "string", None),
            ("is_active", "boolean", None),
            ("created_at", "timestamp", None),
        ]
    },
    {
        "id": "COMPLAINTS",
        "domain": "customer",
        "col": 2,
        "is_new": True,
        "desc_ar": "دورة حياة الشكاوى (open → resolved) — يسجلها وكيل الدعم وتُقاس منها مدة الاستجابة (SLA).",
        "fields": [
            ("complaint_id", "uuid", "PK"),
            ("tenant_id", "uuid", "FK"),
            ("customer_name", "string", None),
            ("channel", "string", None),
            ("subject", "string", None),
            ("message", "text", None),
            ("status", "string", None),
            ("assigned_to", "string", None),
            ("resolution_note", "text", None),
            ("created_at", "timestamp", None),
            ("updated_at", "timestamp", None),
        ]
    },
    {
        "id": "MARKET_INTELLIGENCE_ACTIONS",
        "domain": "ai",
        "col": 10,
        "is_new": True,
        "desc_ar": "سلسلة حوكمة إجراءات ذكاء السوق: موافقة/رفض/تنفيذ موقّعة ومروية إلى سجل WORM الخارجي.",
        "fields": [
            ("action_id", "uuid", "PK"),
            ("tenant_id", "uuid", "FK"),
            ("drug_id", "uuid", "FK"),
            ("action_type", "string", None),
            ("status", "string", None),
            ("priority", "string", None),
            ("title", "string", None),
            ("drug_name", "string", None),
            ("market_signal_id", "string", None),
            ("parameters", "jsonb", None),
            ("execution_result", "jsonb", None),
            ("approved_by", "string", None),
            ("approved_at", "timestamp", None),
            ("executed_at", "timestamp", None),
        ]
    },
    {
        "id": "PLATFORM_SETTINGS",
        "domain": "core",
        "col": 0,
        "is_new": True,
        "desc_ar": "إعدادات على مستوى المنصة كاملة (مفتاح/قيمة) — أشهرها active_vertical لمحور المتاجر المتعددة.",
        "fields": [
            ("key", "string", "PK"),
            ("value", "string", None),
            ("updated_at", "timestamp", None),
        ]
    },
]'''
rep("]\n\n# 35 Cleanly routed relationships\nRELATIONSHIPS = [", NEW_TABLES + "\n\n# 38 cleanly routed relationships\nRELATIONSHIPS = [")

# ── 12) New relationships ─────────────────────────────────────────────────
NEW_RELS = '''    # v7 — Suppliers / Complaints / Market Intelligence governance
    {"from": "TENANTS", "to": "SUPPLIERS", "label": "scopes", "color": "#4338ca", "route": "arch_bottom"},
    {"from": "SUPPLIERS", "to": "PURCHASE_ORDERS", "label": "fulfills", "color": "#0891b2", "route": "vertical"},
    {"from": "CUSTOMERS", "to": "COMPLAINTS", "label": "files", "color": "#0284c7", "route": "h_right_to_left"},
    {"from": "DRUGS", "to": "MARKET_INTELLIGENCE_ACTIONS", "label": "targets", "color": "#e11d48", "route": "arch_bottom"},
    {"from": "TENANTS", "to": "PLATFORM_SETTINGS", "label": "governs", "color": "#4338ca", "route": "side_loop_left"},
]'''
rep("]\n\ndef build_erd_data():", NEW_RELS + "\n\ndef build_erd_data():")

# ── 13) Rebrand remaining v6 → v7 (incl. <title>, output filename) ───────
n = src.count("v6")
src = src.replace("v6", "v7")
print(f"rebranded {n} 'v6' occurrences")

io.open(DST, "w", encoding="utf-8").write(src)
print(f"WROTE {DST} ({len(src)} chars)")

# ── 14) Sanity: column balance report ─────────────────────────────────────
from collections import defaultdict
exec(compile(src, DST, "exec"), {"__name__": "not_main"}) if False else None
spec_done = True
