import os
import re
import json

DOMAIN_META = {
    "core": {
        "title": "Multi-Tenant & Core",
        "title_ar": "المستأجرون والنواة الإدارية",
        "color": "#4338ca",      # Deep Indigo
        "border": "#4338ca",
        "bg_soft": "#eef2ff",
        "badge_bg": "#ede9fe",
        "badge_text": "#4338ca"
    },
    "customer": {
        "title": "Customer & Sessions",
        "title_ar": "العملاء والجلسات وسجل النشاط",
        "color": "#0284c7",      # Sky Blue
        "border": "#0284c7",
        "bg_soft": "#f0f9ff",
        "badge_bg": "#e0f2fe",
        "badge_text": "#0369a1"
    },
    "orders": {
        "title": "Orders & Commerce",
        "title_ar": "المبيعات والطلبات وكوبونات الخصم",
        "color": "#059669",      # Emerald Green
        "border": "#059669",
        "bg_soft": "#ecfdf5",
        "badge_bg": "#d1fae5",
        "badge_text": "#065f46"
    },
    "drugs": {
        "title": "Drug Catalog & Safety",
        "title_ar": "كتالوج الأدوية والتفاعلات الدوائية",
        "color": "#d97706",      # Warm Amber
        "border": "#d97706",
        "bg_soft": "#fffbeb",
        "badge_bg": "#fef3c7",
        "badge_text": "#92400e"
    },
    "inventory": {
        "title": "Inventory & Cycles",
        "title_ar": "المخزون ودورات استهلاك المرضى",
        "color": "#0d9488",      # Teal
        "border": "#0d9488",
        "bg_soft": "#f0fdfa",
        "badge_bg": "#ccfbf1",
        "badge_text": "#115e59"
    },
    "ocr": {
        "title": "Prescriptions & OCR [NEW]",
        "title_ar": "الروشتات ومحرك OCR وحلقة التعلم",
        "color": "#7c3aed",      # Purple / Violet
        "border": "#7c3aed",
        "bg_soft": "#faf5ff",
        "badge_bg": "#ede9fe",
        "badge_text": "#6d28d9"
    },
    "finance": {
        "title": "Procurement & Accounting [NEW]",
        "title_ar": "المشتريات والمحاسبة ومحاكاة التسعير",
        "color": "#0891b2",      # Ocean Cyan
        "border": "#0891b2",
        "bg_soft": "#ecfeff",
        "badge_bg": "#cffafe",
        "badge_text": "#155e75"
    },
    "ai": {
        "title": "AI Agents & Automations [NEW]",
        "title_ar": "وكلاء الذكاء الاصطناعي والأتمتة",
        "color": "#e11d48",      # Rose / Crimson
        "border": "#e11d48",
        "bg_soft": "#fff1f2",
        "badge_bg": "#ffe4e6",
        "badge_text": "#9f1239"
    },
    "analytics": {
        "title": "Analytics, Testing & RAG",
        "title_ar": "التحليلات واختبارات A/B وقاعدة المعرفة",
        "color": "#475569",      # Slate / Steel
        "border": "#475569",
        "bg_soft": "#f8fafc",
        "badge_bg": "#f1f5f9",
        "badge_text": "#334155"
    }
}

