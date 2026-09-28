# -*- coding: utf-8 -*-
"""Build pharmacy_erd_v7_improved.html ("تحسين 7") from Music/pharmacy_erd_v6_improved.html:
same tabbed-mermaid system, upgraded to v7 (37 tables): +SUPPLIERS/COMPLAINTS/
MARKET_INTELLIGENCE_ACTIONS/PLATFORM_SETTINGS, fix orders.total_amount phantom,
add vertical-pivot columns, retitle "تحسين 7".
"""
import io, re, shutil

SRC = r"C:\Users\zbook\Music\pharmacy_erd_v6_improved.html"
DST = r"D:\Graduation Project\pharmacy_erd_v7_improved.html"
MUS = r"C:\Users\zbook\Music\pharmacy_erd_v7_improved.html"

src = io.open(SRC, encoding="utf-8").read()

def rep(old, new, count=1):
    global src
    found = src.count(old)
    assert found == count, f"ANCHOR FAIL ({found}/{count}): {old[:100]!r}"
    src = src.replace(old, new)

# ── 1) Branding: تحسين 7 ─────────────────────────────────────────────────
rep("<title>AI-COS Pharmacy — ERD v6 (2026/2027)</title>",
    "<title>AI-COS Pharmacy — ERD تحسين 7 (2026/2027)</title>")
rep('<span class="badge">v6 — 2026/2027</span>',
    '<span class="badge">تحسين 7 — 2026/2027</span>')
rep("AI-COS Pharmacy Platform — <span>ERD v6</span> —",
    "AI-COS Pharmacy Platform — <span>ERD تحسين 7</span> —")

# ── 2) Tab counts ────────────────────────────────────────────────────────
rep('Core <span class="tab-count">19</span>', 'Core <span class="tab-count">20</span>')
rep('Finance / Procurement <span class="tab-count">5</span>', 'Finance / Procurement <span class="tab-count">6</span>')
rep('AI / Analytics <span class="tab-count">3</span>', 'AI / Analytics <span class="tab-count">4</span>')
rep('Operational / Support <span class="tab-count">1</span>', 'Operational / Support <span class="tab-count">2</span>')

# ── 3) ENTITY_CATEGORY (+4) ──────────────────────────────────────────────
rep("  AI_CHAT_LOGS: 'ai', AUTOMATION_RUNS: 'ai', COUPONS: 'ai',\n  EMERGENCY_OUTBOX: 'ops',\n};",
    "  AI_CHAT_LOGS: 'ai', AUTOMATION_RUNS: 'ai', COUPONS: 'ai',\n  MARKET_INTELLIGENCE_ACTIONS: 'ai',\n  SUPPLIERS: 'fin',\n  COMPLAINTS: 'ops',\n  PLATFORM_SETTINGS: 'core',\n};")

# ── 4) overview FIRST: +5 rels + TENANTS with vertical (unique anchor) ───
rep("""  TENANTS ||--o{ COUPONS : "issues"

  TENANTS { uuid tenant_id PK
    varchar name
    varchar subdomain
    boolean is_active
    timestamp created_at }""",
    """  TENANTS ||--o{ COUPONS : "issues"
  TENANTS ||--o{ SUPPLIERS : "scopes"
  SUPPLIERS ||--o{ PURCHASE_ORDERS : "fulfills"
  TENANTS ||--o{ MARKET_INTELLIGENCE_ACTIONS : "scopes"
  DRUGS ||--o{ MARKET_INTELLIGENCE_ACTIONS : "targets"
  TENANTS ||--o{ COMPLAINTS : "scopes"

  TENANTS { uuid tenant_id PK
    varchar name
    varchar subdomain
    varchar vertical
    boolean is_active
    timestamp created_at }""")

# ── 5) core TENANTS: add vertical (now the only remaining 6-line block) ──
rep("""  TENANTS { uuid tenant_id PK
    varchar name
    varchar subdomain
    boolean is_active
    timestamp created_at }""",
    """  TENANTS { uuid tenant_id PK
    varchar name
    varchar subdomain
    varchar vertical
    boolean is_active
    timestamp created_at }""")

# ── 6) ORDERS phantom fix (core + overview, identical blocks) ────────────
rep("""    varchar status
    numeric total_amount
    varchar shipping_phone""",
    """    varchar status
    varchar shipping_name
    varchar shipping_phone""", 2)

