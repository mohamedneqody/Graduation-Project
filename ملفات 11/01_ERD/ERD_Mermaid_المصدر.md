# 🗃️ ERD — مصدر Mermaid (النطاق الجوهري)
> **المرجع الكامل التفاعلي:** `ERD_v7_تفاعلي.html` (37 جدولًا · 39 جدولًا في الإنتاج)
> هذا المصدر يغطي النواة العلائقية — يُعرض بدعم Mermaid في GitHub/VS Code/Obsidian

```mermaid
erDiagram
    TENANTS ||--o{ CUSTOMERS : "يستضيف"
    TENANTS ||--o{ INVENTORY_ITEMS : "يمتلك المخزون"
    CUSTOMERS ||--o{ ORDERS : "يطلب"
    CUSTOMERS ||--o{ SESSIONS : "يفتح جلسة"
    CUSTOMERS ||--o{ PENDING_REMINDERS : "مذكور له"
    CUSTOMERS ||--o{ COMPLAINTS : "يقدم شكوى"
    CUSTOMERS ||--o{ AI_CHAT_LOGS : "يتحاور"
    SESSIONS ||--o{ EVENTS : "يسجل أحداثاً"
    ORDERS ||--|{ ORDER_ITEMS : "يحتوي"
    DRUGS ||--o{ ORDER_ITEMS : "يُباع كـ"
    DRUGS ||--o{ INVENTORY_ITEMS : "مخزن كـ"
    DRUGS ||--o{ DRUG_INTERACTIONS : "يتعارض مع"
    DRUGS ||--o{ DRUG_AFFINITIES : "يتكامل مع"
    DRUGS ||--o{ PENDING_REMINDERS : "دورة علاجه"
    DRUGS ||--o{ PRESCRIPTION_ITEMS : "يُطابق من الروشتة"
    PRESCRIPTIONS ||--|| PRESCRIPTION_ANALYSES : "يُحلل"
    PRESCRIPTION_ANALYSES ||--|{ PRESCRIPTION_ITEMS : "يستخرج بنوده"
    SUPPLIERS ||--o{ PURCHASE_ORDERS : "يورّد"
    PURCHASE_ORDERS ||--|{ PURCHASE_ORDER_ITEMS : "بنوده"
    MARKET_INTELLIGENCE_ACTIONS ||--|| MARKET_ACTION_OUTBOX : "يؤمن تنفيذه بـ"
    MARKET_INTELLIGENCE_ACTIONS {
        uuid action_id PK
        varchar action_type
        varchar status "PENDING_APPROVAL-AWAITING-EXECUTED-REJECTED"
        varchar priority "critical-high-normal"
        varchar title
        varchar market_signal_id "إشارة السوق المصدر"
        jsonb parameters
        jsonb execution_result
        uuid maker_id FK "اعتماد أول (Maker)"
        uuid checker_id FK "اعتماد ثانٍ (Checker)"
        timestamp approved_at
        timestamp executed_at
    }
    MARKET_ACTION_OUTBOX {
        uuid id PK
        uuid action_id FK
        varchar event_id "MI-{action_id}"
        varchar status "PENDING-PROCESSING-SENT-DEAD_LETTER"
        int attempts
        varchar payload_hash
        varchar worm_line_hash
    }
    ORDERS {
        uuid order_id PK
        uuid customer_id FK
        varchar status
        decimal total
        varchar payment_method
    }
    PENDING_REMINDERS {
        uuid reminder_id PK
        float predicted_days "توقيت الدورة (predict_cycle)"
        float churn_probability
        varchar decision
    }
```

**ملاحظات الحوكمة الظاهرة في التصميم:**
- `MARKET_INTELLIGENCE_ACTIONS` يحمل `maker_id` + `checker_id` — لا يُنفَّذ قرار CRITICAL إلا بهويتين مختلفتين
- `MARKET_ACTION_OUTBOX` يحمل `payload_hash` + `worm_line_hash` — التنفيذ مرة واحدة والربط بسجل WORM
- `EVENTS` يحمل `payload_hash` + `prev_hash` — سلسلة تدقيق جلسات المحادثة