TABLES = [
    # Column 0: Multi-Tenant & Core
    {
        "id": "TENANTS",
        "domain": "core",
        "col": 0,
        "is_new": False,
        "desc_ar": "سجل الصيدليات المشتركة بنظام Multi-Tenancy مع عزل كامل للبيانات والإعدادات.",
        "fields": [
            ("tenant_id", "uuid", "PK"),
            ("name", "string", None),
            ("subdomain", "string", None),
            ("is_active", "boolean", None),
            ("created_at", "timestamp", None),
        ]
    },
    {
        "id": "TENANT_SETTINGS",
        "domain": "core",
        "col": 0,
        "is_new": True,
        "desc_ar": "تفضيلات الصيدلية: نمط المراجعة بالذكاء الاصطناعي، قنوات التنبيه، والاتصال السحابي.",
        "fields": [
            ("id", "uuid", "PK"),
            ("tenant_id", "uuid", "FK"),
            ("ai_review_mode", "boolean", None),
            ("enterprise_notifs", "boolean", None),
            ("cloud_ocr_allowed", "boolean", None),
            ("created_at", "timestamp", None),
            ("updated_at", "timestamp", None),
        ]
    },
    {
        "id": "AUDIT_LOGS",
        "domain": "core",
        "col": 0,
        "is_new": False,
        "desc_ar": "سجل الرقابة والأمان وتدقيق العمليات الحساسة والامتثال الطبي.",
        "fields": [
            ("log_id", "uuid", "PK"),
            ("tenant_id", "uuid", "FK"),
            ("actor_id", "string", None),
            ("action_type", "string", None),
            ("target_entity", "string", None),
            ("timestamp", "timestamp", None),
        ]
    },

    # Column 1: Customer & Identity
    {
        "id": "CUSTOMERS",
        "domain": "customer",
        "col": 1,
        "is_new": False,
        "desc_ar": "بيانات المرضى والعملاء، الهوية الرقمية، قنوات التواصل المفضلة، والفئات العمرية.",
        "fields": [
            ("customer_id", "uuid", "PK"),
            ("auth_user_id", "uuid", None),
            ("tenant_id", "uuid", "FK"),
            ("email", "string", None),
            ("full_name", "string", None),
            ("phone", "string", None),
            ("age_group", "string", None),
            ("preferred_channel", "string", None),
            ("preferred_lang", "string", None),
            ("role", "string", None),
            ("is_active", "boolean", None),
            ("created_at", "timestamp", None),
        ]
    },
    {
        "id": "SESSIONS",
        "domain": "customer",
        "col": 1,
        "is_new": False,
        "desc_ar": "تتبع جلسات العملاء وأجهزتهم على التطبيق والويب.",
        "fields": [
            ("session_id", "uuid", "PK"),
            ("tenant_id", "uuid", "FK"),
            ("customer_id", "uuid", "FK"),
            ("device_info", "string", None),
            ("started_at", "timestamp", None),
        ]
    },
    {
        "id": "EVENTS",
        "domain": "customer",
        "col": 1,
        "is_new": False,
        "desc_ar": "تسجيل سلوك وتفاعلات العميل لحظياً مع التشفير التسلسلي لمنع التلاعب.",
        "fields": [
            ("event_id", "uuid", "PK"),
            ("session_id", "uuid", "FK"),
            ("event_type", "string", None),
            ("payload", "jsonb", None),
            ("timestamp", "timestamp", None),
            ("prev_hash", "string", None),
            ("actor_id", "uuid", None),
            ("event_seq", "bigint", None),
        ]
    },
    {
        "id": "CONTACT_MESSAGES",
        "domain": "customer",
        "col": 1,
        "is_new": True,
        "desc_ar": "رسائل الدعم الفني واستفسارات العملاء الموجهة لإدارة الصيدلية.",
        "fields": [
            ("id", "uuid", "PK"),
            ("tenant_id", "uuid", "FK"),
            ("customer_id", "uuid", "FK"),
            ("first_name", "string", None),
            ("email", "string", None),
            ("message", "string", None),
            ("created_at", "timestamp", None),
        ]
    },

    # Column 2: Orders & Commerce
    {
        "id": "ORDERS",
        "domain": "orders",
        "col": 2,
        "is_new": False,
        "desc_ar": "فواتير المبيعات، قناة الشراء (واتساب، تطبيق، صيدلية)، والعناوين وقيمة الطلب.",
        "fields": [
            ("order_id", "uuid", "PK"),
            ("tenant_id", "uuid", "FK"),
            ("customer_id", "uuid", "FK"),
            ("status", "string", None),
            ("channel", "string", None),
            ("total_amount", "numeric", None),
            ("payment_method", "string", None),
            ("shipping_address", "text", None),
            ("order_date", "timestamp", None),
        ]
    },
    {
        "id": "ORDER_ITEMS",
        "domain": "orders",
        "col": 2,
        "is_new": False,
        "desc_ar": "بنود الفاتورة: تفاصيل الأدوية المباعة والكميات وأسعار البيع الفعلية.",
        "fields": [
            ("order_item_id", "uuid", "PK"),
            ("order_id", "uuid", "FK"),
            ("drug_id", "uuid", "FK"),
            ("quantity", "int", None),
            ("price", "numeric", None),
        ]
    },
    {
        "id": "COUPONS",
        "domain": "orders",
        "col": 2,
        "is_new": True,
        "desc_ar": "أكواد الخصم والحملات الموجهة للمرضى المستهدفين للحد من التسرب.",
        "fields": [
            ("id", "uuid", "PK"),
            ("tenant_id", "uuid", "FK"),
            ("code", "string", None),
            ("discount_pct", "int", None),
            ("campaign_type", "string", None),
            ("drug_name", "string", None),
            ("channel", "string", None),
            ("used_order_id", "uuid", "FK"),
            ("expires_at", "timestamp", None),
        ]
    },

    # Column 3: Drug Catalog & Clinical
    {
        "id": "DRUGS",
        "domain": "drugs",
        "col": 3,
        "is_new": False,
        "desc_ar": "الكتالوج الطبي المركزي: المادة الفعالة، السعر، الجرعات، وتصنيف الأمراض المزمنة.",
        "fields": [
            ("drug_id", "uuid", "PK"),
            ("name", "string", None),
            ("category", "string", None),
            ("is_chronic", "boolean", None),
            ("base_price", "numeric", None),
            ("default_cycle_days", "int", None),
            ("active_ingredient", "string", None),
            ("dosage", "string", None),
            ("warnings", "string", None),
            ("is_verified", "boolean", None),
        ]
    },
    {
        "id": "DRUG_INTERACTIONS",
        "domain": "drugs",
        "col": 3,
        "is_new": False,
        "desc_ar": "قاعدة بيانات التعارضات الدوائية الخطرة (DDI) والتنبيه التلقائي للصيدلي.",
        "fields": [
            ("interaction_id", "uuid", "PK"),
            ("drug_id_a", "uuid", "FK"),
            ("drug_id_b", "uuid", "FK"),
            ("severity", "string", None),
            ("note", "string", None),
        ]
    },
    {
        "id": "DRUG_AFFINITIES",
        "domain": "drugs",
        "col": 3,
        "is_new": False,
        "desc_ar": "الارتباطات الدوائية التكميلية (Cross-selling الذكي مثل فيتامينات مع المضادات).",
        "fields": [
            ("affinity_id", "uuid", "PK"),
            ("drug_id_a", "uuid", "FK"),
            ("drug_id_b", "uuid", "FK"),
            ("affinity_type", "string", None),
            ("confidence_score", "float", None),
        ]
    },

    # Column 4: Inventory & Patient Cycles
    {
        "id": "INVENTORY_ITEMS",
        "domain": "inventory",
        "col": 4,
        "is_new": False,
        "desc_ar": "إدارة الأرصدة اللحظية، حد إعادة الطلب، وتكلفة المخزون لكل صيدلية.",
        "fields": [
            ("inventory_id", "uuid", "PK"),
            ("tenant_id", "uuid", "FK"),
            ("drug_id", "uuid", "FK"),
            ("stock_level", "int", None),
            ("reorder_point", "int", None),
            ("tenant_price", "numeric", None),
            ("is_active", "boolean", None),
        ]
    },
    {
        "id": "CUSTOMER_CYCLES",
        "domain": "inventory",
        "col": 4,
        "is_new": False,
        "desc_ar": "تتبع وتوقع دورة استهلاك أدوية الأمراض المزمنة لكل مريض بدقة إحصائية.",
        "fields": [
            ("customer_id", "uuid", "PK/FK"),
            ("drug_id", "uuid", "PK/FK"),
            ("avg_cycle_days", "float", None),
            ("last_purchase_date", "date", None),
            ("reminder_day", "date", None),
        ]
    },
    {
        "id": "PENDING_REMINDERS",
        "domain": "inventory",
        "col": 4,
        "is_new": False,
        "desc_ar": "جدولة إشعارات إعادة صرف الدواء عبر WhatsApp وSMS مع نسب الثقة التنبؤية.",
        "fields": [
            ("reminder_id", "uuid", "PK"),
            ("customer_id", "uuid", "FK"),
            ("drug_id", "uuid", "FK"),
            ("channel", "string", None),
            ("decision", "string", None),
            ("cycle_confidence", "float", None),
            ("churn_probability", "float", None),
            ("status", "string", None),
            ("created_at", "timestamp", None),
        ]
    },

    # Column 5: Prescriptions & OCR
    {
        "id": "PRESCRIPTIONS",
        "domain": "ocr",
        "col": 5,
        "is_new": True,
        "desc_ar": "صور الروشتات الأصلية المرفوعة وحالات المعالجة وبصمة SHA256 للتحقق.",
        "fields": [
            ("id", "uuid", "PK"),
            ("tenant_id", "uuid", "FK"),
            ("file_id", "string", None),
            ("uploaded_by", "uuid", "FK"),
            ("status", "string", None),
            ("file_sha256", "string", None),
            ("created_at", "timestamp", None),
        ]
    },
    {
        "id": "PRESCRIPTION_ANALYSES",
        "domain": "ocr",
        "col": 5,
        "is_new": True,
        "desc_ar": "نتائج فحص الروشتة عبر TrOCR / Vision ومقاييس زمن الاستجابة والتوكنز.",
        "fields": [
            ("id", "uuid", "PK"),
            ("prescription_id", "uuid", "FK"),
            ("provider", "string", None),
            ("model", "string", None),
            ("model_version", "string", None),
            ("latency_ms", "int", None),
            ("status", "string", None),
            ("created_at", "timestamp", None),
        ]
    },
    {
        "id": "PRESCRIPTION_ITEMS",
        "domain": "ocr",
        "col": 5,
        "is_new": True,
        "desc_ar": "بنود الروشتة المستخرجة: الدواء، الجرعة، الثقة، والمطابقة مع كتالوج الصيدلية.",
        "fields": [
            ("id", "uuid", "PK"),
            ("analysis_id", "uuid", "FK"),
            ("raw_name", "string", None),
            ("normalized_name", "string", None),
            ("strength", "string", None),
            ("dosage_form", "string", None),
            ("ocr_confidence", "float", None),
            ("match_status", "string", None),
            ("matched_drug_id", "uuid", "FK"),
            ("pharmacist_decision", "string", None),
            ("auto_corrected", "boolean", None),
        ]
    },

    # Column 6: OCR Learning Loop & Simulation
    {
        "id": "OCR_CORRECTIONS",
        "domain": "ocr",
        "col": 6,
        "is_new": True,
        "desc_ar": "سجل تصحيحات الصيادلة اليدوية لقراءات OCR لتحسين دقة النموذج باستمرار.",
        "fields": [
            ("id", "uuid", "PK"),
            ("tenant_id", "uuid", "FK"),
            ("wrong_reading_norm", "string", None),
            ("corrected_name", "string", None),
            ("source", "string", None),
            ("hit_count", "int", None),
            ("target_drug_id", "uuid", "FK"),
            ("confidence_score", "float", None),
            ("status", "string", None),
            ("updated_at", "timestamp", None),
        ]
    },
    {
        "id": "OCR_CORRECTION_EXAMPLES",
        "domain": "ocr",
        "col": 6,
        "is_new": True,
        "desc_ar": "قصاصات صور الكلمات والخطوط اليدوية الصعبة لتغذية تدريب نماذج TrOCR.",
        "fields": [
            ("id", "uuid", "PK"),
            ("correction_id", "uuid", "FK"),
            ("source_rx_id", "uuid", "FK"),
            ("crop_storage_key", "string", None),
            ("raw_ocr", "string", None),
            ("model_version", "string", None),
            ("created_at", "timestamp", None),
        ]
    },
    {
        "id": "SIMULATION_RUNS",
        "domain": "finance",
        "col": 6,
        "is_new": True,
        "desc_ar": "محاكاة مرونة الأسعار والخصومات وهوامش الربح المتوقعة قبل إطلاق الحملات.",
        "fields": [
            ("run_id", "uuid", "PK"),
            ("tenant_id", "uuid", "FK"),
            ("drug_id", "uuid", "FK"),
            ("scenario", "string", None),
            ("unit_price", "numeric", None),
            ("discount_pct", "numeric", None),
            ("volume_lift_pct", "numeric", None),
            ("verdict", "string", None),
            ("expected_margin", "numeric", None),
            ("deployed", "boolean", None),
        ]
    },

    # Column 7: Procurement & Financial Accounting
    {
        "id": "PURCHASE_ORDERS",
        "domain": "finance",
        "col": 7,
        "is_new": True,
        "desc_ar": "أوامر الشراء وإعادة توريد الأدوية والمستلزمات من الموزعين والشركات.",
        "fields": [
            ("po_id", "uuid", "PK"),
            ("tenant_id", "uuid", "FK"),
            ("po_number", "string", None),
            ("supplier_name", "string", None),
            ("status", "string", None),
            ("total_cost", "numeric", None),
            ("created_by", "string", None),
            ("created_at", "timestamp", None),
        ]
    },
    {
        "id": "PURCHASE_ORDER_ITEMS",
        "domain": "finance",
        "col": 7,
        "is_new": True,
        "desc_ar": "تفاصيل أصناف أمر التوريد: الكميات المطلوبة والمستلمة وأسعار الشراء بالجملة.",
        "fields": [
            ("item_id", "uuid", "PK"),
            ("po_id", "uuid", "FK"),
            ("drug_id", "uuid", "FK"),
            ("drug_name", "string", None),
            ("quantity_ordered", "int", None),
            ("quantity_received", "int", None),
            ("unit_cost", "numeric", None),
            ("subtotal", "numeric", None),
        ]
    },
    {
        "id": "JOURNAL_ENTRIES",
        "domain": "finance",
        "col": 7,
        "is_new": True,
        "desc_ar": "قيود اليومية المحاسبية التلقائية بنظام القيد المزدوج المتوازن.",
        "fields": [
            ("entry_id", "uuid", "PK"),
            ("tenant_id", "uuid", "FK"),
            ("entry_number", "string", None),
            ("entry_date", "timestamp", None),
            ("reference_type", "string", None),
            ("total_debit", "numeric", None),
            ("total_credit", "numeric", None),
            ("is_balanced", "boolean", None),
        ]
    },
    {
        "id": "JOURNAL_ENTRY_LINES",
        "domain": "finance",
        "col": 7,
        "is_new": True,
        "desc_ar": "سطور القيد المالي: حسابات المدين والدائن المتوازنة لكل عملية تجارية.",
        "fields": [
            ("line_id", "uuid", "PK"),
            ("entry_id", "uuid", "FK"),
            ("account_code", "string", None),
            ("account_name_ar", "string", None),
            ("account_type", "string", None),
            ("debit", "numeric", None),
            ("credit", "numeric", None),
        ]
    },

    # Column 8: AI Agents & Automations
    {
        "id": "AI_CHAT_LOGS",
        "domain": "ai",
        "col": 8,
        "is_new": True,
        "desc_ar": "سجل استفسارات العملاء للوكيل الصيدلي الذكي وتصنيف النوايا والتعارضات.",
        "fields": [
            ("log_id", "uuid", "PK"),
            ("tenant_id", "uuid", "FK"),
            ("session_id", "string", None),
            ("customer_id", "uuid", "FK"),
            ("user_prompt", "text", None),
            ("ai_response", "text", None),
            ("ddi_detected", "boolean", None),
            ("escalation_status", "string", None),
            ("response_time_ms", "int", None),
        ]
    },
    {
        "id": "AUTOMATION_RUNS",
        "domain": "ai",
        "col": 8,
        "is_new": True,
        "desc_ar": "مراقبة سير العمل المؤتمت في n8n وتتبع محاولات المعالجة التلقائية.",
        "fields": [
            ("id", "uuid", "PK"),
            ("workflow_name", "string", None),
            ("tenant_id", "uuid", "FK"),
            ("trigger_source", "string", None),
            ("status", "string", None),
            ("attempts", "int", None),
            ("payload", "jsonb", None),
            ("created_at", "timestamp", None),
        ]
    },
    {
        "id": "EMERGENCY_OUTBOX",
        "domain": "ai",
        "col": 8,
        "is_new": True,
        "desc_ar": "صندوق رسائل الطوارئ الاحتياطي لضمان وصول التنبيهات الحرجة دون فقد.",
        "fields": [
            ("id", "int", "PK"),
            ("tenant_id", "uuid", "FK"),
            ("payload", "jsonb", None),
            ("status", "string", None),
            ("attempts", "int", None),
            ("created_at", "timestamp", None),
        ]
    },

    # Column 9: Analytics, Testing & Knowledge RAG
    {
        "id": "NOTIFICATIONS",
        "domain": "analytics",
        "col": 9,
        "is_new": False,
        "desc_ar": "سجل الإشعارات المرسلة عبر WhatsApp وSMS وحالات التسليم والتفاعل.",
        "fields": [
            ("notification_id", "uuid", "PK"),
            ("tenant_id", "uuid", "FK"),
            ("customer_id", "uuid", "FK"),
            ("notification_type", "string", None),
            ("channel", "string", None),
            ("ab_variant", "string", None),
            ("status", "string", None),
            ("sent_at", "timestamp", None),
        ]
    },
    {
        "id": "AB_TESTS",
        "domain": "analytics",
        "col": 9,
        "is_new": True,
        "desc_ar": "تجارب A/B لصياغة رسائل التذكير الطبية لقياس الأكثر فاعلية وتأثيراً.",
        "fields": [
            ("test_id", "uuid", "PK"),
            ("tenant_id", "uuid", "FK"),
            ("test_name", "string", None),
            ("variant_a", "string", None),
            ("variant_b", "string", None),
            ("is_active", "boolean", None),
            ("created_at", "timestamp", None),
        ]
    },
    {
        "id": "AB_TEST_RESULTS",
        "domain": "analytics",
        "col": 9,
        "is_new": True,
        "desc_ar": "معدلات التحويل والشراء الفعلي الناتجة عن كل نموذج رسالة في تجارب A/B.",
        "fields": [
            ("result_id", "uuid", "PK"),
            ("test_id", "uuid", "FK"),
            ("notification_id", "uuid", "FK"),
            ("variant", "string", None),
            ("converted", "boolean", None),
            ("recorded_at", "timestamp", None),
        ]
    },
    {
        "id": "KNOWLEDGE_CHUNKS",
        "domain": "analytics",
        "col": 9,
        "is_new": True,
        "desc_ar": "قاعدة المعرفة الصيدلانية ومتجهات RAG الرياضية لتوليد الإجابات الدقيقة.",
        "fields": [
            ("chunk_id", "uuid", "PK"),
            ("tenant_id", "uuid", "FK"),
            ("source_type", "string", None),
            ("content", "text", None),
            ("embedding", "vector", None),
            ("created_at", "timestamp", None),
        ]
    },
]