# ── 7) core: PLATFORM_SETTINGS after CONTACT_MESSAGES (ends the tab) ─────
rep("""  CONTACT_MESSAGES { uuid id PK
    uuid tenant_id FK
    uuid customer_id
    varchar first_name
    varchar last_name
    varchar email
    varchar message
    timestamp created_at }
`,""",
    """  CONTACT_MESSAGES { uuid id PK
    uuid tenant_id FK
    uuid customer_id
    varchar first_name
    varchar last_name
    varchar email
    varchar message
    timestamp created_at }
  PLATFORM_SETTINGS { varchar key PK
    varchar value
    timestamp updated_at }
`,""")

# ── 8) overview entity blocks (CONTACT_MESSAGES followed by PRESCRIPTIONS) ──
rep("""    varchar message
    timestamp created_at }
  PRESCRIPTIONS { uuid id PK""",
    """    varchar message
    timestamp created_at }
  PLATFORM_SETTINGS { varchar key PK
    varchar value
    timestamp updated_at }
  SUPPLIERS { uuid supplier_id PK
    uuid tenant_id FK
    varchar name
    varchar contact_person
    varchar phone
    varchar email
    text address
    varchar payment_terms
    boolean is_active
    timestamp created_at }
  COMPLAINTS { uuid complaint_id PK
    uuid tenant_id FK
    varchar customer_name
    varchar channel
    varchar subject
    text message
    varchar status
    varchar assigned_to
    text resolution_note
    timestamp created_at
    timestamp updated_at }
  MARKET_INTELLIGENCE_ACTIONS { uuid action_id PK
    uuid tenant_id FK
    uuid drug_id FK
    varchar action_type
    varchar status
    varchar priority
    varchar title
    varchar drug_name
    varchar market_signal_id
    jsonb parameters
    jsonb execution_result
    varchar approved_by
    timestamp approved_at
    timestamp executed_at }
  PRESCRIPTIONS { uuid id PK""")

# ── 9) fin: SUPPLIERS rels + entity (before fin's PURCHASE_ORDERS) ───────
rep("""  DRUGS ||--o{ SIMULATION_RUNS : "simulated_for"

  TENANTS { uuid tenant_id PK
    varchar name }""",
    """  DRUGS ||--o{ SIMULATION_RUNS : "simulated_for"
  TENANTS ||--o{ SUPPLIERS : "scopes"
  SUPPLIERS ||--o{ PURCHASE_ORDERS : "fulfills"

  TENANTS { uuid tenant_id PK
    varchar name }
  SUPPLIERS { uuid supplier_id PK
    uuid tenant_id FK
    varchar name
    varchar contact_person
    varchar phone
    varchar email
    text address
    varchar payment_terms
    boolean is_active
    timestamp created_at }""")

# ── 10) PURCHASE_ORDERS +supplier_id FK (fin + overview, identical) ──────
rep("""  PURCHASE_ORDERS { uuid po_id PK
    uuid tenant_id FK
    varchar po_number""",
    """  PURCHASE_ORDERS { uuid po_id PK
    uuid tenant_id FK
    uuid supplier_id FK
    varchar po_number""", 2)

# ── 11) ai: MI_ACTIONS rels (anchor: COUPONS rel + 2-line TENANTS stub) ──
rep("""  TENANTS ||--o{ COUPONS : "issues"

  TENANTS { uuid tenant_id PK
    varchar name }""",
    """  TENANTS ||--o{ COUPONS : "issues"
  TENANTS ||--o{ MARKET_INTELLIGENCE_ACTIONS : "scopes"
  DRUGS ||--o{ MARKET_INTELLIGENCE_ACTIONS : "targets"

  TENANTS { uuid tenant_id PK
    varchar name }
  DRUGS { uuid drug_id PK
    varchar name }""")

# ── 12) ai: MI_ACTIONS entity after COUPONS block (ends the tab) ─────────
rep("""    timestamp expires_at
    timestamp used_at }
`,""",
    """    timestamp expires_at
    timestamp used_at }
  MARKET_INTELLIGENCE_ACTIONS { uuid action_id PK
    uuid tenant_id FK
    uuid drug_id FK
    varchar action_type
    varchar status
    varchar priority
    varchar title
    varchar drug_name
    varchar market_signal_id
    jsonb parameters
    jsonb execution_result
    varchar approved_by
    timestamp approved_at
    timestamp executed_at }
`,""")

