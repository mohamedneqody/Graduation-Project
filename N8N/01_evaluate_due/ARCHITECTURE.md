# المعمارية الفنية: evaluate_due Architecture

```mermaid
flowchart LR
    A[Schedule: 0 9 * * *] --> C[FastAPI: /internal/cycles/recalculate]
    B[Webhook: POST /evaluate_due] --> C
    C --> D[(Supabase PostgreSQL: pending_reminders)]
    C --> E[Telegram Bot: Admin Alert]
```

## 🔐 ضوابط الحوكمة والأمان
- **رمز المصادقة الداخلي (Internal Token):** محمي برأس `X-Internal-Token` لمنع الاستدعاء الخارجي غير المصرح به.
- **الاستجابة الفورية (Immediately):** الـ Webhook يرسل استجابة `200 OK` فوراً لمنع حدوث Timeout في السيرفر الرئيسي.
- **تصنيف الضابط الرقابي (COSO):** ضابط وقائي وتوجيهي (Preventive & Directive Control).