# 35 Cleanly routed relationships
RELATIONSHIPS = [
    # Multi-Tenant & Core
    {"from": "TENANTS", "to": "TENANT_SETTINGS", "label": "configures", "color": "#4338ca", "route": "vertical"},
    {"from": "TENANTS", "to": "CUSTOMERS", "label": "registers", "color": "#4338ca", "route": "h_right_to_left"},
    {"from": "TENANTS", "to": "AUDIT_LOGS", "label": "scopes", "color": "#4338ca", "route": "side_loop_left"},
    
    # Customer
    {"from": "CUSTOMERS", "to": "SESSIONS", "label": "opens", "color": "#0284c7", "route": "vertical"},
    {"from": "SESSIONS", "to": "EVENTS", "label": "logs", "color": "#0284c7", "route": "vertical"},
    {"from": "CUSTOMERS", "to": "CONTACT_MESSAGES", "label": "submits", "color": "#0284c7", "route": "side_loop_left"},
    {"from": "CUSTOMERS", "to": "ORDERS", "label": "places", "color": "#0284c7", "route": "h_right_to_left"},
    
    # Orders & Commerce
    {"from": "ORDERS", "to": "ORDER_ITEMS", "label": "contains", "color": "#059669", "route": "vertical"},
    {"from": "COUPONS", "to": "ORDERS", "label": "discounts", "color": "#059669", "route": "side_loop_left"},
    
    # Drugs & Safety
    {"from": "DRUGS", "to": "ORDER_ITEMS", "label": "sold_as", "color": "#d97706", "route": "h_left_to_right"},
    {"from": "DRUGS", "to": "DRUG_INTERACTIONS", "label": "conflicts", "color": "#d97706", "route": "vertical"},
    {"from": "DRUGS", "to": "DRUG_AFFINITIES", "label": "pairs_with", "color": "#d97706", "route": "side_loop_right"},
    
    # Inventory & Cycles
    {"from": "DRUGS", "to": "INVENTORY_ITEMS", "label": "stocked_as", "color": "#0d9488", "route": "h_right_to_left"},
    {"from": "DRUGS", "to": "CUSTOMER_CYCLES", "label": "tracked_for", "color": "#0d9488", "route": "h_right_to_left"},
    {"from": "DRUGS", "to": "PENDING_REMINDERS", "label": "targets", "color": "#0d9488", "route": "h_right_to_left"},
    {"from": "CUSTOMERS", "to": "CUSTOMER_CYCLES", "label": "has", "color": "#0d9488", "route": "arch_top"},
    
    # Prescriptions & OCR
    {"from": "CUSTOMERS", "to": "PRESCRIPTIONS", "label": "uploads", "color": "#7c3aed", "route": "arch_top"},
    {"from": "PRESCRIPTIONS", "to": "PRESCRIPTION_ANALYSES", "label": "analyzes", "color": "#7c3aed", "route": "vertical"},
    {"from": "PRESCRIPTION_ANALYSES", "to": "PRESCRIPTION_ITEMS", "label": "extracts", "color": "#7c3aed", "route": "vertical"},
    {"from": "DRUGS", "to": "PRESCRIPTION_ITEMS", "label": "matches", "color": "#7c3aed", "route": "arch_bottom"},
    {"from": "DRUGS", "to": "OCR_CORRECTIONS", "label": "corrects", "color": "#7c3aed", "route": "arch_top"},
    {"from": "OCR_CORRECTIONS", "to": "OCR_CORRECTION_EXAMPLES", "label": "trains", "color": "#7c3aed", "route": "vertical"},
    {"from": "PRESCRIPTIONS", "to": "OCR_CORRECTION_EXAMPLES", "label": "samples", "color": "#7c3aed", "route": "h_right_to_left"},
    
    # Procurement & Finance
    {"from": "DRUGS", "to": "SIMULATION_RUNS", "label": "simulates", "color": "#0891b2", "route": "arch_bottom"},
    {"from": "PURCHASE_ORDERS", "to": "PURCHASE_ORDER_ITEMS", "label": "orders", "color": "#0891b2", "route": "vertical"},
    {"from": "DRUGS", "to": "PURCHASE_ORDER_ITEMS", "label": "procures", "color": "#0891b2", "route": "arch_bottom"},
    {"from": "PURCHASE_ORDERS", "to": "JOURNAL_ENTRIES", "label": "generates", "color": "#0891b2", "route": "side_loop_left"},
    {"from": "JOURNAL_ENTRIES", "to": "JOURNAL_ENTRY_LINES", "label": "details", "color": "#0891b2", "route": "vertical"},
    {"from": "ORDERS", "to": "JOURNAL_ENTRIES", "label": "settles", "color": "#0891b2", "route": "arch_bottom"},
    
    # AI & Automations
    {"from": "CUSTOMERS", "to": "AI_CHAT_LOGS", "label": "chats", "color": "#e11d48", "route": "arch_top"},
    {"from": "AUTOMATION_RUNS", "to": "EMERGENCY_OUTBOX", "label": "triggers", "color": "#e11d48", "route": "vertical"},
    
    # Analytics & System
    {"from": "CUSTOMERS", "to": "NOTIFICATIONS", "label": "receives", "color": "#475569", "route": "arch_top"},
    {"from": "NOTIFICATIONS", "to": "AB_TEST_RESULTS", "label": "measures", "color": "#475569", "route": "side_loop_right"},
    {"from": "AB_TESTS", "to": "AB_TEST_RESULTS", "label": "tracks", "color": "#475569", "route": "vertical"},
]