# ── 13) ops: COMPLAINTS ──────────────────────────────────────────────────
rep("""  ops: `erDiagram
  EMERGENCY_OUTBOX { int id PK""",
    """  ops: `erDiagram
  TENANTS ||--o{ COMPLAINTS : "scopes"

  TENANTS { uuid tenant_id PK
    varchar name }
  COMPLAINTS { uuid complaint_id PK
    uuid tenant_id FK
    varchar customer_name
    varchar channel
    varchar subject
    text message
    varchar status
    varchar assigned_to
    text resolution_note
    timestamp created_at
    timestamp updated_at }
  EMERGENCY_OUTBOX { int id PK""")

# ── 14) DRUGS vertical (core + overview, identical) ──────────────────────
rep("""    varchar warnings
    varchar data_source
    boolean is_verified }""",
    """    varchar warnings
    varchar data_source
    varchar vertical
    boolean is_verified }""", 2)

# ── 15) Stats bar (honest v7 numbers, computed post-insert) ──────────────
cols_total = len(re.findall(r"^    (?:uuid|varchar|text|boolean|timestamp|numeric|int|float|date|jsonb|vector|inet|bigint|array)\b", src, re.M))
rels_total = len(re.findall(r"^\s+\w+ \}o--\|\| \w+|^\s+\w+ \|\|--o\{ \w+|^\s+\w+ \|\|--\|\| \w+", src, re.M))
rep('<div class="stat-card"><div class="stat-num">+200</div><div class="stat-label">أعمدة إجمالية</div></div>',
    f'<div class="stat-card"><div class="stat-num">{cols_total}</div><div class="stat-label">أعمدة إجمالية</div></div>')
rep('<div class="stat-card"><div class="stat-num">+35</div><div class="stat-label">علاقات (Foreign Keys)</div></div>',
    f'<div class="stat-card"><div class="stat-num">{rels_total}</div><div class="stat-label">علاقات (Foreign Keys)</div></div>')
rep('<div class="stat-card"><div class="stat-num">19</div><div class="stat-label">جداول جديدة منذ v5</div></div>',
    '<div class="stat-card"><div class="stat-num">+4</div><div class="stat-label">جداول جديدة في تحسين 7</div></div>')
rep('<div class="stat-card"><div class="stat-num">33</div><div class="stat-label">إجمالي الجداول</div></div>',
    '<div class="stat-card"><div class="stat-num">37</div><div class="stat-label">إجمالي الجداول</div></div>')

# ── 16) Pane descriptions (stale v6 wording) ─────────────────────────────
rep('pane-desc">أوامر الشراء والموردين، القيود المحاسبية، ومحاكاة السيناريوهات التسعيرية.',
    'pane-desc">أوامر الشراء والموردين (إضافة تحسين 7) وسلسلة التوريد، القيود المحاسبية، ومحاكاة السيناريوهات التسعيرية.')
rep('pane-desc">سجلات محادثات الذكاء الاصطناعي، تشغيلات الأتمتة (n8n)، وكوبونات الخصم.',
    'pane-desc">سجلات محادثات الذكاء الاصطناعي، تشغيلات الأتمتة (n8n)، وكوبونات الخصم، وسلسلة حوكمة إجراءات ذكاء السوق (موافقة/رفض/تنفيذ).')
rep('pane-desc">جدول واحد فقط في هذه الفئة حاليًا: صندوق الرسائل الطارئة غير المرسلة (لا توجد علاقة صريحة مُعرَّفة له في v6).',
    'pane-desc">جدولان: صندوق الرسائل الطارئة غير المرسلة + دورة حياة الشكاوى (open → resolved) بقياس مدة الاستجابة — إضافة تحسين 7.')
rep('pane-desc">كل الـ33 جدول في مخطط واحد',
    'pane-desc">كل الـ37 جدول في مخطط واحد')

io.open(DST, "w", encoding="utf-8").write(src)
shutil.copyfile(DST, MUS)
print(f"WROTE {DST}\nCOPIED {MUS}")
print(f"attribute-lines={cols_total} relationship-lines={rels_total} size={len(src)}")