def build_erd_data():
    COL_WIDTH = 252
    COL_GAP = 38
    START_X = 50
    START_Y = 115
    HEADER_H = 28
    ROW_H = 20
    VERTICAL_GAP = 28

    col_x = {c: START_X + c * (COL_WIDTH + COL_GAP) for c in range(10)}
    table_coords = {}
    col_current_y = {c: START_Y for c in range(10)}

    for t in TABLES:
        col = t["col"]
        num_fields = len(t["fields"])
        height = HEADER_H + 4 + num_fields * ROW_H
        x = col_x[col]
        y = col_current_y[col]
        table_coords[t["id"]] = {
            "id": t["id"],
            "x": x,
            "y": y,
            "w": COL_WIDTH,
            "h": height,
            "domain": t["domain"],
            "is_new": t["is_new"],
            "desc_ar": t["desc_ar"],
            "fields": t["fields"]
        }
        col_current_y[col] += height + VERTICAL_GAP

    max_height = max(col_current_y.values()) + 65
    total_width = col_x[9] + COL_WIDTH + START_X

    return table_coords, total_width, max_height

def generate_svg_markup(table_coords, total_width, max_height):
    center_x = total_width / 2
    HEADER_H = 28
    ROW_H = 20

    svg_parts = []
    svg_parts.append(f'<svg id="main-erd-svg" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total_width} {max_height}" width="{total_width}" height="{max_height}" style="background:white; font-family:\'Segoe UI\', -apple-system, sans-serif;">')

    # SVG Defs
    svg_parts.append('''
  <defs>
    <filter id="card-shadow" x="-5%" y="-4%" width="110%" height="112%" filterUnits="userSpaceOnUse">
      <feDropShadow dx="0" dy="2" stdDeviation="3.5" flood-color="#0f172a" flood-opacity="0.07"/>
    </filter>
  </defs>
''')

    # Header Title & Subtitle
    svg_parts.append(f'''
  <!-- ── Header Title & System Meta ── -->
  <text x="{center_x}" y="38" text-anchor="middle" font-size="23" font-weight="800" fill="#0f172a" letter-spacing="-0.3">AI-COS Pharmacy — Entity Relationship Diagram (v6)</text>
  <text x="{center_x}" y="60" text-anchor="middle" font-size="12.5" fill="#64748b" font-weight="500">33 Tables · 35 Relationships · PostgreSQL 15 + Supabase · Complete Architecture 2026/2027</text>
''')

    # Domain Legend
    legend_items = [
        ("Multi-Tenant", "#4338ca", "core"),
        ("Customer/Session", "#0284c7", "customer"),
        ("Orders/Commerce", "#059669", "orders"),
        ("Drug Catalog", "#d97706", "drugs"),
        ("Inventory/Cycle", "#0d9488", "inventory"),
        ("Prescriptions/OCR [NEW]", "#7c3aed", "ocr"),
        ("Finance/Accounting [NEW]", "#0891b2", "finance"),
        ("AI Agents [NEW]", "#e11d48", "ai"),
        ("Analytics/System", "#475569", "analytics"),
    ]
    
    curr_lx = 50
    for label, col, dkey in legend_items:
        svg_parts.append(f'<g class="legend-chip" data-domain="{dkey}" style="cursor: pointer;">')
        svg_parts.append(f'<rect x="{curr_lx}" y="78" width="13" height="13" rx="3.5" fill="{col}"/>')
        svg_parts.append(f'<text x="{curr_lx + 17}" y="89" font-size="10.5" fill="#334155" font-weight="600">{label}</text>')
        svg_parts.append('</g>')
        curr_lx += len(label) * 7.1 + 28

    # Key Badges Legend
    svg_parts.append(f'<rect x="{curr_lx}" y="77" width="22" height="14" rx="7" fill="#fef3c7"/>')
    svg_parts.append(f'<text x="{curr_lx + 4}" y="87.5" font-size="8" font-weight="bold" fill="#92400e">PK</text>')
    curr_lx += 28
    svg_parts.append(f'<rect x="{curr_lx}" y="77" width="22" height="14" rx="7" fill="#ede9fe"/>')
    svg_parts.append(f'<text x="{curr_lx + 4}" y="87.5" font-size="8" font-weight="bold" fill="#5b21b6">FK</text>')
    curr_lx += 28
    svg_parts.append(f'<rect x="{curr_lx}" y="77" width="38" height="14" rx="7" fill="#dbeafe"/>')
    svg_parts.append(f'<text x="{curr_lx + 4}" y="87.5" font-size="8" font-weight="bold" fill="#1e40af">PK/FK</text>')

    # ── Connector Lines ──
    svg_parts.append('\n  <!-- ── Connector Lines ── -->')
    svg_parts.append('  <g id="connectors-layer">')

    for rel in RELATIONSHIPS:
        fid = rel["from"]
        tid = rel["to"]
        if fid not in table_coords or tid not in table_coords:
            continue
        fc = table_coords[fid]
        tc = table_coords[tid]
        label = rel["label"]
        color = rel["color"]
        route = rel["route"]

        # Calculate exact geometric paths
        if route == "vertical":
            fx = fc["x"] + fc["w"] / 2
            fy = fc["y"] + fc["h"]
            tx = tc["x"] + tc["w"] / 2
            ty = tc["y"]
            cx1 = fx
            cy1 = fy + (ty - fy) * 0.5
            cx2 = tx
            cy2 = fy + (ty - fy) * 0.5
            mid_x = fx
            mid_y = (fy + ty) / 2
            arrow_svg = f'<polygon points="{tx},{ty} {tx-4},{ty-6} {tx+4},{ty-6}" fill="{color}" fill-opacity="0.75"/>'

        elif route == "h_right_to_left":
            fx = fc["x"] + fc["w"]
            fy = fc["y"] + min(45, fc["h"] * 0.3)
            tx = tc["x"]
            ty = tc["y"] + min(45, tc["h"] * 0.3)
            dx = (tx - fx) * 0.5
            cx1 = fx + dx
            cy1 = fy
            cx2 = tx - dx
            cy2 = ty
            mid_x = (fx + tx) / 2
            mid_y = (fy + ty) / 2
            arrow_svg = f'<polygon points="{tx},{ty} {tx-6},{ty-4} {tx-6},{ty+4}" fill="{color}" fill-opacity="0.75"/>'

        elif route == "h_left_to_right":
            fx = fc["x"]
            fy = fc["y"] + min(45, fc["h"] * 0.3)
            tx = tc["x"] + tc["w"]
            ty = tc["y"] + min(45, tc["h"] * 0.3)
            dx = (fx - tx) * 0.5
            cx1 = fx - dx
            cy1 = fy
            cx2 = tx + dx
            cy2 = ty
            mid_x = (fx + tx) / 2
            mid_y = (fy + ty) / 2
            arrow_svg = f'<polygon points="{tx},{ty} {tx+6},{ty-4} {tx+6},{ty+4}" fill="{color}" fill-opacity="0.75"/>'

        elif route == "side_loop_left":
            fx = fc["x"]
            fy = fc["y"] + min(50, fc["h"] * 0.4)
            tx = tc["x"]
            ty = tc["y"] + min(50, tc["h"] * 0.4)
            loop_x = min(fx, tx) - 22
            cx1 = loop_x
            cy1 = fy
            cx2 = loop_x
            cy2 = ty
            mid_x = loop_x
            mid_y = (fy + ty) / 2
            arrow_svg = f'<polygon points="{tx},{ty} {tx-6},{ty-4} {tx-6},{ty+4}" fill="{color}" fill-opacity="0.75"/>'

        elif route == "side_loop_right":
            fx = fc["x"] + fc["w"]
            fy = fc["y"] + min(50, fc["h"] * 0.4)
            tx = tc["x"] + tc["w"]
            ty = tc["y"] + min(50, tc["h"] * 0.4)
            loop_x = max(fx, tx) + 22
            cx1 = loop_x
            cy1 = fy
            cx2 = loop_x
            cy2 = ty
            mid_x = loop_x
            mid_y = (fy + ty) / 2
            arrow_svg = f'<polygon points="{tx},{ty} {tx+6},{ty-4} {tx+6},{ty+4}" fill="{color}" fill-opacity="0.75"/>'

        elif route == "arch_top":
            fx = fc["x"] + fc["w"] * 0.7
            fy = fc["y"]
            tx = tc["x"] + tc["w"] * 0.3
            ty = tc["y"]
            arch_y = min(fy, ty) - 26
            cx1 = fx
            cy1 = arch_y
            cx2 = tx
            cy2 = arch_y
            mid_x = (fx + tx) / 2
            mid_y = arch_y
            arrow_svg = f'<polygon points="{tx},{ty} {tx-4},{ty-6} {tx+4},{ty-6}" fill="{color}" fill-opacity="0.75"/>'

        elif route == "arch_bottom":
            fx = fc["x"] + fc["w"] * 0.7
            fy = fc["y"] + fc["h"]
            tx = tc["x"] + tc["w"] * 0.3
            ty = tc["y"] + tc["h"]
            arch_y = max(fy, ty) + 26
            cx1 = fx
            cy1 = arch_y
            cx2 = tx
            cy2 = arch_y
            mid_x = (fx + tx) / 2
            mid_y = arch_y
            arrow_svg = f'<polygon points="{tx},{ty} {tx-4},{ty+6} {tx+4},{ty+6}" fill="{color}" fill-opacity="0.75"/>'

        # Write edge
        svg_parts.append(f'<g class="erd-rel" data-from="{fid}" data-to="{tid}">')
        svg_parts.append(f'<path d="M {fx:.1f},{fy:.1f} C {cx1:.1f},{cy1:.1f} {cx2:.1f},{cy2:.1f} {tx:.1f},{ty:.1f}" fill="none" stroke="{color}" stroke-width="1.3" stroke-opacity="0.48"/>')
        svg_parts.append(f'<circle cx="{fx:.1f}" cy="{fy:.1f}" r="2.8" fill="white" stroke="{color}" stroke-width="1.3"/>')
        svg_parts.append(arrow_svg)

        # Label pill
        lbl_w = len(label) * 5.6 + 10
        svg_parts.append(f'<rect x="{mid_x - lbl_w/2:.1f}" y="{mid_y - 6.5:.1f}" width="{lbl_w:.1f}" height="13" rx="3.5" fill="#ffffff" stroke="#e2e8f0" stroke-width="0.8"/>')
        svg_parts.append(f'<text x="{mid_x:.1f}" y="{mid_y + 3.2:.1f}" text-anchor="middle" font-size="8" fill="#475569" font-style="italic" font-weight="600">{label}</text>')
        svg_parts.append('</g>')

    svg_parts.append('  </g>')

    # ── Render Tables ──
    svg_parts.append('\n  <!-- ── Tables Layer ── -->')
    svg_parts.append('  <g id="tables-layer">')

    for t_id, data in table_coords.items():
        x = data["x"]
        y = data["y"]
        w = data["w"]
        h = data["h"]
        domain = data["domain"]
        is_new = data["is_new"]
        dinfo = DOMAIN_META[domain]
        hdr_color = dinfo["color"]
        border_color = dinfo["border"]
        fields = data["fields"]

        svg_parts.append(f'<g id="table-{t_id}" class="erd-table-group" data-table="{t_id}" data-domain="{domain}" style="cursor: pointer;">')
        
        # Shadow & Card Outline
        svg_parts.append(f'<rect x="{x+2}" y="{y+2}" width="{w}" height="{h}" rx="8" fill="#0000000a"/>')
        svg_parts.append(f'<rect id="box-{t_id}" class="table-card" x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="#ffffff" stroke="{border_color}" stroke-width="{2.2 if is_new else 1.4}"/>')
        
        # Top Header (Clean rounded fill)
        svg_parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{HEADER_H}" rx="8" fill="{hdr_color}"/>')
        svg_parts.append(f'<rect x="{x}" y="{y+HEADER_H-8}" width="{w}" height="8" fill="{hdr_color}"/>')
        
        # Header Text
        title_str = t_id
        if is_new:
            title_str += "  [NEW]"
        svg_parts.append(f'<text x="{x+10}" y="{y+19}" font-size="11.5" font-weight="700" fill="#ffffff" letter-spacing="0.2">{title_str}</text>')

        # Rows
        curr_ry = y + HEADER_H
        for i, (fname, ftype, fkey) in enumerate(fields):
            row_bg = "#f8fafc" if (i % 2 == 1) else "#ffffff"
            svg_parts.append(f'<rect x="{x+1}" y="{curr_ry}" width="{w-2}" height="{ROW_H}" fill="{row_bg}"/>')
            
            # Type (Gray monospace)
            svg_parts.append(f'<text x="{x+8}" y="{curr_ry+14}" font-size="9" fill="#94a3b8" font-family="Consolas, monospace">{ftype}</text>')
            
            # Name (Dark bold slate)
            svg_parts.append(f'<text x="{x+80}" y="{curr_ry+14}" font-size="10" fill="#1e293b" font-weight="600">{fname}</text>')
            
            # Badge
            if fkey == "PK":
                bx = x + w - 28
                svg_parts.append(f'<rect x="{bx}" y="{curr_ry+3}" width="22" height="14" rx="7" fill="#fef3c7"/>')
                svg_parts.append(f'<text x="{bx+4}" y="{curr_ry+13.5}" font-size="7.5" font-weight="bold" fill="#92400e">PK</text>')
            elif fkey == "FK":
                bx = x + w - 28
                svg_parts.append(f'<rect x="{bx}" y="{curr_ry+3}" width="22" height="14" rx="7" fill="#ede9fe"/>')
                svg_parts.append(f'<text x="{bx+4}" y="{curr_ry+13.5}" font-size="7.5" font-weight="bold" fill="#5b21b6">FK</text>')
            elif fkey == "PK/FK":
                bx = x + w - 42
                svg_parts.append(f'<rect x="{bx}" y="{curr_ry+3}" width="38" height="14" rx="7" fill="#dbeafe"/>')
                svg_parts.append(f'<text x="{bx+4}" y="{curr_ry+13.5}" font-size="7.5" font-weight="bold" fill="#1e40af">PK/FK</text>')

            curr_ry += ROW_H

        svg_parts.append('</g>')

    svg_parts.append('  </g>')

    # Footer
    footer_y = max_height - 24
    svg_parts.append(f'<text x="{center_x}" y="{footer_y}" text-anchor="middle" font-size="10" fill="#94a3b8" font-weight="500">AI-COS Pharmacy · Graduation Project 2026/2027 · Faculty of Computers &amp; Informatics · Suez Canal University · ERD v6 Final Production</text>')

    svg_parts.append('</svg>')
    return "\n".join(svg_parts)

def build_full_html():
    table_coords, total_width, max_height = build_erd_data()
    svg_markup = generate_svg_markup(table_coords, total_width, max_height)

    # JSON metadata for client-side search and inspector drawer
    meta_dict = {}
    for t in TABLES:
        dinfo = DOMAIN_META[t["domain"]]
        meta_dict[t["id"]] = {
            "name_ar": t["desc_ar"],
            "domain": dinfo["title"],
            "domain_ar": dinfo["title_ar"],
            "color": dinfo["color"],
            "fields": [{"name": f[0], "type": f[1], "key": f[2]} for f in t["fields"]]
        }

    meta_json = json.dumps(meta_dict, ensure_ascii=False)

    html_content = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI-COS Pharmacy ERD v6 (2026/2027)</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg-page: #f8fafc;
    --border: #e2e8f0;
    --text-primary: #1e293b;
    --text-secondary: #64748b;
    --primary: #4338ca;
  }}

  * {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    font-family: 'Cairo', "Segoe UI", system-ui, -apple-system, sans-serif;
    background: #ffffff;
    color: var(--text-primary);
    width: 100vw;
    height: 100vh;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    user-select: none;
  }}

  /* Top Minimal Toolbar */
  header {{
    background: #ffffff;
    border-bottom: 1px solid var(--border);
    padding: 10px 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    z-index: 10;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
  }}

  .brand {{
    display: flex;
    align-items: center;
    gap: 12px;
  }}

  .brand-badge {{
    width: 36px;
    height: 36px;
    border-radius: 10px;
    background: linear-gradient(135deg, #4338ca, #6366f1);
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 19px;
  }}

  .brand-info h1 {{
    font-size: 16px;
    font-weight: 800;
    color: #0f172a;
    line-height: 1.2;
  }}

  .brand-info p {{
    font-size: 11.5px;
    color: var(--text-secondary);
  }}

  .header-actions {{
    display: flex;
    align-items: center;
    gap: 10px;
  }}

  .search-box {{
    position: relative;
    width: 260px;
  }}

  .search-input {{
    width: 100%;
    font-family: inherit;
    font-size: 12px;
    padding: 6px 12px 6px 30px;
    border-radius: 8px;
    border: 1px solid var(--border);
    background: #f8fafc;
    color: var(--text-primary);
    outline: none;
    transition: all 0.15s;
  }}

  .search-input:focus {{
    background: #ffffff;
    border-color: #6366f1;
    box-shadow: 0 0 0 3px rgba(99,102,241,0.12);
  }}

  .search-icon {{
    position: absolute;
    left: 9px;
    top: 50%;
    transform: translateY(-50%);
    font-size: 13px;
    color: var(--text-secondary);
    pointer-events: none;
  }}

  .btn {{
    font-family: inherit;
    font-size: 12px;
    font-weight: 600;
    padding: 6px 14px;
    border-radius: 8px;
    border: 1px solid var(--border);
    background: #ffffff;
    color: var(--text-primary);
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    transition: all 0.15s;
  }}

  .btn:hover {{
    background: #f8fafc;
    border-color: #cbd5e1;
  }}

  .btn-primary {{
    background: #4338ca;
    color: white;
    border-color: #4338ca;
  }}

  .btn-primary:hover {{
    background: #3730a3;
  }}

  /* Canvas Container */
  .canvas-wrapper {{
    flex: 1;
    position: relative;
    overflow: hidden;
    background: #ffffff;
    background-image: radial-gradient(rgba(148, 163, 184, 0.22) 1.2px, transparent 1.2px);
    background-size: 24px 24px;
    cursor: grab;
    direction: ltr !important;
  }}

  .canvas-wrapper:active {{
    cursor: grabbing;
  }}

  #panzoom-layer {{
    position: absolute;
    top: 0;
    left: 0;
    transform-origin: 0 0;
    will-change: transform;
    direction: ltr !important;
  }}

  /* Floating Bottom Controls */
  .controls-bar {{
    position: absolute;
    bottom: 24px;
    left: 24px;
    background: #ffffff;
    border: 1px solid var(--border);
    border-radius: 12px;
    box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
    display: flex;
    align-items: center;
    gap: 3px;
    padding: 5px;
    z-index: 20;
    direction: ltr !important;
  }}

  .ctrl-btn {{
    background: transparent;
    border: none;
    border-radius: 8px;
    padding: 6px 10px;
    font-family: inherit;
    font-size: 12px;
    font-weight: 600;
    color: var(--text-primary);
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 4px;
    transition: background 0.15s;
  }}

  .ctrl-btn:hover {{
    background: #f1f5f9;
    color: #4338ca;
  }}

  .ctrl-sep {{
    width: 1px;
    height: 18px;
    background: var(--border);
    margin: 0 2px;
  }}

  .zoom-label {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 11.5px;
    font-weight: 700;
    color: var(--text-secondary);
    min-width: 48px;
    text-align: center;
  }}

  .hint-badge {{
    position: absolute;
    bottom: 24px;
    right: 24px;
    background: #ffffff;
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 6px 14px;
    font-size: 11.5px;
    color: var(--text-secondary);
    box-shadow: 0 2px 4px rgba(0,0,0,0.04);
    pointer-events: none;
    z-index: 10;
  }}

  /* Highlighting and Interaction Styles */
  .erd-table-group {{
    transition: transform 0.15s ease, opacity 0.2s ease;
  }}

  .erd-table-group:hover .table-card {{
    filter: drop-shadow(0 4px 14px rgba(67, 56, 202, 0.3));
    stroke-width: 2.4px !important;
  }}

  .dimmed {{
    opacity: 0.22 !important;
  }}

  .highlighted {{
    opacity: 1 !important;
  }}

  .highlighted .table-card {{
    filter: drop-shadow(0 0 16px rgba(67, 56, 202, 0.6)) !important;
    stroke-width: 2.8px !important;
  }}

  @keyframes pulseNode {{
    0% {{ filter: drop-shadow(0 0 0 rgba(67, 56, 202, 0)); }}
    50% {{ filter: drop-shadow(0 0 24px rgba(67, 56, 202, 0.9)); }}
    100% {{ filter: drop-shadow(0 0 8px rgba(67, 56, 202, 0.4)); }}
  }}

  .spotlight-active .table-card {{
    animation: pulseNode 1.2s ease-in-out infinite alternate !important;
  }}

  /* Drawer Inspector */
  .inspector {{
    position: fixed;
    top: 0;
    right: -420px;
    width: 390px;
    height: 100vh;
    background: #ffffff;
    border-left: 1px solid var(--border);
    box-shadow: -8px 0 24px rgba(0,0,0,0.08);
    z-index: 100;
    transition: right 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    display: flex;
    flex-direction: column;
  }}

  .inspector.open {{
    right: 0;
  }}

  .insp-head {{
    padding: 16px 20px;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    justify-content: space-between;
  }}

  .insp-head h2 {{
    font-size: 16px;
    font-weight: 700;
    color: #0f172a;
  }}

  .close-insp {{
    background: none;
    border: none;
    font-size: 18px;
    color: var(--text-secondary);
    cursor: pointer;
    padding: 4px 8px;
    border-radius: 6px;
  }}

  .close-insp:hover {{
    background: #f1f5f9;
  }}

  .insp-body {{
    padding: 20px;
    overflow-y: auto;
    flex: 1;
  }}

  .insp-item {{
    margin-bottom: 16px;
  }}

  .insp-item label {{
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    color: var(--text-secondary);
    display: block;
    margin-bottom: 4px;
    letter-spacing: 0.4px;
  }}

  .insp-item p {{
    font-size: 13px;
    line-height: 1.6;
    color: #1e293b;
  }}

  .col-list {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 11.5px;
    background: #f8fafc;
    border: 1px solid var(--border);
    padding: 10px;
    border-radius: 8px;
    max-height: 280px;
    overflow-y: auto;
    direction: ltr;
    text-align: left;
  }}

  .col-row {{
    display: flex;
    justify-content: space-between;
    padding: 3px 0;
    border-bottom: 1px dashed #e2e8f0;
  }}

  .col-row:last-child {{
    border-bottom: none;
  }}

  @media print {{
    header, .controls-bar, .hint-badge, .inspector {{ display: none !important; }}
    .canvas-wrapper {{ overflow: visible !important; }}
    #panzoom-layer {{ transform: none !important; position: static !important; }}
    #main-erd-svg {{ width: 100% !important; height: auto !important; }}
  }}
</style>
</head>
<body>

<header>
  <div class="brand">
    <div class="brand-badge">💊</div>
    <div class="brand-info">
      <h1>AI-COS Pharmacy — مخطط قاعدة البيانات الكامل (ERD v6)</h1>
      <p>33 جدولاً مكتملاً · 35 علاقة ربط · نموذج PostgreSQL Supabase الإنتاجي · 2026/2027</p>
    </div>
  </div>

  <div class="header-actions">
    <div class="search-box">
      <span class="search-icon">🔍</span>
      <input type="text" id="search-input" class="search-input" placeholder="ابحث عن جدول للتكبير عليه..." list="tables-list">
      <datalist id="tables-list"></datalist>
    </div>
    <button class="btn btn-primary" id="btn-dl-svg" title="تصدير كملف SVG فكتور عالي الجودة">
      💾 تصدير SVG
    </button>
  </div>
</header>

<main class="canvas-wrapper" id="canvas-wrapper">
  <div id="panzoom-layer">
    {svg_markup}
  </div>

  <div class="controls-bar">
    <button class="ctrl-btn" id="btn-zoom-in" title="تكبير (+)">➕</button>
    <div class="zoom-label" id="zoom-label">100%</div>
    <button class="ctrl-btn" id="btn-zoom-out" title="تصغير (-)">➖</button>
    <div class="ctrl-sep"></div>
    <button class="ctrl-btn" id="btn-reset" title="الحجم الأصلي الطبيعي">1:1 أصلي</button>
    <button class="ctrl-btn" id="btn-fit" title="ملاءمة الشاشة">⊡ ملاءمة</button>
    <div class="ctrl-sep"></div>
    <button class="ctrl-btn" id="btn-fullscreen" title="ملء الشاشة">⛶ ملء الشاشة</button>
  </div>

  <div class="hint-badge">
    💡 عجلة الفأرة للتكبير/التصغير · اسحب بالفأرة للتنقل · انقر على أي جدول أو تصنيف للتفاصيل
  </div>
</main>

<!-- Side Inspector Drawer -->
<aside class="inspector" id="inspector">
  <div class="insp-head">
    <h2 id="insp-title">اسم الجدول</h2>
    <button class="close-insp" id="close-insp">✕</button>
  </div>
  <div class="insp-body">
    <div class="insp-item">
      <label>القطاع المعماري</label>
      <span id="insp-domain" style="font-weight:700; color: #4338ca; font-size:13px;"></span>
    </div>
    <div class="insp-item">
      <label>الوصف والدور الوظيفي في AI-COS</label>
      <p id="insp-desc"></p>
    </div>
    <div class="insp-item">
      <label>الحقول والمفاتيح (PK / FK)</label>
      <div class="col-list" id="insp-cols"></div>
    </div>
  </div>
</aside>

<script>
const META = {meta_json};
const SVG_W = {total_width};
const SVG_H = {max_height};

let scale = 1.0;
let translateX = 0;
let translateY = 0;
let isDragging = false;
let startX = 0, startY = 0;

const panzoomLayer = document.getElementById('panzoom-layer');
const canvasWrapper = document.getElementById('canvas-wrapper');
const zoomLabel = document.getElementById('zoom-label');
const searchInput = document.getElementById('search-input');
const datalist = document.getElementById('tables-list');
const inspector = document.getElementById('inspector');

// Populate Search Datalist
for (const [id, m] of Object.entries(META)) {{
  const opt = document.createElement('option');
  opt.value = id;
  opt.label = `${{m.domain_ar}} (${{id}})`;
  datalist.appendChild(opt);
}}

function updateTransform() {{
  panzoomLayer.style.transform = `translate(${{translateX}}px, ${{translateY}}px) scale(${{scale}})`;
  zoomLabel.textContent = Math.round(scale * 100) + '%';
}}

function fitToScreen() {{
  const r = canvasWrapper.getBoundingClientRect();
  const pad = 30;
  const scaleX = (r.width - pad * 2) / SVG_W;
  const scaleY = (r.height - pad * 2) / SVG_H;
  scale = Math.min(scaleX, scaleY);
  scale = Math.min(Math.max(scale, 0.35), 1.2);
  translateX = (r.width - SVG_W * scale) / 2;
  translateY = Math.max(15, (r.height - SVG_H * scale) / 2);
  updateTransform();
}}

function zoomAt(factor, clientX, clientY) {{
  const r = canvasWrapper.getBoundingClientRect();
  const x = clientX !== undefined ? clientX - r.left : r.width / 2;
  const y = clientY !== undefined ? clientY - r.top : r.height / 2;
  const newScale = Math.min(Math.max(scale * factor, 0.25), 3.5);
  const ratio = newScale / scale;
  translateX = x - (x - translateX) * ratio;
  translateY = y - (y - translateY) * ratio;
  scale = newScale;
  updateTransform();
}}

// Mouse Pan and Zoom
canvasWrapper.addEventListener('wheel', (e) => {{
  e.preventDefault();
  const factor = e.deltaY < 0 ? 1.15 : 0.87;
  zoomAt(factor, e.clientX, e.clientY);
}}, {{ passive: false }});

canvasWrapper.addEventListener('mousedown', (e) => {{
  if (e.button !== 0) return;
  isDragging = true;
  startX = e.clientX - translateX;
  startY = e.clientY - translateY;
}});

window.addEventListener('mousemove', (e) => {{
  if (!isDragging) return;
  translateX = e.clientX - startX;
  translateY = e.clientY - startY;
  updateTransform();
}});

window.addEventListener('mouseup', () => {{
  isDragging = false;
}});

// Touch gestures
let lastTouchDist = 0;
canvasWrapper.addEventListener('touchstart', (e) => {{
  if (e.touches.length === 1) {{
    isDragging = true;
    startX = e.touches[0].clientX - translateX;
    startY = e.touches[0].clientY - translateY;
  }} else if (e.touches.length === 2) {{
    isDragging = false;
    lastTouchDist = Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY);
  }}
}}, {{ passive: false }});

canvasWrapper.addEventListener('touchmove', (e) => {{
  if (e.touches.length === 1 && isDragging) {{
    translateX = e.touches[0].clientX - startX;
    translateY = e.touches[0].clientY - startY;
    updateTransform();
  }} else if (e.touches.length === 2) {{
    e.preventDefault();
    const dist = Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY);
    if (lastTouchDist > 0) {{
      const factor = dist / lastTouchDist;
      const midX = (e.touches[0].clientX + e.touches[1].clientX) / 2;
      const midY = (e.touches[0].clientY + e.touches[1].clientY) / 2;
      zoomAt(factor, midX, midY);
    }}
    lastTouchDist = dist;
  }}
}}, {{ passive: false }});

canvasWrapper.addEventListener('touchend', () => {{
  isDragging = false;
  lastTouchDist = 0;
}});

// Buttons
document.getElementById('btn-zoom-in').addEventListener('click', () => zoomAt(1.2));
document.getElementById('btn-zoom-out').addEventListener('click', () => zoomAt(0.8));
document.getElementById('btn-fit').addEventListener('click', fitToScreen);
document.getElementById('btn-reset').addEventListener('click', () => {{
  scale = 1.0;
  const r = canvasWrapper.getBoundingClientRect();
  translateX = (r.width - SVG_W) / 2;
  translateY = Math.max(20, (r.height - SVG_H) / 2);
  updateTransform();
}});

document.getElementById('btn-fullscreen').addEventListener('click', () => {{
  if (!document.fullscreenElement) {{
    document.documentElement.requestFullscreen();
  }} else {{
    document.exitFullscreen();
  }}
}});

// Table Clicking & Inspector
document.querySelectorAll('.erd-table-group').forEach(grp => {{
  grp.addEventListener('click', (e) => {{
    e.stopPropagation();
    const tid = grp.getAttribute('data-table');
    openInspector(tid);
  }});
}});

function openInspector(tid) {{
  const m = META[tid];
  if (!m) return;
  document.getElementById('insp-title').textContent = tid;
  document.getElementById('insp-domain').textContent = `${{m.domain_ar}} (${{m.domain}})`;
  document.getElementById('insp-domain').style.color = m.color;
  document.getElementById('insp-desc').textContent = m.name_ar;

  let colsHtml = '';
  m.fields.forEach(f => {{
    let badge = '';
    if (f.key === 'PK') badge = '<span style="color:#d97706;font-weight:700;">[PK]</span> ';
    else if (f.key === 'FK') badge = '<span style="color:#7c3aed;font-weight:700;">[FK]</span> ';
    else if (f.key === 'PK/FK') badge = '<span style="color:#0284c7;font-weight:700;">[PK/FK]</span> ';
    colsHtml += `<div class="col-row"><span>${{f.name}}</span><span style="color:#94a3b8;">${{f.type}} ${{badge}}</span></div>`;
  }});
  document.getElementById('insp-cols').innerHTML = colsHtml;
  inspector.classList.add('open');

  // Highlight table
  document.querySelectorAll('.erd-table-group').forEach(g => {{
    g.classList.toggle('spotlight-active', g.getAttribute('data-table') === tid);
  }});
  setTimeout(() => {{
    document.querySelectorAll('.erd-table-group').forEach(g => g.classList.remove('spotlight-active'));
  }}, 4000);
}}

document.getElementById('close-insp').addEventListener('click', () => {{
  inspector.classList.remove('open');
}});

canvasWrapper.addEventListener('click', () => {{
  inspector.classList.remove('open');
  document.querySelectorAll('.erd-table-group, .erd-rel').forEach(el => {{
    el.classList.remove('dimmed', 'highlighted', 'spotlight-active');
  }});
}});

// Search Handler
searchInput.addEventListener('change', (e) => {{
  const q = e.target.value.trim().toUpperCase();
  if (!q) return;
  const grp = document.getElementById('table-' + q);
  if (!grp) {{
    alert('الجدول ' + q + ' غير موجود.');
    return;
  }}
  openInspector(q);
  // Center camera on table
  const bbox = grp.getBBox();
  const r = canvasWrapper.getBoundingClientRect();
  scale = 1.15;
  translateX = (r.width / 2) - (bbox.x + bbox.width / 2) * scale;
  translateY = (r.height / 2) - (bbox.y + bbox.height / 2) * scale;
  updateTransform();
}});

// Domain Chip Filtering
document.querySelectorAll('.legend-chip').forEach(chip => {{
  chip.addEventListener('click', (e) => {{
    e.stopPropagation();
    const dkey = chip.getAttribute('data-domain');
    const allGroups = document.querySelectorAll('.erd-table-group');
    const allRels = document.querySelectorAll('.erd-rel');
    
    allGroups.forEach(g => {{
      const match = g.getAttribute('data-domain') === dkey;
      g.classList.toggle('dimmed', !match);
      g.classList.toggle('highlighted', match);
    }});
  }});
}});

// Export SVG
document.getElementById('btn-dl-svg').addEventListener('click', () => {{
  const svg = document.getElementById('main-erd-svg');
  const serializer = new XMLSerializer();
  const src = '<?xml version="1.0" standalone="no"?>\\r\\n' + serializer.serializeToString(svg);
  const blob = new Blob([src], {{type: "image/svg+xml;charset=utf-8"}});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'AI-COS-Pharmacy-ERD-v6.svg';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}});

// Initial fit on load
window.addEventListener('load', fitToScreen);
window.addEventListener('resize', fitToScreen);
setTimeout(fitToScreen, 100);
</script>
</body>
</html>
"""
    return html_content

if __name__ == '__main__':
    html_code = build_full_html()
    
    # Save to both target locations
    path1 = "D:/Graduation Project/مستندات/pharmacy_erd_v6.html"
    path2 = "D:/Graduation Project/pharmacy_erd_v6.html"
    
    with open(path1, "w", encoding="utf-8") as f:
        f.write(html_code)
    print("Saved to path1 successfully")
    
    with open(path2, "w", encoding="utf-8") as f:
        f.write(html_code)
    print("Saved to path2 successfully")
